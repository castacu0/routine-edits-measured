#!/usr/bin/env python3
"""
Violencia Digital · figure generator
====================================

Writes self-contained SVGs to docs/figures/. No plotting library: every figure
is emitted as raw SVG so the repository has no binary artefacts, the output is
diffable, and GitHub renders it inline in Markdown.

    python3 dossier/analysis/make_figures.py

Each figure carries an embedded stylesheet with a prefers-color-scheme block, so
it stays legible on GitHub's light and dark themes.

Every number here traces to dossier/analysis/detection_math.py or to a cited
source recorded in dossier/08_STATISTICS_DISCIPLINE.md. Nothing is illustrative.
"""

import math
import pathlib

OUT = pathlib.Path(__file__).resolve().parents[2] / "docs" / "figures"

STYLE = """
  <style>
    .bg   { fill: #FFFFFF; }
    .ink  { fill: #0E1A1D; }
    .ink2 { fill: #2F4046; }
    .ink3 { fill: #61757B; }
    .acc  { fill: #0A5F6E; }
    .alert{ fill: #96271B; }
    .rule { stroke: #C8D4D7; }
    .accs { stroke: #0A5F6E; }
    .alerts{ stroke: #96271B; }
    .ink3s{ stroke: #61757B; }
    .accf { fill: #0A5F6E; }
    .softf{ fill: #E4F1F3; }
    text  { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    .mono { font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; }
    .ttl  { font-family: Georgia, "Times New Roman", serif; font-weight: 700; }
    @media (prefers-color-scheme: dark) {
      .bg   { fill: #0B1215; }
      .ink  { fill: #E8EFF0; }
      .ink2 { fill: #A7BCC1; }
      .ink3 { fill: #72898F; }
      .acc  { fill: #45CFE3; }
      .alert{ fill: #FF8A75; }
      .rule { stroke: #22343A; }
      .accs { stroke: #45CFE3; }
      .alerts{ stroke: #FF8A75; }
      .ink3s{ stroke: #72898F; }
      .accf { fill: #45CFE3; }
      .softf{ fill: #12303A; }
    }
  </style>
"""


def svg(w, h, body, title):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}" role="img" aria-label="{title}">\n'
        f'  <title>{title}</title>\n{STYLE}\n'
        f'  <rect class="bg" width="{w}" height="{h}"/>\n{body}\n</svg>\n'
    )


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, cls="ink2", size=13, anchor="start", weight=None, mono=False):
    w = f' font-weight="{weight}"' if weight else ""
    c = f"{cls} mono" if mono else cls
    return (f'<text x="{x}" y="{y}" class="{c}" font-size="{size}" '
            f'text-anchor="{anchor}"{w}>{esc(s)}</text>')


def title_block(x, y, t, sub):
    return (text(x, y, t, "ink", 19, weight="700") + "\n"
            + text(x, y + 20, sub, "ink3", 11.5))


# ── F1 · the three models ────────────────────────────────────────────────────

def fig_fpr_models():
    W, H = 900, 400
    b = [title_block(40, 42, "PDQ false positive rate: three models of one number",
                     "Same quantity, three methods. The measured value is 10^24 larger than the Gaussian fit.")]
    rows = [
        ("Independent uniform bits", 8.28e-38, "textbook assumption", "ink3"),
        ("Gaussian fit to measured data", 1.86e-32, "uses real spread, wrong tail", "ink2"),
        ("Empirically observed floor", 2.00e-8, "what 50M comparisons showed", "alert"),
    ]
    x0, y0, bw, gap = 340, 110, 480, 62
    # log scale from 1e-40 to 1e-6
    lo, hi = -40.0, -6.0
    for i, (label, val, note, cls) in enumerate(rows):
        y = y0 + i * gap
        frac = (math.log10(val) - lo) / (hi - lo)
        w = max(3, bw * frac)
        b.append(text(x0 - 16, y + 13, label, "ink", 12.5, anchor="end", weight="600"))
        b.append(text(x0 - 16, y + 29, note, "ink3", 10.5, anchor="end"))
        b.append(f'<rect x="{x0}" y="{y}" width="{w:.1f}" height="22" '
                 f'class="{"alert" if cls == "alert" else "acc"}" '
                 f'opacity="{0.95 if cls == "alert" else 0.55}"/>')
        exp = int(math.floor(math.log10(val)))
        mant = val / (10 ** exp)
        b.append(text(x0 + w + 10, y + 16, f"{mant:.1f}e{exp}", cls, 12, mono=True))
    # axis
    ay = y0 + 3 * gap - 20
    b.append(f'<line x1="{x0}" y1="{ay}" x2="{x0 + bw}" y2="{ay}" class="rule" stroke-width="1"/>')
    for e in range(-40, -5, 5):
        fx = x0 + bw * (e - lo) / (hi - lo)
        b.append(f'<line x1="{fx:.1f}" y1="{ay}" x2="{fx:.1f}" y2="{ay + 5}" class="rule"/>')
        b.append(text(fx, ay + 20, f"1e{e}", "ink3", 10, anchor="middle", mono=True))
    b.append(text(x0 + bw / 2, ay + 42, "probability that two unrelated images fall within Hamming distance 31",
                  "ink3", 11, anchor="middle"))
    b.append(text(40, H - 22, "Source: McKeown & Buchanan, arXiv:2212.08035, Table 3 · "
                              "reproduce with dossier/analysis/detection_math.py", "ink3", 10, mono=True))
    return svg(W, H, "\n".join(b), "PDQ false positive rate under three models")


# ── F2 · precision vs prevalence ─────────────────────────────────────────────

def fig_precision():
    W, H = 900, 460
    b = [title_block(40, 42, "Precision collapses at low prevalence",
                     "Positive predictive value against base rate, at TPR = 0.90. Accuracy hides all of this.")]
    x0, y0, pw, ph = 90, 100, 700, 260
    b.append(f'<rect x="{x0}" y="{y0}" width="{pw}" height="{ph}" class="softf" opacity="0.35"/>')
    # axes
    for i in range(6):
        gy = y0 + ph - i * ph / 5
        b.append(f'<line x1="{x0}" y1="{gy:.1f}" x2="{x0 + pw}" y2="{gy:.1f}" class="rule"/>')
        b.append(text(x0 - 10, gy + 4, f"{i * 20}%", "ink3", 10.5, anchor="end", mono=True))
    prevs = [1e-2, 1e-3, 1e-4, 1e-5, 1e-6]
    for i, p in enumerate(prevs):
        gx = x0 + i * pw / (len(prevs) - 1)
        b.append(f'<line x1="{gx:.1f}" y1="{y0}" x2="{gx:.1f}" y2="{y0 + ph}" class="rule"/>')
        e = int(math.log10(p))
        b.append(text(gx, y0 + ph + 20, f"1e{e}", "ink3", 10.5, anchor="middle", mono=True))
    b.append(text(x0 + pw / 2, y0 + ph + 42, "prevalence: fraction of submissions that really are known matches",
                  "ink3", 11, anchor="middle"))

    TPR = 0.90
    series = [(1e-6, "FPR/query 1e-6", 0.30), (1e-5, "1e-5", 0.45),
              (1e-4, "1e-4", 0.65), (1e-3, "1e-3", 1.0)]
    # End labels bunch up near zero, so enforce a minimum vertical gap and
    # nudge each one down until it clears the previous label.
    placed = []
    MIN_GAP = 14
    for fpr, label, op in series:
        pts = []
        for i, prev in enumerate(prevs):
            ppv = (prev * TPR) / (prev * TPR + (1 - prev) * fpr)
            gx = x0 + i * pw / (len(prevs) - 1)
            gy = y0 + ph - ppv * ph
            pts.append(f"{gx:.1f},{gy:.1f}")
        strong = op == 1.0
        b.append(f'<polyline points="{" ".join(pts)}" fill="none" '
                 f'class="{"alerts" if strong else "accs"}" stroke-width="{2.4 if strong else 1.8}" '
                 f'opacity="{op}"/>')
        lastx, lasty = (float(v) for v in pts[-1].split(","))
        ly = lasty + 4
        while any(abs(ly - p) < MIN_GAP for p in placed):
            ly += MIN_GAP
        placed.append(ly)
        if abs(ly - (lasty + 4)) > 2:
            b.append(f'<line x1="{lastx + 4:.1f}" y1="{lasty:.1f}" x2="{lastx + 10:.1f}" '
                     f'y2="{ly - 4:.1f}" class="{"alerts" if strong else "accs"}" '
                     f'stroke-width="1" opacity="0.6"/>')
        b.append(text(lastx + 13, ly, label, "alert" if strong else "acc", 10.5, mono=True))

    # the operating point
    prev_op, fpr_op = 1e-4, 1e-3
    ppv_op = (prev_op * TPR) / (prev_op * TPR + (1 - prev_op) * fpr_op)
    gx = x0 + 2 * pw / (len(prevs) - 1)
    gy = y0 + ph - ppv_op * ph
    b.append(f'<circle cx="{gx:.1f}" cy="{gy:.1f}" r="5" class="alert"/>')
    b.append(text(gx + 12, gy - 10, "our likely operating point: 8.3% precision", "alert", 11.5, weight="600"))
    b.append(text(gx + 12, gy + 6, "twelve of every thirteen escalations are wrong", "ink2", 10.5))
    b.append(text(40, H - 20, "This single chart is why nothing auto-files and why trained review is the budget.",
                  "ink3", 10.5, mono=True))
    return svg(W, H, "\n".join(b), "Precision against prevalence")


