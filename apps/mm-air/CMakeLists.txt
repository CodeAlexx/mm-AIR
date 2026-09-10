if(NOT AIR_DESKTOP)
  return()
endif()

set(MM_AIR_BUILD_DIR "${CMAKE_BINARY_DIR}/mm-air")
set(MM_AIR_BIN "${CMAKE_BINARY_DIR}/bin/mm-air")
set(MM_AIR_SHARE "${CMAKE_BINARY_DIR}/share/mm-air")
set(MM_AIR_TOOLCHAIN "" CACHE PATH
  "Built AIR toolchain used to compile MM-Air and resolve its AIR H3 package")
if(AIR_SANITIZE)
  set(MM_AIR_RUNTIME air_rt_native)
else()
  set(MM_AIR_RUNTIME air_rt)
endif()

if(MM_AIR_TOOLCHAIN)
  set(MM_AIR_AIRC "${MM_AIR_TOOLCHAIN}/bin/airc")
  set(MM_AIR_AIRPROJ "${MM_AIR_TOOLCHAIN}/bin/airproj")
  set(MM_AIR_TOOLCHAIN_RUNTIME
    "${MM_AIR_TOOLCHAIN}/runtime/libair_rt.a")
  set(MM_AIR_TOOLCHAIN_NVIDIA_PROVIDER
    "${MM_AIR_TOOLCHAIN}/providers/nvidia/libair_gpu_nvidia.so")
  if(NOT EXISTS "${MM_AIR_AIRC}" OR NOT EXISTS "${MM_AIR_AIRPROJ}")
    message(FATAL_ERROR
      "MM_AIR_TOOLCHAIN must contain bin/airc and bin/airproj")
  endif()
  if(NOT EXISTS "${MM_AIR_TOOLCHAIN_RUNTIME}" OR
     NOT EXISTS "${MM_AIR_TOOLCHAIN_NVIDIA_PROVIDER}")
    message(FATAL_ERROR
      "MM_AIR_TOOLCHAIN must contain the AIR runtime and NVIDIA provider")
  endif()
  set(MM_AIR_TOOL_DEPS
    "${MM_AIR_AIRC}"
    "${MM_AIR_AIRPROJ}"
    "${MM_AIR_TOOLCHAIN_RUNTIME}"
    "${MM_AIR_TOOLCHAIN_NVIDIA_PROVIDER}")
  set(MM_AIR_TOOLCHAIN_ARGS --toolchain "${MM_AIR_TOOLCHAIN}")
else()
  set(MM_AIR_AIRC "$<TARGET_FILE:airc>")
  set(MM_AIR_AIRPROJ "$<TARGET_FILE:airproj>")
  set(MM_AIR_TOOL_DEPS airc airproj)
  if(TARGET air_gpu_nvidia)
    list(APPEND MM_AIR_TOOL_DEPS air_gpu_nvidia)
  endif()
  set(MM_AIR_TOOLCHAIN_ARGS)
endif()

# The linked H3 package owns the checkpoint-manifest declarations. Resolve its
# source from the same dependency declaration that airproj consumes instead of
# maintaining the package path a second time in CMake. Generate the runtime JSON
# beside the selected AIR toolchain, which is also the documented
# MM_AIR_H3_MANIFEST_ROOT. Keeping every produced file as an output makes a
# missing newly-added manifest rebuild this target instead of surviving until a
# Generate request reaches the offloader.
set(MM_AIR_PROJECT_FILE "${CMAKE_CURRENT_SOURCE_DIR}/air.project.json")
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
  "${MM_AIR_PROJECT_FILE}")
file(READ "${MM_AIR_PROJECT_FILE}" MM_AIR_PROJECT_JSON)
string(JSON MM_AIR_H3_DEPENDENCY_PATH ERROR_VARIABLE MM_AIR_H3_PATH_ERROR
  GET "${MM_AIR_PROJECT_JSON}" dependencies h3 path)
if(NOT MM_AIR_H3_PATH_ERROR STREQUAL "NOTFOUND")
  message(FATAL_ERROR
    "Cannot read dependencies.h3.path from ${MM_AIR_PROJECT_FILE}: ${MM_AIR_H3_PATH_ERROR}")
endif()
get_filename_component(MM_AIR_H3_SOURCE_DIR
  "${CMAKE_CURRENT_SOURCE_DIR}/${MM_AIR_H3_DEPENDENCY_PATH}" ABSOLUTE)
if(NOT EXISTS "${MM_AIR_H3_SOURCE_DIR}/write_manifests.ai")
  message(FATAL_ERROR
    "MM-Air's H3 path dependency must provide write_manifests.ai")
endif()
if(MM_AIR_TOOLCHAIN)
  set(MM_AIR_H3_MANIFEST_DIR_DEFAULT "${MM_AIR_TOOLCHAIN}/h3-manifests")
  set(MM_AIR_H3_MANIFEST_TOOL_DEPS ${MM_AIR_TOOL_DEPS})
else()
  set(MM_AIR_H3_MANIFEST_DIR_DEFAULT "${CMAKE_BINARY_DIR}/h3-manifests")
  set(MM_AIR_H3_MANIFEST_TOOL_DEPS ${MM_AIR_TOOL_DEPS} ${MM_AIR_RUNTIME}
    $<TARGET_FILE:${MM_AIR_RUNTIME}>)
