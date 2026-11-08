**Table 1. Residual evasion rate by hash and transformation family** (COCO val2017; n = 5,000 images per condition, 20,000 image–intensity pairs per cell; Wilson 95 % CI).

| Transformation | PDQ (Meta, 256 bit) | pHash (64 bit) | Blockhash (256 bit) |
|---|---|---|---|
| Blur | 0.0% (0.0%–0.0%) | 0.0% (0.0%–0.0%) | 0.0% (0.0%–0.0%) |
| Brightness | 0.0% (0.0%–0.0%) | 0.0% (0.0%–0.1%) | 0.1% (0.0%–0.1%) |
| Center crop | 79.9% (79.3%–80.4%) | 59.0% (58.4%–59.7%) | 53.2% (52.5%–53.9%) |
| Gaussian noise | 0.0% (0.0%–0.1%) | 0.0% (0.0%–0.0%) | 0.0% (0.0%–0.1%) |
| JPEG compression | 0.0% (0.0%–0.0%) | 0.0% (0.0%–0.0%) | 0.1% (0.0%–0.1%) |
| Resize round-trip | 0.0% (0.0%–0.1%) | 0.0% (0.0%–0.0%) | 0.0% (0.0%–0.0%) |
| Rotation | 97.2% (97.0%–97.4%) | 72.6% (71.9%–73.2%) | 64.6% (64.0%–65.3%) |

**Table 2. Paired comparison, PDQ (Meta, 256 bit) vs. Blockhash (256 bit)** (McNemar with continuity correction on identical image–transformation pairs; difference = residual(blockhash) − residual(pdq); bootstrap resampled by image, 2,000 replicates).

| Transformation | Residual diff. (pp) | Bootstrap 95 % CI (pp) | McNemar χ² | p |
|---|---|---|---|---|
| Blur | -0.0 | -0.0 … +0.0 | exact_binomial | 0.250 |
| Brightness | +0.1 | +0.0 … +0.1 | exact_binomial | 0.007 |
| Center crop | -26.7 | -27.3 … -26.1 | 5,310.1 | <0.001 |
| Gaussian noise | +0.0 | -0.0 … +0.1 | exact_binomial | 0.388 |
| JPEG compression | +0.1 | +0.0 … +0.1 | exact_binomial | <0.001 |
| Resize round-trip | -0.0 | -0.0 … +0.0 | exact_binomial | 0.688 |
| Rotation | -32.6 | -33.0 … -32.1 | 6,504.0 | <0.001 |

**Table 3. Images per condition required to detect a given reduction in residual rate** (α = 0.05, power 0.80, two-proportion normal approximation; conservative for a paired design).

| Transformation | Baseline residual (PDQ) | 5 pp | 10 pp | 15 pp | 20 pp | 30 pp |
|---|---|---|---|---|---|---|
| Center crop | 79.9% | 1,098 | 294 | 139 | 82 | 39 |
| Rotation | 97.2% | 314 | 112 | 64 | 43 | 25 |

Corpus: `/Users/castacu0/datasets/val2017` · 9 of 5,000 images below Meta's PDQ quality floor (kept: robustness asks whether the same image survives an edit) · generated 2026-09-14T18:42:17 by `research/run.py --routine`.
