# MM-AIR

MM-Air is a native desktop application for AI media generation, written in AIR:
MiniMax H3 video with audio (text, image, first/last-frame and reference
conditioned, Character Swap with a turbo path), Krea 2 Turbo and Qwen-Image
images, a Qwen3-VL Prompt Lab, editing, and a Movie workspace.

This repository publishes the **MM-Air application source only**. **AIR itself
is private, under development, and not ready for public release.** This is a
development snapshot, not a standalone, publicly buildable release. The source
expects an AIR checkout beside it (`../../AIR`, for example `C:\MM-Air\src`
next to `C:\AIR`). Windows builds use x64 MSVC (`tools/build-windows-app.cmd`,
paths in `tools/local-paths.cmd`).

Selected generated images and movies have a **Copy to Downloads** action.
It uses AIR's shared `std.desktop.copy_to_downloads` primitive, respects the
configured desktop Downloads directory and returns the copied path in the footer.
Copies run on a native worker; originals/history stay intact and repeated copies
receive non-overwriting numbered filenames. No save dialog is opened.

MM-AIR is the native AIR desktop application for generation. Generate links
MiniMax H3, Krea 2 Turbo, and Qwen-Image-2.1 AIR-language sessions directly.
Its six main surfaces are:

- Generate, based on SerenityFlow's three-column Generate workspace with the
  MiniMax H3 model selected.
- Edit, a localized source-preserving image/video workspace with authored masks,
  tracked crops, references, Qwen analysis, and H3 video execution.
- Image Edit, a dedicated Qwen-Image-2.1 source-PNG and edit-instruction
  workspace with side-by-side source/result previews.
- Movie Maker, based on Mojo Serenity's H3 Studio project, shot, inspector and
  continuity-spine workspace.
- H3 ControlNet, based on SerenityFlow's dedicated dense Union ControlNet screen.
- Prompt Lab / Director, an AIR-native Qwen3-VL workspace for prompt chat, image/video
  captioning, shot planning, continuity notes, authoritative window plans, and
  reusable H3 prompt construction.

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

### H3 targeted repair and motion timing

Edit now includes **Repair Frames** and **Motion Repair**. Repair planning snaps
the requested range and handles outward to H3 temporal boundaries, optionally
ends at a nearby authored shot cut, and reports the exact affected range before
generation. Full mode sends only that bounded source span through linked native
Ref2VA. Rolling mode splits a long repair into bounded overlapping H3 jobs,
uses the streaming ConvRot INT8 transformer policy, and releases each job
before the next. The output is restored to the original
24 FPS world duration, inserted by exact frame selection, and published with
the original audio plus a diagnostics sidecar.

An optional SAM 3 source mask is honored by Repair Frames and Motion Repair.
After H3 renders a window, MM-Air automatically tracks the generated subject
with the same native SAM 3 loader and performs a two-matte composite: source
pixels remain authoritative outside the source matte, obscured background is
recovered inside the vacated silhouette, and only the generated-subject matte
is overlaid. Temporal handle feathering softens both splice boundaries.

Motion Repair's plain-data hold map supports range painting, a compact heatmap,
automatic source-motion analysis, and `air.h3.motion.v1` JSON import/export.
The 2026-09-13 same-seed GPU matrix rejected selective physical/compact timing
for severe blur, so those modes were removed from the product UI; Stock H3
timing is the only selectable policy. Movie Maker's **Continuity+** panel adds
validated, video-only schedule-matched drift control while retaining the
existing independent audio-latent context. See
[`H3_REPAIR.md`](../../docs/models/H3_REPAIR.md) for the inventory, APIs,
clean-room boundary, and evidence limits.

The final 2026-09-13 two-window gate used a ConvRot INT8 conditioner,
streaming ConvRot INT8 transformer blocks, BF16 activations, and dense INT8
attention. It completed in
598,955 ms at a whole-process provider peak of 23,576,527,440 B, so this mode
does not meet the 14.5 GB intake target; Ref2VA conditioning/reference
preparation, not the streamed transformer phase, sets the peak. The admitted
four-segment Drift Control A/B reduced mean luma discontinuity across its three
shot boundaries from 11.912 to 7.792 (34.6%), while remaining explicitly a
seam aid rather than a guarantee against long-range palette drift.

The application resolves `air-minimax-h3` as an `airproj` path dependency and
imports its public `session.ai` entry directly into the MM-Air binary. The CMake
target asks that AIR toolchain to verify the locked package graph before every
application build; there is no copied H3 implementation or H3 native wrapper in
MM-Air.

### Qwen-Image-2.1 generation and image edit

Generate's model picker includes **Qwen-Image-2.1** for native text-to-image
generation. The dedicated **Image Edit** surface directly below Edit accepts
one to ten ordered PNG sources and one natural-language edit instruction. The
first source is the primary picture and later sources retain their displayed
order as additional visual conditions. Both paths call the
same linked `models.qwenimage21.session` package inside the MM-Air process;
there is no Python runtime, HTTP model service, helper model process, or
ComfyUI boundary.

Generate exposes the seven creator-published output geometries, an editable
2–100 step count, seed, the creator dynamic Flow schedule or a native linear
Flow alternate, and Euler or native DPM++ 2M sampling. The creator-default
recipe remains 2048x2048, 40 steps, dynamic Flow, Euler and
`true_cfg_scale=1.0`; the alternate schedule/solver are explicit native
choices and are not mislabeled as creator defaults. Outputs are PNG files under
`output/qwen-image-2.1/generate` and `output/qwen-image-2.1/edit`, with the
normal MM-Air parameter sidecar and History integration. Image Edit restores
from its sidecar back into the dedicated source/instruction workspace.

Generate uses model-owned panels rather than hiding individual controls inside
an H3 form. Selecting Qwen shows its resolution, noise schedule, solver, steps,
random-or-locked seed, progress and output controls; the H3 task, geometry,
duration, projection, attention and reference controls are absent as complete
groups. Selecting H3 restores those groups. Search filtering is constrained by
the selected model and cannot make another model's controls reappear. Runtime
resolution mapping, validation and recipe identity come from
`models.qwenimage21.contract`; the Gtk list order is locked to that contract by
the desktop acceptance test. Qwen sidecars preserve both stable numeric IDs and
readable schedule/solver names.

