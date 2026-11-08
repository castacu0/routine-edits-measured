#!/usr/bin/env python3
"""
Build the arXiv preprint (v1) from its source manuscript and the figures.

1. regenerates every empirical figure and table from committed data
   (research/plot_routine.py on paper/data/routine-coco-val2017.json, and
   paper/plot_frontier.py on paper/data/frontier-models-2026.json);
2. replaces each <!--FIG:name.svg--> placeholder in paper/ARXIV_V1_DRAFT.src.html
   with the inlined SVG from paper/figures-en/;
3. writes paper/ARXIV_V1_DRAFT.html and prints it to paper/ARXIV_V1_DRAFT.pdf
   with headless Chrome (same pipeline as build_v13.py).

    python3 paper/build_arxiv.py            # everything
    python3 paper/build_arxiv.py --no-regen # skip step 1

No figure is edited by hand. If a number in the text disagrees with
paper/data/, the text is wrong.
"""

import argparse
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
REPO = ROOT.parent
FIGS = ROOT / "figures-en"
SRC = ROOT / "ARXIV_V1_DRAFT.src.html"
OUT_HTML = ROOT / "ARXIV_V1_DRAFT.html"
OUT_PDF = ROOT / "ARXIV_V1_DRAFT.pdf"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PY = REPO / ".venv-research" / "bin" / "python"


def regen() -> None:
    py = str(PY) if PY.exists() else sys.executable
    subprocess.run([py, str(REPO / "research" / "plot_routine.py"),
                    str(ROOT / "data" / "routine-coco-val2017.json"),
                    "--corpus-label", "COCO val2017",
                    "--svg", str(FIGS / "paper-fig13-routine-residual.svg"),
                    "--svg-levels", str(FIGS / "paper-fig14-routine-by-intensity.svg"),
                    "--md", str(ROOT / "data" / "routine-coco-val2017.md")], check=True)
    subprocess.run([py, str(ROOT / "plot_frontier.py"),
                    "--svg", str(FIGS / "paper-fig15-frontier-timeline.svg"),
                    "--md", str(ROOT / "data" / "frontier-models-2026.md")], check=True)


# ── tables generated from committed data ─────────────────────────────────────

import json  # noqa: E402

FAMILY_LABEL = {"blur": "Blur", "brightness": "Brightness", "center_crop": "Center crop",
                "gaussian_noise": "Gaussian noise", "jpeg": "JPEG compression",
                "resize_roundtrip": "Resize round-trip", "rotation": "Rotation"}
FAMILY_LEVELS = {"blur": "radius 0.5 / 1 / 2 / 3.5", "brightness": "+10 / −10 / +25 / −25",
                 "center_crop": "keep 95 / 85 / 70 / 50 % of area", "gaussian_noise": "σ 5 / 10 / 20 / 35",
                 "jpeg": "quality 90 / 70 / 50 / 30", "resize_roundtrip": "×0.8 / 0.5 / 0.3 / 0.15 and back",
                 "rotation": "2° / 5° / 10° / 15°"}
ALGO_LABEL = {"pdq": "PDQ (Meta, 256 bit)", "phash": "pHash (64 bit)", "blockhash": "Blockhash-GM (256 bit)"}
ORDER = ("blur", "brightness", "center_crop", "gaussian_noise", "jpeg", "resize_roundtrip", "rotation")


def pct(v: float) -> str:
    return f"{100 * v:.1f}%" if v >= 0.0005 else "0.0%"


def load_routine() -> dict:
    d = json.loads((ROOT / "data" / "routine-coco-val2017.json").read_text())
    return d["residual_paired"]


