# Next stage plan: the style's own texture, on every object

Written 2026-10-02, after experiments 000 to 011.

## 1. Where we are

The pipeline is SaMam plus our enhancer. On all 20 test pairs:

| | Style on subjects | Edge prominence | Blotchiness |
|---|---|---|---|
| Raw model | 13.8 | 0.59 | 2.35 |
| Current default | 10.0 | 0.88 | 0.72 |

What works: every object is styled, edges are prominent, faces are sharp, nothing is blotchy, and a result takes well under a second on the laptop's GPU.

## 2. What is wrong now

**The style arrives as a colour tint, and not much more.** With the flowers style, the photo turns green; it does not look made of flowers. The only texture is SaMam's stamp pattern, which we keep low because it looks mechanical.

This is the gap between the current output and the product idea ("turn my photo into flowers, forest, lava"). It is the main thing this stage should close.

**Why it happens.** SaMam's published weights were trained on paintings, at small size. Given a nature photo as the style, it copies the colours and falls back on a generic stamp. The enhancer can clean and place what the model gives it. It cannot supply texture the model never produced.

## 3. Goal for this stage

**A person looking at the result should be able to tell which style was used from the texture alone, on every object, while each object still has a prominent edge.**

Measured by four numbers on the test set:

| Number | Now | Target |
|---|---|---|
| Texture likeness (new): how closely the result's fine texture matches the style image's | not yet measured | clearly better than now, as close to the reference method as we can get |
| Style on subjects | 10.0 | 10 or more |
| Outline strength (replaced edge prominence in experiment 013) | 0.81 | 0.80 or more |
| Blotchiness | 0.72 | 0.8 or less |

The last three are guards: texture must not be bought by losing what the last stage gained.

## 4. The work, in order

Each step states the problem, the change, what it should improve, and how we will know.

### Step 1. Make texture measurable and find the ceiling

| | |
|---|---|
| Problem | "Looks like the style" is judged by eye only, so progress cannot be tracked |
| Change | Add a texture likeness number to `enhance.py measure`. Run NNST, the slow optimisation method, on six pairs as the reference for the best texture this family of methods can produce. Its earlier 515 seconds per image was a memory overflow; at its intended size it should take a minute or two. |
| Should improve | Nothing visible. It tells us how far there is to go and whether the target is reachable. |
| Done when | The table in section 3 has a "now" value and a reference value |
| Effort | About half a day |

**Status, 2026-10-02.** Half done.

- **Done.** The texture likeness number is built and measured on all 20 pairs: raw SaMam 0.44, default 0.22, the 4-pixel option 0.24.
- **There is no outside "ceiling".** NNST froze the machine and is dropped. The founder then ruled out the original notebook's method as a yardstick and had it removed from the repo: the aim is a better method of our own, judged on our measures and by eye.

**Step 4 status, 2026-10-02.** Started early, as experiment 012.

- Matched patches: rejected (checkerboard).
- A style sheet per part: texture likeness 0.22 to 0.34. Works for dense texture styles, fails for scene styles, and sits flat on surfaces. Not yet the default.
- Edge number replaced (experiment 013): outline strength measures the outlines only. Default 0.81, style sheet 0.82. The old number scored a blurred result higher than a sharp one.
- Texture or scene decided per style (experiment 014), from how much the style's colour varies across the image: autumn gets the full sheet, flowers 0.68, forest 0.32, lava and sky none. Blotchiness 1.03 is above its guard; it may count real texture as blotches.
- Photo's colour mood kept (experiment 015, the founder's request on 2026-10-03): own colour plus the photo's brightness mix keeps the mood exactly (colour shift 12.2 to 0.7), but scene styles nearly vanish and texture is weaker. Default, option or partial: founder's decision.
- The founder changed direction on 2026-10-03: the style's pattern on chosen parts of the photo, in its own colours, with the photo's own colours everywhere else. 016 builds the sheet from the style image's most patterned square (texture likeness 0.37). 017 places it on parts with no tint and no model; on portraits it is the closest to the product idea yet.
- Next: remove the repetition, choose where the pattern goes more carefully, close the dark halo along outlines (research/README.md, end of 017). The sheet following each object's shading comes after. The guards in section 3 were set for "style on everything" and need restating for this direction.

### Step 2. Remove the lava style's red patches

| | |
|---|---|
| Problem | Large red patches on the portrait, cat and harbour. They are bigger than the scale the enhancer removes. |
| Change | Add a coarser scale to the split, so that an object's tint is even across the whole object |
| Should improve | Blotchiness, and first-look appeal for any style that is a scene with a subject |
| Done when | The patches are gone in the five lava results, and blotchiness measured at the larger scale drops |
| Effort | About half a day |

