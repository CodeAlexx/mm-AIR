"""Run the real history regression with isolated Windows profile locations."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--binary', type=Path, required=True)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='mm-air history café ') as temporary:
        for mode in ('local', 'profile', 'override'):
            root = Path(temporary) / mode
            environment = os.environ.copy()
            for key in ('HOME', 'XDG_DATA_HOME', 'LOCALAPPDATA', 'USERPROFILE'):
                environment.pop(key, None)
            environment['USERPROFILE'] = str(root / 'profile')
            expected = root / 'profile/AppData/Local/mm-air'
            if mode != 'profile':
                environment['LOCALAPPDATA'] = str(root / 'local data')
                expected = root / 'local data/mm-air'
            if mode == 'override':
                environment['XDG_DATA_HOME'] = str(root / 'explicit data')
                expected = root / 'explicit data/mm-air'
            run = subprocess.run([str(args.binary.resolve()), str(root / 'media')],
                                 env=environment, capture_output=True, text=True, timeout=60)
            assert run.returncode == 0, (mode, run.stdout, run.stderr, run.returncode)
            catalog = json.loads((expected / 'generate-history.json').read_text(encoding='utf-8'))
            assert catalog['items'] == []
            assert (root / 'media/output/krea/krea-test.png').exists()
    print('PASS: native history persistence, Windows profile fallback, explicit override and media-preserving clear.')


if __name__ == '__main__':
    main()
