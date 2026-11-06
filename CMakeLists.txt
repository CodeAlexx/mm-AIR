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
  # airproj is produced by a custom target, so TARGET_FILE is not a valid
  # generator expression for it.  Its owning CMake module publishes the
  # executable at this stable build-tree path.
  set(MM_AIR_AIRPROJ "${CMAKE_BINARY_DIR}/bin/airproj")
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
  # H3 inference (and its manifest writer) moved into stdlib/inference/h3.
  set(MM_AIR_H3_DEPENDENCY_PATH "../AIR/stdlib/inference/h3")
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
# Every manifest file name comes from the H3 deployment layout (the same file
# MM_AIR_H3_DEPLOYMENT names at run time): its "manifests" and
# "training_manifests" objects, which write_manifests.ai writes in full.
set(MM_AIR_H3_DEPLOYMENT_FILE
  "${CMAKE_CURRENT_SOURCE_DIR}/../../models/h3/presets/h3_deployment.json"
  CACHE FILEPATH "H3 deployment layout (schema air.inference.h3.deployment)")
set_property(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS
  "${MM_AIR_H3_DEPLOYMENT_FILE}")
file(READ "${MM_AIR_H3_DEPLOYMENT_FILE}" MM_AIR_H3_DEPLOYMENT_JSON)
# The manifests follow the model's own config (block counts, head regrouping, tower
# depths), so generation needs the H3 pipeline folder (the one with model_index.json).
set(MM_AIR_H3_MODEL_ROOT "" CACHE PATH "H3 pipeline folder (model_index.json)")
if(MM_AIR_H3_MODEL_ROOT STREQUAL "")
  message(FATAL_ERROR "Set MM_AIR_H3_MODEL_ROOT to the H3 pipeline folder (model_index.json)")
endif()
set(MM_AIR_H3_MANIFEST_NAMES)
foreach(manifest_group IN ITEMS manifests training_manifests)
  string(JSON manifest_count ERROR_VARIABLE manifest_error
    LENGTH "${MM_AIR_H3_DEPLOYMENT_JSON}" ${manifest_group})
  if(NOT manifest_error STREQUAL "NOTFOUND")
    message(FATAL_ERROR
      "${MM_AIR_H3_DEPLOYMENT_FILE}: key ${manifest_group} is required: ${manifest_error}")
  endif()
  math(EXPR manifest_last "${manifest_count} - 1")
  foreach(manifest_index RANGE ${manifest_last})
    string(JSON manifest_key MEMBER "${MM_AIR_H3_DEPLOYMENT_JSON}"
      ${manifest_group} ${manifest_index})
    string(JSON manifest_name GET "${MM_AIR_H3_DEPLOYMENT_JSON}"
      ${manifest_group} ${manifest_key})
    list(APPEND MM_AIR_H3_MANIFEST_NAMES "${manifest_name}")
  endforeach()
endforeach()
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
    "${MM_AIR_H3_DEPLOYMENT_FILE}" "${MM_AIR_H3_MODEL_ROOT}" "${MM_AIR_H3_MANIFEST_DIR}"
  DEPENDS ${MM_AIR_H3_MANIFEST_TOOL_DEPS} ${MM_AIR_H3_MANIFEST_SOURCES}
    "${MM_AIR_H3_DEPLOYMENT_FILE}"
  VERBATIM)
add_custom_target(mm_air_h3_manifests DEPENDS ${MM_AIR_H3_MANIFEST_OUTPUTS})

# Prompt Lab manifests are produced by its reusable AIR toolkit, beside the
# chosen compiler/runtime so the desktop worker can load exactly that ABI.
string(JSON MM_AIR_PROMPT_DEPENDENCY_PATH ERROR_VARIABLE MM_AIR_PROMPT_PATH_ERROR
  GET "${MM_AIR_PROJECT_JSON}" dependencies prompt path)
if(NOT MM_AIR_PROMPT_PATH_ERROR STREQUAL "NOTFOUND")
  message(FATAL_ERROR
    "Cannot read dependencies.prompt.path from ${MM_AIR_PROJECT_FILE}: ${MM_AIR_PROMPT_PATH_ERROR}")
endif()
get_filename_component(MM_AIR_PROMPT_SOURCE_DIR
  "${CMAKE_CURRENT_SOURCE_DIR}/${MM_AIR_PROMPT_DEPENDENCY_PATH}" ABSOLUTE)
