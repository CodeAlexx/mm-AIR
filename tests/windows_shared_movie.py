"""Edit and reopen a real shared Movie project through the native Windows UI.

python apps/mm-air/tests/windows_shared_movie.py APP.exe air-ui.exe --runtime-directory DIR
Uses a temporary project library, never the user's current project or clipboard.
"""
import argparse
from contextlib import ExitStack
import ctypes as C
from ctypes import wintypes as W
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import struct
import zlib


def restore_fixture(source, payload, destination):
    """Verify and restore only a Recycle Bin entry identifying our owned fixture."""
    source = source.resolve()
    recycle = Path(source.drive + "/$Recycle.Bin")
    # Match the full NUL-terminated name: a media path prefixes its .json sidecar.
    original = str(source).encode("utf-16-le") + b"\x00\x00"
    for folder in recycle.iterdir():
        try:
            entries = list(folder.glob("$I*"))
        except PermissionError:
            continue
        for entry in entries:
            try:
                body = entry.read_bytes()
            except PermissionError:
                continue
            if original in body:
                recycled = entry.with_name("$R" + entry.name[2:])
                assert recycled.read_bytes() == payload, "Recycled fixture content changed"
                recycled.rename(destination)
                entry.unlink()
                return
    raise AssertionError("Deleted fixture is missing its Recycle Bin restoration record")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("application", type=Path)
    parser.add_argument("adapter", type=Path)
    parser.add_argument("--runtime-directory", type=Path)
    parser.add_argument("--trash", action="store_true", help="Verify project deletion reaches the Windows Recycle Bin")
    args = parser.parse_args()
    user = C.WinDLL("user32", use_last_error=True)
    user.SetProcessDPIAware()
    user.SendMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
    user.SendMessageW.restype = W.LPARAM
    user.PostMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
    callback_type = C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
    def text(window):
        value = C.create_unicode_buffer(8192)
        user.SendMessageW(window, 0xD, len(value), C.cast(value, C.c_void_p).value)
        return value.value
    def windows(parent=None):
        found = []
        @callback_type
        def collect(window, _):
            found.append(window)
            return True
        if parent:
            user.EnumChildWindows(parent, collect, 0)
        else:
            user.EnumWindows(collect, 0)
        return found
    sample = "A quiet winter clearing. Preserve character identity and the red cloak. \u65e5\u672c\u8a9e \u03bb"
    app_directory = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="mm-air-movie-\u03bb-test-") as temporary:
        environment = os.environ.copy()
        environment["MM_AIR_OUTPUT_ROOT"] = str(Path(temporary) / "output")
        environment["XDG_DATA_HOME"] = str(Path(temporary) / "data")
        if args.trash:
            def chunk(kind, body):
                return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))
            bitmap = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00\xff")) + chunk(b"IEND", b"")
            result = Path(temporary) / "result-\u65e5\u672c\u8a9e.png"
            result.write_bytes(bitmap)
            sidecar = result.with_suffix(".png.json")
            sidecar.write_bytes(b'{"owned_test_fixture":true}')
            catalog = Path(temporary) / "data/mm-air/generate-history.json"
            catalog.parent.mkdir(parents=True)
            catalog.write_text(json.dumps(dict(schema="mm-air.generate.history", version=2, items=[dict(path=str(result), thumbnail=str(result), parameters=str(sidecar), postprocess="")])), encoding="utf-8")
        if args.runtime_directory:
            environment["PATH"] = str(args.runtime_directory.resolve()) + os.pathsep + environment["PATH"]
        for reopening in (False, True):
            before = set(windows())
            with ExitStack() as cleanup, (Path(temporary) / "log").open("w+") as log:
                process = subprocess.Popen([str(args.application.resolve()), str(app_directory / "desktop.ui"), str(app_directory / "desktop.css"), str(args.adapter.resolve())], env=environment, stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
                def stop():
                    if process.poll() is None:
                        process.terminate()
                        process.wait()
                cleanup.callback(stop)
                deadline = time.monotonic() + 20
                editor = None
                while time.monotonic() < deadline:
                    assert process.poll() is None, "Shared controller exited"
                    candidates = [w for w in windows() if w not in before and text(w).startswith("MM-AIR")]
                    if candidates:
                        window = candidates[0]
                        controls = windows(window)
                        editors = [w for w in controls if text(w) == sample] if reopening else [w for w in controls if text(w).startswith("Describe the story, visual language")]
                        if editors:
                            editor = editors[0]
                            break
                    time.sleep(.1)
                assert editor, "Movie text was not loaded into the native editor"
                # Select the same policies in Generate that Movie must display/use.
                user.GetParent.argtypes = [W.HWND]
                user.GetParent.restype = W.HWND
                user.GetClassNameW.argtypes = [W.HWND, W.LPWSTR, C.c_int]
                def kind(handle):
                    value = C.create_unicode_buffer(128)
                    user.GetClassNameW(handle, value, len(value))
                    return value.value
                def choose(caption, index):
                    control = next(w for w in controls if kind(w) == "ComboBox" and text(w) == caption)
                    user.SendMessageW(control, 0x14E, index, 0)  # CB_SETCURSEL
                    user.SendMessageW(user.GetParent(control), 0x111, 1 << 16, control)  # CBN_SELCHANGE
                if args.trash and not reopening:
                    deadline = time.monotonic() + 10
                    while time.monotonic() < deadline:
                        galleries = [w for w in controls if kind(w)=="SysListView32" and user.SendMessageW(w, 0x1004, 0, 0)==1]
                        if galleries:
                            break
                        time.sleep(.05)
                    assert len(galleries)==1, "Fixture history gallery was not loaded"
                    user.SendMessageW(galleries[0], 0x100, 0x24, 0)  # Home selects the sole history tile.
                    trash = next(w for w in controls if kind(w)=="Button" and text(w)=="Trash")
                    deadline = time.monotonic() + 10
                    while time.monotonic() < deadline and not user.IsWindowEnabled(trash):
                        time.sleep(.05)
                    assert user.IsWindowEnabled(trash), "History selection did not enable Trash"
                    user.SendMessageW(trash, 0xF5, 0, 0)
                    deadline = time.monotonic() + 10
                    while time.monotonic() < deadline:
                        if not result.exists() and not sidecar.exists() and json.loads(catalog.read_text(encoding="utf-8"))["items"]==[]:
                            break
                        time.sleep(.05)
                    else:
                        raise AssertionError("Result Trash did not recycle media, sidecar and remove its history entry")
                    restore_fixture(result, bitmap, Path(temporary)/"restored-result.png")
                    restore_fixture(sidecar, b'{"owned_test_fixture":true}', Path(temporary)/"restored-sidecar.json")
                choose("CK INT8 · all evaluations", 1)
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    if any(text(w) == "Exact" for w in controls if kind(w) == "Static"):
                        break
                    time.sleep(.05)
                else:
                    raise AssertionError("Movie did not follow the Exact selection")
                choose("Exact attention", 4)
                choose("Euler simple · 19 evaluations", 3)
                choose("Exact BF16", 2)
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    labels = [text(w) for w in controls if kind(w) == "Static"]
                    if "CK INT8" in labels and "DC Euler · 19" in labels and labels.count("ConvRot INT8") >= 2:
                        break
                    time.sleep(.05)
                else:
                    raise AssertionError(dict(message="Movie policies did not follow Generate", labels=labels))
                movie = next(w for w in controls if text(w) == "Movie")
                user.SendMessageW(movie, 0xF5, 0, 0)
                deadline = time.monotonic() + 10
                while not user.IsWindowVisible(editor) and time.monotonic() < deadline:
                    time.sleep(.05)
                assert user.IsWindowVisible(editor), "Movie mode did not become visible"
                target_label = next(w for w in controls if text(w) == "Target seconds")
                endless_group = user.GetParent(target_label)
                endless_fields = [w for w in windows(endless_group)
                                  if user.GetParent(w) == endless_group and kind(w) == "Edit"]
                assert len(endless_fields) == 2, "Endless target and segment editors missing"
                geometry_label = next(w for w in controls if text(w) == "Duration (seconds)" and user.IsWindowVisible(w))
                geometry_group = user.GetParent(geometry_label)
                geometry_fields = [w for w in windows(geometry_group)
                                   if user.GetParent(w) == geometry_group and kind(w) == "Edit"]
                assert len(geometry_fields) == 3, "Movie duration, width and height editors missing"
                if reopening:
                    deadline = time.monotonic() + 10
                    while [float(text(w)) for w in endless_fields] != [7200.5, 45.125] and time.monotonic() < deadline:
                        time.sleep(.05)
                    assert [float(text(w)) for w in endless_fields] == [7200.5, 45.125], (
                        "Custom Endless durations did not survive reopening", [text(w) for w in endless_fields])
                    deadline = time.monotonic() + 10
                    while [float(text(w)) for w in geometry_fields] != [35.125, 1920, 1088] and time.monotonic() < deadline:
                        time.sleep(.05)
                    assert [float(text(w)) for w in geometry_fields] == [35.125, 1920, 1088], "Custom Movie geometry did not survive reopening"
                else:
                    for control, seconds in zip(endless_fields, ("7200.5", "45.125")):
                        value = C.create_unicode_buffer(seconds)
                        user.SendMessageW(control, 0xC, 0, C.cast(value, C.c_void_p).value)
                    project = Path(temporary) / "output/movies/current.serenitymovie.json"
                    deadline = time.monotonic() + 10
                    while time.monotonic() < deadline:
                        saved = json.loads(project.read_text(encoding="utf-8"))
                        if (saved.get("endless_target_seconds"), saved.get("endless_segment_seconds")) == (7200.5, 45.125):
                            break
                        time.sleep(.05)
                    else:
                        raise AssertionError("Endless duration edits were capped or failed to persist")
                    for control, key, value in zip(geometry_fields,
                                                  ("duration_seconds", "width", "height"),
                                                  (35.125, 1920, 1088)):
                        native_text = C.create_unicode_buffer(str(value))
                        user.SendMessageW(control, 0xC, 0, C.cast(native_text, C.c_void_p).value)
                        deadline = time.monotonic() + 10
                        while time.monotonic() < deadline:
                            saved = json.loads(project.read_text(encoding="utf-8"))
                            if saved["shots"][0][key] == value:
                                break
                            time.sleep(.05)
                        else:
                            raise AssertionError("Custom Movie geometry edit did not persist: " + key)
                if not reopening:
                    user.SendMessageW(editor, 0xB1, 0, -1)
                    # Queued keyboard input follows pending controller restoration;
                    # cross-process synchronous edit messages can reenter that work.
                    for character in sample:
                        user.PostMessageW(editor, 0x102, ord(character), 0)  # WM_CHAR
                    project = Path(temporary) / "output/movies/current.serenitymovie.json"
                    deadline = time.monotonic() + 10
                    while time.monotonic() < deadline:
                        try:
                            saved = json.loads(project.read_text(encoding="utf-8"))
                        except (OSError, json.JSONDecodeError):
                            saved = {}
                        if saved.get("director_brief") == sample:
                            break
                        time.sleep(.1)
                    else:
                        log.seek(0)
                        raise AssertionError(dict(editor=text(editor), saved=saved.get("director_brief"), files=[str(p.relative_to(temporary)) for p in Path(temporary).rglob("*.json")], output=log.read()))
                reset = next(w for w in controls if kind(w) == "Button" and text(w) == "Reset")
                user.SendMessageW(reset, 0xF5, 0, 0)
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline:
                    labels = [text(w) for w in controls if kind(w) == "Static"]
                    if "CK INT8" in labels and "Euler · 19" in labels:
                        break
                    time.sleep(.05)
                else:
                    raise AssertionError("Reset did not preserve the shared CK default")
                if reopening and args.trash:
                    library = Path(temporary) / "output/movies"
                    previous = set(library.glob("*.serenitymovie.json"))
                    new = next(w for w in controls if kind(w) == "Button" and text(w) == "New")
                    user.SendMessageW(new, 0xF5, 0, 0)
                    deadline = time.monotonic() + 10
                    while time.monotonic() < deadline:
                        created = set(library.glob("*.serenitymovie.json")) - previous
                        if len(created) == 1 and text(editor) != sample:
                            break
                        time.sleep(.05)
                    else:
                        raise AssertionError("New movie project was not created")
                    deleting = created.pop().resolve()
                    payload = deleting.read_bytes()
                    delete = next(w for w in controls if kind(w) == "Button" and text(w) == "Delete")
                    user.SendMessageW(delete, 0xF5, 0, 0)
                    deadline = time.monotonic() + 10
                    while time.monotonic() < deadline:
                        if not deleting.exists() and text(editor) == sample:
                            break
                        time.sleep(.05)
                    else:
                        log.seek(0)
                        raise AssertionError(dict(message="Trash did not remove the project and restore the previous project", exists=deleting.exists(), editor=text(editor), labels=[text(w) for w in controls if kind(w)=="Static" and text(w)], log=log.read()))
                    restore_fixture(deleting, payload, Path(temporary)/"restored-project.json")
                user.PostMessageW(window, 0x10, 0, 0)
                assert process.wait(20) == 0
                log.seek(0)
                output = log.read()
                assert "Unknown widget" not in output and "Unsupported desktop operation" not in output, output
    print("Shared Movie controller: selected H3 runtime policies, CK Reset, native Unicode edit, custom Endless target/segment durations, project autosave, clean close and reopening persisted values passed." + (" Native Recycle Bin media, sidecar, history and project deletion and restoration verified." if args.trash else ""))


if __name__ == "__main__":
    main()
