#!/usr/bin/env python3
"""Static acceptance contract for the first MM-AIR native desktop surface."""
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
AIR_ROOT = ROOT.parents[1]
UI = ROOT / "desktop.ui"
CSS = ROOT / "desktop.css"
MAIN = ROOT / "main.ai"
GENERATE = ROOT / "generate.ai"
CHARACTER_SHEET = ROOT / "character_sheet.ai"
CHARACTER_SWAP = ROOT / "character_swap.ai"
MASKED_EDIT = ROOT / "masked_edit.ai"
MASKED_RUNTIME = ROOT / "masked_runtime.ai"
OUTPAINT = ROOT / "outpaint.ai"
OUTPAINT_RUNTIME = ROOT / "outpaint_runtime.ai"
PROMPT_LAB = ROOT / "prompt_lab.ai"
SAM3_ROOT = AIR_ROOT / "toolkits/sam3"
AUTO_MASK = SAM3_ROOT / "mask.ai"
SAM3_NATIVE = SAM3_ROOT / "native/air_sam3.cpp"
SAM3_EXPORTS = SAM3_ROOT / "native/air_sam3.map"
MOVIE_PROJECT = ROOT / "movie_project.ai"
APP_CMAKE = ROOT / "CMakeLists.txt"
SAM3_CMAKE = SAM3_ROOT / "CMakeLists.txt"

tree = ET.parse(UI)
objects = tree.findall(".//object")
ids = [node.attrib["id"] for node in objects if "id" in node.attrib]
assert len(ids) == len(set(ids)), "GtkBuilder IDs must be unique"

for selector in ("h3_profile_list", "h3_projection_list", "h3_attention_list"):
    model = tree.find(f".//object[@id='{selector}']")
    assert model is not None, selector
    first = model.find("./items/item")
    assert first is not None and first.text.startswith("Select "), (
        f"{selector} must fail closed instead of selecting runtime policy")

for selector in ("gen_conditioner_projection", "gen_transformer_projection",
                 "gen_attention"):
    assert tree.find(f".//object[@id='{selector}']") is not None, selector

assert [item.text for item in tree.findall(
    ".//object[@id='qwen_image_resolution_list']/items/item")] == [
    "1:1 · 2048×2048", "4:3 · 2400×1792", "3:4 · 1792×2400",
    "3:2 · 2528×1696", "2:3 · 1696×2528", "16:9 · 2752×1536",
    "9:16 · 1536×2752", "Custom"]
assert [item.text for item in tree.findall(
    ".//object[@id='qwen_image_scheduler_list']/items/item")] == [
    "Creator Dynamic Flow", "Linear Flow · native alternate"]
assert [item.text for item in tree.findall(
    ".//object[@id='qwen_image_sampler_list']/items/item")] == [
    "Euler", "DPM++ 2M · native alternate"]

for control in ("gen_qwen_sampling", "qwen_image_resolution",
                "qwen_image_scheduler", "qwen_image_sampler",
                "qwen_image_steps"):
    assert tree.find(f".//object[@id='{control}']") is not None, control

for control in ("gen_krea_sampling", "krea_resolution", "krea_scheduler",
                "krea_sampler", "krea_steps"):
    assert tree.find(f".//object[@id='{control}']") is not None, control

for h3_only in ("gen_h3_core_group", "gen_h3_geometry_group",
                "gen_h3_runtime_group"):
    assert tree.find(f".//object[@id='{h3_only}']") is not None, h3_only

for common in ("gen_seed_group", "gen_output_summary_group", "gen_output_group"):
    assert tree.find(f".//object[@id='{common}']") is not None, common

assert "qwen_image_contract.resolution(qwen_image_resolution_index)" in MAIN.read_text()
assert "if qwen_image_resolution_index==0" not in MAIN.read_text(), (
    "Qwen resolution geometry must come from the AIR model contract")

for frame_picker in ("choose_reference", "choose_last_reference"):
    assert tree.find(f".//object[@id='{frame_picker}']") is not None, frame_picker

