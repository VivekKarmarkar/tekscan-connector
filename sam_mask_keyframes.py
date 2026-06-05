#!/usr/bin/env python3
"""
SAM mask-outline / glow overlay generator for the Tekscan demo freeze frames.

Uses Ultralytics SAM (MobileSAM by default, ~40MB, fits 8GB easily) with
point + box prompts pinned from niche-library-research:

    from ultralytics import SAM
    model = SAM("mobile_sam.pt")
    r = model(img, points=[x,y], labels=[1], bboxes=[x0,y0,x1,y1], device=...)
    mask = r[0].masks.data   # torch.uint8 (N,H,W) values 0/1
    poly = r[0].masks.xy     # list[np.ndarray] polygon pixel coords

Exports, per target, a TRANSPARENT RGBA PNG at full 1920x720 with a colored
glow + crisp outline of the mask, so the render stage can alpha-composite it
directly onto the corresponding freeze frame.

BEST-EFFORT: on any per-target failure we skip that target and keep going.
"""
import os, sys, json, traceback
import numpy as np

FRAMES = "/home/vivekkarmarkar/Python Files/tekscan-connector/meta/turn-the-existing-15-second-split-b5a894/assets/frames"
OUT    = "/home/vivekkarmarkar/Python Files/tekscan-connector/meta/turn-the-existing-15-second-split-b5a894/assets/masks"
CKPT   = "/home/vivekkarmarkar/Python Files/tekscan-connector/sam_assets/mobile_sam.pt"

os.makedirs(OUT, exist_ok=True)

# hex -> (r,g,b)
def hx(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

# Targets. Each: which frame, a prompt (point and/or bbox), and a glow color.
# Boxes/points are full-frame 1920x720 pixel coords (webcam half = x in [0,960]).
TARGETS = [
    # --- lift-off frame 319: the finger ---
    dict(name="finger", frame=319, color="#FF3C3C",
         points=[[693, 378]], labels=[1],
         bbox=[640, 330, 745, 430]),
    # --- mid-force frame 173: physical setup objects ---
    dict(name="flexiforce", frame=173, color="#3CFF3C",
         points=[[470, 466]], labels=[1],
         bbox=[385, 448, 640, 485]),
    dict(name="cable", frame=173, color="#FFC800",
         points=[[655, 449]], labels=[1],
         bbox=[600, 430, 720, 468]),
    dict(name="blue_box", frame=173, color="#3C78FF",
         points=[[35, 425]], labels=[1],
         bbox=[0, 378, 72, 472]),
    dict(name="adapter", frame=173, color="#FFFFFF",
         points=[[200, 472]], labels=[1],
         bbox=[162, 448, 244, 498]),
]


def frame_path(idx):
    return os.path.join(FRAMES, f"frame_{idx:04d}.png")


def pick_device():
    try:
        import torch
        if torch.cuda.is_available():
            # smoke test: a tiny op on cuda to surface 'unknown error' early
            _ = torch.zeros(8, device="cuda") + 1
            torch.cuda.synchronize()
            return "cuda:0"
    except Exception as e:
        print(f"[device] cuda unusable ({e}); falling back to cpu", flush=True)
    return "cpu"


def best_mask(result, bbox):
    """Pick the mask whose pixels best fall inside the prompt bbox."""
    import torch
    masks = result.masks
    if masks is None or masks.data is None or len(masks.data) == 0:
        return None
    data = masks.data
    if hasattr(data, "cpu"):
        data = data.cpu().numpy()
    data = (data > 0).astype(np.uint8)  # (N,H,W)
    x0, y0, x1, y1 = bbox
    best, best_score = None, -1.0
    for m in data:
        area = m.sum()
        if area == 0:
            continue
        inside = m[y0:y1, x0:x1].sum()
        frac = inside / max(area, 1)            # how much of mask is in the box
        cover = inside / max((y1 - y0) * (x1 - x0), 1)  # box coverage
        score = frac * 0.7 + min(cover, 1.0) * 0.3
        if score > best_score:
            best_score, best = score, m
    return best


def glow_rgba(mask, color, W, H):
    """Build transparent RGBA: soft outer glow + crisp outline of `mask`."""
    import cv2
    rgba = np.zeros((H, W, 4), np.uint8)
    r, g, b = color
    m = (mask > 0).astype(np.uint8) * 255

    # outline = dilated(mask) - eroded(mask) -> a ring following the contour
    k = np.ones((5, 5), np.uint8)
    outline = cv2.subtract(cv2.dilate(m, k, iterations=1),
                           cv2.erode(m, k, iterations=1))

    # soft glow = heavy gaussian blur of the mask, used as alpha falloff outside
    glow = cv2.GaussianBlur(m, (0, 0), sigmaX=9, sigmaY=9)
    glow_only = cv2.subtract(glow, cv2.erode(m, k, iterations=1))  # outside ring
    glow_alpha = (glow_only.astype(np.float32) * 0.45).astype(np.uint8)

    # compose: glow first, then crisp outline on top
    rgba[..., 0] = r
    rgba[..., 1] = g
    rgba[..., 2] = b
    alpha = np.maximum(glow_alpha, outline)  # outline fully opaque (255)
    rgba[..., 3] = alpha
    return rgba


def main():
    try:
        from ultralytics import SAM
        import cv2
    except Exception as e:
        print(f"[fatal] import failed: {e}", flush=True)
        traceback.print_exc()
        return 2

    ckpt = CKPT if os.path.exists(CKPT) else "mobile_sam.pt"
    device = pick_device()
    print(f"[setup] checkpoint={ckpt} device={device}", flush=True)

    try:
        model = SAM(ckpt)
    except Exception as e:
        print(f"[fatal] could not load SAM checkpoint: {e}", flush=True)
        traceback.print_exc()
        return 3

    manifest = {"checkpoint": os.path.basename(ckpt), "device": device,
                "model": "MobileSAM (ultralytics)", "overlays": []}
    ok = 0
    for t in TARGETS:
        name = t["name"]
        fp = frame_path(t["frame"])
        try:
            img = cv2.imread(fp)              # BGR HxWx3
            H, W = img.shape[:2]
            res = model(img, points=t["points"], labels=t["labels"],
                        bboxes=t["bbox"], device=device, verbose=False)
            mask = best_mask(res[0], t["bbox"])
            if mask is None:
                print(f"[skip] {name}: no mask returned", flush=True)
                continue
            rgba = glow_rgba(mask, hx(t["color"]), W, H)
            outpath = os.path.join(OUT, f"mask_{name}_f{t['frame']:04d}.png")
            # cv2 writes BGRA; reorder RGBA->BGRA
            bgra = rgba[..., [2, 1, 0, 3]]
            cv2.imwrite(outpath, bgra)
            area = int((mask > 0).sum())
            ys, xs = np.where(mask > 0)
            bb = [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())] if area else None
            manifest["overlays"].append(dict(name=name, frame=t["frame"],
                                             color=t["color"], png=outpath,
                                             mask_area_px=area, mask_bbox=bb))
            ok += 1
            print(f"[ok] {name}: area={area}px -> {outpath}", flush=True)
        except Exception as e:
            print(f"[skip] {name}: {e}", flush=True)
            traceback.print_exc()

    man_path = os.path.join(OUT, "sam_overlays_manifest.json")
    with open(man_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"[done] {ok}/{len(TARGETS)} overlays -> {man_path}", flush=True)
    return 0 if ok > 0 else 4


if __name__ == "__main__":
    sys.exit(main())
