# Style Transfer Web Product: Market Research and V1 Spec

**Status:** Draft for review · **Date:** 2026-10-02 · **Revision:** 6 · **Working name:** TBD

**Decisions so far**

- The model runs in the visitor's browser. No photo is sent to us.
- The site is static and hosted on a free plan. There is no server and no per-image cost.
- Anonymous usage analytics are included: visits, button clicks, features used, downloads.
- The notebook in this repo is reference material. The product gets a new model and new code.
- If the browser cannot deliver good enough results, the model moves to free cloud hosting. Section 10 defines when and where.
- **New in revision 5: quality first.** Output quality is the only thing being optimised now. Download size, speed, memory and hosting limits are set aside until a model produces results people like. Nothing is chosen or reduced because it is small. Section 9.1 lists what is deferred.
- **New in revision 6: no generative models.** We use texture-transfer methods only and get the best quality that family can give. Being fast and never redrawing the photo is what separates the product from ChatGPT and Gemini.
- **New in revision 6: a quality enhancer in the flow.** Every result is cleaned and sharpened after style transfer, without destroying the photo's detail or its original look. It uses only the photo and the stylized result, never a model that invents content.
- **New in revision 6: style by part.** The visitor can choose where the style goes: the whole photo, the background, the hair, the clothes, or everything except face and skin. A prototype (research experiment 003) showed this works for photos of people and gives the most likable results so far.
- **Style reaches every object by default**, faces and pets included, crafted so that each thing keeps a prominent edge and nothing looks like a random pattern laid on top (research experiment 010). Leaving subjects natural is an option the visitor can switch on.

## 1. Summary

The product turns a personal photo into an artistic version of itself in a style the person chooses: flowers, forest, sky, lava, or any style image they pick from their device. It is free, needs no account, and takes a few taps. People share the result, print it, or use it as a profile picture.

**What we promise**

1. **Private.** Photos never leave the device. The work happens in the browser.
2. **Still your photo.** We restyle the picture and do not redraw it. Faces and large details stay as they were.
3. **Good at first look.** The first result shown has passed a quality check, so it is not a random outcome.
4. **Fast and easy.** One photo, one style, one result.

**What we are not:** an image editor or an image generator. There are no prompts.

**Business aim for V1:** traffic. Running cost is close to zero, so a quiet month costs nothing and a busy one does not create a bill.

**Order of work:** find the model with the best output first (section 9), then make it fast and small enough to ship, then build the web app.

**If the browser falls short:** the model runs on a free cloud service instead (section 10). Promise 1 then changes from "never leaves your device" to "sent, processed and not kept".

## 2. What exists today

The project began from `NeuralStyleTransfer.ipynb`, a year-old implementation of the Gatys et al. optimisation method. It was removed from the repo on 2026-10-02 at the founder's request and remains only in git history.

It is not the product's engine, and it is not a reference or a yardstick. The aim is a better method of our own. What exists now is the model work in `model/` and the experiment log in `research/`.

## 3. Market research

### 3.1 Demand

- **AI image generation software:** research firms put the 2026 market at roughly $0.48–0.56 billion, growing 17–19% a year. Definitions vary between firms, so treat this as an order of magnitude.
- **Where results end up:** wall art is estimated at $65–78 billion in 2026. Print-on-demand art is reported as the fastest-growing part of it (one source cites 23–25% a year). Several reports say over half of consumers prefer personalised prints.
- **Reading:** people want artistic versions of their own photos.

### 3.2 Competitors

| Type | Examples | What they do well | Where they are weak against our promises |
|---|---|---|---|
| General chatbots | ChatGPT Images 2.0, Gemini (Nano Banana) | Free or bundled, huge reach, can restyle from a typed request | Need an account. Photos go to a large AI company. They redraw the image, so faces and details can change. One hands-on test measured ChatGPT at 97–149 s per image with thinking on. |
| Creative suites | OpenArt (from about $10–14/month), Krea (from $10/month), Magic Hour | Style reference plus strength slider, many models | Sign-up and subscription. Too much tool for someone who wants one nice picture. |
| Commercially safe | Adobe Firefly | Licensed training data | Tied to an Adobe plan. |
| Preset filter apps | Prisma, Fotor GoArt | One tap, mobile | App install, subscription prompts, photos processed on their servers. |
| Model APIs | FLUX.1 Kontext ($0.04–0.08 per image), FLUX.1 Redux (about $0.012) | Anyone can wrap these in a weekend | Every image costs money and every photo is uploaded. |

### 3.3 Lessons from the last wave

- **Prisma (2016)** used the same family of technique. It reached about 70 million downloads in a few months, then the craze faded and the company pivoted.
- **Lensa (2022)**, from the same company, earned tens of millions during its "Magic Avatars" peak and was reported at under $600,000 a month by May 2024.
- **Lesson:** this kind of product can attract traffic quickly, and the traffic fades when the novelty does. Keep the running cost near zero, add new styles regularly, and make sharing bring new visitors.

### 3.4 Known technical weakness of the alternatives

Recent diffusion research papers repeatedly name the same two problems: content from the style image leaks into the result, and the structure of the content image is not preserved.

| | Our approach (neural style transfer) | Generative restyle (diffusion or chat models) |
|---|---|---|
| Faces, text, large details | Preserved by construction | Can change |
| Same inputs, same result | Yes | Usually not |
| Where the photo goes | Stays on the device | Uploaded to the provider |
| Turning a person into a cartoon character | No. Transfers colour, texture and brushwork only | Yes |
| Risk of an ugly result | Real, without tuning | Lower; outputs are usually polished |

