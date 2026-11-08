# Research Harness

Reproducible experiments for **RA-1**, **RA-2** and **RA-3** in
[`dossier/12_RESEARCH_AGENDA.md`](../dossier/12_RESEARCH_AGENDA.md). Built so a
researcher can produce a defensible result in week one rather than month two.

---

> ## 🔴 Benign corpora only
>
> This harness operates on **ordinary photographs**. Suitable corpora: Flickr 1M,
> Open Images, DIV2K, COCO, or your own photographs.
>
> It must never be pointed at abuse material, case data, or any dataset you are
> not licensed to process. If your question requires abuse material, that work
> happens inside an authorised holder's environment under their governance —
> see [`docs/ETHICS_AND_IRB.md`](../docs/ETHICS_AND_IRB.md).
>
> Two guards are built in: the harness refuses a corpus path inside this
> repository, and refuses to run without `--i-confirm-benign-corpus`. **Both are
> speed bumps, not security controls.** The actual control is you.

---

## Install

```bash
python3 -m venv .venv-research
```

```bash
.venv-research/bin/pip install -r research/requirements.txt
```

`pdqhash` wraps Meta's reference PDQ implementation, so results are directly
comparable to production rather than to a reimplementation.

## Run

```bash
.venv-research/bin/python research/run.py --corpus ~/datasets/flickr1m --all --i-confirm-benign-corpus --limit 20000
```

| Flag | Purpose |
|---|---|
| `--inter` | RA-1 · inter-image distribution and its tail |
| `--correlation` | RA-2 · error correlation across the stack (implies `--inter`) |
| `--dihedral` | RA-3 · recall gain and false-positive cost of D₄ indexing |
| `--intra` | Robustness to each transformation |
| `--routine` | Residual population under seven routine transformations × four intensities, with paired statistics (see below). Not part of `--all`; it is the slow one |
| `--boot` | Bootstrap replicates for `--routine` (default 2000) |
| `--mckeown-only` | Restrict to the seven transforms in arXiv:2212.08035, for comparability |
| `--limit`, `--comparisons`, `--seed` | Sample size and determinism |

Output: `research/results/results-<stamp>.json` and a Markdown summary written
to be pasted straight into a PR description.

---

## It reproduces the published baseline

Smoke test, 232 procedurally generated images, ~9k pairs:

| algorithm | our mean | published mean | our σ | published σ |
|---|---|---|---|---|
| **pdq** | **0.4999** | **0.5000** | **0.0318** | **0.0321** |
| phash | 0.4917 | 0.4904 | 0.0655 | 0.0649 |
| blockhash | 0.4871 | 0.4923 | 0.0781 | 0.0785 |

Published values: McKeown & Buchanan (arXiv:2212.08035) Table 3, ~50M pairs on
Flickr 1M. PDQ matches the published mean and σ to three decimal places; pHash
and Blockhash agree within 0.006. Matching this closely on a completely
different corpus is good evidence the implementations are correct.

> ## ⚠️ Do not cite the smoke-test numbers. Here is exactly why.
>
> The smoke test ran on **232 procedurally generated images**: coloured
> rectangles and ellipses on flat backgrounds, drawn by a script. They were
> never photographs.
>
> That matters because of **frequency statistics**, and this is worth
> understanding rather than taking on trust.
>
> **What a photograph looks like to a DCT.** Natural images follow an
> approximate **1/f power spectrum**: most of their energy sits in low spatial
> frequencies (broad gradients, large regions of similar tone), falling away
> smoothly toward high frequencies (fine texture, noise). This is a
> well-established property of natural scenes and it is *why* PDQ works — it
> keeps the 256 lowest-frequency DCT coefficients precisely because that is
> where a photograph's information is.
>
> **What our generated images look like.** Hard-edged geometric shapes produce
> the opposite: flat regions carrying almost no low-frequency variation, and
> sharp boundaries injecting strong high-frequency energy. The DCT coefficient
> distribution is nothing like a photograph's, so the *median threshold* PDQ
> applies lands somewhere different, and the resulting bit patterns are
> distributed differently.
>
> **The visible consequence.** The smoke test found the closest unrelated PDQ
> pair at **94 bits** of 256. McKeown & Buchanan, on a million real photographs,
> found **10 bits**. Our synthetic images are far *more distinguishable* from one
> another than photographs are, so **zero near-collisions occurred** and the
> false-positive rate could not be estimated at all.
>
> Real photographs collide because real photographs repeat: thousands of
> sunsets, thousands of beaches, thousands of similar portraits. That clustering
> is where every false positive comes from, and a script drawing random
> rectangles does not reproduce it.
>
> **What the smoke test does prove:** the implementations are correct, because
> PDQ's mean and standard deviation match published values to three decimals
> and pHash and Blockhash agree within 0.006. It proves the harness computes
> PDQ properly. It says nothing whatsoever about error rates.
>
> **Run on a real photographic corpus before reporting any number.** See
> [`COMPUTE.md`](COMPUTE.md) for which corpus, what it costs, and where to run
> it.

