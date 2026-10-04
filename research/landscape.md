# Style transfer in 2026: what exists and what to test

Researched 2026-10-02.

## 1. Decisions

- **No generative models.** We use texture-transfer methods only and aim for the best quality that family can give. This is what separates the product from ChatGPT and Gemini: it is fast, and it can be trusted not to redraw the photo. (Decided 2026-10-02.)
- **Every result passes through a quality enhancer** (section 5). The output should always be as high in quality as we can make it without destroying the photo's detail or its original look.
- The notebook's method (2015) is two generations old and is not developed further.

## 2. The two families

| | Family A: texture transfer (ours) | Family B: generative restyling (not used) |
|---|---|---|
| How it works | Moves the style image's colours, strokes and textures onto the photo's own pixels | A large image generator redraws the photo, guided by the style image |
| Result looks like | The same photo, painted or textured | A new picture of the same scene in that style |
| Keeps the photo intact | By construction | Improved in 2025–26, but it is still a redraw |
| Model size | 0.5 to 35 million parameters | 1 to 20 billion parameters |
| Time per image | 0.03 to 0.4 s on a desktop GPU | 4 to 50 s on a data-centre GPU |
| Can run in a browser | Plausible for the small ones | No |
| Fits "photos never leave the device" | Yes | No |

Family B currently has the highest published quality scores. Choosing family A means accepting that and competing on trust, speed and privacy. Section 6 keeps the family B findings for reference.

## 3. Candidates to test

Scores are from the SaMam paper's benchmark. Lower is better for both. Time is per 512px image on an RTX 3090.