The last two rows are our weaknesses. The fourth is accepted, since we do not sell that. The fifth is why the quality check in section 8.2 is a launch requirement.

### 3.5 Can this run in a browser?

- **GPU access:** WebGPU ships by default in Chrome and Edge, in Firefox (Windows from version 141, Apple Silicon Macs from 145), in Safari 26 on Mac, iPhone and iPad, and in Chrome on Android 12 and later. Older devices need a slower fallback.
- **Speed:** on the same machine, published tests show the GPU path running 1.4 to 9.4 times faster than the fallback path, depending on the model. The first run is slower because the browser compiles the GPU programs.
- **Small models exist:** MicroAST has about 0.47 million parameters, drops the large VGG network at run time, and its paper reports 4K output in about half a second on a desktop GPU. Its code is MIT licensed.
- **It has been done before:** Google's Magenta team shipped arbitrary style transfer in the browser in 2018, with a 9.6 MB model.
- **Limits:** iPhone Safari refuses canvases above about 16.7 million pixels and has tight memory caps. Phone GPUs expose far less memory than desktops. Output size has to adapt to the device.
- **Not yet known:** real speed and quality on ordinary phones. Section 9 measures this.

### 3.6 Free hosting and analytics

| Need | Finding |
|---|---|
| Hosting | Cloudflare Pages free plan: no bandwidth cap, commercial use allowed, 25 MB limit per file, custom response headers supported. Vercel's free plan prohibits commercial use. GitHub Pages has a soft limit of about 100 GB a month and no custom headers. |
| Analytics | Umami Cloud free plan: 100,000 events a month, cookieless, supports custom events for button clicks. PostHog's free plan allows 1 million events but is heavier and uses cookies unless configured otherwise. Cloudflare Web Analytics is free but cannot track button clicks. |

### 3.7 Legal landscape

This is not legal advice.

- No US or UK court has held that an artistic style is itself protected by copyright (as of mid-2026).
- A style *image* is still a copyrighted work unless the person owns it or it is in the public domain.
- In *Andersen v. Stability AI*, claims tied to outputs "in the style of" named artists survived dismissal. A trial was scheduled for September 2026; check the current status.
- **Implication for us:** the built-in gallery uses nature and texture images that we own or that are public domain. No styles are named after artists. Because nothing is uploaded, we never hold a visitor's photo or style image.
- **Training data:** published style transfer models, including MicroAST, are usually trained on WikiArt, a collection of artists' paintings. See section 9.3.

### 3.8 Free cloud hosting for the model (fallback)

Researched in case the browser route fails. "Free" here always has a catch, listed in the last column.

| Service | What is free | Suits | Catches |
|---|---|---|---|
| **Google Cloud Run** | 180,000 vCPU-seconds, 360,000 GiB-seconds and 2 million requests a month. Scales to zero when idle. | A small model running on CPU | Needs a billing account. Use beyond the allowance is charged. No GPU in the free allowance. First request after idle is slow. |
| **AWS Lambda** | 400,000 GB-seconds and 1 million requests a month, with no expiry. Container images up to 10 GB. | A small model running on CPU | New accounts start on a 6-month free plan and must then move to the paid plan to keep running. Use beyond the allowance is charged. CPU only. Requests are limited to about 6 MB, which is tight for photos. |
| **Oracle Cloud Always Free** | An always-on ARM machine with 2 cores and 12 GB of memory | A small model on CPU with no start-up delay | Cut in half from 4 cores and 24 GB in June 2026 with no announcement. Idle machines can be reclaimed. Free capacity is often unavailable. |
| **Modal Starter** | $30 of compute credit every month, GPUs included (about 50 hours of a T4). Scales to zero. | A larger model that needs a GPU | Credit does not carry over. Use beyond it is charged. First request after idle is slow. |
| **Hugging Face ZeroGPU** | A free account can host up to 2 Spaces on a shared GPU. Each visitor gets 2 minutes of GPU a day without logging in. | A GPU model at low traffic | Gradio apps only. The account must be 30 days old with a verified email. Visitors without an account have the lowest queue priority. Built for demos, not for products. |

**Ruled out**

- Hugging Face CPU Spaces: creating a Docker or Gradio Space now needs a paid plan ($9 a month).
- Render free plan: 512 MB of memory and sleeps after 15 minutes, with about a minute to wake.
- Koyeb free plan: 0.1 vCPU and 512 MB of memory, and a card hold at sign-up.
- Railway: $1 of credit a month.
- Fly.io: no free plan for new users.

**Rough capacity.** If one image takes 3 seconds of one CPU core with 2 GB of memory, Cloud Run's allowance covers about 60,000 images a month and Lambda's about 66,000. The 3 seconds is an assumption until the model is measured.

**Three things this research showed**

1. A free allowance is not a spending cap. Every option with a card on file charges for use beyond the allowance, so the service must stop itself.
2. Free plans change without warning. Oracle halved its plan, Fly.io removed its plan, and Hugging Face moved CPU Spaces to a paid plan, all recently.
3. Free GPU time is scarce. Free CPU time is plentiful. A model small enough to run on CPU has many more free homes.

## 4. What keeps us ahead

Nothing here is impossible to copy. These are the advantages a large AI tool is slow or unwilling to match:

