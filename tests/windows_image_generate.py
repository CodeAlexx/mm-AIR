"""Run real image generation through the shared native MM-Air UI.

Model configuration is inherited from the caller. User data is isolated.
Usage: python windows_image_generate.py APP UI PARAMETERS --runtime-directory DIR
"""
import argparse
import ctypes as C
from ctypes import wintypes as W
import hashlib
import json
import os
import shutil
from pathlib import Path
import subprocess
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('application', type=Path)
    parser.add_argument('adapter', type=Path)
    parser.add_argument('parameters', type=Path)
    parser.add_argument('--runtime-directory', type=Path)
    parser.add_argument('--direct', action='store_true',
                        help='Launch without arguments from System32 and restore parameters through runtime configuration')
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args()
    request = json.loads(args.parameters.read_text(encoding='utf-8'))
    output = Path(request['output'])
    assert not output.exists(), 'Choose a fresh output path'
    editing = request.get('mode')=='edit'
    button_label = 'Generate Edit' if editing else {'krea2-turbo': 'Generate Krea PNG', 'qwen-image-2.1': 'Generate Qwen PNG'}[request['model']]
    restored = 'Qwen Image Edit parameters restored' if editing else {'krea2-turbo': 'Krea Generate parameters restored', 'qwen-image-2.1': 'Qwen Generate parameters restored'}[request['model']]
    user = C.WinDLL('user32', use_last_error=True)
    user.SetProcessDPIAware()
    user.SendMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
    user.SendMessageW.restype = W.LPARAM
    user.PostMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
    user.IsWindowEnabled.argtypes = [W.HWND]
    user.IsWindowVisible.argtypes = [W.HWND]
    user.GetClassNameW.argtypes = [W.HWND, W.LPWSTR, C.c_int]
    callback = C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
    def text(window):
        value = C.create_unicode_buffer(8192)
        user.SendMessageW(window, 0xD, len(value), C.cast(value, C.c_void_p).value)
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
    def kind(window):
        value = C.create_unicode_buffer(128)
        user.GetClassNameW(window, value, len(value))
        return value.value
    environment = os.environ.copy()
    environment['MM_AIR_UI_HOST'] = str(args.adapter.resolve())
    if args.direct:
        environment['MM_AIR_PARAMETERS_FILE'] = str(args.parameters.resolve())
    if args.runtime_directory:
        environment['PATH'] = str(args.runtime_directory.resolve()) + os.pathsep + environment['PATH']
    before = set(windows())
    host = None
    with tempfile.TemporaryDirectory(prefix='mm-air-image-') as temporary:
        environment['XDG_DATA_HOME'] = str(Path(temporary)/'data')
        environment['MM_AIR_OUTPUT_ROOT'] = str(Path(temporary)/'output')
        with (Path(temporary)/'log').open('w+', encoding='utf-8') as log:
            command = [str(args.application.resolve())]
            if not args.direct:
                command += ['--parameters', str(args.parameters.resolve())]
            host = None
            process = subprocess.Popen(command, cwd=Path(os.environ['SystemRoot'])/'System32' if args.direct else None,
                env=environment, stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                deadline = time.monotonic()+30
                while time.monotonic()<deadline:
                    assert process.poll() is None, 'Controller exited at startup'
                    candidates = [w for w in windows() if w not in before and text(w).startswith('MM-AIR')]
                    if candidates:
                        host = candidates[0]
                        controls = windows(host)
                        if any(text(w)==restored for w in controls):
                            break
                    time.sleep(.1)
                else:
                    raise AssertionError('Image parameters did not restore')
                button = next(w for w in controls if text(w)==button_label)
                if request['model']=='krea2-turbo' and (request['width'],request['height'])!=(1024,1024):
                    assert any(kind(w)=='ComboBox' and text(w)=='Custom' and
                               user.IsWindowVisible(w) and user.SendMessageW(w,0x146,0,0)==2
                               for w in controls), 'Custom Krea resolution is mislabeled'
                    expected_geometry=f"{request['width']} × {request['height']}"
                    assert any(text(w)==expected_geometry and user.IsWindowVisible(w)
                               for w in controls), 'Custom dimensions are not shown'
                lock = next(w for w in controls if text(w)=='Lock' and user.IsWindowVisible(w))
                if user.SendMessageW(lock, 0xF0, 0, 0)!=1:  # BM_GETCHECK
                    user.SendMessageW(lock, 0xF5, 0, 0)
                started = time.monotonic()
                user.SendMessageW(button, 0xF5, 0, 0)
                print(f'Shared {button_label} activated; controller PID {process.pid}', flush=True)
                time.sleep(1)
                while time.monotonic()-started<1200:
                    assert process.poll() is None, 'Controller exited during generation'
                    if user.IsWindowEnabled(button):
                        folder = 'krea' if request['model']=='krea2-turbo' else ('qwen-image-2.1/edit' if editing else 'qwen-image-2.1/generate')
                        generated = list((Path(temporary)/'output'/folder).glob('*.png'))
                        assert len(generated)==1, [text(w) for w in windows(host)]
                        actual = json.loads(Path(str(generated[0])+'.json').read_text(encoding='utf-8'))
                        for key in ('model', 'prompt', 'seed', 'width', 'height', 'steps'):
                            assert actual[key]==request[key], (key, actual[key], request[key])
                        if editing:
                            assert actual['mode']=='edit'
                            assert Path(actual['source']).resolve()==Path(request['source']).resolve()
                            assert [Path(value).resolve() for value in actual['references']]==[Path(value).resolve() for value in request['references']]
                        output.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(generated[0], output)
                        break
                    time.sleep(.5)
                else:
                    raise AssertionError('Generation did not finish')
                from PIL import Image, ImageStat
                with Image.open(output) as image:
                    assert image.size==(request['width'], request['height'])
                    deviation=ImageStat.Stat(image.convert('RGB')).stddev
                    assert min(deviation)>1, 'Generated image is flat'
                user.PostMessageW(host, 0x10, 0, 0)
                assert process.wait(30)==0, 'Controller did not close cleanly'
                log.seek(0)
                transcript=log.read()
                assert 'Unsupported desktop operation' not in transcript, transcript
                receipt=dict(native_windows=True, shared_controller=True, request=request, actual_parameters=actual,
                    automatic_output_folder=folder,
                    application_sha256=hashlib.sha256(args.application.read_bytes()).hexdigest(),
                    adapter_sha256=hashlib.sha256(args.adapter.read_bytes()).hexdigest(),
                    direct_launch=args.direct,
                    working_directory=str(Path(os.environ['SystemRoot'])/'System32') if args.direct else str(Path.cwd()),
                    runtime_directory_override=bool(args.runtime_directory),
                    elapsed_seconds=time.monotonic()-started, sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                    rgb_stddev=deviation, clean_shutdown=True)
                args.receipt.write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
                args.receipt.with_suffix('.log').write_text(transcript, encoding='utf-8')
                print(json.dumps(receipt), flush=True)
            except Exception:
                # Temporary user-data isolation must not erase the evidence of
                # a failed real generation when the harness tears down.
                log.flush()
                log.seek(0)
                args.receipt.with_suffix('.log').write_text(log.read(), encoding='utf-8')
                raise
            finally:
                if process.poll() is None:
                    if host:
                        user.PostMessageW(host, 0x10, 0, 0)
                    try:
                        process.wait(30)
                    except subprocess.TimeoutExpired:
                        process.terminate()
                        process.wait()


if __name__=='__main__':
    main()