| Method | Year | Overall (ArtFID) | Photo kept (LPIPS) | Time | Size | Code and licence |
|---|---|---|---|---|---|---|
| **SaMam** | 2025 | **26.3** | **0.39** | 0.034 s | 18.5 M | [Chernobyllight/SaMam](https://github.com/Chernobyllight/SaMam), MIT |
| AesPA-Net | 2023 | 29.8 | 0.41 | 0.35 s | 24.2 M | [Kibeom-Hong/AesPA-Net](https://github.com/Kibeom-Hong/AesPA-Net), licence not stated |
| StyTr2 | 2022 | 39.3 | 0.50 | 0.39 s | 35.4 M | [diyiiyiii/StyTR-2](https://github.com/diyiiyiii/StyTR-2), licence not stated |
| ArtFlow | 2021 | 47.3 | 0.57 | 0.15 s | 6.5 M | not checked |
| EFDM | 2022 | 54.7 | 0.53 | 0.027 s | 7.0 M | not checked |

Not in that table, worth testing:

| Method | Year | Why | Code and licence |
|---|---|---|---|
| AdaAttN | 2021 | Attention-based; a common strong baseline | [Huage001/AdaAttN](https://github.com/Huage001/AdaAttN), Apache-2.0 |
| NNST (Neural Neighbor Style Transfer) | 2022 | An optimisation method like the notebook's, with a different matching rule designed to carry over richer texture. The direct modern replacement for the notebook. | [nkolkin13/NeuralNeighborStyleTransfer](https://github.com/nkolkin13/NeuralNeighborStyleTransfer), MIT |
| CAP-VSTNet | 2023 | Photorealistic transfer: changes colour and tone and leaves every detail alone. The safest option for faces. | [linfengWen98/CAP-VSTNet](https://github.com/linfengWen98/CAP-VSTNet), MIT |
| MicroAST | 2023 | Smallest. Tested in experiment 000. | MIT |
| The notebook's method | 2015 | Partly tested in experiment 001. | ours |

All of these run on the development laptop (RTX 3050, 6 GB). No accounts or cloud GPU are needed.

SaMam's published weights were trained on paintings (WikiArt), like MicroAST's. How it behaves on nature styles is unknown until tested.

## 4. Test plan and status

Same four photos and five styles for every candidate, scored against `quality-checklist.md`.

| Candidate | Status |
|---|---|
| SaMam | **Leading.** Tested in experiment 002. The enhancer is built on it. |
| NNST | Abandoned: 515 seconds for one image on this laptop (experiment 004) |
| AesPA-Net | Ruled out: no licence, so not usable in a commercial product without permission |
| SaMam, 4-pixel checkpoint | Does not fit in 6 GB of GPU memory at our image size |
| AdaAttN | Not yet tested |
| CAP-VSTNet | Not yet tested. Still of interest for colour handling. |
| StyTr2 | Not yet tested; licence not stated |
| MicroAST | Tested (experiment 000); behind SaMam |

Each candidate is one experiment in the research log.

For reference only: the same pairs run by hand through ChatGPT and Gemini, to know what a visitor can already get elsewhere.

## 5. The quality enhancer

A step after style transfer that makes every result clean and sharp.

**The rule.** The enhancer may use only two things: the visitor's original photo and the stylized result. It must not use any model that invents content. Anything that could change who is in the photo breaks the trust the product is built on.

### 5.0 What is built

The first version is `enhance()` in `model/enhance.py` (experiments 005 and 006). It treats the style as a change made to the photo, smooths only that change using the photo's edges as the guide, and adds it back to the untouched photo. A **texture** setting returns a chosen share of the model's fine pattern, as one number or per part of the photo.

It covers the first two steps in the table below. Colour and tone protection, guided upscaling and sharpening are not built yet.

### 5.1 What fits the rule

These are classical image-processing steps. They are deterministic, need no large model, and can run in a browser.

| Step | What it does | Fixes |
|---|---|---|
| Artifact clean-up guided by the photo | Smooths the stylized image only where the original photo was smooth, and leaves it alone at the photo's edges (guided filter or joint bilateral filter) | Woven patterns, speckles and blotches in flat areas |
| Detail restoration from the photo | Puts the photo's own fine detail (eyes, whiskers, lettering) back on top of the stylized image | Softened faces and lost small detail |
| Colour and tone protection | Keeps skin and fur a believable colour, and stops the result going darker or flatter than the photo | Green and red faces, darkened faces |
| Guided upscaling | Stylizes at the size the model works best at, then enlarges using the full-size photo as the guide, so edges come from the real photo | Blurry or shrunken-texture results at large sizes |
| Mild sharpening and contrast | A light final pass | Soft overall look |

The first four all rest on one idea from photorealistic style transfer research: the stylized image supplies colour and texture, and the original photo supplies structure and detail.

### 5.2 What needs testing before it is allowed

| Option | Why it is tempting | Why it needs care |
|---|---|---|
| A small learned upscaler (Real-ESRGAN's compact model, BSD-3 licence, already shown to run in browsers) | Sharper large output than classical enlarging | It is trained to invent plausible fine texture. On a painted look that may be acceptable; on a face it may not be. It is used only if 5.1 is not enough, and only if it passes the likeness checks. |

### 5.3 What is excluded

| Option | Why not |
|---|---|
| Face restoration models (GFPGAN, CodeFormer) | They rebuild a face from what faces usually look like. Research papers and GFPGAN's own documentation report that they change identity. This breaks the rule. |
| Diffusion-based upscalers and "enhancers" | Generative, so excluded by the first decision |

### 5.4 Where it sits in the flow

1. Photo and style are loaded and sized.
2. Style transfer makes the stylized image.
3. **Enhancer:** artifact clean-up, detail restoration, colour and tone protection, guided upscaling, mild sharpening.
4. Quality check: if the result has drifted too far from the photo, lower the strength and repeat.
5. Result is shown.

## 6. Family B, for reference

Not used. Recorded so the decision can be revisited with facts if needed.

Scores from the TeleStyle and Style-CCL papers' shared benchmark. Higher is better. These cannot be compared with the scores in section 3.

| Method | Year | Built on | Style match | Photo kept | Looks good | Licence |
|---|---|---|---|---|---|---|
| TeleStyle | Jan 2026 | Qwen-Image-Edit, 20 billion parameters | 0.577 | 0.441 | 6.32 | Apache-2.0 |
| Style-CCL | Jun 2026 | FLUX.1 dev | 0.561 | 0.401 | 6.30 | Base model is non-commercial |
| CSGO | 2024 | SDXL | 0.535 | 0.379 | 5.97 | Apache-2.0 weights |
| StyleID | 2024 | Stable Diffusion 1.4 | 0.453 | 0.190 | 5.75 | not checked |
| StyleShot | 2024 | Stable Diffusion 1.5 | 0.450 | 0.227 | 5.74 | MIT |
| InstantStyle | 2024 | SDXL | 0.397 | 0.189 | 5.46 | not checked |

None of these fits the laptop's 6 GB GPU or a browser. Each needs a server GPU for every image.

## Sources

Texture transfer
- [SaMam: Style-aware State Space Model for Arbitrary Image Style Transfer](https://arxiv.org/abs/2503.15934)
- [SaMam code](https://github.com/Chernobyllight/SaMam)
- [Mamba-ST: State Space Model for Efficient Style Transfer](https://arxiv.org/pdf/2409.10385)
- [Style Transfer: A Decade Survey](https://arxiv.org/html/2506.19278v1)
- [Portrait Stylization: Artistic Style Transfer with Auxiliary Networks for Human Face Stylization](https://arxiv.org/pdf/2309.13492)
- [Style Injection in Diffusion (metrics: ArtFID, CFSD)](https://openaccess.thecvf.com/content/CVPR2024/papers/Chung_Style_Injection_in_Diffusion_A_Training-free_Approach_for_Adapting_Large-scale_CVPR_2024_paper.pdf)

Enhancer
- [Joint Bilateral Upsampling](https://kops.uni-konstanz.de/bitstream/123456789/5563/1/Joint_Bilateral_Upsampling.pdf)
- [Detail-preserving Joint Image Upsampling](https://dl.acm.org/doi/10.1145/3665246)
- [Photorealistic Style Transfer via Wavelet Transforms (WCT2)](https://arxiv.org/pdf/1903.09760)
- [PhotoWCT2](https://arxiv.org/html/2110.11995)
- [Drafting and Revision: Laplacian Pyramid Network for Fast High-Quality Artistic Style Transfer](https://arxiv.org/abs/2104.05376)
- [Real-ESRGAN](https://github.com/xinntao/real-esrgan)
- [web-realesrgan: Real-ESRGAN in the browser](https://github.com/xororz/web-realesrgan)
- [GFPGAN](https://github.com/TencentARC/GFPGAN)
- [CodeFormer++: Blind Face Restoration Using Deformable Registration and Deep Metric Learning](https://arxiv.org/pdf/2510.04410)
- [Robust ID-Specific Face Restoration via Alignment Learning](https://arxiv.org/pdf/2507.10943)

Family B
- [TeleStyle: Content-Preserving Style Transfer in Images and Videos](https://arxiv.org/html/2601.20175v1)
- [TeleStyle code](https://github.com/Tele-AI/TeleStyle)
- [Style-CCL: Content-Preserving Style Transfer via Curriculum Continual Learning](https://arxiv.org/html/2606.14746v2)
- [CSGO: Content-Style Composition in Text-to-Image Generation](https://huggingface.co/papers/2408.16766)
- [StyleShot: A Snapshot on Any Style](https://arxiv.org/pdf/2407.01414)
- [StyleID: Style Injection in Diffusion](https://github.com/jiwoogit/StyleID)
- [Awesome Style Transfer with Diffusion Models](https://github.com/Westlake-AGI-Lab/Awesome-Style-Transfer-with-Diffusion-Models)
- [Qwen-Image-Edit hardware requirements discussion](https://huggingface.co/Qwen/Qwen-Image-Edit/discussions/6)
