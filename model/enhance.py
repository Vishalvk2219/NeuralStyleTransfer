"""The quality enhancer, and the experiments that shaped it (research/quality-checklist.md).

Every step uses only the photo and the stylized result. Each experiment writes, per photo and style
pair, a sheet of full images and a sheet of 2x close-ups to research/<run-name>/.

  docker run --rm --gpus all -v "<repo>:/work" nst-bench python /work/model/enhance.py <run-name> <experiment>

Experiments: artifacts (005), texture (006), colour (007), edges (008), auto and all (009),
crafted, all-crafted and measure (010), finer (011), surface and all-sheet (012), variation and
all-gated (014), all-colour (015), patterns and all-pattern (016), all-placed (017).
"""
import itertools
import sys

import torch
import torch.nn.functional as F
from PIL import Image, ImageDraw

from compare import HERE, METHODS, device, load, samam, samam4, sheet, stylize, to_image, vgg
from regions import (ANIMAL, BACKGROUND, BODY_SKIN, CLOTHES, COLOURS, FACE_SKIN, HAIR, IMAGENET_MEAN,
                     IMAGENET_STD, OBJECT, OTHERS, mask, parts)

SHIFTS = [(0, 0), (4, 4), (2, 6), (6, 2)]
LUMA = torch.tensor([0.299, 0.587, 0.114]).view(1, 3, 1, 1)
# Two sets of settings. Per part of the photo: how much of the model's fine pattern it gets, and how
# much of its own colour it keeps. Then: how much of the photo's light and dark is kept, and how
# strongly the boundaries between things are drawn.
# PROTECT keeps people, animals and objects close to the photo (experiment 009). It is an option.
PROTECT = dict(
    texture={BACKGROUND: 0.6, OTHERS: 0.6, CLOTHES: 0.6, HAIR: 0.3, ANIMAL: 0.3, OBJECT: 0.3, FACE_SKIN: 0.0, BODY_SKIN: 0.0},
    own_colour={FACE_SKIN: 1.0, BODY_SKIN: 1.0, ANIMAL: 1.0, OBJECT: 0.7, HAIR: 0.5},
    keep_light=0.5, mottle=1.0, outline=0.0)
# FIRST_TRY put the style on everything by turning PROTECT's settings up (experiment 010). It gave
# animals pink blotches, because the model's mid-sized patches were all still there.
FIRST_TRY = dict(
    texture={BACKGROUND: 0.7, OTHERS: 0.6, CLOTHES: 0.6, OBJECT: 0.5, ANIMAL: 0.45, HAIR: 0.45, BODY_SKIN: 0.3, FACE_SKIN: 0.25},
    own_colour={FACE_SKIN: 0.25, BODY_SKIN: 0.25},
    keep_light=0.7, mottle=1.0, outline=0.0)
# CRAFTED puts the style on everything as one even tint per object, without the patches. The default.
CRAFTED = dict(
    texture={BACKGROUND: 0.6, OTHERS: 0.5, CLOTHES: 0.5, OBJECT: 0.4, HAIR: 0.35, ANIMAL: 0.3, BODY_SKIN: 0.2, FACE_SKIN: 0.15},
    own_colour={},
    keep_light=0.3, mottle=0.0, outline=0.0)
SUBJECT_PARTS = [FACE_SKIN, BODY_SKIN, HAIR, ANIMAL, OBJECT]
CROP, ZOOM, PAD = 200, 2, 30


def shift_average(method, content, style, shifts=SHIFTS):
    """Run `method` on shifted copies of the photo and average the results back in place.

    A pattern locked to the model's 8px patch grid lands somewhere else each time and cancels out.
    Anything that follows the photo stays. Costs one model run per shift.
    """
    h, w = content.shape[2:]
    padded = F.pad(content, (8, 8, 8, 8), mode="reflect")
    total = 0
    for dy, dx in shifts:
        out = method(padded[..., dy:dy + h + 8, dx:dx + w + 8], style)
        total = total + out[..., 8 - dy:8 - dy + h, 8 - dx:8 - dx + w]
    return total / len(shifts)


def lum(x):
    return (x * LUMA.to(x.device)).sum(1, keepdim=True)


def box(x, r):
    """Mean over a (2r+1) square window, from running sums, so the cost does not grow with r."""
    k = 2 * r + 1
    sums = F.pad(F.pad(x.double(), (r, r, r, r), mode="reflect").cumsum(2).cumsum(3), (1, 0, 1, 0))
    return ((sums[..., k:, k:] - sums[..., :-k, k:] - sums[..., k:, :-k] + sums[..., :-k, :-k]) / k ** 2).to(x.dtype)


