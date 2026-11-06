"""DEV ORACLE ONLY (never run by MM-Air): official SAM 3 / SAM 3.1 video tracking
on the same raw RGB24 fixture the AIR swap-mask job tracks (<job>/part.rgb).

Writes, like the native toolkit: OUT/track-<id>.gray (frames*W*H, 0/255) and
OUT/tracks.tsv (frame id score area x0 y0 x1 y1).

Run under ~/h3-air/bin/gpu-run.sh with the OneTrainer venv:
  PYTHONPATH=<sam3 src>:<extra site> ~/OneTrainer/venv/bin/python sam3_tracks_oracle.py \
      --raw part.rgb --width W --height H --frames N \
      --prompt person --version sam3|sam3.1 --checkpoint CKPT --out DIR
"""
import argparse
import os

import numpy as np
import torch
from PIL import Image


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--width", type=int, required=True)
    ap.add_argument("--height", type=int, required=True)
    ap.add_argument("--frames", type=int, required=True)
    ap.add_argument("--prompt", default="person")
    ap.add_argument("--version", choices=["sam3", "sam3.1"], required=True)
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--evict-outputs", action="store_true",
                    help="evict each frame's cached outputs after it is read (SAM 3.1 on 24 GB)")
    ap.add_argument("--offload-video", action="store_true",
                    help="keep decoded frames on the CPU (24 GB cards, long SAM 3.1 runs)")
    a = ap.parse_args()

    from sam3.model_builder import build_sam3_predictor

    plane = a.width * a.height * 3
    data = np.fromfile(a.raw, dtype=np.uint8)
    assert data.size == plane * a.frames, (data.size, plane * a.frames)
    frames = [Image.fromarray(data[i * plane:(i + 1) * plane].reshape(a.height, a.width, 3))
              for i in range(a.frames)]

    predictor = build_sam3_predictor(checkpoint_path=a.checkpoint, version=a.version,
                                     use_fa3=False, compile=False,
                                     async_loading_frames=False)
    # Upstream f1647e8d: the base predictor passes offload_state_to_cpu=False,
    # which the SAM 3.1 multiplex init_state does not accept. Drop keywords the
    # model's init_state does not declare (the dropped value is the default).
    import inspect
    init_state = predictor.model.init_state
    accepted = set(inspect.signature(init_state).parameters)

    def filtered_init_state(**kwargs):
        return init_state(**{k: v for k, v in kwargs.items() if k in accepted})

    predictor.model.init_state = filtered_init_state
    session = predictor.handle_request({"type": "start_session", "resource_path": frames,
                                        "offload_video_to_cpu": a.offload_video})
    sid = session["session_id"]
    predictor.handle_request({"type": "add_prompt", "session_id": sid,
                              "frame_index": 0, "text": a.prompt})
    per_frame = {}
    for out in predictor.handle_stream_request({"type": "propagate_in_video",
                                                "session_id": sid,
                                                "evict_cached_frame_outputs": a.evict_outputs}):
        fi = int(out["frame_index"])
        o = out["outputs"]
        ids = np.asarray(o["out_obj_ids"]).reshape(-1)
        masks = np.asarray(o["out_binary_masks"]).astype(bool)
        probs = np.asarray(o.get("out_probs", np.zeros(len(ids)))).reshape(-1)
        per_frame[fi] = (ids, masks, probs)

    os.makedirs(a.out, exist_ok=True)
    all_ids = sorted({int(i) for ids, _, _ in per_frame.values() for i in ids})
    hw = a.height * a.width
    files = {i: open(os.path.join(a.out, f"track-{i}.gray"), "wb") for i in all_ids}
    with open(os.path.join(a.out, "tracks.tsv"), "w") as index:
        index.write("frame\tid\tscore\tarea\tx0\ty0\tx1\ty1\n")
        for fi in range(a.frames):
            ids, masks, probs = per_frame.get(fi, (np.zeros(0), np.zeros((0, a.height, a.width), bool), np.zeros(0)))
            have = {int(i): k for k, i in enumerate(ids)}
            for i in all_ids:
                if i in have:
                    m = masks[have[i]]
                    assert m.shape == (a.height, a.width), m.shape
                    files[i].write((m.astype(np.uint8) * 255).tobytes())
                    area = int(m.sum())
                    if area:
                        ys, xs = np.nonzero(m)
                        index.write(f"{fi}\t{i}\t{float(probs[have[i]]):.6f}\t{area}\t"
                                    f"{xs.min()}\t{ys.min()}\t{xs.max()}\t{ys.max()}\n")
                else:
                    files[i].write(b"\0" * hw)
    for f in files.values():
        f.close()
    print(f"oracle {a.version}: {len(all_ids)} ids, {len(per_frame)} frames with output")
    predictor.handle_request({"type": "close_session", "session_id": sid})
    torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