endif()
set(MM_AIR_H3_MANIFEST_DIR "${MM_AIR_H3_MANIFEST_DIR_DEFAULT}" CACHE PATH
  "Generated H3 manifest directory used by MM_AIR_H3_MANIFEST_ROOT")
set(MM_AIR_H3_MANIFEST_NAMES
  h3-token-refiner-bf16.json
  h3-transformer-denoiser-static.json
  h3-blocks-bf16.json
  h3-blocks-convrot.json
  h3-modulation-cache.json
  h3-video-vae-encoder.json
  h3-video-vae-decoder-aux.json
  h3-video-vae-decoder-convrot.json
  h3-audio-vae.json
  h3-audio-encoder.json
  h3-qwen-static.json
  h3-qwen-layers-bf16.json
  h3-qwen-norms-bf16.json
  h3-qwen-convrot-i8.json
  h3-vision-static.json
  h3-vision-layers.json)
set(MM_AIR_H3_MANIFEST_OUTPUTS)
foreach(manifest_name IN LISTS MM_AIR_H3_MANIFEST_NAMES)
  list(APPEND MM_AIR_H3_MANIFEST_OUTPUTS
    "${MM_AIR_H3_MANIFEST_DIR}/${manifest_name}")
endforeach()
file(GLOB MM_AIR_H3_MANIFEST_SOURCES CONFIGURE_DEPENDS
  "${MM_AIR_H3_SOURCE_DIR}/*.ai")
add_custom_command(OUTPUT ${MM_AIR_H3_MANIFEST_OUTPUTS}
  COMMAND ${CMAKE_COMMAND} -E make_directory "${MM_AIR_H3_MANIFEST_DIR}"
  COMMAND "${MM_AIR_AIRC}" run
    "${MM_AIR_H3_SOURCE_DIR}/write_manifests.ai"
    --mode release --cc "${CMAKE_C_COMPILER}" --
    "${MM_AIR_H3_MANIFEST_DIR}"
  DEPENDS ${MM_AIR_H3_MANIFEST_TOOL_DEPS} ${MM_AIR_H3_MANIFEST_SOURCES}
  VERBATIM)
add_custom_target(mm_air_h3_manifests DEPENDS ${MM_AIR_H3_MANIFEST_OUTPUTS})

add_custom_command(OUTPUT "${MM_AIR_BIN}"
  COMMAND ${CMAKE_COMMAND} -E make_directory "${MM_AIR_BUILD_DIR}"
  COMMAND "${MM_AIR_AIRPROJ}" --project "${CMAKE_CURRENT_SOURCE_DIR}"
    ${MM_AIR_TOOLCHAIN_ARGS} check
  COMMAND "${MM_AIR_AIRC}" build "${CMAKE_CURRENT_SOURCE_DIR}/main.ai"
    -o "${MM_AIR_BIN}" --mode release
    --cc "${CMAKE_C_COMPILER}"
    --depfile "${MM_AIR_BUILD_DIR}/main.d"
    --report "${MM_AIR_BUILD_DIR}/build.json"
  DEPENDS ${MM_AIR_TOOL_DEPS} ${MM_AIR_RUNTIME} $<TARGET_FILE:${MM_AIR_RUNTIME}>
          "${CMAKE_CURRENT_SOURCE_DIR}/air.project.json"
          "${CMAKE_CURRENT_SOURCE_DIR}/air.lock.json"
          "${CMAKE_CURRENT_SOURCE_DIR}/main.ai"
          "${CMAKE_CURRENT_SOURCE_DIR}/generate.ai"
  DEPFILE "${MM_AIR_BUILD_DIR}/main.d"
  BYPRODUCTS "${MM_AIR_BUILD_DIR}/build.json"
  VERBATIM)

add_custom_command(OUTPUT "${MM_AIR_SHARE}/desktop.ui" "${MM_AIR_SHARE}/desktop.css"
  COMMAND ${CMAKE_COMMAND} -E make_directory "${MM_AIR_SHARE}"
  COMMAND ${CMAKE_COMMAND} -E copy_if_different
          "${CMAKE_CURRENT_SOURCE_DIR}/desktop.ui" "${MM_AIR_SHARE}/desktop.ui"
  COMMAND ${CMAKE_COMMAND} -E copy_if_different
          "${CMAKE_CURRENT_SOURCE_DIR}/desktop.css" "${MM_AIR_SHARE}/desktop.css"
  DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/desktop.ui"
          "${CMAKE_CURRENT_SOURCE_DIR}/desktop.css"
  VERBATIM)

add_custom_target(mm_air_desktop DEPENDS "${MM_AIR_BIN}"
  "${MM_AIR_SHARE}/desktop.ui" "${MM_AIR_SHARE}/desktop.css")
add_dependencies(mm_air_desktop air_ui)
add_dependencies(mm_air_desktop mm_air_h3_manifests)

find_package(Python3 REQUIRED COMPONENTS Interpreter)
add_test(NAME mm_air_contract
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/test_contract.py")
set_tests_properties(mm_air_contract PROPERTIES TIMEOUT 20)
