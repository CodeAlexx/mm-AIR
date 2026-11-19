# Movie Maker MCP

A native AIR stdio MCP server for MM-Air's Movie Maker: create and edit movie projects, render
shots, follow and stop renders, and join the selected takes into one MP4, without the window.
No Python, Node or MCP SDK is in the server or the worker.

Two programs, built beside `mm-air` in `build/release/bin`:

- `mm-air-movie-mcp` (`mcp/movie_server.ai`): the stdio JSON-RPC server. CPU only, small.
- `mm-air-movie-render` (`mcp/movie_render.ai`): the headless render worker. One process, one H3
  load, the shots of a job one after another. Started by the server under `~/h3-air/bin/gpu-run.sh`
  (the GPU lock and thermal guard), never directly on the GPU.

Both use `movie_project.ai` for the project file (schema `serenity.h3.movie.v1`), the prompt
compiler, take records and the stitch, and `generate.ai` for H3, so a project edited here is the
same file the window reads and writes.

## Build and test

```sh
mcp/build.sh            # both programs (the worker takes minutes: it links the whole H3 runtime)
mcp/build.sh server     # only the server
python3 mcp/tests/protocol_test.py
```

The build uses `$AIR_ROOT` (default `../AIR`) for `airc` and the standard library, sets the CUDA
library path itself and runs under `~/h3-air/bin/capped.sh`. The full app build
(`tools/build-linux.sh`) builds both programs too: they are declared in `air.project.json`.

The protocol test is CPU only. It runs the real worker in its test-fixture mode (an ffmpeg test
clip stands in for H3), in a temporary output folder, and covers framing, every tool, refusals,
write-back of takes in the window's format, continuation, assembly, stop and socket stdin.

## Start

```sh
build/release/bin/mm-air-movie-mcp --allow-render
```

| Option | Default |
|---|---|
| `--allow-render` | off: every tool except `movie_render` works |
| `--output-root DIR` | the window's output folder (`MM_AIR_OUTPUT_ROOT`; empty = home). Projects are in `DIR/movies` |
| `--gpu-run FILE` | `~/h3-air/bin/gpu-run.sh` |
| `--render-bin FILE` | `mm-air-movie-render` next to the server |
| `--cuda-lib DIRS` | `~/cuda/13.2/lib:~/cuda/cudnn-9.27/lib` (the worker's `LD_LIBRARY_PATH`) |
| `--scratch DIR` | `~/mm-air-scratch` (the worker's `TMPDIR`, as `~/mm-air.sh`) |

Claude Code registration (`~/.claude.json`, `mcpServers`):

```json
"mm-air-movie": {
  "type": "stdio",
  "command": "/home/alex/mm-AIR/build/release/bin/mm-air-movie-mcp",
  "args": ["--allow-render"],
  "env": {}
}
```

## Tools

| Tool | Arguments |
|---|---|
| `movie_list` | none |
| `movie_inspect` | `project` |
| `movie_create` | `name`, optional `title`, `project_json` (a whole project), `make_current` |
| `movie_update_project` | `project`, any of `title`, `director_brief`, `continuity_bible`, `brand_bible`, `takes_per_shot`, `target_duration_seconds`, `make_current` |
| `movie_update_shot` | `project`, `shot` (id), `fields` |
| `movie_add_shot` | `project`, optional `fields`, `continue_from_shot` (id of a shot with a finished take) |
| `movie_delete_shot` | `project`, `shot` |
| `movie_render` | `project`, `conditioner_projection`, `transformer_projection`, `attention`, `profile` or `evaluations` + `schedule` + `sampler`; optional `shots` (ids in order), `loras`, `window_seconds`, `overlap_seconds`, `drift` |
| `movie_status` | optional `job` (default newest) |
| `movie_logs` | optional `job`, `limit` |
| `movie_stop` | optional `job`, `mode` = `now` (default) or `after_shot` |
| `movie_assemble` | `project`, optional `output` (absolute .mp4) |

`project` is a file name in the library (`ball` or `ball.serenitymovie.json`) or an absolute
path directly inside it. Shot `fields`: `title`, `brief`, `shot_description`, `soundscape`,
`music`, `prompt_override`, `first_frame`, `last_frame`, `continue_from`, `duration_seconds`,
`width`, `height`, `steps`, `seed` (-1 random), `motion_context_frames`, `references`, `locked`,
`selected_take`. Unknown fields, missing pictures, sizes H3 cannot render and paths outside the
library are refused before anything is written.

## Rendering

`movie_render` routes each shot like the window's Queue take / Render all: a continuation
(`continue_from`) runs Base T2VA with the motion context of the take it continues; cast or shot
references run Reference Ref2VA; a first and/or last frame runs I2VA, FL2VA or L2VA; otherwise
T2VA. Shots longer than `window_seconds` (default 20, overlap 3, the window's defaults) on Base
are rendered in windows. Without `shots` it renders every shot without a finished selected take.
It stops at the first failed shot, as Render all does.

MM-Air never chooses the H3 execution policy, so it must be given. Profiles are the presets'
schedules: `donor_7` (7, simple, res_multistep), `quality_19` (19, simple, euler),
`dc_euler_19` (19, exponential, euler). The 4-step turbo needs Character Swap and is refused.
For 10 s clips on the RTX 3090 use conditioner `convrot_i8`, transformer `row_scaled_i8`,
attention `dense_i8` (a `convrot_i8` transformer runs out of memory at 124+ frames with a LoRA).
The window's Movie tab always uses `convrot_i8` for the conditioner; here it is stated.

Each finished take is written into the project as the window does (takes, take_states,
take_output_paths, selected_take, status, output_path), with a parameters sidecar
(`take.mp4.json`) beside the video in `movies/takes`. A shot that fails inside H3 gets a failed
take, as in the window. One render at a time; it waits for the GPU lock if another GPU job runs.
A render keeps running when the MCP session ends; a new session sees it with `movie_status`.

Job files: `movies/.mcp-jobs/job-<ms>/` holds `request.json`, `status.json`, `log` (the worker's
and the GPU guard's output), the launcher's and the worker's process-group records, and
`stop-after-shot` when `movie_stop` asked for that.

## The window and the project file

Every edit is a fresh read of the file, one change and an atomic write (unique temporary file +
rename); the worker does the same after each take, finding the shot by id. The window does not
watch the file: it keeps the project in memory and writes it back when you edit there. Reopen
the project in the window (Movie library) to see changes made here, and do not edit the same
project in the window while a render from here is running, or the window's next save replaces
the takes written by the render. Like the window, saving rewrites the file in its own format
(for example the unused `assets` list is written empty).

## Limits

- Linux only (the worker launch uses `/bin/sh`, `setsid` and the GPU guard scripts).
- No post-processing (Restore / Upscale), no generate-history entries, no Endless chains, no
  character editing; shots are added at the end (no reordering).
- `movie_stop now` loses the shot being rendered (H3 has no mid-shot cancel); `after_shot` keeps it.
- `movie_assemble` runs ffmpeg in the server call; long movies take a while.