Krea likewise owns an explicit sampling panel. Its current AIR session admits
exactly the creator Turbo contract—1024x1024, eight evaluations, creator Turbo
Flow and Euler—so the controls remain visible while unsupported alternatives
remain unavailable rather than silently becoming no-ops. Generate keeps a
fixed 360-pixel parameter rail across H3, Krea and Qwen model changes. H3 ships
with valid projection and attention defaults selected, and duration is an
integer 1–30 seconds.

Generated-image galleries are image-first: paths and filenames are not drawn
under thumbnails, selecting an image opens the full-size overlay, and **Trash**
moves the selected artifact through the desktop trash service instead of
permanently deleting it. File controls accept native picker selection and
desktop drag-and-drop. Image Edit exposes the same Qwen resolution, schedule,
solver, step and random-or-locked seed controls as Generate.

Deployment provides the pinned creator snapshot and AIR manifests:

```sh
QWEN_IMAGE21_ROOT=/models/Qwen-Image-2.1 \
QWEN_IMAGE21_MANIFEST_DIR="$AIR_ROOT/models/qwenimage21/manifests" \
  build-gcc15/bin/mm-air
```

While a request is live the Generate screen reports prompt encoding,
transformer residency, every sampling step with ETA, VAE decode and PNG save.
The transformer checkpoint is loaded once into provider-owned pinned host
residency, then reused for every block and denoise step. The runtime records
checkpoint bytes immediately after load and fails if that counter changes in
the denoise loop. The 2026-09-20 bounded T2I and edit smokes both completed at
2048x2048 and reported exactly `0 bytes after load`; their two-step PNGs prove
the direct runtime and edit route, not the visual quality of the required
40-step production recipe.

### SeedVR2 Generate post-processing

Generate includes optional **SeedVR2 3B** and **SeedVR2 7B** post-processing.
Enable it, select the model,
choose same-size restoration, 2x, or custom multiple-of-16 dimensions, then
select source-audio preservation, seed, one/eight-step quality, and
Auto/Low VRAM/Performance memory policy. **Run after generation** turns the
selection into a real post-process: H3 first saves a retained
`.pre-seedvr2.mp4`, unloads and synchronizes its model session, and only then
loads SeedVR2 in the same AIR process. Krea and H3 character-sheet requests are
rejected because their final product is PNG rather than video.

The app is a thin settings and metadata adapter over the reusable
[AIR SeedVR2 toolkit](../../AIR/toolkits/seedvr2/README.md). VAE encode, two-pass CFG
DiT inference, VAE decode, VRAM admission, exact frame count/FPS, and optional
audio remux all live in that toolkit. The completed MP4 becomes the visible
Generate result. Its full SeedVR2 settings, checkpoint paths, input/final files,
runtime, conservative VRAM estimate, and measured provider peak allocation are
stored in both `<result>.seedvr2.json` and Generate History. Older version-one
history remains readable; new history is schema version two with an optional
`postprocess` record.

SeedVR2 is optional delivery work. If its VRAM admission or runtime fails,
MM-Air reports the warning but publishes and displays the already-completed
`.pre-seedvr2.mp4` instead of misclassifying successful H3 generation as a
failed request.

Deployment supplies the model locations rather than compiling personal paths
into the application:

```sh
MM_AIR_SEEDVR2_DIT=/models/seedvr2-3b/diffusion_models/seedvr2_3b_fp16.safetensors \
MM_AIR_SEEDVR2_7B_DIT=/models/seedvr2-7b/diffusion_models/seedvr2_7b_fp16.safetensors \
MM_AIR_SEEDVR2_VAE=/models/seedvr2-3b/vae/seedvr2_ema_vae_fp16.safetensors \
MM_AIR_SEEDVR2_MANIFEST_ROOT=/models/seedvr2-3b/manifests \
MM_AIR_SEEDVR2_7B_MANIFEST_ROOT=/models/seedvr2-7b/manifests \
  build-mm-air/bin/mm-air
```

The 7B model uses the same reusable AIR media/VAE path, but its own 36-layer
transformer contract and manifest root. On 24 GB cards, use **Low VRAM** so
blocks stream after the generating model has fully unloaded.

The toolkit automatically splits long clips into bounded causal `4k+1`
windows, selects a live-VRAM-admitted window size, uses deterministic global
noise offsets, blends overlap shoulders, and streams the assembled RGB result
to disk. A forced GPU/media regression delivered two windows, nine exact video
frames, and the original AAC. The 2026-09-13 useful-shape receipt restored the
48-frame 256x448 clay-character edit in two full-context windows (37-frame
maximum, 25-frame final overlap) in 100.619 seconds, preserving its two seconds
of AAC; measured provider peak allocation was 24,126,103,248 bytes and the
separate planning estimate was 23,215,472,640 bytes.
Visual inspection found strong one-step sharpening/color-edge artifacts, so
that receipt proves execution and media delivery rather than quality parity.

Same-size Restore is the default. A 512x896 2x attempt currently fails inside
the native VAE encoder with `GPU operation unsupported`; 2x and custom remain
explicit experimental choices pending VAE spatial tiling or a provider fix.

### H3 Movie Maker

Movie Maker (`Ctrl+3`) is now a functional native AIR adaptation of Serenity's
MiniMax Filmmaker workspace rather than a static tab. It keeps the same durable
Project → Shots → Takes → Edit model and keeps a native file-backed project
library under `output/movies` using the
`serenity.h3.movie.v1` schema. The project title, format, target runtime,
takes-per-shot, Director/Continuity/Brand bibles, shot fields, ordered
references, shared cast, endless-chain state, locks, selected takes, and output
paths autosave and restore across application launches. The Projects picker can
open any saved project; New and Import add projects, while Delete moves the
selected project to Trash and never removes the final project.

The shot deck supports New, Add, Duplicate, Delete, shot selection, 5–15 second
duration, the six admitted H3 resolutions, opening/final frames, ordered visual
references, last-frame-only L2VA, soundscape, music, and an editable compiled H3 prompt. Prompt
compilation preserves Serenity's three-section base and six-section Ref2VA
contracts. **Run Qwen Director pass** uses the AIR-native Qwen3-VL 8B runtime,
applies the result as the selected shot plan, and requires complete Qwen unload
before H3 can run.

