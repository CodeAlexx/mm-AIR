# MM-AIR

Selected generated images and movies have a **Copy to Downloads** action.
It uses AIR's shared `std.desktop.copy_to_downloads` primitive, respects the
configured desktop Downloads directory and returns the copied path in the footer.
Copies run on a native worker; originals/history stay intact and repeated copies
receive non-overwriting numbered filenames. No save dialog is opened.

MM-AIR is the native AIR desktop application for generation. Generate links
MiniMax H3 and Krea 2 Turbo AIR-language sessions directly. Its four main surfaces are:

- Generate, based on SerenityFlow's three-column Generate workspace with the
  MiniMax H3 model selected.
- Movie Maker, based on Mojo Serenity's H3 Studio project, shot, inspector and
  continuity-spine workspace.
- H3 ControlNet, based on SerenityFlow's dedicated dense Union ControlNet screen.
- Prompt Lab / Director, an AIR-native Qwen3-VL workspace for prompt chat, image/video
  captioning, shot planning, continuity notes, and reusable H3 prompt construction.

The application uses AIR's optional GTK desktop toolkit. AIR owns navigation and
application state; GTK supplies native controls and presentation. Generate and
ControlNet use native file dialogs, retain the selected local media, validate it
through [`std.media_input`](../../stdlib/media_input.md), and render selected
images in their native preview widgets. Generate also captures the live prompt,
model, task, schedule, independent conditioner and transformer projection
paths, attention path, exact integer seed, resolution, duration,
ordered visual/audio references, and MP4 destination into the shared
H3 package's public `request.ai` contract. Schedule, both projections,
and attention begin unselected and validation fails closed until the user
chooses each policy explicitly; MM-AIR does not silently choose an H3
execution path.

The application resolves `air-minimax-h3` as an `airproj` path dependency and
imports its public `session.ai` entry directly into the MM-Air binary. The CMake
target asks that AIR toolchain to verify the locked package graph before every
application build; there is no copied H3 implementation or H3 native wrapper in
MM-Air.

Generate has distinct first-frame and last-frame pickers. After validation, its
button starts an owned AIR task, opens the GPU inside that task, and calls the
linked geometry-aware `session` functions. Progress and the terminal result return to
the native event loop through a bounded in-process channel. No server, child
model executable, Python runtime, or model-specific C/C++ adapter is involved.

Generate wiring follows Mojo Serenity's Generate/reference controls and media
preparation, with the requested native layout: history on the right and current
generations at the bottom. Movie Maker and ControlNet are outside this change.

- Base tasks: text, first-image, and first/last-image video + audio.
- Reference task: up to nine ordered images/videos plus three explicit audio
  files. Add/remove controls display image/video thumbnails and audio waveforms.
  Selecting a source previews it; video and audio use native playback controls.
- Width and height are editable in 32-pixel increments. Duration is editable in
  seconds and mapped to frames at 24 fps through the shared H3 geometry contract.
  The existing 832x480, 124-frame default is unchanged.
- Save/Load parameters persist the prompt, model/task, all execution policies,
  exact seed, dimensions/duration, ordered references, and output path as versioned
  JSON. `--parameters FILE.json` restores the same request at startup.

Generation never asks for an output filename. Parameters are stored with history
and in a JSON sidecar beside completed media. Save parameters creates an automatic
snapshot under `output/parameters`; only movie-project naming needs a save name.

References: select a thumbnail and use **Remove selected** beneath its visual or
audio list. **Clear all references** removes every visual/audio reference and both
first/last frame slots from the request. Neither action deletes source media.

Krea's **LoRAs** section opens the local LoRA folder, accepts a `.safetensors`
overlay, and exposes enable, strength, remove and clear controls. One overlay may
be enabled, matching the inspected Mojo Krea backend. Strength is limited to the
Serenity UI range `[-10,10]`. Saved parameters/history retain paths, strength and
enabled state; older parameter files without LoRAs remain base-only. The native
runtime currently admits complete plain PEFT Krea main-block A/B pairs, including
the supplied `eri2_krea2_v2_2000.safetensors`; unsupported alpha/DoRA/LoKr and
text-fusion formats are rejected explicitly, not silently ignored.

Behavior reference: MojoDiffusion `serenity-server/canvas/js/generate.js`
(`addLora`, `renderLoraList`) and `serenitymojo/serve/krea2_backend.mojo`.
Model implementation stays in private AIR; MM-Air only owns controls and requests.
Prompt Lab is a full fourth workspace (`Ctrl+4`), not a modal. Its left pane keeps the
conversation and ordered image/video references; its right pane holds the current workprint.
The controls expose final prompts, variations, image/video captions, shot lists, continuity,
scene plans, and director notes, plus H3 Expand, Shorten, Cinematic, and Shot List actions.
Results can replace or append Generate's prompt, populate Movie Maker Director, be preserved
as a variant, or be saved as versioned JSON under `output/prompt-history`.