| Advantage | What makes it real | What would make it empty |
|---|---|---|
| **Privacy** | Photos never leave the device, and anyone can verify it: the tool keeps working with the internet switched off after the first load. | Loading third-party scripts that could read the page, or wording the claim more broadly than the truth (section 8.4). |
| **It stays your photo** | The method restyles pixels and does not regenerate them. Faces get extra protection. | Generative models are improving at keeping likeness, so this gap narrows over time. |
| **Likable first result** | Styles are tested with human ratings before they enter the gallery, and every result passes automatic checks. | Showing whatever the model returns. |
| **Simplicity and cost** | No sign-up, no prompt, no limits, free. A company paying for servers per image cannot offer unlimited free use. | Adding features until it looks like every other tool. |
| **Our own model** | Trained by us for nature and texture styles and for keeping faces intact. | Shipping a public model unchanged, which anyone else can do in a day. |

## 5. Target user

**People who want an artistic version of a personal photo to share.** They have a photo of themselves, family, a pet or a place. They want it to look beautiful, they want it quickly, and they do not want to hand it to an AI company or learn a tool. Most arrive on a phone.

## 6. Goals

| # | Goal | How we will know |
|---|---|---|
| G1 | Results are liked at first look | 70% or more of rated first results get a thumbs-up, and 50% or more of results are downloaded or shared |
| G2 | It is fast | Median time from choosing a style to seeing the result: 5 seconds or less on devices with WebGPU, 20 seconds or less on the fallback |
| G3 | It loads quickly | First visit downloads 10 MB or less in total; the gallery is usable while the model loads; later visits load from the device's cache |
| G4 | It is easy | 50% or more of visitors who add a photo reach a result; the flow is three steps |
| G5 | It keeps the photo recognisable | In blind tests, people pick our output over a chatbot's for "still looks like my photo" in at least 60% of pairs |
| G6 | It brings traffic | 15% or more of results are shared with the share button; visits from shared links grow month over month |
| G7 | It costs nothing to run | Hosting and analytics stay within free plans |

All targets are starting hypotheses. G1 and G5 come first. G2, G3 and G7 are deferred until a model meets G1 (revision 5); they still apply at launch.

## 7. Non-goals for V1

| Not building | Why |
|---|---|
| Any server that receives photos | The privacy promise depends on there being none. The only exception is the fallback in section 10. |
| Accounts and sign-in | Works against privacy and ease |
| Payments | V1 is for traffic; section 12 covers what comes next |
| Editing tools, prompts, text-to-image | We are not an editor or a generator |
| Styles named after artists | Legal exposure in 3.7, and not needed |
| Public galleries or hosted share pages | We would have to store people's photos |
| Print-resolution output | Phone memory limits make it unreliable in a browser |
| Mobile apps, video, API | A responsive web page is enough for now |
| Advertising | Ad scripts contradict the privacy promise |

## 8. V1 scope

### 8.1 User stories

1. As a visitor, I want to add a photo and pick a style in a few taps, so that I get a result without learning anything.
2. As a visitor, I want the first result to look good, so that I do not have to experiment.
3. As a visitor, I want faces in my photo to stay recognisable.
4. As a visitor, I want to use my own style image when the gallery does not have what I want.
5. As a visitor, I want to make the style lighter or stronger if the first result is not quite right.
6. As a visitor, I want to save or share the result in a size that fits social media.
7. As a visitor, I want proof that my photo is not uploaded.
8. As the owner, I want to see which pages, buttons, styles and features people use, so that I know what to improve.

### 8.2 Requirements

**P0: required to launch**

| ID | Requirement | Acceptance criteria |
|---|---|---|
| R1 | Add a photo | Accepts JPG, PNG and WebP from camera roll or file. Photos display the right way up. Nothing is uploaded: the browser's network log shows no request containing image data. |
| R2 | Style gallery | At least 12 built-in styles (for example flowers, forest, sky, lava, water, autumn leaves). Every gallery image is owned by us or public domain. Each style passed the human rating test in section 9 before being added. |
| R3 | Own style image | A visitor can pick a style image from their device. It also stays on the device. If the image is unlikely to work (too small, or nearly flat colour), the visitor is told before the run. |
| R4 | Result in the browser | The model runs on the device's GPU when available and on the fallback otherwise. Progress is shown. The page stays responsive during the run. Speed meets G2. |
| R5 | Adapts to the device | Output size is chosen from what the device can handle: up to 2048px on the long side on capable devices, 1024px or less on weaker ones. A device that cannot run the model sees a clear message, not a crash. |
| R6 | Quality check on every result | Faces: detected faces receive a lighter style so they stay recognisable. Structure: the result is compared with the original, and if it has drifted past a set threshold the style is lowered and the run repeated once. Defaults: each gallery style carries its own tested settings. |
| R6b | Choose where the style goes | The visitor can apply the style to the whole photo, the background only, the hair only, the clothes only, or everything except face and skin. Switching between them is instant, with no new model run. The default is the whole photo, with every object styled and kept distinct. Mask edges follow the photo's own edges with no visible blocks or halo. Selecting pets and objects by tapping them is a fast follow (P1). |
| R6a | Enhancement on every result | Every result passes through the enhancer in section 9.2a before it is shown. The enhanced image has fewer artifacts and crisper detail than the raw result at the output size. Faces are no less recognisable after enhancement than before. The style is still clearly present. No step uses a model that invents content. |
| R7 | Two adjustments | A lighter-to-stronger slider and a "keep my photo's colours" switch. Identical inputs and settings return an identical image on the same device. |
| R8 | Before and after | A draggable divider over the two images, working on touch and mouse. |
| R9 | Save and share | Download as JPG or PNG. One-tap crops for square, portrait and story formats. The phone's own share sheet opens from a share button, with a link back to the site. A small corner tag with the site name is on by default and can be switched off. |
| R10 | Privacy statement | One plain sentence on the first screen, worded as in section 8.4, and a full privacy page. |
| R11 | Rating | Thumbs up or down on each result. Only the rating, the style and the settings are recorded. |
| R12 | Usage analytics | The events in section 8.3 are recorded. No cookies, no visitor identifier, no image data. |
| R13 | Landing page proof | At least six real before and after examples made with photos we have rights to. |
| R14 | Pages search engines can read | The home page and one page per gallery style are plain HTML with their own title, description and example images. |