# ── F3 · where the money goes ────────────────────────────────────────────────

def fig_cost():
    W, H = 960, 330
    b = [title_block(40, 42, "The budget is people, not compute",
                     "Annual cost by scenario. Infrastructure is the thin bar you cannot see at this scale.")]
    rows = [("Pilot · one Mexican state", 500, 2.0, 130_000),
            ("Mexico national", 20_000, 80.0, 5_200_000),
            ("LATAM regional", 100_000, 400.0, 26_000_000)]
    x0, y0, bw, gap = 290, 105, 350, 58
    mx = 26_000_000
    for i, (label, rpd, rev, cost) in enumerate(rows):
        y = y0 + i * gap
        w = bw * cost / mx
        b.append(text(x0 - 16, y + 14, label, "ink", 12.5, anchor="end", weight="600"))
        b.append(text(x0 - 16, y + 30, f"{rpd:,} reports/day", "ink3", 10.5, anchor="end"))
        b.append(f'<rect x="{x0}" y="{y}" width="{w:.1f}" height="24" class="acc" opacity="0.75"/>')
        # infra bar, to scale, on the same axis
        infra_w = max(0.6, bw * 1200 / mx)
        b.append(f'<rect x="{x0}" y="{y + 26}" width="{infra_w:.2f}" height="4" class="alert"/>')
        money = f"${cost / 1e6:.1f}M" if cost >= 1e6 else f"${cost / 1e3:.0f}K"
        b.append(text(x0 + w + 10, y + 17, f"{money}  ·  {rev:.0f} reviewers", "ink2", 11.5, mono=True))
    b.append(text(x0, y0 + 3 * gap + 6, "▬ review team, fully loaded incl. clinical supervision",
                  "acc", 10.5))
    b.append(text(x0, y0 + 3 * gap + 22, "▬ cloud infrastructure (~$1,200/yr at pilot scale — visible only as a hairline)",
                  "alert", 10.5))
    b.append(text(40, H - 18, "One reviewer ≈ 54× the annualized infrastructure (>98% of operating cost). Any pitch dominated by SaaS spend describes a different system.",
                  "ink3", 10.5, mono=True))
    return svg(W, H, "\n".join(b), "Annual cost by scenario")


# ── F4 · custody boundary ────────────────────────────────────────────────────

def fig_architecture():
    W, H = 920, 470
    b = [title_block(40, 42, "The custody boundary",
                     "Only a 64-character hexadecimal string crosses the scissor line. Media never does.")]

    def box(x, y, w, h, label, sub, cls="rule", fill=None, dash=False):
        # One class attribute only. Emitting two makes the SVG invalid XML and
        # the whole figure fails to render.
        classes = f"{cls} {fill}" if fill else cls
        fill_attr = "" if fill else ' fill="none"'
        d = ' stroke-dasharray="5 4"' if dash else ""
        out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" class="{classes}"'
               f'{fill_attr} stroke-width="1.4"{d} fill-opacity="0.5"/>']
        out.append(text(x + 14, y + 24, label, "ink", 12.5, weight="700"))
        for i, line in enumerate(sub):
            out.append(text(x + 14, y + 44 + i * 15, line, "ink2", 10.8))
        return "\n".join(out)

    b.append(box(40, 90, 380, 92, "REPORTER'S DEVICE",
                 ["image → PDQ hash (256 bits)",
                  "optional: on-device synthetic score",
                  "the image never leaves"], "accs", "softf"))

    b.append(f'<line x1="230" y1="182" x2="230" y2="228" class="alerts" stroke-width="2" stroke-dasharray="6 4"/>')
    b.append(text(246, 210, "✂  hash + jurisdiction + age indicator only", "alert", 11.5, weight="600", mono=True))

    b.append(box(40, 232, 380, 96, "OUR INFRASTRUCTURE · zero custody",
                 ["fusion of four matchers → routing decision",
                  "no media column, no object storage,",
                  "no hash in any log line"], "accs", "softf"))

    b.append(box(500, 90, 380, 92, "LICENSED SERVICES · their custody",
                 ["PhotoDNA · CSAI Match · HMA · CLIP",
                  "receive a hash, return a score",
                  "never receive a URL to fetch"], "rule"))

    b.append(box(500, 232, 380, 96, "AUTHORITIES · their custody",
                 ["NCMEC CyberTipline (minors)",
                  "FGR / GN Cyber (Mexico)",
                  "preservation BEFORE takedown"], "rule"))

    b.append(f'<line x1="420" y1="136" x2="496" y2="136" class="ink3s" stroke-width="1.4" marker-end="url(#a)"/>')
    b.append(f'<line x1="420" y1="280" x2="496" y2="280" class="ink3s" stroke-width="1.4" marker-end="url(#a)"/>')
    b.append('<defs><marker id="a" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">'
             '<path d="M0,0 L7,3 L0,6" class="ink3" /></marker></defs>')

    b.append(box(40, 366, 840, 64, "WHAT NEVER EXISTS ANYWHERE IN THIS DIAGRAM",
                 ["media bytes · media URLs · thumbnails · a corpus of our own · a storage bucket"],
                 "alerts", None, dash=True))
    return svg(W, H, "\n".join(b), "Zero-custody architecture")


# ── F5 · six disciplines ─────────────────────────────────────────────────────

