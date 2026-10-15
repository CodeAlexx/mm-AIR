"""Exercise the native executable's real load/edit/save and render path."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
from PIL import Image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--render', type=Path, required=True)
    args = parser.parse_args()
    args.render.parent.mkdir(parents=True, exist_ok=True)
    request = dict(schema='mm-air.qwen-image-2.1.parameters', version=2,
                   model='qwen-image-2.1', mode='edit', prompt='A robot in a café garden',
                   source='first.png', references=['second.png', 'third.png'],
                   output='result.png', width=2048, height=2048, steps=40,
                   scheduler=1, sampler=1, seed=18446744073709551615)
    with tempfile.TemporaryDirectory(prefix='mm-air-native-') as temporary:
        root = Path(temporary)
        environment = os.environ.copy()
        environment['XDG_DATA_HOME'] = str(root / 'data')
        source, saved = root / 'input.json', root / 'saved.json'
        source.write_text(json.dumps(request, ensure_ascii=False), encoding='utf-8')
        preview = root / 'preview.png'
        colour = (239, 17, 83)
        Image.new('RGB', (64, 32), colour).save(preview)
        history = dict(schema='mm-air.generate.history', version=2, items=[
            dict(path=str(preview), thumbnail=str(preview), parameters=json.dumps(request), postprocess='')])
        history_file = root / 'data/mm-air/generate-history.json'
        history_file.parent.mkdir(parents=True)
        history_file.write_text(json.dumps(history), encoding='utf-8')
        subprocess.run([str(args.binary.resolve()), '--parameters', str(source),
                        '--save', str(saved), '--preview', str(preview),
                        '--render', str(args.render.resolve())],
                       check=True, timeout=60, env=environment)
        restored = json.loads(saved.read_text(encoding='utf-8'))
        for key, expected in request.items():
            assert restored[key] == expected, (key, restored[key], expected)
        assert args.render.read_bytes()[:8] == b'\x89PNG\r\n\x1a\n'
        with Image.open(args.render) as rendered:
            rgb = rendered.convert('RGB')
            points = [(x, y) for y in range(rgb.height) for x in range(rgb.width)
                      if rgb.getpixel((x, y)) == colour]
            assert len(points) > 1000, 'Output preview was not painted'
            left, right = min(x for x, _ in points), max(x for x, _ in points)
            top, bottom = min(y for _, y in points), max(y for _, y in points)
            assert rgb.size == (1600, 1000)
            assert left >= 724 and right < 1356, 'Preview overlaps parameters or history'
            assert abs((right-left+1) / (bottom-top+1) - 2) < 0.03, 'Preview stretched'
        preview.write_bytes(b'not a png')
        failed = subprocess.run([str(args.binary.resolve()), '--preview', str(preview),
                                 '--render', str(root / 'invalid.png')],
                                capture_output=True, timeout=60, env=environment)
        assert failed.returncode == 6, failed.stderr
        assert not (root / 'invalid.png').exists()
        krea = dict(schema='mm-air.krea2.parameters', version=1, model='krea2-turbo',
                    prompt='A café garden at dawn', seed=9223372036854775807,
                    width=1024, height=1024, steps=8, precision='bf16',
                    output='krea-result.png', loras=[
                        dict(path='D:/loras/café.safetensors', strength=0.75, enabled=True),
                        dict(path='D:/loras/second.safetensors', strength=-0.5, enabled=False),
                        dict(path='D:/loras/third.safetensors', strength=0.25, enabled=False),
                        dict(path='D:/loras/fourth.safetensors', strength=1.25, enabled=False),
                        dict(path='D:/loras/fifth.safetensors', strength=-2.0, enabled=False)])
        source.write_text(json.dumps(krea, ensure_ascii=False), encoding='utf-8')
        krea_render = args.render.with_stem(args.render.stem + '-krea')
        subprocess.run([str(args.binary.resolve()), '--parameters', str(source),
                        '--save', str(saved), '--render', str(krea_render.resolve())],
                       check=True, timeout=60, env=environment)
        assert json.loads(saved.read_text(encoding='utf-8')) == krea
        h3 = dict(schema='mm-air.generate.parameters', version=1,
                  prompt='A robot walks through a garden, birds singing.',
                  model=1, task=3, profile=3, conditioner_projection=1,
                  transformer_projection=2, attention=4, seed=9223372036854775807,
                  resolution=7, width=832, height=480, seconds=5.166666666666667,
                  references=['C:/images/café.png', 'D:/images/last.png'],
                  audio_references=['D:/sound.wav'], output='movie.mp4',
                  loras=[dict(path='D:/loras/h3.safetensors', strength=0.5, enabled=True)])
        source.write_text(json.dumps(h3, ensure_ascii=False), encoding='utf-8')
        h3_render = args.render.with_stem(args.render.stem + '-h3')
        subprocess.run([str(args.binary.resolve()), '--parameters', str(source),
                        '--save', str(saved), '--render', str(h3_render.resolve())],
                       check=True, timeout=60, env=environment)
        assert json.loads(saved.read_text(encoding='utf-8')) == h3
        assert json.loads(history_file.read_text(encoding='utf-8')) == history
    print('PASS: parameter round-trip, exact u64 seed, Unicode, reference order, aspect-fit preview and invalid PNG refusal. No generation tested.')


if __name__ == '__main__':
    main()
