# Generate source mapping

Behavior reference: MojoDiffusion `serenity-server/canvas/js/generate.js`.
The native MM-Air port does not run the Serenity server, JavaScript, or Mojo.
Placement follows the owner's explicit request: history right, current results
bottom, regardless of the reference application's panel placement.

| Reference behavior | MM-Air implementation |
| --- | --- |
| Source controls, `generate.js:799-807` | `desktop.ui` source/reference controls; `main.ai` add/remove and preview events |
| Ordered media, `h3ReferenceKind`, `h3ReferenceCounts`, `renderH3References` | `request.ai` nine visual / three audio limit; `main.ai` ordered arrays; `library.ai` thumbnails |
| Move reference earlier/later, `generate.js:2704-2716` | `desktop.ui` visual/audio up/down buttons; `main.ai` selection-preserving events; `library.move_item` whole-record swap; native desktop regression in `tests/gallery_selection.sh` |
| Reuse result settings, `generate.js:1060`, `applyParams` | `parameters.ai` versioned JSON; `main.ai` Save, Load, Reuse and startup restore |
| Current result and history, `generate.js:91-97,1090-1098` | `main.ai` current/history ownership; `library.ai` atomic persistent catalog |
| Selected image reused as H3 reference | `main.ai` explicit `gen_use_image_reference` action appends the original image, selects Ref2VA, and preserves prompt, seed, geometry, references, and execution settings; it does not start generation or select a schedule, so an unselected profile still fails closed; `library.prep_output` accepts both image and video history; `tests/gallery_selection.sh` image-reference mode drives the actual GTK action |
| Video preview | Existing desktop toolkit `GtkVideo`; advancing playback and clean shutdown tested by `tests/ui_layout.ai` |
| Editable output geometry | Shared H3 `request.set_geometry` → `media.geometry` → geometry-aware native session and decoder |
| Creator keyframe resize | Mojo `minimax_h3_keyframe_image.mojo` → AIR H3 `image_input.ai`; five native-oracle RGB byte-exact fixtures |
| Mixed Ref2VA conditioning | AIR H3 `presentation.ai`, `packing.ai`, `conditioning.ai`, `vae.ai`, `audio_encode.ai`; `generate.ai` handles media intake |
| Krea image generation and reference reuse | Shared AIR Krea `session.ai` through `generate.run_krea`; owned task completion populates the same image history and explicit H3 reference action |
| Explicit H3 exponential schedule | Saved profile ID 3 maps to the existing `session.Schedule.Exponential`; W8A8 transformer and all-step dense INT8 attention have separate explicit IDs |
| H3 character-sheet workflow | `character_sheet.ai` adapts `PoopMan333/H3_Character_Sheet_Generator` revision `13c095e84c6d651d49ddcbdb672779cc66a7d44d`: exact 4/6-panel geometry, fixed orbit/Anime-to-Real prompts, fixed frame picks, and six-pixel black-gutter stitching; `desktop.ui`/`main.ai` expose and apply the Ref2VA preset; `generate.ai` retains the MP4 and returns the stitched PNG |
| H3 Character Swap | `character_swap.ai` builds the dedicated Qwen3-VL CharacterSwap request with source `<Video 1>` and identity `<Picture 1…N>` roles; `desktop.ui`/`main.ai` keep target/media state distinct, populate the editable prompt, require Qwen teardown, and submit the original ordered files to H3 Ref2VA |
| H3 Masked Character Swap | `masked_edit.ai` cleans soft masks, keeps an opaque removal core, plans stable crops, maps 5+17k delivery frames through H3's 2+5k latent geometry and 2x2 spatial token groups, and supports a crop-local target matte; `generate.ai` runs replacement Ref2VA, tracks that result with same-process SAM 3, runs sequential background-only Ref2VA, and asks `masked_runtime.ai` to composite reconstructed background under the expanded old-subject matte plus the replacement under its tighter new-subject matte; missing masks and full-frame fallback remain hard errors |
| Separate Edit workspace | `desktop.ui`/`main.ai` retain source, imported/freehand mask, references, prompt and crop settings; native GtkVideo events drive the scrubber, frame step and synchronized mask-video seek; Prompt Lab and Generate can send state to Edit; Preview Crop and Run Localized Edit use the same linked in-process H3 preparation for video or a bounded 22-frame still wrapper that publishes PNG |
| H3 Video Outpaint | `outpaint.ai` owns source/target placement, directional generated regions, Exact Source/Blended masks, authoritative window spans, Qwen Outpaint requests, and sidecars; `outpaint_runtime.ai` pads/slices/stitches local media, exports only the previous visual tail, exact-composites source RGB, and remaps untouched source audio; `generate.run_outpaint` runs sequential native Ref2VA windows and records the honest `decoded-tail-reference` fallback because Ref2VA direct latent carry is not implemented |
| H3 Director windows and AV slicing | AIR `models/h3/timeline.ai` is used by H3 request validation and Prompt Lab `director.ai`; it emits ordered frame/video-latent/audio-latent spans, clamps per-window source/reference ranges without restarting, and preserves audio independently for visual-only edits. The current sampler truthfully remains one full-request window. |
| H3 targeted repair and motion repair | Reusable `toolkits/h3-repair` owns RepairPlan, MotionPlan JSON/heatmap, deterministic native motion analysis, H3-token snapping, temporal/spatial/two-matte RGB splice, and continuation utilities. `repair_runtime.ai` prepares only the affected Ref2VA window, restores source-world timing, remuxes source audio, asserts every decoded frame outside the repair range, and supports sequential Rolling mode with streaming ConvRot INT8 transformer weights. When a source mask is present, `generate.ai` automatically tracks the generated subject through the same native SAM 3 loader before two-matte background recovery. Rejected latent insertion is not shipped. |
| H3 selective physical clock | `models/h3/timing.ai` retains the research implementation and same-seed harness, but the 2026-09-13 matrix rejected selective physical/compact policies for severe blur. Edit exposes only stock H3 timing; failed research presets are not product-selectable. |
| Movie continuation drift control | Native Motion Context can schedule-match only carried video condition rows with a validated latent-step taper. Existing fixed audio-latent context remains separate and is not touched by video drift control. |

