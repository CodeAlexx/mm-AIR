# MM-AIR

MM-Air is a native desktop application for AI media generation, written in AIR:
MiniMax H3 video with audio (text, image, first/last-frame and reference
conditioned, Character Swap with a turbo path), Krea 2 Turbo, Qwen-Image-2.1
(and its Turbo) images and edits with the model's own
prompt enhancers, a Qwen3-VL Prompt Lab, editing, and a Movie workspace.

This repository publishes the **MM-Air application source only**. **AIR itself
is private, under development, and not ready for public release.** This is a
development snapshot, not a standalone, publicly buildable release. The source
expects an AIR checkout beside it (`~/mm-AIR` next to `~/AIR` on Linux; `C:\MM-Air\src`
next to `C:\AIR` on Windows). Windows builds use x64 MSVC (`tools/build-windows-app.cmd`,
paths in `tools/local-paths.cmd`).

Selected generated images and movies have a **Copy to Downloads** action.
It uses AIR's shared `std.desktop.copy_to_downloads` primitive, respects the
configured desktop Downloads directory and returns the copied path in the footer.
Copies run on a native worker; originals/history stay intact and repeated copies
receive non-overwriting numbered filenames. No save dialog is opened.

**Safe mode** (Settings → Safe mode) keeps adult pictures and videos out of
MM-Air for younger users. It uses AIR's shared `std.safe_media` store
(`~/.config/air/safe-media`, also read by SerenityAir): On/Off, a PIN, Hide or
Blur, relock minutes, adult LoRAs (from the LoRA library) and adult words. An
item is adult when the owner marked it (the **Adult** toggle beside a selected
result, or a folder mark made in SerenityAir); otherwise when its parameters or
`<file>.json` sidecar name an adult LoRA or prompt word, or it was made from an
adult picture or video (side-by-side and stitched movies inherit). While on and
locked, every gallery, preview, player, full view, take list and file picker in
MM-Air leaves adult items out (Hide; counts exclude them) or shows them blurred
and unopenable (Blur). Turning it off or unlocking needs the PIN; an unlock
relocks after the set minutes and on restart. Off: everything shows, adult
items carry a small `18+` caption. Audio is never affected. The desktop's own
file chooser shows its own previews; MM-Air refuses an adult pick from it.
`tests/safe_mode.ai` (`mm-air-safe-mode-check`) covers the rules with a scratch
store: `AIR_SAFE_MEDIA_DIR=... XDG_DATA_HOME=... mm-air-safe-mode-check SCRATCH PICTURE.png`.

MM-AIR is the native AIR desktop application for generation. Generate links
MiniMax H3, Krea 2 Turbo and Qwen-Image-2.1 AIR-language
sessions directly.
Its six main surfaces are:

- Generate, based on SerenityFlow's three-column Generate workspace with the
  MiniMax H3 model selected.
- Edit, a localized source-preserving image/video workspace with authored masks,
  tracked crops, references, Qwen analysis, and H3 video execution.
- Image Edit, a dedicated Qwen-Image-2.1 source-image and
  edit-instruction workspace with side-by-side source/result previews.
- Movie Maker, based on Mojo Serenity's H3 Studio project, shot, inspector and
  continuity-spine workspace.
- H3 ControlNet, based on SerenityFlow's dedicated dense Union ControlNet screen.
- Prompt Lab / Director, an AIR-native Qwen3-VL workspace for prompt chat, image/video
  captioning, shot planning, continuity notes, authoritative window plans, and
  reusable H3 prompt construction.

The application uses AIR's optional GTK desktop toolkit. AIR owns navigation and
application state; GTK supplies native controls and presentation. Generate and
ControlNet use native file dialogs, retain the selected local media, validate it
through [`std.media_input`](../AIR/stdlib/media_input.md), and render selected
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
[`H3_REPAIR.md`](../AIR/docs/models/H3_REPAIR.md) for the inventory, APIs,
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

H3 inference is AIR's own `std.inference.h3` library, imported directly into the
MM-Air binary. `airproj` verifies the locked package graph before every build;
there is no copied H3 implementation or H3 native wrapper in MM-Air.

### Safe mode, downloads, output folder (2026-11-09)