def table_residual(r: dict) -> str:
    algos = [a for a in ("pdq", "phash", "blockhash") if a in r["families"]["blur"]["per_algorithm"]]
    h = "<tr><th>Transformation family</th><th>Intensities</th>" + "".join(f"<th>{ALGO_LABEL[a]}</th>" for a in algos) + "</tr>"
    rows = []
    for fam in ORDER:
        e = r["families"][fam]
        cells = "".join(f'<td class="c">{pct(e["per_algorithm"][a]["residual"])}<br><span class="small">({pct(e["per_algorithm"][a]["ci_low"])} to {pct(e["per_algorithm"][a]["ci_high"])})</span></td>' for a in algos)
        rows.append(f"<tr><td>{FAMILY_LABEL[fam]}</td><td class=\"small\">{FAMILY_LEVELS[fam]}</td>{cells}</tr>")
    return f"<table>{h}{''.join(rows)}</table>"


def table_pairwise(r: dict) -> str:
    pairs = [("pdq~phash", "PDQ vs. pHash"), ("pdq~blockhash", "PDQ vs. Blockhash-GM"), ("phash~blockhash", "pHash vs. Blockhash-GM")]
    h = "<tr><th>Family</th><th>Pair (A vs. B)</th><th>Residual B − A (pp)</th><th>Bootstrap 95% CI (pp)</th><th>Discordant pairs (A only / B only)</th><th>McNemar χ²</th><th>p</th></tr>"
    rows = []
    for fam in ("center_crop", "rotation", "jpeg", "brightness", "gaussian_noise", "resize_roundtrip", "blur"):
        for key, lab in pairs:
            if fam not in ("center_crop", "rotation") and key != "pdq~blockhash":
                continue
            pw = r["families"][fam]["pairwise"][key]
            m, b = pw["mcnemar"], pw["bootstrap"]
            chi = f"{m['chi2']:,.1f}" if m["chi2"] is not None else "exact binomial"
            pv = "&lt;0.001" if m["p_value"] < 0.001 else f"{m['p_value']:.3f}"
            rows.append(f"<tr><td>{FAMILY_LABEL[fam]}</td><td>{lab}</td><td class=\"c\">{100 * b['diff_b_minus_a']:+.1f}</td>"
                        f"<td class=\"c\">{100 * b['ci_low']:+.1f} to {100 * b['ci_high']:+.1f}</td><td class=\"c\">{m['discordant']:,} ({m['a_only']:,} / {m['b_only']:,})</td>"
                        f"<td class=\"c\">{chi}</td><td class=\"c\">{pv}</td></tr>")
    return f"<table class=\"long\"><thead>{h}</thead><tbody>{''.join(rows)}</tbody></table>"


def table_samplesize(r: dict) -> str:
    h = "<tr><th>Family</th><th>Baseline residual (PDQ)</th><th>5 pp</th><th>10 pp</th><th>15 pp</th><th>20 pp</th><th>30 pp</th></tr>"
    rows = []
    for fam, ss in r["sample_size"].items():
        by = {row["min_detectable_effect"]: row["required_n_per_condition"] for row in ss["table"]}
        cells = "".join(f'<td class="c">{by[e]:,}</td>' for e in (0.05, 0.10, 0.15, 0.20, 0.30))
        rows.append(f"<tr><td>{FAMILY_LABEL[fam]}</td><td class=\"c\">{pct(ss['baseline_residual'])}</td>{cells}</tr>")
    return f"<table>{h}{''.join(rows)}</table>"


def table_perlevel(r: dict) -> str:
    algos = [a for a in ("pdq", "phash", "blockhash") if a in r["families"]["blur"]["per_algorithm"]]
    h = "<tr><th>Family</th><th>Level</th>" + "".join(f"<th>{ALGO_LABEL[a]}</th>" for a in algos) + "</tr>"
    rows = []
    for fam in ORDER:
        e = r["families"][fam]
        for lv in e["levels"]:
            cells = "".join(f'<td class="c">{pct(e["per_algorithm"][a]["per_level"][lv])}</td>' for a in algos)
            rows.append(f"<tr><td>{FAMILY_LABEL[fam]}</td><td class=\"small\">{lv.split(':')[1]}</td>{cells}</tr>")
    return f"<table class=\"long\"><thead>{h}</thead><tbody>{''.join(rows)}</tbody></table>"