**P1: fast follow**

- Works offline after the first visit, with a visible "try it in flight mode" note as proof of privacy.
- New gallery styles added on a regular schedule.
- HEIC photos.
- Blend two styles.

**P2: design so these stay possible**

- Larger output through tiling on capable devices.
- A print partner link from the result screen.
- Installable as an app from the browser.

### 8.3 Analytics

**Tool:** Umami Cloud free plan, called through one small `track()` function so the tool can be swapped later.

**Events**

| Event | Recorded with it | Question it answers |
|---|---|---|
| Page view | Page, referrer, campaign tag, device type, country | Where do visitors come from and which pages do they see? |
| `photo_added` | Source: camera, library or file | How many visitors start? |
| `style_selected` | Style name, or "own" | Which styles are popular? |
| `model_loaded` | Time band, whether cached | Is the first load too slow? |
| `stylize_done` | Style, GPU or fallback, output size, time band | How fast is it on real devices? |
| `stylize_failed` | Reason code | Where does it break? |
| `quality_rerun` | Style | How often does the quality check step in? |
| `strength_changed`, `keep_colour_toggled`, `compare_used` | New value or band | Which controls are used? |
| `crop_selected` | Format | Which formats matter? |
| `download` | Style, format, size, tag on or off | How many results are kept? |
| `share_clicked` | Style | How many results are shared? |
| `rating` | Style, up or down, settings | Are results liked? |
| `unsupported_device` | Browser family | How many visitors can we not serve? |

**Rules**

- No image data, file names, photo metadata or free text is ever sent.
- No cookies and no visitor identifier.
- Returning visitors are counted with a yes or no flag kept on the device and sent with the page view.
- Visits from shared results are counted with a tag on the shared link.

**Limit to watch:** the free plan allows 100,000 events a month. At roughly 10 events a visit, that is about 10,000 visits. Past that, move to a paid plan, self-host Umami, or switch to PostHog's larger free plan.

### 8.4 Privacy wording

The claim must match what happens exactly.

- **Say:** "Your photos never leave your device. The styling happens in your browser."
- **Also say:** "We count anonymous visits and button clicks to improve the site. We never see your images."
- **Do not say:** "No data leaves your browser" or "we collect nothing". Analytics events do leave.

To keep the claim true, all code, the model and fonts are served from our own domain. The only third-party request is the analytics script.

If the fallback in section 10 is used, the wording changes for any photo that is sent:

- **Say:** "Your photo is sent securely to our server only to make the result. It is not saved and is never used for training."
- **Do not say:** "never leaves your device" for those photos.

### 8.5 Tech stack

| Part | Choice | Why it suits this product |
|---|---|---|
| Site | Astro with TypeScript, built to static files | Produces plain HTML pages that search engines read, which matters for traffic. Only the tool itself loads as an interactive part. No server needed. |
| Tool interface | One React component inside the Astro page | Small, widely known, easy to hand to another developer |
| Model runtime | ONNX Runtime Web, WebGPU first, WebAssembly as the fallback | Runs models exported from PyTorch. Covers both the GPU path and older devices with one library. |
| Background work | A Web Worker runs the model | Keeps the page responsive during a run |
| Finding the parts of a photo | MediaPipe Image Segmenter, multiclass selfie model | Labels hair, face skin, body skin, clothes and background. Runs on the device, 16.4 MB, Apache 2.0 licence. It classifies pixels and invents nothing. It covers people only. In the prototype, animals come from a DeepLabV3 model (about 42 MB) and other prominent objects from U²-Net's small model (4.7 MB, Apache 2.0); browser-ready and smaller equivalents are to be chosen. Tap-to-select for arbitrary parts is still a fast follow. |
| Structure check | Plain TypeScript comparing edges of the original and the result | No extra model to download |
| Model training | PyTorch, exported to ONNX at half precision | PyTorch is already used in this repo. Half precision halves the download. |
| Hosting | Cloudflare Pages free plan | No bandwidth cap, commercial use allowed, supports the response headers that multi-threaded WebAssembly needs |
| Analytics | Umami Cloud free plan | Cookieless, supports button events |

Each file must stay under Cloudflare's 25 MB per-file limit, including the runtime's own files. Check this in M0.

**Repository layout**

| Folder | Contents |
|---|---|
| `web/` | The Astro site and the tool |
| `model/` | Training, evaluation and ONNX export in PyTorch |
| `research/` | Experiment log with output images, the method survey and the current plan |

