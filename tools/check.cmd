@echo off
rem MM-Air's checks that need no GPU, model or display, on Windows. Run before every push:
rem   tools\check.cmd          static contract, every declared program compiles, screen wording
rem   tools\check.cmd --tests  the above, then `airproj test` (builds and runs the declared tests)
rem The same checks as tools/check.sh. AIR is found at %AIR_ROOT% or ..\AIR; its built tools at
rem %AIR_TOOLCHAIN% or %AIR_ROOT%\build-windows-compiler.
setlocal
set "APP=%~dp0.."
if not defined AIR_ROOT set "AIR_ROOT=%APP%\..\AIR"
for %%p in ("%AIR_ROOT%") do set "AIR_ROOT=%%~fp"
if not defined AIR_TOOLCHAIN set "AIR_TOOLCHAIN=%AIR_ROOT%\build-windows-compiler"
if not exist "%AIR_TOOLCHAIN%\bin\airc.exe" (echo no airc.exe in %AIR_TOOLCHAIN%\bin ^(set AIR_TOOLCHAIN^) 1>&2 & exit /b 2)
if not defined AIR_STDLIB set "AIR_STDLIB=%AIR_ROOT%\stdlib"
set "PYTHON=python"
if exist "%~dp0local-paths.cmd" call "%~dp0local-paths.cmd"
if defined MM_AIR_PYTHON_DIR if exist "%MM_AIR_PYTHON_DIR%\python.exe" set "PYTHON=%MM_AIR_PYTHON_DIR%\python.exe"
rem A shell opened for 32-bit Visual Studio makes airc pick the 32-bit C compiler; drop that
rem environment so airc finds x64 MSVC itself.
for %%v in (INCLUDE LIB LIBPATH Platform VSCMD_ARG_TGT_ARCH VSCMD_ARG_HOST_ARCH VSCMD_ARG_app_plat VSCMD_VER VSINSTALLDIR VCINSTALLDIR VCToolsInstallDir VCToolsVersion VCIDEInstallDir VS170COMNTOOLS WindowsSdkDir WindowsSdkBinPath WindowsSdkVerBinPath WindowsLibPath WindowsSDKLibVersion WindowsSDKVersion UCRTVersion UniversalCRTSdkDir DevEnvDir EXTERNAL_INCLUDE __VSCMD_PREINIT_PATH __DOTNET_PREFERRED_BITNESS) do set %%v=
set "PATH=C:\Windows\system32;C:\Windows;C:\Windows\System32\WindowsPowerShell\v1.0"
cd /d "%APP%" || exit /b 1

"%PYTHON%" -X utf8 -B test_contract.py || exit /b 1

rem `airproj check` compiles every declared program, including the hand-run ones under
rem targets.check, and builds none of them.
"%AIR_TOOLCHAIN%\bin\airproj.exe" --project "%APP%" --toolchain "%AIR_TOOLCHAIN%" check || exit /b 1

rem Wording on screens: users are not developers. Only findings not in the baseline fail.
"%PYTHON%" -X utf8 "%AIR_ROOT%\tools\ui-text-check.py" "%APP%" --baseline tests\ui-text-baseline.txt || exit /b 1

if /i "%~1"=="--tests" (
  "%AIR_TOOLCHAIN%\bin\airproj.exe" --project "%APP%" --toolchain "%AIR_TOOLCHAIN%" test || exit /b 1
)
exit /b 0