def guided_filter(photo, x, r=6, eps=4e-3):
    """Smooth `x` where the photo is smooth and keep it where the photo has an edge (He et al. 2010)."""
    # ponytail: the guide is brightness only, so an edge between two colours of equal brightness is not
    # protected. Use the colour-guide form of the filter if that shows up as smeared boundaries.
    guide = photo.mean(1, keepdim=True)
    mean_g, mean_x = box(guide, r), box(x, r)
    a = (box(guide * x, r) - mean_g * mean_x) / (box(guide * guide, r) - mean_g ** 2 + eps)
    b = mean_x - a * mean_g
    return box(a, r) * guide + box(b, r)


def split(photo, change):
    """Split the change the style made into three scales, each following the photo's edges.

    even    one tint per object, varying only with that object's own shading
    mottle  patches a few dozen pixels across, which the model places arbitrarily
    fine    the model's fine pattern
    """
    smooth = guided_filter(photo, change)
    even = guided_filter(photo, change, r=32, eps=1e-3)
    return even, smooth - even, change - smooth


def enhance(photo, result, texture=0.0, keep_light=0.0, mottle=1.0):
    """Clean a stylized result without losing the photo's detail.

    The style is treated as a change made to the photo. Only that change is filtered, so the photo's
    own detail is never touched.
      texture     share of the model's fine pattern to return: 0 is clean, 1 is the raw result
      keep_light  share of the photo's own light and dark to keep, so areas that differed in
                  brightness in the photo still differ in the result
      mottle      share of the model's mid-sized patches to keep. On fur and skin they look like stains.
    Each may be a number or a per-pixel map of shape 1x1xHxW.
    """
    even, patches, fine = split(photo, result - photo)
    tint = even + mottle * patches
    tint = tint - keep_light * lum(tint)
    return (photo + tint + texture * fine).clamp(0, 1)


def keep_colour(photo, result, amount):
    """Return `amount` of the photo's own colour to the result, leaving the result's brightness alone."""
    own_colour = (photo + lum(result) - lum(photo)).clamp(0, 1)
    return result + amount * (own_colour - result)


def step_map(x):
    """Colour step between each pixel and its right and lower neighbours, largest of the three channels."""
    dx = F.pad(x[..., :, 1:] - x[..., :, :-1], (0, 1, 0, 0))
    dy = F.pad(x[..., 1:, :] - x[..., :-1, :], (0, 0, 0, 1))
    return (dx ** 2 + dy ** 2).sqrt().amax(1, keepdim=True)


def prominent_edges(photo):
    """0..1 map of the boundaries between things in the photo.

    Measured at quarter size, where fur, freckles and ripples have averaged away and only the edges
    that separate one object from another remain. Uses colour, so two colours of equal brightness
    still count. The scale is absolute: experiment 008 measured edges relative to the image, and a
    photo of rippling water came out as nearly all edge.
    """
    step = step_map(F.avg_pool2d(photo, 4))
    strength = ((step - 0.05) / 0.15).clamp(0, 1)  # a colour step of 0.05 is ignored, 0.2 counts fully
    return F.interpolate(strength, size=photo.shape[2:], mode="bilinear")


def outline(photo, out, strength):
    """Darken a thin line along the boundaries between things, like a drawn outline.

    `strength` may be a per-pixel map, so that faces can be left without lines.
    """
    flat = guided_filter(photo, photo, r=4, eps=1e-2)  # full size, with fine texture flattened
    line = ((step_map(flat) - 0.03) / 0.09).clamp(0, 1) * prominent_edges(photo)
    return out * (1 - strength * line)


def part_map(photo, labels, amounts):
    """Per-pixel setting from a value per part, with boundaries that follow the photo's own edges."""
    if not amounts:
        return 0.0
    blocky = sum(amount * mask(labels, [cls], photo.shape[2:]) for cls, amount in amounts.items())
    return guided_filter(photo, blocky.to(photo.device), r=8, eps=1e-3).clamp(0, 1)


def has_subject(labels):
    return torch.isin(labels, torch.tensor([FACE_SKIN, ANIMAL])).float().mean() > 0.005


def enhance_auto(photo, result, labels=None, settings=CRAFTED):
    """Apply a set of settings without any choices from the user.

    Texture and own colour are set per part of the photo, texture is kept off the boundaries between
    things, some of the photo's own light and dark is kept, and boundaries may be drawn in.
    """
    labels = parts(photo) if labels is None else labels
    texture = part_map(photo, labels, settings["texture"]) * (1 - prominent_edges(photo))
    out = enhance(photo, result, texture, keep_light=settings["keep_light"], mottle=settings["mottle"])
    out = keep_colour(photo, out, part_map(photo, labels, settings["own_colour"]))
    # Lines on a face read as wrinkles, so faces and skin get none.
    off_skin = 1 - part_map(photo, labels, {FACE_SKIN: 1.0, BODY_SKIN: 1.0})
    return outline(photo, out, settings["outline"] * off_skin)


