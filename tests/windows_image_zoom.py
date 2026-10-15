"""Exercise image zoom in the real shared controller with isolated user data.

python windows_image_zoom.py APP.exe air-ui.exe --runtime-directory DIR
"""
import argparse
import ctypes as C
from ctypes import wintypes as W
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import time
import zlib


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('application', type=Path)
    parser.add_argument('adapter', type=Path)
    parser.add_argument('--runtime-directory', type=Path)
    args = parser.parse_args()
    user, gdi = C.WinDLL('user32'), C.WinDLL('gdi32')
    user.SetProcessDPIAware()
    user.SendMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
    user.SendMessageW.restype = W.LPARAM
    user.PostMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
    user.GetClientRect.argtypes = [W.HWND, C.POINTER(W.RECT)]
    user.IsWindowVisible.argtypes = [W.HWND]
    user.GetDC.argtypes, user.GetDC.restype = [W.HWND], W.HDC
    user.ReleaseDC.argtypes = [W.HWND, W.HDC]
    gdi.GetPixel.argtypes, gdi.GetPixel.restype = [W.HDC, C.c_int, C.c_int], W.DWORD
    callback = C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)

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

    def text(window):
        value = C.create_unicode_buffer(8192)
        user.SendMessageW(window, 0xD, len(value), C.cast(value, C.c_void_p).value)
        return value.value

    def size(window):
        value = W.RECT()
        user.GetClientRect(window, C.byref(value))
        return value.right, value.bottom

    def until(predicate, label):
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            assert process.poll() is None, 'Controller exited: ' + log_path.read_text(encoding='utf-8')
            value = predicate()
            if value:
                return value
            time.sleep(.05)
        raise AssertionError(label + ': ' + log_path.read_text(encoding='utf-8'))

    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))

    app_directory = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='mm-air-zoom-') as temporary:
        root = Path(temporary)
        image = root / 'preview-\u65e5\u672c\u8a9e.png'
        rgb = bytes((189, 48, 149))
        image.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 640, 360, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress((b'\x00' + rgb * 640) * 360)) + chunk(b'IEND', b''))
        sidecar = Path(str(image) + '.json')
        sidecar.write_text('{}', encoding='utf-8')
        catalog = root / 'data/mm-air/generate-history.json'
        catalog.parent.mkdir(parents=True)
        catalog.write_text(json.dumps(dict(schema='mm-air.generate.history', version=2, items=[dict(path=str(image), thumbnail=str(image), parameters=str(sidecar), postprocess='')])), encoding='utf-8')
        environment = os.environ.copy()
        environment['XDG_DATA_HOME'] = str(root / 'data')
        environment['MM_AIR_OUTPUT_ROOT'] = str(root / 'output')
        if args.runtime_directory:
            environment['PATH'] = str(args.runtime_directory.resolve()) + os.pathsep + environment['PATH']
        before = set(windows())
        log_path = root / 'log'
        host = None
        with log_path.open('w+', encoding='utf-8') as log:
            process = subprocess.Popen([str(args.application.resolve()), str(app_directory / 'desktop.ui'), str(app_directory / 'desktop.css'), str(args.adapter.resolve())], env=environment, stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
            try:
                host = until(lambda: next((w for w in windows() if w not in before and text(w).startswith('MM-AIR')), None), 'No native window')
                controls = windows(host)
                user.GetClassNameW.argtypes = [W.HWND, W.LPWSTR, C.c_int]
                def kind(window):
                    value = C.create_unicode_buffer(128)
                    user.GetClassNameW(window, value, len(value))
                    return value.value
                history = until(lambda: next((w for w in controls if kind(w) == 'SysListView32' and user.SendMessageW(w, 0x1004, 0, 0) == 1), None), 'No fixture gallery')
                back = next(w for w in controls if kind(w) == 'Button' and text(w) == 'Back')
                prompt = next(w for w in controls if kind(w) == 'Edit' and text(w).startswith('Describe'))
                time.sleep(.4)  # Let the startup snapshot finish before typing the draft.
                draft = 'Keep this unsaved prompt while viewing the image. \u03bb'
                draft_buffer = C.create_unicode_buffer(draft)
                user.SendMessageW(prompt, 0xC, 0, C.cast(draft_buffer, C.c_void_p).value)
                user.SendMessageW(history, 0x100, 0x24, 0)  # Home selects the fixture.
                def visible_picture():
                    for window in controls:
                        if not user.IsWindowVisible(window) or kind(window) != 'AIRDesktopContainer' or windows(window):
                            continue
                        width, height = size(window)
                        if width < 100 or height < 100:
                            continue
                        dc = user.GetDC(window)
                        try:
                            pixel = gdi.GetPixel(dc, width // 2, height // 2)
                        finally:
                            user.ReleaseDC(window, dc)
                        if pixel == 189 | (48 << 8) | (149 << 16):
                            return window
                preview = until(visible_picture, 'Image preview was not painted')
                def double(window):
                    width, height = size(window)
                    point = (height // 2 << 16) | width // 2
                    for message, buttons in ((0x201, 1), (0x202, 0), (0x203, 1), (0x202, 0)):
                        user.SendMessageW(window, message, buttons, point)
                # A single click must leave the normal workspace visible.
                user.SendMessageW(preview, 0x201, 1, 0)
                user.SendMessageW(preview, 0x202, 0, 0)
                time.sleep(.3)
                assert not user.IsWindowVisible(back), 'Single click opened zoom'
                double(preview)
                until(lambda: user.IsWindowVisible(back), 'Double-click did not open zoom')
                expanded = until(visible_picture, 'Expanded image was not painted')
                width, height = size(expanded)
                client_width, client_height = size(host)
                assert width >= client_width - 40 and height >= client_height - 130, (size(expanded), size(host))
                assert not user.IsWindowVisible(history), 'Gallery stayed on the full image page'
                user.PostMessageW(back, 0x100, 0x1B, 0)  # Real message-loop Escape shortcut.
                until(lambda: user.IsWindowVisible(history) and not user.IsWindowVisible(back), 'Escape did not return')
                assert text(prompt) == draft, ('Zoom changed the unsaved prompt', text(prompt), draft)
                double(preview)
                until(lambda: user.IsWindowVisible(back), 'Could not reopen zoom')
                user.SendMessageW(back, 0xF5, 0, 0)
                until(lambda: user.IsWindowVisible(history), 'Back did not return')
                double(preview)
                until(lambda: user.IsWindowVisible(back), 'Could not reopen for double-click close')
                expanded = until(visible_picture, 'Missing reopened image')
                double(expanded)
                until(lambda: user.IsWindowVisible(history), 'Expanded double-click did not return')
                # Let the native gallery produce its activation notification.
                user.PostMessageW(history, 0x100, 0x24, 0)  # Home
                user.PostMessageW(history, 0x100, 0x0D, 0)  # Return
                until(lambda: user.IsWindowVisible(back), 'History activation did not open zoom')
                user.SendMessageW(back, 0xF5, 0, 0)
                until(lambda: user.IsWindowVisible(history), 'History zoom did not return')
                assert text(prompt) == draft
                user.PostMessageW(host, 0x10, 0, 0)
                assert process.wait(30) == 0
                transcript = log_path.read_text(encoding='utf-8')
                assert 'Unsupported desktop operation' not in transcript and 'Unknown widget' not in transcript, transcript
                print('Native shared UI: preview double-click/gallery activation, full-page image pixels, Escape/Back/double-click return, unsaved prompt preservation and clean shutdown PASS')
            finally:
                if process.poll() is None:
                    if host:
                        user.PostMessageW(host, 0x10, 0, 0)
                    try:
                        process.wait(10)
                    except subprocess.TimeoutExpired:
                        process.terminate()
                        process.wait()


if __name__ == '__main__':
    main()
