# Generate behavior mapping

The behavior reference is MojoDiffusion's Serenity Generate interface. MM-Air
maps those behaviors into native AIR application state and GTK controls; it
does not execute Serenity's JavaScript, server or Mojo model runtime. History
on the right and current results below the preview follow the requested native
layout.

| Behavior | Application implementation |
| --- | --- |
| Prompt, model, geometry and explicit execution choices | `desktop.ui`, `main.ai`, `parameters.ai`; shared model request validation |
| Image/video/audio reference pickers and previews | `main.ai` events; `library.ai` media preparation and thumbnails |
| Reference ordering | `main.ai` selection-preserving earlier/later actions; `library.move_item` whole-record moves |
| Save, Load and Reuse settings | `parameters.ai` versioned H3/Krea JSON; `main.ai` persistence and startup restore |
| Current results and right-side history | `main.ai` ownership; `library.ai` persistent catalog that preserves user media |
| Click-only result selection and playback | `desktop.ui` gallery settings; `main.ai` preview selection; private desktop toolkit playback |
| Selected image reused as H3 reference | Explicit `gen_use_image_reference` action; no automatic generation |
| H3 native generation | `generate.ai` media intake and direct shared H3 session call |
| Krea native generation | `generate.run_krea` and direct shared Krea session call |
| Loading, step/count, decode and save status | Existing worker channel; `main.ai` central status, elapsed display and logs |
| Blank output on Generate | Native Save chooser; selection resumes the request, cancellation submits no worker |

The implementation retains explicit H3 execution-policy selection rather than
importing another application's defaults. The private model packages own model
math, schedules, latent layouts and decoders; they are not included in this
public application repository.

`tests/parameters.ai`, `tests/library.ai`, `tests/ui_layout.ai` and
`tests/gallery_selection.sh` test the corresponding application boundaries.
The gallery test generates only with an explicit opt-in; its default paths are
UI tests, not model inference or numerical-parity evidence.
