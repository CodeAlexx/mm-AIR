"""Opt-in real Movie generation through the installed shared Windows application.

Provide an isolated output root containing movies/current.serenitymovie.json,
an H3 parameter file, and the usual MM_AIR_H3_* runtime environment variables.
This uses the GPU and preserves generated media and logs in that output root.
"""
import argparse
import ctypes as C
from ctypes import wintypes as W
import json
import os
from pathlib import Path
import subprocess
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("application", type=Path)
    parser.add_argument("parameters", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--direct", action="store_true", help="Start the executable without arguments; restore parameters from its runtime configuration")
    args = parser.parse_args()
    output = args.output.resolve()
    project_path = output / "movies/current.serenitymovie.json"
    project = json.loads(project_path.read_text(encoding="utf-8"))
    assert len(project["shots"]) == 1 and not project["shots"][0]["takes"]
    expected = json.loads(args.parameters.read_text(encoding="utf-8"))
    shot = project["shots"][0]
    expected_geometry = dict(width=shot["width"], height=shot["height"], seconds=shot["duration_seconds"], seed=shot["seed"])
    assert expected["attention"] == 4, "This acceptance test requires selected CK INT8"
    user = C.WinDLL("user32")
    user.SetProcessDPIAware()
    user.SendMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
    user.SendMessageW.restype = W.LPARAM
    user.PostMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
    callback_type = C.WINFUNCTYPE(W.BOOL, W.HWND, W.LPARAM)
    user.EnumChildWindows.argtypes = [W.HWND, callback_type, W.LPARAM]

    def text(window):
        value = C.create_unicode_buffer(4096)
        user.SendMessageW(window, 0xD, len(value), C.cast(value, C.c_void_p).value)
        return value.value

    def windows(parent=None):
        result = []

        @callback_type
        def collect(window, _):
            result.append(window)
            return True

        if parent:
            user.EnumChildWindows(parent, collect, 0)
        else:
            user.EnumWindows(collect, 0)
        return result

    environment = os.environ.copy()
    environment["PATH"] = str(args.application.resolve().parent) + os.pathsep + environment["PATH"]
    environment["MM_AIR_OUTPUT_ROOT"] = str(output)
    environment["XDG_DATA_HOME"] = str(output / "data")
    before = set(windows())
    host = None
    with (output / "generation.log").open("w", encoding="utf-8") as log:
        command = [str(args.application.resolve())]
        if not args.direct:
            command += ["--parameters", str(args.parameters.resolve())]
        process = subprocess.Popen(command, env=environment, stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                assert process.poll() is None, "Controller exited during startup"
                found = [w for w in windows() if w not in before and text(w).startswith("MM-AIR")]
                if found:
                    host = found[0]
                    controls = windows(host)
                    if any(text(w) == "Generate parameters restored" for w in controls):
                        break
                time.sleep(.1)
            else:
                raise AssertionError("Saved H3 parameters were not restored")
            assert any(text(w) == "CK INT8" for w in controls), "Movie did not show selected CK policy"
            movie = next(w for w in controls if text(w) == "Movie")
            user.SendMessageW(movie, 0xF5, 0, 0)
            queue = next(w for w in controls if text(w) == "Queue H3 take")
            user.SendMessageW(queue, 0xF5, 0, 0)
            started = time.monotonic()
            print("Shared Movie Queue H3 take activated with selected CK INT8", flush=True)
            while time.monotonic() - started < 1200:
                assert process.poll() is None, "Controller exited during generation"
                saved = json.loads(project_path.read_text(encoding="utf-8"))
                takes = saved["shots"][0]["takes"]
                if takes and takes[-1]["state"] == "done":
                    media = Path(takes[-1]["output"])
                    assert media.is_file() and media.stat().st_size > 0
                    parameters = json.loads(Path(str(media) + ".json").read_text(encoding="utf-8"))
                    for key in ("profile", "conditioner_projection", "transformer_projection", "attention"):
                        assert parameters[key] == expected[key], (key, parameters[key], expected[key])
                    for key, value in expected_geometry.items():
                        assert parameters[key] == value, (key, parameters[key], value)
                    receipt = dict(media=str(media), elapsed_seconds=time.monotonic()-started,
                                   startup="direct_executable" if args.direct else "explicit_parameters",
                                   selected_policies={key: parameters[key] for key in ("profile", "conditioner_projection", "transformer_projection", "attention")},
                                   geometry={key: parameters[key] for key in ("width", "height", "seconds", "seed")},
                                   project=str(project_path))
                    (output / "acceptance.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
                    print(json.dumps(receipt), flush=True)
                    break
                assert not any(t["state"] == "failed" for t in takes), "Movie take failed; inspect generation.log"
                time.sleep(1)
            else:
                raise TimeoutError("Movie generation did not finish within 20 minutes")
            user.PostMessageW(host, 0x10, 0, 0)
            assert process.wait(30) == 0
        finally:
            if process.poll() is None:
                if host:
                    user.PostMessageW(host, 0x10, 0, 0)
                try:
                    process.wait(30)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    process.wait()


if __name__ == "__main__":
    main()
