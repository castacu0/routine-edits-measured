#!/usr/bin/env python3
"""
Violencia Digital · research harness entry point
================================================

Runs the experiments behind RA-1 (tail of the inter-image distribution),
RA-2 (error correlation across the matcher stack) and RA-3 (what dihedral
robustness costs). See dossier/12_RESEARCH_AGENDA.md.

    python run.py --corpus ~/datasets/flickr1m --limit 20000 --all

Output goes to research/results/ as JSON plus a Markdown summary.

────────────────────────────────────────────────────────────────────────────
CORPUS REQUIREMENT — read this before pointing it at anything
────────────────────────────────────────────────────────────────────────────
This harness is BENIGN-ONLY. It operates on ordinary photographs. Suitable
corpora: Flickr 1M, Open Images, DIV2K, COCO, or your own photographs.

It must NEVER be pointed at abuse material, at case data, or at any dataset
you are not licensed to process. If your research question requires abuse
material, that work happens inside an authorised holder's environment under
their governance — see docs/ETHICS_AND_IRB.md.

The harness refuses to run against a path inside this repository, and requires
you to state affirmatively that the corpus is benign. Both are speed bumps, not
security controls: the actual control is you.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from vdlab import experiment as X  # noqa: E402
from vdlab import transforms as T  # noqa: E402
from vdlab.guard import guard_corpus  # noqa: E402

RESULTS = Path(__file__).resolve().parent / "results"


def progress(label: str):
    def report(i, total):
        pct = 100 * i / max(1, total)
        print(f"\r  {label}: {i}/{total} ({pct:.0f}%)", end="", flush=True)
    return report


def summarise(results: dict) -> str:
    """Markdown summary. Written so it can be pasted into a PR description."""
    lines = ["# Research harness results", ""]
    lines.append(f"- generated: {results['generated']}")
    lines.append(f"- corpus: `{results['corpus']}`")
    lines.append(f"- seed: {results['seed']}")
    lines.append("")

    if "inter_image" in results:
        r = results["inter_image"]
        lines += ["## RA-1 · Inter-image distribution", "",
                  f"{r['images_used']:,} images, {r['pairs']:,} pairs. "
                  f"{r['images_skipped_low_quality']:,} skipped on PDQ quality.", "",
                  "| algorithm | mean | median | stdev | min | min bits | ≤ threshold | empirical FPR |",
                  "|---|---|---|---|---|---|---|---|"]
        for a, s in r["algorithms"].items():
            fpr = (f"{s['empirical_fpr']:.2e}" if s["empirical_fpr"]
                   else f"< {s['empirical_fpr_upper_bound_if_zero']:.2e}")
            lines.append(
                f"| {a} | {s['mean']:.4f} | {s['median']:.4f} | {s['stdev']:.4f} | "
                f"{s['min']:.4f} | {s['min_bits']} | {s['pairs_below_threshold']} | {fpr} |")
        lines += ["",
                  "Compare the first four columns against McKeown & Buchanan Table 3. "
                  "The last two columns are the contribution: the published work reports "
                  "the range but not the tail mass below the match threshold.", ""]

    if "error_correlation" in results:
        r = results["error_correlation"]
        lines += ["## RA-2 · Error correlation", "", "| pair | Pearson r |", "|---|---|"]
        for k, v in r["pearson"].items():
            lines.append(f"| {k} | {v:.3f} |")
        lines += ["", "| conditioning | observed | expected if independent | lift |", "|---|---|---|---|"]
        for k, v in r["joint_low_tail"].items():
            lines.append(f"| {k} | {v['observed']} | {v['expected_if_independent']} | "
                         f"{v['lift'] if v['lift'] is not None else 'n/a'} |")
        lines += ["",
                  "Lift > 1 means the algorithms produce near-collisions on the same pairs, "
                  "i.e. fusion buys less than independence would imply. Our fusion model "
                  "assumes rho ≈ 0.7; this measures it.", ""]

    if "dihedral" in results:
        r = results["dihedral"]
        rec, fp = r["recall_vs_mirror"], r["false_positives"]
        lines += ["## RA-3 · Dihedral cost", "",
                  f"- recall against a mirrored image — plain PDQ: **{rec['plain_pdq']:.1%}**, "
                  f"dihedral: **{rec['dihedral_pdq']:.1%}**",
                  f"- false positives over {fp['trials']:,} trials — single: {fp['single_hash']}, "
                  f"dihedral: {fp['dihedral_8']}",
                  f"- measured multiplier: **{fp['multiplier'] if fp['multiplier'] else 'unresolved at this sample size'}** "
                  f"(naive assumption: {fp['naive_assumption']})", ""]

    if "intra_image" in results:
        r = results["intra_image"]
        algos = list(next(iter(r["transforms"].values())).keys())
        lines += ["## Intra-image robustness", "",
                  f"{r['images_used']:,} images. Cell shows recall at the match threshold.", "",
                  "| transform | " + " | ".join(algos) + " |",
                  "|---" * (len(algos) + 1) + "|"]
        for t, per in r["transforms"].items():
            row = [f"{per[a]['recall_at_threshold']:.1%}" for a in algos]
            lines.append(f"| {t} | " + " | ".join(row) + " |")
        lines += ["",
                  "`mirror_x` near 0% for every non-dihedral algorithm is the expected result "
                  "and the reason RA-3 exists. `laundering_chain` is the realistic case and "
                  "the one to report.", ""]

    if "residual_paired" in results:
        r = results["residual_paired"]
        algos = list(next(iter(r["families"].values()))["per_algorithm"].keys())
        lines += ["## Residual population under routine transformations", "",
                  f"{r['images_used']:,} images × 4 intensities per family. Residual = share of "
                  f"transformed images NOT matched to their own original at the match threshold "
                  f"(bits: {r['threshold_bits']}). Wilson 95% intervals. "
                  f"{r['images_below_pdq_quality_floor']:,} images sit below Meta's PDQ quality "
                  f"floor and were kept (robustness asks whether the same image survives an edit).", "",
                  "| family | " + " | ".join(algos) + " |",
                  "|---" * (len(algos) + 1) + "|"]
        for fam, e in r["families"].items():
            cells = [f"{e['per_algorithm'][a]['residual']:.1%} "
                     f"({e['per_algorithm'][a]['ci_low']:.1%}–{e['per_algorithm'][a]['ci_high']:.1%})"
                     for a in algos]
            lines.append(f"| {fam} | " + " | ".join(cells) + " |")
        lines += ["", "Paired comparisons. McNemar on identical image–transformation pairs; "
                  "bootstrap resampled by image; difference is residual(B) − residual(A) in "
                  "percentage points, positive = B misses more.", "",
                  "| family | pair A~B | diff (pp) | bootstrap 95% CI (pp) | McNemar | p |",
                  "|---|---|---|---|---|---|"]
        for fam, e in r["families"].items():
            for pair, pw in e["pairwise"].items():
                m, b = pw["mcnemar"], pw["bootstrap"]
                stat = f"χ²={m['chi2']:.1f}" if m["chi2"] is not None else m["method"]
                lines.append(f"| {fam} | {pair} | {100 * b['diff_b_minus_a']:+.2f} | "
                             f"{100 * b['ci_low']:+.2f} … {100 * b['ci_high']:+.2f} | {stat} | "
                             f"{m['p_value']:.3g} |")
        if r["sample_size"]:
            lines += ["", "Images per condition needed to detect a reduction from the first "
                      "algorithm's residual rate (α=0.05, power 0.80, two-proportion normal "
                      "approximation; conservative for a paired design):", "",
                      "| family | baseline residual | 5 pp | 10 pp | 15 pp | 20 pp | 30 pp |",
                      "|---|---|---|---|---|---|---|"]
            for fam, ss in r["sample_size"].items():
                by = {row["min_detectable_effect"]: row["required_n_per_condition"] for row in ss["table"]}
                cells = [str(by.get(e, "—")) for e in (0.05, 0.10, 0.15, 0.20, 0.30)]
                lines.append(f"| {fam} | {ss['baseline_residual']:.1%} | " + " | ".join(cells) + " |")
        lines += ["", "⚠️ If the corpus is procedurally generated (`research/make_synthetic_corpus.py`) "
                  "these rates describe shapes on gradients, not photographs. Do not cite them; "
                  "rerun the same command on a benign photographic corpus.", ""]

    lines += ["---", "",
              "Reproduce: `python research/run.py --corpus <dir> --all --i-confirm-benign-corpus`",
              "", "Raw numbers in the accompanying JSON."]
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--corpus", required=True, type=Path,
                   help="directory of ordinary images, OUTSIDE this repository")
    p.add_argument("--i-confirm-benign-corpus", action="store_true",
                   help="affirm the corpus contains no abuse material and no case data")
    p.add_argument("--limit", type=int, default=5000, help="max images to load")
    p.add_argument("--comparisons", type=int, default=50, help="random pairs per image")
    p.add_argument("--algorithms", default="pdq,phash,blockhash")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--inter", action="store_true", help="RA-1")
    p.add_argument("--correlation", action="store_true", help="RA-2 (implies --inter)")
    p.add_argument("--dihedral", action="store_true", help="RA-3")
    p.add_argument("--intra", action="store_true", help="transformation robustness")
    p.add_argument("--routine", action="store_true",
                   help="residual population under 7 routine transformations × 4 intensities, "
                        "with paired statistics (not included in --all; it is the slow one)")
    p.add_argument("--boot", type=int, default=2000, help="bootstrap replicates for --routine")
    p.add_argument("--all", action="store_true")
    p.add_argument("--mckeown-only", action="store_true",
                   help="use only the seven transforms from arXiv:2212.08035")
    p.add_argument("--out", type=Path, default=RESULTS)
    args = p.parse_args()

    guard_corpus(args.corpus, args.i_confirm_benign_corpus)

    if args.all:
        args.inter = args.correlation = args.dihedral = args.intra = True
    if args.correlation:
        args.inter = True
    if not any([args.inter, args.dihedral, args.intra, args.routine]):
        raise SystemExit("Nothing to do. Pass --all, or one of --inter/--dihedral/--intra/--routine.")

    algorithms = [a.strip() for a in args.algorithms.split(",") if a.strip()]
    started = time.time()

    print(f"Loading corpus from {args.corpus} …")
    corpus = X.Corpus.load(args.corpus, limit=args.limit, seed=args.seed)
    print(f"  {len(corpus):,} images\n")

    results = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "corpus": str(args.corpus),
        "corpus_size": len(corpus),
        "seed": args.seed,
        "algorithms": algorithms,
    }

    if args.inter:
        print("RA-1 · inter-image distribution")
        inter = X.inter_image(corpus, algorithms, args.comparisons, progress("hashing"))
        print()
        if args.correlation:
            print("RA-2 · error correlation")
            results["error_correlation"] = X.error_correlation(inter, algorithms)
        inter.pop("_pair_distances", None)
        results["inter_image"] = inter

    if args.dihedral:
        print("RA-3 · dihedral cost")
        results["dihedral"] = X.dihedral_cost(corpus, sample=min(600, len(corpus)))

    if args.intra:
        print("Intra-image robustness")
        names = T.MCKEOWN_SUBSET if args.mckeown_only else list(T.TRANSFORMS)
        results["intra_image"] = X.intra_image(corpus, algorithms, names,
                                               sample=min(400, len(corpus)),
                                               progress=progress("transforms"))
        print()

    if args.routine:
        print("Residual population · routine transformations, paired")
        results["residual_paired"] = X.residual_paired(
            corpus, algorithms, sample=args.limit, n_boot=args.boot, progress=progress("routine"))
        print()

    results["elapsed_seconds"] = round(time.time() - started, 1)

    args.out.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    (args.out / f"results-{stamp}.json").write_text(json.dumps(results, indent=2, default=str))
    summary = summarise(results)
    (args.out / f"summary-{stamp}.md").write_text(summary)

    print(f"\n{'─' * 70}\n")
    print(summary)
    print(f"\nWritten to {args.out}/")


if __name__ == "__main__":
    main()