**Queue H3 take** submits directly to the linked AIR MiniMax H3 session with
24 FPS synchronized audio, 19-evaluation exponential Euler, exact BF16
conditioner projection, ConvRot INT8 transformer projection, and CK dense INT8
attention (Ck-INT8 dense v4, `owned_dense_int8_attention`) on every evaluation; the
donor-hybrid exact-first policy remains selectable. MM-Air runs ConvRot with bounded
block residency: two device slots over one page-locked host slab holding all 19 GB
of blocks, filled once per request. Repeated 24 GB requests therefore never need the
whole transformer on the device, and no step reads the checkpoint.

Measured 2026-09-23 on the RTX 3090 Ti (300 W cap), with the Release toolchain,
Ref2VA with two pictures, 832x480, 5 s, 19 evaluations: the bounded path was Streaming
before this change, re-reading about 15.6 GB from disk per step at about 58 s/step.
Pinned, a step is about 8 s with the GPU at 100% and zero checkpoint reads.
Generate-to-displayed-result was 375.6 s (encode 113 s, pinned load 32 s warm,
sampling 152 s, video and audio decode 59 s). The Qwen-Image size control no
longer rewrites H3 geometry: a hidden Qwen resolution event had sent H3 requests to
2048x2048 (about 154k attention tokens instead of 17.4k).
Results remain contained in the selected shot's take list. **Render
all shots** runs missing shots serially because the GPU session is single-tenant.
**Continue selected take** creates a following native Motion Context shot. Every
successful Base or Ref2VA take saves a compact `.airh3ctx` A/V latent tail.
Continuation loads that tail directly, uses fixed video and audio row classes
with the source-faithful rotary layout, trims the protected overlap from picture
and sound, and saves the next tail without decoding and re-encoding the seam.
The deployment checkpoint must include the four-table Motion Context modulation
cache at
`serenity_runtime_cache_v1/native-modcache-motion-context-steps20-blocks50.safetensors`;
this is static checkpoint preprocessing, not a second runtime or helper process.

The **Cast** inspector stores shared character image, name, role, and identity
rules at project scope. Cast images lead each non-continuation shot's ordered
Ref2VA inputs, and the compiled character bible makes those identities
authoritative over conflicting shot prose. **Endless** exposes a persistent
5–3,600 second target and 5–15 second segment size. Start/resume generates one
segment at a time, waits for success, creates the next Motion Context shot, and
uses a legal final segment to land exactly on the target; Stop after current
prevents the next segment from being created.

Export Project writes the complete `.serenitymovie.json`; Export Edit writes a
`serenity.h3.edit.v1` selected-take manifest. **Stitch movie** normalizes every
selected take to 1344×768, constant 24 FPS, stereo 48 kHz audio before assembly,
trims to the planned cut duration, saves a non-overwriting MP4 under
`output/movies`, and opens the result in the Movie monitor.

`tests/movie_project.ai` verifies shot operations, shared cast ordering, native
continuation creation, H3's `17j+5` internal-frame alignment, project/edit
schemas, autosave round-trip, and a real two-clip normalized audiovisual stitch.
`models/h3/tests/motion_context.ai` verifies compact-tail persistence and exact
condition-row geometry. `tests/movie_continuation_generate.ai` performs the
bounded GPU generation → latent continuation → stitch artifact gate. The private-X11 desktop gate additionally
creates a new project, adds a shot, and verifies that the two-shot project was
written to disk before continuing through the other workspaces.

The 2026-09-13 production gate generated two native five-second H3 clips and a
stitched ten-second movie with non-silent audio. FFprobe stream/duration checks,
SHA-256 hashes, seam frames and a contact sheet are retained under
`output/movie-gpu-gate-20260913/`; the inspected movie SHA-256 is
`3c267db539e4ae41a307bf1dc339782334a656b32d3973a3cb9e8b3d0fef8363`.

### Masked Character Swap and Edit

Generate's H3 mode selector also exposes **Masked Character Swap**. It requires
one source video, one or more identity pictures, and either an automatic SAM 3
mask, an imported mask image/video, or a freehand mask authored in Edit. A
missing mask is a hard error: the application never substitutes ordinary
full-frame Character Swap. **Preserve Outside Mask** is enabled by default and
must remain enabled for this path.

The native SAM 3 plugin validates video geometry and contains allocation or
other C++ exceptions at its C ABI. A failed automatic-mask job is reported in
Edit while the MM-Air process and project remain open; native exceptions are
never allowed to unwind through AIR and terminate the desktop application.
For video, AIR decodes one bounded 24 FPS RGB stream before entering the CUDA
tracker, avoiding SAM3's unsafe per-frame subprocess decoder on a GPU worker.

The reusable AIR implementation is split deliberately:

- `masked_edit.ai` owns f32 masks, connected-component speck removal and hole
  fill, temporal smoothing, expansion/shrink, soft feathering, deterministic
  Fixed/Combined, Tracked, and Zoomed crop metadata, RGB crop/reinsert, and the
  final pixel-authoritative composite.
- `masked_runtime.ai` owns bounded local codec/container orchestration. It
  decodes source and mask media at 24 FPS, runs H3 on the aligned working crop,
  wraps still crops as lossless 22-frame source clips, and encodes the
  AIR-composited full-size result with source audio when available. For
  replacement, it first fills the expanded old-subject matte with a clean H3
  background and then inserts the generated subject under its own tighter
  SAM 3 matte. FFmpeg is not a model runtime.
- `generate.ai` retains two native mask strategies. The strict library path
  passes the exact-geometry clean source latent and snapped token mask into the
  H3 session. The Edit UI uses full tracked-crop Ref2VA, same-process SAM 3,
  a sequential background-only Ref2VA pass, and AIR's two-matte compositor
  because a single authored-mask blend can retain a conflicting source
  silhouette. Both strategies stay in-process; the two-matte path preserves
  source pixels outside the expanded removal influence.