## 9. Model research plan

### 9.1 What the model must do

**Required now**

| Requirement | Target |
|---|---|
| Quality | Meets G1 in human ratings. This comes before everything else. |
| Keeps the photo recognisable | Meets G5 |
| Works with any style image without retraining | Needed for "own style" |
| Strength control | One number from light to strong that works across the whole range |
| Licence | Code, weights and training data all allow commercial use |

**Deferred until a model meets the above**

| Requirement | Target at launch |
|---|---|
| Download size | 5 MB or less at half precision |
| Speed | Meets G2 at 1024px on the reference devices |
| Memory | Runs at 1024px on a mid-range phone without the tab crashing |
| Hosting limits | Files fit the free plan |

No model is ruled out for being large or slow at this stage. If the best one cannot be made to run in a browser, section 10 applies.

**Reference devices:** a mid-range Android phone from the last three years, an iPhone on iOS 26, and a laptop with integrated graphics.

### 9.2 Candidates to compare

The full survey, with published scores, licences and where each method can run, is in [research/landscape.md](research/landscape.md). The summary:

| Family | What it does | Status |
|---|---|---|
| A: texture transfer | Moves the style's colours and textures onto the photo's own pixels | **Ours.** Candidates, best first: SaMam, NNST, AesPA-Net, AdaAttN, CAP-VSTNet, StyTr2. Already tested: MicroAST, the notebook's method. |
| B: generative restyling | A large image generator redraws the photo, guided by the style | **Not used** (revision 6). Has the highest published scores, but redraws the photo and needs a server GPU for every image. |

- **SaMam is the leading candidate** after experiment 002: it keeps faces natural where MicroAST and the notebook's method did not. Its open problem is artifacts.
- The notebook's method is the oldest member of family A and is not developed further.
- All family A candidates run on the development laptop.
- Closed products (ChatGPT, Gemini) are run by hand on the same test set, only to know what a visitor can already get elsewhere.

### 9.2a The quality enhancer

A step after style transfer. Details and sources are in [research/landscape.md](research/landscape.md) section 5.

| | |
|---|---|
| Rule | It may use only the visitor's photo and the stylized result. No model that invents content. |
| Built so far | **Clean-up with detail kept** (experiment 006): the style is treated as a change to the photo, only the change is filtered, and the photo is never touched. **Three scales** (010): the change is split into one even tint per object, mid-sized patches, and fine texture. The tint is kept, the patches are removed, and a **texture** setting returns a chosen share of the fine pattern per part. **Separation** (008, 009): texture is kept off the boundaries between things, and some of the photo's own light and dark is kept. **Own colour** (007): parts can be given their own colour back. `enhance_auto()` applies a set of settings without choices from the user. |
| Default | Style on every object, faces and pets included, as an even tint with light texture (`CRAFTED`). Decided by the founder on 2026-10-02. |
| Options | **Protect subjects**: faces, pets and objects keep their own colour and get little texture (`PROTECT`, experiment 009). **Stronger style**: SaMam's 4-pixel checkpoint as the source (experiment 011). **Outlines**: a drawn line along boundaries, kept off faces. |
| Measured by | Style on subjects, style on the rest, edge prominence and blotchiness, averaged over the test set (`enhance.py <run> measure`) |
| Parts it works on | Face and skin, hair, clothes, animals, any other prominent object, and background, found by three small models that classify pixels and invent nothing |
| Steps still to build | Guided upscaling to the output size, mild sharpening |
| Allowed only if tested | A small learned upscaler, and never if it changes a face |
| Excluded | Face restoration models and diffusion upscalers. Both are documented to change identity or invent content. |
| Tested by | Checks E1 to E4 in [research/quality-checklist.md](research/quality-checklist.md): adds nothing invented, keeps the style, keeps the look, clearly cleaner and sharper |

### 9.3 Where we expect to improve on them

1. **Train on nature and texture images, not paintings.** This fits our gallery, and lets us say truthfully that the model was not trained on artists' work.
2. **Protect faces during training** by weighting the content loss more heavily on face regions and edges.
3. **Keep colours** by transferring style to brightness only and reusing the photo's own colour. This needs no model change.
4. **Shrink for the browser** with half-precision weights and, if needed, a smaller decoder.

### 9.4 How we judge

- **Test set:** 30 photos (single faces, groups, pets, landscapes, low light) across the 12 candidate styles.
- **Feature by feature:** every candidate is scored against the 13 features in [research/quality-checklist.md](research/quality-checklist.md), worked through in order: reliability, likeness, skin colour, artifacts, style richness, and so on.
- **Primary measure:** first-look rating by at least 15 people who do not know which model made which image.
- **Supporting measures:** the numbers proposed in the checklist. Time, memory and download size are recorded but deferred.
- **Rule:** choose the model people rate highest. Only then make it smaller and faster, checking after each change that the ratings hold. If none meets G1, improve quality before any web work. If a per-style network clearly wins on ratings, use those for the gallery and an any-style model for "own style".

### 9.5 Findings so far (M0)

Measured on 2026-10-02 on the development laptop (Intel integrated graphics plus an RTX 3050).

**MicroAST**