---

## What each experiment answers

### RA-1 · the tail
The published work reports the *range* of inter-image distance, so we know the
minimum observed but not the mass below the match threshold. That mass is the
false positive rate, and it currently sits somewhere in three orders of
magnitude.

The harness emits the empirical CDF at 5-bit intervals plus a full histogram.
When zero pairs fall below threshold it reports an **upper bound**
(`< 1/N`) rather than a rate, because "we saw none" is not "there are none".

**To resolve 10⁻⁸ you need on the order of 10⁸ pairs.** At `--comparisons 50`
that means ~2M images. Plan compute accordingly; this is the expensive one.

### RA-2 · correlation
Our fusion model assumes ρ ≈ 0.7 and that figure is a placeholder we invented.
The harness scores **every algorithm on identical pairs**, which is what makes
the comparison valid, and reports both Pearson r and a conditional lift: when
one algorithm puts a pair in its lowest percentile, how much more likely than
chance is another to do the same?

Smoke test showed **lift 7.6 for pdq|phash** and 2.2 for pdq|blockhash — exactly
the pattern the design predicts, since PDQ and pHash are both DCT descendants
and Blockhash is not. If that holds on a real corpus, it is a direct argument for
keeping a non-DCT signal in the stack.

### RA-3 · dihedral
Both sides of the trade in one pass. Smoke test:

- **Plain PDQ recall against a mirrored image: 0.0%.** Dihedral: **100.0%.**
- False-positive multiplier: unresolved at 11,550 trials, because zero false
  positives occurred at either setting.

The recall result is unambiguous and reproduces on any corpus: a horizontal flip
completely defeats non-dihedral PDQ. The cost side needs a corpus large enough to
produce false positives at all, which is the same scale problem as RA-1.

### Residual population under routine transformations · paired
**Added 2026-09-14.** The share of transformed images a hash FAILS to match
against its own original, per transformation family, pooled over four
intensities, with the statistics a reviewer asks for when two methods are
compared on the same images:

| family | intensities |
|---|---|
| `jpeg` | quality 90 / 70 / 50 / 30 |
| `center_crop` | keep 95 / 85 / 70 / 50 % of the area, rescale back |
| `resize_roundtrip` | down to 0.8 / 0.5 / 0.3 / 0.15, back up |
| `gaussian_noise` | σ = 5 / 10 / 20 / 35 (seeded from image content) |
| `rotation` | 2° / 5° / 10° / 15°, canvas kept, corners black |
| `brightness` | +10 / −10 / +25 / −25 |
| `blur` | Gaussian radius 0.5 / 1.0 / 2.0 / 3.5 |

Every algorithm is scored on the **same** transformed image, so the paired
tests are valid. Output per family: Wilson interval on every rate, McNemar on
identical pairs for each algorithm pair (exact binomial below 25 discordant
pairs), a bootstrap CI for the residual difference resampled **by image**, and
the two-proportion sample size needed to detect a 5 / 10 / 15 / 20 / 30 pp
improvement on the first algorithm's residual. Implementation:
[`vdlab/stats.py`](vdlab/stats.py) (numpy + stdlib, known-answer self-test:
`python research/vdlab/stats.py`), runner `residual_paired` in
[`vdlab/experiment.py`](vdlab/experiment.py), families in
[`vdlab/transforms.py`](vdlab/transforms.py).

This is the protocol of the September 2026 JOTS resubmission draft, so that
draft's residual table regenerates from committed code on Meta's reference
PDQ rather than on a 64-bit pHash, and on a real corpus rather than on
generated shapes. The sample-size formula reproduces that draft's Table 3
(1,325 / 345 / 159 / 92 / 42 at a 72.2 % baseline) to rounding.

