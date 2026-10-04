# Output quality checklist

The features of an output image that we test and improve, one at a time. Every candidate model is scored against this list on the same test set, and the scores are recorded in the research log.

## How we use it

1. Take the next feature in the order below.
2. Agree what "pass" means for it, using the test images named in the table.
3. Score every candidate on that feature.
4. Fix or tune, re-run, and record before and after images in the research log.
5. Move to the next feature only when the current one passes or is consciously accepted.

A feature is judged by eye first. The "number to track" column is a measurement that lets us see progress between runs without re-judging everything by eye. Those measurements are proposals and none is built yet.

## The features, in working order

| # | Feature | Good looks like | Best test images | Number to track |
|---|---|---|---|---|
| Q1 | **Reliability** | Every photo and style pair gives a valid image. Never blank, black or broken. | All 20 pairs | Share of pairs giving a valid image |
| Q2 | **People stay themselves** | A face is recognisably the same person. Eyes, nose and mouth are not bent, smeared or replaced. | portrait, astronaut_dogs | Face-recognition similarity between photo and result |
| Q3 | **Shapes stay put** | Outlines and objects keep their position and shape: ears, whiskers, sails, the flag's stars. | cat, harbour, astronaut_dogs | Structure distance between photo and result (LPIPS or CFSD) |
| Q3a | **Things stay separate** | Every element keeps a prominent edge. The person stands apart from the background, and each object stands apart from its neighbours. Nothing merges into one random texture. | astronaut_dogs, portrait, harbour with autumn | Contrast across the photo's object boundaries, compared with the photo |
| Q4 | **Skin and fur colour** | Skin and fur stay a believable colour unless the user asks for a strong look. No green or red faces. | portrait, astronaut_dogs, cat with flowers, forest, lava | Colour shift inside the face region |
| Q5 | **No artifacts** | No woven or plaid pattern, speckles, halos around edges, banding or blotches. | Any photo with flat or blurred areas: cat, portrait | Fine-pattern energy in areas that were smooth in the photo |
| Q6 | **The style arrives** | The style's own texture and pattern are visible. It is more than a colour tint. | All photos with autumn and flowers | Style similarity between style and result (CSD or Gram distance) |
| Q7 | **Style goes where it makes sense** | Subject and background are each treated sensibly. No flowers growing on a face, no lava dots on a dog. | astronaut_dogs, portrait | By eye for now |
| Q8 | **Fine detail** | Small details stay crisp: eyes, whiskers, the NASA patch, the small boats. | cat, astronaut_dogs, harbour | Sharpness in detail regions compared with the photo |
| Q9 | **First-look appeal** | A person seeing it for the first time likes it. | All 20 pairs | Human rating 1 to 5; an automatic aesthetics score as a rough stand-in |
| Q10 | **Any style image works** | A dense texture (autumn leaves) and a scene with a subject (lava fountain, forest path) both give good results. | Each photo across all five styles | Spread of Q9 ratings across the five styles |
| Q11 | **Strength control** | One slider from light to strong, smooth all the way, nothing breaks in between. | One photo at five strengths | Smoothness of change between steps |
| Q12 | **Same in, same out** | The same photo, style and settings give the same image. | Any pair, run twice | Pixel difference between two runs |
| Q13 | **Holds at larger sizes** | At 1024px and 2048px the result looks like the 512px one, with no new artifacts and no shrunken texture. | harbour, portrait | By eye, plus Q5 at each size |

Deferred until a model passes the list above (spec section 9.1): speed, download size, memory, hosting limits.

## The enhancer's own checks

The quality enhancer (`landscape.md` section 5) runs after style transfer. It exists to raise Q4, Q5, Q8 and Q13. It is tested by comparing each result before and after enhancement.

| # | Check | Pass means | Number to track |
|---|---|---|---|
| E1 | **Adds nothing invented** | Everything in the enhanced image was in the photo or in the stylized result. No new features, no changed face. | Face similarity and structure distance are no worse after enhancement than before |
| E2 | **Keeps the style** | The style's texture is still there. The enhancer has not smoothed it away or turned the result back into the photo. | Style similarity (Q6) is no lower after enhancement |
| E3 | **Keeps the look** | The mood of the result is unchanged: brightness, contrast and colour balance are the same or closer to the photo's, never further from it. | Brightness and contrast difference against the photo |
| E4 | **Clearly cleaner and sharper** | Side by side, the enhanced image has fewer artifacts and crisper detail at the final output size. | Q5 and Q8 numbers improve |

E1 comes first. An enhancer that fails E1 is rejected however good its output looks.

## Why this order

- **Q1 first.** A method that sometimes returns a black image cannot be judged on anything else.
- **Q2 to Q4 next.** The product is for personal photos. A result that damages a face is a failure however good the style looks.
- **Q3a was added on 2026-10-02** at the founder's request, after seeing results where the person and objects merged into the style texture.
- **Q5 before Q6.** Artifacts are what make a result look cheap. Removing them often matters more than adding style.
- **Q6 to Q8** are where the result becomes attractive.
- **Q9** is the goal the others serve. It is rated throughout, and decided at this point.
- **Q10 to Q13** make a good result dependable.

## Where the tested methods stand

Judged by eye. SaMam and MicroAST were run on all 20 pairs (experiments 000 and 002). The enhancer was tried on 3 pairs (experiment 006). The notebook's method was run on 5 pairs (experiment 001).