def fig_disciplines():
    """Twelve disciplines in four clusters. Six were the first draft; a project
    at this scale needs the rest, and each addition has a named failure mode."""
    W, H = 1000, 760
    b = [title_block(40, 42, "Twelve disciplines, four clusters, one system",
                     "Each discipline owns decisions the others are not competent to make. "
                     "A gap in any one is a failure of the whole.")]
    cx, cy, r = 500, 400, 132

    # English primary, Spanish beneath in muted grey. The repository works in
    # English; the region works in Spanish. Both audiences read this figure.
    clusters = [
        ("TECHNICAL CORE", "NÚCLEO TÉCNICO", "acc", [
            ("TECHNOLOGY", "Tecnología", "hashing · fusion · infra"),
            ("DATA & EVIDENCE", "Datos y Evidencia", "measurement · evaluation"),
            ("SECURITY", "Seguridad", "opsec · access · incident"),
        ]),
        ("HUMAN CORE", "NÚCLEO HUMANO", "acc", [
            ("SOCIAL", "Social", "victim research · Defensoras"),
            ("CLINICAL", "Clínica", "trauma · reviewer welfare"),
            ("EDUCATION", "Educación", "prevention · curricula"),
        ]),
        ("INSTITUTIONAL CORE", "NÚCLEO INSTITUCIONAL", "acc", [
            ("LEGAL", "Legal", "7-country tracker · routing"),
            ("PUBLIC POLICY", "Política Pública", "MESECVI · diplomacy"),
            ("ETHICS & GOVERNANCE", "Ética y Gobernanza", "IRB · integrity · COI"),
        ]),
        ("OPERATIONAL CORE", "NÚCLEO OPERATIVO", "alert", [
            ("OPERATIONS", "Operaciones", "review queue · staffing"),
            ("COMMUNICATION", "Comunicación", "message safety"),
            ("ADVERTISING", "Publicidad", "inventory · sequencing"),
        ]),
    ]

    b.append(f'<circle cx="{cx}" cy="{cy}" r="{r - 46}" class="softf" opacity="0.65"/>')
    b.append(text(cx, cy - 8, "VICTIM", "ink", 15, anchor="middle", weight="700"))
    b.append(f'<g opacity="0.7">{text(cx, cy + 8, "Víctima", "ink3", 12, anchor="middle")}</g>')
    b.append(text(cx, cy + 26, "the only stakeholder", "ink3", 10, anchor="middle"))

    flat = [(n, es, s, c) for _, _, c, items in clusters for n, es, s in items]
    total = len(flat)
    for i, (name, spanish, sub, cls) in enumerate(flat):
        ang = -math.pi / 2 + i * 2 * math.pi / total
        nx = cx + (r + 80) * math.cos(ang)
        ny = cy + (r + 52) * math.sin(ang)
        b.append(f'<line x1="{cx + (r - 44) * math.cos(ang):.1f}" '
                 f'y1="{cy + (r - 44) * math.sin(ang):.1f}" '
                 f'x2="{nx:.1f}" y2="{ny:.1f}" class="rule" stroke-width="1"/>')
        b.append(f'<circle cx="{nx:.1f}" cy="{ny:.1f}" r="6.5" class="{cls}"/>')
        b.append(text(nx, ny - 24, name, cls, 11, anchor="middle", weight="700"))
        b.append(f'<g opacity="0.7">'
                 f'{text(nx, ny - 11, spanish, "ink3", 9.5, anchor="middle")}</g>')
        b.append(text(nx, ny + 24, sub, "ink3", 9.5, anchor="middle"))

    # cluster legend
    lx, ly = 40, H - 118
    for i, (label, label_es, cls, items) in enumerate(clusters):
        col = lx + (i % 2) * 470
        row = ly + (i // 2) * 48
        b.append(f'<rect x="{col}" y="{row - 8}" width="9" height="9" class="{cls}"/>')
        b.append(text(col + 16, row, label, cls, 10.5, weight="700"))
        b.append(f'<g opacity="0.7">{text(col + 16, row + 13, label_es, "ink3", 9)}</g>')
        b.append(text(col + 16, row + 27, " · ".join(n for n, _, _ in items), "ink3", 9.5))

    b.append(text(40, H - 20, "The first six were where we started. The other six each have a named "
                              "failure mode; see dossier/13_DISCIPLINES.md.", "ink3", 10, mono=True))
    return svg(W, H, "\n".join(b), "Twelve-discipline operating model")


def fig_routing():
    """Who receives what, and under which instrument."""
    W, H = 980, 520
    b = [title_block(40, 42, "Where a report goes, and under what authority",
                     "The routing layer. This mapping is the project's defensible asset; the hashing is open source.")]

    rows = [
        ("minor · any jurisdiction", "NCMEC CyberTipline", "bridges to INTERPOL ICSE",
         "⚫ vetting pending", "alert"),
        ("adult · 🇲🇽 MX", "FGR / GN Cyber", "Ley Olimpia EN VIGOR",
         "art. 199 Septies still in committee", "acc"),
        ("adult · 🇵🇪 PE", "Takedown + local report", "Ley 32314 EN VIGOR since abr-2025",
         "regional proof point", "acc"),
        ("adult · 🇪🇨 EC", "Takedown package", "integración en curso",
         "pitch: implement the OAS standard", "acc"),
        ("adult · 🇨🇱 CL", "Takedown package", "⚠ source conflict unresolved",
         "blocked for Chile-facing material", "alert"),
        ("adult · 🇦🇷 AR · 🇵🇦 PA", "Takedown package", "Ley Olimpia 2023 / 2024",
         "regional context", "acc"),
        ("any · 🇺🇸 US platform", "TAKE IT DOWN Act notice", "48h removal · FTC enforcing",
         "$53,088 per violation since 19-may-2026", "acc"),
        ("any · 🇪🇺 EU", "DSA notice-and-action", "DSA EN VIGOR",
         "CSA Regulation still in trilogue", "acc"),
        ("below threshold · all", "Human review queue", "trained reviewer + clinical support",
         "the binding constraint", "alert"),
    ]

    x0, y = 40, 108
    b.append(f'<line x1="{x0}" y1="{y - 14}" x2="{W - 40}" y2="{y - 14}" class="rule" stroke-width="1"/>')
    for label, col in [("REPORT CLASS", x0), ("ROUTES TO", 300), ("INSTRUMENT", 530), ("STATUS", 770)]:
        b.append(text(col, y - 22, label, "ink3", 8.5, weight="600", mono=True))

    for cls_label, dest, instrument, status, cls in rows:
        b.append(text(x0, y + 12, cls_label, "ink", 11, weight="600"))
        b.append(text(300, y + 12, dest, cls, 11, weight="600"))
        b.append(text(530, y + 12, instrument, "ink2", 10))
        b.append(text(770, y + 12, status, "ink3", 9.5))
        y += 40
        b.append(f'<line x1="{x0}" y1="{y - 14}" x2="{W - 40}" y2="{y - 14}" class="rule"/>')

    b.append(text(40, H - 22, "Preservation ALWAYS precedes takedown. Removing content first destroys the "
                              "evidence with it.", "alert", 10.5, mono=True))
    return svg(W, H, "\n".join(b), "Routing by jurisdiction and instrument")


def fig_country_status():
    """Legislative status board. Only en_vigor may be cited as applicable law."""
    W, H = 980, 460
    b = [title_block(40, 42, "Legislative status · verified 2026-07-25 · Chile re-verified 2026-08-02",
                     "CI fails any tracker file older than 90 days. Only EN VIGOR may be cited as applicable law.")]

    rows = [
        ("🇵🇪 Perú", "Ley 32314", "EN VIGOR", 1.0, "abr-2025 · AI as aggravating factor · 6–10 yrs", "acc"),
        ("🇲🇽 México", "Ley Olimpia federal", "EN VIGOR", 1.0, "2021 · covers REAL content only", "acc"),
        ("🇲🇽 México", "Reforma art. 199 Septies", "EN COMISIÓN", 0.45, "Gaceta 21-ene-2026 · NOT LAW", "alert"),
        ("🇦🇷 Argentina", "Ley Olimpia AR", "EN VIGOR", 0.85, "2023 · law number unverified", "acc"),
        ("🇵🇦 Panamá", "Ley Olimpia PA", "EN VIGOR", 0.85, "2024 · law number unverified", "acc"),
        ("🇪🇨 Ecuador", "Integración Ley Olimpia", "EN CURSO", 0.35, "ruta abierta 2024 · trip target", "alert"),
        ("🇨🇱 Chile", "Ley 21.675 art. 161-D CP", "EN VIGOR", 0.9, "jun-2024 · real content only; AI wording unconfirmed", "acc"),
        ("🌎 OEA", "Ley Modelo MESECVI", "ESTÁNDAR", 0.7, "dic-2025 · model, not binding anywhere", "acc"),
        ("🇺🇸 EE.UU.", "TAKE IT DOWN Act", "EN VIGOR", 1.0, "FTC enforcing since 19-may-2026", "acc"),
        ("🇪🇺 UE", "DSA", "EN VIGOR", 1.0, "CSA Regulation still in trilogue", "acc"),
    ]

    x0, y, bw = 40, 105, 210
    labx, barx = x0, 330
    for country, inst, status, level, note, cls in rows:
        b.append(text(labx, y + 11, country, "ink", 11, weight="700"))
        b.append(text(labx + 92, y + 11, inst, "ink2", 10.5))
        b.append(f'<rect x="{barx}" y="{y + 1}" width="{bw}" height="13" class="rule" '
                 f'fill="none" stroke-width="1"/>')
        b.append(f'<rect x="{barx}" y="{y + 1}" width="{bw * level:.0f}" height="13" '
                 f'class="{cls}" opacity="0.75"/>')
        b.append(text(barx + bw + 12, y + 11, status, cls, 9.5, weight="700", mono=True))
        b.append(text(barx + bw + 120, y + 11, note, "ink3", 9.5))
        y += 30

    b.append(text(40, H - 40, "Bar length = how far the instrument reaches, not how confident we are. "
                              "Confidence is per-file in legal/tracker/.", "ink3", 10))
    b.append(text(40, H - 20, "Presenting a bill in committee as law is the single most credibility-costly "
                              "error available in this project.", "alert", 10.5, mono=True))
    return svg(W, H, "\n".join(b), "Legislative status by country")


def fig_global_status():
    """
    Legislative status board for the global tracker expansion, same layout as
    fig_country_status so the two print and read as one pair. All eighteen
    jurisdictions added on 2026-08-02 appear; the LATAM board stays fig8.
    """
    W, H = 980, 700
    b = [title_block(40, 42, "Legislative status · global expansion · verified 2026-08-02",
                     "The 18 jurisdictions added to legal/tracker/. Only EN VIGOR may be cited as applicable law.")]

    rows = [
        ("🇪🇺 UE", "DSA · 2024/1385 · AI Act", "EN VIGOR", 1.0, "trusted flaggers · CSAM recast still in trilogue", "acc"),
        ("🇩🇪 Alemania", "§ 184b StGB", "EN VIGOR", 1.0, "\"realistic\" written into the offence · primary-checked", "acc"),
        ("🇫🇷 Francia", "Art. 226-8-1 CP (SREN)", "EN VIGOR", 0.9, "may-2024 · sexual deepfake, 2 yrs + EUR 60k", "acc"),
        ("🇪🇸 España", "Art. 173 bis CP", "EN COMISIÓN", 0.45, "in Congress since mar-2025 · NOT LAW · 189 covers pseudo-CSAM", "alert"),
        ("🇮🇪 Irlanda", "Coco's Law + CTPA 1998", "EN VIGOR", 0.7, "deepfake reach untested in court · verify first", "acc"),
        ("🇮🇹 Italia", "Art. 612-quater CP", "EN VIGOR", 1.0, "oct-2025 · first EU member state with its own deepfake crime", "acc"),
        ("🇳🇱 P. Bajos", "Art. 252 Sr (ex 240b)", "EN VIGOR", 1.0, "jul-2024 · AI CSAM punishable, explicit doctrine", "acc"),
        ("🇬🇧 R. Unido", "OSA 2023 + DUAA 2025", "EN VIGOR", 1.0, "creating a deepfake criminal since 6-feb-2026", "acc"),
        ("🇿🇦 Sudáfrica", "Cybercrimes Act s. 16", "EN VIGOR", 0.8, "dic-2021 · \"real or simulated\" pending primary check", "acc"),
        ("🇯🇵 Japón", "sin estatuto sintético", "VACÍO", 0.15, "⚠ DECLARED GAP · Nagoya ruling stretches a 1999 law", "alert"),
        ("🇰🇷 Corea del Sur", "Art. 14-2 reformado", "EN VIGOR", 1.0, "sep-2024 · 7 yrs production, 3 yrs possession/viewing", "acc"),
        ("🇨🇳 China", "Deep Synthesis + Labeling", "EN VIGOR", 0.7, "administrative regime, no specific crime", "acc"),
        ("🇮🇳 India", "IT Rules 2026 (SGI)", "EN VIGOR", 0.75, "feb-2026 · 2-hour NCII takedown · administrative", "acc"),
        ("🇵🇭 Filipinas", "RA 11930 · CSAEM", "EN VIGOR", 1.0, "\"computer-generated\" explicit in the CSAM definition", "acc"),
        ("🇮🇩 Indonesia", "UU TPKS art. 14", "EN VIGOR", 0.6, "applied to deepfakes by doctrine · no express AI wording", "acc"),
        ("🇸🇬 Singapur", "377BE + OSRAA 2025", "EN VIGOR", 0.95, "Online Safety Commission live since 29-jun-2026", "acc"),
        ("🇦🇺 Australia", "Deepfake Sexual Material Act", "EN VIGOR", 1.0, "No. 78/2024 · verified at legislation.gov.au", "acc"),
        ("🇺🇳 ONU", "UNICEF · OHCHR · UNESCO", "SOFT LAW", 0.5, "binds nobody until a state legislates · framing only", "acc"),
    ]

    x0, y, bw = 40, 105, 210
    labx, barx = x0, 330
    for country, inst, status, level, note, cls in rows:
        b.append(text(labx, y + 11, country, "ink", 11, weight="700"))
        b.append(text(labx + 120, y + 11, inst, "ink2", 10.5))
        b.append(f'<rect x="{barx}" y="{y + 1}" width="{bw}" height="13" class="rule" '
                 f'fill="none" stroke-width="1"/>')
        b.append(f'<rect x="{barx}" y="{y + 1}" width="{bw * level:.0f}" height="13" '
                 f'class="{cls}" opacity="0.75"/>')
        b.append(text(barx + bw + 12, y + 11, status, cls, 9.5, weight="700", mono=True))
        b.append(text(barx + bw + 120, y + 11, note, "ink3", 9.5))
        y += 30

    b.append(text(40, H - 40, "Bar length = how far the instrument reaches, not how confident we are. "
                              "Confidence is per-file in legal/tracker/.", "ink3", 10))
    b.append(text(40, H - 20, "China and India reach fast but administratively: obligations on platforms, "
                              "not criminal law. Japan is the declared gap.", "alert", 10.5, mono=True))
    return svg(W, H, "\n".join(b), "Legislative status, global tracker expansion")


def fig_pipeline():
    """Where harm actually originates, and which layer can intervene where."""
    W, H = 980, 470
    b = [title_block(40, 42, "The exploitation pipeline, and where each layer can act",
                     "Hash matching sits at the far right. Everything to its left is somebody else's layer.")]

    stages = [
        ("CONTACT", "child-heavy platform", "grooming begins in-game", 0),
        ("MIGRATION", "→ unmonitored app", "\"add me on Discord\"", 1),
        ("PRODUCTION", "coerced imagery", "or AI-generated from photos", 2),
        ("DISTRIBUTION", "forums · clear web", "IWF: 3,440 AI videos in 2025", 3),
        ("REDISTRIBUTION", "years of circulation", "where harm compounds", 4),
    ]
    x0, y, step = 55, 150, 182
    for name, sub, note, i in stages:
        x = x0 + i * step
        danger = i <= 2
        b.append(f'<rect x="{x}" y="{y}" width="152" height="66" class="{"alerts" if danger else "accs"}" '
                 f'fill="none" stroke-width="1.5"/>')
        b.append(text(x + 12, y + 22, name, "alert" if danger else "acc", 11, weight="700"))
        b.append(text(x + 12, y + 39, sub, "ink2", 9.5))
        b.append(text(x + 12, y + 54, note, "ink3", 8.8))
        if i < 4:
            b.append(f'<line x1="{x + 152}" y1="{y + 33}" x2="{x + step - 4}" y2="{y + 33}" '
                     f'class="ink3s" stroke-width="1.3" marker-end="url(#p)"/>')
    b.append('<defs><marker id="p" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">'
             '<path d="M0,0 L7,3 L0,6" class="ink3"/></marker></defs>')

    interventions = [
        ("age assurance", 0, "Roblox facial age estimation, global Jan-2026"),
        ("off-platform friction", 1, "⚫ THE GAP — nobody owns this"),
        ("on-device nudity block", 2, "Apple Sensitive Content Analysis · on-device"),
        ("platform-edge classifier", 3, "licensed, in the platform's custody"),
        ("HASH MATCHING · ours", 4, "redistribution interdiction + legal routing"),
    ]
    yy = y + 120
    b.append(text(55, yy - 12, "WHO CAN INTERVENE", "ink3", 8.5, weight="600", mono=True))
    for label, i, who in interventions:
        x = x0 + i * step
        ours = i == 4
        gap = i == 1
        cls = "acc" if ours else ("alert" if gap else "ink2")
        b.append(f'<line x1="{x + 76}" y1="{y + 66}" x2="{x + 76}" y2="{yy - 4}" '
                 f'class="rule" stroke-dasharray="3 3"/>')
        b.append(text(x + 76, yy + 8, label, cls, 10, anchor="middle",
                      weight="700" if ours or gap else None))
        # wrap
        words, line, lines = who.split(), "", []
        for w in words:
            if len(line) + len(w) > 24:
                lines.append(line); line = w
            else:
                line = (line + " " + w).strip()
        lines.append(line)
        for j, ln in enumerate(lines):
            b.append(text(x + 76, yy + 24 + j * 12, ln, "ink3", 8.6, anchor="middle"))

    b.append(text(40, H - 22, "The migration step is the highest-leverage unowned problem in this diagram. "
                              "It is a platform-design problem, not a detection problem.",
                  "alert", 10.5, mono=True))
    return svg(W, H, "\n".join(b), "Exploitation pipeline and intervention points")


# ── F6 · what broke, when ────────────────────────────────────────────────────

def fig_timeline():
    W, H = 920, 340
    b = [title_block(40, 42, "Why no single algorithm is defensible",
                     "Public breaks of deployed perceptual hashes. Each was announced as robust before it was broken.")]
    events = [
        ("2009", "PhotoDNA deployed", "Microsoft + Hany Farid, donated to NCMEC", "ink2"),
        ("2019", "PDQ open-sourced", "Meta publishes a 256-bit DCT hash", "ink2"),
        ("2021", "NeuralHash broken", "collisions found within weeks; Apple shelves the programme", "alert"),
        ("2022", "PDQ tail measured", "closest unrelated pair at 10 bits, threshold is 31", "alert"),
        ("2026", "PhotoDNA inverted", "collisions + partial image recovery, ~100% success on a laptop", "alert"),
    ]
    # Inset from the canvas edge so the centred first and last labels fit.
    x0, y, x1 = 150, 175, 790
    b.append(f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y}" class="rule" stroke-width="2"/>')
    step = (x1 - x0) / (len(events) - 1)
    for i, (yr, head, sub, cls) in enumerate(events):
        x = x0 + i * step
        up = i % 2 == 0
        ty = y - 34 if up else y + 48
        b.append(f'<circle cx="{x:.1f}" cy="{y}" r="6" class="{cls}"/>')
        b.append(f'<line x1="{x:.1f}" y1="{y + (-8 if up else 8)}" x2="{x:.1f}" '
                 f'y2="{ty + (14 if up else -22)}" class="rule"/>')
        b.append(text(x, ty, yr, cls, 12.5, anchor="middle", weight="700", mono=True))
        b.append(text(x, ty + (-16 if up else 16), head, "ink", 11.5, anchor="middle", weight="600"))
        # wrap the subtitle
        words, line, lines = sub.split(), "", []
        for wd in words:
            if len(line) + len(wd) > 30:
                lines.append(line)
                line = wd
            else:
                line = (line + " " + wd).strip()
        lines.append(line)
        # Above the axis the block grows upward, so the lines have to be laid
        # out in reverse or the caption reads bottom-to-top.
        n = len(lines)
        for j, ln in enumerate(lines):
            dy = -32 - (n - 1 - j) * 13 if up else 32 + j * 13
            b.append(text(x, ty + dy, ln, "ink3", 9.8, anchor="middle"))
    b.append(text(40, H - 18, "Sources: arXiv:2111.06628 · arXiv:2212.08035 · IACR ePrint 2026/486",
                  "ink3", 10, mono=True))
    return svg(W, H, "\n".join(b), "Timeline of perceptual hash breaks")


def fig_hard_rules():
    """The six hard rules, with what enforces each one."""
    W, H = 980, 620
    b = [title_block(40, 42, "The six hard rules, and what enforces them",
                     "Not principles. Automated checks that fail the build. "
                     "A rule nobody can break by accident is the only kind worth writing.")]

    rules = [
        ("01", "No media. Ever.",
         "Never download, store, cache or log media content or media URLs.",
         "scripts/check-custody.mjs · logger allowlist · .strict() schemas",
         "A URL to abuse material IS custody. Logs count."),
        ("02", "No self-trained classifier",
         "Only licensed services: PhotoDNA, CSAI Match, HMA, Thorn.",
         "matchers accept a string, never an image",
         "A synthetic-media detector is a different thing, and is permitted."),
        ("03", "Synthetic test data only",
         "All tests use fixtures/dummy_hashes.json. No real case data, ever.",
         "tests/fixtures.ts refuses any unlabelled entry",
         "20 random 256-bit values. No image, no case, no person."),
        ("04", "Thresholds stay server-side",
         "Match thresholds live in env config, never in a client bundle.",
         "server-only import · CI greps the built bundle",
         "Apple's NeuralHash fell in weeks once thresholds shipped to clients."),
        ("05", "No silent drops",
         "Every queue consumer needs a dead-letter path and an alerting hook.",
         "Pub/Sub DLQ · PagerDuty · hourly SLA sweep",
         "A dropped report is a person who asked for help and did not get it."),
        ("06", "Secrets never touch the repo",
         "Google Secret Manager. Nothing in .env. Pre-commit scanning on.",
         "gitleaks · Terraform creates containers, never values",
         "Never paste a credential into any chat, including an AI assistant."),
    ]

    cw, ch, gx, gy = 448, 132, 24, 18
    x0, y0 = 40, 96
    for i, (num, title, rule, enforced, why) in enumerate(rules):
        x = x0 + (i % 2) * (cw + gx)
        y = y0 + (i // 2) * (ch + gy)
        b.append(f'<rect x="{x}" y="{y}" width="{cw}" height="{ch}" class="rule" '
                 f'fill="none" stroke-width="1.2"/>')
        b.append(f'<rect x="{x}" y="{y}" width="4" height="{ch}" class="acc"/>')
        b.append(text(x + 18, y + 26, num, "acc", 15, weight="700", mono=True))
        b.append(text(x + 50, y + 26, title, "ink", 13.5, weight="700"))
        b.append(text(x + 18, y + 48, rule, "ink2", 10.2))
        b.append(f'<line x1="{x + 18}" y1="{y + 60}" x2="{x + cw - 18}" y2="{y + 60}" class="rule"/>')
        b.append(text(x + 18, y + 78, "ENFORCED BY", "ink3", 7.8, weight="600", mono=True))
        b.append(text(x + 18, y + 92, enforced, "acc", 9.2, mono=True))
        b.append(text(x + 18, y + 114, why, "ink3", 9.2))

    b.append(text(40, H - 20, "Run all six locally:  npm run verify", "ink3", 10.5, mono=True))
    return svg(W, H, "\n".join(b), "The six hard rules and their enforcement")


def fig_three_branches():
    """Three workstreams moving at different speeds, and the gate between them."""
    W, H = 980, 570
    b = [title_block(40, 42, "Three branches, three speeds, one gate",
                     "The branches do not move at the same pace, and pretending otherwise "
                     "is how projects like this fail.")]

    lanes = [
        ("ENGINEERING", "Ingeniería", "acc", 118,
         "weeks", "Code, infrastructure, measurement. Fast, reversible, "
                  "and the only branch we fully control.",
         ["hash intake", "fusion + routing", "auto-dismiss", "client apps"]),
        ("POLICY & LAW", "Política y Derecho", "ink2", 246,
         "years", "Legislatures, ministries, MESECVI. Slow by design, and "
                  "nothing we do accelerates it much.",
         ["7-country tracker", "NCMEC vetting", "legal entity", "OAS route"]),
        ("SOCIAL & CAMPAIGN", "Social y Campaña", "alert", 374,
         "days", "Awareness, media, public attention. The fastest branch, "
                 "and the one that must be held back.",
         ["Defensoras", "earned media", "free inventory", "MASIVA"]),
    ]

    x0, xw = 210, 560
    for name, es, cls, y, speed, desc, items in lanes:
        b.append(f'<rect x="{x0}" y="{y}" width="{xw}" height="86" class="{cls}s" '
                 f'fill="none" stroke-width="1.4"/>')
        b.append(text(40, y + 24, name, cls, 12.5, weight="700"))
        b.append(f'<g opacity="0.7">{text(40, y + 39, es, "ink3", 10)}</g>')
        b.append(text(40, y + 60, f"moves in {speed}", "ink3", 9.5, mono=True))
        words, line, dlines = desc.split(), "", []
        for wd in words:
            if len(line) + len(wd) > 64:
                dlines.append(line); line = wd
            else:
                line = (line + " " + wd).strip()
        dlines.append(line)
        for di, dl in enumerate(dlines[:2]):
            b.append(text(x0 + 16, y + 24 + di * 14, dl, "ink2", 10))
        for j, it in enumerate(items):
            ix = x0 + 16 + j * 136
            b.append(f'<rect x="{ix}" y="{y + 52}" width="124" height="20" '
                     f'class="softf"/>')
            b.append(text(ix + 62, y + 66, it, "ink2", 9, anchor="middle"))

    # the gate
    gy = 462
    b.append(f'<rect x="40" y="{gy}" width="{W - 80}" height="46" class="alerts" '
             f'fill="none" stroke-width="1.5" stroke-dasharray="5 4"/>')
    b.append(text(58, gy + 20, "THE GATE", "alert", 11, weight="700"))
    b.append(text(58, gy + 36, "Social may not outrun engineering. A campaign that exceeds intake capacity "
                               "manufactures a queue of people who asked for help and did not get it.",
                  "ink2", 10))

    b.append(f'<line x1="{x0 + xw + 20}" y1="204" x2="{x0 + xw + 20}" y2="{gy}" '
             f'class="alerts" stroke-width="1.2" stroke-dasharray="4 3"/>')
    b.append(text(W - 40, 200, "pipeline → pilot → MASIVA", "alert", 9.5, anchor="end", mono=True))

    b.append(text(40, H - 14, "Each branch needs its own people, its own timeline and its own "
                              "definition of done.", "ink3", 10, mono=True))
    return svg(W, H, "\n".join(b), "Three branches at three speeds")


# ── F12 · the synthetic media quadrants ──────────────────────────────────────

def fig_synthetic_quadrants():
    """
    Corrects the "generative AI vs deepfake" binary used in the Berkeley deck.

    The deck's slide 11 splits synthetic sexual imagery by MECHANISM (generated
    from a prompt vs. face-swapped onto footage) and concludes that the
    generative side has "no direct individual victim". That conclusion is wrong,
    and the mechanism axis is collapsing anyway: current tools do both in one
    pass. The axes that actually determine legality, harm and detectability are
    identifiability of the subject and whether the subject is a minor.

    See dossier/19_DECK_AUDIT.md §A.11.
    """
    # H is sized so the correction panel (which ends at ny + 96 = 612) clears
    # the footer. An earlier 600 put the footer through the panel's last line;
    # the XML parsed fine and the figure was unreadable. Look at the render.
    W, H = 980, 664
    b = [title_block(40, 42, "What actually divides synthetic sexual imagery",
                     "Not “generative vs deepfake”. Mechanism is collapsing; "
                     "these two axes decide legality, harm and whether we can see it.")]

    x0, y0, qw, qh = 250, 110, 340, 176
    cells = [
        (0, 0, "Identifiable minor",
         ["Worst case. Illegal in every", "jurisdiction in our scope.",
          "Victim identifiable, so victim", "identification applies."],
         "MATCHABLE once enrolled", "acc"),
        (1, 0, "Non-identifiable minor",
         ["Illegal in most jurisdictions", "in scope regardless of whether",
          "a specific child exists.", "The deck calls this victimless."],
         "INVISIBLE on first generation", "alert"),
        (0, 1, "Identifiable adult",
         ["NCII. Take It Down Act (US),",
          "DUAA 2025 s.138 (UK),", "Ley Olimpia (MX).",
          "Named victim, named remedy."],
         "MATCHABLE once enrolled", "acc"),
        (1, 1, "Non-identifiable adult",
         ["Largely lawful in most of",
          "our scope. Not this", "project’s remit.", ""],
         "OUT OF SCOPE", "ink3"),
    ]
    for col, row, label, lines, verdict, cls in cells:
        x = x0 + col * (qw + 14)
        y = y0 + row * (qh + 14)
        b.append(f'<rect x="{x}" y="{y}" width="{qw}" height="{qh}" class="rule" '
                 f'fill="none" stroke-width="1.2"/>')
        b.append(f'<rect x="{x}" y="{y}" width="{qw}" height="26" class="softf" opacity="0.55"/>')
        b.append(text(x + 14, y + 18, label, "ink", 12.5, weight="700"))
        for j, line in enumerate(lines):
            b.append(text(x + 14, y + 48 + j * 16, line, "ink2", 10.4))
        b.append(f'<line x1="{x + 14}" y1="{y + qh - 32}" x2="{x + qw - 14}" '
                 f'y2="{y + qh - 32}" class="rule"/>')
        b.append(text(x + 14, y + qh - 14, verdict, cls, 10, weight="700", mono=True))

    b.append(text(x0 + qw + 7, y0 - 16, "SUBJECT", "ink3", 9, anchor="middle",
                  weight="600", mono=True))
    b.append(text(x0 + qw / 2, y0 - 2, "identifiable real person", "ink3", 9.5, anchor="middle"))
    b.append(text(x0 + qw + 14 + qw / 2, y0 - 2, "no identifiable person", "ink3", 9.5,
                  anchor="middle"))
    b.append(text(x0 - 18, y0 + qh / 2, "MINOR", "ink3", 10, anchor="end", weight="700", mono=True))
    b.append(text(x0 - 18, y0 + qh + 14 + qh / 2, "ADULT", "ink3", 10, anchor="end",
                  weight="700", mono=True))

    ny = y0 + 2 * qh + 40
    b.append(f'<rect x="40" y="{ny}" width="900" height="96" class="alerts" fill="none" '
             f'stroke-width="1.4" stroke-dasharray="5 4"/>')
    b.append(text(56, ny + 24, "THE CORRECTION", "alert", 10.5, weight="700", mono=True))
    b.append(text(56, ny + 46,
                  "“Unlinked to real individuals” is an assumption, not a property. "
                  "Absence of a named victim is a failure of attribution,", "ink", 11))
    b.append(text(56, ny + 64,
                  "not an absence of harm. Fully synthetic material depicting minors is "
                  "illegal across our scope, and the top-right cell", "ink", 11))
    b.append(text(56, ny + 82,
                  "is the one our architecture structurally cannot see. "
                  "Both red cells are L1, not an implementation gap.", "ink", 11))
    b.append(text(40, H - 16, "Corrects: Berkeley deck slide 11 · see "
                              "dossier/19_DECK_AUDIT.md §A.11", "ink3", 10, mono=True))
    return svg(W, H, "\n".join(b), "The four cases of synthetic sexual imagery")


# ── F13 · biometric layers against the custody boundary ──────────────────────

def fig_biometric_custody():
    """
    Every forensic biometric layer, scored on two questions: does it need
    custody of the content, and does it work against generated material.

    The point of the figure is that only one row sits inside our boundary, and
    that the layers outside it mostly fail against the threat we exist for.
    See dossier/20_BIOMETRIC_LAYERS.md.
    """
    W, H = 980, 560
    b = [title_block(40, 42, "Forensic biometric layers vs. our custody boundary",
                     "Built for camera-captured abuse. Against generated material, "
                     "most of the stack has nothing to read.")]

    rows = [
        ("Facial / craniofacial", "CHEXIA · DHS S&T · NIST", False,
         "partial", "identifies nobody — the face is a training average"),
        ("Voice / acoustic", "AIC · BANE", False,
         "partial", "matches a synthesis model at best"),
        ("Camera sensor (PRNU)", "device-level attribution", False,
         "none", "UNDEFINED — no sensor ever existed"),
        ("Object / background", "INTERPOL · analyst-led", False,
         "none", "the room and the props never existed"),
        ("ICSE corpus matching", "INTERPOL · 72 countries", False,
         "partial", "matches nothing on first generation"),
        ("Perceptual hashing", "PhotoDNA · PDQ · ours", True,
         "none", "cannot see first generation — L1"),
    ]

    x0, y0, rh = 40, 108, 54
    b.append(text(x0 + 8, y0 - 12, "LAYER", "ink3", 8.6, weight="600", mono=True))
    b.append(text(x0 + 336, y0 - 12, "NEEDS CUSTODY?", "ink3", 8.6, weight="600", mono=True))
    b.append(text(x0 + 470, y0 - 12, "WORKS ON SYNTHETIC?", "ink3", 8.6, weight="600", mono=True))

    for i, (name, who, inside, synth, note) in enumerate(rows):
        y = y0 + i * rh
        b.append(f'<rect x="{x0}" y="{y}" width="900" height="{rh - 6}" class="rule" '
                 f'fill="none" stroke-width="1"/>')
        b.append(f'<rect x="{x0}" y="{y}" width="4" height="{rh - 6}" '
                 f'class="{"acc" if inside else "alert"}"/>')
        b.append(text(x0 + 18, y + 22, name, "ink", 12.5, weight="700"))
        b.append(text(x0 + 18, y + 39, who, "ink3", 9.6, mono=True))
        b.append(text(x0 + 336, y + 30, "inside ✓" if inside else "OUTSIDE ✗",
                      "acc" if inside else "alert", 11, weight="700", mono=True))
        cls = {"partial": "ink2", "none": "alert"}[synth]
        label = {"partial": "partial", "none": "no"}[synth]
        b.append(text(x0 + 470, y + 30, label, cls, 11, weight="700", mono=True))
        b.append(text(x0 + 546, y + 30, note, "ink3", 10))

    ny = y0 + len(rows) * rh + 14
    b.append(f'<rect x="40" y="{ny}" width="900" height="76" class="accs" fill="none" '
             f'stroke-width="1.4"/>')
    b.append(text(56, ny + 24, "WHY WE DO NOT ADOPT ANY OF IT", "acc", 10.5,
                  weight="700", mono=True))
    b.append(text(56, ny + 46,
                  "Adopting these layers imports full custody risk, full legal exposure and "
                  "a live research-ethics controversy,", "ink", 11))
    b.append(text(56, ny + 64,
                  "and buys close to nothing against synthetic material. "
                  "We route to the authorities who hold them. We do not replicate them.", "ink", 11))
    b.append(text(40, H - 16, "ICSE: 6M+ files, 72 countries, 56,000 victims identified by "
                              "Sept 2025 — law enforcement access only", "ink3", 10, mono=True))
    return svg(W, H, "\n".join(b), "Biometric layers against the custody boundary")


# ── F14 · deck claim audit ───────────────────────────────────────────────────

def fig_deck_audit():
    """Verdict on every checkable numeric claim in the Berkeley deck."""
    # 17 rows push the tally legend to y=605; the footer must sit below it.
    W, H = 980, 680
    b = [title_block(40, 42, "Every checkable claim in the Berkeley deck",
                     "Verified against primary sources, 2026-07-27. "
                     "Green survives a fact-check. Red does not.")]

    claims = [
        ("1.2M children, deepfake abuse", "ok", "correct — but 11 countries, not 17"),
        ("MOCIBA: 18.9M, 21.0%, 22.2%/19.6%", "ok", "every figure verified against INEGI"),
        ("Yucatán 29.7% · SLP 26.9% · Hidalgo 26.2%", "ok", "verified"),
        ("EU DSA · VLOP threshold 45M", "ok", "verified"),
        ("Take It Down Act · 48-hour window", "ok", "live since 19 May 2026, FTC enforcing"),
        ("UK · creation of purported intimate image", "ok", "in force 6 Feb 2026, SOA ss.66E–H"),
        ("45 million views", "warn", "real, but it is one case: Swift, Jan 2024, 17 hrs"),
        ("4M monthly users, nudify bots", "warn", "WIRED Oct 2024, uncited and 21 months old"),
        ("58% of girls, online harassment", "bad", "ages 15–25, not 8–15 · 2020 data, undated"),
        ("1 in 25 girls / six months", "bad", "1 in 25 CHILDREN, in SOME countries, past YEAR"),
        ("96% of deepfakes are explicit", "bad", "Sensity 2019, n=14,678 · seven years stale"),
        ("Korea: mandatory 7-year sentences", "bad", "maxima not minima · viewing is 3 yrs"),
        ("GenAI porn: “no direct victim”", "bad", "contradicts slide 22 and the law"),
        ("17% of synthetic content on IG/FB/WA", "none", "no source found"),
        ("2/3 of children report an uptick", "none", "no source found for that wording"),
        ("thousands of images per hour", "none", "no source found"),
        ("61% payment leaders / 60%", "none", "broadly attested, specific pairing uncited"),
    ]

    key = {
        "ok":   ("acc",   "VERIFIED"),
        "warn": ("ink2",  "NEEDS CONTEXT"),
        "bad":  ("alert", "WRONG"),
        "none": ("ink3",  "UNSOURCED"),
    }

    x0, y0, rh = 40, 104, 29
    for i, (claim, verdict, note) in enumerate(claims):
        y = y0 + i * rh
        cls, label = key[verdict]
        if i % 2 == 0:
            b.append(f'<rect x="{x0}" y="{y - 14}" width="900" height="{rh}" '
                     f'class="softf" opacity="0.30"/>')
        b.append(f'<rect x="{x0}" y="{y - 10}" width="3" height="16" class="{cls}"/>')
        b.append(text(x0 + 14, y, claim, "ink", 11.4))
        b.append(text(x0 + 348, y, label, cls, 9.4, weight="700", mono=True))
        b.append(text(x0 + 468, y, note, "ink2", 10.4))

    ny = y0 + len(claims) * rh + 8
    tally = [("6 verified", "acc"), ("2 need context", "ink2"),
             ("5 wrong", "alert"), ("4 unsourced", "ink3")]
    cx = x0
    for label, cls in tally:
        b.append(f'<rect x="{cx}" y="{ny}" width="10" height="10" class="{cls}"/>')
        b.append(text(cx + 18, ny + 9, label, "ink2", 11))
        cx += 150
    b.append(text(40, H - 16, "Full working: dossier/19_DECK_AUDIT.md", "ink3", 10, mono=True))
    return svg(W, H, "\n".join(b), "Audit verdicts on the Berkeley deck's claims")


# ── F16 · provenance / watermark robustness matrix ───────────────────────────

def fig_watermark_robustness():
    """
    The provenance layer, scored the way the detection stack is scored elsewhere:
    where the mark is embedded, whether independent tests show it survives
    crop+JPEG laundering, and the published attack that removes it.

    The point is that no single row is a standalone signal, which is the same
    layered conclusion the hashing stack reaches. See
    dossier/22_PROVENANCE_WATERMARK_LANDSCAPE.md Tasks 1-2.
    """
    W, H = 980, 620
    b = [title_block(40, 42, "No single invisible watermark is a standalone signal",
                     "Embedding point predicts the attack that beats it. "
                     "Robustness = independent crop+JPEG tests, not vendor claims.")]

    # embed: where the mark lives · robust: survives laundering · break: named attack
    rows = [
        ("C2PA / Content Credentials", "signed metadata (off-pixel)", "no",
         "stripped by every major social platform on re-upload"),
        ("StableSignature", "in-model weights", "no",
         "regeneration, ~20 noising steps (arXiv 2410.05470)"),
        ("TreeRing", "initial noise", "no",
         "steganalysis averaging + regeneration (WAVES)"),
        ("SynthID (image)", "post-hoc pixel", "partial",
         "degrades on heavy crop; noai-watermark targets it"),
        ("Meta Pixel/Video Seal", "post-hoc pixel", "partial",
         "open weights aid white-box attacks; audit thin"),
        ("Digimarc Validate (C2PA 2.1)", "post-hoc pixel", "partial",
         "durable soft-binding; robustness vendor-sourced"),
        ("Adobe TrustMark", "post-hoc pixel", "partial",
         "best-documented open robustness; ships a removal model"),
    ]

    x0, y0, rh = 40, 112, 58
    b.append(text(x0 + 18, y0 - 12, "SCHEME", "ink3", 8.6, weight="600", mono=True))
    b.append(text(x0 + 300, y0 - 12, "EMBEDDING POINT", "ink3", 8.6, weight="600", mono=True))
    b.append(text(x0 + 520, y0 - 12, "SURVIVES CROP+JPEG?", "ink3", 8.6, weight="600", mono=True))

    for i, (name, embed, robust, brk) in enumerate(rows):
        y = y0 + i * rh
        good = robust == "partial"
        b.append(f'<rect x="{x0}" y="{y}" width="900" height="{rh - 6}" class="rule" '
                 f'fill="none" stroke-width="1"/>')
        b.append(f'<rect x="{x0}" y="{y}" width="4" height="{rh - 6}" '
                 f'class="{"acc" if good else "alert"}"/>')
        b.append(text(x0 + 18, y + 22, name, "ink", 12.5, weight="700"))
        b.append(text(x0 + 18, y + 40, "break: " + brk, "ink3", 9.6, mono=True))
        b.append(text(x0 + 300, y + 30, embed, "ink2", 10.4))
        label = {"no": "no", "partial": "partial only"}[robust]
        cls = "acc" if good else "alert"
        b.append(text(x0 + 520, y + 30, label, cls, 11, weight="700", mono=True))

    ny = y0 + len(rows) * rh + 10
    b.append(f'<rect x="40" y="{ny}" width="900" height="70" class="accs" fill="none" '
             f'stroke-width="1.4"/>')
    b.append(text(56, ny + 24, "THE POSTURE", "acc", 10.5, weight="700", mono=True))
    b.append(text(56, ny + 45,
                  "Best case is “partial”: every mark falls to regeneration or "
                  "denoising given enough effort, and open weights help the", "ink", 11))
    b.append(text(56, ny + 63,
                  "attacker. Treat a watermark as a score input, never a verdict. "
                  "Absence of a mark is no-information, not exoneration.", "ink", 11))
    b.append(text(40, H - 16, "Source: dossier/22_PROVENANCE_WATERMARK_LANDSCAPE.md "
                              "Tasks 1-2 · citations verified 2026-08-02", "ink3", 10, mono=True))
    return svg(W, H, "\n".join(b), "Watermark schemes, embedding point and the attack that removes each")


# ── F17 · synthetic-coverage by jurisdiction ─────────────────────────────────

def fig_synthetic_coverage():
    """
    Does an in-force statute reach fully-synthetic, identity-free sexual content
    (case (a)), as opposed to only real / identity-based content (case (b))?

    Extends fig12's top-right red cell into the legal axis, and visualises the
    proposed covers_synthetic tracker field. See
    dossier/22_PROVENANCE_WATERMARK_LANDSCAPE.md Task 4.
    """
    # H clears the footer below the callout box: rows end at ny=436, the box is
    # 72 tall (→508), footer at H-16. 548 leaves a clean gap; 500 put the footer
    # inside the box. Look at the render, not just the XML parse.
    W, H = 980, 548
    b = [title_block(40, 42, "Who covers fully-synthetic, identity-free abuse imagery",
                     "The hardest case to detect is also the least covered in law. "
                     "Only EN VIGOR + “cubre” is citable coverage.")]

    # cov: cubre / no_cubre / parcial / sin_verificar · in_force bool
    rows = [
        ("🇵🇪 Perú", "Ley 32314", True, "cubre", "deepfake child content named; AI aggravating", "acc"),
        ("🇺🇸 EE.UU.", "TAKE IT DOWN Act", True, "cubre", "explicitly covers AI-generated content", "acc"),
        ("🇲🇽 México", "Ley Olimpia federal", True, "no_cubre", "its own gap field: real content only", "alert"),
        ("🇲🇽 México", "Reforma 199 Septies", False, "cubre*", "*only if enacted — EN COMISIÓN, not law", "alert"),
        ("🇦🇷 Argentina", "Ley Olimpia AR", True, "sin_verificar", "text not checked for synthetic reach", "ink3"),
        ("🇵🇦 Panamá", "Ley Olimpia PA", True, "sin_verificar", "open question pa-synthetic-coverage", "ink3"),
        ("🇪🇺 UE", "DSA / Dir. 2024/1385", True, "parcial", "takedown leverage, not a criminal definition", "ink2"),
        ("🌎 OEA", "Ley Modelo MESECVI", False, "sin_verificar", "model instrument; check synthetic clause", "ink3"),
    ]

    x0, y0, rh = 40, 108, 40
    b.append(text(x0, y0 - 12, "JURISDICTION", "ink3", 8.6, weight="600", mono=True))
    b.append(text(x0 + 300, y0 - 12, "IN FORCE?", "ink3", 8.6, weight="600", mono=True))
    b.append(text(x0 + 410, y0 - 12, "COVERS SYNTHETIC?", "ink3", 8.6, weight="600", mono=True))

    for i, (juris, inst, in_force, cov, note, cls) in enumerate(rows):
        y = y0 + i * rh
        if i % 2 == 0:
            b.append(f'<rect x="{x0}" y="{y - 12}" width="900" height="{rh}" '
                     f'class="softf" opacity="0.30"/>')
        b.append(text(x0, y, juris, "ink", 11, weight="700"))
        b.append(text(x0 + 92, y, inst, "ink2", 10.4))
        b.append(text(x0 + 300, y, "EN VIGOR" if in_force else "NOT LAW",
                      "acc" if in_force else "alert", 9.2, weight="700", mono=True))
        b.append(text(x0 + 410, y, cov, cls, 10, weight="700", mono=True))
        b.append(text(x0 + 548, y, note, "ink3", 9.6))

    ny = y0 + len(rows) * rh + 8
    b.append(f'<rect x="40" y="{ny}" width="900" height="72" class="alerts" fill="none" '
             f'stroke-width="1.4" stroke-dasharray="5 4"/>')
    b.append(text(56, ny + 23, "THE GAP", "alert", 10.5, weight="700", mono=True))
    b.append(text(56, ny + 44,
                  "Only Peru and the US cover identity-free synthetic abuse imagery "
                  "in force. Mexico’s in-force law covers real content only;", "ink", 11))
    b.append(text(56, ny + 62,
                  "the fix is in committee. This is the case with no hash to match "
                  "and, in most of the region, no statute to route to.", "ink", 11))
    b.append(text(40, H - 16, "Proposed covers_synthetic field · "
                              "dossier/22_PROVENANCE_WATERMARK_LANDSCAPE.md Task 4 · "
                              "values subject to SCHEMA.md owner", "ink3", 9.5, mono=True))
    return svg(W, H, "\n".join(b), "Synthetic-content legal coverage by jurisdiction")


FIGURES = {
    "fig1-fpr-models.svg": fig_fpr_models,
    "fig2-precision-prevalence.svg": fig_precision,
    "fig3-cost-structure.svg": fig_cost,
    "fig4-custody-boundary.svg": fig_architecture,
    "fig5-disciplines.svg": fig_disciplines,
    "fig6-hash-breaks-timeline.svg": fig_timeline,
    "fig7-routing-authorities.svg": fig_routing,
    "fig8-country-status.svg": fig_country_status,
    "fig9-exploitation-pipeline.svg": fig_pipeline,
    "fig10-hard-rules.svg": fig_hard_rules,
    "fig11-three-branches.svg": fig_three_branches,
    "fig12-synthetic-media-quadrants.svg": fig_synthetic_quadrants,
    "fig13-biometric-custody.svg": fig_biometric_custody,
    "fig14-deck-claim-audit.svg": fig_deck_audit,
    "fig15-global-status.svg": fig_global_status,
    "fig16-watermark-robustness.svg": fig_watermark_robustness,
    "fig17-synthetic-coverage.svg": fig_synthetic_coverage,
}

if __name__ == "__main__":
    import xml.etree.ElementTree as ET

    OUT.mkdir(parents=True, exist_ok=True)
    failed = []
    for name, fn in FIGURES.items():
        content = fn()
        # Parse every figure before writing it. An SVG that is not well-formed
        # XML renders as a broken-image icon in GitHub and in the browser, and
        # nothing else in the pipeline would catch it.
        try:
            ET.fromstring(content)
        except ET.ParseError as err:
            failed.append(f"{name}: {err}")
            continue
        (OUT / name).write_text(content)
        print(f"  wrote docs/figures/{name}")

    if failed:
        print("\n✖ malformed SVG, not written:")
        for f in failed:
            print("   ", f)
        raise SystemExit(1)
    print(f"\n{len(FIGURES)} figures written, all well-formed.")
