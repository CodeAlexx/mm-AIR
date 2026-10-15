# MM-Air Movie Maker parity map

Authoritative reference inspected on 2026-09-13:

- `/home/alex/mojodiffusion/serenity-server/canvas/js/h3-project.js`
- `/home/alex/mojodiffusion/serenity-server/canvas/js/h3-studio.js`
- `/home/alex/mojodiffusion/serenity-server/canvas/index.html`

MM-Air keeps the product inside one AIR-native desktop process. Serenity's DOM,
local-storage, HTTP submission, Rust server and Mojo worker boundaries are not
copied into MM-Air.

| Serenity behavior | Native AIR destination | State |
| --- | --- | --- |
| `serenity.h3.movie.v1` project | `movie_project.ai` encode/decode/autosave | Working; imports a real Serenity project |
| Project bibles and controls | `desktop.ui` + `main.ai` | Working |
| Shot deck; add/duplicate/delete/select | `movie_project.ai` + native `GtkListBox` | Working |
| Brief, shot plan, sound and prompt | `movie_project.compile_prompt` | Working |
| T2VA/I2VA/FL2VA/L2VA/Ref2VA precedence | `main.ai` queue routing + `models/h3/session.ai` | Working; a lone ending frame uses the Base model's native last-keyframe anchor |
| Qwen Director | AIR Qwen3-VL 8B `prompt_lab.run` | Working; H3 stays blocked until Qwen fully unloads |
| Multiple takes and selected take | `Shot.takes`, take list and monitor | Working |
| Render all | UI `render_all` + sequential native button activation | Working; one GPU job at a time |
| Continue selected take | `motion_context.ai` + four-class packed denoise layout | Working; the selected take's compact latent A/V tail is consumed directly, trimmed from delivery, and replaced with a fresh sidecar at the next cut |
| Export project/edit | Native save dialog + `serenity.h3.edit.v1` | Working |
| Assemble selected takes | `movie_project.stitch` | Working; normalizes CFR video/audio before concatenation |
| Browser local-storage/server project library | Native file-backed Projects popover | Working; New and Import add durable projects, selection reopens them, and Delete moves one project to Trash while retaining at least one |
| Cast/character-sheet project library | Shared Cast inspector and project character bible | Working; cast images lead shot references, identity/role text compiles into the H3 prompt, and cast identity overrides conflicting prose |
| Endless one-hour continuation chain | Native Start/resume/stop controller | Working; 5–15 second segments run strictly one at a time through Motion Context, persist after every segment, and cap the requested target at 3,600 seconds |

`tests/motion_context.ai` freezes the compact-tail and four-class layout
contract. `tests/movie_continuation_generate.ai` is the bounded production gate:
it renders one five-second native take on the GPU, continues it from the latent
sidecar for another five seconds, stitches both selected takes, and leaves all
three MP4s for audiovisual inspection.

## Production GPU evidence

The bounded gate passed on 2026-09-13 with the native CUDA H3 session:

- `shot-01.mp4`: H.264 256x256 at 24 FPS plus stereo AAC at 32 kHz, 5.000 s.
- `shot-02.mp4`: generated from `shot-01.mp4.airh3ctx` with the same stream
  shape, 5.000 s.
- `movie.mp4`: normalized H.264 1344x768 at 24 FPS plus stereo AAC at 48 kHz,
  10.000 s.
- Final movie SHA-256:
  `3c267db539e4ae41a307bf1dc339782334a656b32d3973a3cb9e8b3d0fef8363`.

Artifacts and the visually inspected seam/contact sheet are under
`output/movie-gpu-gate-20260913/`. Both takes contain non-silent audio; visual
inspection confirmed the same fairy robot, wings, silhouette and garden across
the native latent seam.
