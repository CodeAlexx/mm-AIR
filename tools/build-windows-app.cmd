@echo off
rem Build C:\MM-Air\src into a native MM-Air executable (x64 MSVC only).
rem Usage: build-mmair.cmd NAME   -> produces %BUILD%\bin\NAME.exe
setlocal
if not exist "%~dp0local-paths.cmd" (echo Create tools\local-paths.cmd from local-paths.example.cmd & exit /b 1)
call "%~dp0local-paths.cmd"
set NAME=%1
if "%NAME%"=="" set NAME=MM-Air-dev
for %%v in (INCLUDE LIB LIBPATH Platform VSCMD_ARG_TGT_ARCH VSCMD_ARG_HOST_ARCH VSCMD_ARG_app_plat VSCMD_VER VSINSTALLDIR VCINSTALLDIR VCToolsInstallDir VCToolsVersion VCIDEInstallDir VS170COMNTOOLS WindowsSdkDir WindowsSdkBinPath WindowsSdkVerBinPath WindowsLibPath WindowsSDKLibVersion WindowsSDKVersion UCRTVersion UniversalCRTSdkDir DevEnvDir EXTERNAL_INCLUDE __VSCMD_PREINIT_PATH __DOTNET_PREFERRED_BITNESS) do set %%v=
set PATH=C:\Windows\system32;C:\Windows;C:\Windows\System32\WindowsPowerShell\v1.0;%MM_AIR_PYTHON_DIR%
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul || exit /b 1
where cl | findstr /i "Hostx64\\x64" >nul || (echo wrong cl & exit /b 1)
set BUILD=%AIR_GPU_BUILD%
set CUDA=%CUDA_ROOT%
set STAGE=C:\MM-Air\build\%NAME%
set CMAKE="C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe"
set PATH=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja;%CUDA%\bin;%CUDA%\bin\x64;C:\NVIDIA-Runtime\cuda-13.3-cudnn-9.26;%PATH%
if not exist "%STAGE%" mkdir "%STAGE%"
echo [0/3] update airc and runtime from C:\AIR
%CMAKE% --build "%BUILD%" --target airc air_rt >"%STAGE%\toolchain.log" 2>&1 || (type "%STAGE%\toolchain.log" & exit /b 1)
echo [1/3] airc emit C
"%BUILD%\bin\airc.exe" build C:\MM-Air\src\main.ai -o "%STAGE%\console.exe" --mode release --provider hash.sha256=portable --keep-c "%STAGE%\main.c" || exit /b 1
echo [2/3] configure
%CMAKE% -S "%AIR_GPU_SOURCE%" -B "%BUILD%" "-DAIR_WINDOWS_APP_C=%STAGE%\main.c" "-DAIR_WINDOWS_APP_NAME=%NAME%" >"%STAGE%\configure.log" 2>&1 || (type "%STAGE%\configure.log" & exit /b 1)
echo [3/3] link
%CMAKE% --build "%BUILD%" --target air_windows_app >"%STAGE%\link.log" 2>&1 || (type "%STAGE%\link.log" & exit /b 1)
copy /y "%BUILD%\bin\%NAME%.exe" "%STAGE%\%NAME%.exe" >nul
echo built %STAGE%\%NAME%.exe
