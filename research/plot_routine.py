#!/usr/bin/env python3
"""
Render a --routine results file as a paper figure (SVG) and as paste-ready
Markdown tables in the shape of the resubmission draft's Table 1 and Table 2.

    python research/plot_routine.py research/results/results-<stamp>.json \
        --corpus-label "COCO val2017" \
        --svg paper/figures-en/paper-fig13-routine-residual.svg \
        --md  paper/data/routine-tables.md

No images are read. The input is aggregate statistics only (rates, intervals,
test statistics); nothing in it can reconstruct a photograph. Style and helpers
come from dossier/analysis/make_figures.py so the figure matches the others.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dossier" / "analysis"))
from make_figures import svg, text, title_block, esc  # noqa: E402

FAMILY_LABEL = {
    "blur": "Blur",
    "brightness": "Brightness",
    "center_crop": "Center crop",
    "gaussian_noise": "Gaussian noise",
    "jpeg": "JPEG compression",
    "resize_roundtrip": "Resize round-trip",
    "rotation": "Rotation",
}
FAMILY_LEVELS = {
    "blur": "r 0.5/1/2/3.5", "brightness": "±10/±25", "center_crop": "95/85/70/50 % area",
    "gaussian_noise": "σ 5/10/20/35", "jpeg": "q 90/70/50/30",
    "resize_roundtrip": "×0.8/0.5/0.3/0.15", "rotation": "2/5/10/15°",
}
ALGO_LABEL = {"pdq": "PDQ (Meta, 256 bit)", "phash": "pHash (64 bit)", "blockhash": "Blockhash (256 bit)"}
ALGO_CLASS = {"pdq": "accf", "phash": "alert", "blockhash": "ink3"}   # fill classes from make_figures STYLE
ALGO_STROKE = {"pdq": "accs", "phash": "alerts", "blockhash": "ink3s"}  # stroke classes, same palette


def load(path: pathlib.Path) -> dict:
    d = json.loads(path.read_text())
    r = d.get("residual_paired")
    if not r:
        raise SystemExit("no residual_paired section in this results file; run with --routine")
    r["_corpus"] = d.get("corpus", "?")
    r["_generated"] = d.get("generated", "?")
    return r


def families_in_draft_order(r: dict) -> list[str]:
    return [f for f in ("blur", "brightness", "center_crop", "gaussian_noise", "jpeg",
                        "resize_roundtrip", "rotation") if f in r["families"]]


# ── figure ───────────────────────────────────────────────────────────────────

def figure(r: dict, corpus_label: str) -> str:
    fams = families_in_draft_order(r)
    algos = [a for a in ("pdq", "phash", "blockhash") if a in next(iter(r["families"].values()))["per_algorithm"]]
    W, H = 940, 500
    left, right, top, bottom = 70, 30, 104, 110
    plot_w, plot_h = W - left - right, H - top - bottom
    group_w = plot_w / len(fams)
    bar_w = min(26, (group_w - 24) / len(algos))
    body = []

    n_img = r["images_used"]
    body.append(title_block(24, 34, "Residual evasion rate under routine transformations, by hash",
                            f"{corpus_label} · n = {n_img:,} images per condition · 4 intensities per family"))
    body.append(text(24, 70, f"Match threshold {r['threshold_bits'].get('pdq', 31)}/256 bits (Meta's PDQ default), "
                     "scaled to the same normalised distance for the others · whiskers are Wilson 95 % intervals",
                     "ink3", 11.5))

    # y axis
    for pct in (0, 25, 50, 75, 100):
        y = top + plot_h - plot_h * pct / 100
        body.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" class="rule" stroke-width="1"/>')
        body.append(text(left - 8, y + 4, f"{pct} %", "ink3", 11, anchor="end"))
    body.append(text(20, top - 10, "share of edited images NOT matched to their original", "ink3", 11))

    for i, fam in enumerate(fams):
        gx = left + i * group_w
        e = r["families"][fam]
        x0 = gx + (group_w - bar_w * len(algos)) / 2
        for j, a in enumerate(algos):
            s = e["per_algorithm"][a]
            x = x0 + j * bar_w
            h = plot_h * s["residual"]
            y = top + plot_h - h
            body.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w - 3:.1f}" height="{max(h, 1.2):.1f}" class="{ALGO_CLASS[a]}" rx="2"/>')
            # Wilson interval whisker
            ylo = top + plot_h - plot_h * s["ci_high"]
            yhi = top + plot_h - plot_h * s["ci_low"]
            cx = x + (bar_w - 3) / 2
            body.append(f'<line x1="{cx:.1f}" y1="{ylo:.1f}" x2="{cx:.1f}" y2="{yhi:.1f}" class="ink3s" stroke-width="1.2"/>')
            label = f"{100 * s['residual']:.1f}" if s["residual"] >= 0.0005 else "0.0"
            body.append(text(cx, min(y, ylo) - 5, label, "ink2", 9.5, anchor="middle"))
        body.append(text(gx + group_w / 2, top + plot_h + 18, FAMILY_LABEL[fam], "ink", 12, anchor="middle", weight="600"))
        body.append(text(gx + group_w / 2, top + plot_h + 33, FAMILY_LEVELS[fam], "ink3", 10, anchor="middle", mono=True))

    # legend, then the provenance line on its own row
    lx = left
    ly = H - 40
    for a in algos:
        body.append(f'<rect x="{lx}" y="{ly - 10}" width="12" height="12" class="{ALGO_CLASS[a]}" rx="2"/>')
        body.append(text(lx + 17, ly, ALGO_LABEL[a], "ink2", 11))
        lx += 190
    body.append(text(left, H - 16, f"research/run.py --routine · {r['_generated'][:10]} · every hash is scored on the same edited image, "
                     "so comparisons between hashes are paired", "ink3", 10, mono=True))
    return svg(W, H, "\n".join(body), "Residual evasion rate under routine transformations, by hash")


def figure_levels(r: dict, corpus_label: str) -> str:
    """Residual rate per intensity level for the two families that matter (crop, rotation), all hashes."""
    fams = [f for f in ("center_crop", "rotation") if f in r["families"]]
    algos = [a for a in ("pdq", "phash", "blockhash") if a in next(iter(r["families"].values()))["per_algorithm"]]
    W, H = 940, 470
    left, right, top, bottom = 120, 30, 110, 150
    plot_w, plot_h = W - left - right, H - top - bottom
    gap = 70
    panel_w = (plot_w - gap) / len(fams)
    body = [title_block(24, 34, "Where the matching breaks: residual rate by intensity",
                        f"{corpus_label} · n = {r['images_used']:,} images per level · the two geometric families; the other five stay at or near 0 % at every level")]
    body.append(text(24, 70, "Same thresholds as Figure 1 · a point is the share of images whose edited copy no longer matches its original · values in the rows below each axis", "ink3", 11.5))
    for pct in (0, 25, 50, 75, 100):
        y = top + plot_h - plot_h * pct / 100
        body.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" class="rule" stroke-width="1"/>')
        body.append(text(left - 8, y + 4, f"{pct} %", "ink3", 11, anchor="end"))
    body.append(text(left, top - 14, "share of edited images NOT matched to their original", "ink3", 11))
    for i, fam in enumerate(fams):
        px0 = left + i * (panel_w + gap)
        e = r["families"][fam]
        levels = e["levels"]
        n = len(levels)
        xs = [px0 + panel_w * (k + 0.5) / n for k in range(n)]
        for k, lv in enumerate(levels):
            lab = lv.split(":")[1]
            lab = f"{round(float(lab) * 100)} % area" if fam == "center_crop" else f"{lab}°"
            body.append(text(xs[k], top + plot_h + 18, lab, "ink", 11.5, anchor="middle", weight="600"))
        body.append(text(px0 + panel_w / 2, top + plot_h + 96, FAMILY_LABEL[fam], "ink3", 11, anchor="middle", weight="600"))
        for j, a in enumerate(algos):
            pl = e["per_algorithm"][a]["per_level"]
            pts = [(xs[k], top + plot_h - plot_h * pl[lv]) for k, lv in enumerate(levels)]
            d = " ".join(f"{'M' if k == 0 else 'L'}{x:.1f},{y:.1f}" for k, (x, y) in enumerate(pts))
            body.append(f'<path d="{d}" class="{ALGO_STROKE[a]}" fill="none" stroke-width="2.4"/>')
            for (x, y) in pts:
                body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.2" class="{ALGO_CLASS[a]}"/>')
            ry = top + plot_h + 40 + j * 16
            if i == 0:
                body.append(f'<rect x="{left - 100}" y="{ry - 9}" width="10" height="10" class="{ALGO_CLASS[a]}" rx="2"/>')
                body.append(text(left - 86, ry, {"pdq": "PDQ", "phash": "pHash", "blockhash": "Blockhash"}[a], "ink2", 10.5))
            for k, lv in enumerate(levels):
                v = pl[lv]
                body.append(text(xs[k], ry, f"{100 * v:.1f} %" if v >= 0.0005 else "0.0 %", "ink2", 10.5, anchor="middle", mono=True))
    body.append(text(left, H - 14, f"research/run.py --routine · {r['_generated'][:10]} · per-level rates from the same paired run as Figure 1 · percentages are of {r['images_used']:,} images", "ink3", 10, mono=True))
    return svg(W, H, "\n".join(body), "Residual rate by intensity for center crop and rotation, by hash")


# ── tables ───────────────────────────────────────────────────────────────────

def pct(v: float) -> str:
    return f"{100 * v:.1f}%" if v >= 0.0005 else "0.0%"


def tables(r: dict, corpus_label: str, pair: str) -> str:
    fams = families_in_draft_order(r)
    algos = [a for a in ("pdq", "phash", "blockhash") if a in next(iter(r["families"].values()))["per_algorithm"]]
    n_img = r["images_used"]
    pairs_per_cell = n_img * 4
    out = []
    out.append(f"**Table 1. Residual evasion rate by hash and transformation family** "
               f"({corpus_label}; n = {n_img:,} images per condition, {pairs_per_cell:,} image–intensity pairs per cell; Wilson 95 % CI).")
    out.append("")
    out.append("| Transformation | " + " | ".join(ALGO_LABEL[a] for a in algos) + " |")
    out.append("|---|" + "---|" * len(algos))
    for fam in fams:
        e = r["families"][fam]
        cells = []
        for a in algos:
            s = e["per_algorithm"][a]
            cells.append(f"{pct(s['residual'])} ({pct(s['ci_low'])}–{pct(s['ci_high'])})")
        out.append(f"| {FAMILY_LABEL[fam]} | " + " | ".join(cells) + " |")
    out.append("")

    a, b = pair.split("~")
    out.append(f"**Table 2. Paired comparison, {ALGO_LABEL[a]} vs. {ALGO_LABEL[b]}** "
               f"(McNemar with continuity correction on identical image–transformation pairs; "
               f"difference = residual({b}) − residual({a}); bootstrap resampled by image, {r['n_boot']:,} replicates).")
    out.append("")
    out.append("| Transformation | Residual diff. (pp) | Bootstrap 95 % CI (pp) | McNemar χ² | p |")
    out.append("|---|---|---|---|---|")
    for fam in fams:
        pw = r["families"][fam]["pairwise"].get(pair)
        if not pw:
            continue
        m, bs = pw["mcnemar"], pw["bootstrap"]
        chi = f"{m['chi2']:,.1f}" if m["chi2"] is not None else m["method"]
        p = "<0.001" if m["p_value"] < 0.001 else f"{m['p_value']:.3f}"
        out.append(f"| {FAMILY_LABEL[fam]} | {100 * bs['diff_b_minus_a']:+.1f} | "
                   f"{100 * bs['ci_low']:+.1f} … {100 * bs['ci_high']:+.1f} | {chi} | {p} |")
    out.append("")
    if r.get("sample_size"):
        out.append("**Table 3. Images per condition required to detect a given reduction in residual rate** "
                   "(α = 0.05, power 0.80, two-proportion normal approximation; conservative for a paired design).")
        out.append("")
        out.append("| Transformation | Baseline residual (PDQ) | 5 pp | 10 pp | 15 pp | 20 pp | 30 pp |")
        out.append("|---|---|---|---|---|---|---|")
        for fam in fams:
            ss = r["sample_size"].get(fam)
            if not ss:
                continue
            by = {row["min_detectable_effect"]: row["required_n_per_condition"] for row in ss["table"]}
            cells = [f"{by[e]:,}" if e in by else "—" for e in (0.05, 0.10, 0.15, 0.20, 0.30)]
            out.append(f"| {FAMILY_LABEL[fam]} | {pct(ss['baseline_residual'])} | " + " | ".join(cells) + " |")
        out.append("")
    out.append(f"Corpus: `{r['_corpus']}` · {r['images_below_pdq_quality_floor']:,} of {n_img:,} images below Meta's PDQ quality floor (kept: robustness asks whether the same image survives an edit) · generated {r['_generated']} by `research/run.py --routine`.")
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("results", type=pathlib.Path)
    ap.add_argument("--corpus-label", default="benign photographic corpus")
    ap.add_argument("--svg", type=pathlib.Path, help="write the figure here")
    ap.add_argument("--md", type=pathlib.Path, help="write the tables here (default: stdout)")
    ap.add_argument("--svg-levels", type=pathlib.Path, help="write the per-intensity figure (crop and rotation) here")
    ap.add_argument("--pair", default="pdq~blockhash", help="pair for Table 2, e.g. pdq~phash")
    args = ap.parse_args()

    r = load(args.results)
    if args.svg:
        args.svg.parent.mkdir(parents=True, exist_ok=True)
        args.svg.write_text(figure(r, args.corpus_label))
        print(f"✔ figure → {args.svg}")
    if args.svg_levels:
        args.svg_levels.parent.mkdir(parents=True, exist_ok=True)
        args.svg_levels.write_text(figure_levels(r, args.corpus_label))
        print(f"✔ figure → {args.svg_levels}")
    md = tables(r, args.corpus_label, args.pair)
    if args.md:
        args.md.parent.mkdir(parents=True, exist_ok=True)
        args.md.write_text(md)
        print(f"✔ tables → {args.md}")
    else:
        print(md)


if __name__ == "__main__":
    main()