# Every primary media-ingress control must retain the native drop-target class.
# This guards the picker-only regression while still allowing click-to-browse.
for drop_target in (
    "gen_swap_choose_source", "gen_swap_add_character", "gen_add_visual",
    "gen_add_audio", "choose_reference", "choose_last_reference",
    "choose_opening", "choose_ending", "movie_add_reference",
    "movie_add_character",
    "edit_choose_source", "qwen_edit_choose_source", "gen_add_lora",
):
    widget = tree.find(f".//object[@id='{drop_target}']")
    assert widget is not None, drop_target
    assert widget.find("./style/class[@name='drop-target']") is not None, (
        f"{drop_target} must accept native file drops")

ui = UI.read_text()
css = CSS.read_text()
main = MAIN.read_text()
generate = GENERATE.read_text()
h3_deployment = (AIR_ROOT / "stdlib/inference/h3/deployment.ai").read_text()
character_sheet = CHARACTER_SHEET.read_text()
character_swap = CHARACTER_SWAP.read_text()
masked_edit = MASKED_EDIT.read_text()
masked_runtime = MASKED_RUNTIME.read_text()
outpaint = OUTPAINT.read_text()
outpaint_runtime = OUTPAINT_RUNTIME.read_text()
prompt_lab = PROMPT_LAB.read_text()
auto_mask = AUTO_MASK.read_text()
sam3_native = SAM3_NATIVE.read_text()
sam3_exports = SAM3_EXPORTS.read_text()
movie_project = MOVIE_PROJECT.read_text()
app_cmake = APP_CMAKE.read_text()
sam3_cmake = SAM3_CMAKE.read_text()

assert "PNG / JPEG / WebP" in ui
assert "PNG/JPEG/WebP images or videos" in ui
assert "parameters.qwen_condition_image" in main
assert "ordered Qwen Image Edit images · PNG, JPEG, or WebP" in main
assert "ordered Qwen Image Edit PNGs" not in main

# Model switching and parameter search share one complete-group visibility
# policy.  Keep model_widgets from growing a second, drifting list of toggles.
model_widgets_source = main[main.index("fn model_widgets"):main.index("fn clear_swap_source_ui")]
assert 'filter_parameters(session,"",model,swap_mode)' in model_widgets_source
for group in ("gen_seed_group", "gen_h3_core_group", "gen_krea_sampling",
              "gen_qwen_sampling",
              "gen_h3_geometry_group", "gen_output_summary_group",
              "gen_sources_group", "gen_h3_runtime_group", "gen_output_group"):
    assert f'"{group}","visible"' not in model_widgets_source, (
        f"{group} visibility must be owned only by filter_parameters")

# Each model owns an explicit sampling panel. This catches the prior regression
# where Krea's steps, sampler, scheduler and resolution disappeared from the UI.
filter_source = main[main.index("fn filter_parameters"):main.index("fn model_widgets")]
assert '"gen_krea_sampling","visible",krea' in filter_source
for control in ("krea_resolution", "krea_scheduler", "krea_sampler", "krea_steps"):
    assert tree.find(f".//object[@id='{control}']") is not None
for control in ("qwen_image_resolution", "qwen_image_scheduler",
                "qwen_image_sampler", "qwen_image_steps"):
    assert tree.find(f".//object[@id='{control}']") is not None

# Generate layout and controls must not shift or silently regress by model.
rail = tree.find(".//object[@id='gen_parameter_scroll']")
assert rail is not None
props = {p.attrib.get("name"): p.text for p in rail.findall("property")}
assert props.get("width-request") == "300"
assert props.get("min-content-width") == "300"
assert props.get("max-content-width") == "300"
duration = tree.find(".//object[@id='gen_duration']")
assert duration is not None and duration.find("property[@name='digits']").text == "3"
duration_adjustment = tree.find(".//object[@id='gen_duration_adjustment']")
duration_props = {p.attrib.get("name"): p.text for p in duration_adjustment.findall("property")}
assert float(duration_props["lower"]) <= 4/24+1e-12
assert float(duration_props["upper"]) >= 4294967295/24
assert float(duration_props["step-increment"]) <= 1/24+1e-12
expected_h3_defaults = {
    "gen_task": "0", "gen_profile": "2",
    "gen_conditioner_projection": "1",
    "gen_transformer_projection": "2", "gen_attention": "4",
}
for control, expected in expected_h3_defaults.items():
    widget = tree.find(f".//object[@id='{control}']")
    assert widget is not None
    assert widget.find("property[@name='selected']").text == expected

