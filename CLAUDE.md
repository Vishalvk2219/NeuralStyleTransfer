# CLAUDE.md

## Project

A free website that turns a personal photo into an artistic version in a chosen style (flowers, forest, sky, lava, or the visitor's own style image). The model runs in the visitor's browser. The goal of V1 is traffic.

[spec.md](spec.md) is the source of truth for scope, requirements, stack and milestones. Read the relevant section before starting work, and update it when a decision changes.

## Ponytail

Invoke the `ponytail:ponytail` skill before any coding task: writing, adding, refactoring, fixing, reviewing or designing code, and choosing libraries or dependencies. Use the default intensity unless told otherwise.

- Review for over-engineering: `ponytail:ponytail-review` (a diff) or `ponytail:ponytail-audit` (the whole repo).
- List deferred shortcuts: `ponytail:ponytail-debt`.
- Do not use ponytail for non-coding work such as the spec, research or writing.

## Rules that must not be broken

- **Photos never leave the device.** No code may send image data, file names or photo metadata over the network. The only exception is the server fallback in spec section 10, and only if it has been triggered.
- **No third-party requests except analytics.** Serve code, the model, runtime files and fonts from our own domain.
- **Analytics go through one `track()` function.** No cookies, no visitor identifier, no free text. Event names and properties are listed in spec section 8.3.
- **Privacy wording is fixed** in spec section 8.4. Do not write a broader claim anywhere in the site.
- **No generative models.** Texture-transfer methods only. No diffusion models, image generators, face restoration models or diffusion upscalers anywhere in the flow. This is what makes the product trustworthy and fast.
- **The enhancer invents nothing.** It may use only the visitor's photo and the stylized result (spec section 9.2a).
- **No styles named after artists.** Gallery images must be owned by us or public domain.
- **Stay on free plans.** Each hosted file must be under 25 MB. Deferred: see "Current priority".

## Current priority

**Output quality first.** Do not pick, shrink or simplify anything to save download size, speed, memory or hosting cost until a model produces results people like (spec section 9.1). Those limits come back at launch, not now.

## Stack

| Part | Choice |
|---|---|
| Site | Astro + TypeScript, static output |
| Tool interface | One React component |
| Model runtime | ONNX Runtime Web: WebGPU first, WebAssembly fallback, inside a Web Worker |
| Face detection | MediaPipe Face Detector |
| Training | PyTorch, exported to ONNX at half precision |
| Hosting | Cloudflare Pages free plan |
| Analytics | Umami Cloud free plan |

## Layout

| Folder | Contents |
|---|---|
| `web/` | The Astro site and the tool (not created yet) |
| `model/` | Model experiments, ONNX export, browser test page, test images |
| `research/` | Experiment log with output images, one numbered folder per experiment |

The founder's original notebook (`NeuralStyleTransfer.ipynb`) was removed from the repo on 2026-10-02 at their request. It is not a reference, a baseline or a yardstick for this project; do not bring it back or measure against it. It remains in git history at commit `e62716b`.

## Commands

There is no Python or Node on this machine. Everything runs in Docker.

```sh
# Build: exports MicroAST to ONNX and checks it against PyTorch (the build fails if they differ)
docker build -t nst-bench model

# Browser test page at http://localhost:8000
docker run --rm -p 8000:8000 nst-bench

# Quality comparison sheets, written to research/<run-name>/ (uses the NVIDIA GPU)
# methods: samam, samam4, microast (nnst exists in the code but must not be run here; see below)
docker run --rm --gpus all -v "D:/Gtihub-Repos/NeuralStyleTransfer:/work" nst-bench python /work/model/compare.py <run-name> samam,microast [photo names]

# Style-by-part prototype (background, hair, clothes), written to research/<run-name>/
docker run --rm --gpus all -v "D:/Gtihub-Repos/NeuralStyleTransfer:/work" nst-bench python /work/model/regions.py <run-name>

# Enhancer experiments: artifacts (005), texture (006), colour (007), edges (008), auto and all (009),
# crafted, all-crafted and measure (010), finer (011), surface and all-sheet (012), variation and all-gated (014),
# all-colour (015), patterns and all-pattern (016), all-placed (017).
# The script checks itself on start.
# `measure` prints the six numbers results are judged on, averaged over all 20 pairs.
docker run --rm --memory 5g --gpus all -v "D:/Gtihub-Repos/NeuralStyleTransfer:/work" nst-bench python /work/model/enhance.py <run-name> <experiment>
```

- Model results are cached in `model/cache/` (git-ignored), so re-running an experiment takes seconds. Delete a file there to force a re-run.
- A shell `timeout` stops the docker client, not the container. Give long runs a `--name` and `docker rm -f` it afterwards, or the model keeps running on the GPU.
- SaMam takes about 0.25 s per image using the compiled `mamba-ssm` kernel in the image. If it ever takes 10 s or more, that kernel is missing and it has fallen back to the pure-PyTorch path.
- **Do not run NNST on this machine.** It keeps very large feature tables in ordinary RAM. On 2026-10-02 it froze the Docker virtual machine and took the whole Docker engine down, including the user's unrelated containers. The host has 15.7 GB of RAM and is usually short of it.
- Give every `docker run` a memory limit, for example `--memory 5g`, so a runaway job is stopped by Docker and cannot starve the machine.
- Keep heavy image work on the GPU and time it. Before accepting a slow run, check GPU memory with `nvidia-smi`: at or near 6 GB means it is overflowing into shared memory.

Model weights live in `model/weights/` and are not in git. Download them once:

| File | From |
|---|---|
| `SaMam_patchsize_x8.ckpt` (289 MB) | Google Drive link in the [SaMam README](https://github.com/Chernobyllight/SaMam); direct: `https://drive.usercontent.google.com/download?id=1HH_cSdtUzdgUMspwJ30Osax-LpdF9zag&export=download&confirm=t` |
| `selfie_multiclass_256x256.onnx` (16 MB) | `https://huggingface.co/senty-au/selfie_multiclass_256x256-ONNX/resolve/main/onnx/model.onnx` |
| `u2netp.onnx` (4.7 MB) | `https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2netp.onnx` |
| `SaMam_patchsize_x4.ckpt` (294 MB, optional) | Same README; does not fit a 6 GB GPU at our image size |

- In Git Bash, prefix `docker run` commands that contain container paths with `MSYS_NO_PATHCONV=1`.
- The NVIDIA driver here (536.52, July 2023) supports CUDA 12.2 at most, so the image pins PyTorch 2.5.1 built for CUDA 12.1. Newer builds either cannot see the GPU (CUDA 13) or see it and then fail with "device busy or unavailable" (CUDA 12.6). Updating the driver removes the need for the pin.

## Research log

Every experiment that produces images gets a numbered folder in `research/` and an entry in [research/README.md](research/README.md): what was tried, the settings, the images, what was learned, and what comes next. The images are tracked in git so quality can be compared over time. Add the entry in the same piece of work as the experiment, not later.

## Current state

Spec revision 6. Milestone M0 (spec section 14) is in progress: comparing output quality across candidate models.

- [research/landscape.md](research/landscape.md): the methods that exist, the order to test them, and the quality enhancer design.
- [research/quality-checklist.md](research/quality-checklist.md): the output features to test and improve one at a time, in order. Work on one feature at a time.
- [research/README.md](research/README.md): results with images. Experiments 000 to 012 are done.
- [research/next-stage.md](research/next-stage.md): the plan for the current stage, approved by the founder on 2026-10-02. Follow its order and its measures, and update it when a step finishes or a decision changes. Step 1 is done and step 4 is under way (experiment 012).
- Spec section 9.5: technical findings.

Where things stand: SaMam is the base model. `enhance_auto()` in `model/enhance.py` is the pipeline. Its default settings, `CRAFTED`, put the style on every object, faces and pets included, as one even tint per object with light texture; the founder asked for this on 2026-10-02. `PROTECT` (subjects stay natural) is an option, not the default. `with_sheet()` adds the style image's own texture per part (experiment 012); it works for dense texture styles and not for scene styles. `by_style()` gives each style a share of it from how much the style's colour varies (experiment 014). Keeping the photo's colour mood (`photo_brightness()` then `keep_colour()`, experiment 015) works but removes most of a scene style. Neither is the default yet. On 2026-10-03 the founder set a new direction: the style's pattern (`pattern_box()`, experiment 016) placed on chosen parts in its own colours, with the photo's own colours elsewhere and no model tint (`placed_pattern()`, experiment 017). The open items are listed at the end of the checklist.

How to work on quality here: state the goal, say what is wrong and why, change one thing, and show before and after with both images and the `measure` numbers. Do not make changes that are not tied to a stated problem.

Do not develop MicroAST further. The aim is to create a better method of our own, not to tune or measure against old ones.

## Conventions

- Branch: `nstbranch` is the main branch.
- Commit only when asked.
- Add build, test and run commands to this file when they exist.
