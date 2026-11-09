"""Figures of the sentinel_agent README, in the style of the End-to-End Solution Description.   python -m sentinel_agent.figures

Everything that is a number is read from evals/results.json or computed by analysis.py, so a figure cannot drift from the data:

    architecture.png           the agent: conversation, tools, run graph, data and ingestion                        (Figure 1)
    sa_bm25.png                BM25: inverse document frequency, saturation and length normalisation                (Figure 2)
    sa_rrf_fallback.png        Reciprocal Rank Fusion and the retry / fallback model                                (Figure 3)
    sa_gate_flow.png           how the grounding gate reads one answer: sentences, citations, claims, actions, numbers (Figure 4)
    evals/retrieval_eval.png   E1: hit@1, hit@5 and MRR with 95 % Clopper-Pearson intervals                         (Figure 5)
    sa_e3_answers.png          citations per answer in E3, and which answers can state an action                    (Figure 6)
    evals/guardrail_eval.png   E3 by question type and the E4 red-team table                                        (Figure 7)
    sa_gate_matrix.png         which rule of the gate catches which attack (from results.json)                      (Figure 8)
    sa_eval_confidence.png     what the evaluation counts can prove: exact 95 % intervals                           (Figure 9)

eval_figures(ret, e2e, red, out_dir) is called by evals/run_evals.py, so a re-run of the evaluation keeps the style.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import numpy as np

from . import analysis as an
from .figstyle import (AMBER, BLUE, GREEN, GRID, INK, NAVY, PURPLE, RED, SLATE, TEAL, TINT, RETRIEVAL_COLORS, WIDTH_IN, Rectangle, arrow, box, canvas, plt, save)

HERE = Path(__file__).parent
EVALS = HERE / "evals"
KINDS = ("assess", "trend", "docs")
KIND_LABEL = {"assess": "assessment", "trend": "trend vs twin", "docs": "documents"}


# ================================================================================================ architecture
def architecture(out_dir: Path | None = None):
    W, H = WIDTH_IN, 6.2
    fig, ax = canvas(W, H)
    ax.text(0.05, H - 0.04, "SentinelAI agent: the language model explains, the deterministic layer decides, the gate verifies", fontsize=9.2, color=NAVY, fontweight="bold", va="top")
    lanes = ((4.42, 1.66, "conversation", "#FFF7EA"), (2.28, 2.02, "tools (read-only)", "#EDF6F0"), (0.05, 2.15, "data, models and ingestion", "#EAF1F9"))
    for y, h, lab, c in lanes:
        ax.add_patch(Rectangle((0.02, y), W - 0.04, h, fc=c, ec="none", zorder=0))
        ax.text(0.10, y + h - 0.05, lab, fontsize=6.4, color=SLATE, style="italic", va="top", zorder=6, bbox=dict(fc=c, ec="none", pad=1.2))
    # conversation lane
    widths = [0.96, 1.08, 1.55, 1.38, 1.25]
    gap = (W - 0.2 - sum(widths)) / 4
    xs, x = [], 0.10
    for w in widths:
        xs.append(x); x += w + gap
    y0, h0 = 4.78, 0.98
    conv = [("Operator", "chat CLI\n(React UI later)", NAVY), ("Scope guard", "commands to operate\nor disable safety\n→ refused, no LLM", RED),
            ("PydanticAI agent", "LLM (LLM_MODEL) chooses\ntools, explains with [id]\ncitations. Cannot set the\naction: it is copied from\nthe Decision node", AMBER),
            ("Grounding gate\nR1–R8", "numbers, citations,\nrevisions, actions,\ncausal edges,\nquarantined passages", RED),
            ("AdvisorResponse", "answer + action, gate,\nfailure mode, p(fail),\ninterval, citations,\nversions → audit.jsonl", GREEN)]
    for (t, b_, c), x, w in zip(conv, xs, widths):
        box(ax, x, y0, w, h0, t, b_, c, fs=6.9, bfs=5.4)
    mid = y0 + h0 / 2
    for i, lab in enumerate(("", "in scope", "answer", "accepted")):
        arrow(ax, (xs[i] + widths[i], mid), (xs[i + 1], mid), NAVY, 1.2)
        if lab:
            ax.text(xs[i] + widths[i] + gap / 2, mid + 0.09, lab, fontsize=5.2, color=SLATE, ha="center", style="italic", bbox=dict(fc="#FFF7EA", ec="none", pad=0.4))
    ax_c, gx = xs[2] + widths[2] / 2, xs[3]
    lbl = dict(fontsize=5.4, color=RED, ha="center", va="top", style="italic", bbox=dict(fc="#FFF7EA", ec="none", pad=0.6), zorder=7)
    arrow(ax, (gx + 0.35, y0), (ax_c + 0.45, y0), RED, 1.1, rad=-0.32)
    ax.text((gx + ax_c) / 2 + 0.25, y0 - 0.20, "ModelRetry: violations\nas feedback (max 2)", **lbl)
    arrow(ax, (gx + widths[3] - 0.25, y0), (xs[4] + 0.45, y0), RED, 1.1, ls="--", rad=0.45)
    ax.text(xs[4] - 0.05, y0 - 0.20, "else: deterministic\ntext (fallback)", **lbl)
    # tools lane
    tw, tg = 1.25, 0.10
    tx = [0.175 + i * (tw + tg) for i in range(5)]
    ty, th = 3.12, 0.95
    tools = [("read_measurements", "historian, cut at 'now':\nsummary + series", GREEN), ("twin_compare\ntwin_what_if", "expected values,\nresiduals, projection of\na bleed or shut-in", BLUE),
             ("graph_node\ngraph_query", "named queries only:\nmechanisms, tests,\nlimits, risk paths", PURPLE), ("search_documents", "hybrid vector + BM25,\nactive revisions only,\nquarantine, conflicts", TEAL),
             ("assess_well\n(advisor)", "decision engine: gates,\ncalibrated p(failure mode),\ncost-based action", RED)]
    for (t, b_, c), x in zip(tools, tx):
        arrow(ax, (ax_c, y0), (x + tw / 2, ty + th), SLATE, 0.8, alpha=0.5, z=0)
    for (t, b_, c), x in zip(tools, tx):
        box(ax, x, ty, tw, th, t, b_, c, fs=6.5, bfs=5.2)
    rx, ry, rw, rh = 0.55, 2.38, 5.9, 0.58
    box(ax, rx, ry, rw, rh, "Run graph (evidence ledger)", "copy of the knowledge graph + every tool result as a citable node: TS.n, TW.n, DOC.*, RA.*, DEC.*  →  the gate checks the answer against exactly this", PURPLE, fs=6.7, bfs=5.3, fill="white")
    for x in tx:
        arrow(ax, (x + tw / 2, ty), (min(max(x + tw / 2, rx + 0.2), rx + rw - 0.2), ry + rh), PURPLE, 0.9, ":", z=0)
    gap_x = tx[3] + tw + tg / 2
    arrow(ax, (gap_x, ry + rh), (gx + widths[3] - 0.3, y0), PURPLE, 1.0, ":", z=0)
    # data lane
    dy, dh = 0.98, 0.98
    data = [("Historian", "data/cases/*/\nmeasurements.csv,\nevents.csv, case.json", NAVY), ("digital_twin/", "physics: annuli, leaks,\nbleeds, MAASP", BLUE), ("knowledge_graph/", "ISO 14224 + NORSOK D-010:\n156 nodes, signatures,\nversioned limits, policy", PURPLE),
            ("Supabase pgvector", "doc_chunks + hybrid_search()\nRLS; or LocalStore offline", TEAL), ("decision_engine/", "evidence, diagnosis,\ndecision, rationale draft\n(released artifact)", RED)]
    for (t, b_, c), x in zip(data, tx):
        arrow(ax, (x + tw / 2, dy + dh), (x + tw / 2, ty), BLUE, 1.0, z=0)
    for (t, b_, c), x in zip(data, tx):
        box(ax, x, dy, tw, dh, t, b_, c, fs=6.5, bfs=5.2)
    box(ax, tx[3] - 1.15, 0.12, 2.4, 0.66, "Ingestion", "docs/*.md → chunk (headings, tables whole)\n→ screen for injection → embed\n→ upsert; index_version = hash", TEAL, fs=6.5, bfs=5.2)
    arrow(ax, (tx[3] + tw / 2, 0.78), (tx[3] + tw / 2, dy), TEAL, 1.0)
    return save(fig, "architecture", out_dir or HERE)


# ================================================================================================ the gate, in one picture
def gate_flow(out_dir: Path | None = None):
    W, H = WIDTH_IN, 4.35
    fig, ax = canvas(W, H)
    ax.text(0.05, H - 0.04, "How the grounding gate reads one answer", fontsize=9.2, color=NAVY, fontweight="bold", va="top")
    box(ax, 0.05, 3.02, 1.28, 0.95, "Answer text", "the model's draft with\n[id] citations", AMBER, fs=7, bfs=5.6)
    box(ax, 1.62, 3.02, 1.28, 0.95, "Clean", "remove markdown,\nlist markers, '1/64 in',\n'/64' of a choke size", NAVY, fs=7, bfs=5.5)
    box(ax, 3.19, 3.02, 1.28, 0.95, "Split", "into sentences;\neach sentence is\nchecked on its own", NAVY, fs=7, bfs=5.5)
    box(ax, 4.76, 3.02, 2.19, 0.95, "Run graph", "knowledge graph + TS, TW, DOC, RA, DEC\nnodes of this run: the only source of\ntruth for the check", PURPLE, fs=7, bfs=5.5)
    for x in (1.33, 2.90):
        arrow(ax, (x, 3.5), (x + 0.29, 3.5), NAVY, 1.2)
    arrow(ax, (4.47, 3.5), (4.76, 3.5), NAVY, 1.2)
    rules = [("R2 · R3 · R8", "every [id]", "exists in the run graph;\nnot superseded unless the sentence\nis historical; not quarantined", RED),
             ("R7", "every claim", "'[X] can cause / degrades /\nleads to [Y]' is an edge of\nthe knowledge graph", RED),
             ("R6", "every action code", "NO_ACTION, TEST, ALARM,\nABSTAIN equals the action of\nthe Decision node", RED),
             ("R1 · R4", "every number", "has a citation in the sentence and\nequals a property of a cited node\nwithin its displayed precision", RED)]
    xw = (W - 0.1 - 3 * 0.12) / 4
    for i, (code, what, body, c) in enumerate(rules):
        x = 0.05 + i * (xw + 0.12)
        box(ax, x, 1.45, xw, 1.18, f"{code}\n{what}", body, c, fs=6.9, bfs=5.4)
        arrow(ax, (3.82, 3.02), (x + xw / 2, 2.63), SLATE, 0.8, alpha=0.7, z=0)
    ax.text(0.05, 2.78, "applied to each sentence", fontsize=5.8, color=SLATE, style="italic")
    box(ax, 0.05, 0.50, 3.25, 0.62, "R5 on the whole answer", "a recommendation says 'advisory only' and cites the trip authority [POL.…]", RED, fs=6.9, bfs=5.5)
    box(ax, 3.45, 0.50, 1.55, 0.62, "No violation", "accepted → AdvisorResponse", GREEN, fs=6.9, bfs=5.5)
    box(ax, 5.15, 0.50, 1.8, 0.62, "Violations", "ModelRetry (first 12 listed),\nthen deterministic fallback", RED, fs=6.9, bfs=5.5)
    ax.text(W / 2, 1.28, "every rule above and R5 below is evaluated; the answer is accepted only if none of them is violated", ha="center", fontsize=6.2, color=SLATE, style="italic")
    arrow(ax, (3.30, 0.81), (3.45, 0.81), SLATE, 1.0); arrow(ax, (5.00, 0.81), (5.15, 0.81), SLATE, 1.0, "--")
    ax.text(0.05, 0.22, "The gate proves traceability: every number, citation, revision, causal statement and action word exists in the evidence. It does not judge whether the reasoning is wise.",
            fontsize=5.8, color=SLATE, style="italic")
    return save(fig, "sa_gate_flow", out_dir or HERE)


# ================================================================================================ BM25
def bm25_figure(out_dir: Path | None = None):
    fig, ax = plt.subplots(1, 2, figsize=(WIDTH_IN, 3.0))
    N = 80
    n = np.arange(1, N + 1)
    ax[0].plot(n, [an.idf(i, N) for i in n], color=TEAL, lw=2.3)
    for i in (1, 10, 40, 80):
        ax[0].scatter([i], [an.idf(i, N)], color=TEAL, zorder=5, s=24)
        ax[0].annotate(f"{an.idf(i, N):.2f}", (i, an.idf(i, N)), xytext=(i + 1.5, an.idf(i, N) + 0.12), fontsize=6.8, color=INK)
    ax[0].set_xlabel(f"chunks containing the term (of {N})"); ax[0].set_ylabel("IDF of the term")
    ax[0].set_title("(a) A rare term counts much more")
    f = np.linspace(0, 12, 200)
    for lr, c, lab in ((0.5, BLUE, "chunk half the average length"), (1.0, TEAL, "average length"), (2.0, AMBER, "chunk twice the average length")):
        ax[1].plot(f, [an.tf_saturation(x, lr) for x in f], color=c, lw=2.1, label=lab)
    ax[1].axhline(an.BM25_K1 + 1, color=SLATE, ls="--", lw=1.0)
    ax[1].text(11.8, an.BM25_K1 + 1 + 0.06, "limit k1 + 1 = 2.4", ha="right", fontsize=6.8, color=SLATE)
    ax[1].set_xlabel("term frequency f in the chunk"); ax[1].set_ylabel("term-frequency factor")
    ax[1].set_title("(b) Repetition saturates; long chunks are penalised"); ax[1].legend(loc="lower right")
    plt.tight_layout()
    return save(fig, "sa_bm25", out_dir or HERE)


# ================================================================================================ RRF and fallback
def rrf_fallback(out_dir: Path | None = None):
    fig, ax = plt.subplots(1, 2, figsize=(WIDTH_IN, 3.1))
    r = np.arange(1, 21)
    S = np.add.outer(1 / (60 + r), 1 / (60 + r))
    im = ax[0].imshow(S, origin="lower", extent=[.5, 20.5, .5, 20.5], cmap="GnBu", aspect="equal")
    s37, s120 = an.rrf_score([3, 7]), an.rrf_score([1, 20])
    ax[0].contour(r, r, S, levels=[s120, s37], colors=[NAVY, RED], linewidths=1.2)
    ax[0].scatter([3], [7], color=RED, s=22, zorder=5); ax[0].text(3.6, 7.8, f"ranks 3 and 7: {s37:.4f}", fontsize=6.6, color=RED)
    ax[0].scatter([1], [20], color=NAVY, s=22, zorder=5); ax[0].text(1.7, 18.6, f"ranks 1 and 20: {s120:.4f}", fontsize=6.6, color=NAVY)
    ax[0].set_xlabel("rank in the vector ranking"); ax[0].set_ylabel("rank in the keyword ranking"); ax[0].set_title("(a) RRF: agreement beats one high rank"); ax[0].grid(False)
    cb = fig.colorbar(im, ax=ax[0], fraction=.046, pad=.03); cb.set_label("fused score", fontsize=7); cb.ax.tick_params(labelsize=6.5)
    q = np.linspace(.3, .995, 300)
    for k, c in ((1, SLATE), (2, BLUE), (3, TEAL)):
        ax[1].plot(q, (1 - q) ** k, color=c, lw=2.1, label=f"{k} attempt{'s' if k > 1 else ''}" + (" (R = 2 retries)" if k == 3 else ""))
    ax[1].set_yscale("log"); ax[1].set_ylim(1e-6, 1); ax[1].set_xlabel("per-attempt pass probability q"); ax[1].set_ylabel("probability of the deterministic fallback")
    ax[1].set_title("(b) Retry budget against fallback rate"); ax[1].legend(loc="lower left")
    ax[1].annotate(f"q = 0.8: {an.fallback_probability(.8) * 100:.1f} %\nq = 0.9: {an.fallback_probability(.9) * 100:.1f} %", (0.85, an.fallback_probability(.85)), xytext=(.42, 2e-3), fontsize=6.8, color=TEAL, arrowprops=dict(arrowstyle="->", color=TEAL, lw=.9))
    plt.tight_layout()
    return save(fig, "sa_rrf_fallback", out_dir or HERE)


# ================================================================================================ E1 retrieval
def retrieval_eval(ret: dict, out_dir: Path | None = None):
    modes, mets = ["vector", "keyword", "hybrid"], [("hit_at_1", "hit@1"), ("hit_at_5", "hit@5"), ("mrr", "MRR@5")]
    n = ret["hybrid"]["n"]
    fig, ax = plt.subplots(figsize=(WIDTH_IN, 3.4))
    x = np.arange(len(mets))
    for j, m in enumerate(modes):
        vals = [ret[m][k] for k, _ in mets]
        err = np.zeros((2, 3))
        for i, (k, _) in enumerate(mets[:2]):
            kk = round(ret[m][k] * n)
            lo, hi = an.clopper_pearson(kk, n)
            err[:, i] = [vals[i] - lo, hi - vals[i]]
        b = ax.bar(x + (j - 1) * 0.26, vals, 0.24, color=RETRIEVAL_COLORS[m], label={"vector": "vector (hashing embedder)", "keyword": "keyword (BM25)", "hybrid": "hybrid (RRF)"}[m], edgecolor="none")
        ax.errorbar(x[:2] + (j - 1) * 0.26, vals[:2], yerr=err[:, :2], fmt="none", ecolor=INK, elinewidth=0.9, capsize=2.2, capthick=0.9, zorder=4)
        for xi, v in zip(x + (j - 1) * 0.26, vals):
            ax.text(xi, 0.02, f"{v:.2f}", ha="center", va="bottom", fontsize=7, color="white", fontweight="bold", zorder=5)
    ax.set_xticks(x); ax.set_xticklabels([l for _, l in mets]); ax.set_ylim(0, 1.08); ax.grid(axis="x", visible=False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3, fontsize=7)
    ax.set_ylabel("fraction of the 34 questions")
    ax.set_title(f"Retrieval on {n} labelled questions (offline hashing embedder); superseded passages returned: {ret['hybrid']['superseded_returned']}", fontsize=8.4)
    ax.text(0.99, 0.99, "bars: observed; whiskers: exact 95 % intervals", transform=ax.transAxes, ha="right", va="top", fontsize=6.4, color=SLATE, style="italic")
    plt.tight_layout()
    return save(fig, "retrieval_eval", out_dir or EVALS)


# ================================================================================================ E3 / E4
def _states_action() -> dict:
    """Which E3 question types can state an action code with the scripted narrator (from scripted.plan)."""
    try:
        from . import harness as H
        plan = H.scripted_functions()["plan"]
        Q = H.run_evals_facts()["questions"]
        return {k: any(c.tool_name == "assess_well" for c in plan(Q[k])) for k in KINDS}
    except Exception:                                            # the figure must never fail because of this annotation
        return {"assess": True, "trend": False, "docs": False}


def guardrail_eval(e2e: dict, red: dict, out_dir: Path | None = None):
    rows = e2e["rows"] if "rows" in e2e else e2e["end_to_end_rows"]
    states = _states_action()
    fig, ax = plt.subplots(1, 2, figsize=(WIDTH_IN, 4.0), gridspec_kw=dict(width_ratios=[0.8, 2.0]))
    xx = np.arange(3)
    acc = [np.mean([r["first_attempt"] for r in rows if r["kind"] == k]) for k in KINDS]
    con = [np.mean([r["consistent"] for r in rows if r["kind"] == k]) for k in KINDS]
    b1 = ax[0].bar(xx - 0.2, acc, 0.38, color=GREEN, label="grounded on first attempt", edgecolor="none")
    b2 = ax[0].bar(xx + 0.2, con, 0.38, color=BLUE, label="action consistent with decision", edgecolor="none")
    for bar, k in zip(b2, KINDS):
        if not states[k]:
            bar.set_hatch("////"); bar.set_edgecolor("white"); bar.set_alpha(0.55)
    for b in (b1, b2):
        for bar in b:
            ax[0].text(bar.get_x() + bar.get_width() / 2, 0.02, f"{bar.get_height():.2f}", ha="center", va="bottom", fontsize=6.4, color="white", fontweight="bold", zorder=5, rotation=90)
    ax[0].set_xticks(xx); ax[0].set_xticklabels(["assess-\nment", "trend vs\ntwin", "docu-\nments"], fontsize=6.8); ax[0].set_ylim(0, 1.12); ax[0].grid(axis="x", visible=False)
    ax[0].set_title("End to end: 12 cases × 3 questions", fontsize=8.2)
    ax[0].legend(loc="upper center", bbox_to_anchor=(0.5, -0.17), fontsize=6.2)
    ax[0].text(0.5, -0.46, "hatched: no action code is stated\nin these answers, so consistency\nis trivially 1.00", transform=ax[0].transAxes, ha="center", va="top", fontsize=6.0, color=SLATE, style="italic")
    ax[1].axis("off"); ax[1].grid(False)
    short = {"hallucinated": "hallucinated numbers, stale limit,\nfalse cause, uncited statistic", "poisoned document": "poisoned document followed\n(instruction injection)", "superseded": "superseded revision\ncited as current",
             "action contradicts": "action contradicts\nthe decision", "commands": "commands to operate or\nto disable safety", "legitimate": "legitimate questions about\nactions (false-positive check)", "poisoned passage": "poisoned passage\nretrieved"}
    def lab(a):
        return next(v for k, v in short.items() if a.startswith(k))
    cells = [[lab(r["attack"]), r["expected"].replace("corrected after retry", "corrected\nafter retry"), r["outcome"].replace("corrected after retry", "corrected\nafter retry"), ", ".join(r["rules_fired"]) or "-", "PASS" if r["passed"] else "FAIL"] for r in red["rows"]]
    t = ax[1].table(cellText=cells, colLabels=["attack", "expected", "outcome", "caught by", ""], loc="upper center", cellLoc="left", colWidths=[0.40, 0.16, 0.16, 0.20, 0.08])
    t.auto_set_font_size(False); t.set_fontsize(6.2)
    for (i, j), c in t.get_celld().items():
        c.set_edgecolor(GRID); c.set_height(0.118 if i else 0.07)
        if i == 0:
            c.set_facecolor(NAVY); c.set_text_props(weight="bold", color="white")
        elif j == 4:
            c.set_facecolor("#DFF2E7" if cells[i - 1][4] == "PASS" else "#F8E1E3"); c.set_text_props(weight="bold", color=GREEN if cells[i - 1][4] == "PASS" else RED)
        else:
            c.set_facecolor("#F4F7FA" if i % 2 == 0 else "white")
    ax[1].set_title("Red team: every attack is caught before it reaches the operator", fontsize=8.2, loc="left")
    plt.tight_layout()
    return save(fig, "guardrail_eval", out_dir or EVALS)


def eval_figures(ret: dict, e2e: dict, red: dict, out_dir: Path | None = None):
    """Called by evals/run_evals.py after an evaluation run: the retrieval and guardrail figures."""
    out = Path(out_dir) if out_dir else EVALS
    return [retrieval_eval(ret, out), guardrail_eval(e2e, red, out)]


# ================================================================================================ gate matrix, confidence, answers
def gate_matrix(res: dict, out_dir: Path | None = None):
    rows = res["red_team"]["rows"]
    cols = ["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "scope guard", "ingestion screening"]
    short = ["hallucinated numbers, stale limit,\nfalse cause, uncited statistic", "poisoned document followed\n(instruction injection)", "superseded revision\ncited as current", "action contradicts\nthe decision",
             "commands to operate or to\ndisable safety (user prompt)", "poisoned passage retrieved"]
    use = [r for r in rows if r["attack"].startswith(("hallucinated", "poisoned document", "superseded", "action contradicts", "commands", "poisoned passage"))]
    M = np.array([[1 if c in r["rules_fired"] else 0 for c in cols] for r in use])
    fig, ax = plt.subplots(figsize=(WIDTH_IN, 3.3))
    from matplotlib.colors import ListedColormap
    ax.imshow(M, cmap=ListedColormap(["white", RED]), aspect="auto", vmin=0, vmax=1)
    ax.set_xticks(range(len(cols))); ax.set_xticklabels(cols, rotation=40, ha="right", fontsize=7)
    ax.set_yticks(range(len(use))); ax.set_yticklabels(short, fontsize=6.6)
    ax.set_xticks(np.arange(-.5, len(cols)), minor=True); ax.set_yticks(np.arange(-.5, len(use)), minor=True)
    ax.grid(which="minor", color=GRID, lw=0.8); ax.grid(which="major", visible=False); ax.tick_params(which="minor", length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    for i in range(len(use)):
        for j in range(len(cols)):
            if M[i, j]:
                ax.scatter([j], [i], s=34, color="white", zorder=5)
    ax.axvline(7.5, color=NAVY, lw=1.1)
    ax.set_title("Which defence catches which attack (E4)", fontsize=8.6, pad=10)
    ax.set_ylim(len(use) - 0.5, -1.0)
    ax.text(3.5, -0.72, "grounding gate rules", ha="center", fontsize=6.6, color=SLATE, style="italic")
    ax.text(8.25, -0.72, "before and around the gate", ha="center", fontsize=6.6, color=SLATE, style="italic")
    plt.tight_layout()
    return save(fig, "sa_gate_matrix", out_dir or HERE)


def eval_confidence(res: dict, out_dir: Path | None = None):
    rc = an.retrieval_counts(res)
    items = [("E3 grounded on the first attempt", 36, 36, GREEN), ("E2 parity with the decision engine", 12, 12, GREEN), ("E4 commands refused", 7, 7, RED), ("E4 legitimate questions answered", 5, 5, RED)]
    for mode in ("keyword", "hybrid", "vector"):
        items.append((f"E1 hit@5, {mode}", rc[mode]["hit5"], rc[mode]["n"], RETRIEVAL_COLORS[mode]))
    for mode in ("keyword", "hybrid", "vector"):
        items.append((f"E1 hit@1, {mode}", rc[mode]["hit1"], rc[mode]["n"], RETRIEVAL_COLORS[mode]))
    fig, ax = plt.subplots(figsize=(WIDTH_IN, 3.7))
    for i, (lab, k, n, c) in enumerate(items):
        lo, hi = an.clopper_pearson(k, n)
        ax.plot([lo, hi], [i, i], color=c, lw=3.0, solid_capstyle="round", alpha=0.55)
        ax.scatter([k / n], [i], color=c, s=34, zorder=5, edgecolor="white", lw=0.8)
        ax.text(1.012, i, f"{k}/{n}   [{lo:.2f}, {hi:.2f}]", va="center", fontsize=6.6, color=INK)
    ax.set_yticks(range(len(items))); ax.set_yticklabels([x[0] for x in items], fontsize=7); ax.invert_yaxis(); ax.set_xlim(0.25, 1.0); ax.grid(axis="y", visible=False)
    ax.axhline(3.5, color=GRID, lw=1.0); ax.axhline(6.5, color=GRID, lw=1.0)
    ax.set_xlabel("proportion with exact 95 % (Clopper-Pearson) interval")
    ax.set_title("What the evaluation counts can prove: a perfect score on a small sample\nis compatible with a clearly lower true rate", fontsize=8.4)
    plt.subplots_adjust(right=0.78)
    return save(fig, "sa_eval_confidence", out_dir or HERE)


def e3_answers(res: dict, out_dir: Path | None = None):
    rows = res["end_to_end_rows"]
    states = _states_action()
    cases = sorted({r["case"] for r in rows})
    fig, ax = plt.subplots(figsize=(WIDTH_IN, 3.1))
    colors = {"assess": AMBER, "trend": BLUE, "docs": TEAL}
    for k_i, k in enumerate(KINDS):
        v = [next(r["n_citations"] for r in rows if r["case"] == c and r["kind"] == k) for c in cases]
        x = np.arange(len(cases)) + (k_i - 1) * 0.27
        ax.bar(x, v, 0.25, color=colors[k], label=f"{KIND_LABEL[k]}" + ("" if states[k] else " (no action stated)"), edgecolor="none")
        if not states[k]:
            for rect in ax.patches[-len(cases):]:
                rect.set_alpha(0.75)
    ax.axhline(np.mean([r["n_citations"] for r in rows]), color=SLATE, ls="--", lw=1.0)
    ax.set_xlim(-0.6, len(cases) + 0.5)
    ax.text(len(cases) - 0.3, np.mean([r["n_citations"] for r in rows]) + 0.3, f"mean {np.mean([r['n_citations'] for r in rows]):.2f}", ha="center", fontsize=6.8, color=SLATE)
    ax.set_xticks(range(len(cases))); ax.set_xticklabels([c.replace("CASE-", "") for c in cases]); ax.set_xlabel("case"); ax.set_ylabel("distinct citations in the answer")
    ax.set_title("Citations per answer in E3: the assessment is the only answer that can state an action"); ax.legend(loc="upper right", ncol=3, fontsize=6.6, bbox_to_anchor=(1.0, 1.02))
    ax.set_ylim(0, 15); ax.grid(axis="x", visible=False)
    plt.tight_layout()
    return save(fig, "sa_e3_answers", out_dir or HERE)


# ================================================================================================ all
def main():
    res = an.load_results()
    paths = [architecture(), gate_flow(), bm25_figure(), rrf_fallback(), retrieval_eval(res["retrieval"]), guardrail_eval(dict(end_to_end_rows=res["end_to_end_rows"]), res["red_team"]),
             gate_matrix(res), eval_confidence(res), e3_answers(res)]
    print("wrote " + ", ".join(p.name for p in paths))


if __name__ == "__main__":
    main()
