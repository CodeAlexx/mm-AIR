"""Drive native Edit source/mask pickers and real crop preparation without GPU inference."""
import argparse
import ctypes as C
from ctypes import wintypes as W
import hashlib
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
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--installed', action='store_true',
                        help='Launch with no arguments from System32 using the system PATH')
    args = parser.parse_args()
    user = C.WinDLL('user32', use_last_error=True)
    user.SetProcessDPIAware()
    user.SendMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
    user.SendMessageW.restype = W.LPARAM
    user.PostMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
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

    def kind(window):
        value = C.create_unicode_buffer(128)
        user.GetClassNameW(window, value, len(value))
        return value.value

    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))

    def png(path, gray=False):
        width, height = 320, 256
        rows = bytearray()
        for y in range(height):
            rows.append(0)
            if gray:
                rows.extend(255 if 96 <= x < 224 and 32 <= y < 224 else 0 for x in range(width))
            else:
                rows.extend(bytes((20, 150, 90)) * width)
        path.write_bytes(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 0 if gray else 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b''))

    environment = os.environ.copy()
    windows_root = os.environ['SystemRoot']
    for key in tuple(environment):
        if key.startswith(('MM_AIR_', 'AIR_QWEN3_VL_')):
            del environment[key]
    environment['PATH'] = str(args.adapter.resolve().parent) + os.pathsep + (
        os.path.join(windows_root, 'System32') + os.pathsep + windows_root
        if args.installed else environment['PATH'])
    source_layout = Path(__file__).resolve().parents[1]
    result = {'application_sha256': hashlib.sha256(args.application.read_bytes()).hexdigest(),
              'native_edit_crop_preparation': [], 'inference_started': False,
              'no_argument_launch': args.installed, 'system_only_path': args.installed}
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='mm-air-edit-') as temporary:
        root = Path(temporary)
        media = root/'Media 日本語 with spaces'
        media.mkdir()
        still, mask, video = media/'source.png', media/'mask.png', media/'source.mp4'
        png(still)
        png(mask, gray=True)
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-y', '-loop', '1', '-i', str(still),
                        '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=32000', '-frames:v', '4',
                        '-r', '24', '-shortest', '-pix_fmt', 'yuv420p', '-c:v', 'libx264', '-c:a', 'aac',
                        str(video)], env=environment, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
        environment.update({'XDG_DATA_HOME': str(root/'data'), 'TMPDIR': str(media),
                            'MM_AIR_OUTPUT_ROOT': str(root/'output')})
        before = set(windows())
        with (root/'log').open('w+', encoding='utf-8') as log:
            command = [str(args.application.resolve())]
            if not args.installed:
                command.extend([str(source_layout/'desktop.ui'), str(source_layout/'desktop.css'),
                                str(args.adapter.resolve())])
            process = subprocess.Popen(command, env=environment,
                cwd=os.path.join(windows_root, 'System32') if args.installed else None,
                stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
            def wait(predicate, reason):
                deadline = time.monotonic() + 45
                while time.monotonic() < deadline:
                    assert process.poll() is None, 'Application exited before ' + reason
                    value = predicate()
                    if value:
                        return value
                    time.sleep(.05)
                raise AssertionError(reason)
            try:
                host = wait(lambda: next((w for w in windows() if w not in before and text(w).startswith('MM-AIR')), None), 'Native window did not open')
                def labels():
                    return [text(w) for w in windows(host)]
                def click(label):
                    button = wait(lambda: next((w for w in windows(host) if kind(w)=='Button' and text(w)==label and user.IsWindowVisible(w)), None), label + ' is unavailable')
                    user.SendMessageW(button, 0xF5, 0, 0)
                def pick(button, title, filename):
                    click(button)
                    picker = wait(lambda: next((w for w in windows() if text(w)==title), None), title + ' did not open')
                    editor = wait(lambda: next((w for w in windows(picker) if kind(w)=='Edit'), None), 'Filename field missing')
                    value = C.create_unicode_buffer(str(filename))
                    user.SendMessageW(editor, 0xC, 0, C.cast(value, C.c_void_p).value)
                    user.PostMessageW(picker, 0x111, 1, 0)
                    wait(lambda: not user.IsWindow(picker), 'Picker did not close')
                    wait(lambda: filename.name in labels(), 'Selected media did not load')
                time.sleep(.5)
                click('Edit')
                mode = wait(lambda: next((w for w in windows(host)
                    if kind(w) == 'ComboBox' and user.IsWindowVisible(w)
                    and text(w) == 'Character Replace · no mask'), None), 'Edit mode missing')
                user.SendMessageW(mode, 0x14E, 4, 0)  # Prompt-guided Local Edit
                user.SendMessageW(user.GetParent(mode), 0x111, 1 << 16, mode)
                wait(lambda: text(mode) == 'Prompt-guided Local Edit', 'Localized mode not selected')
                for source, frames in [(still, 22), (video, 4)]:
                    pick('＋ Source image or video', 'Choose Edit source image or video', source)
                    pick('＋ Imported mask image or video', 'Choose authored mask image or video', mask)
                    wait(lambda: 'Imported mask ready for cleanup and crop planning' in labels(), 'Imported mask did not become ready')
                    click('Preview Crop')
                    wait(lambda: 'Tracked crop prepared from the cleaned authored mask' in labels(), 'Crop preparation failed')
                    description = next(s for s in labels() if 'H3 working crop' in s and 'conditioning' in s)
                    assert f'conditioning 22 / delivery {frames} frames' in description, description
                    result['native_edit_crop_preparation'].append({'source_type': source.suffix, 'description': description,
                        'unicode_space_paths': True, 'native_temp_root': True})
                user.PostMessageW(host, 0x10, 0, 0)
                assert process.wait(30) == 0
                result['clean_shutdown'] = True
            except Exception:
                if 'host' in locals() and user.IsWindow(host):
                    result['visible_labels_at_failure'] = [text(w) for w in windows(host) if user.IsWindowVisible(w) and text(w)]
                raise
            finally:
                if process.poll() is None:
                    process.terminate()
                    process.wait(30)
                log.seek(0)
                args.receipt.with_suffix('.log').write_text(log.read(), encoding='utf-8')
                args.receipt.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
