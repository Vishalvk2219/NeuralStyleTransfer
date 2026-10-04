"""Quality comparison: every photo in data/content with every style in data/style, one column per method.

Writes one contact sheet per photo to research/<run-name>/, which is tracked in git.

  docker run --rm --gpus all -v "<repo>:/work" nst-bench \
      python /work/model/compare.py <run-name> <method,method,...> [photo or style names to keep]

Methods: samam, samam4, nnst, microast (see METHODS near the bottom). Do not run nnst here: see CLAUDE.md.
"""
import functools
import importlib.util
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image, ImageDraw

HERE = Path(__file__).parent
CACHE = HERE / "cache"  # git-ignored raw results, so later experiments reuse them instead of re-running models
HEIGHT = 512
device = "cuda" if torch.cuda.is_available() else "cpu"


def to_tensor(img):
    return torch.from_numpy(np.asarray(img, np.float32) / 255).permute(2, 0, 1)[None].contiguous()


def to_image(t):
    return Image.fromarray((t[0].cpu().permute(1, 2, 0).numpy() * 255).round().astype(np.uint8))


def load(path):
    img = Image.open(path).convert("RGB")
    # Multiples of 8: SaMam works on 8px patches, MicroAST halves the size twice.
    return to_tensor(img.resize((round(img.width * HEIGHT / img.height / 8) * 8, HEIGHT)))


def stylize(method, photo_name, style_name, content, style):
    """Result of METHODS[method] for this pair, from the cache when it has been computed before."""
    path = CACHE / method / f"{photo_name}_{style_name}.png"
    if path.exists():
        return to_tensor(Image.open(path)).to(content.device)
    tic = time.time()
    result = METHODS[method](content.cpu(), style.cpu())
    assert result.shape == content.shape, (method, result.shape, content.shape)
    print(f"{photo_name} x {style_name}: {method} took {time.time() - tic:.1f}s", flush=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    to_image(result).save(path)
    return result.to(content.device)


# --- SaMam (2025). Pure PyTorch path; the authors' faster path needs the compiled mamba-ssm package.

@functools.cache
def samam_model(patch):
    sys.path.insert(0, "/opt/SaMam")
    from MODEL.SaMam_model import SaMam

    ckpt = HERE / f"weights/SaMam_patchsize_x{patch}.ckpt"
    state = torch.load(ckpt, map_location="cpu", weights_only=True)["state_dict"]
    # The compiled mamba-ssm kernel is far faster and lighter on memory than the pure-PyTorch scan.
    model = SaMam(patch_size=patch, mamba_from_trion=int(importlib.util.find_spec("mamba_ssm") is not None))
    model.load_state_dict({k[len("model."):]: v for k, v in state.items() if k.startswith("model.")})
    return model.to(device).eval()


def samam(content, style, patch=8, style_side=256):
    # The authors resize the style so its shorter side is 256, the size the model was trained at.
    h, w = style.shape[2:]
    k = style_side / min(h, w)
    style = F.interpolate(style, size=(round(h * k / 8) * 8, round(w * k / 8) * 8), mode="bilinear", antialias=True)
    with torch.no_grad():
        return samam_model(patch)(content.to(device), style.to(device)).clamp(0, 1).cpu()


def samam4(content, style):
    """The authors' second checkpoint, which works on 4px patches instead of 8px."""
    return samam(content, style, patch=4)


# --- NNST (2022). An optimisation method with nearest-neighbour feature matching.
#     Settings are the authors' defaults from their styleTransfer.py.

@functools.cache
def nnst_features():
    sys.path.insert(0, "/opt/NNST")
    from pretrained.vgg import Vgg16Pretrained

    cnn = Vgg16Pretrained().to(device)
    return lambda x, inds, concat: cnn.forward(x, inds=inds, concat=concat)


def nnst(content, style):
    phi = nnst_features()
    from utils.stylize import produce_stylization  # NNST's own `utils` package, on the path via nnst_features

    torch.manual_seed(0)
    out = produce_stylization(content.to(device), style.to(device), phi, max_iter=200, lr=2e-3,
                              content_weight=0.25, max_scls=4, flip_aug=True)
    return out.detach().clamp(0, 1).cpu()


# --- MicroAST (2023), through the ONNX file the browser test page uses.

@functools.cache
def microast_session():
    import onnxruntime as ort
    return ort.InferenceSession("/site/microast.onnx")


def microast(content, style):
    feeds = {"content": content.numpy(), "style": style.numpy(), "alpha": np.array(1.0, np.float32)}
    return torch.from_numpy(microast_session().run(None, feeds)[0])


# --- VGG19, used by enhance.py to measure texture.

@functools.cache
def vgg():
    from torchvision.models import VGG19_Weights, vgg19
    return vgg19(weights=VGG19_Weights.IMAGENET1K_V1).features[:30].to(device).eval().requires_grad_(False)


METHODS = {"samam": samam, "samam4": samam4, "nnst": nnst, "microast": microast}


def sheet(path, content, rows, labels):
    w, pad = content.shape[3], 34
    img = Image.new("RGB", (len(labels) * w, len(rows) * (HEIGHT + pad)), "white")
    draw = ImageDraw.Draw(img)
    for r, (style_name, *results) in enumerate(rows):
        for c, (label, t) in enumerate(zip(labels, (content, *results))):
            tile = to_image(t)
            tile.thumbnail((w, HEIGHT))
            img.paste(tile, (c * w, r * (HEIGHT + pad) + pad))
            draw.text((c * w + 8, r * (HEIGHT + pad) + 6), f"style: {style_name}" if label == "style" else label,
                      fill="black", font_size=20)
    img.save(path, quality=90)


if __name__ == "__main__":
    out = HERE.parent / "research" / sys.argv[1]
    methods = sys.argv[2].split(",")
    only = set(sys.argv[3:])  # photo and style names to keep; an empty set keeps everything
    out.mkdir(parents=True, exist_ok=True)
    photos = sorted((HERE / "data/content").glob("*.jpg"))
    styles = sorted((HERE / "data/style").glob("*.jpg"))
    photos = [p for p in photos if p.stem in only] or photos
    styles = [p for p in styles if p.stem in only] or styles
    print(f"device: {device}", flush=True)
    for path in photos:
        content, rows = load(path), []
        for style_path in styles:
            style = load(style_path)
            rows.append((style_path.stem, style,
                         *(stylize(m, path.stem, style_path.stem, content, style) for m in methods)))
        sheet(out / f"{path.stem}.jpg", content, rows, ("photo", "style", *methods))
