#!/usr/bin/env python3
"""Static acceptance contract for the first MM-AIR native desktop surface."""
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
UI = ROOT / "desktop.ui"
CSS = ROOT / "desktop.css"
MAIN = ROOT / "main.ai"
GENERATE = ROOT / "generate.ai"
CMAKE = ROOT / "CMakeLists.txt"

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

for frame_picker in ("choose_reference", "choose_last_reference"):
    assert tree.find(f".//object[@id='{frame_picker}']") is not None, frame_picker

ui = UI.read_text()
css = CSS.read_text()
main = MAIN.read_text()
generate = GENERATE.read_text()
cmake = CMAKE.read_text()

# The creator decoder bundle preserves selected F32 tensors that are not in
# the official FP16 encoder source. Keep those two checkpoint lifetimes and
# paths distinct at the in-process H3 session boundary.
assert 'video_vae_checkpoint: joined(str.view(checkpoint_root),' in generate
assert '"video_vae/source/model.safetensors")' in generate
assert 'video_decoder_aux_checkpoint: joined(str.view(donor_root),' in generate
assert '"shared/video-vae/derived-fp16.safetensors")' in generate

# Rebuilding the external AIR toolchain provider must invalidate MM-Air's
# custom command so airc republishes the matching provider beside the binary.
for artifact in (
    "${MM_AIR_TOOLCHAIN}/runtime/libair_rt.a",
    "${MM_AIR_TOOLCHAIN}/providers/nvidia/libair_gpu_nvidia.so",
):
    assert artifact in cmake, f"missing MM-Air toolchain dependency: {artifact}"
assert "list(APPEND MM_AIR_TOOL_DEPS air_gpu_nvidia)" in cmake

for page in ("generate", "movie", "control", "prompt"):
    assert f"<property name=\"name\">{page}</property>" in ui
    assert f'"{page}"' in main

for required in (
    "MiniMax H3", "Generate H3 MP4", "Movie Maker",
    "Queue H3 take", "H3 Union ControlNet", "Stage H3 CT Request",
    "CK-INT8", "ConvRot INT8", "Donor hybrid", "24 FPS", "832×480",
    "Current Generations", "Continuity spine",
    "PROMPT LAB / DIRECTOR", "Qwen3-VL 4B", "Send to Generate",
    "Send to Movie Maker", "Save to History", "prompt_cancel",
):
    assert required in ui, required

assert [item.text for item in tree.findall(".//object[@id='gen_model_list']/items/item")] == [
    "MiniMax H3 Base", "MiniMax H3 Reference", "Krea 2 Turbo"]
assert 'krea_session.run_to_png' in generate
assert 'task.spawn(work,fn=generation.run_krea)' in main
assert 'gen_use_image_reference' in main
assert 'task.spawn(work,fn=prompt_lab.run)' in main
assert 'prompt_lab.cancel' in main
assert 'mm_air_prompt_manifests' in cmake
assert 'Wait for Qwen teardown before starting H3/Krea' in main
for excluded in ("Klein", "Flux", "SDXL", "Z-Image", "Wan"):
    assert not re.search(rf"\b{re.escape(excluded)}\b", ui, re.IGNORECASE), excluded

for token in ("#0d1011", "#131718", "#181d1e", "#e8a84c", "#6c6af5", "#72c6c4"):
    assert token in css, token

print("MM-AIR desktop contract: native H3/Krea Generate, H3 editor pages, unique IDs, source palette PASS")
