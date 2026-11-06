"""DEV GATE ONLY: compare AIR swap-mask tracks (manifest.json) with an oracle
track directory written by sam3_tracks_oracle.py. Reports per-frame IoU of the
selected person (largest summed area on each side, the same rule) and of the
union of all instances, plus instance counts. Writes OUT.tsv, prints a summary.

  python compare_tracks.py MANIFEST ORACLE_DIR OUT.tsv
"""
import json
import os
import sys

import numpy as np


def load_tracks(index_path, root, frames, h, w):
    rows = [l.rstrip("\n").split("\t") for l in open(index_path)][1:]
    ids = sorted({int(r[1]) for r in rows if r and r[0]})
    area = {i: 0 for i in ids}
    for r in rows:
        if r and r[0]:
            area[int(r[1])] += int(r[3])
    masks = {i: np.fromfile(os.path.join(root, f"track-{i}.gray"), np.uint8).reshape(frames, h, w) >= 128
             for i in ids}
    return ids, area, masks


def select_per_frame(ids, masks, f, h, w, factor, min_iou):
    """The swap_masks.select_per_frame rule, for the oracle's tracks."""
    people = np.zeros((f, h, w), bool)
    choice = []
    prev = None
    for k in range(f):
        present = [(int(masks[i][k].sum()), i) for i in ids if masks[i][k].any()]
        if not present:
            choice.append(-1)
            continue
        largest_area, largest = max(present, key=lambda x: (x[0], -x[1]))
        pick = largest
        if prev is not None:
            best_iou, keep, keep_area = 0.0, None, 0
            for area, i in present:
                v = iou(prev, masks[i][k])
                if v > best_iou:
                    best_iou, keep, keep_area = v, i, area
            if keep is not None and best_iou >= min_iou and keep_area * factor >= largest_area:
                pick = keep
        people[k] = masks[pick][k]
        prev = people[k]
        choice.append(pick)
    return people, choice


def iou(a, b):
    u = np.logical_or(a, b).sum()
    return 1.0 if u == 0 else float(np.logical_and(a, b).sum()) / float(u)


def main():
    manifest = json.load(open(sys.argv[1]))
    oracle = sys.argv[2]
    out = sys.argv[3]
    f, h, w = manifest["part"]["frames"], manifest["height"], manifest["width"]
    track_dir = os.path.dirname(manifest["tracks"][0]["raw"])
    a_ids, a_area, a_masks = load_tracks(os.path.join(track_dir, "tracks.tsv"), track_dir, f, h, w)
    o_ids, o_area, o_masks = load_tracks(os.path.join(oracle, "tracks.tsv"), oracle, f, h, w)
    preset = manifest.get("selection_rule", {"switch_area_factor": 2.0, "min_iou": 0.1})
    people = np.fromfile(manifest["people_mask"]["raw"], np.uint8).reshape(f, h, w) >= 128
    if "selection" in manifest:
        # The AIR People Mask must equal the per-frame choices it records.
        for entry in manifest["selection"]:
            k, tid = entry["frame"], entry["track_id"]
            want = a_masks[tid][k] if tid >= 0 else np.zeros((h, w), bool)
            assert np.array_equal(people[k], want), k
        o_people, o_choice = select_per_frame(o_ids, o_masks, f, h, w,
                                              preset["switch_area_factor"], preset["min_iou"])
        a_sel = manifest["selected_track"]
        o_sel = max(set(o_choice) - {-1}, key=o_choice.count)
    else:
        a_sel = max(a_ids, key=lambda i: (a_area[i], -i))
        o_sel = max(o_ids, key=lambda i: (o_area[i], -i))
        assert np.array_equal(people, a_masks[a_sel])
        o_people = o_masks[o_sel]
    sel, uni = [], []
    with open(out, "w") as t:
        t.write("frame\tselected_iou\tunion_iou\tair_instances\toracle_instances\tair_area\toracle_area\n")
        for k in range(f):
            au = np.zeros((h, w), bool)
            ou = np.zeros((h, w), bool)
            na = no = 0
            for i in a_ids:
                if a_masks[i][k].any():
                    na += 1
                    au |= a_masks[i][k]
            for i in o_ids:
                if o_masks[i][k].any():
                    no += 1
                    ou |= o_masks[i][k]
            s = iou(people[k], o_people[k])
            u = iou(au, ou)
            sel.append(s)
            uni.append(u)
            t.write(f"{k}\t{s:.4f}\t{u:.4f}\t{na}\t{no}\t{int(people[k].sum())}\t{int(o_people[k].sum())}\n")
    sel = np.array(sel)
    uni = np.array(uni)
    # Identity-agnostic check: for each oracle track, the AIR track with the
    # largest clip-wide intersection, and the per-frame IoU of that pair.
    print("oracle track -> best AIR track (clip-wide intersection): mean/median/min IoU over frames where either is present")
    for oid in sorted(o_ids, key=lambda i: -o_area[i]):
        inter = {aid: int(np.logical_and(a_masks[aid], o_masks[oid]).sum()) for aid in a_ids}
        best = max(inter, key=inter.get)
        vals = [iou(a_masks[best][k], o_masks[oid][k]) for k in range(f)
                if a_masks[best][k].any() or o_masks[oid][k].any()]
        vals = np.array(vals) if vals else np.zeros(1)
        print(f"  oracle {oid} (mean area {o_area[oid] / (f * h * w):.4f}) -> air {best} "
              f"(mean area {a_area[best] / (f * h * w):.4f}): mean={vals.mean():.4f} "
              f"median={np.median(vals):.4f} min={vals.min():.4f} frames={len(vals)}")
    print(f"frames={f} air_ids={a_ids} oracle_ids={o_ids} air_sel={a_sel} oracle_sel={o_sel}")
    worst = np.argsort(sel)[:5]
    print("worst selected frames: " + ", ".join(f"{int(k)}:{sel[k]:.3f}" for k in worst))
    print(f"selected IoU mean={sel.mean():.4f} median={np.median(sel):.4f} min={sel.min():.4f} "
          f"frames<0.9={int((sel < 0.9).sum())} frames<0.5={int((sel < 0.5).sum())}")
    print(f"union    IoU mean={uni.mean():.4f} median={np.median(uni):.4f} min={uni.min():.4f} "
          f"frames<0.9={int((uni < 0.9).sum())}")


if __name__ == "__main__":
    main()