The tab uses the reusable AIR [`toolkits/prompt`](../../../AIR/toolkits/prompt/README.md)
package in-process. Qwen3-VL 4B and 8B use resident BF16 language weights. The 8B profile
uses the official checkpoint's untied language head and measured profile-driven vision
tower. Qwen3-VL 32B uses AIR's explicit approximate row-scaled W8A8 language projections with 64
two-slot streamed blocks while its embedding, norms, untied head, and vision tower remain
BF16. A completed quantization receipt is required, and no model silently falls back to
4B or 8B. Text, image,
and bounded video inputs share the same request interface. Video decode samples two, four,
or eight timestamped observations by duration and preserves their order.

Before loading, Prompt Lab checks current free VRAM and requires about 11 GiB for 4B,
20 GiB for 8B, or 8 GiB for the measured 32B row-INT8 profile. The 4B/8B language weights
are resident BF16; 32B language blocks and every vision tower are streamed.
Measured 8B text and bounded-video gates peaked at 16,448,009,632 and 16,476,117,048 bytes,
respectively, and returned the RTX 3090 Ti to its pre-request 721 MiB baseline. The UI marks H3
blocked for the whole worker lifetime and enables it only after Qwen's synchronized full
teardown. Cancel is cooperative at safe phase boundaries; H3 remains blocked until cleanup
actually completes.

On the same RTX 3090 Ti, the integrated 32B text gate returned exact `READY` in 23.91
seconds at a 4,233,108,128-byte device peak. The integrated 0.2-second 64x48 video gate
correctly described the uniform blue sequence and no temporal change in 140.63 seconds at
a 4,296,010,552-byte peak. Both returned `fully_unloaded=true`; no compute process remained.
- Completed outputs populate current generations and persistent history, with
  image thumbnails/previews and embedded video playback. Select a result and use Reuse parameters
  to restore its request. Clearing history removes only the catalog, not media.
- Selecting an image result enables **Use image as H3 reference**. This explicit
  action appends the original image to the existing visual-reference list and
  selects H3 Ref2VA. It preserves the prompt, seed, geometry, audio references,
  and execution policies, and respects the nine-visual limit. This does not
  start generation or select an H3 schedule. If the profile still reads
  **Select schedule…**, Generate reports `profile: select the H3 schedule
  explicitly`; choose the intended seven- or nineteen-evaluation profile before
  starting H3. Krea generation uses the shared AIR-language Krea session, not
  the older C++ model orchestration.

Krea 2 Turbo has its own PNG parameter schema, eight-step recipe, and currently
the ported decoder's 1024x1024 constraint. Its worker uses the same owned-task
completion/history path as H3. The first native port test hit a host memory-cgroup
OOM before output; the session now preserves the donor's explicit Streaming
offloader mode instead of Auto. A fresh 1024x1024/eight-step Generate-button run
now completes in about148s, displaying real stages and adding its robot PNG to
history. The PNG was opened and visually inspected. This verifies native Krea
execution through MM-Air, not numerical parity with another implementation.

### Live application gate — 2026-09-12

The rebuilt desktop app completed two real 1024x1024, eight-step Krea requests
through its Generate action. The first saved `krea-251603416395953.png` in
223.301 seconds; the second, with the selected LoRA enabled, saved
`krea-251926622598286.png` in 59.075 seconds. Both are 4,195,716-byte RGBA PNGs,
were opened, and show coherent output. These are execution and artifact checks,
not a Krea numerical-parity claim.

The same build completed an H3 Ref2VA request with the explicit DC exponential
Euler 19 profile as `h3-250268056424773.mp4` in 426.828 seconds. The result is a
1,351,679-byte, 768x768, five-second MP4 with 120 H.264 frames at 24 FPS and
stereo AAC at 32 kHz. Complete video/audio decode passed and sampled frames were
visually coherent. This is a decoded-artifact gate, not full numerical parity or
audio-quality acceptance.

The same live session selected the latter Krea result and used **Use image as H3
reference**. The original PNG appeared in the ordered H3 reference list and the
task changed to Ref2VA. Generate then rejected the request because H3 Profile
was still **Select schedule…**. This is the expected fail-closed policy behavior,
not a failed reference transfer; the action intentionally never chooses a
seven- or nineteen-evaluation schedule for the user.

Both model sessions send actual loading/conditioning, sampling step/count,
decoding and save stages through the existing worker channel. A prominent label
beside Generate shows these messages and validation failures; a separate elapsed
timer advances throughout work. Generate automatically creates fresh filenames
under application-root `output/krea` (PNG) or `output/h3` (MP4), including reused
parameters. It never opens an output Save dialog or selects an existing result
for overwrite. Completed media and parameters are linked in history automatically.
Select a reference thumbnail and press its list's Remove selected button to
remove it from the request without deleting the source file.
Stage messages also appear in the application log. No estimated
percentage is presented as measured progress.