| # | Feature | SaMam + enhancer (current best) | SaMam alone | MicroAST | Notebook's method |
|---|---|---|---|---|---|
| Q1 | Reliability | Pass on the 3 pairs tried | Pass: 20 of 20 valid | Pass: 20 of 20 valid | **Fail: 1 of 5 diverged** and came out black |
| Q2 | People stay themselves | **Pass:** the face is the photo's own, sharp and unmarked | Pass at a glance; close up there are crackle marks on the face | Pass: recognisable | Recognisable, face darkened |
| Q3 | Shapes stay put | Pass | Pass | Pass | Pass on the one photo tested |
| Q3a | Things stay separate | **Much improved:** people, pets and prominent objects are each their own part, keep their own colour, and have texture kept off their outlines (experiment 009) | **Fail:** everything merges into one patterned mass | Not assessed | Not assessed |
| Q4 | Skin and fur colour | **Pass for detected subjects:** faces, skin and animals keep their own colour (experiment 007) | Mostly pass: skin stays natural; white fur turns green | **Fail:** green and red faces | **Fail:** green face with flowers |
| Q5 | No artifacts | **Pass at texture 0.** Open: the lava style's large red patches | **Fail:** repeating stamp pattern, red patches with lava, a line at some borders | **Fail:** woven pattern | **Fail:** red speckles with lava |
| Q6 | The style arrives | As colour and tone at texture 0; as texture where texture is turned up | Fair: colour and pattern on backgrounds and clothes | Weak: mostly a tint | Better: real leaves and flowers appear |
| Q7 | Style goes where it makes sense | **Controlled:** texture by part keeps the face clean and puts texture on the background | Good by default: the subject is styled more lightly | Not applicable | Mixed |
| Q8 | Fine detail | **Pass:** freckles, whiskers, clouds and waves are the photo's own | Kept at a glance; damaged close up | Partly kept | Softened in the lava and sky rows |
| Q9 | First-look appeal | Best so far; not yet rated by people | Fair: sky and lava are likable on people | Low on people and pets, fair on the landscape | Not rated |
| Q10 | Any style image works | Not tested beyond 3 pairs | Mixed | Weak | Not tested enough |
| Q11 | Strength control | Texture dial works smoothly from 0 to 1; strength itself not tested | Not tested | Built-in control is broken; our blend works | Not tested |
| Q12 | Same in, same out | Not tested | Not tested | Expected to pass; not confirmed | Not guaranteed: two runs of the same pair followed different paths |
| Q13 | Holds at larger sizes | Not tested | Not tested | Not tested | Not tested |

**The enhancer's own checks (first version, 3 pairs, by eye)**

| # | Check | Result |
|---|---|---|
| E1 | Adds nothing invented | Pass by construction: every pixel is the photo plus a smoothed copy of the model's change |
| E2 | Keeps the style | Partly: colour and tone are kept; fine texture is removed unless the texture setting returns it |
| E3 | Keeps the look | Looks right by eye; no measurement yet |
| E4 | Clearly cleaner and sharper | Pass: see the close-ups in experiment 006 |

**Update after experiment 010.** The founder asked for style on every object, faces and pets included, crafted and with prominent edges. The table's first column describes the "protect subjects" option from experiment 009. The default is now the `CRAFTED` settings, which differ from that column in three rows:

| # | Feature | With the default (`CRAFTED`) |
|---|---|---|
| Q4 | Skin and fur colour | Skin and fur take the style's colour, by design. Even and unblotched. The protect option restores natural colour. |
| Q5 | No artifacts | The pink blotches on animals are gone: blotchiness fell from 1.39 to 0.72. The lava style's large red patches remain. |
| Q6 | The style arrives | On every object: style on subjects rose from 5.7 to 10.0, against 13.8 for the raw model |

**Measured, on all 20 pairs** (experiment 010):

| Version | Style on subjects | Style on the rest | Edge prominence | Blotchiness |
|---|---|---|---|---|
| Raw SaMam | 13.8 | 18.6 | 0.59 | 2.35 |
| Protect subjects (009) | 5.7 | 12.3 | 0.87 | 1.39 |
| Default (010) | 10.0 | 14.1 | 0.88 | 0.72 |
| Stronger style, 4-pixel (011) | 12.6 | 14.5 | 0.78 | 0.80 |

| Style sheet per part (012, not default) | 10.1 | 14.6 | 0.55 | 1.30 |

Texture likeness, added in experiment 012: raw SaMam 0.44, default 0.22, style sheet per part 0.34.

Experiment 014 gives each style a share of the style sheet from how much its colour varies across the image (texture likeness 0.25, blotchiness 1.03). Experiment 015 keeps the photo's colour mood as an option: colour shift 12.2 to 0.7, at the cost of scene styles nearly vanishing.

Outline strength replaced edge prominence in experiment 013 (the old number scored a blurred result higher than a sharp one): raw SaMam 0.79, protect subjects 0.89, default 0.81, 4-pixel 0.74, style sheet per part 0.82.

**What is open, in order**

1. **Texture that is the style's own** (Q6). Experiment 012 gets it for dense texture styles (leaves, flowers); 014 keeps it off scene styles (lava, sky, forest). Open: the texture sits flat on surfaces, and blotchiness may count real texture as blotches.
1a. **Photo's colour mood or style's colour** (015). Keeping the photo's mood works, but removes most of a scene style. Founder's decision.
2. ~~The edge prominence number is no longer trustworthy.~~ Replaced by outline strength (013). It shows the default's outlines are weaker than the photo's (0.81); a candidate for a later step.
3. **The lava style's large red patches** (Q5). They are bigger than the scale the enhancer removes.
3. **Rating by people.** The four numbers above stand in for it and do not replace it.
4. **Q10 to Q13:** any style image, strength control, repeatability and larger sizes are untested with the enhancer. Larger sizes are now practical, since SaMam runs in a quarter of a second.