| Finding | Detail |
|---|---|
| Exports to ONNX correctly | 471,987 parameters, 1.9 MB. Output matches the authors' PyTorch code to within 0.00002. |
| Runs in Chrome on WebGPU | On Intel integrated graphics: 1.1 s at 512px, 3.5 s at 1024px, 13.6 s at 2048px. Measured before the fix below, so these are upper bounds. |
| The raw export was wasteful | 884 operations for a network with 31 convolutions. Most were shape arithmetic that runs on the CPU and stalls the GPU. Folding them leaves 170 with identical output. Browser speed after the fix is not yet re-measured. |
| One CPU core, no browser | 0.49 s at 512px and 1.93 s at 1024px, after the fix |
| Its strength setting is broken | Any value between 0 and 1 blows the output up to 11 times the valid range and gives a blank image. The released weights were only trained at full strength. Our export blends the photo with the full-strength result instead, which is correct at every value. A model we train ourselves should be trained across the range. |
| First look at quality | On a painting style the photo stays recognisable, with visible banding in flat areas such as sky and water |

**Tooling**

| Finding | Detail |
|---|---|
| ONNX Runtime Web's WebGPU file is 26.8 MB | 6.6 MB when compressed. It is over Cloudflare Pages' 25 MB per-file limit. Deferred with the other hosting limits. |
| Headless Chrome is unreliable for GPU timing | It worked once and stalled on later runs. Timings should be taken in an ordinary browser window. |

**Test set:** four photos (a portrait, a person with two dogs, a cat, a harbour) and five nature styles (flowers, autumn leaves, forest, lava, sky), all public domain or CC0. Sources are in `model/data/SOURCES.md`.

## 10. Fallback: free cloud hosting

The browser is tried first. This section applies only if it falls short.

### 10.1 When to switch

| Trigger | How we know | What we do |
|---|---|---|
| **A. Too slow or unsupported on some devices** | G2 is missed on a reference phone in M0 or M1. After launch: `unsupported_device` above 5% of visitors or `stylize_failed` above 2% of runs. | **Hybrid.** Capable devices keep running in the browser. Only devices that fail send the photo to the server. |
| **B. No browser-sized model is good enough** | G1 is missed at the end of the M1 time box, and a larger model or the notebook's optimisation method does meet it. | **Server for everyone.** The larger model runs in the cloud. |

Hybrid is preferred wherever it is enough. It keeps most photos on the device and keeps server use small.

### 10.2 Where to host

| Situation | First choice | Second choice | Why |
|---|---|---|---|
| The same small model, run on CPU (trigger A) | Google Cloud Run | Oracle Always Free machine | Cloud Run takes an ordinary container, accepts photo-sized requests, costs nothing when idle, and its allowance is large. Oracle has no start-up delay but is the least dependable. |
| A larger model that needs a GPU (trigger B) | Modal Starter | Hugging Face ZeroGPU | Modal's $30 monthly credit is the only free GPU option that works as an ordinary API behind our own site. ZeroGPU is free but built for demos. |

AWS Lambda is kept as a backup for the CPU case. Its request-size limit and the 6-month plan change make it a worse fit than Cloud Run.

### 10.3 How it is built

- **One container, one endpoint.** `POST /stylize` takes a photo, a style and the settings, and returns the result. The container runs ONNX Runtime with the same model file the browser uses (trigger A) or the larger model (trigger B).
- **Portable.** Nothing in the container depends on one provider, so moving hosts is a redeploy.
- **Same checks.** The face protection and structure check from R6 run on the server too.
- **Photos held in memory only.** Nothing is written to disk and images never appear in logs.
- **Only our site can call it.** Requests from other origins are refused.

### 10.4 Staying free

| Guard | Purpose |
|---|---|
| Per-visitor daily limit | Stops one visitor using the whole allowance |
| Daily budget counter that refuses work once reached | Makes the free allowance a real cap, since the providers do not |
| Maximum request size and output size | Bounds the work per image |
| Maximum number of running copies set to a small number | Bounds the worst-case bill |
| Billing alert at a low amount | Warns if a guard fails |

When the daily budget is reached, visitors on capable devices are unaffected. Others see a clear "busy today, try tomorrow" message.

### 10.5 What changes if the fallback is used

- **Privacy.** The strongest promise no longer holds for photos that are sent. The wording in section 8.4 applies, and the result screen states which path was used: "made on your device" or "made on our server".
- **Speed.** Upload time and start-up delay are added. G2 for server runs becomes 20 seconds or less.
- **Requirements.** R1's "nothing is uploaded" applies only to the browser path.
- **Analytics.** `stylize_done` records which path ran.
- **Legal.** A privacy policy covering processing of photos is needed, and the question of screening uploads returns (section 15, Q7).
- **Risk.** The product now depends on a free plan that the provider can change.

## 11. Success metrics

**Leading (first weeks)**

| Metric | Target | Source |
|---|---|---|
| Thumbs-up share among rated first results | 70% | `rating` |
| Results downloaded or shared | 50% | `download`, `share_clicked` |
| Visitors who add a photo and reach a result | 50% | `photo_added`, `stylize_done` |
| Median time to result | 5 s with WebGPU, 20 s on the fallback | `stylize_done` |
| Failed runs | under 2% | `stylize_failed` |
| Visitors on unsupported devices | under 5% | `unsupported_device` |

**Lagging (first 3 months)**

| Metric | Target | Source |
|---|---|---|
| Results shared with the share button | 15% | `share_clicked` |
| Visits from shared links | growing month over month | Link tag |
| Returning visitors | 20% of visits | Returning flag |
| Visits from search | growing month over month | Referrer |

