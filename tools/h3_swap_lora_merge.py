"""Merge H3 Ref2VA LoRAs into a ConvRot transformer cache.

MM-Air samples Ref2VA through fused ConvRot INT8 kernels, which have no LoRA
insertion points. This tool bakes one or more ComfyUI-layout LoRAs (optional
per-projection `.alpha`, scale alpha/rank, else 1) into the official BF16 weights and re-quantizes them with the exact H256
ConvRot recipe of difh3convrot (per-row F32 scale, contiguous Q/K/V rows), so a
LoRA-specific Ref2VA root runs at normal ConvRot speed.

  verify  ROOT [--blocks 0,49]            requantize unmerged blocks and compare
                                           bytes with ROOT's existing cache
  merge   ROOT OUT LORA[@STRENGTH] ...      write OUT as a complete Ref2VA root

ComfyUI LoRAs address fused QKV as contiguous [q;k;v] rows, while the raw
official shards interleave Q/K/V per head (diffusers reorder_interleaved_qkv);
LoRA deltas are re-interleaved before merging. FC1 is [gate; value] in both.
"""
import argparse
import json
import os
import struct
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

CACHE = 'serenity_runtime_cache_v1/native_convrot_h256_ref2va_blocks_50.safetensors'
INNER, HEAD_DIM, LAYERS = 7168, 128, 50
SOURCE = ['attn.qkv_proj', 'attn.out_proj', 'mlp.fc1', 'mlp.fc2']
INV127 = np.float32(1.0) / np.float32(127.0)


def header(path):
    with open(path, 'rb') as handle:
        length = struct.unpack('<Q', handle.read(8))[0]
        return json.loads(handle.read(length)), 8 + length


class Checkpoint:
    def __init__(self, index_path):
        self.root = Path(index_path).parent
        self.map = json.loads(Path(index_path).read_text())['weight_map']
        self.headers = {}

    def bf16(self, name):
        file = self.root / self.map[name]
        if file not in self.headers:
            self.headers[file] = header(file)
        entries, base = self.headers[file]
        entry = entries[name]
        assert entry['dtype'] == 'BF16', name
        begin, end = entry['data_offsets']
        with open(file, 'rb') as handle:
            handle.seek(base + begin)
            raw = np.frombuffer(handle.read(end - begin), dtype=np.uint16)
        return raw.reshape(entry['shape'])


def lora_pair(path, cache, name):
    """Return (A, B, scale) for one projection, or None if absent."""
    if path not in cache:
        cache[path] = header(path)
    entries, base = cache[path]
    if f'diffusion_model.{name}.lora_A.weight' not in entries:
        return None
    out = []
    with open(path, 'rb') as handle:
        for side in ('lora_A', 'lora_B'):
            entry = entries[f'diffusion_model.{name}.{side}.weight']
            begin, end = entry['data_offsets']
            handle.seek(base + begin)
            out.append(decode(handle.read(end - begin), entry['dtype']).reshape(entry['shape']))
        scale = 1.0
        alpha = entries.get(f'diffusion_model.{name}.alpha')
        if alpha is not None:
            begin, end = alpha['data_offsets']
            handle.seek(base + begin)
            value = decode(handle.read(end - begin), alpha['dtype'])
            scale = float(value.reshape(-1)[0]) / out[0].shape[0]
    return out[0], out[1], scale


def decode(raw, dtype):
    if dtype == 'BF16':
        return to_f32(np.frombuffer(raw, dtype=np.uint16))
    if dtype == 'F16':
        return np.frombuffer(raw, dtype=np.float16).astype(np.float32)
    assert dtype == 'F32', dtype
    return np.frombuffer(raw, dtype=np.float32).copy()


def interleave_qkv_rows(delta):
    """Contiguous [q;k;v] rows -> per-head interleaved official rows."""
    official = np.arange(delta.shape[0])
    head, within = official // (3 * HEAD_DIM), official % (3 * HEAD_DIM)
    part, d = within // HEAD_DIM, within % HEAD_DIM
    return delta[part * INNER + head * HEAD_DIM + d]


def to_f32(bits16):
    return (bits16.astype(np.uint32) << 16).view(np.float32)


def round_bf16(values):
    # Same integer rounding as the donor kernel: NaN/Inf pass through.
    bits = values.view(np.uint32)
    special = (bits & 0x7F800000) == 0x7F800000
    rounded = (bits + (0x7FFF + ((bits >> 16) & 1))) & 0xFFFF0000
    return np.where(special, bits, rounded).astype(np.uint32).view(np.float32)


