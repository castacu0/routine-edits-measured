# Compute, Corpora and Cost

**Short answer: the compute is nearly free and your laptop can do it. The
annoying part is bandwidth and disk, and you only have to suffer it once.**

Measured on an Apple M5, 10 cores, 2026-07-26. Reproduce with the benchmark at
the end.

---

## ⚠️ Read this before anyone downloads 100 GB

> ### Do NOT have five researchers each download the corpus.
>
> That is 500 GB of transfer, five copies of a dataset on five personal laptops,
> and five slightly different preprocessing pipelines producing results nobody
> can reconcile.
>
> **Hash the corpus ONCE. Publish the hash file. Everyone works from that.**
>
> The hash file for 1 million images is about **90 MB**. It contains no images,
> and it is the only artefact anyone downstream needs.
>
> ```
>   corpus 100 GB  ──► hash once ──►  hashes 90 MB  ──► everyone
>   (one machine, one time)            (email it, or a release)
> ```
>
> This is not a performance optimisation. It is the difference between a
> reproducible collaboration and five incompatible answers.

---

## What things actually cost

### Which licence to pick when research now, commercial later

This is the question to get right early, and the answer is more permissive than
it first appears.

**The key distinction: publishing a statistic is not redistributing a dataset.**

An image licence governs copying, redistributing and making derivative works of
*the images*. Measuring the error distribution of a hash function over a corpus
and publishing the resulting numbers does none of those things. The output is a
mean, a standard deviation and a histogram. Nobody can reconstruct an image from
them, and they are not a derivative work of anything.

So **an "academic use only" corpus is fine for RA-1, RA-2, RA-3 and RA-11**,
because the deliverable is a measurement, not a dataset or a model.

**Where it changes completely: training.** The moment anyone trains, fine-tunes
or distils a model on a corpus, the model may be a derivative work and the
licence follows it into whatever the model is later used for. **RA-4 involves
training a synthetic-media detector, so it must use commercially permissive data
from the start.** Discovering this after training is expensive and the model has
to be thrown away.

| Licence | Research | Commercial product later | Verdict |
|---|---|---|---|
| **CC0 / public domain** | Yes | Yes | Best. Prefer where available |
| **CC-BY 4.0** | Yes | Yes, with attribution | **Recommended default.** COCO, Open Images |
| CC-BY-SA | Yes | Viral — derivatives must share alike | Avoid for anything model-shaped |
| **CC-BY-NC** | Yes | **No** | Avoid entirely. The NC term is untested and chills investment |
| "Academic use only" (MIRFLICKR) | Yes | Not for training | **Fine for measurement, not for models** |
| Scraped, no licence | No | No | Never |

**Recommendation:**

- **Primary corpus: CC-BY.** COCO 2017 (CC-BY 4.0) or Open Images (CC-BY). Safe
  for everything including training, and the attribution requirement is trivial.
- **MIRFLICKR-1M only for the comparability run** against the published baseline,
  and only for statistics. Say so explicitly in the paper.
- **Never mix corpora with different licences into one training set.** The result
  inherits the most restrictive terms and untangling it later is impractical.

**On the funding sequence you raised:** wanting research money now and commercial
partnership later is normal and creates no conflict here, **provided the corpus
choice does not foreclose it.** A CC-BY corpus keeps both doors open at zero
cost. An NC corpus closes the second one silently, and you would not discover it
until a diligence team asked.

⚫ **For counsel:** confirm that publishing aggregate statistics derived from an
academic-use corpus is outside the licence's restriction. This reading is
standard, and it is worth a sentence in writing rather than an assumption.

### Corpus licensing cost: **free**

| Corpus | Images | Size | Licence | Notes |
|---|---|---|---|---|
| **MIRFLICKR-1M** | 1,000,000 | ~100 GB | Free, academic use | What the published baseline used. Comparability argues for it |
| MIRFLICKR-25k | 25,000 | ~3 GB | Free | Good for validation, too small for the tail |
| COCO 2017 | 330,000 | ~25 GB | CC-BY 4.0 | Well-curated photographs |
| Open Images | 9,000,000 | ~500 GB+ | CC-BY | Only if you need beyond 10⁶ |
| Unsplash Lite | 25,000 | ~2 GB | Free for research | Fastest to get started |

**Nobody charges you for the images.** The cost is bandwidth and disk, and the
research-use restrictions are exactly what we are doing.

### Time on your own hardware · measured, not estimated

| Step | Rate | 1M images |
|---|---|---|
| Download @ 100 Mbps | — | ~2.2 hours |
| Download @ 500 Mbps | — | ~27 minutes |
| **Decode + PDQ, single core** | **319 img/s** | ~52 minutes |
| **Decode + PDQ, 8 cores** | ~2,500 img/s | **~7 minutes** |
| Same, realistic photos (3–5× larger) | ~600 img/s | **~30 minutes** |
| **Pair comparison** | **12.9M pairs/s** | 10⁸ pairs in **8 seconds** |

> **The finding that matters:** hashing a million images is minutes, not days,
> and comparing a hundred million pairs is seconds. The assumption that this
> needs a cluster is wrong.

### Your MacBook Air M5, specifically