- `main.ai` owns Generate/Edit session state and routes Qwen completion, mask
  controls, crop preview, native H3 work, and Save As.

H3 mapping follows the model's real geometry: 16x spatial VAE compression,
5-frame/2-latent prefix, repeating 17-frame/5-latent temporal cycles, and 2x2
latent spatial token grouping. Latent weights are derived from the cleaned soft
crop mask; the denoiser mask snaps any selected latent cell to its complete 2x2
token, matching H3's per-row timestep labels. The original authored full-canvas mask remains the
final compositing authority, so every byte at a zero-weight pixel is copied
unchanged into the pre-encode RGB composite. H.264 output encoding is lossy and
can introduce codec-level differences even in those regions; the application
does not mislabel the final compressed bitstream as byte-identical.

The **Edit** workspace (`Ctrl+2`) keeps source, automatic/imported/painted mask, references,
prompt, feather/cleanup/expansion, crop strategy, and preview/result state
separate from Generate. It supports bounded Qwen analysis and prompt building,
native freehand paint/erase through AIR's letterbox-aware mask overlay, a live
video scrubber with frame-step/play controls and synchronized video-mask preview,
tracked crop preview, localized H3 image/video execution, source-preserving
reconstruction, and Save As. `Send to Edit` is available from both Prompt Lab and masked
Generate. Prompt Lab is now `Ctrl+5`; Movie Maker and ControlNet are `Ctrl+3`
and `Ctrl+4`.

Edit's ordinary **Character Replace · no mask** mode is the semantic replacement
path: load source media, add at least one character identity image, describe the
replacement, build the Qwen prompt, and run H3 Ref2VA. It never asks for an
authored mask. Video sources run full-frame Ref2VA directly. Still-image sources
are repeated on H3's 22-frame grid and use an internal full-canvas edit region
only to publish the first result frame as PNG; that internal region is not a
user mask or an outside-pixel preservation claim. Use **Masked Character
Replace** when exact localization and source-pixel compositing are required.

Masked still-image Edit uses the same in-process H3 Ref2VA session: MM-Air repeats the
source crop on the bounded 22-frame H3 grid, VAE-encodes that clip at the exact
target geometry, uses its first decoded result frame for the edited region, composites under the original
full-resolution mask, and publishes a lossless PNG. Character modes require an
identity reference; Image Edit and Prompt-guided Local Edit can use the source
picture alone but remain explicit-mask modes.

#### Automatic SAM 3 subject masks

Edit now has **Auto Mask with SAM 3** directly below Source. Enter a text concept
such as `person`, `blue robot`, or `car`, then press the button. The native CUDA
model detects that concept and tracks it over the complete 24 FPS edit timeline;
the generated mask is loaded into the synchronized mask-video overlay and is
accepted anywhere an imported mask is accepted. Manual paint/erase remains
available for corrections.

