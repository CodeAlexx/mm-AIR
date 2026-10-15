@echo off
rem Configure and build AIR's NVIDIA GPU tree (compiler, runtime, providers, UI host) with x64 MSVC.
setlocal
if not exist "%~dp0local-paths.cmd" (echo Create tools\local-paths.cmd from local-paths.example.cmd & exit /b 1)
call "%~dp0local-paths.cmd"
for %%v in (INCLUDE LIB LIBPATH Platform VSCMD_ARG_TGT_ARCH VSCMD_ARG_HOST_ARCH VSCMD_ARG_app_plat VSCMD_VER VSINSTALLDIR VCINSTALLDIR VCToolsInstallDir VCToolsVersion VCIDEInstallDir VS170COMNTOOLS WindowsSdkDir WindowsSdkBinPath WindowsSdkVerBinPath WindowsLibPath WindowsSDKLibVersion WindowsSDKVersion UCRTVersion UniversalCRTSdkDir DevEnvDir EXTERNAL_INCLUDE __VSCMD_PREINIT_PATH __DOTNET_PREFERRED_BITNESS) do set %%v=
set PATH=C:\Windows\system32;C:\Windows;C:\Windows\System32\WindowsPowerShell\v1.0;%MM_AIR_PYTHON_DIR%
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul 2>&1 || exit /b 1
where cl | findstr /i "Hostx64\x64" >nul || (echo wrong cl & exit /b 1)
set VSCMAKE=C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake
set PATH=%VSCMAKE%\Ninja;%VSCMAKE%\CMake\bin;%CUDA_ROOT%\bin;%CUDA_ROOT%\bin\x64;C:\NVIDIA-Runtime\cuda-13.3-cudnn-9.26;%PATH%
cmake -S "%AIR_GPU_SOURCE%" -B "%AIR_GPU_BUILD%" -G Ninja -DCMAKE_BUILD_TYPE=Release ^
  -DAIR_WINDOWS_COMPILER=ON -DAIR_WINDOWS_NVIDIA=ON -DAIR_DESKTOP=ON -DAIR_SAM3=OFF ^
  -DCMAKE_DISABLE_FIND_PACKAGE_CUDAToolkit=FALSE "-DCUDAToolkit_ROOT=%CUDA_ROOT%" ^
  "-DCMAKE_CUDA_COMPILER=%CUDA_ROOT%\bin\nvcc.exe" -DCMAKE_CUDA_ARCHITECTURES=120 -DAIR_CK_TARGET_SM=120 ^
  "-DAIR_CK_ROOT=%AIR_CK_ROOT%" "-DAIR_CUTLASS_ROOT=%AIR_CUTLASS_ROOT%" "-DAIR_CUDNN_ROOT=%AIR_CUDNN_ROOT%" ^
  "-DPython3_EXECUTABLE=%MM_AIR_PYTHON_DIR%\python.exe" "-DAIR_SQLITE3_DLL=%MM_AIR_PYTHON_DIR%\DLLs\sqlite3.dll" || exit /b 1
if "%~1"=="" (echo configured & exit /b 0)
cmake --build "%AIR_GPU_BUILD%" --target %* || exit /b 1
echo BUILD OK