def table_frontier() -> str:
    d = json.loads((ROOT / "data" / "frontier-models-2026.json").read_text())
    h = "<tr><th>Date</th><th>Developer</th><th>Model</th><th>Kind</th><th>Access</th><th>Licence</th></tr>"
    rows = []
    for e in sorted(d["events"], key=lambda e: e["date"]):
        if e["date"] < "2026-07-20":
            continue
        cls = ' class="win"' if e.get("window") else ""
        rows.append(f"<tr{cls}><td class=\"small\">{e['date']}</td><td>{e['org']} ({e['country']})</td><td>{e['name']}</td><td>{e['kind']}</td><td>{e['access']}</td><td class=\"small\">{e['license']}</td></tr>")
    return f"<table class=\"long\"><thead>{h}</thead><tbody>{''.join(rows)}</tbody></table>"


def inline_tables(html: str) -> str:
    r = load_routine()
    gen = {"residual": table_residual(r), "pairwise": table_pairwise(r), "samplesize": table_samplesize(r),
           "perlevel": table_perlevel(r), "frontier": table_frontier()}
    return re.sub(r"<!--TABLE:(\w+)-->", lambda m: gen[m.group(1)], html)


def check_numbers(html: str) -> None:
    """Every headline number in the prose must be derivable from the JSON. Fails loudly otherwise."""
    r = load_routine()
    f = r["families"]
    must = [pct(f["center_crop"]["per_algorithm"]["pdq"]["residual"]), pct(f["rotation"]["per_algorithm"]["pdq"]["residual"]),
            pct(f["center_crop"]["per_algorithm"]["phash"]["residual"]), pct(f["rotation"]["per_algorithm"]["phash"]["residual"]),
            pct(f["center_crop"]["per_algorithm"]["blockhash"]["residual"]), pct(f["rotation"]["per_algorithm"]["blockhash"]["residual"]),
            f"{r['images_used']:,}", str(r["images_below_pdq_quality_floor"]),
            f"{100 * f['center_crop']['per_algorithm']['pdq']['per_level']['center_crop:0.95']:.1f}",
            f"{100 * f['rotation']['per_algorithm']['pdq']['per_level']['rotation:2']:.1f}",
            f"{f['center_crop']['pairwise']['pdq~blockhash']['mcnemar']['chi2']:,.0f}",
            f"{f['rotation']['pairwise']['pdq~blockhash']['mcnemar']['chi2']:,.0f}"]
    missing = [m for m in must if m.replace("%", "") not in html]
    if missing:
        sys.exit(f"numbers in the manuscript do not match paper/data: {missing}")


def inline_figures(html: str) -> str:
    def repl(m):
        path = FIGS / m.group(1)
        if not path.exists():
            sys.exit(f"missing figure: {path}")
        return f'<div class="fig">{path.read_text()}</div>'
    return re.sub(r"<!--FIG:([\w.\-]+)-->", repl, html)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-regen", action="store_true")
    a = ap.parse_args()
    if not a.no_regen:
        regen()
    html = inline_tables(inline_figures(SRC.read_text()))
    check_numbers(html)
    if "—" in html:
        sys.exit("em-dash found in the manuscript; the repository style forbids it")
    OUT_HTML.write_text(html)
    print(f"wrote {OUT_HTML.name} ({OUT_HTML.stat().st_size // 1024} KB)")
    if not pathlib.Path(CHROME).exists():
        sys.exit(f"Chrome not found at {CHROME}; open {OUT_HTML.name} and print to PDF manually")
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    "--run-all-compositor-stages-before-draw", "--virtual-time-budget=8000",
                    f"--print-to-pdf={OUT_PDF}", f"file://{OUT_HTML}"], check=True, capture_output=True)
    print(f"wrote {OUT_PDF.name} ({OUT_PDF.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