The explicit H3 DC Euler19 profile selects the existing exponential sigma grid.
Direct row-scaled W8A8 is transformer-only; dense INT8 from evaluation zero is a
separate attention selection. These are opt-in additions, not changed defaults
or rewritten saved profiles. The existing Ref2VA steps20 modulation artifact is
the same prepared artifact used by the accepted DC reference. The old simple
profile retains its previous path and semantics; this does not assert matching
modulation/sigma provenance for that older combination.

The existing native gallery regression has an image-reference mode (no GPU or
generation); use two existing PNG files as its final arguments:

```sh
MM_AIR_TEST_IMAGE_REFERENCE=1 MM_AIR_TEST_SCALE=2 \
  bash apps/mm-air/tests/gallery_selection.sh \
  build-gcc15/bin/mm-air build-gcc15/bin/air-ui "$XVFB" \
  apps/mm-air/desktop.ui apps/mm-air/desktop.css "$PNG_A" "$PNG_B"
```

History and thumbnails live under `XDG_DATA_HOME/mm-air`, falling back to
`HOME/.local/share/mm-air`. Requests retain the selected file paths; parameter
files do not bundle the media. Missing restored sources remain visible and their
preview failure is reported. An invalid seed never silently reuses the previous
value.

The linked paths and controls are not, by themselves, numerical or production
parity claims. A saved, inspected MM-Air MP4 remains the delivery evidence.

Build and run:

```sh
AIR_ROOT="$(cd "${AIR_ROOT:-../AIR}" && pwd)"
CC="${CC:-gcc-15}"
CXX="${CXX:-g++-15}"
cmake -S . -B build-gcc15 -G Ninja \
  -DAIR_DESKTOP=ON \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER="$CC" \
  -DCMAKE_CXX_COMPILER="$CXX" \
  -DMM_AIR_TOOLCHAIN="$AIR_ROOT/build-gcc15" \
  -DMM_AIR_H3_MANIFEST_DIR="$AIR_ROOT/build-gcc15/h3-manifests" \
  -DMM_AIR_PROMPT_MANIFEST_DIR="$AIR_ROOT/build-gcc15/prompt-manifests" \
  -DPKG_CONFIG_EXECUTABLE="$AIR_ROOT/build-dev/desktop-sdk/pkg-config"
cmake --build build-gcc15 --target mm_air_desktop -j2

MM_AIR_H3_CHECKPOINT_ROOT=/models/MiniMax-H3/FL2VA \
MM_AIR_H3_REFERENCE_ROOT=/models/MiniMax-H3/Ref2VA \
MM_AIR_H3_DONOR_ROOT=/artifacts/h3-flref-product \
MM_AIR_H3_MANIFEST_ROOT="$AIR_ROOT/build-gcc15/h3-manifests" \
MM_AIR_PROMPT_MANIFEST_ROOT="$AIR_ROOT/build-gcc15/prompt-manifests" \
AIR_QWEN3_VL_4B_DIR=/models/Qwen3-VL-4B-Instruct \
  build-gcc15/bin/mm-air
```

`mm_air_desktop` depends on both `mm_air_h3_manifests` and
`mm_air_prompt_manifests`, so the build above generates every runtime manifest into
their configured directories. Keep the explicit runtime roots equal to those directories.
Focused refreshes are:

```sh
cmake --build build-gcc15 --target mm_air_h3_manifests -j2
cmake --build build-gcc15 --target mm_air_prompt_manifests -j2
```

The 2026-09-10 focused clean-tree check generated all 16 declared files, including
the 21,220-byte `h3-audio-encoder.json`; an immediate repeat reported no work, and
removing only that output in the isolated test tree caused the target to regenerate
and restore it.

The environment variables are deployment configuration: checkpoint and
cache locations are deployment configuration, not personal paths compiled into
the application. The Reference root is required for Ref2VA.
`MM_AIR_H3_DONOR_ROOT` contains the port's Qwen, video-decoder,
and audio-decoder SafeTensors caches; MM-Air does not execute the donor compiler.

Krea deployment uses `MM_AIR_KREA_MODEL` (Turbo checkpoint),
`MM_AIR_KREA_QWEN_INDEX` (Qwen3-VL-4B checkpoint index),
`MM_AIR_KREA_TOKENIZER_DIR`, `MM_AIR_KREA_VAE` (Qwen-Image VAE checkpoint),
`MM_AIR_KREA_VAE_CONFIG`, and `MM_AIR_KREA_MANIFEST_ROOT` (the prepared native
Krea manifest directory). Missing locations are reported before a worker opens
the GPU. Paths are deployment configuration, not compiled-in machine paths.