**Stop and rethink if:** after 1,000 results, the thumbs-up share is under 50%. The quality promise is not being met and more traffic will not fix it.

## 12. After traffic: ways to earn

Running in the browser removes the cost. It also removes the easy paid feature: anything computed on the visitor's device cannot be reliably locked behind a payment.

1. **Print partner referral.** A link from the result screen to order a canvas or poster. The visitor chooses to send the file to the printer.
2. **Optional high-resolution render on a server.** Paid, clearly marked as leaving the device, and never the default.
3. **Advertising.** Not recommended, for the privacy reason in section 7.

Decide after launch, using download and share figures.

## 13. Risks

| Risk | Likelihood | Response |
|---|---|---|
| The fallback's free plan is cut or removed | Medium; three such changes were found in this research | Portable container (10.3); a second-choice host named for each case (10.2) |
| The fallback produces a bill | Medium without guards | The guards in 10.4 |
| A small model's results are not liked at first look | High without tuning | Section 9 runs before the web app; tested gallery; face protection; rating loop |
| Too slow or crashes on ordinary phones | Medium | Reference-device benchmark; output size adapts; fallback path; clear message on unsupported devices |
| First visit is slow because of the model download | Medium | 10 MB budget; gallery usable while loading; cached afterwards |
| Results differ between devices | Medium | Accept small differences; the "same result" promise is per device |
| Traffic spikes, then fades | Medium to high | New styles on a schedule; search pages per style; sharing loop |
| Chatbots close the "keeps your photo" gap | Medium to high over 12–24 months | Privacy, simplicity and free unlimited use do not depend on the engine |
| The privacy claim is worded more broadly than the truth | Medium | Fixed wording in 8.4; everything except analytics served from our own domain |
| Training data or a borrowed model has a licence that forbids commercial use | Medium | Check every licence in M0; train our own weights |
| Analytics outgrows the free plan | Certain if the product succeeds | The `track()` wrapper makes switching a one-file change |

## 14. Milestones

Durations are rough estimates for one developer. Research milestones are time-boxed, since quality work has no natural end.

| Milestone | What happens | Exit condition |
|---|---|---|
| **M0: Quality comparison** (about 2 weeks) | Run the candidates in 9.2 on the same photos and styles and compare the results side by side, with the notebook's optimisation method as the ceiling. Collect human ratings. Check licences. Speed and size are recorded but do not decide anything yet. | The best-rated approach is chosen by the rule in 9.4, and we know how far it is from G1 |
| **M1: Our model** (time-boxed to 4 weeks) | Train on nature and texture styles with face protection. Re-run the ratings. Choose the 12 gallery styles and their settings. | Meets G1 and G5 in ratings |
| **M1a: Make it shippable** (time-boxed to 2 weeks) | Shrink and speed up the chosen model for the browser, re-checking ratings after each change. Measure on the reference devices and on one CPU core. | Meets G2 and G3 with ratings intact. If not, apply the triggers in 10.1 and record the decision: browser only, hybrid, or server. |
| **M1b: Fallback service** (about 1 week, only if triggered) | Build the container in 10.3 with the guards in 10.4 and deploy to the host chosen in 10.2 | A photo sent from the test page returns a result, and the daily budget stop is shown to work |
| **M2: Web app** (about 3 weeks) | R1–R9, R13, R14 | A stranger makes and shares a result on a phone without instructions |
| **M3: Launch** (about 1 week) | R10–R12, privacy page and terms, domain | Public launch with analytics recording |
| **M4: Learn** | Offline mode, new styles, first earning option from section 12. Add the hybrid fallback if the launch figures hit trigger A. | Decided by M3 data |

## 15. Open questions