if(NOT EXISTS "${MM_AIR_PROMPT_SOURCE_DIR}/write_manifests.ai")
  message(FATAL_ERROR "MM-Air's prompt dependency must provide write_manifests.ai")
endif()
if(MM_AIR_TOOLCHAIN)
  set(MM_AIR_PROMPT_MANIFEST_DIR_DEFAULT "${MM_AIR_TOOLCHAIN}/prompt-manifests")
else()
  set(MM_AIR_PROMPT_MANIFEST_DIR_DEFAULT "${CMAKE_BINARY_DIR}/prompt-manifests")
endif()
set(MM_AIR_PROMPT_MANIFEST_DIR "${MM_AIR_PROMPT_MANIFEST_DIR_DEFAULT}" CACHE PATH
  "Generated Qwen3-VL Prompt Engine manifest directory")
set(MM_AIR_PROMPT_MANIFEST_OUTPUTS
  "${MM_AIR_PROMPT_MANIFEST_DIR}/qwen-static.json"
  "${MM_AIR_PROMPT_MANIFEST_DIR}/qwen-static-8b.json"
  "${MM_AIR_PROMPT_MANIFEST_DIR}/qwen-static-32b.json"
  "${MM_AIR_PROMPT_MANIFEST_DIR}/qwen-layers.json"
  "${MM_AIR_PROMPT_MANIFEST_DIR}/qwen-layers-32b-i8.json"
  "${MM_AIR_PROMPT_MANIFEST_DIR}/qwen-vision-static.json"
  "${MM_AIR_PROMPT_MANIFEST_DIR}/qwen-vision-layers.json"
  "${MM_AIR_PROMPT_MANIFEST_DIR}/qwen-vision-layers-8b.json"
  "${MM_AIR_PROMPT_MANIFEST_DIR}/qwen-vision-layers-32b.json")
file(GLOB MM_AIR_PROMPT_MANIFEST_SOURCES CONFIGURE_DEPENDS
  "${MM_AIR_PROMPT_SOURCE_DIR}/*.ai")
file(GLOB MM_AIR_SEEDVR2_SOURCES CONFIGURE_DEPENDS
  "${CMAKE_SOURCE_DIR}/toolkits/seedvr2/*.ai")
add_custom_command(OUTPUT ${MM_AIR_PROMPT_MANIFEST_OUTPUTS}
  COMMAND ${CMAKE_COMMAND} -E make_directory "${MM_AIR_PROMPT_MANIFEST_DIR}"
  COMMAND "${MM_AIR_AIRC}" run
    "${MM_AIR_PROMPT_SOURCE_DIR}/write_manifests.ai"
    --mode release --cc "${CMAKE_C_COMPILER}" --
    "${MM_AIR_PROMPT_MANIFEST_DIR}"
  DEPENDS ${MM_AIR_TOOL_DEPS} ${MM_AIR_PROMPT_MANIFEST_SOURCES}
  VERBATIM)
add_custom_target(mm_air_prompt_manifests DEPENDS ${MM_AIR_PROMPT_MANIFEST_OUTPUTS})

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
          "${CMAKE_CURRENT_SOURCE_DIR}/movie_project.ai"
          "${CMAKE_CURRENT_SOURCE_DIR}/character_sheet.ai"
          "${CMAKE_CURRENT_SOURCE_DIR}/character_swap.ai"
          "${CMAKE_SOURCE_DIR}/toolkits/sam3/mask.ai"
          "${CMAKE_CURRENT_SOURCE_DIR}/masked_edit.ai"
          "${CMAKE_CURRENT_SOURCE_DIR}/masked_runtime.ai"
          "${CMAKE_CURRENT_SOURCE_DIR}/repair_runtime.ai"
          "${CMAKE_CURRENT_SOURCE_DIR}/seedvr2_post.ai"
          "${CMAKE_CURRENT_SOURCE_DIR}/prompt_lab.ai"
          ${MM_AIR_SEEDVR2_SOURCES}
          ${MM_AIR_H3_MANIFEST_SOURCES}
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
if(TARGET air_sam3_toolkit)
  add_dependencies(mm_air_desktop air_sam3_toolkit)
endif()
add_dependencies(mm_air_desktop mm_air_h3_manifests)
add_dependencies(mm_air_desktop mm_air_prompt_manifests)

find_package(Python3 REQUIRED COMPONENTS Interpreter)
add_test(NAME mm_air_contract
  COMMAND "${Python3_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/test_contract.py")
set_tests_properties(mm_air_contract PROPERTIES TIMEOUT 20)