# Qwen edit must expose the creator-supported ordered 1..10 source path and
# selectable generation settings; fixed seed-42 recipe text is forbidden.
for control in ("qwen_edit_references", "qwen_edit_remove_source",
                "qwen_edit_clear_sources", "qwen_edit_resolution",
                "qwen_edit_scheduler", "qwen_edit_sampler", "qwen_edit_steps",
                "qwen_edit_seed", "qwen_edit_seed_randomize", "qwen_edit_seed_lock",
                "qwen_edit_width", "qwen_edit_height", "movie_width", "movie_height"):
    assert tree.find(f".//object[@id='{control}']") is not None, control
assert "2048×2048 · 40 steps · seed 42" not in ui
assert "run_request_images_configured" in generate
assert "array.len(qwen_edit_references)>=10" in main
for seed_id in ("gen_seed", "qwen_edit_seed"):
    seed_widget = tree.find(f".//object[@id='{seed_id}']")
    assert seed_widget.find("property[@name='text']").text == "Random"
for lock_id in ("gen_seed_lock", "qwen_edit_seed_lock"):
    lock_widget = tree.find(f".//object[@id='{lock_id}']")
    active = lock_widget.find("property[@name='active']")
    assert active is None or active.text == "false"
assert "and not seed_locked" in main
assert "if not qwen_edit_seed_locked" in main

# Results are image-first and actionable: no filename/path labels, expanded
# preview on click, and recoverable Trash removal.
for control in ("result_fullscreen", "result_fullscreen_picture",
                "result_fullscreen_close", "gen_delete_result"):
    assert tree.find(f".//object[@id='{control}']") is not None, control
assert 'codec.field_text(command,"label","")' in main
assert 'desktop_files.trash_file' in main
assert 'proc.check(["gio","trash"' not in main

# Sending an image-model result to H3 must restore H3's independently saved
# geometry. Qwen and Krea resolutions belong to their source generation only.
use_as_h3 = main[main.index('if id == "gen_use_image_reference"'):
                 main.index('if id == "gen_visual_earlier"')]
assert 'model_index == parameters.krea_model_index() or' in use_as_h3
assert 'model_index == parameters.qwen_image_model_index()' in use_as_h3
for assignment in (
    'width = saved_h3_width', 'height = saved_h3_height',
    'seconds = saved_h3_seconds', 'resolution_index = saved_h3_resolution',
):
    assert assignment in use_as_h3, (
        f"Use-as-H3-reference must restore H3 state: {assignment}")
assert 'geometry_widgets(session,width,height,seconds,false,false)' in use_as_h3, (
    "Use-as-H3-reference must refresh the visible output after H3 owns the UI")

# The creator decoder bundle preserves selected F32 tensors that are not in
# the official FP16 encoder source. Keep those two checkpoint lifetimes and
# paths distinct at the in-process H3 session boundary.
assert 'h3_deployment.sources(deployment_roots' in generate
assert 'video_vae_checkpoint: joined(str.view(checkpoint_root), "video_vae/source/model.safetensors")' in h3_deployment
assert 'video_decoder_aux_checkpoint: joined(str.view(donor_root), "shared/video-vae/derived-fp16.safetensors")' in h3_deployment

# Rebuilding the external AIR toolchain provider must invalidate MM-Air's
# custom command so airc republishes the matching provider beside the binary.
for artifact in (
    "${MM_AIR_TOOLCHAIN}/runtime/libair_rt.a",
    "${MM_AIR_TOOLCHAIN}/providers/nvidia/libair_gpu_nvidia.so",
):
    assert artifact in app_cmake, f"missing MM-Air toolchain dependency: {artifact}"