This uses the shared [AIR SAM 3 toolkit](../../AIR/toolkits/sam3/README.md) in the
same process, not a Python service. The C runtime loads `libair_sam3.so` and
invokes its C ABI directly. The toolkit pins
[PABannier/sam3.cpp](https://github.com/PABannier/sam3.cpp) commit
`01832ef85fcc8eb6488f1d01cd247f07e96ff5a9`, adds the required ggml CUDA window
and attention support, and loads the local `sam3-q4_0.ggml` checkpoint. FFmpeg is
used only at the existing media boundary to decode frames and encode the mask
preview. Set `MM_AIR_SAM3_PLUGIN` or `MM_AIR_SAM3_MODEL` to override their
default locations beside the executable and under
`$HOME/.serenity/models/sam3/` respectively.

The native library exposes only the `air_sam3_mask_media` C ABI and binds its bundled
GGML/CUDA implementation locally. This keeps SAM 3's private runtime symbols
from colliding with the AIR H3 provider already loaded by the desktop process.

The exact two-second acceptance source
`output/character-swaps/coconut-source-2s.mp4` produced a 720x1280, 48-frame,
24 FPS mask in 108.76 seconds on the RTX 3090 Ti. Peak host RSS was 703,088 KiB.
The saved mask preview was decoded and a seven-frame contact sheet was visually
inspected, including frame zero and the final frame. This proves the local
automatic-mask path on that clip; it is not a universal segmentation-quality
claim.

`tests/masked_edit.ai` verifies paint/erase rasterization, cleanup, hole fill,
one-sided feather cores, no-jitter tracking, crop extraction, gray-mask round
trip, H3 latent/token mapping, target-matte reinsertion, and exact outside-mask
RGB preservation. `tests/masked_runtime.ai` creates a bounded
four-frame 320x256 video fixture plus a 22-frame wrapped still-image fixture and
verifies real source/mask decode, a 256x256 H3 working crop, crop decode,
full-canvas composite, final MP4 encode, and final PNG encode without
loading the H3 checkpoint. Full H3 masked output quality
remains a separate GPU/artifact gate.

The 2026-09-13 two-matte video gate used the 48-frame, 24 FPS, 256x448 clay
dancer request at seed 424242 with nineteen exponential evaluations, exact BF16
conditioning, row-scaled W8A8 transformer projection, and dense INT8 attention.
The inspected native base MP4 is exactly 2.000 seconds with AAC and has SHA-256
`56a3d50d3ac150e8727da528c36552c1ef71c2f5fd27b4fcc41f90ca2dc2e401`.
A twelve-frame full-view contact and enlarged head-region contact show no old
robot/bow contour. The subsequent SeedVR2 3B F16 one-step restore (seed 42)
retained that contour fix, but visibly increased sharpening/color artifacts;
the clean base and restored derivative are therefore reported separately.

`tests/masked_image_generate.ai` is the bounded real-model receipt. It runs the
same linked Ref2VA worker used by Edit, with an authored freehand mask, then
publishes the composited 1024x1024 PNG. On 2026-09-12 the corrected
nineteen-evaluation Euler/Exponential run completed in 237.04 seconds. The final
PNG changed 44,603 of 1,048,576 pixels, all within `(443,48)-(734,241)`; visual
review confirms the complete pink bow became coherent cobalt-blue satin without
the rejected duplicate figure, while the robot and room outside the authored
blend area remained source-identical.

### H3 character sheets

Generate includes a native H3 character-sheet preset adapted from
[`PoopMan333/H3_Character_Sheet_Generator`](https://huggingface.co/PoopMan333/H3_Character_Sheet_Generator)
at revision `13c095e84c6d651d49ddcbdb672779cc66a7d44d`. It does not execute that
repository's ComfyUI workflow. The preset selects H3 Reference/Ref2VA, supplies
the source's fixed orbit prompt, accepts the existing ordered set of up to nine
visual references, and performs frame extraction and stitching inside AIR.

- **4 panels · faster:** 480×864, 3 seconds, frames 2/24/45/68, 2×2 layout.
- **6 panels · full orbit:** 768×1376, 5 seconds, frames
  2/21/42/63/84/113, 3×2 layout.
- Both layouts use six-pixel black gutters. The final PNG and its source H3 MP4
  are retained under `output/character-sheets`.
- **Keep Picture 1 style** and the source's **Anime to photoreal** fixed prompts
  are available. The editable prompt remains the source's per-reference input
  section and is prepended to the selected fixed prompt at submission.

The source workflow's optional acceleration stack does not map one-to-one onto
AIR's admitted profiles. Applying this preset therefore leaves schedule,
conditioner projection, transformer projection, and attention unselected or at
their existing explicit values; Generate continues to fail closed until the
user chooses every required H3 execution policy.

Parameter sidecars store the fully expanded H3 request and raw MP4 target.
Loading or reusing one restores that exact H3 request with the character-sheet
switch off; reselect and apply the preset when another stitched PNG is wanted.

The focused `tests/character_sheet.ai` gate verifies prompt markers, exact
geometry/frame indices, panel ordering, output dimensions, and gutters. The
`character-sheet-video` binary additionally runs the native extraction/stitch
path on an existing MP4. A 120-frame, 768×768, 24-FPS H3 artifact produced an
inspected 2316×1542 six-panel PNG. Because that input was not generated with the
orbit prompt, this proves the postprocessor and layout—not end-to-end orbit
quality.

### H3 Character Swap

Generate's **H3 mode** selector now includes **Character Swap**. This is a
dedicated Ref2VA path rather than the generic Prompt Lab Enhance action:

1. **Source Video** accepts one clip, shows its first-frame thumbnail and
   metadata, and gives Qwen two, four, or eight ordered observations according
   to duration (never more than eight).
2. **Reference Character** accepts up to seven identity images. The UI keeps
   these separate from the source-video role and lets the user identify the
   main or one selected source subject.
3. **Build / Rebuild Prompt** runs the selected Prompt Lab Qwen3-VL model and
   populates the normal editable Generate prompt. It does not start H3.
4. **Generate H3 Character Swap** requires a successfully built prompt with all
   six official Ref2VA sections. It submits the original source clip first as
   `<Video 1>` and the original identity files as `<Picture 1>` through
   `<Picture N>` to the linked in-process H3 Ref2VA session. Editing the built
   prompt before Generate is preserved in the H3 request and output sidecar.

Changing source media, identity media, target, notes, or preservation
instructions invalidates the previous build and requires Rebuild. Clearing a
slot removes only its request reference, never the source file. The optional
environment, camera, and identity switches are explicitly prompt instructions,
not numeric controls or reconstruction guarantees. Qwen analyzes visual frames
only and is instructed not to claim it heard audio or invent dialogue.

The prompt contract was checked against the official MiniMax H3
`h3-prompt-writing` skill and `ref-en.txt` at repository revision
`d21241f0a4b3acbb34c97dae47fa417b7065e438`. The installed copies matched that
revision byte-for-byte (SHA-256 `a7000443588ca3f145e3b3fd8900f14e0325dc460bd811268fac89a9dc8e56d0`
and `1e574f356716ad55612247ffb7bbccbcdb484ad96599d63c7dca1af186b1fab7`).

A real Qwen3-VL 4B bounded-video test produced and admitted this shape, then
returned `fully_unloaded=true` before H3 was allowed to run:

```text
subject_definitions: <Video 1> is the source edit. <Subject 1> is the replacement character whose appearance comes from <Picture 1> and any later pictures. <Subject 1> is the main onscreen subject identified from <Video 1>.
summary: [video editing + reference generation]
retention_analysis: <Video 1> is partially_preserved because its target subject's appearance changes. <Subject 1> is fully_preserved for the requested identity anchors: face, hair, body proportions, skin tone, outfit, and defining features.
detailed_description: [Shot 1] <Subject 1> stands front-facing in the source composition. [Shot 2] At 00:01.666, the source action and camera progression continue with <Subject 1> retaining the replacement identity anchors.
overall_soundscape: N/A
non_diegetic_music: N/A
```

Focused coverage is in `tests/character_swap.ai` and the reusable prompt-toolkit
tests. `tests/character_swap_4b_smoke.ai` runs the actual AIR Qwen3-VL 4B media
path and rejects truncated or mislabeled output. No full-size H3 character-swap
render was launched for this UI change; decoded replacement quality therefore
remains unverified.

### Character Swap LoRA and direct prompt (2026-10-15)

Ordinary (unmasked) Character Swap now follows the
[akatz-ai Character Swap LoRA](https://huggingface.co/akatz-ai/MiniMax-H3-Character-Swap-LoRA)
workflow instead of a Qwen scene description:

- **Build Prompt** writes the direct instruction the LoRA was trained on, with
  no Qwen load: "Replace only TARGET in <Video 1> with the character in
  <Picture 1>. Keep the replacement character's identity, face, hair, outfit,
  and art style … Preserve the source video's camera, framing, background,
  lighting, objects, and all other people. Match TARGET's position, scale,
  pose, and movement … Do not show the reference sheet or its background."
  TARGET comes from the target notes (empty means "the main person"). The
  six-section Qwen prompt described the source actor's look, which pulled the
  original identity back in and re-described the whole scene. Generate accepts
  this direct form or a full six-section prompt; Masked Character Swap keeps
  its Qwen build.
- **LoRA root.** MM-Air samples Ref2VA with fused ConvRot INT8 kernels that
  have no LoRA insertion points, so `tools/h3_swap_lora_merge.py merge` bakes
  the LoRA into the official BF16 weights and re-quantizes them with the
  difh3convrot H256 recipe into a separate root (junctions and hard links for
  everything else; token-refiner pairs go into a small merged shard).
  `verify` re-quantizes unmerged blocks and must match the existing cache byte
  for byte; it does for blocks 0 and 49. Set `MM_AIR_H3_CHARACTER_SWAP_ROOT`
  (Settings or runtime.json) to that root. Unmasked swap jobs then use it and
  force ConvRot transformer projection, because only the ConvRot cache carries
  the adapter.
- **Character reference.** The gallery's **Swap Char** button makes the
  selected Krea image or H3 character sheet `<Picture 1>` and switches Generate
  to Character Swap. A Krea "character reference sheet" prompt (front, side,
  back, face close-up on a plain background) works well; the LoRA was trained
  with sheets.
- Video references with a soundtrack need `audio_vae/model.safetensors` in the
  Ref2VA root (official `MiniMaxAI/MiniMax-H3` `Ref2VA/audio_vae`).

Windows gate, RTX 5080 16 GB: a synthetic Krea astronaut sheet swapped into a
5 s 832x480 H3 pier clip (profile quality-19, ConvRot, CK INT8 attention, seed
555123). Identity, suit, and helmet transferred in every sampled frame; pier,
sky, framing, and walking path matched the source. Source-video VAE encode took
7m16s and sampling 6m51s.

Swap speed-up (same day): the source clip was encoded on the 768-short-edge
creator canvas (1344x768 for an 832x480 clip), tripling encoder tiles and
reference tokens. Unmasked swaps now set `reference_video_match` and encode at
the target resolution (ComfyUI `ref_image_size: match`). The H3 encoder's cuDNN
Conv3d workspace cap rose from 64 MiB to 1 GiB, which picks kernels 3.6x faster
per 17x256x256 tile (`tests/video_encode_bench.ai`; moments rel_l2 1.2e-4).
The same job now takes 48 s to encode, 3m04s to sample, and 4m50s end to end
(previously 15m30s). The output was visually equivalent.

### Turbo Character Swap and corrected LoRA layout (2026-10-15)

- **Layout fix.** ComfyUI-format LoRAs (the akatz swap LoRA, lightx2v turbo)
  address fused QKV as contiguous [q;k;v], but the raw official shards
  interleave Q/K/V per head (diffusers `reorder_interleaved_qkv`). FC1 is
  [gate; value] in both. Checked exactly against the Diffusers build of the turbo
  LoRA. `tools/h3_swap_lora_merge.py` now re-interleaves QKV deltas, honours
  per-projection `.alpha` (scale alpha/rank) and stacks several LoRAs. The first
  `reference-charswap` root was merged without the QKV reorder; use
  `reference-charswap-v2`.
- **Turbo.** `reference-charswap-turbo4` = swap LoRA + lightx2v
  `minimax_h3_ref2v_turbo_4step_v0.1` (shift 12/3, which is exactly MM-Air's
  simple grid at four evaluations). New profile `profile_turbo_4` (four Euler
  evaluations) reads `native-modcache-ref2va[-audio]-steps5-blocks50`, built by
  `tools/h3_modcache.py`. That tool regenerates the shipped 7-step caches with
  99.7% of values bit-identical and the rest within one BF16 ulp. Character Swap
  selects Turbo automatically when `MM_AIR_H3_CHARACTER_SWAP_TURBO_ROOT` is set;
  any 19-evaluation schedule uses `MM_AIR_H3_CHARACTER_SWAP_ROOT`. Turbo is
  refused outside unmasked swap.
- The plain 7-evaluation donor profile is not a shortcut for swaps: on the gate
  clip it copied the source actor for the first ~2.5 s.
- Gate (same clip, seed 555123, matched reference canvas): sampling took 36 s
  instead of 3m04s, 2m42s end to end. Identity, scene and path held, with detail
  comparable to the 19-step render; the turbo pass dropped the carried helmet.

### H3 Video Outpaint

Edit's **Video Outpaint** mode is a dedicated geometry-driven Ref2VA path. It
accepts one source video, explicit 32-aligned target width/height, aspect
conversion presets, Left/Right/Top/Bottom/Horizontal/Vertical/All Sides,
Start/Center/End anchoring, and Exact Source or bounded Blended compositing.
**Preview Geometry** draws the preserved source rectangle without loading H3;
**Preview First Window** and **Run Full Outpaint** use the same generation job
and runtime policies.

`outpaint.ai` owns deterministic placement, per-edge expansion, non-overlapping
generated regions, the preserved rectangle, seam weights, authoritative H3
window plans, the Qwen Outpaint request, validation, and the versioned metadata
sidecar. `outpaint_runtime.ai` performs only local codec/container operations:
it pads the source onto the target canvas, slices source/reference windows,
exports a visual-only prior tail, invokes the existing native masked Ref2VA
contract, exact-composites original RGB inside the preserved rectangle, and
maps source audio independently. Exact Source publishes lossless RGB H.264 so
the decoded saved source rectangle remains byte-identical; Blended may modify
only its selected seam width.

Long clips use `models/h3/timeline.ai` as the single window authority. Every
window receives its matching source slice. AIR's Base path supports direct
latent carry, but Ref2VA direct latent carry is not yet implemented; Video
Outpaint therefore uses the explicit `decoded-tail-reference` fallback. Only
the previous window's planned visual tail is supplied, with no tail audio, and
the stitcher drops exactly the next window's planned leading overlap. The final
soundtrack is copied from the untouched source video.

Focused gates are `tests/outpaint.ai` (geometry, exact/blended masks, planning,
Qwen request, metadata) and `tests/outpaint_runtime.ai` (real codec preparation,
full target mask, saved-file RGB identity, all delivery frames, and audio).
`tests/outpaint_generate.ai` is the bounded real-model receipt. On an RTX 3090
Ti, a two-window 56-frame 384x256 run used two 39-frame windows with 22-frame
overlap and saved `output/outpaint/native-right-384x256-2window-admitted.mp4`.
Its decoded 256x256 preserved area matched all 56 decoded source frames exactly
(SHA-256 `fd11d9e880d44154c927f09c4e06f53d72a8da31e646965afe429ca53e8a1704`),
AAC remained present, and its `.outpaint.json` records
`continuity_carry=decoded-tail-reference`. This admits the native path and its
preservation contract, not universal semantic quality for every prompt/source.

Generate has distinct first-frame and last-frame pickers. After validation, its
button starts an owned AIR task, opens the GPU inside that task, and calls the
linked geometry-aware `session` functions. Progress and the terminal result return to
the native event loop through a bounded in-process channel. No server, child
model executable, Python runtime, or model-specific C/C++ adapter is involved.

Generate wiring follows Mojo Serenity's Generate/reference controls and media
preparation, with the requested native layout: history on the right and current
generations at the bottom. The styling is deliberately plain, one muted palette
shared with SerenityAir, sentence-case labels, and no badges, pills or gradients.
The parameter panel is capped at 300 pixels of content: labels wrap and dropdowns
truncate their closed label, while the popup list keeps full text. The preview and a
full-width prompt editor share a draggable vertical split, sized for structured H3
prompts of several thousand characters. Movie Maker and ControlNet are outside this change.

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

References live in **Source / References**, directly under the H3 **Task**. For
tasks that take no pictures, the section names the tasks that do. The whole section
is a drop zone for files from a file manager or any other app, and for images
dragged from a web browser. A drop follows the task: I2VA and L2VA fill the
first/last frame, FL2VA takes the first two files as first and last frame, and
Ref2VA adds each file to the visual or audio references by its media kind (limits
9 and 3). Select a thumbnail and use **Remove** beneath its visual or audio list. **Clear all references** removes every visual/audio reference and both
first/last frame slots from the request. Neither action deletes source media.

Generate's **Model LoRA** section opens the local LoRA folder for both Krea and
MiniMax H3, accepts one enabled `.safetensors` overlay, and exposes enable,
strength, remove and clear controls. Strength is limited to the Serenity UI range
`[-10,10]`. Saved parameters, history, and completed-media sidecars retain the
path, strength, and enabled state; older parameter files without `loras` remain
base-only.

For H3, selecting a LoRA switches the transformer projection to the supported
row-scaled INT8 path. The picker accepts valid canonical PEFT, flat legacy
Musubi/Kohya, or dotted `diffusion_model.*.lora_{down,up}.weight` plus scalar
per-projection alpha H3 `.safetensors` from any filesystem path and retains that
exact path in saved parameters. The linked native AIR H3 sampler strictly
validates and streams each admitted layout directly; no adjacent converted
checkpoint, Python sampler, or helper runtime is required.
H3 LoRA currently admits Base-model direct generation with Exact BF16
or Row-scaled INT8 transformer projections. Ref2VA, ConvRot transformer blocks,
latent windowing, and Motion Context fail explicitly instead of ignoring the
adapter. Krea continues to admit complete plain PEFT main-block A/B pairs;
unsupported alpha/DoRA/LoKr and text-fusion formats are rejected explicitly.

The dotted-layout boundary is covered by a native CPU MM-Air test against the
real unchanged rank-32 checkpoint and by a bounded GPU overlay gate for one
token-refiner and one denoiser block. Those gates prove intake and application,
not a complete generated-video or quality result.

Behavior reference: MojoDiffusion `serenity-server/canvas/js/generate.js`
(`addLora`, `renderLoraList`) and `serenitymojo/serve/krea2_backend.mojo`.
Model implementation stays in private AIR; MM-Air only owns controls and requests.
Prompt Lab is a full fifth workspace (`Ctrl+5`), not a modal. Its left pane keeps the
conversation and ordered image/video references; its right pane holds the current workprint.
The controls expose final prompts, variations, image/video captions, shot lists, continuity,
scene plans, and director notes, plus H3 Expand, Shorten, Cinematic, and Shot List actions.
Results can replace or append Generate's prompt, populate Movie Maker Director, be preserved
as a variant, or be saved as versioned JSON under `output/prompt-history`.

The expanded **H3 Window Plan** uses AIR's shared `models.h3.timeline` geometry.
Total, approximate window, and approximate overlap seconds are resolved into the
actual `17j+5` / `5j+2` H3 endpoints. The report lists every ordered delivery-frame,
video-latent, and separately mapped 40 Hz audio-latent span. Scene Plan injects
that exact report into Qwen and requires one prompt per listed window after global
definitions, continuity notes, and a whole-film beat sheet. Compact continuation
state carries only global anchors, the prior realized state, and optionally the
immediately preceding detailed prompt; older window prompts are not replayed.

The same model primitive drives long Base-model jobs from Generate. When the
requested duration exceeds Prompt Lab's Window value, the worker executes the
reported plan in-process. Every later window preserves the preceding realized
video-latent overlap inside H3 denoising, appends only its new video and audio
extents on their separate clocks, and decodes the assembled AV latent once.
There is no between-window VAE round trip. Ref2VA and masked generation remain
single-window because reference-media slicing and authored-mask scheduling need
their own product gate; the worker rejects rather than silently changing those
semantics. Visual-only AV edits preserve the independent audio storage verbatim;
a visual subject mask is never converted into an audio mask.
These behaviors were independently implemented after reviewing
[ComfyUI-MMH3Tools](https://github.com/ckinpdx/ComfyUI-MMH3Tools); MM-Air remains
native AIR and includes no ComfyUI node/runtime code.

The bounded product receipt is `tests/windowed_generate.ai`: 56 requested frames
at 256x256, two 39-frame windows, a representable 22-frame overlap, exact BF16
conditioning/transformer weights, exact attention, and seven evaluations. It
must finish through `generation.Job` and save an inspected MP4.
The exact-seed receipt completed in 573.54 seconds at
`output/h3-gates/windowed-exact-seedfix-56f-256.mp4` (SHA-256
`25857f1bf7d173d6ddd4bb1bad33246deb52b9f7b1585f3a3834caea2fd26b42`).
FFprobe reports 56 H.264 frames at 256x256/24 FPS and stereo 32 kHz AAC.
Inspection kept the same robot and workshop through the join, with a noticeable
camera/pose adjustment; this is an execution/artifact receipt, not a claim that
every long-form seam is visually invisible.
Generate completion and failure remain visible in the batch/run-state controls
and also issue a best-effort `notify-send` desktop notification. A missing
notification service never changes a generation result.

The tab uses the reusable AIR [`toolkits/prompt`](../../../AIR/toolkits/prompt/README.md)
package in-process. Qwen3-VL 4B and 8B use resident BF16 language weights. The 8B profile
uses the official checkpoint's untied language head and measured profile-driven vision
tower. The optional Qwen3-VL 32B profile uses AIR's explicit approximate row-scaled W8A8 language projections with 64
two-slot streamed blocks while its embedding, norms, untied head, and vision tower remain
BF16 when that separately installed cache is present. A completed quantization receipt is required,
and no model silently falls back to
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
  image thumbnails/previews and embedded video playback. History is a two-column
  grid of image-only 136-pixel tiles. Its actions are **Download**, **Reuse**,
  **Reference** and **Trash**. Select a result and use **Reuse** to restore its
  request: H3, Krea and Qwen-Image entries each restore through their own parameter
  schema. Clearing history removes only the catalog, not media.
- Selecting an image result enables **Reference**. This explicit
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

On 2026-09-15, the real Generate screen restored the canonical 3000-step
`eri_with_trigger` H3 LoRA, displayed it in **Model LoRA**, persisted it through
**Save parameters**, and submitted the linked AIR H3 worker. The 19-evaluation
512x512 request completed prompt conditioning, LoRA application, sampling, video
and audio decode, and MP4 save in 160.403 seconds. Its
`h3-148257392320908.mp4` contains 124 H.264 frames at 24 FPS (5.166667 seconds)
and stereo AAC at 32 kHz; the adjacent JSON sidecar records the enabled LoRA at
strength 1.0. This is end-to-end UI/runtime/artifact evidence, not a claim that
the adapter's visual quality has been accepted.

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
  build-mm-air/bin/mm-air build-mm-air/bin/air-ui "$XVFB" \
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
# The desktop tree is separate from the toolchain tree: configuring build-gcc15 itself
# with AIR_DESKTOP=ON would rewrite the toolchain's cache (and a later toolchain
# reconfigure turns the desktop targets back off).
AIR_ROOT="$(cd "${AIR_ROOT:-.}" && pwd)"
CC="${CC:-gcc-15}"
CXX="${CXX:-g++-15}"
cmake -S . -B build-mm-air -G Ninja \
  -DAIR_DESKTOP=ON \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_C_COMPILER="$CC" \
  -DCMAKE_CXX_COMPILER="$CXX" \
  -DCMAKE_CUDA_COMPILER=/usr/local/cuda-12.4/bin/nvcc \
  -DCMAKE_CUDA_HOST_COMPILER=/usr/bin/g++-13 \
  -DCMAKE_CUDA_ARCHITECTURES=86 \
  -DMM_AIR_TOOLCHAIN="$AIR_ROOT/build-gcc15" \
  -DMM_AIR_H3_MANIFEST_DIR="$AIR_ROOT/build-gcc15/h3-manifests" \
  -DMM_AIR_PROMPT_MANIFEST_DIR="$AIR_ROOT/build-gcc15/prompt-manifests" \
  -DPKG_CONFIG_EXECUTABLE="$AIR_ROOT/build-dev/desktop-sdk/pkg-config"

# A pixi GCC 15 toolchain needs the host driver, cuDNN, and C++ runtime visible
# while linking the final desktop executable.
export LIBRARY_PATH="/usr/lib/x86_64-linux-gnu:$HOME/dif-vendor/cudnn/lib:$HOME/.pixi/envs/gcc-15/lib${LIBRARY_PATH:+:$LIBRARY_PATH}"
export LD_LIBRARY_PATH="/usr/lib/x86_64-linux-gnu:$HOME/dif-vendor/cudnn/lib:$HOME/.pixi/envs/gcc-15/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
cmake --build build-mm-air --target mm_air_desktop -j2

MM_AIR_H3_CHECKPOINT_ROOT=/models/MiniMax-H3/FL2VA \
MM_AIR_H3_REFERENCE_ROOT=/models/MiniMax-H3/Ref2VA \
MM_AIR_H3_DONOR_ROOT=/artifacts/h3-flref-product \
MM_AIR_H3_MANIFEST_ROOT="$AIR_ROOT/build-gcc15/h3-manifests" \
MM_AIR_PROMPT_MANIFEST_ROOT="$AIR_ROOT/build-gcc15/prompt-manifests" \
AIR_QWEN3_VL_4B_DIR=/models/Qwen3-VL-4B-Instruct \
MM_AIR_SAM3_MODEL="$HOME/.serenity/models/sam3/sam3-q4_0.ggml" \
  build-mm-air/bin/mm-air
```

`mm_air_desktop` depends on both `mm_air_h3_manifests` and
`mm_air_prompt_manifests`, so the build above generates every runtime manifest into
their configured directories. Keep the explicit runtime roots equal to those directories.
Focused refreshes are:

```sh
cmake --build build-mm-air --target mm_air_h3_manifests -j2
cmake --build build-mm-air --target mm_air_prompt_manifests -j2
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
desktop testing. `Ctrl+1` through `Ctrl+6` select Generate, Edit, Image Edit,
Movie Maker, ControlNet, and Prompt Lab respectively;
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

"$AIR_ROOT/build-gcc15/bin/airc" run apps/mm-air/tests/character_sheet_video.ai \
  --mode release --cc gcc-15 -- /path/to/h3.mp4 /tmp/character-sheet.png 6

# The playback fixture must be a 10-second video with a real audio stream.
"$AIR_ROOT/build-gcc15/bin/airc" run apps/mm-air/tests/ui_layout.ai \
  --mode release --cc gcc-15 -- \
  "$PWD/build-mm-air/bin/air-ui" "$PWD/apps/mm-air/desktop.ui" \
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
  "$PWD/build-mm-air/bin/mm-air" "$PWD/build-mm-air/bin/air-ui" \
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
