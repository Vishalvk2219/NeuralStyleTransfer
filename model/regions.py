"""Prototype: apply the style to chosen parts of a photo only.

Two segmentation models label every pixel as background, hair, skin, clothes or animal. The photo is
stylized once and then blended with the original through a mask, so choosing a different part needs
no extra model run.

  docker run --rm --gpus all -v "<repo>:/work" nst-bench python /work/model/regions.py <run-name>
"""
import functools
import sys

import numpy as np
import onnxruntime as ort
import torch
import torch.nn.functional as F
from PIL import Image, ImageDraw

from compare import HERE, load, stylize

TILE, PAD = 300, 30
# Classes of MediaPipe's selfie_multiclass_256x256 model (Apache-2.0). It is built for photos of people,
# so animals come from a second model and get their own class.
# OBJECT is anything else that stands out in the photo (a boat, a monument), from a third model.
BACKGROUND, HAIR, BODY_SKIN, FACE_SKIN, CLOTHES, OTHERS, ANIMAL, OBJECT = range(8)
COLOURS = torch.tensor([[40, 40, 40], [230, 160, 30], [240, 190, 160], [250, 120, 120], [60, 140, 230],
                        [150, 230, 120], [170, 90, 220], [40, 210, 210]]) / 255
REGIONS = {  # label -> classes that receive the style
    "whole photo": range(8),
    "background only": [BACKGROUND],
    "hair only": [HAIR],
    "clothes only": [CLOTHES],
    "all but face and skin": [BACKGROUND, HAIR, CLOTHES, OTHERS, ANIMAL, OBJECT],
}
# bird, cat, cow, dog, horse, sheep among the 21 Pascal VOC classes of torchvision's DeepLabV3
VOC_ANIMALS = torch.tensor([3, 8, 10, 12, 13, 17])
IMAGENET_MEAN = torch.tensor([0.485, 0.456, 0.406]).view(1, 3, 1, 1)
IMAGENET_STD = torch.tensor([0.229, 0.224, 0.225]).view(1, 3, 1, 1)

segmenter = ort.InferenceSession(str(HERE / "weights/selfie_multiclass_256x256.onnx"))
# U2-Net's small model (Apache-2.0): how much each pixel belongs to whatever stands out in the photo.
salience = ort.InferenceSession(str(HERE / "weights/u2netp.onnx"))


@functools.cache
def animal_segmenter():
    from torchvision.models.segmentation import DeepLabV3_MobileNet_V3_Large_Weights as Weights
    from torchvision.models.segmentation import deeplabv3_mobilenet_v3_large
    return deeplabv3_mobilenet_v3_large(weights=Weights.COCO_WITH_VOC_LABELS_V1).eval()


def parts(photo):
    """Class of each pixel, on a 256x256 grid."""
    photo = photo.cpu()  # the detectors run through ONNX Runtime and a small CPU model
    small = F.interpolate(photo, size=(256, 256), mode="bilinear", antialias=True)
    scores = segmenter.run(None, {segmenter.get_inputs()[0].name: small.permute(0, 2, 3, 1).numpy()})[0]
    labels = torch.from_numpy(scores[0]).argmax(-1)
    # The people model calls a dog "clothes" or "hair". Where the general model sees an animal, it wins.
    with torch.no_grad():
        voc = animal_segmenter()((photo - IMAGENET_MEAN) / IMAGENET_STD)["out"].argmax(1, keepdim=True)
    voc = F.interpolate(voc.float(), size=(256, 256), mode="nearest")[0, 0].long()
    labels[torch.isin(voc, VOC_ANIMALS)] = ANIMAL
    # Whatever else stands out and has no label yet is an object.
    x = (F.interpolate(photo, size=(320, 320), mode="bilinear", antialias=True) - IMAGENET_MEAN) / IMAGENET_STD
    standout = torch.from_numpy(salience.run(None, {salience.get_inputs()[0].name: x.numpy()})[0])
    standout = (standout - standout.min()) / (standout.max() - standout.min() + 1e-8)
    standout = F.interpolate(standout, size=(256, 256), mode="bilinear")[0, 0]
    labels[(standout > 0.5) & (labels == BACKGROUND)] = OBJECT
    return labels


def mask(labels, classes, size):
    m = torch.isin(labels, torch.tensor(list(classes))).float()[None, None]
    # ponytail: the soft edge comes only from upsampling 256px labels. A guided filter using the photo
    # would hug hair and shoulders more tightly; add it when mask edges are the visible problem.
    return F.interpolate(m, size=size, mode="bilinear")


def tile(t):
    img = Image.fromarray((t[0].permute(1, 2, 0).numpy() * 255).round().astype(np.uint8))
    img.thumbnail((10**4, TILE))
    return img


if __name__ == "__main__":
    out = HERE.parent / "research" / sys.argv[1]
    out.mkdir(parents=True, exist_ok=True)
    styles = {p.stem: load(p) for p in sorted((HERE / "data/style").glob("*.jpg"))}
    for name in ("portrait", "astronaut_dogs"):
        photo = load(HERE / f"data/content/{name}.jpg")
        size = photo.shape[2:]
        labels = parts(photo)
        overlay = 0.4 * photo + 0.6 * F.interpolate(COLOURS[labels].permute(2, 0, 1)[None], size=size, mode="nearest")
        columns = ["photo", "detected parts", *REGIONS]
        w = tile(photo).width
        sheet = Image.new("RGB", (len(columns) * w, len(styles) * (TILE + PAD)), "white")
        draw = ImageDraw.Draw(sheet)
        for r, (style_name, style) in enumerate(styles.items()):
            stylized = stylize("samam", name, style_name, photo, style)
            tiles = [photo, overlay]
            for classes in REGIONS.values():
                m = mask(labels, classes, size)
                tiles.append(m * stylized + (1 - m) * photo)
            for c, (label, t) in enumerate(zip(columns, tiles)):
                sheet.paste(tile(t), (c * w, r * (TILE + PAD) + PAD))
                draw.text((c * w + 6, r * (TILE + PAD) + 5), label if c < 2 else f"{style_name}: {label}", fill="black", font_size=18)
            print(f"{name} x {style_name} done", flush=True)
        sheet.save(out / f"{name}.jpg", quality=90)