def merged_bf16_bits(weight_bits, name, loras, cache):
    """Add every LoRA's delta for projection `name` in F32, round once to BF16."""
    weight = to_f32(weight_bits)
    touched = False
    for path, strength in loras:
        pair = lora_pair(path, cache, name)
        if pair is None:
            continue
        a, b, scale = pair
        delta = (b @ a).astype(np.float32) * np.float32(scale * strength)
        if name.endswith('attn.qkv_proj'):
            delta = interleave_qkv_rows(delta)
        weight = weight + delta
        touched = True
    if not touched:
        return weight_bits
    merged = round_bf16(weight)
    return (merged.view(np.uint32) >> 16).astype(np.uint16)


def stage(x, axis):
    x0, x1, x2, x3 = (np.take(x, i, axis=axis) for i in range(4))
    half = np.float32(0.5)
    y0 = half * (((x0 + x1) + x2) - x3)
    y1 = half * (((x0 + x1) - x2) + x3)
    y2 = half * (((x0 - x1) + x2) + x3)
    y3 = half * ((((-x0) + x1) + x2) + x3)
    return np.stack([y0, y1, y2, y3], axis=axis)


def convrot(bits, reorder_qkv):
    rows, columns = bits.shape
    if reorder_qkv:
        out_row = np.arange(rows)
        part, within = out_row // INNER, out_row % INNER
        head, d = within // HEAD_DIM, within % HEAD_DIM
        bits = bits[(head * 3 + part) * HEAD_DIM + d]
    weight = np.empty((rows, columns), dtype=np.int8)
    scales = np.empty(rows, dtype=np.float32)
    step = 1024
    for start in range(0, rows, step):
        x = to_f32(bits[start:start + step])
        n = x.shape[0]
        # index = d0 + 4*d1 + 16*d2 + 64*d3 inside each 256-wide group
        x = x.reshape(n, columns // 256, 4, 4, 4, 4)
        for axis in (5, 4, 3, 2):
            x = stage(x, axis)
        y = x.reshape(n, columns)
        scale = np.abs(y).max(axis=1) * INV127
        scale = np.maximum(scale, np.float32(1.0e-30))
        scales[start:start + n] = scale
        scale16 = round_bf16(scale.copy())
        q = np.rint(round_bf16(round_bf16(y) / scale16[:, None]))
        weight[start:start + n] = np.clip(q, -128, 127).astype(np.int8)
    return weight, scales


def block_payload(job):
    root, loras, layer = job
    checkpoint = Checkpoint(Path(root) / 'transformer/model.safetensors.index.json')
    cache = {}
    out = []
    for slot, source in enumerate(SOURCE):
        name = f'blocks.{layer}.{source}'
        bits = checkpoint.bf16(name + '.weight')
        if loras:
            bits = merged_bf16_bits(bits, name, loras, cache)
        weight, scales = convrot(bits, slot == 0)
        out.append((weight.tobytes(), scales.tobytes()))
    return layer, out


def cache_layout(path):
    entries, base = header(path)
    return entries, base


def verify(args):
    cache_path = Path(args.root) / CACHE
    entries, base = cache_layout(cache_path)
    layers = [int(v) for v in args.blocks.split(',')]
    ok = True
    with open(cache_path, 'rb') as handle:
        for layer in layers:
            _, payload = block_payload((args.root, [], layer))
            for slot, (weight, scales) in enumerate(payload):
                for kind, data in (('weight', weight), ('scale', scales)):
                    begin, end = entries[f'block.{layer}.convrot_{kind}.{slot}']['data_offsets']
                    handle.seek(base + begin)
                    expected = handle.read(end - begin)
                    same = expected == data
                    if not same:
                        a = np.frombuffer(expected, dtype=np.int8 if kind == 'weight' else np.float32)
                        b = np.frombuffer(data, dtype=a.dtype)
                        diff = int((a != b).sum())
                        print(f'block {layer} {kind}.{slot}: {diff} of {a.size} differ')
                    else:
                        print(f'block {layer} {kind}.{slot}: exact')
                    ok = ok and same
    print('VERIFY PASS' if ok else 'VERIFY FAIL')
    return 0 if ok else 1


def link_tree(source, target):
    # Junctions need no privilege and keep the swap root a thin overlay.
    subprocess.run(['cmd', '/c', 'mklink', '/J', str(target), str(source)],
                   check=True, stdout=subprocess.DEVNULL)


def merge_refiner(args, out_transformer):
    checkpoint = Checkpoint(Path(args.root) / 'transformer/model.safetensors.index.json')
    cache = {}
    tensors = {}
    for layer in range(2):
        for source in SOURCE:
            name = f'token_refiner.blocks.{layer}.{source}'
            if not any(f'diffusion_model.{name}.lora_A.weight' in header(path)[0]
                       for path, _ in args.loras):
                continue
            bits = checkpoint.bf16(name + '.weight')
            tensors[name + '.weight'] = merged_bf16_bits(bits, name, args.loras, cache)
    shard = 'refiner-swap-merged.safetensors'
    meta, offset = {}, 0
    for name, value in tensors.items():
        meta[name] = {'dtype': 'BF16', 'shape': list(value.shape),
                      'data_offsets': [offset, offset + value.nbytes]}
        offset += value.nbytes
    blob = json.dumps(meta, separators=(',', ':')).encode()
    blob += b' ' * (-len(blob) % 8)
    with open(out_transformer / shard, 'wb') as handle:
        handle.write(struct.pack('<Q', len(blob)))
        handle.write(blob)
        for value in tensors.values():
            handle.write(value.tobytes())
    index = json.loads((Path(args.root) / 'transformer/model.safetensors.index.json').read_text())
    for name in tensors:
        index['weight_map'][name] = shard
    for file in sorted(set(checkpoint.map.values())):
        os.link(Path(args.root) / 'transformer' / file, out_transformer / file)
    (out_transformer / 'model.safetensors.index.json').write_text(json.dumps(index, indent=2))
    return len(tensors)


def merge(args):
    root, out = Path(args.root), Path(args.out)
    if out.exists():
        sys.exit(f'{out} already exists; choose a fresh output root')
    for path, _ in args.loras:
        lora_keys = header(path)[0]
        assert all(k.startswith('diffusion_model.') or k == '__metadata__' for k in lora_keys), path
        assert not any('adaln' in k for k in lora_keys), 'adaLN LoRA would invalidate modulation caches'
    out.mkdir(parents=True)
    (out / 'transformer').mkdir()
    for name in ('text_encoder', 'video_vae', 'audio_vae'):
        if (root / name).exists():
            link_tree((root / name).resolve(), out / name)
    cache_out = out / 'serenity_runtime_cache_v1'
    cache_out.mkdir()
    for name in ('exponential', 'simple'):
        if (root / 'serenity_runtime_cache_v1' / name).exists():
            link_tree(root / 'serenity_runtime_cache_v1' / name, cache_out / name)
    refined = merge_refiner(args, out / 'transformer')
    print(f'token refiner: merged {refined} projections')
    entries, base = cache_layout(root / CACHE)
    target = cache_out / Path(CACHE).name
    partial = target.with_suffix('.partial')
    with open(root / CACHE, 'rb') as source, open(partial, 'wb') as handle:
        handle.write(source.read(base))  # identical header: same names, shapes, offsets
        begin, end = entries['__meta__.h3_convrot']['data_offsets']
        source.seek(base + begin)
        handle.write(source.read(end - begin))
        jobs = [(str(root), args.loras, layer) for layer in range(LAYERS)]
        with ProcessPoolExecutor(args.workers) as pool:
            for layer, payload in pool.map(block_payload, jobs):
                for slot, (weight, scales) in enumerate(payload):
                    for kind, data in (('weight', weight), ('scale', scales)):
                        begin, end = entries[f'block.{layer}.convrot_{kind}.{slot}']['data_offsets']
                        assert handle.tell() == base + begin and len(data) == end - begin
                        handle.write(data)
                print(f'block {layer} merged', flush=True)
    partial.rename(target)
    (out / 'swap-lora.json').write_text(json.dumps({
        'schema': 'mm-air.h3-merged-lora-root.v1', 'source_root': str(root),
        'loras': [{'path': str(Path(p).resolve()), 'strength': w} for p, w in args.loras],
        'merged_cache': str(target)}, indent=2))
    print(f'MERGE DONE {out}')


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    v = sub.add_parser('verify')
    v.add_argument('root')
    v.add_argument('--blocks', default='0,49')
    m = sub.add_parser('merge')
    m.add_argument('root')
    m.add_argument('out')
    m.add_argument('lora', nargs='+', help='LORA.safetensors[@STRENGTH]')
    m.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    if args.command == 'merge':
        args.loras = []
        for item in args.lora:
            path, _, strength = item.rpartition('@') if '@' in item else (item, '', '')
            args.loras.append((path, float(strength) if strength else 1.0))
    return verify(args) if args.command == 'verify' else merge(args)


if __name__ == '__main__':
    sys.exit(main())