```bash
.venv-research/bin/python research/run.py --corpus ~/datasets/coco-val2017 --routine --limit 8000 --i-confirm-benign-corpus
```

**Real corpus · COCO val2017, 5,000 photographs, 2026-09-14, 25 min on an M5
laptop, one core.** Residual evasion rate = share of edited images NOT matched
to their own original at the threshold (PDQ 31/256; the others scaled to the
same normalised distance). Wilson 95 % intervals in `paper/data/routine-coco-val2017.md`;
figure `paper/figures-en/paper-fig13-routine-residual.svg`; raw JSON
`paper/data/routine-coco-val2017.json`. **These numbers are reportable**, with
their scope stated: everyday photographs, robustness under routine edits, not
the false-positive tail.

| Transformation (4 intensities) | PDQ (Meta, 256 bit) | pHash (64 bit) | Blockhash (256 bit) |
|---|---|---|---|
| Blur r 0.5/1/2/3.5 | **0.0%** | 0.0% | 0.0% |
| Brightness ±10/±25 | **0.0%** | 0.0% | 0.1% |
| Center crop 95/85/70/50 % area | **79.9%** (79.3–80.4) | 59.0% | 53.2% |
| Gaussian noise σ 5/10/20/35 | **0.0%** | 0.0% | 0.0% |
| JPEG q 90/70/50/30 | **0.0%** | 0.0% | 0.1% |
| Resize ×0.8/0.5/0.3/0.15 | **0.0%** | 0.0% | 0.0% |
| Rotation 2/5/10/15° | **97.2%** (97.0–97.4) | 72.6% | 64.6% |

Per intensity, PDQ: center crop keeping 95 % of the area already loses 19.8 %,
85 % loses 99.8 %, 70 % and 50 % lose 100 %; rotation by 2° loses 88.8 %, 5° and
beyond lose 100 %. Paired tests: PDQ vs. Blockhash differs on crop by −26.7 pp
(bootstrap −27.3 … −26.1, McNemar χ² = 5,310) and on rotation by −32.6 pp
(−33.0 … −32.1, χ² = 6,504); on JPEG and brightness the difference is +0.1 pp
and still "significant" (exact binomial p < 0.001 and 0.007), which is the
large-n caution in one row. Only 9 of the 5,000 photographs fall below Meta's
PDQ quality floor, against 318 of 600 generated shapes in the smoke test below.

Smoke test, 600 generated images (`make_synthetic_corpus.py`, seed 1), 3.5 min
on one core, **not citable** for the reasons in the box above and one more:
318 of the 600 sit below Meta's PDQ quality floor, which is the generator
telling you these are not photographs:

| family | pdq | phash | blockhash |
|---|---|---|---|
| jpeg | 0.0% | 0.0% | 1.4% |
| center_crop | 79.2% | 55.9% | 27.5% |
| resize_roundtrip | 0.0% | 0.0% | 0.1% |
| gaussian_noise | 0.8% | 0.0% | 1.8% |
| rotation | 98.8% | 81.5% | 64.3% |
| brightness | 0.0% | 0.0% | 0.8% |
| blur | 0.0% | 0.0% | 0.3% |