# For each part: how large the style's texture is drawn (finer on a face than on a wall), and how
# much of it is added. Texture on skin reads as blemishes, so skin gets very little.
SHEET = {BACKGROUND: (1.0, 0.6), OTHERS: (0.75, 0.5), CLOTHES: (0.75, 0.5), OBJECT: (0.5, 0.35),
         HAIR: (0.5, 0.3), ANIMAL: (0.5, 0.25), BODY_SKIN: (0.5, 0.06), FACE_SKIN: (0.5, 0.05)}


def tileable(image, band=48):
    """A copy of the image that repeats without a visible seam.

    Near its borders it fades into the same image shifted by half its size, whose own border falls in
    the middle of the picture. Mirroring was tried first and left kaleidoscope shapes the eye picks up
    at once.
    """
    h, w = image.shape[2:]
    ramp = lambda n: (torch.minimum(torch.arange(n), n - 1 - torch.arange(n)) / band).clamp(0, 1)
    inside = torch.outer(ramp(h), ramp(w)).to(image)
    return inside * image + (1 - inside) * image.roll((h // 2, w // 2), (2, 3))


def sheet_pieces(photo, style, labels):
    """The style image laid over the photo as an unbroken sheet, a different piece of it for each part.

    Patches chosen one by one (experiment 012) came out as a checkerboard of unrelated squares. A sheet
    is continuous by construction, and giving each part its own piece means the texture never runs
    across from one thing into the next. Yields each part's amount, mask and piece.
    """
    h, w = photo.shape[2:]
    for part, (scale, amount) in SHEET.items():
        where = mask(labels, [part], (h, w)).to(photo.device)
        if where.max() == 0:
            continue
        s = style if scale == 1 else F.interpolate(style, scale_factor=scale, mode="bilinear", antialias=True)
        tile = tileable(s)
        tiled = tile.repeat(1, 1, -(-2 * h // tile.shape[2]), -(-2 * w // tile.shape[3]))
        top, left = part * 97 % h, part * 151 % w  # fixed per part, so results repeat exactly
        yield amount, where, tiled[..., top:top + h, left:left + w]


def sheet_texture(photo, style, labels):
    """The sheet's texture, without its overall colour, scaled by each part's amount."""
    return sum(amount * where * (piece - box(piece, 16)) for amount, where, piece in sheet_pieces(photo, style, labels))


def placed_pattern(photo, style, labels):
    """The style's pattern in its own colours, on the parts SHEET gives it; the photo's own colours
    everywhere else, with no tint over the whole photo (experiment 017, the founder's direction).
    Kept off the outlines, so each thing keeps its edge."""
    cover, alpha = 0, 0
    for amount, where, piece in sheet_pieces(photo, pattern(style).to(photo.device), labels):
        cover, alpha = cover + where * piece, alpha + amount * where
    alpha = alpha * (1 - prominent_edges(photo))
    return photo + alpha * (cover - photo)


def pattern_box(style, size=0.5):
    """Top, left and side of the square of the style image most evenly full of fine detail: its pattern.

    A scene has its pattern in one place (lava's fountain, the forest's leaves), and laying the whole
    scene over a photo gave a double exposure (012). Each square is scored by the least detailed of
    the 3x3 cells inside it, so a square that runs into empty sky or a smooth trunk scores low.
    """
    cell = int(size * min(style.shape[2:])) // 12 * 4  # a third of the square, divisible by 4
    step = cell // 4
    detail = (style - box(style, 4)).abs().mean(1, keepdim=True)
    cells = F.avg_pool2d(detail, cell, stride=step)
    score = -F.max_pool2d(-cells, 3, stride=1, dilation=4)  # least detailed of 3x3 cells, one cell apart
    top, left = divmod(score.flatten().argmax().item(), score.shape[3])
    return top * step, left * step, 3 * cell


def pattern(style):
    top, left, side = pattern_box(style)
    return style[..., top:top + side, left:left + side]


def colour_variation(style, grid=4):
    """How much the style's average colour changes across a 4x4 grid, relative to its overall spread.

    A texture (a bed of leaves) has the same mix everywhere: low. A scene (sky above, rock below,
    trunks in places) does not: high. Comparing the tiles' texture statistics was tried first
    (experiment 014) and ranked flowers as more of a scene than forest.
    """
    means = F.adaptive_avg_pool2d(style, grid)
    return ((means - style.mean((2, 3), keepdim=True)).norm(dim=1).mean() / style.std((2, 3)).norm()).item()


def texture_share(style):
    """How much style sheet a style gets: all of it at a colour variation of 0.2 or less, none at 0.5."""
    # ponytail: the ramp's ends are set from five styles (autumn 0.15, flowers 0.30, forest 0.40, sky
    # 0.69, lava 0.80). Re-check them when the test set grows to ten styles (next-stage.md step 5).
    return min(max((0.5 - colour_variation(style)) / 0.3, 0.0), 1.0)


def with_sheet(photo, tinted, style, labels, strength=1.0):
    """The even tint from the model, plus the style's own texture inside each part, kept off the outlines."""
    base = enhance_auto(photo, tinted, labels, CRAFTED | dict(texture={}))
    texture = sheet_texture(photo, style.to(photo.device), labels) * (1 - prominent_edges(photo))
    return (base + strength * texture).clamp(0, 1)


def by_style(photo, tinted, labels, style):
    """with_sheet(), with as much of the sheet as the style suits (experiment 014)."""
    return with_sheet(photo, tinted, style, labels, texture_share(style))


def directions(n, seed):
    """`n` fixed directions through colour space, as a 3 x n matrix."""
    return F.normalize(torch.randn(n, 3, generator=torch.Generator().manual_seed(seed)), dim=1).T


def photo_palette(photo, out, amount=1.0, steps=10):
    """Give the result the photo's mix of colours, while each colour stays where the result put it.

    Iterative distribution transfer (Pitie et al. 2005): along a few directions through colour space,
    the result's values are swapped, rank for rank, for the photo's. Uses only the two images.
    `amount` 1 is the photo's mix exactly, 0 the result unchanged.
    """
    original = out
    x, y = out.flatten(2)[0].T, photo.flatten(2)[0].T  # one row per pixel
    for i in range(steps):
        q = torch.linalg.qr(directions(3, i))[0].to(x)  # three directions at right angles
        px, py = x @ q, y @ q
        order = px.argsort(0)
        moved = torch.empty_like(px).scatter_(0, order, py.sort(0)[0])
        x = x + (moved - px) @ q.T
    return original + amount * (x.T.reshape(out.shape).clamp(0, 1) - original)


def photo_brightness(photo, out):
    """Give the result the photo's mix of light and dark with one tone curve, so that a dark photo stays
    dark. Brightness only: experiment 015 found that swapping colours rank for rank (photo_palette)
    turned faces teal."""
    l_out = lum(out).flatten()
    moved = torch.empty_like(l_out).scatter_(0, l_out.argsort(), lum(photo).flatten().sort()[0])
    return (out + (moved - l_out).view_as(lum(out))).clamp(0, 1)


def colour_shift(photo, out):
    """How far the result's mix of colours is from the photo's, 0 to 100. Where the colours sit does
    not count, only which colours there are and how much of each."""
    q = directions(16, 99).to(photo)
    spread = lambda x: (x.flatten(2)[0].T @ q).sort(0)[0]
    return 100 * (spread(out) - spread(photo)).abs().mean().item()


def texture_stats(x):
    """A colour-blind summary of an image's texture: how its brightness features vary together,
    at two depths of VGG19 (relu2_1 and relu3_1)."""
    feats = (lum(x).expand(-1, 3, -1, -1) - IMAGENET_MEAN.to(x.device)) / IMAGENET_STD.to(x.device)
    stats = []
    with torch.no_grad():
        for i, layer in enumerate(vgg()[:12]):
            feats = layer(feats)
            if i in (6, 11):
                f = feats.flatten(2)
                f = f - f.mean(2, keepdim=True)
                stats.append(f @ f.transpose(1, 2) / f.shape[2])
    return stats


def texture_likeness(photo, out, style):
    """Share of the gap between the photo's texture and the style's that the result has closed.

    0 is no closer to the style than the photo was, 1 is the style's own texture. Colour does not
    count. The style is tried at full and half size, since a method may render texture at either.
    """
    gap = lambda a, b: sum((p - q).pow(2).mean().sqrt() for p, q in zip(texture_stats(a), texture_stats(b)))
    return max(1 - gap(out, s) / gap(photo, s) for s in (style, F.avg_pool2d(style, 2))).item()


def measure(photo, out, labels, style):
    """The numbers results are judged on, each for one image.

    style on subjects   average colour change on people, animals and objects, 0 to 100
    style on the rest   the same on everything else
    outline strength    contrast across the boundaries between things, relative to the photo's. Fine
                        texture is flattened first, so texture inside things does not count. 1.0 is
                        as strong as the photo. (Experiment 013 replaced "edge prominence", which
                        counted texture as clutter and scored a blurred result higher than a sharp one.)
    blotchiness         size of the mid-sized patches in the change, 0 to 100. Lower is cleaner.
    texture likeness    see texture_likeness()
    colour shift        see colour_shift()
    """
    change = out - photo
    amount = 100 * change.abs().mean(1, keepdim=True)
    subject = mask(labels, SUBJECT_PARTS, photo.shape[2:]).to(photo.device) > 0.5
    boundary = prominent_edges(photo) > 0.5
    outlines = lambda x: step_map(guided_filter(photo, x, r=4, eps=1e-2))[boundary].mean()
    _, patches, _ = split(photo, change)
    return {
        "style on subjects": amount[subject].mean().item(),
        "style on the rest": amount[~subject].mean().item(),
        "outline strength": (outlines(out) / outlines(photo)).item(),
        "blotchiness": 100 * patches.abs().mean().item(),
        "texture likeness": texture_likeness(photo, out, style.to(photo.device)),
        "colour shift": colour_shift(photo, out),
    }


def print_table(rows_by_name):
    """Average each measure over the images, one line per version."""
    names = list(next(iter(rows_by_name.values()))[0])
    print(f"{'':28}" + "".join(f"{n:>19}" for n in names))
    for name, rows in rows_by_name.items():
        print(f"{name:28}" + "".join(f"{sum(r[n] for r in rows) / len(rows):19.2f}" for n in names), flush=True)


METHODS["samam_shift"] = lambda c, s: shift_average(samam, c, s)
METHODS["samam_style512"] = lambda c, s: samam(c, s, style_side=512)
# The 4px checkpoint has a 4px grid, so its shifts must differ within 4 pixels.
METHODS["samam4_shift"] = lambda c, s: shift_average(samam4, c, s, [(0, 0), (2, 2), (1, 3), (3, 1)])


# --- Experiments. Each returns the labelled images for one photo and style pair.

def artifacts(photo_name, style_name, photo, style):
    """005: three ways to remove SaMam's repeating stamp pattern."""
    raw = stylize("samam", photo_name, style_name, photo, style)
    shifted = stylize("samam_shift", photo_name, style_name, photo, style)
    return {
        "photo": photo,
        "raw SaMam": raw,
        "shift-average": shifted,
        "guided filter": guided_filter(photo, raw).clamp(0, 1),
        "shift-average + guided filter": guided_filter(photo, shifted).clamp(0, 1),
        "style at 512px": stylize("samam_style512", photo_name, style_name, photo, style),
    }


def texture(photo_name, style_name, photo, style):
    """006: smooth the style's change only, keep the photo's detail, dial texture back in."""
    raw = stylize("samam", photo_name, style_name, photo, style)
    shifted = stylize("samam_shift", photo_name, style_name, photo, style)
    variants = {
        "photo": photo,
        "raw SaMam": raw,
        "enhanced, texture 0": enhance(photo, shifted, 0.0),
        "enhanced, texture 0.3": enhance(photo, shifted, 0.3),
        "enhanced, texture 0.6": enhance(photo, shifted, 0.6),
    }
    labels = parts(photo)
    if has_subject(labels):
        variants["enhanced, texture by part"] = enhance(photo, shifted, part_map(photo, labels, PROTECT["texture"]))
    return variants


def colour(photo_name, style_name, photo, style):
    """007: give skin, fur and hair their own colour back."""
    shifted = stylize("samam_shift", photo_name, style_name, photo, style)
    labels = parts(photo)
    overlay = 0.4 * photo + 0.6 * F.interpolate(COLOURS[labels].permute(2, 0, 1)[None], size=photo.shape[2:]).to(photo.device)
    enhanced = enhance(photo, shifted, part_map(photo, labels, PROTECT["texture"]))
    keep = part_map(photo, labels, PROTECT["own_colour"])
    return {
        "photo": photo,
        "detected parts": overlay,
        "enhanced, texture by part": enhanced,
        "+ half of own colour on skin, fur, hair": keep_colour(photo, enhanced, 0.5 * keep),
        "+ all of own colour on skin, fur, hair": keep_colour(photo, enhanced, keep),
    }


def edges(photo_name, style_name, photo, style):
    """008: keep things separate from each other when texture is strong."""
    shifted = stylize("samam_shift", photo_name, style_name, photo, style)
    found = prominent_edges(photo)
    return {
        "photo": photo,
        "edges found": found.expand(-1, 3, -1, -1),
        "enhanced, texture 0.6": enhance(photo, shifted, 0.6),
        "+ texture kept off the edges": enhance(photo, shifted, 0.6 * (1 - found)),
        "+ photo's light and dark kept": enhance(photo, shifted, 0.6, keep_light=0.7),
        "+ both": enhance(photo, shifted, 0.6 * (1 - found), keep_light=0.7),
    }


def auto(photo_name, style_name, photo, style):
    """009: every setting together, with what the detectors found."""
    raw = stylize("samam", photo_name, style_name, photo, style)
    shifted = stylize("samam_shift", photo_name, style_name, photo, style)
    labels = parts(photo)
    return {
        "photo": photo,
        "detected parts": 0.4 * photo + 0.6 * F.interpolate(COLOURS[labels].permute(2, 0, 1)[None], size=photo.shape[2:]).to(photo.device),
        "edges found": prominent_edges(photo).expand(-1, 3, -1, -1),
        "raw SaMam": raw,
        "enhanced": enhance_auto(photo, shifted, labels, PROTECT),
    }


def crafted(photo_name, style_name, photo, style):
    """010: style on everything, each thing kept distinct."""
    raw = stylize("samam", photo_name, style_name, photo, style)
    shifted = stylize("samam_shift", photo_name, style_name, photo, style)
    labels = parts(photo)
    return {
        "photo": photo,
        "raw SaMam": raw,
        "first try: settings turned up": enhance_auto(photo, shifted, labels, FIRST_TRY),
        "even tint per object": enhance_auto(photo, shifted, labels, CRAFTED),
        "+ a third of the patches back": enhance_auto(photo, shifted, labels, CRAFTED | dict(mottle=0.35)),
        "+ outline": enhance_auto(photo, shifted, labels, CRAFTED | dict(outline=0.4)),
    }


def finer(photo_name, style_name, photo, style):
    """011: does SaMam's 4px checkpoint give a texture that reads as deliberate?"""
    labels = parts(photo)
    coarse = stylize("samam_shift", photo_name, style_name, photo, style)
    fine = stylize("samam4_shift", photo_name, style_name, photo, style)
    return {
        "photo": photo,
        "raw SaMam, 8px patches": stylize("samam", photo_name, style_name, photo, style),
        "raw SaMam, 4px patches": stylize("samam4", photo_name, style_name, photo, style),
        "crafted, from 8px": enhance_auto(photo, coarse, labels, CRAFTED),
        "crafted, from 4px": enhance_auto(photo, fine, labels, CRAFTED),
    }


def surface(photo_name, style_name, photo, style):
    """012: texture taken from the style image itself, in place of the model's stamp."""
    labels = parts(photo)
    shifted = stylize("samam_shift", photo_name, style_name, photo, style)
    return {
        "photo": photo,
        "style": F.interpolate(style, size=photo.shape[2:]).to(photo.device),
        "current default": enhance_auto(photo, shifted, labels, CRAFTED),
        "style sheet per part": with_sheet(photo, shifted, style, labels),
        "style sheet per part, doubled": with_sheet(photo, shifted, style, labels, 2.0),
    }


# What each column of the all-pairs sheets and the measurements shows.
COLUMNS = {
    "raw SaMam": lambda photo, raw, shifted, labels, style: raw,
    "subjects protected": lambda photo, raw, shifted, labels, style: enhance_auto(photo, shifted, labels, PROTECT),
    "first try": lambda photo, raw, shifted, labels, style: enhance_auto(photo, shifted, labels, FIRST_TRY),
    "style on everything": lambda photo, raw, shifted, labels, style: enhance_auto(photo, shifted, labels, CRAFTED),
    "style sheet per part": lambda photo, raw, shifted, labels, style: with_sheet(photo, shifted, style, labels),
    "style sheet per part x2": lambda photo, raw, shifted, labels, style: with_sheet(photo, shifted, style, labels, 2.0),
    "style sheet, by style": lambda photo, raw, shifted, labels, style: by_style(photo, shifted, labels, style),
    "A: each pixel's own colour": lambda photo, raw, shifted, labels, style: keep_colour(photo, by_style(photo, shifted, labels, style), 1.0),
    "B: photo's palette": lambda photo, raw, shifted, labels, style: photo_palette(photo, by_style(photo, shifted, labels, style)),
    "B: photo's palette, half": lambda photo, raw, shifted, labels, style: photo_palette(photo, by_style(photo, shifted, labels, style), 0.5),
    "C: own colour and brightness": lambda photo, raw, shifted, labels, style: keep_colour(photo, photo_brightness(photo, by_style(photo, shifted, labels, style)), 1.0),
    "sheet from the style's pattern": lambda photo, raw, shifted, labels, style: with_sheet(photo, shifted, pattern(style), labels),
    "pattern placed, photo's colours": lambda photo, raw, shifted, labels, style: placed_pattern(photo, style, labels),
}


def every_pair():
    """Yield photo name, style name, photo, style, detected parts, and each column's result."""
    for photo_path in sorted((HERE / "data/content").glob("*.jpg")):
        photo = load(photo_path).to(device)
        labels = parts(photo)
        for style_path in sorted((HERE / "data/style").glob("*.jpg")):
            style = load(style_path)
            raw = stylize("samam", photo_path.stem, style_path.stem, photo, style)
            shifted = stylize("samam_shift", photo_path.stem, style_path.stem, photo, style)
            results = {name: make(photo, raw, shifted, labels, style) for name, make in COLUMNS.items()}
            finer_result = stylize("samam4_shift", photo_path.stem, style_path.stem, photo, style)
            results["style on everything, 4px"] = enhance_auto(photo, finer_result, labels, CRAFTED)
            yield photo_path.stem, style_path.stem, photo, style, labels, results


def all_pairs(out, columns):
    """One sheet per photo: every style, with the chosen columns side by side."""
    for photo_name, pairs in itertools.groupby(every_pair(), key=lambda pair: pair[0]):
        pairs = list(pairs)
        rows = [(style_name, style, *(results[c] for c in columns)) for _, style_name, _, style, _, results in pairs]
        sheet(out / f"{photo_name}.jpg", pairs[0][2], rows, ("photo", "style", *columns))
        print(f"{photo_name} written", flush=True)


def show_patterns(out):
    """Each style image with the square pattern_box() chose drawn on it, and its colour variation (014)."""
    tiles, names = [], []
    for path in sorted((HERE / "data/style").glob("*.jpg")):
        style = load(path)
        top, left, side = pattern_box(style)
        tile = to_image(style)
        ImageDraw.Draw(tile).rectangle((left, top, left + side, top + side), outline="white", width=4)
        tiles.append(tile.resize((tile.width * 384 // tile.height, 384)))
        names.append(f"{path.stem}: {colour_variation(style):.2f} whole, {colour_variation(pattern(style)):.2f} square")
    stack([labelled_row([t], [n]) for t, n in zip(tiles, names)]).save(out / "patterns.jpg", quality=90)


def measurements():
    """Average of measure() over all 20 pairs, for each column."""
    totals = {}
    for _, _, photo, style, labels, results in every_pair():
        for name, result in results.items():
            totals.setdefault(name, []).append(measure(photo, result, labels, style))
    print_table(totals)


# photo, style, and the top-left corners of two 200px close-ups (x, y)
STAMP_PAIRS = [
    ("portrait", "autumn", [(540, 120), (270, 150)]),
    ("cat", "flowers", [(20, 150), (300, 150)]),
    ("harbour", "lava", [(100, 60), (500, 300)]),
]
COLOUR_PAIRS = [
    ("cat", "flowers", [(300, 150), (130, 20)]),
    ("portrait", "flowers", [(270, 150), (380, 200)]),
    ("astronaut_dogs", "flowers", [(200, 130), (20, 200)]),
]
EDGE_PAIRS = [
    ("astronaut_dogs", "autumn", [(200, 130), (20, 200)]),
    ("portrait", "autumn", [(380, 200), (270, 150)]),
    ("harbour", "autumn", [(130, 230), (520, 240)]),
]
AUTO_PAIRS = [
    ("astronaut_dogs", "autumn", [(200, 130), (20, 200)]),
    ("harbour", "autumn", [(130, 230), (520, 240)]),
    ("cat", "flowers", [(300, 150), (130, 20)]),
]
CRAFTED_PAIRS = [
    ("astronaut_dogs", "autumn", [(200, 130), (20, 200)]),
    ("astronaut_dogs", "flowers", [(200, 130), (20, 200)]),
    ("portrait", "flowers", [(270, 150), (380, 200)]),
    ("cat", "autumn", [(300, 150), (130, 20)]),
    ("harbour", "flowers", [(130, 230), (520, 240)]),
]
EXPERIMENTS = {
    "artifacts": (artifacts, STAMP_PAIRS),
    "texture": (texture, STAMP_PAIRS),
    "colour": (colour, COLOUR_PAIRS),
    "edges": (edges, EDGE_PAIRS),
    "auto": (auto, AUTO_PAIRS),
    "crafted": (crafted, CRAFTED_PAIRS),
    "finer": (finer, [("astronaut_dogs", "autumn", [(200, 130), (20, 200)]),
                      ("cat", "flowers", [(300, 150), (130, 20)]),
                      ("portrait", "autumn", [(270, 150), (540, 120)])]),
    "surface": (surface, [("portrait", "autumn", [(270, 150), (540, 120)]),
                          ("astronaut_dogs", "flowers", [(200, 130), (20, 200)]),
                          ("cat", "autumn", [(300, 150), (130, 20)]),
                          ("harbour", "autumn", [(130, 230), (520, 240)])]),
}
# Runs over all 20 pairs instead of a few chosen ones.
WHOLE_SET = {
    "all": lambda out: all_pairs(out, ["raw SaMam", "subjects protected"]),  # 009
    "all-crafted": lambda out: all_pairs(out, ["raw SaMam", "subjects protected", "style on everything"]),  # 010
    "all-sheet": lambda out: all_pairs(out, ["style on everything", "style sheet per part", "style sheet per part x2"]),  # 012
    "measure": lambda out: measurements(),                                   # 010 onwards
    "variation": lambda out: [print(f"{p.stem:10}{colour_variation(load(p)):.2f}{texture_share(load(p)):8.2f}")  # 014
                              for p in sorted((HERE / "data/style").glob("*.jpg"))],
    "all-gated": lambda out: all_pairs(out, ["style on everything", "style sheet per part", "style sheet, by style"]),  # 014
    "patterns": lambda out: show_patterns(out),  # 016
    "all-pattern": lambda out: all_pairs(out, ["style sheet, by style", "sheet from the style's pattern"]),  # 016
    "all-placed": lambda out: all_pairs(out, ["style on everything", "sheet from the style's pattern", "pattern placed, photo's colours"]),  # 017
    "all-colour": lambda out: all_pairs(out, ["style sheet, by style", "A: each pixel's own colour", "B: photo's palette", "C: own colour and brightness"]),  # 015
}


def labelled_row(tiles, labels):
    w, h = tiles[0].size
    row = Image.new("RGB", (len(tiles) * w, h + PAD), "white")
    draw = ImageDraw.Draw(row)
    for i, (tile, label) in enumerate(zip(tiles, labels)):
        row.paste(tile, (i * w, PAD))
        draw.text((i * w + 6, 5), label, fill="black", font_size=18)
    return row


def stack(rows):
    out = Image.new("RGB", (max(r.width for r in rows), sum(r.height for r in rows)), "white")
    y = 0
    for r in rows:
        out.paste(r, (0, y))
        y += r.height
    return out


if __name__ == "__main__":
    # Each setting, at the end of its range, must give back exactly what went in.
    a, b = torch.rand(1, 3, 64, 80), torch.rand(1, 3, 64, 80)
    assert torch.allclose(enhance(a, b, 1.0), b, atol=1e-5), "texture 1 must return the raw result"
    assert torch.allclose(enhance(a, a, 0.0), a, atol=1e-5), "an unchanged photo must stay unchanged"
    assert torch.allclose(keep_colour(a, b, 0.0), b), "keeping no colour must change nothing"
    mid_a, mid_b = 0.4 + 0.2 * a, 0.4 + 0.2 * b  # mid-range values, so nothing is clipped to 0..1
    assert torch.allclose(lum(keep_colour(mid_a, mid_b, 1.0)), lum(mid_b), atol=1e-5), "keeping colour must not change brightness"
    halves = torch.cat([torch.tensor([1.0, 0, 0]).view(1, 3, 1, 1).expand(1, 3, 32, 80),
                        torch.tensor([0, 0, 1.0]).view(1, 3, 1, 1).expand(1, 3, 32, 80)], 2)
    assert texture_share(a) == 1.0 and texture_share(halves) == 0.0, "even noise is a texture, two halves are a scene"
    assert torch.allclose(photo_palette(a, a), a, atol=1e-5), "a result already in the photo's colours must not change"
    assert torch.allclose(photo_brightness(a, a), a, atol=1e-5), "a result already in the photo's brightness must not change"
    half_flat = torch.cat([torch.full((1, 3, 200, 300), 0.5), torch.rand(1, 3, 200, 300)], 3)
    assert pattern_box(half_flat)[1] >= 300, "the pattern must be found in the detailed half"
    assert colour_shift(a, photo_palette(a, b ** 3)) < 0.1 * colour_shift(a, b ** 3), "the palette must move most of the way to the photo's"

    out = HERE.parent / "research" / sys.argv[1]
    out.mkdir(parents=True, exist_ok=True)
    if sys.argv[2] in WHOLE_SET:
        WHOLE_SET[sys.argv[2]](out)
        sys.exit()
    experiment, pairs = EXPERIMENTS[sys.argv[2]]
    for photo_name, style_name, corners in pairs:
        photo = load(HERE / f"data/content/{photo_name}.jpg").to(device)
        style = load(HERE / f"data/style/{style_name}.jpg")
        images = {k: to_image(v) for k, v in experiment(photo_name, style_name, photo, style).items()}
        labels = list(images)
        labelled_row(list(images.values()), labels).save(out / f"{photo_name}_{style_name}.jpg", quality=90)
        rows = []
        for x, y in corners:
            crops = [im.crop((x, y, x + CROP, y + CROP)).resize((CROP * ZOOM,) * 2, Image.NEAREST) for im in images.values()]
            rows.append(labelled_row(crops, labels))
        stack(rows).save(out / f"{photo_name}_{style_name}_closeups.jpg", quality=92)
        print(f"{photo_name} x {style_name} written", flush=True)
