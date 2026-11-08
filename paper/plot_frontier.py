#!/usr/bin/env python3
"""
Render paper/data/frontier-models-2026.json as the preprint's Figure 3 (a dated
timeline of image and video model releases, open weights versus hosted) and as
a Markdown table for the manuscript.

    python3 paper/plot_frontier.py --svg paper/figures-en/paper-fig15-frontier-timeline.svg --md paper/data/frontier-models-2026.md

No number in the figure is typed by hand: every mark is a row of the JSON, and
every row carries the primary source it was checked against and the date it was
checked. Style helpers come from dossier/analysis/make_figures.py so the figure
matches the rest of the paper.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dossier" / "analysis"))
from make_figures import svg, text, title_block  # noqa: E402

DATA = ROOT / "paper" / "data" / "frontier-models-2026.json"

COUNTRY_LABEL = {"US": "United States", "CN": "China", "DE": "Germany", "FR": "France", "n/a": "community"}


def load() -> dict:
    return json.loads(DATA.read_text())


def _d(s: str) -> dt.date:
    return dt.date.fromisoformat(s)


def figure(d: dict) -> str:
    ev = sorted((e for e in d["events"] if _d(e["date"]) >= dt.date(2026, 7, 20)), key=lambda e: e["date"])
    t0, t1 = dt.date(2026, 7, 20), dt.date(2026, 11, 12)
    row_h = 19
    W = 940
    label_w = 385
    left, right, top = 24, 30, 112
    ax0 = left + label_w
    ax1 = W - right
    H = top + row_h * len(ev) + 86
    body = [title_block(24, 34, "Image and video generators, July to November 2026: what shipped, and whether the weights did",
                        "One row per dated release, checked against its model card or announcement · filled = open weights, hollow = hosted only")]
    body.append(text(24, 70, f"Shaded band: the two weeks the preprint discusses ({d['window_start']} to {d['window_end']}) · colour: China, United States, Europe", "ink3", 11.5))

    def x_of(day: dt.date) -> float:
        return ax0 + (ax1 - ax0) * (day - t0).days / (t1 - t0).days

    wx0, wx1 = x_of(_d(d["window_start"])), x_of(_d(d["window_end"]))
    body.append(f'<rect x="{wx0:.1f}" y="{top - 12}" width="{wx1 - wx0:.1f}" height="{row_h * len(ev) + 12}" class="softf"/>')
    for m in (8, 9, 10, 11):
        day = dt.date(2026, m, 1)
        x = x_of(day)
        body.append(f'<line x1="{x:.1f}" y1="{top - 12}" x2="{x:.1f}" y2="{top + row_h * len(ev)}" class="rule" stroke-width="1"/>')
        body.append(text(x + 4, top - 16, day.strftime("%b 2026"), "ink3", 10.5))
    body.append(text(left, top - 16, "date · developer · model", "ink3", 10.5))
    stroke_of = {"CN": "alerts", "US": "accs", "DE": "ink3s", "FR": "ink3s", "n/a": "ink3s"}
    for i, e in enumerate(ev):
        y = top + i * row_h + row_h / 2
        body.append(f'<line x1="{left}" y1="{y + row_h / 2:.1f}" x2="{ax1}" y2="{y + row_h / 2:.1f}" class="rule" stroke-width="0.5"/>')
        short = e["name"].split(" (")[0]
        org = e["org"].split(" (")[0]
        body.append(text(left, y + 4, f"{e['date'][5:]}  {org}: {short}", "ink", 10.2, weight="600" if e.get("window") else None))
        x = x_of(_d(e["date"]))
        fill = "accf" if e["access"] == "open weights" else "bg"
        if e["access"] == "open weights" and e["country"] == "CN":
            fill = "alert"
        if e["access"] == "open weights" and e["country"] not in ("CN", "US"):
            fill = "ink3"
        body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5.5" class="{fill} {stroke_of.get(e["country"], "ink3s")}" stroke-width="2"/>')
        tag = e["access"] if e["access"] != "open weights" else e["license"].split(" (")[0]
        if x > ax1 - 150:
            body.append(text(x - 10, y + 4, tag, "ink3", 9.6, anchor="end"))
        else:
            body.append(text(x + 10, y + 4, tag, "ink3", 9.6))
    ly = top + row_h * len(ev) + 28
    body.append(f'<circle cx="{left + 6}" cy="{ly}" r="5.5" class="alert alerts" stroke-width="2"/>')
    body.append(text(left + 18, ly + 4, "China, open weights", "ink2", 10.5))
    body.append(f'<circle cx="{left + 156}" cy="{ly}" r="5.5" class="accf accs" stroke-width="2"/>')
    body.append(text(left + 168, ly + 4, "United States, open weights", "ink2", 10.5))
    body.append(f'<circle cx="{left + 356}" cy="{ly}" r="5.5" class="ink3 ink3s" stroke-width="2"/>')
    body.append(text(left + 368, ly + 4, "Europe or community, open weights", "ink2", 10.5))
    body.append(f'<circle cx="{left + 596}" cy="{ly}" r="5.5" class="bg alerts" stroke-width="2"/>')
    body.append(text(left + 608, ly + 4, "hosted only (API or app)", "ink2", 10.5))
    body.append(text(left, H - 14, "paper/plot_frontier.py · sources and access dates per row in paper/data/frontier-models-2026.json · Hugging Face dates are repository creation dates", "ink3", 10, mono=True))
    return svg(W, H, "\n".join(body), "Image and video generator releases, July to November 2026, by region and openness")


def table(d: dict) -> str:
    out = ["| Date | Developer | Model | Kind | Access | Licence | Source |", "|---|---|---|---|---|---|---|"]
    for e in sorted(d["events"], key=lambda e: e["date"]):
        src = e["source"].split(" ; ")[0]
        out.append(f"| {e['date']} | {e['org']} ({e['country']}) | {e['name']} | {e['kind']} | {e['access']} | {e['license']} | {src} |")
    out.append("")
    out.append(f"Window discussed in the text: {d['window_start']} to {d['window_end']}. Every row checked on the `accessed` date recorded in the JSON.")
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--svg", type=pathlib.Path)
    ap.add_argument("--md", type=pathlib.Path)
    a = ap.parse_args()
    d = load()
    if a.svg:
        a.svg.write_text(figure(d))
        print(f"✔ figure → {a.svg}")
    md = table(d)
    if a.md:
        a.md.write_text(md)
        print(f"✔ table → {a.md}")
    else:
        print(md)


if __name__ == "__main__":
    main()
