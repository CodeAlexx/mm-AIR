#!/usr/bin/env python3
"""Exercise all five MM-AIR workspaces on an owned private X11 display."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "tests"))
from desktop_x11 import X11, png, wait_for

import importlib.util
spec = importlib.util.spec_from_file_location(
    "desktop_fixture", ROOT / "toolkits/desktop/test_desktop.py")
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


def type_text(keys, value: str) -> None:
    names = {" ": "space", "/": "slash", ".": "period", "-": "minus", "_": "underscore"}
    for character in value:
        keys.key(names.get(character, character))


def run(args: argparse.Namespace, scratch: Path) -> None:
    from PIL import Image

    temporary = scratch / "tmp"
    temporary.mkdir()
    reference = scratch / "reference.png"
    reference_color = (231, 37, 145)
    Image.new("RGB", (480, 270), reference_color).save(reference)
    last_reference = scratch / "last-reference.png"
    last_reference_color = (41, 109, 239)
    Image.new("RGB", (480, 270), last_reference_color).save(last_reference)
    control_media = scratch / "control.png"
    control_color = (23, 211, 83)
    Image.new("RGB", (480, 270), control_color).save(control_media)
    output_media = scratch / "result.mp4"
    edit_source = scratch / "edit-source.mp4"
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "lavfi",
                    "-i", "color=c=blue:size=640x360:rate=24:duration=4", "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", str(edit_source)], check=True)
    captures = Path(args.screenshots)
    captures.mkdir(parents=True, exist_ok=True)
    app_log = scratch / "app.log"
    env = dict(
        os.environ,
        TMPDIR=str(temporary),
        XDG_CACHE_HOME=str(scratch / "cache"),
        GDK_BACKEND="x11",
        GSK_RENDERER="cairo",
        GTK_A11Y="none",
        GTK_USE_PORTAL="0",
        MM_AIR_OUTPUT_ROOT=str(scratch / "output"),
    )
    app = x = helper = window = None
    try:
        with app_log.open("wb") as output:
            app = subprocess.Popen([args.binary], env=env, stdout=output, stderr=output)
            pid_file = wait_for(
                app, "owned AIR adapter PID",
                lambda: next(temporary.glob("air-desktop-*/pid"), None), timeout=15)
            helper_pid = int(wait_for(
                app, "AIR adapter PID contents",
                lambda: pid_file.read_text().strip(), timeout=10))
            helper_path = Path("/proc") / str(abs(helper_pid))
            helper = SimpleNamespace(
                pid=abs(helper_pid), poll=lambda: None if helper_path.exists() else 0)
            x = X11()
            # XFetchName exposes the legacy WM_NAME encoding; identify this test's
            # only large visible window by the adapter PID, as AIR's shared test does.
            window = wait_for(
                app, "MM-AIR native window",
                lambda: next((w for w in x.children(x.root)
                              if x.pid(w) == helper.pid and x.geometry(w)[0] >= 1180), None),
                timeout=15)
            x.activate(window, helper)
            keys = native.Input(x)
            width, height = x.geometry(window)
            assert width >= 1180 and height >= 760, (width, height)

            def shot(name: str) -> bytes:
                time.sleep(0.35)
                frame = x.image(window)
                png(captures / name, frame)
                return frame[2]

            def changed(before: bytes):
                pixels = x.image(window)[2]
                return pixels if pixels != before else None

            def colored_pixels(color):
                pixels = x.image(window)[2]
                count = 0
                for offset in range(0, len(pixels), 3):
                    if all(abs(pixels[offset + channel] - color[channel]) <= 5
                           for channel in range(3)):
                        count += 1
                return pixels if count >= 500 else None

            def reference_pixels():
                return colored_pixels(reference_color)

            def choose_path(title: str, pathname: Path) -> None:
                dialog = wait_for(
                    app, title, lambda: x.find(helper.pid, title), timeout=8)
                x.x.XSetInputFocus(x.display, dialog, 2, 0)
                x.sync()
                keys.key("l", ("Control_L",))
                type_text(keys, str(pathname))
                deadline = time.monotonic() + 8
                while x.find(helper.pid, title):
                    if app.poll() is not None:
                        raise AssertionError(f"application exited while {title} was open")
                    if time.monotonic() >= deadline:
                        raise AssertionError(f"timed out accepting typed path in {title}")
                    keys.key("Return")
                    time.sleep(0.4)

            generate = shot("generate.png")
            keys.key("5", ("Control_L",))
            wait_for(app, "Prompt Lab transition", lambda: changed(generate), timeout=5)
            prompt_lab = shot("prompt-lab.png")
            assert prompt_lab != generate
            keys.key("1", ("Control_L",))
            wait_for(app, "Generate transition from Prompt Lab", lambda: changed(prompt_lab), timeout=5)
            keys.key("o", ("Control_L",))
            choose_path("Add H3 reference media", reference)
            selected = shot("reference-selected.png")
            assert selected != generate
            keys.key("l", ("Control_L",))
            choose_path("Choose H3 last frame", last_reference)
            shot("last-reference-selected.png")
            keys.key("2", ("Control_L",))
            wait_for(app, "Edit transition", lambda: changed(selected), timeout=5)
            edit = shot("edit.png")
            keys.click(260, 182)
            choose_path("Choose Edit source image or video", edit_source)
            time.sleep(0.8)
            edit_loaded = shot("edit-source-loaded.png")
            assert edit_loaded != edit
            keys.click(250, 472)
            time.sleep(1.2)
            keys.drag((650, 350), (900, 500))
            time.sleep(1.2)
            painted = shot("edit-painted-mask.png")
            assert painted != edit_loaded
            assert sum(1 for offset in range(0, len(painted), 3)
                       if painted[offset] > 145 and painted[offset + 1] < 115 and
                       painted[offset + 2] < 115) >= 500, (
                "paint gesture did not produce a visible red authored mask")
            keys.click(250, 472)
            keys.key("3", ("Control_L",))
            wait_for(app, "Movie Maker transition", lambda: changed(edit), timeout=5)
            movie = shot("movie-maker.png")
            keys.click(1209, 84)  # New project
            time.sleep(0.5)
            keys.click(151, 615)  # Add shot
            project_file = scratch / "output/movies/current.serenitymovie.json"
            project = wait_for(app, "Movie Maker project autosave", lambda: (
                json.loads(project_file.read_text()) if project_file.exists() and
                len(json.loads(project_file.read_text()).get("shots", [])) == 2 else None), timeout=5)
            assert project["schema"] == "serenity.h3.movie.v1"
            shot("movie-shot-added.png")
            keys.key("4", ("Control_L",))
            wait_for(app, "ControlNet transition", lambda: changed(movie), timeout=5)
            control = shot("controlnet.png")
            assert generate != movie and movie != control and generate != control
            keys.key("o", ("Control_L", "Shift_L"))
            choose_path("Add H3 control media", control_media)
            shot("control-selected.png")

            keys.key("1", ("Control_L",))
            wait_for(app, "Generate page return", lambda: changed(control), timeout=5)
            keys.key("q", ("Control_L",))
            app.wait(timeout=8)
            assert app.returncode == 0, app_log.read_text(errors="replace")
            log_text = app_log.read_text(errors="replace")
            assert f"mm-air media selected first-reference={reference}\n" in log_text
            assert f"mm-air media selected last-reference={last_reference}\n" in log_text
            assert f"mm-air media selected control={control_media}\n" in log_text
            assert "mm-air edit painted mask accepted\n" in log_text
            assert "mm-air H3 request validated; generation not connected\n" not in log_text, (
                "runtime policy selectors must fail closed until explicitly chosen")
            assert not helper_path.exists(), "AIR process returned before its adapter exited"
            assert not list(temporary.iterdir()), "AIR left native session scratch behind"
            print("MM-AIR desktop: native media/output choosers, fail-closed H3 runtime policy, five workspaces and clean shutdown PASS")
    except Exception:
        if app_log.exists():
            print(app_log.read_text(errors="replace"), file=sys.stderr)
        raise
    finally:
        if app and app.poll() is None:
            if helper and helper.poll() is None:
                try:
                    os.kill(helper.pid, 15)
                except ProcessLookupError:
                    pass
            app.terminate()
            try:
                app.wait(timeout=8)
            except subprocess.TimeoutExpired:
                app.kill()
                app.wait(timeout=8)
        if x:
            x.restore()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", default=str(ROOT / "build-dev/bin/mm-air"))
    parser.add_argument("--xvfb", default=(
        shutil.which("Xvfb") or str(ROOT / "build-dev/desktop-sdk/usr/bin/Xvfb")))
    parser.add_argument("--screenshots", required=True)
    parser.add_argument("--isolated", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not args.isolated:
        runner = Path(args.xvfb).resolve().parent / "xvfb-run"
        if not runner.exists():
            parser.error("xvfb-run is required")
        env = dict(os.environ, PATH=str(runner.parent) + os.pathsep + os.environ["PATH"])
        subprocess.run([
            str(runner), "-a", "-s", "-screen 0 1600x1000x24",
            sys.executable, str(Path(__file__).resolve()), "--isolated",
            "--binary", args.binary, "--xvfb", args.xvfb,
            "--screenshots", args.screenshots,
        ], env=env, check=True, timeout=45)
        return
    with tempfile.TemporaryDirectory(prefix="mm-air-desktop-") as temporary:
        run(args, Path(temporary))


if __name__ == "__main__":
    main()
