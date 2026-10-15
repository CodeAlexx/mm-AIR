@echo off
rem Copy to local-paths.cmd and edit. Used by build-windows-app.cmd / build-windows-cli.cmd.
rem AIR_GPU_BUILD : CMake build tree of the AIR checkout configured with the NVIDIA provider
rem AIR_GPU_SOURCE: the AIR source directory that build tree was configured from
set "MM_AIR_PYTHON_DIR=C:\Python313"
set "AIR_GPU_BUILD=C:\AIR\build-win-nvidia-ninja"
set "AIR_GPU_SOURCE=C:\AIR"
set "CUDA_ROOT=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.3"