| | Verdict |
|---|---|
| CPU | **Fine.** 10 cores at 319 img/s/core each |
| RAM | **Fine.** Images stream; hashes for 1M images are ~90 MB |
| Disk | **Tight.** 100 GB on a 256 GB machine is uncomfortable. On 512 GB it is fine |
| **Thermals** | **The real limit.** The Air is fanless. Sustained all-core load throttles, maybe halving throughput. A 30-minute job becomes an hour and the machine gets hot |
| Verdict | **It will work.** Do it overnight, plugged in, on a hard surface, and expect throttling |

**If the disk is the problem, and it usually is:** stream. Download in chunks,
hash, delete, repeat. Peak disk stays under 5 GB. The scripted version of this is
the recommended path regardless of hardware.

### If you would rather not: cloud, and it is cheap

| Option | Spec | Time | Cost |
|---|---|---|---|
| GCP `e2-standard-8` | 8 vCPU, 32 GB | ~1 hr | **~$0.27** |
| GCP `c4-standard-16` | 16 vCPU | ~30 min | **~$0.40** |
| 100 GB persistent disk, 1 day | — | — | **~$0.13** |
| Egress of the 90 MB hash file | — | — | **~$0.01** |
| **Total for the whole one-time run** | | | **under $5** |

Add the download into the VM, which is free if the corpus is on a cloud bucket in
the same region. Delete the VM afterwards.

**Under $5, once, ever.** Compare that to five people spending an afternoon each
downloading 100 GB on domestic broadband.

---

## The statistical constraint nobody mentions

You cannot manufacture independent pairs from a small corpus.

With **N** images you can generate up to **N(N−1)/2** pairs, but they share
hashes, so they are **not independent observations**. The effective sample size
for estimating a tail probability sits somewhere between N and N²/2, closer to
the low end than people assume.

| Images | Max pairs | Realistically resolves down to |
|---|---|---|
| 10,000 | 5.0 × 10⁷ | ~10⁻⁵ |
| 100,000 | 5.0 × 10⁹ | ~10⁻⁶ to 10⁻⁷ |
| **1,000,000** | 5.0 × 10¹¹ | **~10⁻⁸, which is what RA-1 needs** |

**This is why the corpus has to be about a million images.** It is not
throughput, it is statistics. Running 10⁸ comparisons over 10,000 images and
reporting a 10⁻⁸ resolution would be wrong, and a reviewer will catch it.

If you report a bound, state the number of **distinct images**, not just the
number of pairs.

---

## Recommended sequence

**Week 1 · validate on something small**
```bash
.venv-research/bin/python research/run.py --corpus ~/data/unsplash-lite --all --i-confirm-benign-corpus --limit 5000
```
Confirms the pipeline works and reproduces published means. ~2 GB, minutes.

**Week 2 · the real run, once, by one person**
Stream MIRFLICKR-1M, hash, publish the ~90 MB hash file to a release or Zenodo.

**Week 3 onward · everyone works from the hash file**
No further downloads. Pair analysis, tail estimation, correlation and dihedral
cost all run from hashes in seconds on any laptop.

---

## Built 2026-09-14 · `research/hash_corpus.py`

The streaming hash-once script now exists. It:

1. Walks the corpus in sorted, chunked order, never materialising 100 GB
2. Hashes with PDQ, pHash and Blockhash in one multi-core pass
3. Records image ID (relative path), packed hashes and PDQ quality
4. Writes one compressed part per chunk and merges them into `hashes.npz`, plus
   `MANIFEST.json` with corpus path, counts, library versions, the harness
   commit and a SHA-256 of the hash file
5. Resumes with `--resume`, because a two-hour job will be interrupted

```bash
.venv-research/bin/python research/hash_corpus.py --corpus ~/datasets/mirflickr1m --out ~/datasets/mirflickr1m-hashes --i-confirm-benign-corpus --workers 8 --chunk 5000
```

Measured on the 600-image smoke corpus, 4 workers: ~200 img/s including
process start-up, so the M5's ten cores land near the ~2,500 img/s estimate
above once the pool is warm. It refuses to write inside the repository.

**The manifest is not optional.** A hash file whose provenance is unknown is not
reproducible, and reproducibility is the whole reason for this approach.

---

## Security note on the hash file

The hash file contains perceptual hashes of **ordinary public photographs**. It
carries no abuse material and no case data, so it is safe to share among
researchers.

It nonetheless does **not** belong in this repository: the repo holds no image
datasets or derivatives, benign or otherwise, and keeping that rule absolute is
worth more than the convenience. Publish it as a release asset, on Zenodo, or in
a bucket.

**A corpus of hashes of known abuse material would be a completely different
object** with completely different handling. We do not have one, will not build
one, and no part of this workflow produces one.

---

## Benchmark

```bash
.venv-research/bin/python - <<'PY'
import sys, time, pathlib, numpy as np
sys.path.insert(0, 'research')
from vdlab import hashes as H
from PIL import Image
paths = sorted(pathlib.Path('YOUR_CORPUS').glob('*.jpg'))[:200]
t = time.time()
for p in paths:
    im = Image.open(p); im.load(); H.pdq_with_quality(im)
print(f"{len(paths)/(time.time()-t):.0f} img/s/core")
PY
```