assert "list(APPEND MM_AIR_TOOL_DEPS air_gpu_nvidia)" in app_cmake

for page in ("generate", "edit", "movie", "control", "prompt"):
    assert f"<property name=\"name\">{page}</property>" in ui
    assert f'"{page}"' in main

for required in (
    "MiniMax H3", "Generate H3 MP4", "Movie Maker",
    "Queue H3 take", "H3 Union ControlNet", "Stage H3 CT Request",
    "CK-INT8", "ConvRot INT8", "Donor hybrid", "24 FPS", "832×480",
    "16:9 · 1344×768", "SeedVR2 3B", "SeedVR2 7B",
    "Current Generations", "Continuity spine",
    "Prompt lab", "Qwen3-VL 4B", "Send to Generate",
    "Send to Movie Maker", "Save to History", "prompt_cancel",
    "H3 character sheet", "4 panels · faster · 3 seconds",
    "6 panels · full orbit · 5 seconds", "Anime to photoreal",
    "Character Swap", "Source Video · motion, timing, camera, staging",
    "Reference Character · identity pictures", "Build / Rebuild Prompt",
    "Open in Prompt Lab / Director", "Replace selected subject",
    "Masked Character Swap", "Preserve Outside Mask", "Preview tracked crop",
    "Localized image and video edits", "Qwen Analyze", "Build Edit Prompt",
    "Run Localized Edit", "Send to Edit", "Character Replace · no mask required",
    "Video Outpaint", "16:9 → 9:16", "9:16 → 16:9",
    "Preview Geometry", "Preview First Window", "Run Full Outpaint",
    "Exact Source", "Blended", "Window seconds", "Overlap seconds",
    "Run Qwen Director pass", "Render all shots", "Continue selected take",
    "Stitch movie", "Project bibles", "Continuity spine",
):
    assert required in ui, required

assert [item.text for item in tree.findall(".//object[@id='gen_model_list']/items/item")] == [
    "MiniMax H3 Base", "MiniMax H3 Reference", "Krea 2 Turbo", "Qwen-Image-2.1"]
assert [item.text for item in tree.findall(".//object[@id='h3_resolution_list']/items/item")] == [
    "16:9 · 1344×768", "21:9 · 1536×672", "4:3 · 1024×768",
    "1:1 · 768×768", "3:4 · 768×1024", "9:16 · 768×1344",
    "Donor · 832×480", "Custom"]
assert [item.text for item in tree.findall(".//object[@id='seedvr2_method_list']/items/item")] == [
    "SeedVR2 3B", "SeedVR2 7B"]
assert 'krea_session.run_to_png' in generate
assert 'task.spawn(work,fn=generation.run_krea)' in main
assert 'desk.clear_video(session,"result_video")' in main
assert 'gen_use_image_reference' in main
assert 'task.spawn(work,fn=prompt_lab.run)' in main
assert 'prompt_lab.cancel' in main
assert 'mm_air_prompt_manifests' in app_cmake
assert 'Cancelling Qwen; H3 remains blocked until teardown completes' in main
for widget in ("gen_character_sheet_mode", "gen_character_sheet_style",
               "gen_character_sheet_apply"):
    assert tree.find(f".//object[@id='{widget}']") is not None, widget
assert 'character_sheet.prompt' in main
assert 'character_sheet.from_video' in generate
assert '13c095e84c6d651d49ddcbdb672779cc66a7d44d' in character_sheet
assert '[2,24,45,68]' in character_sheet
assert '[2,21,42,63,84,113]' in character_sheet
assert 'let gutter: u64 = 6' in character_sheet
assert [item.text for item in tree.findall(".//object[@id='gen_mode_list']/items/item")] == [
    "Standard", "Character Swap", "Masked Character Swap"]
