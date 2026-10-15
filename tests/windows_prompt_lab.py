"""Exercise real Prompt Lab inference, cancellation and routing in native Windows.

Developer-only harness with isolated preferences and output. Runs the shared UI.
"""
import argparse
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('application', type=Path)
    parser.add_argument('adapter', type=Path)
    parser.add_argument('--model-directory', type=Path)
    parser.add_argument('--manifest-directory', type=Path)
    parser.add_argument('--image', type=Path)
    parser.add_argument('--runtime-directory', type=Path)
    parser.add_argument('--direct', action='store_true')
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    user = C.WinDLL('user32', use_last_error=True)
    user.SetProcessDPIAware()
    user.SendMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
    user.SendMessageW.restype = W.LPARAM
    user.PostMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
    callback = C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)

    def text(window):
        value = C.create_unicode_buffer(32768)
        user.SendMessageW(window, 0xD, len(value), C.cast(value, C.c_void_p).value)
        return value.value

    def kind(window):
        value = C.create_unicode_buffer(128)
        user.GetClassNameW(window, value, len(value))
        return value.value

    def windows(parent=None):
        found = []
        @callback
        def collect(window, _):
            found.append(window)
            return True
        if parent:
            user.EnumChildWindows(parent, collect, 0)
        else:
            user.EnumWindows(collect, 0)
        return found

    def wait(predicate, message, seconds=30):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            assert process.poll() is None, 'Controller exited unexpectedly'
            value = predicate()
            if value:
                return value
            time.sleep(.05)
        raise AssertionError(message + '\n' + '\n'.join(text(w) for w in windows(host)))

    def button(label):
        return next((w for w in windows(host) if kind(w) == 'Button' and text(w) == label and user.IsWindowVisible(w)), None)

    def click(label):
        target = wait(lambda: button(label), 'Button is not visible: ' + label)
        user.PostMessageW(target, 0xF5, 0, 0)

    def replace(editor, value):
        buffer = C.create_unicode_buffer(value)
        user.SendMessageW(editor, 0xB1, 0, -1)
        user.SendMessageW(editor, 0xC2, 1, C.cast(buffer, C.c_void_p).value)

    environment = os.environ.copy()
    for key in tuple(environment):
        if key.startswith(('MM_AIR_', 'AIR_QWEN3_VL_')):
            del environment[key]
    if args.direct:
        environment['PATH'] = os.pathsep.join([str(Path(os.environ['SystemRoot'])/'System32'),
                                               os.environ['SystemRoot']])
    elif args.runtime_directory:
        environment['PATH'] = str(args.runtime_directory.resolve()) + os.pathsep + environment['PATH']
    result = {'application': str(args.application.resolve()),
              'application_sha256': hashlib.sha256(args.application.read_bytes()).hexdigest(),
              'adapter_sha256': hashlib.sha256(args.adapter.read_bytes()).hexdigest(),
              'direct_launch': args.direct, 'runtime_directory_override': bool(args.runtime_directory)}
    with tempfile.TemporaryDirectory(prefix='mm-air-prompt-') as temporary:
        root = Path(temporary)
        data = root/'data/mm-air'
        data.mkdir(parents=True)
        output = root/'output'
        prefs = {'schema': 'mm-air.runtime.v1', 'MM_AIR_OUTPUT_ROOT': str(output)}
        if not args.direct:
            assert args.model_directory and args.manifest_directory
            prefs.update({'AIR_QWEN3_VL_4B_DIR': str(args.model_directory.resolve()),
                          'MM_AIR_PROMPT_MANIFEST_ROOT': str(args.manifest_directory.resolve())})
        (data/'runtime.json').write_text(json.dumps(prefs), encoding='utf-8')
        environment['XDG_DATA_HOME'] = str(root/'data')
        before = set(windows())
        command = [str(args.application.resolve())]
        if not args.direct:
            source = Path(__file__).resolve().parents[1]
            command.extend([str(source/'desktop.ui'), str(source/'desktop.css'), str(args.adapter.resolve())])
        with (root/'log').open('w+', encoding='utf-8') as log:
            process = subprocess.Popen(command, env=environment, stdout=log, stderr=log,
                cwd=Path(os.environ['SystemRoot'])/'System32' if args.direct else None,
                creationflags=subprocess.CREATE_NO_WINDOW)
            host = None
            try:
                host = wait(lambda: next((w for w in windows() if w not in before and text(w).startswith('MM-AIR')), None),
                            'MM-Air window did not open')
                wait(lambda: any(text(w).startswith('Resident BF16 language') for w in windows(host)),
                     'Installed 4B model was unavailable')
                click('Prompt')
                wait(lambda: user.IsWindowVisible(button('Run Qwen')), 'Prompt Lab page did not open')
                run = button('Run Qwen')
                wait(lambda: user.IsWindowEnabled(run), 'Installed 4B model was unavailable')
                editor = next(w for w in windows(host) if kind(w)=='Edit' and text(w)=='Expand this into a cinematic H3 prompt.')
                output_editor = next(w for w in windows(host) if kind(w)=='Edit' and text(w)=='Your current production-ready result will appear here.')

                def new_session():
                    click('New session')
                    wait(lambda: text(editor)=='', 'New session did not clear the instruction')

                def infer(instruction):
                    replace(editor, instruction)
                    started = time.monotonic()
                    click('Run Qwen')
                    wait(lambda: user.IsWindowEnabled(button('Cancel')) and not user.IsWindowEnabled(run), 'Request did not start')
                    wait(lambda: user.IsWindowEnabled(run), 'Prompt inference timed out', 1200)
                    labels = [text(w) for w in windows(host)]
                    assert 'Unloaded' in labels, labels
                    metrics = next((s for s in labels if ' in · ' in s and ' out · peak ' in s), None)
                    assert metrics, labels
                    return {'response': text(output_editor), 'metrics': metrics,
                            'elapsed_seconds': time.monotonic()-started, 'fully_unloaded': True}

                new_session()
                result['text'] = infer('Reply with exactly one word: READY')
                assert result['text']['response'].strip() == 'READY', result['text']
                history = json.loads((output/'prompt-history/latest.json').read_text(encoding='utf-8'))
                assert 'READY' in json.dumps(history)
                result['history_document'] = history
                click('Save to History')
                preserved = wait(lambda: list((output/'prompt-history').glob('prompt-*.json')), 'History was not saved')
                result['history_saved'] = len(preserved)
                click('Send to Generate')
                wait(lambda: not user.IsWindowVisible(run) and any(kind(w)=='Edit' and text(w)=='READY' and user.IsWindowVisible(w) for w in windows(host)),
                     'Prompt result did not route to Generate')
                result['routed_to_generate'] = True
                click('Prompt')
                new_session()
                replace(editor, 'Write a long detailed description of a sailing boat.')
                click('Run Qwen')
                wait(lambda: user.IsWindowEnabled(button('Cancel')), 'Cancellation request did not start')
                click('Cancel')
                wait(lambda: user.IsWindowEnabled(run), 'Cancellation did not finish', 120)
                labels = [text(w) for w in windows(host)]
                assert any('cancelled' in s.lower() for s in labels), labels
                assert 'Unloaded · request failed' in labels
                assert not list(Path(temporary).parent.glob('mm-air-prompt-cancel-*.signal')), 'Cancellation signal leaked'
                result['cancelled_and_unloaded'] = True
                if args.image:
                    new_session()
                    click('＋ Image / video')
                    picker = wait(lambda: next((w for w in windows() if text(w)=='Add ordered image or video references'), None),
                                  'Native image picker did not open')
                    filename = wait(lambda: next((w for w in windows(picker) if kind(w)=='Edit'), None), 'Picker filename field missing')
                    replace(filename, str(args.image.resolve()))
                    user.PostMessageW(picker, 0x111, 1, 0)
                    wait(lambda: not user.IsWindow(picker), 'Image picker did not close')
                    wait(lambda: any(args.image.name in text(w) for w in windows(host)), 'Image reference did not attach')
                    result['image'] = infer('Identify the central subject in the picture. Answer in one short sentence.')
                    assert result['image']['response'].strip()
                    result['image']['source'] = str(args.image.resolve())
                user.PostMessageW(host, 0x10, 0, 0)
                assert process.wait(30)==0
                result['clean_shutdown'] = True
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait()
                log.seek(0)
                full_log = log.read()
                args.receipt.with_suffix('.log').write_text(full_log, encoding='utf-8')
                args.receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
