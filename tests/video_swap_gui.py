#!/usr/bin/env python3
"""DEV GUI HARNESS: drive MM-Air's Edit mode 8 (Video Swap) on a private Xvfb display.

It never touches the owner's desktop session: xvfb-run owns a fresh display, the
application runs on a private D-Bus session bus (dbus-run-session) with portals
disabled and its own XDG_RUNTIME_DIR, and it gets its own data/config/cache/
output/tmp folders under --scratch. Steps: open Edit, pick "Video Swap · auto person", load the source video,
add a character picture, press Auto Mask, wait for the job, and screenshot each step.

Auto Mask runs SAM 3 on the GPU inside the app, so run this whole harness under
~/h3-air/bin/gpu-run.sh LOG -- python3 video_swap_gui.py ...  (it takes no GPU lock itself).
Use --probe to stop after the Edit page (no GPU work).
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from types import SimpleNamespace

APP = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(APP / "tests"))
from air_root import air_root
ROOT = air_root()
sys.path.insert(0, str(ROOT / "tests"))
from desktop_x11 import X11, png, wait_for  # noqa: E402

import importlib.util  # noqa: E402
spec = importlib.util.spec_from_file_location(
    "desktop_fixture", ROOT / "toolkits/desktop/test_desktop.py")
native = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native)


def type_text(keys, value: str) -> None:
    names = {" ": "space", "/": "slash", ".": "period", "-": "minus", "_": "underscore"}
    for character in value:
        keys.key(names.get(character, character))


def prepare_bin(args, scratch: Path) -> Path:
    """mm-air finds desktop.ui, desktop.css and swap-masks.json in <bindir>/share/mm-air."""
    bindir = scratch / "bin"
    share = bindir / "share/mm-air"
    share.mkdir(parents=True, exist_ok=True)
    shutil.copy2(args.binary, bindir / "mm-air")
    providers = Path(args.binary).parent / ".air"
    if providers.exists():  # RUNPATH $ORIGIN/.air/providers
        shutil.copytree(providers, bindir / ".air", symlinks=True)
    app = APP
    shutil.copy2(app / "desktop.ui", share / "desktop.ui")
    shutil.copy2(app / "desktop.css", share / "desktop.css")
    shutil.copy2(app / "presets/swap-masks.json", share / "swap-masks.json")
    return bindir / "mm-air"


def run(args, scratch: Path) -> None:
    shots = Path(args.shots)
    shots.mkdir(parents=True, exist_ok=True)
    for name in ("tmp", "data", "config", "cache", "output"):
        (scratch / name).mkdir(parents=True, exist_ok=True)
    binary = prepare_bin(args, scratch)
    env = dict(
        os.environ,
        TMPDIR=str(scratch / "tmp"),
        XDG_DATA_HOME=str(scratch / "data"),
        XDG_CONFIG_HOME=str(scratch / "config"),
        XDG_CACHE_HOME=str(scratch / "cache"),
        MM_AIR_OUTPUT_ROOT=str(scratch / "output"),
        MM_AIR_UI_HOST=args.air_ui,
        MM_AIR_SAM3_PLUGIN=args.plugin,
        MM_AIR_SAM3_MODEL=args.model,
        # Isolation from the owner's desktop session: no session bus, no portals,
        # a private runtime dir. Without this, GtkFileChooserNative asks the
        # owner's xdg-desktop-portal, whose dialogs open on the owner's screen.
        XDG_RUNTIME_DIR=str(scratch / "runtime"),
        GDK_DEBUG="no-portals",
        GDK_BACKEND="x11",
        GSK_RENDERER="cairo",
        GTK_A11Y="none",
        GTK_USE_PORTAL="0",
    )
    for name in ("DBUS_SESSION_BUS_ADDRESS", "WAYLAND_DISPLAY", "XDG_SESSION_TYPE",
                 "GNOME_SETUP_DISPLAY", "SESSION_MANAGER"):
        env.pop(name, None)
    (scratch / "runtime").mkdir(mode=0o700, exist_ok=True)
    if args.runtime_config:
        # A private copy: the app may write preferences back into it.
        shutil.copy2(args.runtime_config, scratch / "runtime.json")
        env["MM_AIR_RUNTIME_CONFIG"] = str(scratch / "runtime.json")
    if args.probe or args.stop_after:
        env["CUDA_VISIBLE_DEVICES"] = ""
    log_path = scratch / "app.log"
    app = x = helper = None
    try:
        with log_path.open("wb") as output:
            # A private session bus for the app and its UI adapter only.
            app = subprocess.Popen(["dbus-run-session", "--", str(binary)], env=env,
                                   stdout=output, stderr=output)
            pid_file = wait_for(app, "AIR adapter PID",
                                lambda: next((scratch / "tmp").glob("air-desktop-*/pid"), None),
                                timeout=30)
            helper_pid = abs(int(wait_for(app, "adapter PID contents",
                                          lambda: pid_file.read_text().strip(), timeout=10)))
            helper_path = Path("/proc") / str(helper_pid)
            helper = SimpleNamespace(pid=helper_pid,
                                     poll=lambda: None if helper_path.exists() else 0)
            x = X11()
            window = wait_for(app, "MM-Air window", lambda: next(
                (w for w in x.children(x.root)
                 if x.pid(w) == helper.pid and x.geometry(w)[0] >= 1180), None), timeout=30)
            x.activate(window, helper)
            keys = native.Input(x)

            def shot(name: str, settle: float = 0.6) -> None:
                time.sleep(settle)
                # The root window also holds GTK popovers (dropdown lists).
                png(shots / name, x.image(x.root))
                print("shot", shots / name, flush=True)

            def choose_path(title: str, pathname: str) -> None:
                try:
                    dialog = wait_for(app, title, lambda: x.find(helper.pid, title),
                                      timeout=args.dialog_timeout)
                except AssertionError:
                    shot("dialog-missing.png", 0.1)
                    raise
                x.x.XSetInputFocus(x.display, dialog, 2, 0)
                x.sync()
                keys.key("l", ("Control_L",))
                type_text(keys, pathname)
                deadline = time.monotonic() + 10
                while x.find(helper.pid, title):
                    if time.monotonic() >= deadline:
                        raise AssertionError(f"timed out accepting {title}")
                    keys.key("Return")
                    time.sleep(0.5)

            time.sleep(2.0)
            keys.click(*args.edit_nav)  # the Edit item of the navigation rail
            shot("01-edit.png", 1.5)
            if args.probe:
                return
            # Mode dropdown, then its 9th item (Video Swap · auto person).
            keys.click(*args.mode_dropdown)
            time.sleep(0.8)
            shot("02-mode-list.png", 0.2)
            if args.stop_after == 2:
                return
            keys.click(*args.mode_item)
            shot("03-mode-video-swap.png", 1.0)
            # Optional scripted settings: "click:X,Y", "type:TEXT", "key:NAME",
            # "select:X,Y" (click a field, select all), "shot:NAME", separated by ";".
            for action in [a for a in args.actions.split(";") if a]:
                kind, _, value = action.partition(":")
                if kind == "click":
                    keys.click(*point(value))
                    time.sleep(0.6)
                elif kind == "select":
                    keys.click(*point(value))
                    time.sleep(0.3)
                    keys.key("a", ("Control_L",))
                elif kind == "type":
                    type_text(keys, value)
                elif kind == "key":
                    keys.key(value)
                    time.sleep(0.4)
                elif kind == "shot":
                    shot(value + ".png", 0.6)
                else:
                    raise ValueError(action)
            if args.stop_after == 3:
                return
            keys.click(*args.source_button)
            choose_path("Choose Edit source image or video", args.source)
            shot("04-source-loaded.png", 2.0)
            if args.stop_after == 4:
                return
            keys.click(*args.picture_button)
            choose_path(args.picture_title, args.picture)
            shot("05-picture-added.png", 1.5)
            keys.click(*args.auto_mask_button)
            shot("06-auto-mask-started.png", 2.0)
            start = time.monotonic()
            log = log_path
            while time.monotonic() - start < args.mask_timeout:
                text = log.read_text(errors="replace")
                if "Video Swap masks ready" in text or "Video Swap masks failed" in text:
                    break
                if app.poll() is not None:
                    raise AssertionError("mm-air exited during Auto Mask")
                time.sleep(5)
            shot("07-auto-mask-done.png", 4.0)
            shot("08-check-preview-later.png", 3.0)
    finally:
        if app and app.poll() is None:
            if helper and helper.poll() is None:
                try:
                    os.kill(helper.pid, 15)
                except ProcessLookupError:
                    pass
            app.terminate()
            try:
                app.wait(timeout=10)
            except subprocess.TimeoutExpired:
                app.kill()
                app.wait(timeout=10)
        if x:
            x.restore()
        print(log_path.read_text(errors="replace")[-3000:])


def point(value: str):
    a, b = value.split(",")
    return int(a), int(b)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True)
    parser.add_argument("--air-ui", required=True)
    parser.add_argument("--plugin", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--source", default="")
    parser.add_argument("--picture", default="")
    parser.add_argument("--picture-title", default="Add character reference image")
    parser.add_argument("--shots", required=True)
    parser.add_argument("--scratch", required=True)
    parser.add_argument("--xvfb-run", default=str(Path.home() / ".local/opt/xvfb/usr/bin/xvfb-run"))
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--stop-after", type=int, default=0)
    parser.add_argument("--actions", default="")
    parser.add_argument("--dialog-timeout", type=float, default=60)
    parser.add_argument("--runtime-config", default="",
                        help="mm-air.runtime.v1 JSON to copy into the scratch folder")
    parser.add_argument("--edit-nav", type=point, default=(47, 122))
    parser.add_argument("--mode-dropdown", type=point, default=(150, 400))
    parser.add_argument("--mode-item", type=point, default=(150, 600))
    parser.add_argument("--source-button", type=point, default=(260, 182))
    parser.add_argument("--picture-button", type=point, default=(260, 300))
    parser.add_argument("--auto-mask-button", type=point, default=(150, 500))
    parser.add_argument("--mask-timeout", type=float, default=900)
    parser.add_argument("--isolated", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not args.isolated:
        runner = Path(args.xvfb_run)
        env = dict(os.environ, PATH=str(runner.parent) + os.pathsep + os.environ["PATH"])
        env.pop("DISPLAY", None)
        env.pop("WAYLAND_DISPLAY", None)
        argv = [str(runner), "-a", "-s", "-screen 0 1600x1000x24", sys.executable,
                str(Path(__file__).resolve()), "--isolated"] + sys.argv[1:]
        subprocess.run(argv, env=env, check=True, timeout=args.mask_timeout + 300)
        return
    scratch = Path(args.scratch)
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)
    run(args, scratch)


if __name__ == "__main__":
    main()