| # | Question | Who | Blocking? |
|---|---|---|---|
| Q1 | Which candidate wins the benchmark, and what are the real speed and size numbers? | Engineering, M0 | Yes |
| Q2 | Which image sources do we train on, and do their licences allow commercial use? This covers content photos, style textures, and the VGG network used as the training loss (trained on ImageNet, whose terms are limited to non-commercial research). | Legal and engineering | Before M1 |
| Q3 | Where do the 12 gallery style images come from: our own photos or public-domain sources? | Founder | Before M1 |
| Q4 | What must the privacy page say about analytics under the laws that apply (for example GDPR, India's DPDP Act)? | Legal | Before M3 |
| Q5 | Is the corner tag acceptable to users, or does it reduce sharing? | Founder, from M3 data | No |
| Q6 | Product name and domain | Founder | Before M3 |
| Q7 | If the fallback is used: is a payment card available for the cloud account, and does receiving photos create a duty to screen uploads for illegal content? | Founder and legal | Only if section 10 is triggered |

## 16. Sources

Market and competitors
- [Fortune Business Insights: AI Image Generator Market](https://www.fortunebusinessinsights.com/ai-image-generator-market-108604)
- [Grand View Research: AI Image Generator Market](https://www.grandviewresearch.com/industry-analysis/artificial-intelligence-ai-image-generator-market-report)
- [Research and Markets: AI Image Generator Market Report 2026](https://www.researchandmarkets.com/reports/6226884/ai-image-generator-market-report)
- [Persistence Market Research: Wall Art Market](https://www.persistencemarketresearch.com/market-research/wall-art-market.asp)
- [Fortune Business Insights: Wall Art Market](https://www.fortunebusinessinsights.com/wall-art-market-105009)
- [Magnetic Art: Wall Art and Home Decor Statistics 2026](https://www.magneticart.art/blog/wall-art-home-decor-statistics)
- [Magic Hour: 7 best AI style transfer tools (2026)](https://magichour.ai/blog/best-ai-style-transfer)
- [Wireflow: Best AI Style Transfer Tools in 2026](https://www.wireflow.ai/blog/best-ai-style-transfer-tools-in-2026)
- [Capterra: OpenArt Pricing 2026](https://www.capterra.com/p/10015082/OpenArt/pricing/)
- [G2: Krea Pricing 2026](https://www.g2.com/products/krea/pricing)
- [PhotoWorkout: ChatGPT Images 2.0 vs Gemini Nano Banana 2](https://www.photoworkout.com/chatgpt-images-2-vs-gemini-nano-banana/)
- [Price Per Token: Flux API Pricing 2026](https://pricepertoken.com/flux-pricing)

History
- [Wikipedia: Prisma (app)](https://en.wikipedia.org/wiki/Prisma_(app))
- [TechCrunch: Prisma Labs raises $6M](https://techcrunch.com/2019/04/30/prisma-labs-raises-6-7m-for-its-ai-powered-approach-to-visual-editing/)
- [Priori Data: Lensa AI Revenue, Users and Statistics](https://prioridata.com/data/lensa-ai-statistics/)

Running in the browser
- [Wikipedia: WebGPU](https://en.wikipedia.org/wiki/WebGPU)
- [Webo 360: WebGPU Browser Support in 2026](https://webo360solutions.com/blog/webgpu-browser-support/)
- [DEV: WebGPU vs WASM in onnxruntime-web](https://dev.to/yue_shu_c621a4a637f22396f/webgpu-vs-wasm-in-onnxruntime-web-14x-to-94x-faster-on-the-same-mac-depending-on-the-model-li5)
- [SitePoint: WebGPU vs WebASM browser inference benchmarks](https://www.sitepoint.com/webgpu-vs-webasm-transformers-js/)
- [ONNX Runtime: Web performance diagnosis](https://onnxruntime.ai/docs/tutorials/web/performance-diagnosis.html)
- [Pqina: Total canvas memory use exceeds the maximum limit](https://pqina.nl/blog/total-canvas-memory-use-exceeds-the-maximum-limit/)
- [Ayoob AI: WebGPU memory limits](https://ayoob.ai/blog/webgpu-maxstoragebufferbindingsize-limits-enterprise)
- [Google: MediaPipe Face Detector guide](https://developers.google.com/edge/mediapipe/solutions/vision/face_detector)

Models
- [MicroAST paper](https://arxiv.org/abs/2211.15313)
- [MicroAST code](https://github.com/EndyWon/MicroAST)
- [Magenta: Porting Arbitrary Style Transfer to the Browser](https://magenta.tensorflow.org/blog/2018/12/20/style-transfer-js/)
- [Style Transfer: A Decade Survey](https://arxiv.org/html/2506.19278v1)
- [Design and experimental research of on-device style transfer models for mobile environments](https://www.nature.com/articles/s41598-025-98545-4)
- [Less is More: Masking Elements in Image Condition Features Avoids Content Leakages](https://arxiv.org/pdf/2502.07466)

Hosting and analytics
- [Cloudflare Pages Free Tier Limits and Pricing 2026](https://dev.to/david_viejo_4d48fdfa7cfff/cloudflare-pages-free-tier-limits-pricing-2026-1f8f)
- [Stacktree: GitHub Pages vs Vercel in 2026](https://stacktr.ee/compare/github-pages-vs-vercel)
- [Dmytro Klymentiev: Best Free Web Analytics in 2026](https://klymentiev.com/blog/best-free-analytics-2026)
- [OpenPanel: Open source web analytics survey 2026](https://openpanel.dev/articles/open-source-web-analytics)

Free cloud hosting for the fallback
- [Google Cloud Run pricing](https://cloud.google.com/run/pricing)
- [nOps: Cloud Run pricing 2026](https://www.nops.io/blog/cloud-run-functions-pricing/)
- [AWS Lambda pricing](https://aws.amazon.com/lambda/pricing/)
- [Rackspace Spot: AWS Free Tier explained 2026](https://spot.rackspace.com/blog/aws-free-tier)
- [InfoQ: Oracle halves free tier Ampere A1 limits](https://www.infoq.com/news/2026/07/oracle-cloud-free-tier-limits/)
- [Beam: Modal pricing explained 2026](https://www.beam.cloud/blog/modal-pricing-explained)
- [Hugging Face: Spaces overview](https://huggingface.co/docs/hub/en/spaces-overview)
- [Hugging Face: Spaces ZeroGPU](https://huggingface.co/docs/hub/en/spaces-zerogpu)
- [SnapDeploy: Free backend hosting platforms 2026](https://snapdeploy.dev/blog/free-backend-hosting-2026-apis-servers)
- [ExpressTech: Fly.io alternatives after the free tier ended](https://expresstech.io/7-fly-io-alternatives-in-2026-real-pricing-after-the-free-tier-died/)

Legal
- [AI Lawsuit Tracker: Andersen v. Stability AI](https://ailawsuittracker.com/cases/andersen-v-stability-ai-ltd-3-23-cv-00201/)
- [NYU JIPEL: Andersen v. Stability AI](https://jipel.law.nyu.edu/andersen-v-stability-ai-the-landmark-case-unpacking-the-copyright-risks-of-ai-image-generators/)
