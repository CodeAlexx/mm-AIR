@echo off
rem Build an MM-Air console tool with airc (x64 MSVC). Usage: build-cli.cmd SOURCE.ai OUT.exe
setlocal
if not exist "%~dp0local-paths.cmd" (echo Create tools\local-paths.cmd from local-paths.example.cmd & exit /b 1)
call "%~dp0local-paths.cmd"
for %%v in (INCLUDE LIB LIBPATH Platform VSCMD_ARG_TGT_ARCH VSCMD_ARG_HOST_ARCH VSCMD_ARG_app_plat VSCMD_VER VSINSTALLDIR VCINSTALLDIR VCToolsInstallDir VCToolsVersion VCIDEInstallDir VS170COMNTOOLS WindowsSdkDir WindowsSdkBinPath WindowsSdkVerBinPath WindowsLibPath WindowsSDKLibVersion WindowsSDKVersion UCRTVersion UniversalCRTSdkDir DevEnvDir EXTERNAL_INCLUDE __VSCMD_PREINIT_PATH __DOTNET_PREFERRED_BITNESS) do set %%v=
set PATH=C:\Windows\system32;C:\Windows;C:\Windows\System32\WindowsPowerShell\v1.0
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1 || exit /b 1
set CUDA=%CUDA_ROOT%
set PATH=%CUDA%\bin;%CUDA%\bin\x64;C:\NVIDIA-Runtime\cuda-13.3-cudnn-9.26;%PATH%
set BUILD=%AIR_GPU_BUILD%
"%BUILD%\bin\airc.exe" build %1 -o %2 --mode release --provider hash.sha256=portable || exit /b 1