The app also accepts optional `UI CSS AIR-UI` positional overrides for focused
desktop testing. `Ctrl+1`, `Ctrl+2`, `Ctrl+3`, and `Ctrl+4` select the four workspaces;
`Ctrl+O` chooses the first frame, `Ctrl+L` chooses the last frame,
`Ctrl+Shift+O` chooses control media, `Ctrl+S` chooses the output MP4, `F5`
starts a valid configured H3 request, and `Ctrl+Q` closes the app.
`Ctrl+Shift+S` saves parameters, `Ctrl+Shift+L` loads them, `Ctrl+R` reuses
the selected result, and `Ctrl+Shift+R` resets Generate controls.

Focused native regressions (from the MM-Air repository):

```sh
AIR_ROOT="$(cd "${AIR_ROOT:-../AIR}" && pwd)"
"$AIR_ROOT/build-gcc15/bin/airproj" --project apps/mm-air \
  --toolchain "$AIR_ROOT/build-gcc15" test

# The library/history check accepts an owned scratch directory and optional
# existing video/audio fixtures, so it is an explicit binary rather than an
# argument-free airproj test target.
"$AIR_ROOT/build-gcc15/bin/airc" run apps/mm-air/tests/library.ai \
  --mode release --cc gcc-15 -- /tmp/mm-air-library-check \
  /path/to/video.mp4 /path/to/audio.wav

"$AIR_ROOT/build-gcc15/bin/airc" run apps/mm-air/tests/parameters.ai \
  --mode release --cc gcc-15

# The playback fixture must be a 10-second video with a real audio stream.
"$AIR_ROOT/build-gcc15/bin/airc" run apps/mm-air/tests/ui_layout.ai \
  --mode release --cc gcc-15 -- \
  "$PWD/build-gcc15/bin/air-ui" "$PWD/apps/mm-air/desktop.ui" \
  "$PWD/apps/mm-air/desktop.css" /path/to/video.mp4 /path/to/thumbnail.png
```

The native widget test round-trips 960x544, 10 seconds, a seed above the exact
f64 integer range, and all four populated galleries. With the required 10-second
audio/video fixture, it requires playback to advance through at least four
seconds and reports the GTK media state, including `has_audio=true`,
`muted=false`, and positive volume, before checking clean shutdown. Parameter
tests cover all nine visual and three audio slots, ordering, and
malformed/excessive input rejection. These tests do not run inference or
substitute for a generated MP4.

Click-only history regression (no generation):

```sh
MM_AIR_TEST_SCALE=2 bash apps/mm-air/tests/gallery_selection.sh \
  "$PWD/build-gcc15/bin/mm-air" "$PWD/build-gcc15/bin/air-ui" \
  "$AIR_ROOT/build-dev/desktop-sdk/usr/bin/Xvfb" \
  "$PWD/apps/mm-air/desktop.ui" "$PWD/apps/mm-air/desktop.css" \
  /path/to/first.mp4 /path/to/second.mp4
```

The test owns a private 3840x2160 X11 display, accessibility bus/registry, and
temporary history/cache. It drives a real pointer over the second history item,
requires both the selection and current preview path to remain on the first,
then requires one click to select and preview the second. It passed at 1x and
2x scale on 2026-09-10; the prior `single-click-activate=true` layout failed
with `hovering changed history selection`. All four galleries now disable
that GTK hover-selection behavior; the app's existing selection event still
provides single-click preview. This test verifies history selection/preview
dispatch, not generated audio quality.

For reference ordering, select a visual/audio thumbnail and use its list's
up/down buttons. The selected item follows its new position, with its thumbnail
and metadata intact; moves beyond the first/last position are disabled. Save
parameters and Generate use that reordered list. This maps Serenity's reference
move controls without changing model settings or copying/deleting media.

The same isolated desktop regression can load a parameter file and exercise
both lists instead of history hover: prefix the command above with
`MM_AIR_TEST_PARAMETERS=/path/to/parameters.json`. The fixture needs at least
two visual and two audio references. The nine-visual/three-audio fixture passed
at 1x/2x scale; no inference is submitted. Native `tests/library.ai` additionally
checks whole-record moves with duplicate paths and invalid indices.

GTK 4.14's accessibility SCREEN coordinates return zero, so the test uses
WINDOW coordinates plus the actual X11 window origin and scale. See the
[upstream coordinate implementation](https://raw.githubusercontent.com/GNOME/gtk/4.14.5/gtk/a11y/gtkatspicomponent.c).

The controlled 2026-09-10 native playback run reached 4.007 seconds with a
10-second fixture, `has_audio=true`, `muted=false`, and volume 1.0. A concurrent
HDMI monitor measured nonzero PCM (peak -11.46 dB, RMS -29.05 dB). This proves
audio reached the selected output sink; it does not claim the generated audio's
semantic content is correct.
