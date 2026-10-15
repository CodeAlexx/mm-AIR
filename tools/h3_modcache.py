"""Build MiniMax-H3 adaLN modulation caches for any simple-schedule step count.

MM-Air's sampler reads per-block adaLN tables precomputed for the exact
timesteps of one schedule (`serenity_runtime_cache_v1/<schedule>/
native-modcache-*-stepsN-blocks50.safetensors`). Distilled turbo LoRAs need
step counts that were never prepared, so this tool computes them from the
official checkpoint with the same row layout ("per-evaluation-sorted-unique-
padded-v1"): for each evaluation the sorted distinct timesteps of the generated
video, generated audio, conditioned video (max(t, 0.999)) and, for audio
references, conditioned audio (1.0), padded with the last value to the table
count. adaLN must not be touched by any merged LoRA.

  verify ROOT EXISTING.safetensors --evaluations 7 --tables 3
  build  ROOT OUT.safetensors      --evaluations 4 --tables 3
"""
import argparse
import json
import os
import struct
import sys
from pathlib import Path

import numpy as np

HIDDEN, BLOCKS = 5376, 50
VIDEO_SHIFT, AUDIO_SHIFT = np.float32(12.0), np.float32(3.0)
CONDITION_T = np.float32(0.999)


def header(path):
    with open(path, 'rb') as handle:
        length = struct.unpack('<Q', handle.read(8))[0]
        return json.loads(handle.read(length)), 8 + length


class Checkpoint:
    def __init__(self, root):
        self.root = Path(root) / 'transformer'
        self.map = json.loads((self.root / 'model.safetensors.index.json').read_text())['weight_map']
        self.headers = {}

    def f32(self, name):
        file = self.root / self.map[name]
        if file not in self.headers:
            self.headers[file] = header(file)
        entries, base = self.headers[file]
        entry = entries[name]
        begin, end = entry['data_offsets']
        with open(file, 'rb') as handle:
            handle.seek(base + begin)
            raw = handle.read(end - begin)
        if entry['dtype'] == 'BF16':
            value = (np.frombuffer(raw, dtype=np.uint16).astype(np.uint32) << 16).view(np.float32)
        else:
            assert entry['dtype'] == 'F32', (name, entry['dtype'])
            value = np.frombuffer(raw, dtype=np.float32)
        return value.reshape(entry['shape'])


def shifted(base, shift):
    return (shift * base) / (np.float32(1.0) + (shift - np.float32(1.0)) * base)


def simple_schedule(evaluations):
    """tables.simple_av_schedule in the same F32 operation order."""
    video, audio = [], []
    stride = 1000.0 / evaluations
    for step in range(evaluations):
        table_index = 999 - int(step * stride)
        base = np.float32(table_index + 1) / np.float32(1000.0)
        v = shifted(base, VIDEO_SHIFT)
        unshifted = v / (VIDEO_SHIFT + v * (np.float32(1.0) - VIDEO_SHIFT))
        video.append(v)
        audio.append(shifted(unshifted, AUDIO_SHIFT))
    return video + [np.float32(0)], audio + [np.float32(0)]


def timestep_rows(evaluations, tables):
    video, audio = simple_schedule(evaluations)
    rows = []
    for e in range(evaluations):
        vt = np.float32(1.0) - video[e]
        at = np.float32(1.0) - audio[e]
        values = [vt, at]
        if tables >= 3:
            values.append(max(vt, CONDITION_T))
        if tables >= 4:
            values.append(np.float32(1.0))
        distinct = sorted(set(float(v) for v in values))
        distinct += [distinct[-1]] * (tables - len(distinct))
        rows.extend(distinct)
    return np.array(rows, dtype=np.float32)


def features(timesteps):
    half = 128
    log_period = np.float32(np.log(np.float32(10000.0)))
    column = np.arange(half, dtype=np.float32)
    frequency = np.exp(((np.float32(0) - log_period) * column / np.float32(half)).astype(np.float32))
    angle = timesteps[:, None].astype(np.float32) * frequency[None, :]
    return np.concatenate([np.cos(angle), np.sin(angle)], axis=1).astype(np.float32)


def silu(x):
    return (x / (np.float32(1.0) + np.exp(-x))).astype(np.float32)


def bf16(x):
    bits = x.astype(np.float32).view(np.uint32)
    rounded = (bits + (0x7FFF + ((bits >> 16) & 1))) & 0xFFFF0000
    return rounded.astype(np.uint32).view(np.float32)


def bf16_bits(x):
    return (bf16(x).view(np.uint32) >> 16).astype(np.uint16)


def activated(checkpoint, timesteps):
    hidden = features(timesteps) @ checkpoint.f32('time_embedder.proj_in.weight').T
    hidden = hidden + checkpoint.f32('time_embedder.proj_in.bias')
    embedded = silu(hidden) @ checkpoint.f32('time_embedder.proj_out.weight').T
    embedded = embedded + checkpoint.f32('time_embedder.proj_out.bias')
    return bf16(silu(embedded))