### Step 3. Decide the base model

Two cheap checks that could change what we build on. Both are worth doing before the large step.

| Check | Question | Why it matters |
|---|---|---|
| Small model plus enhancer | Does MicroAST with our enhancer score close to SaMam with our enhancer? | The enhancer now does most of the visible work. If the small model is good enough underneath it, the browser version becomes much easier: MicroAST already runs in a browser at 1.9 MB. |
| SaMam in a browser | Can SaMam be exported and run with ONNX Runtime Web at all, and how fast? | SaMam scans the image as a long sequence, which browsers may handle badly. Better to find out now than after tuning everything for it. |

| | |
|---|---|
| Done when | We have the four numbers for MicroAST plus enhancer, and a yes, no or "slow" for SaMam in Chrome |
| Effort | About a day and a half |
| Possible outcomes | Keep SaMam. Switch to the small model. Or keep SaMam and accept the server fallback in spec section 10. |

This step is a risk check, not optimisation. Size and hosting stay deferred.

### Step 4. Real texture from the style image

The main work of the stage.

| | |
|---|---|
| Problem | Section 2: the texture is a generic stamp, not the style |
| Change | Take the fine texture from the style image itself. Three sources to compare, cheapest first. |
| Should improve | Texture likeness, with the three guards held |
| Effort | Three to four days, with real uncertainty |

| Source | How it works | Cost | Note |
|---|---|---|---|
| SaMam, tuned | More shifted copies averaged, and the style fed at the scale that suits its texture | None | Cheap to try; unlikely to be enough alone |
| Patch-based texture transfer | A classical method: rebuild each object's surface from small patches of the style image, chosen to match the photo's light and dark. Uses only the photo and the style image, so it fits the no-generative rule. | Seconds per image on the GPU | The most promising route to "made of leaves". New code. |
| NNST | The reference from step 1, used directly | A minute or more per image | Too slow for the product; useful as the target and possibly for a later server "high quality" mode |

Whichever source wins is fed into the enhancer as its fine layer, so it inherits the per-part amounts, clean boundaries and photo detail already built.

Two refinements belong here, once a real texture exists:

- **Texture follows the object.** Scale it to the part (finer on a face than on a wall) and let it follow the object's shading.
- **Outlines revisited.** With real texture inside each object, a drawn boundary may add more than it does now.

### Step 5. Widen the test and get people's ratings

| | |
|---|---|
| Problem | Four photos and five styles, judged by one reader and four numbers |
| Change | Grow the test set to about 12 photos (group, child, low light, food, building, close-up object) and 10 styles (add water, sand, stone, bark, snow). Build a simple blind rating page: two results side by side, pick the one you like. |
| Should improve | Confidence. It also shows whether the numbers agree with what people like. |
| Done when | At least five people have rated, and we know which version they prefer and how often |
| Effort | About a day, plus the raters' time |

Also covered here, since the fast model makes them cheap: larger output sizes (checklist Q13), same input giving the same output (Q12), and strength control (Q11).

### Step 6. Decide what comes after

A short review with the results in hand:

- Is the quality good enough to start the web app?
- Or does it need our own trained model (spec milestone M1)?
- Which base model, from step 3?

## 5. Order and rough time

| Step | Effort | Depends on |
|---|---|---|
| 1. Measure texture, find the ceiling | half a day | nothing |
| 2. Lava patches | half a day | nothing |
| 3. Base model checks | a day and a half | nothing |
| 4. Real texture | three to four days | step 1 |
| 5. Wider test and ratings | one day plus raters | step 4 |
| 6. Review | an hour | step 5 |

About seven to eight working days. Step 4 is the uncertain one: it is research, and it may need a second approach if the first does not hold the guards.

## 6. Not in this stage

| Left out | Why |
|---|---|
| Training our own model | Days of GPU time on this laptop. Worth it only if step 4 shows the texture cannot be had another way. |
| Generative models | Ruled out by decision |
| Download size, hosting, the web app | Still deferred. Step 3 only checks feasibility. |
| Tap-to-select parts, more detection classes | The default no longer depends on detection quality |

## 7. Decisions for the founder

| Decision | Recommendation |
|---|---|
| Include step 3 now, or stay purely on quality? | Include it. It costs a day and a half and could save weeks of tuning a model that cannot ship. |
| Who rates in step 5? | You plus four or more people who have not seen the project |
| If patch-based texture works but takes a few seconds per image, is that acceptable? | Your call. It trades some speed for a much stronger style. |