for widget in (
    "gen_mode", "gen_swap_fields", "gen_swap_choose_source",
    "gen_swap_source_preview", "gen_swap_source_metadata",
    "gen_swap_add_character", "gen_swap_character_refs", "gen_swap_target",
    "gen_swap_target_notes", "gen_swap_notes", "gen_swap_qwen_model",
    "gen_swap_build_prompt", "gen_swap_open_prompt", "gen_swap_clear",
    "gen_masked_fields", "gen_mask_choose", "gen_mask_preserve",
    "gen_mask_feather", "gen_mask_cleanup", "gen_mask_expand",
    "gen_mask_crop_strategy", "gen_mask_preview_crop", "gen_mask_send_edit",
):
    assert tree.find(f".//object[@id='{widget}']") is not None, widget
for widget in (
    "prompt_total_seconds", "prompt_window_seconds", "prompt_overlap_seconds",
    "prompt_build_plan", "prompt_window_report",
):
    assert tree.find(f".//object[@id='{widget}']") is not None, widget
assert 'prompt_lab.scene_instruction' in main
assert 'director.scene_plan_instruction' in prompt_lab
assert 'Current Generate remains one native H3 latent' in ui
assert 'prompt.Task.CharacterSwap' in character_swap
assert 'prompt.attachment(source_video,prompt.AttachmentKind.Video,1)' in character_swap
assert 'prompt.AttachmentKind.Image,index+1' in character_swap
assert 'character_swap.h3_references' in main
assert 'Cancelling Qwen; H3 remains blocked until teardown completes' in main
assert 'swap_prompt_built' in main
assert 'Character Swap prompt needs all six official Ref2VA sections' in character_swap
for widget in (
    "nav_edit", "edit_choose_source", "edit_choose_mask", "edit_draw_mask",
    "edit_brush", "edit_erase_mask", "edit_clear_paint", "edit_references",
    "edit_source_picture", "edit_source_video", "edit_mask_overlay", "edit_mask_video",
    "edit_timeline", "edit_mask_visible", "edit_crop_preview", "edit_mode",
    "edit_prompt", "edit_crop_strategy", "edit_qwen_analyze",
    "edit_auto_mask_prompt", "edit_auto_mask",
    "edit_build_prompt", "edit_preview_crop", "edit_run", "edit_save_as",
    "prompt_send_edit",
    "edit_outpaint_fields", "edit_outpaint_preset", "edit_outpaint_width",
    "edit_outpaint_height", "edit_outpaint_direction", "edit_outpaint_anchor",
    "edit_outpaint_composite", "edit_outpaint_seam", "edit_outpaint_window",
    "edit_outpaint_overlap", "edit_outpaint_preview_geometry",
    "edit_outpaint_preview_window", "edit_outpaint_geometry_status",
    "edit_repair_fields", "edit_repair_start", "edit_repair_end",
    "edit_repair_handle_before", "edit_repair_handle_after",
    "edit_repair_dilation", "edit_repair_cuts", "edit_repair_memory",
    "edit_repair_window", "edit_repair_overlap", "edit_repair_preview",
    "edit_repair_report",
    "edit_motion_plan_fields", "edit_motion_heatmap", "edit_motion_add_span",
    "edit_motion_clear", "edit_motion_import", "edit_motion_export",
    "edit_timing_mode", "edit_timing_block_lo", "edit_timing_block_hi",
    "edit_timing_fade", "edit_timing_step_lo", "edit_timing_step_hi",
):
    assert tree.find(f".//object[@id='{widget}']") is not None, widget
assert [item.text for item in tree.findall(".//object[@id='edit_mode_list']/items/item")] == [
    "Image Edit", "Video Edit", "Character Replace · no mask",
    "Masked Character Replace", "Prompt-guided Local Edit", "Video Outpaint",
    "Repair Frames", "Motion Repair"]
