# MM-Air

MM-Air is a native desktop application for AI media generation, written in AIR.
Its current focus is MiniMax H3 video generation with audio: a Generate workspace
for prompts, reference media, generation settings, saved results, and playback.

This repository publishes the **MM-Air application source only**. **AIR itself
is private, under development, and not ready for public release.** This is an
early development snapshot, not a standalone, publicly buildable release.

## What MM-Air does

- Runs the AIR-native H3 session directly inside the application process.
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

The interface uses native GTK controls. AIR owns application state and generation;
there is no browser-based generation server, Python model runtime, or separate
model executable. Native media tools handle media preparation and MP4 encoding.

Generate is the active development surface. Movie Maker and ControlNet screens
are not claimed to be complete generation workflows.

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

Native development builds have produced H3 MP4s, including an 832×480,
241-frame result. That does **not** establish complete model parity or production
readiness. Generated audio quality and peak GPU-memory behavior are still being
investigated, and UI interaction fixes remain in progress.

Building this snapshot requires access to the private AIR toolchain, its desktop
SDK, and the AIR-native H3 package, plus separately obtained model assets and
compatible native dependencies. The application manifest and integration CMake
file retain those external dependency references. This repository does not
currently supply a standalone public build or downloadable application release.

No AIR compiler implementation, standard library, GPU provider, H3 model
implementation, private Git history, binaries, model weights, or generated
caches are included here. Publishing MM-Air does not release AIR.

Application sources and native tests are in [`apps/mm-air`](apps/mm-air).
