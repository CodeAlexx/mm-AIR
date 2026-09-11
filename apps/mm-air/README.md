# MM-Air Generate workspace

This directory contains the public MM-Air application, written in AIR. Its
Generate workspace calls the private AIR-native H3 and Krea 2 Turbo sessions
inside the application process. It does not run a separate model executable,
Python model runtime, browser server, or model-specific C++ adapter.

**This is application source, not a standalone public build.** The AIR compiler,
runtime, standard library, model packages and desktop toolkit remain private.
See the [repository README](../../README.md) for the publication boundary.

## Controls and behavior

- H3 Base supports text, first-image and first/last-image video/audio tasks.
  Ref2VA accepts up to nine ordered image/video references and three audio
  references. Pickers show thumbnails or waveforms; selected media can preview.
- H3 width and height are editable in 32-pixel increments. Duration is editable
  in seconds and mapped to the model's 24 FPS frame grid. Editable dimensions
  are not a guarantee that every resolution or duration fits available memory.
- H3 schedule, conditioner projection, transformer projection and attention
  start unselected. Generate reports validation errors until the user explicitly
  chooses them. The DC Euler 19 exponential schedule, transformer-only direct
  row-scaled W8A8 and all-step dense INT8 attention are separate opt-in choices;
  existing saved profiles and defaults are not changed.
- Krea 2 Turbo uses its own PNG parameter schema and native eight-step BF16
  recipe. The current decoder supports 1024×1024. Switching models preserves
  their separate output destinations and restores H3 geometry when returning.
- Actual loading, conditioning, sampling step/count, decoding and saving
  messages appear next to Generate, with elapsed time and application logs.
  The UI does not invent progress percentages. Validation errors use the same
  prominent status area.
- Generate with no destination opens the native Save dialog. Selecting a path
  continues the request; Cancel starts no worker.
- History is on the right; current generations are below the preview. Hover
  does not change the selected result. Explicit selection updates the preview;
  videos use embedded playback controls.
- Save, Load and Reuse parameters preserve prompt, exact integer seed,
  geometry, references and execution settings. `--parameters FILE.json`
  restores a request at startup. Parameter files refer to original media paths;
  they do not bundle media.
- **Use image as H3 reference** explicitly adds a selected image result to
  Ref2VA, preserves the other request settings and does not start generation.

History and thumbnails use `XDG_DATA_HOME/mm-air`, falling back to
`HOME/.local/share/mm-air`. Clearing history removes catalog entries, not the
user's media files. Movie Maker and ControlNet presentation exists, but these
screens are not claimed to be complete generation workflows.

## Private integration requirements

The existing `CMakeLists.txt` is an integration fragment for an authorized AIR
development build, not a root project for `cmake -S .`. It expects AIR runtime
and desktop targets. `air.project.json` declares sibling private AIR model
packages; `.air` resolutions and lockfiles are generated locally and excluded
from this repository. The main application and widget tests also import the
private desktop toolkit. These dependencies are not vendored here.
The inherited CMake fragment also registers a private-development
`test_contract.py` fixture that is not included in this public snapshot; that
registration is not a claim of a runnable public test target. The maintained
native application tests published here are listed below.

H3 deployment provides `MM_AIR_H3_CHECKPOINT_ROOT`,
`MM_AIR_H3_REFERENCE_ROOT` for Ref2VA, `MM_AIR_H3_DONOR_ROOT` for prepared data
artifacts, and `MM_AIR_H3_MANIFEST_ROOT`. Prepared artifact paths do not imply
executing another compiler or runtime during generation.

Krea deployment provides `MM_AIR_KREA_MODEL`, `MM_AIR_KREA_QWEN_INDEX`,
`MM_AIR_KREA_TOKENIZER_DIR`, `MM_AIR_KREA_VAE`, `MM_AIR_KREA_VAE_CONFIG` and
`MM_AIR_KREA_MANIFEST_ROOT`. Missing configuration is reported before GPU work.
Model weights, manifests, generated caches and personal configuration are not
published in this repository.

## Native tests

The `.ai` tests cover parameter round trips, reference ordering, media/history
behavior and actual GTK controls/playback. They require the corresponding
private AIR dependencies. Test success is scoped: playback and UI submission
alone do not prove generated media quality or numerical model parity.

`tests/gallery_selection.sh` drives the real application on a private
3840×2160 X11 display and accessibility bus, with isolated history/cache. It
takes seven arguments: `APP AIR_UI XVFB LAYOUT CSS MEDIA_A MEDIA_B`.

Supported modes:

- Default: select, hover without changing preview, then click another result.
- `MM_AIR_TEST_SCALE=2`: exercise 4K/HiDPI behavior.
- `MM_AIR_TEST_IMAGE_REFERENCE=1`: add a selected PNG as an H3 reference.
- `MM_AIR_TEST_PARAMETERS=FILE.json`: restore and reorder reference lists.
- `MM_AIR_TEST_KREA_PARAMETERS=FILE.json`: restore Krea, then verify Generate
  reports a missing model in both central status and footer. This mode unsets
  the model location and does not generate by default.
- `MM_AIR_TEST_OUTPUT_CHOOSER=1`: use the initial blank output, open Save with
  Generate, cancel and require no worker or history change.
- **Explicit GPU opt-in:** `MM_AIR_TEST_GENERATE=1` with Krea parameters above,
  or `MM_AIR_TEST_H3_GENERATE_PARAMETERS=FILE.json`, presses the real Generate
  button with configured assets. It requires observed sampling/decode stages,
  advancing elapsed time, a new nonempty output and persisted history, with a
  720-second deadline. Never combine this opt-in with a cancellation test.

The opt-in generation test refuses pre-existing output paths. Use a fresh
destination and only run one model-generation test at a time on a shared GPU.
