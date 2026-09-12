# MM-Air

MM-Air is a native desktop application for AI media generation, written in AIR.
Its Generate workspace supports MiniMax H3 video generation with audio and
Krea 2 Turbo image generation, with prompts, reference media, generation
settings, saved results, and playback. Its Prompt Lab / Director workspace runs
Qwen3-VL in-process for prompt work, image/video captioning, shot planning, and
H3 prompt construction.

This repository publishes the **MM-Air application source only**. **AIR itself
is private, under development, and not ready for public release.** This is an
early development snapshot, not a standalone, publicly buildable release.

## What MM-Air does

- Runs the AIR-native H3 and Krea 2 Turbo sessions directly inside the
  application process.
- Provides text-to-video/audio, first-image and first/last-image conditioning,
  and reference-conditioned generation.
- Exposes editable resolution and duration in seconds, with duration mapped to
  H3's 24 FPS frame grid.
- Accepts up to nine visual references and three audio references, with media
  pickers and thumbnails.
- Keeps completed results in a right-side history gallery and current
  generations below the preview, with embedded video playback.
- Saves, loads, and reuses generation parameters, including the prompt, seed,
  resolution, duration, references, and explicitly selected execution settings.
- Generates Krea 2 Turbo PNGs with its current 1024×1024, eight-step BF16 recipe;
  an explicit action can reuse an image result as an H3 reference.
- Provides Qwen3-VL 4B and 8B BF16 profiles plus an explicitly approximate 32B
  profile whose language projections use row-scaled INT8. Model selection never
  silently falls back to a smaller checkpoint.
- Shows actual loading, conditioning, sampling step/count, decoding and saving
  stages, elapsed time, and prominent validation errors. Generate creates a
  fresh non-overwriting filename under `output/krea` or `output/h3` and records
  a parameter sidecar; it does not open an output-name dialog.

The interface uses native GTK controls. AIR owns application state and generation;
there is no browser-based generation server, Python model runtime, or separate
model executable. Native media tools handle media preparation and MP4 encoding.

Generate is the active development surface. Movie Maker and ControlNet screens
are not claimed to be complete generation workflows.

Selecting a generated image and pressing **Use image as H3 reference** appends
that original image to the ordered reference list and selects Ref2VA. It does
not start generation or choose an H3 execution schedule. If the profile still
reads **Select schedule…**, Generate deliberately fails closed until the user
chooses the intended seven- or nineteen-evaluation schedule.

## What AIR is

AIR is the underlying general-purpose native programming language and compiler
toolchain, designed to make software easier for people and coding agents to
understand, build, diagnose, and maintain. It is not just an H3 wrapper or a UI
framework.

Programs can use concise `.ai` source or explicit `.air` intermediate
instructions. The compiler verifies typed instructions, ownership, and effects,
optimizes the program, and emits C11 for compilation into a native executable.
It also provides structured diagnostics, source provenance, dependency tooling,
reusable standard libraries, and optional native GPU and desktop facilities.

The guiding idea is to let the compiler derive mechanical details from
authoritative declarations instead of making authors maintain the same facts
in multiple places. MM-Air is one application built with that system.

AIR's compiler implementation uses C++/C; MM-Air's application logic is AIR
source. These are separate projects and separate publication boundaries.

## Availability and current status

Actual native Generate-button tests have completed both model paths. The latest
2026-09-12 checks include:

- **Krea 2 Turbo:** two 1024×1024, eight-step PNGs, including a selected-LoRA
  run. They completed in 223.301 and 59.075 seconds, were opened, and showed
  coherent output.
- **H3:** a five-second 768×768 H.264 MP4 with AAC stereo audio at 32 kHz,
  in 426.828 seconds on 2026-09-12. Full video/audio decoding passed and sampled
  frames were visually coherent.
- **Prompt Lab:** exact 8B text/video and approximate 32B row-INT8 text/video
  gates completed and fully unloaded. The 32B text gate returned `READY` in
  23.91 seconds; its bounded video gate completed in 140.63 seconds.

These tests observed real stage updates and advancing elapsed time, and
required a newly saved output plus a persisted history entry. Isolated 4K/2×
UI tests also passed for click-only gallery selection, playback, automatic output
naming without dialogs, and visible policy/missing-model validation errors.

These are development-run results, not promised performance on other hardware.
They do **not** establish full numerical model parity, speech intelligibility,
audio quality, or production readiness. Other settings and larger workloads
require their own validation; editable geometry is not a memory-capacity claim.

Building this snapshot requires access to the private AIR toolchain, its desktop
SDK, and the AIR-native H3/Krea packages, plus separately obtained model assets and
compatible native dependencies. Prompt Lab additionally requires the selected
Qwen3-VL checkpoint; 32B requires a completed AIR row-INT8 quantization receipt.
The application manifest and integration CMake file retain those external
dependency references. This repository does not currently supply a standalone
public build or downloadable application release.

No AIR compiler implementation, standard library, GPU provider, H3/Krea model
implementation, private Git history, binaries, model weights, or generated
caches are included here. Publishing MM-Air does not release AIR.

Application sources and native tests are in [`apps/mm-air`](apps/mm-air).
