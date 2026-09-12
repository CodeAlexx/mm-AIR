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

The actual native Generate-to-MP4 run is separate evidence from these focused
tests. See the task handoff for the current artifact and measured result.
The saved one-image/one-video/one-audio Ref2VA request now also completes through
the real native Generate button: 704x384, 48 frames, 2 seconds, both galleries
updated, and persisted parameters identical to the submitted request. App
Generate-to-displayed-result time456800ms; raw audio mean -12.4dBFS. This is
a bounded mixed-reference case, not a claim of maximum-count GPU capacity or
speech intelligibility. See `HANDOFF.md` in the repository root for the receipt.