assert tree.find(".//object[@id='edit_mode']/property[@name='selected']").text == "2"
assert 'character_swap.masked_request' in main
assert 'character_swap.local_image_request' in main
assert 'character_swap.image_replace_request' in main
assert 'character_swap.edit_character_replace(edit_mode)' in main
assert 'generation_mode=if character_swap.edit_character_replace(edit_mode)' in main
assert 'character_swap.validate_local_image_prompt' in main
assert 'generation.enable_masked' in main
assert 'masked_runtime.prepare' in main
assert 'masked_runtime.finish' in generate
assert 'edit.map_to_h3' in masked_runtime
assert 'edit.composite_rgb' in masked_runtime
assert 'edit.painted' in masked_runtime
assert 'source_video:source_video' in masked_runtime
assert '"-c:v","png"' in masked_runtime
assert 'desk.seek(session,"edit_source_video"' in main
assert 'desk.mask_paint(session,"edit_canvas"' in main
assert 'task.spawn(work,fn=auto_mask.run)' in main
assert 'automask.mask_media' in auto_mask
assert '"-vf","fps=24"' in auto_mask
assert 'the host application stayed open' in auto_mask
assert 'catch (const std::bad_alloc &)' in sam3_native
assert 'MM-Air automatic mask ready' in main
assert 'libair_sam3.so' in main
assert 'PABannier/sam3.cpp.git' in sam3_cmake
assert '01832ef85fcc8eb6488f1d01cd247f07e96ff5a9' in sam3_cmake
assert '--version-script=${AIR_SAM3_VERSION_SCRIPT}' in sam3_cmake
assert 'LINKER:-Bsymbolic' in sam3_cmake
assert re.search(r'global:\s*air_sam3_mask_media;\s*local:\s*\*;', sam3_exports)
assert 'no full-frame fallback' in main
assert 'prompt_types.Task.Outpaint' in outpaint
assert 'outpaint.prompt_request' in main
assert 'generation.enable_repair' in main
assert 'repair_plan.build' in main
assert 'repair_runtime.finish' in generate
assert 'outside frames exact' in generate
assert 'generation.enable_timing' in main
assert 'generation.enable_outpaint' in main
assert 'outpaint_runtime.preview' in main
assert 'outpaint_runtime.stitch' in generate
assert 'masked.prepare' in outpaint_runtime
assert 'source_audio_preserved' in outpaint
assert 'decoded-tail-reference' in generate
for widget in (
    "new_project", "import_project", "export_project", "export_edit",
    "movie_shot_list", "movie_take_list", "add_shot", "duplicate_shot",
    "delete_shot", "prepare_director", "copy_request", "queue_take",
    "render_all", "continue_take", "assemble_movie", "choose_opening",
    "choose_ending", "movie_reference_list", "movie_project_list",
    "delete_project", "movie_cast_list", "movie_add_character",
    "movie_remove_character", "movie_endless_start", "movie_endless_stop",
    "movie_drift_enabled", "movie_drift_matched", "movie_drift_taper",
    "movie_drift_amount",
):
    assert tree.find(f".//object[@id='{widget}']") is not None, widget
assert 'serenity.h3.movie.v1' in movie_project
assert 'pub fn load(filename:str)' in movie_project
assert 'pub fn record_take_at' in movie_project
assert 'pub fn stitch(project:ref<Project>' in movie_project
assert 'pub fn effective_references' in movie_project
assert 'pub fn create_continuation' in movie_project
assert '.airh3ctx' in movie_project
assert 'generation.enable_motion_context' in main
assert 'generation.enable_drift_control' in main
assert 'movie.record_take_at' in main
assert 'movie.stitch' in main
assert 'desk.activate(session,"queue_take")' in main
assert 'id == "prepare_director"' in main
assert 'task.spawn(work,fn=prompt_lab.run)' in main
for excluded in ("Klein", "Flux", "SDXL", "Z-Image", "Wan"):
    assert not re.search(rf"\b{re.escape(excluded)}\b", ui, re.IGNORECASE), excluded

for token in ("#16181b", "#1c1f23", "#23272c", "#30353b", "#e3e5e8", "#6f94c8"):
    assert token in css, token

print("MM-AIR desktop contract: native Generate/Edit/Movie workflows, unique IDs, source palette PASS")
