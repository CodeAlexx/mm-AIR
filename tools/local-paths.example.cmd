@echo off
rem Copy to local-paths.cmd and edit. Used by the build-windows-*.cmd and configure-gpu-tree.cmd scripts.
rem AIR_GPU_SOURCE: AIR checkout; AIR_GPU_BUILD: its NVIDIA-enabled CMake build tree.
set "MM_AIR_PYTHON_DIR=C:\Python313"
set "AIR_GPU_SOURCE=C:\AIR"
set "AIR_GPU_BUILD=C:\AIR\build-win-gpu"
set "CUDA_ROOT=C:\AIR\build-deps\cuda-13.3"
set "AIR_CUDNN_ROOT=C:\AIR\build-deps\cudnn-9.26.0.51\cudnn-windows-x86_64-9.26.0.51_cuda13-archive"
set "AIR_CUTLASS_ROOT=C:\AIR\build-deps\cutlass-f7b19de"
set "AIR_CK_ROOT=C:\AIR\build-deps\comfy-kitchen"