def tables_for(checkpoint, timesteps):
    active = activated(checkpoint, timesteps)
    for layer in range(BLOCKS):
        weight = checkpoint.f32(f'blocks.{layer}.adaln_proj.linear.weight')
        bias = checkpoint.f32(f'blocks.{layer}.adaln_proj.linear.bias')
        projected = active @ weight.T + bias
        yield f'block.{layer}', projected.reshape(len(timesteps) * 3, 6 * HIDDEN)
    weight = checkpoint.f32('final_layer.adaln_proj.linear.weight')
    bias = checkpoint.f32('final_layer.adaln_proj.linear.bias')
    yield 'final', active @ weight.T + bias


def meta_tensors(root, evaluations, rows):
    index = Path(root) / 'transformer' / 'model.safetensors.index.json'
    stat = index.stat()
    text = lambda value: np.frombuffer(value.encode(), dtype=np.uint8)
    one = lambda value: np.array([value], dtype=np.int64)
    return [('__meta__.version', 'I64', one(1)),
            ('__meta__.kind', 'U8', text('adaln-modulation')),
            ('__meta__.row_layout', 'U8', text('per-evaluation-sorted-unique-padded-v1')),
            ('__meta__.src_path', 'U8', text(str(index))),
            ('__meta__.src_size', 'I64', one(stat.st_size)),
            ('__meta__.src_mtime', 'I64', one(int(stat.st_mtime))),
            ('__meta__.steps', 'I64', one(evaluations + 1)),
            ('__meta__.distinct_timesteps', 'I64', one(rows)),
            ('__meta__.nblocks', 'I64', one(BLOCKS))]


def build(args):
    out = Path(args.out)
    if out.exists():
        sys.exit(f'{out} exists; choose a fresh path')
    checkpoint = Checkpoint(args.root)
    timesteps = timestep_rows(args.evaluations, args.tables)
    tensors = meta_tensors(args.root, args.evaluations, len(timesteps))
    for name, value in tables_for(checkpoint, timesteps):
        tensors.append((name, 'BF16', bf16_bits(value)))
        print(f'{name} {value.shape}', flush=True)
    meta, offset = {}, 0
    for name, dtype, value in tensors:
        shape = list(value.shape) if dtype != 'BF16' else list(value.shape)
        meta[name] = {'dtype': dtype, 'shape': shape,
                      'data_offsets': [offset, offset + value.nbytes]}
        offset += value.nbytes
    blob = json.dumps(meta, separators=(',', ':')).encode()
    blob += b' ' * (-len(blob) % 8)
    partial = out.with_suffix('.partial')
    with open(partial, 'wb') as handle:
        handle.write(struct.pack('<Q', len(blob)))
        handle.write(blob)
        for _, _, value in tensors:
            handle.write(value.tobytes())
    os.replace(partial, out)
    print(f'BUILT {out} rows={len(timesteps)}')


def verify(args):
    entries, base = header(args.existing)
    checkpoint = Checkpoint(args.root)
    timesteps = timestep_rows(args.evaluations, args.tables)
    print('timesteps', [round(float(t), 6) for t in timesteps])
    worst, total, exact, count = 0.0, 0.0, 0, 0
    with open(args.existing, 'rb') as handle:
        for name, value in tables_for(checkpoint, timesteps):
            entry = entries[name]
            assert entry['shape'] == list(value.shape), (name, entry['shape'], value.shape)
            begin, end = entry['data_offsets']
            handle.seek(base + begin)
            stored = (np.frombuffer(handle.read(end - begin), dtype=np.uint16)
                      .astype(np.uint32) << 16).view(np.float32).reshape(value.shape)
            mine = bf16(value)
            diff = np.abs(mine - stored)
            scale = np.abs(stored).max()
            worst = max(worst, float(diff.max() / scale))
            exact += int((diff == 0).sum())
            count += diff.size
            total += float(np.sqrt((diff ** 2).sum() / (stored ** 2).sum()))
            if name in ('block.0', 'block.49', 'final'):
                print(f'{name}: exact {(diff == 0).mean():.4f} max_rel {diff.max() / scale:.2e}')
    print(f'exact fraction {exact / count:.4f}; worst max_rel {worst:.2e}; mean rel_l2 {total / 51:.2e}')
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command', required=True)
    v = sub.add_parser('verify')
    v.add_argument('root')
    v.add_argument('existing')
    b = sub.add_parser('build')
    b.add_argument('root')
    b.add_argument('out')
    for p in (v, b):
        p.add_argument('--evaluations', type=int, required=True)
        p.add_argument('--tables', type=int, choices=(2, 3, 4), required=True)
    args = parser.parse_args()
    return verify(args) if args.command == 'verify' else build(args)


if __name__ == '__main__':
    sys.exit(main())
