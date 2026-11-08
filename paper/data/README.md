# paper/data · the numbers behind the paper's empirical figures

Aggregate statistics only. Nothing in this directory is an image, a hash, or
derived from a case; every file is the JSON that `research/run.py` wrote plus
the Markdown that `research/plot_routine.py` rendered from it. They are
committed so that every empirical figure in the paper regenerates from
committed code **and committed numbers**, which is the reproducibility
commitment in `governance/DRAFT_authorship_and_publication.md` §6.

| File | What | Regenerate |
|---|---|---|
| `routine-coco-val2017.json` | `--routine` results on COCO val2017 (5,000 photographs, 7 families × 4 intensities, PDQ / pHash / Blockhash, paired statistics) | `research/run.py --corpus ~/datasets/val2017 --routine --i-confirm-benign-corpus --limit 5000` (25 minutes on an M5 laptop, one core) |
| `routine-coco-val2017.md` | Tables 1–3 in the resubmission draft's shape | `research/plot_routine.py paper/data/routine-coco-val2017.json --corpus-label "COCO val2017" --md paper/data/routine-coco-val2017.md` |
| `../figures-en/paper-fig13-routine-residual.svg` | Figure 1 of the arXiv preprint | same command with `--svg` |
| `../figures-en/paper-fig14-routine-by-intensity.svg` | Figure 2: residual rate per intensity, crop and rotation | same command with `--svg-levels` |
| `frontier-models-2026.json` | Dated, primary-sourced image and video generator releases (July to November 2026) behind §5.3; each row carries its source URL and access date | hand-curated register; every row re-checked against its source before a new version |
| `frontier-models-2026.md` · `../figures-en/paper-fig15-frontier-timeline.svg` | Table 4 and Figure 3 | `python3 paper/plot_frontier.py --svg ... --md ...` |

**Corpus.** COCO 2017 validation images: 5,000 everyday photographs
(`http://images.cocodataset.org/zips/val2017.zip`, about 815 MB). The images
are Flickr photographs under Creative Commons licences; the COCO annotations
(not used here) are CC-BY 4.0. Measuring a hash function's error behaviour
over the corpus and publishing the resulting rates redistributes no image and
creates no derivative work (`research/COMPUTE.md`, "Which licence to pick").
The corpus lives outside the repository and never enters it.

**What these numbers are not.** Robustness under routine edits, not the
false-positive tail: RA-1 needs on the order of a million distinct
photographs and is a different experiment (`research/README.md`, RA-1).
