"""Exercise shared Settings persistence and theme rendering in native Windows.

Developer-only harness. Uses isolated user data; does not change user preferences.
"""
import argparse
import ctypes as C
from ctypes import wintypes as W
from contextlib import ExitStack
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("application", type=Path)
    parser.add_argument("adapter", type=Path)
    parser.add_argument("--runtime-directory", type=Path)
    parser.add_argument("--capture-script", type=Path)
    parser.add_argument("--screenshot", type=Path)
    args = parser.parse_args()
    user = C.WinDLL("user32", use_last_error=True)
    gdi = C.WinDLL("gdi32", use_last_error=True)
    user.SetProcessDPIAware()
    user.SendMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
    user.SendMessageW.restype = W.LPARAM
    user.GetParent.argtypes = [W.HWND]
    user.GetParent.restype = W.HWND
    user.GetWindow.argtypes = [W.HWND, W.UINT]
    user.GetWindow.restype = W.HWND
    callback = C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)

    def text(window):
        buffer = C.create_unicode_buffer(8192)
        user.SendMessageW(window, 0xD, len(buffer), C.cast(buffer, C.c_void_p).value)
        return buffer.value

    def kind(window):
        buffer = C.create_unicode_buffer(128)
        user.GetClassNameW(window, buffer, len(buffer))
        return buffer.value

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

    def wait(predicate, message):
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            value = predicate()
            if value:
                return value
            time.sleep(.05)
        raise AssertionError(message)

    def replace(editor, value):
        buffer = C.create_unicode_buffer(value)
        user.SendMessageW(editor, 0xB1, 0, -1)
        user.SendMessageW(editor, 0xC2, 1, C.cast(buffer, C.c_void_p).value)

    source = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="mm-air-settings-") as temporary:
        root = Path(temporary)
        prefs = root / "data/mm-air/runtime.json"
        prefs.parent.mkdir(parents=True)
        base = str(root / "H3 日本語")
        output = str(root / "Output λ")
        saved = {"schema": "mm-air.runtime.v1", "MM_AIR_H3_CHECKPOINT_ROOT": "initial-base",
                 "MM_AIR_H3_REFERENCE_ROOT": "initial-reference", "MM_AIR_H3_DONOR_ROOT": "initial-donor",
                 "MM_AIR_H3_MANIFEST_ROOT": "initial-manifests", "MM_AIR_OUTPUT_ROOT": str(root / "old-output"),
                 "MM_AIR_THEME": "0", "MM_AIR_ACCENT_COLOR": "#0066AA", "future": {"preserved": True}}
        model_keys = ['QWEN_IMAGE21_ROOT', 'QWEN_IMAGE21_MANIFEST_DIR', 'MM_AIR_KREA_MODEL',
                      'MM_AIR_KREA_QWEN_INDEX', 'MM_AIR_KREA_TOKENIZER_DIR', 'MM_AIR_KREA_VAE',
                      'MM_AIR_KREA_VAE_CONFIG', 'MM_AIR_KREA_MANIFEST_ROOT',
                      'AIR_QWEN3_VL_4B_DIR', 'AIR_QWEN3_VL_8B_DIR', 'AIR_QWEN3_VL_32B_DIR',
                      'MM_AIR_PROMPT_MANIFEST_ROOT', 'MM_AIR_SEEDVR2_DIT',
                      'MM_AIR_SEEDVR2_7B_DIT', 'MM_AIR_SEEDVR2_VAE',
                      'MM_AIR_SEEDVR2_MANIFEST_ROOT', 'MM_AIR_SEEDVR2_7B_MANIFEST_ROOT']
        changed_models = {key: str(root / ('Models 日本語 ' + str(index))) for index, key in enumerate(model_keys)}
        saved.update({key: 'initial-model-' + str(index) for index, key in enumerate(model_keys)})
        prefs.write_text(json.dumps(saved), encoding="utf-8")
        environment = os.environ.copy()
        for name in tuple(environment):
            if name.startswith(("MM_AIR_", "AIR_QWEN3_VL_")):
                del environment[name]
        environment["XDG_DATA_HOME"] = str(root / "data")
        if args.runtime_directory:
            environment["PATH"] = str(args.runtime_directory.resolve()) + os.pathsep + environment["PATH"]
        for reopened in (False, True):
            before = set(windows())
            with ExitStack() as cleanup, (root / "log").open("w+", encoding="utf-8") as log:
                process = subprocess.Popen([str(args.application.resolve()), str(source / "desktop.ui"),
                    str(source / "desktop.css"), str(args.adapter.resolve())], env=environment,
                    stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
                def stop():
                    if process.poll() is None:
                        process.terminate()
                        process.wait()
                cleanup.callback(stop)
                host = wait(lambda: next((w for w in windows() if w not in before and text(w).startswith("MM-AIR")), None), "MM-Air window did not open")
                controls = wait(lambda: windows(host) if any(text(w) == (base if reopened else "initial-base") for w in windows(host)) else None,
                                "Settings did not load")
                nav = next(w for w in controls if kind(w) == "Button" and text(w) == "Settings")
                user.SendMessageW(nav, 0xF5, 0, 0)
                wait(lambda: any(text(w) == "Settings ready" for w in controls), "Settings navigation did not open the page")
                editor = next(w for w in controls if text(w) == (base if reopened else "initial-base"))
                wait(lambda: user.IsWindowVisible(editor), "Settings fields are not visible")
                out_editor = next(w for w in controls if text(w) == (output if reopened else saved["MM_AIR_OUTPUT_ROOT"]))
                accent = next(w for w in controls if text(w) == ("#9F55AA" if reopened else "#0066AA"))
                themes = next(w for w in controls if kind(w) == "ListBox" and user.SendMessageW(w, 0x18B, 0, 0) == 7)
                save = next(w for w in controls if kind(w) == "Button" and text(w) == "Save and Apply")
                model_editors = {key: next(w for w in controls if text(w)==(changed_models[key] if reopened else saved[key])) for key in model_keys}
                dimensions = [('Side panel width (px)', 'MM_AIR_PANEL_WIDTH', 260),
                              ('Navigation width (px)', 'MM_AIR_NAV_WIDTH', 72),
                              ('Navigation tab height (px)', 'MM_AIR_NAV_HEIGHT', 40)]
                dimension_editors = {key: user.GetWindow(next(w for w in controls if text(w)==label), 2)
                                     for label, key, value in dimensions}
                if reopened:
                    assert user.SendMessageW(themes, 0x188, 0, 0) == 3, "Theme choice was not restored"
                    for label, key, value in dimensions:
                        assert text(dimension_editors[key]) == str(value), key
                else:
                    browse = next(w for w in controls if kind(w) == "Button" and text(w) == "Browse…")
                    user.SendMessageW(browse, 0xF5, 0, 0)
                    picker = wait(lambda: next((w for w in windows() if text(w) == "Choose MM-Air folder"), None), "Native folder picker did not open")
                    user.PostMessageW(picker, 0x10, 0, 0)
                    wait(lambda: not user.IsWindow(picker), "Folder picker did not close")
                    assert text(editor) == "initial-base", "Cancelling the picker changed the saved path"
                    file_parent = user.GetParent(model_editors['MM_AIR_KREA_MODEL'])
                    file_browse = next(w for w in controls if user.GetParent(w)==file_parent and text(w)=='Browse…')
                    user.SendMessageW(file_browse, 0xF5, 0, 0)
                    picker = wait(lambda: next((w for w in windows() if text(w)=='Choose MM-Air model file'), None), 'Native model file picker did not open')
                    user.PostMessageW(picker, 0x10, 0, 0)
                    wait(lambda: not user.IsWindow(picker), 'Model file picker did not close')
                    for key, control in model_editors.items():
                        replace(control, changed_models[key])
                    replace(editor, base)
                    replace(out_editor, output)
                    replace(accent, "#9F55AA")
                    for label, key, value in dimensions:
                        replace(dimension_editors[key], str(value))
                    user.SendMessageW(themes, 0x186, 3, 0)
                    user.SendMessageW(user.GetParent(themes), 0x111, 1 << 16, themes)
                    user.SendMessageW(save, 0xF5, 0, 0)
                    def persisted():
                        value = json.loads(prefs.read_text(encoding="utf-8"))
                        return value if value.get("MM_AIR_H3_CHECKPOINT_ROOT") == base and value.get("MM_AIR_THEME") == "3" else None
                    result = wait(persisted, "Save and Apply did not persist settings")
                    assert result["MM_AIR_OUTPUT_ROOT"] == output
                    assert result["MM_AIR_ACCENT_COLOR"] == "#9F55AA"
                    assert result["future"] == {"preserved": True}
                    for key, value in changed_models.items():
                        assert result[key]==value, (key, result[key], value)
                    for label, key, value in dimensions:
                        assert result[key] == str(value), (key, result[key])
                wait(lambda: any(text(w).startswith("Saved and applied") for w in controls) if not reopened else True, "Apply did not complete")
                if args.capture_script and args.screenshot:
                    import runpy
                    pid = W.DWORD()
                    user.GetWindowThreadProcessId(host, C.byref(pid))
                    runpy.run_path(str(args.capture_script))["capture"](pid.value, str(args.screenshot))
                # Sample the rendered native EDIT background after applying Nord.
                user.GetDC.argtypes = [W.HWND]
                user.GetDC.restype = W.HDC
                user.ReleaseDC.argtypes = [W.HWND, W.HDC]
                gdi.CreateCompatibleDC.argtypes = [W.HDC]
                gdi.CreateCompatibleDC.restype = W.HDC
                gdi.CreateCompatibleBitmap.argtypes = [W.HDC, C.c_int, C.c_int]
                gdi.CreateCompatibleBitmap.restype = W.HBITMAP
                gdi.SelectObject.argtypes = [W.HDC, W.HANDLE]
                gdi.SelectObject.restype = W.HANDLE
                gdi.GetPixel.argtypes = [W.HDC, C.c_int, C.c_int]
                gdi.GetPixel.restype = W.DWORD
                gdi.DeleteObject.argtypes = [W.HANDLE]
                gdi.DeleteDC.argtypes = [W.HDC]
                user.PrintWindow.argtypes = [W.HWND, W.HDC, W.UINT]
                rectangle = W.RECT()
                user.GetClientRect(editor, C.byref(rectangle))
                screen = user.GetDC(editor)
                dc = gdi.CreateCompatibleDC(screen)
                bitmap = gdi.CreateCompatibleBitmap(screen, rectangle.right, rectangle.bottom)
                old = gdi.SelectObject(dc, bitmap)
                assert user.PrintWindow(editor, dc, 2), (rectangle.right, rectangle.bottom, C.get_last_error())
                color = gdi.GetPixel(dc, rectangle.right-8, rectangle.bottom//2)
                gdi.SelectObject(dc, old)
                gdi.DeleteObject(bitmap)
                gdi.DeleteDC(dc)
                user.ReleaseDC(editor, screen)
                assert color == 0x332B29, f"Saved Nord theme did not render: {color:#x}"
                replace(accent, "invalid-color")
                user.SendMessageW(save, 0xF5, 0, 0)
                wait(lambda: any(text(w).startswith("Accent color must") for w in controls), "Invalid color was not refused")
                assert json.loads(prefs.read_text(encoding="utf-8"))["MM_AIR_ACCENT_COLOR"] == "#9F55AA"
                # Fixed side panels retain their chosen width as the canvas grows.
                edit_nav = next(w for w in controls if kind(w)=='Button' and text(w)=='Edit')
                user.SendMessageW(edit_nav, 0xF5, 0, 0)
                source_button = next(w for w in controls if text(w)=='＋ Source image or video')
                wait(lambda: user.IsWindowVisible(source_button), 'Edit workspace did not open')
                left = user.GetParent(user.GetParent(source_button))
                edit_prompt = next(w for w in controls if kind(w)=='Edit' and text(w)=='Replace the main character with the character shown in the reference image. Preserve the source action, camera, lighting, environment, timing, and audio.')
                right = user.GetParent(user.GetParent(user.GetParent(edit_prompt)))
                def size(window):
                    bounds = W.RECT()
                    user.GetWindowRect(window, C.byref(bounds))
                    return bounds.right-bounds.left, bounds.bottom-bounds.top
                wait(lambda: size(left)[0]==260 and size(right)[0]==260, 'Edit side panels stretched across the canvas')
                assert size(edit_nav)[0] in (71, 72) and size(edit_nav)[1] == 40, ('Navigation size', size(edit_nav))
                user.SetWindowPos(host, None, 0, 0, 1800, 1000, 0x16)
                wait(lambda: size(left)[0]==260 and size(right)[0]==260, 'Resizing expanded the fixed Edit side panels')
                user.PostMessageW(host, 0x10, 0, 0)
                assert process.wait(20) == 0
                log.seek(0)
                output_log = log.read()
                assert "Unknown widget" not in output_log and "Unsupported desktop operation" not in output_log, output_log
    print("Shared Settings: native pickers, Unicode model paths, saved appearance and layout, fixed Edit side panels on resize, compact navigation, invalid color refusal and restart persistence passed.")


if __name__ == "__main__":
    main()