Only Generate (H3 and the requested Krea reference-image path) is in scope. Existing Movie Maker/ControlNet presentation is
not newly wired here. The UI retains explicit execution-policy selection; it
does not import Serenity's defaults. Original media paths are saved, not copied
into parameter files. A missing source is reported, not silently discarded.

## Evidence boundaries

- `tests/parameters.ai`: all fields, exact i64 seed, ordered nine visual / three
  audio paths, schema/version and excessive-reference rejection. Fractional
  durations (5.125, 7.5, 10.25, 12.75 seconds) round-trip across landscape and
  portrait geometry; 2.3125 seconds retains the requested value while restoring
  the nearest 24-FPS delivery count of 56 frames. These are persistence checks,
  not evidence of GPU capacity at every tested resolution.
- Krea's separate parameter schema retains its PNG output, exact seed, prompt,
  and the currently ported 1024x1024/eight-step recipe. Krea GPU generation is
  verified through the native Generate action, including a selected-LoRA run;
  this is saved-artifact evidence, not full numerical parity.
- `tests/library.ai`: real image/video/audio thumbnails, history round trip,
  catalog clearing preserves user media.
- `tests/ui_layout.ai`: native GTK populated galleries, controls, and advancing
  playback; no inference is claimed by this test.
- H3 `tests/presentation.ai`: full visual spans and MRoPE positions above 2048
  tokens are retained; the bound comes from the official Qwen checkpoint's
  262144-token context, not a smaller application cap.
- H3 `tests/reference_video_encode.ai`: official 17-frame encoder runs without
  model-side synchronization workarounds. Strict donor numerical equality is
  still failed; the test records the measured differences and reduction-block
  mismatch. Operational encoding is not a full-parity claim.
- `tests/character_sheet.ai`: exact preset geometry, frame indices, prompt
  markers, panel ordering, dimensions, and gutters. The native video harness
  extracted six frames from the existing 768×768/120-frame H3 MP4 and produced
  an inspected 2316×1542 PNG. The fixture was not an orbit-prompt generation,
  so this does not admit character-orbit quality.
- `tests/character_swap.ai`: source/identity role ordering, selected-person
  fail-closed behavior, six-section syntax, and source-first H3 reference wiring.
  `tests/character_swap_4b_smoke.ai` additionally admitted a real bounded-video
  Qwen3-VL 4B prompt and confirmed complete unload. This is prompt-build evidence,
  not a decoded H3 character-replacement quality result.
- `tests/masked_edit.ai`: generic soft-mask cleanup, opaque feather core,
  deterministic stable crop, crop/uncrop, H3-aware latent/token mapping,
  crop-local target-matte insertion, and exact zero-weight source-byte
  preservation before codec encoding.
- `tests/masked_runtime.ai`: bounded real FFmpeg intake, working-crop preparation,
  full-canvas composite, and MP4 encode for four 320x256 frames; this is
  codec/orchestration evidence and deliberately
  does not load H3 or claim final edited-video quality.
- `tests/outpaint.ai` and `tests/outpaint_runtime.ai`: directional placement,
  exact and bounded seam masks, window/source spans, Qwen roles, sidecar fields,
  target-canvas preparation, 24-FPS delivery count, source-audio presence, and
  decoded saved-file RGB equality inside the preserved rectangle.
- `tests/outpaint_generate.ai`: a real two-window native Ref2VA receipt at
  384x256 and 56 frames. Window 2 consumed the video-only decoded tail from
  window 1; the final file retained 56 frames plus AAC and its decoded 256x256
  preserved rectangle matched the source byte-for-byte. This is bounded
  outpaint evidence, not direct Ref2VA latent-carry evidence.

The actual native Generate-to-MP4 run is separate evidence from these focused
tests. See the task handoff for the current artifact and measured result.
The saved one-image/one-video/one-audio Ref2VA request now also completes through
the real native Generate button: 704x384, 48 frames, 2 seconds, both galleries
updated, and persisted parameters identical to the submitted request. App
Generate-to-displayed-result time456800ms; raw audio mean -12.4dBFS. This is
a bounded mixed-reference case, not a claim of maximum-count GPU capacity or
speech intelligibility. See `HANDOFF.md` in the repository root for the receipt.
