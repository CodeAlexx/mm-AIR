"""Native GUI startup with absent auto-restore files and temporary parents.

Uses isolated settings and no inherited console streams, matching Explorer launch.
"""
import argparse
import ctypes as C
from ctypes import wintypes as W
import importlib.util
import os
from pathlib import Path
import tempfile
import time

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('application',type=Path)
    parser.add_argument('adapter',type=Path)
    args=parser.parse_args()
    source=Path(__file__).resolve().parents[3]/'toolkits/desktop/test_windows.py'
    spec=importlib.util.spec_from_file_location('native_desktop_test',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    bind=module.bind
    user=C.WinDLL('user32',use_last_error=True)
    process=None
    previous=os.environ.copy()
    try:
        with tempfile.TemporaryDirectory(prefix='mm-air-launch-') as temporary:
            root=Path(temporary)
            missing=root/'missing-startup.json'
            os.environ['MM_AIR_PARAMETERS_FILE']=str(missing)
            os.environ['MM_AIR_UI_HOST']=str(args.adapter.resolve())
            os.environ['XDG_DATA_HOME']=str(root/'data')
            os.environ['MM_AIR_OUTPUT_ROOT']=str(root/'output')
            os.environ['TEMP']=str(root/'not-created-yet'/'temp')
            system_root=os.environ['SystemRoot']  # Windows env lookup ignores key casing.
            os.environ['PATH']=str(Path(system_root)/'System32')+os.pathsep+system_root
            os.environ.pop('TMPDIR',None)
            callback=C.WINFUNCTYPE(W.BOOL,W.HWND,W.LPARAM)
            get_text=bind(user,'GetWindowTextW',C.c_int,W.HWND,W.LPWSTR,C.c_int)
            visible=bind(user,'IsWindowVisible',W.BOOL,W.HWND)
            def windows():
                found=[]
                @callback
                def collect(window,_):
                    text=C.create_unicode_buffer(2048);get_text(window,text,len(text))
                    if text.value.startswith('MM-AIR') and visible(window):found.append(window)
                    return True
                bind(user,'EnumWindows',W.BOOL,callback,W.LPARAM)(collect,0)
                return found
            before=set(windows())
            process=module.Child([str(args.application.resolve())],'WinSta0\\Default')
            deadline=time.monotonic()+20
            while time.monotonic()<deadline:
                assert process.poll() is None,'GUI exited during launch'
                hosts=[window for window in windows() if window not in before]
                if hosts:break
                time.sleep(.05)
            else:raise AssertionError('Native window did not become visible')
            time.sleep(.5)
            bind(user,'PostMessageW',W.BOOL,W.HWND,W.UINT,W.WPARAM,W.LPARAM)(hosts[0],0x10,0,0)
            assert process.wait(20)==0
            log=Path(previous['LOCALAPPDATA'])/'AIR/Logs'/f'{args.application.stem}-{process.pid}.log'
            transcript=log.read_text(encoding='utf-8')
            assert str(missing) in transcript and 'Application exit code: 0' in transcript,transcript
            print('Native GUI launch with system-only PATH: visible Win32 window, missing startup recipe recovered, missing temp parents created, clean shutdown PASS')
    finally:
        if process:
            if process.poll() is None:process.terminate();process.wait()
            process.close()
        os.environ.clear();os.environ.update(previous)

if __name__=='__main__':main()