Even here the shape of the answer is the one worth carrying forward: geometric
edits dominate, and the non-DCT hash fails differently (crop residual 27.5 %
against PDQ's 79.2 %, McNemar χ² = 1233, bootstrap CI −53.7 … −49.7 pp). Whether
that survives on photographs is exactly the run to do next.

### From a results file to the paper

```bash
.venv-research/bin/python research/plot_routine.py research/results/results-<stamp>.json --corpus-label "COCO val2017" --svg paper/figures-en/paper-fig13-routine-residual.svg --md paper/data/routine-coco-val2017.md
```

[`plot_routine.py`](plot_routine.py) reads only aggregate statistics (rates,
intervals, test statistics; no hashes, no pixels) and writes the figure in the
same style as the other paper figures plus paste-ready Markdown for Table 1
(residual by family and hash, Wilson CI), Table 2 (paired McNemar and bootstrap
for one pair, default `pdq~blockhash`, `--pair` to change) and Table 3 (sample
size), and with `--svg-levels` the per-intensity figure for crop and rotation (Figure 2 of the arXiv preprint). The results file that backs a published figure is copied to
`paper/data/` so the figure regenerates from committed code and committed
numbers; `research/results/` itself stays gitignored.

### Intra-image robustness
Smoke-test recall at threshold:

| transform | pdq | phash | blockhash |
|---|---|---|---|
| compression q30 | 100% | 100% | 98.8% |
| scale 150% | 100% | 100% | 100% |
| thumbnail 96px | 100% | 100% | 100% |
| screenshot | 100% | 100% | 100% |
| laundering chain | 100% | 100% | 100% |
| watermark | 39.6% | 51.7% | 97.5% |
| crop 5% | 0.0% | 34.2% | 28.7% |
| border 30px | 0.0% | 8.3% | 0.4% |
| **mirror** | **0.0%** | **0.0%** | **0.0%** |

Two findings worth carrying forward even at this sample size: **mirroring
defeats all three**, and **PDQ is markedly more brittle to geometric change
(crop, border) than the others** while being the most robust to compression.
That is the expected consequence of its downsampling stage, and it is an
argument for pairing it with an algorithm that fails differently.

`laundering_chain` — platform recompress → screenshot → repost — is the
realistic case and the one to report. That every hash survives it is genuinely
good news and worth stating.

---

## Hash a corpus once, share the hashes

```bash
.venv-research/bin/python research/hash_corpus.py --corpus ~/datasets/mirflickr1m --out ~/datasets/mirflickr1m-hashes --i-confirm-benign-corpus --workers 8
```

[`hash_corpus.py`](hash_corpus.py) is the streaming, resumable, multi-core
hash-once script [`COMPUTE.md`](COMPUTE.md) asked for: PDQ + quality, pHash and
Blockhash in one pass, one compressed part file per chunk (`--resume` skips the
ones that exist), merged into `hashes.npz` with a `MANIFEST.json` recording
corpus path, counts, library versions, harness commit and a SHA-256. About 90
bytes per image, no pixels. It refuses to write inside the repository; publish
the output as a release asset or on Zenodo.

## A corpus to smoke-test with

```bash
.venv-research/bin/python research/make_synthetic_corpus.py --out ~/datasets/vd-synthetic --n 1000
```

Deterministic generated images (gradient + noise + 3–7 shapes), seeded per
image, written outside the repo. For proving the pipeline runs and for
like-for-like reproduction of anything computed on a corpus of this kind.
Never for a number about real content; see the box above.

## Layout

```
research/
  run.py                    CLI, corpus guards, Markdown summary
  hash_corpus.py            hash once, resumable, manifest + checksum
  make_synthetic_corpus.py  deterministic smoke-test images, outside the repo
  plot_routine.py           results JSON → paper figure (SVG) + Table 1/2/3 in the draft's shape
  regression.py             hash-stability check against hash_baseline.json
  requirements.txt
  vdlab/
    hashes.py               PDQ (Meta bindings), pHash, Blockhash, DCT
    transforms.py           the evasion set, the laundering chain, the 7×4 routine set
    experiment.py           inter, intra, correlation, dihedral, residual_paired runners
    stats.py                Wilson, McNemar, bootstrap-by-image, sample size (self-tested)
    guard.py                corpus-outside-the-repo and benign-confirmation guards
  results/                  gitignored output
```

## Extending it

- **A new hash:** add to `ALGORITHMS` in `hashes.py`. It needs to return a numpy
  bool array; everything else follows.
- **A new transform:** add to `TRANSFORMS` in `transforms.py`; a new routine
  family with intensities goes in `ROUTINE_LEVELS`.
- **A new experiment:** add a runner to `experiment.py` returning a plain dict,
  then a section in `summarise()`.
- **A new statistic:** add it to `stats.py` with a known-answer check in
  `_selftest()`; the nightly workflow runs that self-test.

Keep every runner deterministic given a seed. A number that cannot be
regenerated cannot be defended, and in this project everything gets challenged.

## Before you publish

- Run on a real photographic corpus, not the smoke-test generator.
- State your sample size and the resolution limit it implies.
- Report an upper bound when you observe zero events. Never report zero.
- Send the result to us before submission so we can correct our own materials —
  see [`CONTRIBUTING.md`](../CONTRIBUTING.md). We are asking for notice, not
  approval.