**Safe mode** (Settings, Safe mode column) keeps adult pictures and videos away from younger
users: On, PIN (Unlock / Lock, Set PIN), Adult items Hide or Blur, Relock after (minutes, default
30; a restart relocks), Adult LoRAs (from the LoRA library) and Adult words. The **Adult** toggle
in History marks one item; the owner's mark wins over the automatic rule both ways. While on and
locked, adult items are kept out of every gallery, preview and player (`safe_mode.ai`); anything
made from an adult picture or video counts as adult, and side-by-side or stitched movies made from
adult results are marked adult. Images and videos only. The logic and store
(`~/.config/air/safe-media`) are AIR's `std.safe_media`, shared with SerenityAir. Test:
`mm-air-safe-mode-check SCRATCH PICTURE.png` with `AIR_SAFE_MEDIA_DIR` and `XDG_DATA_HOME` set to
scratch folders.

**Download** copies the shown picture to the desktop Downloads folder from History, from the
**Image Edit** screen (under Generate Edit; Qwen and Fibo edits) and from the fullscreen view.

An empty **Output folder** setting (`MM_AIR_OUTPUT_ROOT` = "") means the home folder, as an
absolute path, so outputs keep landing in `~/h3`, `~/qwen-image-2.1`, `~/fibo2`, ...
(the relative empty path made Fibo and MOSS refuse their output with "must be an absolute PNG
path").

**H3 always encodes the prompt with the ConvRot INT8 conditioner** (24 GB, held in RAM). The
exact BF16 conditioner streams 49 GB from disk and AIR allows that once per process, so a second
BF16 run was refused; the Encoder choice is hidden and reused settings use ConvRot too.

### Qwen-Image-2.1 generation and image edit

Generate's model picker includes **Qwen-Image-2.1** for native text-to-image
generation. The dedicated **Image Edit** surface directly below Edit accepts
one to ten ordered PNG sources and one natural-language edit instruction. The
first source is the primary picture and later sources retain their displayed
order as additional visual conditions. Both paths call the
same linked `models.qwenimage21.session` package inside the MM-Air process;
there is no Python runtime, HTTP model service, or helper model process
boundary.

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
  build/release/bin/mm-air
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

### FLUX 3 Image Klein removed (2026-11-05)

FLUX 3 Image Klein is no longer on Generate's model list or in Image Edit's
**EDIT MODEL** dropdown (owner request). Its saved parameter files and history
entries (schema `mm-air.flux3-klein.parameters`) never restore as another model:
Reuse puts only their prompt and seed on Generate and keeps the selected model. Existing FLUX 3 PNGs stay in the
gallery and output folders.

### MOSS-Image Base and SFT (2026-11-05)

Generate's model list has **MOSS-Image Base** (model 4) and **MOSS-Image SFT** (model 5),
text-to-image PNGs made in the MM-Air process by AIR's `models/moss_image` generator
(`generate.run_adapted`): the text encoder is read once and freed, the DiT is read once and
stays resident for every step, then the VAE decodes. The **Sampling** panel holds Steps
(default 50), Guidance (CFG, default 3), Shift (default 5), Speed (Best quality, or Fast:
the INT8 projections, about twice as fast with slightly different fine detail) and an optional
negative prompt; size is any 256–2048 px in multiples of 16 (default 1024²). LoRA, LoHa, LoKr
and the other LyCORIS/PEFT adapters from **Model LoRA** run beside the DiT at their strength and
are never merged. Outputs go to `output/moss-image/generate` with the usual parameter sidecar
(schema `mm-air.moss-image.parameters.v1`), History and Reuse.

Settings: `MM_AIR_MOSS_BASE_ROOT` and `MM_AIR_MOSS_SFT_ROOT` (the published folders), and
`MM_AIR_LORA_DIR`, the folder **Add LoRA** opens for every model. One generation through the
app's worker: `build/release/bin/image-generate MODEL OUT.png PROMPT SEED [STEPS]`.

MOSS also takes an **Image prompt** (Generate, MOSS selected): up to four pictures the text encoder
reads beside the prompt, each with its own strength (0-1, default 0.05; 0 leaves it out), a
**Text strength** (default 1) and a **Vision size** (default 384). With no picture and text
strength 1 the result is the ordinary MOSS image. The values save with the other MOSS parameters
(`prompt_images`, `prompt_strength_percent`, `text_strength`, `vision_size`); older files still load.

### Fibo 2.0 Dev in Generate, Fibo 2.0 Edit Turbo in Image Edit (2026-11-05)

**Fibo 2.0** (model 6 on Generate) is Bria's Fibo-2.0-dev text-to-image, run in the MM-Air
process by AIR's `models/fibo2` (`generate.run`): the Qwen3-VL-4B encoder is read once and
closed, the 8.1B transformer is read once and stays resident on the GPU for every step, then
the FLUX.2 VAE decodes. The **Sampling** panel shows Steps (default 50), Guidance (default 5)
and an optional negative prompt (empty uses the model's own); size 256–2048 px in multiples
of 16 (default 1024²). LoRAs from **Model LoRA** run unmerged. Fibo reports no per-step
progress; the elapsed timer runs until it finishes.

**Fibo 2.0 Edit Turbo** is the second entry in Image Edit's **EDIT MODEL** dropdown. Image 1
is the picture to change and up to four more images guide it (PNG or JPEG, five in all); the
instruction box is the edit instruction. It runs the creator's 4 steps at guidance 1. **Keep
the first image's size** (on by default) uses image 1's trained size; untick it to use Width
and Height. The Qwen-only controls (Turbo, prompt enhancer, swaps, schedule, solver, steps)
are hidden while it is selected. Outputs: `output/fibo2/generate` and `output/fibo2/edit`,
schema `mm-air.fibo2.parameters.v1`; Reuse restores Dev runs on Generate and edits on
Image Edit.

Settings: `MM_AIR_FIBO_DEV_ROOT`, `MM_AIR_FIBO_EDIT_TURBO_ROOT` (the published folders) and
`MM_AIR_FIBO_PIPELINE_PRESET` (AIR's `models/fibo2/presets/pipeline.json`). One generation
through the app's worker: `image-generate fibo-2.0-dev OUT.png PROMPT SEED` or
`image-generate fibo-2.0-edit-turbo OUT.png INSTRUCTION SEED 0 SOURCE.png [REF...]`.

### Qwen-Image Turbo and prompt enhancers (2026-10-15)

**Qwen-Image-2.1-Turbo** is the **Turbo (8 steps)** checkbox on Generate (Qwen
Sampling) and Image Edit. It is on by default, keeps your last choice across restarts, and
Reset turns it back on. While it is on:
- it loads the Turbo transformer from `QWEN_IMAGE21_TURBO_ROOT`;
- Steps is fixed at 8 and the schedule dropdown is greyed out;
- it uses the checkpoint's own sigma schedule.

Untick it to run base 2.1 with the chosen schedule and steps. Saved parameters still
record Turbo as scheduler 2, so older saves restore with the box ticked.

A two-reference 2048² edit drops from 6.5 min to under 2 min. The Turbo folder
hardlinks 2.1's text encoder, processor and VAE.

**Generate layout (2026-10-16).** The Generate page has draggable splitters:
- between Parameters and the stage;
- between the stage and History;
- between the image and the prompt dock.

Double-click a splitter handle to collapse or restore the side panel. Each parameter
section has a ▾/▸ header that collapses it. Splitter sizes, collapsed panels and
collapsed sections are remembered in your preferences (`%LOCALAPPDATA%\mm-air\runtime.json`,
`MM_AIR_UI_*` keys), and so is the Turbo checkbox (`MM_AIR_QWEN_TURBO`). This needs the matching `MM-Air-UI.exe` (AIR
`toolkits/desktop/windows/air_ui.cpp`).

**Enhance prompt** checkboxes on Generate and Image Edit (both on by default, Qwen-Image
only) run the model's own 9B prompt rewriter first: Qwen-Image-2.1-PE-T2I (`QWEN_IMAGE21_PE_T2I_ROOT`) or PE-I2I for
  edits (`QWEN_IMAGE21_PE_I2I_ROOT`). These think before answering, so they take
  about 1-2 min. They also choose the aspect ratio (text-to-image) or which source's
  aspect to keep (edits), and the status line reports the size used.

**Qwen-Image weights stay on the GPU.** Each Qwen snapshot (2.1 and Turbo) needs
the resident INT8 transformer that AIR's
`models/qwenimage21/tools/quantize_int8.py SNAPSHOT MANIFEST_DIR` writes to
`SNAPSHOT/transformer-int8/`. It is about 7.5 GB, with one scale per 128 inputs,
and matches the BF16 weights against the creator. MM-Air refuses to run Qwen
without it rather than stream weights every step. On an RTX 5080 a 2048² edit
with a reference runs about 5.5 s per step on Turbo and about 6 s on the 40-step
base model.

**Prompt rewriter speed.** The 9B rewriters decode at about 15 ms per token, so
Qwen's text-to-image and edit enhancers usually take 25-35 s, about 4 s of which
is loading the model.

The rewriter loads, runs and is freed before the image model loads. The
rewritten prompt is saved next to the PNG as `<name>.png.prompt.txt`. Untick the
box to send the prompt exactly as typed at the size you set. All of this runs
natively in AIR (`models/qwen35`); see AIR's
`docs/models/QWEN35.md` and `docs/models/QWEN_IMAGE_2_1.md` for parity evidence.

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
  build/release/bin/mm-air
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

Edit now has **Auto Mask with SAM 3.1** directly below Source. Enter a text concept
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

#### Video swap masks (tracks, People Mask, edit mask, mannequin, check preview)

`swap_masks.ai` is the mask side of the one-click video character swap. One job
turns a source video and a text target (`person` by default) into the files the
H3 generation side reads, listed in `<job>/manifest.json`
(schema `mm-air.swap-masks.v1`):

- **Part to use** (`part`): `whole`, or a length placed at `start`, `middle` or
  `end` with a signed offset, rounded down to H3's 17n+5 frames at 24 FPS and
  clamped inside the source. `part.mp4` holds those frames losslessly
  (libx264rgb, crf 0); `part.wav` is the soundtrack cut sample-exactly at the
  same frame boundaries (`ceil(frame * rate / 24)`), PCM; the source is never
  modified.
- **Tracks** (`tracks`): every instance SAM 3 finds, with its tracker id, and
  per frame its area fraction, score and bounding box. Raw 0/255 planes are in
  `tracks/track-<id>.gray`. The native call is `air_sam3_track_media` in
  `toolkits/sam3`, through `toolkits/sam3/tracks.ai` and `std.cabi`.
- **People Mask** (`people_mask`, `selection`, `selected_track`): chosen per
  frame. The largest instance is the default; the instance with the best IoU
  against the last selected mask is kept while its IoU is at least
  `selection_min_iou` and `selection_switch_area_factor` times its area is at
  least the largest area, so a jump to another figure needs a clear area win.
  This does not rely on the tracker keeping one id per figure. `selection` lists
  the track id per frame (-1 when nothing is found); `selected_track` is the id
  chosen most often. `tracker` names the backend; `prepare_part`, a tracker and
  `finish` are separate stages so another backend can supply the same
  `track-<id>.gray` + `tracks.tsv` files.
- **Edit mask** (`edit_mask`): headroom above the head (each mask pixel also
  covers `round(0.1 * mask bbox height)` pixels above it), a 2-frame trailing
  pose hold, a Euclidean grow, then three clamp-to-edge box blurs. Margins come
  from `presets/swap-masks.json` (installed as `share/mm-air/swap-masks.json`)
  and are stated at a 736-pixel short edge, scaled to the source.
- **Motion reference** (`motion_reference`): the part with the People Mask
  replaced by flat grey (128) with a hard edge; the mask is resampled
  nearest-neighbour and the picture Lanczos to H3's reference canvas
  (`reference_media.video_canvas`, short edge 512/768/1376, at most 768x1344
  pixels).
- **Edit sources** (`edit_source`): Video 1 for the masked H3 edit, at source
  geometry and part length, lossless with the part audio. `silhouette` greys the
  People Mask pixels; `blank` blends every pixel toward the grey by its edit-mask
  weight, `(src*(255-m) + grey*m + 127) / 255`. `video` is the one the preset's
  `edit_source_mode` names (`blank` by default).
- **Check preview** (`check_preview`): orange on the tracked person, cyan by the
  edit-mask weight elsewhere, the mannequin on the right, every frame a key
  frame so it scrubs exactly.

Mask videos are lossless full-range H.264 (`yuvj420p`, crf 0) whose luma is the
mask byte-for-byte; `masked_runtime.decoded_mask` reads them unchanged, so the
edit mask fits the Edit screen's existing mask slot. `tests/swap_masks.ai`
checks every mask operation with exact pixels, the part planning, the track
index, the preset and that round trip. `tests/swap_masks_job.ai` runs one job
from the command line. `parity/sam3_tracks_oracle.py` (official SAM 3 / SAM 3.1,
dev only) and `parity/compare_tracks.py` are the track gate.

### H3 character sheets

Generate includes a native H3 character-sheet preset adapted from
[`PoopMan333/H3_Character_Sheet_Generator`](https://huggingface.co/PoopMan333/H3_Character_Sheet_Generator)
at revision `13c095e84c6d651d49ddcbdb672779cc66a7d44d`. It does not execute that
repository's workflow graph. The preset selects H3 Reference/Ref2VA, supplies
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
- **LoRA root (superseded 2026-10-17, see below).** MM-Air sampled Ref2VA with
  fused ConvRot INT8 kernels that had no LoRA insertion points, so a Python
  merge script (`tools/h3_swap_lora_merge.py`, deleted 2026-10-19) baked
  the LoRA into the official BF16 weights and re-quantized them with the
  difh3convrot H256 recipe into a separate root (junctions and hard links for
  everything else; token-refiner pairs went into a small merged shard).
  Its `verify` re-quantized unmerged blocks and matched the existing cache byte
  for byte for blocks 0 and 49. `MM_AIR_H3_CHARACTER_SWAP_ROOT`
  (Settings or runtime.json) pointed at that root; unmasked swap jobs used it and
  forced ConvRot transformer projection, because only the ConvRot cache carried
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
the target resolution. The H3 encoder's cuDNN
Conv3d workspace cap rose from 64 MiB to 1 GiB, which picks kernels 3.6x faster
per 17x256x256 tile (`tests/video_encode_bench.ai`; moments rel_l2 1.2e-4).
The same job now takes 48 s to encode, 3m04s to sample, and 4m50s end to end
(previously 15m30s). The output was visually equivalent.

### Turbo Character Swap and corrected LoRA layout (2026-10-15)

- **Layout fix.** Single-file community LoRAs (the akatz swap LoRA, lightx2v turbo)
  address fused QKV as contiguous [q;k;v], but the raw official shards
  interleave Q/K/V per head (diffusers `reorder_interleaved_qkv`). FC1 is
  [gate; value] in both. Checked exactly against the Diffusers build of the turbo
  LoRA. The merge script (since deleted) re-interleaved QKV deltas, honoured
  per-projection `.alpha` (scale alpha/rank) and stacked several LoRAs. The first
  `reference-charswap` root was merged without the QKV reorder; use
  `reference-charswap-v2`.
- **Turbo.** `reference-charswap-turbo4` = swap LoRA + lightx2v
  `minimax_h3_ref2v_turbo_4step_v0.1` (shift 12/3, which is exactly MM-Air's
  simple grid at four evaluations). New profile `profile_turbo_4` (four Euler
  evaluations) reads `native-modcache-ref2va[-audio]-steps5-blocks50`, built by
  AIR's `h3-modcache` (`std.inference.h3.modcache`, see AIR `tools/h3/README.md`;
  it replaced the Python `tools/h3_modcache.py` on 2026-10-19 and matches it byte
  for byte when numpy's BLAS runs one thread). It regenerates the shipped 7-step caches with
  99.7% of values bit-identical and the rest within one BF16 ulp. Character Swap
  selects Turbo automatically when `MM_AIR_H3_CHARACTER_SWAP_TURBO_ROOT` is set;
  any 19-evaluation schedule uses `MM_AIR_H3_CHARACTER_SWAP_ROOT`. Turbo is
  refused outside unmasked swap.
- The plain 7-evaluation donor profile is not a shortcut for swaps: on the gate
  clip it copied the source actor for the first ~2.5 s.
- Gate (same clip, seed 555123, matched reference canvas): sampling took 36 s
  instead of 3m04s, 2m42s end to end. Identity, scene and path held, with detail
  comparable to the 19-step render; the turbo pass dropped the carried helmet.

### Character Swap LoRAs as runtime files (2026-10-17)

The swap and turbo LoRAs are no longer merged into checkpoint roots. AIR's H3
ConvRot path now applies PEFT adapters at runtime (`std.inference.h3`
`forward_convrot_lora`), so a new or updated swap LoRA is just a file:

- **Guide-video adapters (character swap v1.1, head swap r32):** in Character Swap, "Source video is used as" chooses
  *Guide video · character swap* or *Guide video · head swap*. The source clip is then packed as an aligned guide beside
  the character pictures (it is not a `<Video 1>` reference), the adapter file named in Settings
  (`MM_AIR_H3_GUIDE_CHARACTER_SWAP_LORA`, `MM_AIR_H3_GUIDE_HEAD_SWAP_LORA`) runs unmerged, and Build Prompt has Qwen describe
  the first picture and fills the adapter's own template (`body_swap:` / `head_swap:`), which stays editable. Output frames
  are `17n + 5`; Turbo is not available with these adapters. The adapters and templates are Alissonerdx's (credit and terms in
  `docs/models/H3.md`).
- **Guide-video edit adapters (VFX edit, style transfer, sharpen):** the same dropdown also lists *Guide video · VFX edit*,
  *style transfer* and *sharpen*. The source clip is an aligned guide; pictures are optional (the edited first frame for the
  `_ffp` VFX adapter, the style picture for style transfer; none for sharpen). Build Prompt sets the adapter's trigger word
  (`vfx_edit:` / `style_transfer:`) in front of your sentence, or the sharpness adapter's fixed caption. Settings:
  `MM_AIR_H3_GUIDE_VFX_EDIT_LORA`, `MM_AIR_H3_GUIDE_STYLE_TRANSFER_LORA`, `MM_AIR_H3_GUIDE_SHARPEN_LORA`. Live wallpaper is
  ordinary Ref2VA with one to three pictures and its LoRA in the Generate LoRA list. Credit and terms: Alissonerdx (see
  `docs/models/H3.md`).
- **Settings:** `MM_AIR_H3_CHARACTER_SWAP_LORA` (the swap LoRA) and
  `MM_AIR_H3_CHARACTER_SWAP_TURBO_LORA` (the 4-step turbo LoRA). Unmasked
  swaps add the swap LoRA, plus the turbo LoRA when Turbo is on, to the job's
  LoRA list and force ConvRot projection; Turbo requires the turbo file.
- **Your own LoRAs** from the Generate LoRA section stack on top. The section is
  shown for Krea 2 and every H3 run, and the one-enabled-LoRA limit is gone.
- `MM_AIR_H3_CHARACTER_SWAP_ROOT` / `_TURBO_ROOT` are no longer read by
  Character Swap, and the merge script `tools/h3_swap_lora_merge.py` was deleted
  (2026-10-19): LoRAs are never merged into base weights.

Gate (RTX 5080 16 GB, 2 s 832x480 Ref2VA, both LoRAs, turbo 4 evaluations):
3/3 runs completed with bit-identical output in about 128 s each (the merged
root took 77 s). The reference identity transferred. This needed the AIR
provider fix for unordered row-gather index uploads (AIR 7afbcc43).

MM-Air now imports H3 and Krea 2 from the standard library
(`std.inference.h3.*`, `std.inference.krea2.*`) after AIR moved model sources
out of `models/`; the `h3` and `krea2` path dependencies were dropped.

### Long Character Swap and Side by Side Movie (2026-10-15)

- **Clips longer than one H3 window.** One H3 pass makes 124 frames (about
  5.2 s). When the Character Swap source is longer, `run_rolling_reference`
  (`generate.ai`):
  - cuts it into consecutive 24 FPS windows of up to 124 frames with ffmpeg;
  - runs each window as an ordinary Ref2VA swap with the same character
    pictures, prompt and seed;
  - joins the outputs with the ffmpeg concat demuxer.

  The progress line shows `H3 rolling window i/n`. A 15 s clip at Custom
  480x832 with Turbo took 11.5 min (three windows, about 50 s of sampling each).
  The joins at 5.2 s and 10.3 s showed no identity or outfit jump.
- **Use 480x832 or 832x480 for long swaps.** At 768x1344 a single window
  packs about 2.6x the tokens and leaves too little room for resident blocks on
  a 16 GB card.
- **Bounded residency.** H3 now keeps as many transformer blocks on the GPU as
  fit after its sampling memory and streams only the rest (see
  `docs/models/H3.md` in AIR, "Sampling residency budget").
- **Side by Side Movie.** A button under the Generate button. It appears when
  the selected result is a video whose parameter sidecar names a source video
  that still exists (Video 1). It writes `<result>-side-by-side.mp4` with:
  - the source on the left, resampled to 24 FPS and scaled to the result's
    height;
  - the result on the right;
  - the result's soundtrack.

  It runs in the background, then adds the movie to Current Generations and
  History.

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

Long clips use `stdlib/inference/h3/timeline.ai` as the single window authority. Every
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
- Model and task follow each other: picking Reference to video selects the
  Reference model, and switching the model from Reference back to Base sets the
  task to Text to video + audio, which needs no pictures.
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

The expanded **H3 Window Plan** uses AIR's shared `std.inference.h3.timeline` geometry.
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
These behaviors are independently implemented in native AIR; no external node or
runtime code is included.

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

The tab uses the reusable AIR [`toolkits/prompt`](../AIR/../AIR/toolkits/prompt/README.md)
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
- Selecting a result shows what made it under the preview: the model, task, size,
  length, steps and seed on one line and the prompt on the next (both selectable).
- Videos in the preview have play/pause, back to start, a seek bar and the time
  (GTK's own controls on Linux, the AIR Windows host's bar on Windows); a click on the
  video also plays or pauses.
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
  bash tests/gallery_selection.sh \
  build/release/bin/mm-air build/release/bin/air-ui "$XVFB" \
  desktop.ui desktop.css "$PNG_A" "$PNG_B"
```

History and thumbnails live under `XDG_DATA_HOME/mm-air`, falling back to
`HOME/.local/share/mm-air`. Requests retain the selected file paths; parameter
files do not bundle the media. Missing restored sources remain visible and their
preview failure is reported. An invalid seed never silently reuses the previous
value.

The linked paths and controls are not, by themselves, numerical or production
parity claims. A saved, inspected MM-Air MP4 remains the delivery evidence.

Build and run (Linux). MM-Air is built by `airproj` from `air.project.json`; AIR sits
beside this repository (`../AIR`, or `AIR_ROOT`) with its tools already built
(`$AIR_ROOT/build-release`, or `AIR_TOOLCHAIN`):

```sh
tools/build-linux.sh            # every declared program -> build/release/bin
build/release/bin/mm-air        # or the launcher that sets the scratch folder
```

The script also links `desktop.ui`, `desktop.css` and `presets/swap-masks.json` into
`build/release/bin/share/mm-air`, where the app reads its screens, and copies AIR's
window host `air-ui` beside the app when it is missing (built once by AIR's
`toolkits/desktop/build.sh`). Windows builds use `tools/build-windows-app.cmd`.

Model locations are settings, saved in `~/.local/share/mm-air/runtime.json`
(`%LOCALAPPDATA%\mm-air\runtime.json` on Windows) from the Settings screen; the same
names can be given as environment variables:

```sh
MM_AIR_H3_CHECKPOINT_ROOT=/models/MiniMax-H3/FL2VA \
MM_AIR_H3_REFERENCE_ROOT=/models/MiniMax-H3/Ref2VA \
MM_AIR_H3_DONOR_ROOT=/artifacts/h3-flref-product \
MM_AIR_H3_MANIFEST_ROOT=/models/MiniMax-H3/air-manifests \
MM_AIR_H3_DEPLOYMENT="$AIR_ROOT/models/h3/presets/h3_deployment.json" \
MM_AIR_H3_APP_PRESET="$AIR_ROOT/models/h3/presets/h3_app.json" \
MM_AIR_PROMPT_MANIFEST_ROOT=/models/Qwen3-VL-8B-Instruct/air-manifests \
  build/release/bin/mm-air
```

The manifest folders are written once per model by AIR's own writers:

```sh
"$AIR_TOOLCHAIN/bin/airc" run "$AIR_ROOT/stdlib/inference/h3/write_manifests.ai" --mode release -- \
  "$AIR_ROOT/models/h3/presets/h3_deployment.json" /models/MiniMax-H3/FL2VA /models/MiniMax-H3/air-manifests
"$AIR_TOOLCHAIN/bin/airc" run "$AIR_ROOT/toolkits/prompt/write_manifests.ai" --mode release -- \
  /models/Qwen3-VL-8B-Instruct/air-manifests
```

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

Checks (from this repository):

```sh
tools/check.sh            # no GPU, model or display: static contract (test_contract.py),
                          # a compile of every hand-run test program, and screen wording
tools/check.sh --tests    # the above, then `airproj test`: builds and runs the declared tests
```

`air.project.json` declares the programs (`targets.bin`), the automatic tests
(`targets.test`) and the programs that are run by hand with inputs (`targets.check`:
verified by `airproj check`, never built). `tests/hand-run.txt` says what each hand-run
program or script needs; the contract fails when a test file is in neither place.

Screen wording is checked against one rule: users are not developers (controls, short
labels and status; no paragraphs, developer words, identifiers or file names). AIR's
`tools/ui-text-check.py` reports what breaks it; `tests/ui-text-baseline.txt` lists the 80
findings that exist today, so only new ones fail. Shorten that list; do not add to it.

Examples of hand-run programs:

```sh
airc=$AIR_TOOLCHAIN/bin/airc
"$airc" run tests/library.ai --mode release -- /path/to/scratch /path/to/video.mp4 /path/to/audio.wav
"$airc" run tests/character_sheet_video.ai --mode release -- /path/to/h3.mp4 /path/to/sheet.png 6

# The playback fixture must be a 10-second video with a real audio stream.
"$airc" run tests/ui_layout.ai --mode release -- \
  "$PWD/build/release/bin/air-ui" "$PWD/desktop.ui" "$PWD/desktop.css" \
  /path/to/video.mp4 /path/to/thumbnail.png
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
MM_AIR_TEST_SCALE=2 bash tests/gallery_selection.sh \
  "$PWD/build/release/bin/mm-air" "$PWD/build/release/bin/air-ui" \
  "$(command -v Xvfb)" \
  "$PWD/desktop.ui" "$PWD/desktop.css" \
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

### MiniMax H3-Image (2026-11-10)

Generate lists **MiniMax H3-Image** (prompt, size, seed, one LoRA with strength, Prompt expander Off / Low / Extra high).
Its sizes are SerenityAir's H3 Image presets: 2048×2048 (default), 2720×1536, 1536×2720, 1024×1024, 4096×4096,
5952×3360, 3552×1184, or Custom (up to 20 MP).
Image Edit lists it as a third model: 1 to 16 pictures in order, keep the first picture's size or set Width and Height,
one LoRA, Prompt expander Off / Low / Extra high / Qwen3-VL 8B. It runs in this process through AIR's
`std.inference.h3image.session` (`h3image.ai`); LoRAs stay unmerged. Folders: `MM_AIR_H3IMAGE_ROOT`,
`MM_AIR_H3IMAGE_AIR_ROOT`, `MM_AIR_H3IMAGE_PE_ROOT` (defaults under `~/models`). If files are missing the screen says so
in one line. Needs an AIR with `std.inference.h3image` (branch work/h3image until merged).

### P-H3-Image (2026-11-11)

Generate lists **P-H3-Image** at the end of the model list (prompt, size, seed, Prompt upsampler on/off). Sizes:
2912×2912 (default), 3360×2496, 2496×3360, 3552×2368, 2368×3552, 3872×2176, 2176×3872, or Custom (sides in
32-pixel steps). Image Edit lists it as a fourth model: 1 to 8 pictures in order, Picture 1 is the one edited; Size is
Picture 1's size or 2048×2048, 2368×1760, 1760×2368, 2496×1664, 1664×2496, 2720×1536, 1536×2720. The model's 8 steps
are fixed; there is no guidance, negative prompt or LoRA control for it. With the Prompt upsampler on, the prompt that
was rendered is written beside the picture as `<picture>.png.prompt.txt` (as for MiniMax H3-Image). It runs in this
process through AIR's `std.inference.ph3image.session` (`ph3image.ai`). Folders: `MM_AIR_PH3IMAGE_ROOT`,
`MM_AIR_PH3IMAGE_AIR_ROOT` (defaults `~/models/P-H3-Image`, `~/models/P-H3-Image-air`). If files are missing the screen
says so in one line. Saved settings use their own schema (`mm-air.ph3image.parameters.v1`); the model takes list
position 8 and no earlier position moved. Test: `ph3image-job OUTPUT.png PROMPT SEED WxH|keep on|off [IMAGE ...]`
(`tests/ph3image_generate.ai`, the worker the two buttons start). Agent assumptions: Custom is limited to 256 px or
more per side and to the area of 2912×2912; 1 GiB of the card is kept free and host memory minus 2 GiB is offered
(the MiniMax H3-Image values).
