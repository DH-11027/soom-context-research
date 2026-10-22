"""Plot the 18 recorded post-hoc cells; never run a selector or a new probe.

The plotted cost is the stored P7 proxy, not elapsed time or LLM expenditure.
All segments simply connect recorded observations; no curve is fitted.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/soom-phase07-mpl")

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, MultipleLocator

HERE = Path(__file__).resolve().parent
CHEAP = "#0072B2"
DEEP = "#009E73"
EVICTION = "#D55E00"
OVERSIZED = "#73568E"
INK = "#263544"


def percent_tick(value, _position):
    return "0%" if value == 0 else f"{value:+.0f}%"


def load_cells(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["posthoc"] is True
    assert data["independent_evaluation"] is False
    assert data["cell_count"] == len(data["cells"]) == 18
    assert data["queries_per_cell"] == 8
    for cell in data["cells"]:
        actual = 100 * (cell["cache_proxy"] / cell["fresh_proxy"] - 1)
        assert math.isclose(actual, cell["proxy_change_percent"], abs_tol=1e-9)
    return data


def style_axis(ax):
    ax.set_facecolor("white")
    ax.set_axisbelow(True)
    ax.grid(axis="y", color="#DCE2E8", linewidth=0.75)
    ax.axhline(0, color="#657384", linewidth=1.1, linestyle=(0, (4, 3)), zorder=1)
    ax.yaxis.set_major_formatter(FuncFormatter(percent_tick))
    ax.yaxis.set_major_locator(MultipleLocator(25))
    ax.tick_params(colors=INK, labelsize=10, length=4)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#ABB5C0")
        ax.spines[side].set_linewidth(0.8)


def plot(data, output_dir):
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 10.5,
        "axes.labelcolor": INK, "text.color": INK,
        "axes.titleweight": "bold", "svg.hashsalt": "soom-phase07-posthoc-boundary",
        "savefig.facecolor": "white",
    })
    fig, (left, right) = plt.subplots(1, 2, figsize=(14.6, 7.3),
                                     gridspec_kw={"width_ratios": [1.08, 1]})
    fig.subplots_adjust(left=0.075, right=0.975, top=0.77, bottom=0.23, wspace=0.24)
    fig.suptitle("Post-hoc constructed probe; not holdout, no timing",
                 x=0.075, y=0.96, ha="left", fontsize=19, fontweight="bold")
    fig.text(0.075, 0.895,
             "18 observed cells, 8 repeated queries per cell  |  "
             "P7 change relative to a fresh, uncached run",
             ha="left", fontsize=11, color="#536171")

    for ax in (left, right):
        style_axis(ax)
        ax.set_ylabel("P7 proxy change (%)", labelpad=8)
        ax.set_xlabel("Quoted source text (UTF-8 bytes)", labelpad=10)

    left.set_title("A  Observed source-length conditions", loc="left", fontsize=13, pad=14)
    left.set_xscale("log")
    left.set_xlim(40, 100000)
    left.set_ylim(-25, 137)
    for mode, color, marker in (("cheap", CHEAP, "o"), ("deep", DEEP, "s")):
        cells = sorted((c for c in data["cells"] if c["mode"] == mode),
                       key=lambda c: c["quote_utf8_bytes"])
        left.plot([c["quote_utf8_bytes"] for c in cells],
                  [c["proxy_change_percent"] for c in cells],
                  color=color, marker=marker, markersize=5.5, linewidth=1.35,
                  markeredgecolor="white", markeredgewidth=0.65,
                  label=f"{mode.capitalize()} path ({len(cells)} cells)", zorder=3)
    left.legend(loc="upper right", frameon=False, fontsize=10)
    left.text(0.025, 0.045, "Negative = lower proxy cost", transform=left.transAxes,
              fontsize=9.3, color="#477061")
    left.annotate("Capacity boundary\nexpanded at right",
                  xy=(65060, 75.3096272195706), xycoords="data",
                  xytext=(0.46, 0.53), textcoords="axes fraction", fontsize=9.5,
                  ha="left", va="center", color="#536171",
                  arrowprops={"arrowstyle": "->", "color": "#8793A0", "lw": 0.9})

    right.set_title("B  Capacity boundary: deep path", loc="left", fontsize=13, pad=14)
    targets = (65057, 65060, 65279, 65282)
    boundary = sorted((c for c in data["cells"]
                       if c["mode"] == "deep" and c["quote_utf8_bytes"] in targets),
                      key=lambda c: c["quote_utf8_bytes"])
    assert [c["quote_utf8_bytes"] for c in boundary] == list(targets)
    right.plot([c["quote_utf8_bytes"] for c in boundary],
               [c["proxy_change_percent"] for c in boundary],
               color="#768692", linewidth=1.1, linestyle=(0, (3, 2)), zorder=2)
    regions = {"both_fit": (DEEP, "o"), "mutual_eviction": (EVICTION, "s"),
               "quote_oversized": (OVERSIZED, "D")}
    for cell in boundary:
        color, marker = regions[cell["region"]]
        right.scatter(cell["quote_utf8_bytes"], cell["proxy_change_percent"],
                      s=65, marker=marker, color=color, edgecolor="white",
                      linewidth=0.8, zorder=4)
    right.set_xlim(65035, 65310)
    right.set_ylim(-25, 108)
    right.set_xticks([65050, 65100, 65150, 65200, 65250, 65300])
    right.xaxis.set_major_formatter(FuncFormatter(lambda value, _pos: f"{value:,.0f}"))
    right.tick_params(axis="x", labelsize=9)

    point = {c["quote_utf8_bytes"]: c for c in boundary}
    right.annotate("65,057 bytes\n-12.2333%\nBoth entries fit",
                   xy=(65057, point[65057]["proxy_change_percent"]),
                   xytext=(16, 8), textcoords="offset points", ha="left", va="bottom",
                   fontsize=9, color=DEEP,
                   bbox={"facecolor": "white", "edgecolor": "none", "pad": 1.5})
    right.annotate("65,060 bytes\n+75.3096%\nMutual eviction",
                   xy=(65060, point[65060]["proxy_change_percent"]),
                   xytext=(12, 13), textcoords="offset points", ha="left", va="bottom",
                   fontsize=9, color=EVICTION)
    right.annotate("65,279 bytes\n+75.3086%",
                   xy=(65279, point[65279]["proxy_change_percent"]),
                   xytext=(-12, 16), textcoords="offset points", ha="right", va="bottom",
                   fontsize=9, color=EVICTION)
    right.annotate("65,282 bytes\n+50.1589%\nQuote is oversized",
                   xy=(65282, point[65282]["proxy_change_percent"]),
                   xytext=(-14, -12), textcoords="offset points", ha="right", va="top",
                   fontsize=9, color=OVERSIZED)
    right.annotate("+3 source bytes\n-12.2333% to +75.3096%",
                   xy=(65058.5, 34), xycoords="data",
                   xytext=(0.32, 0.30), textcoords="axes fraction",
                   ha="left", va="center", fontsize=9.5,
                   bbox={"boxstyle": "round,pad=0.45", "fc": "#F4F6F8", "ec": "#D8DFE6"},
                   arrowprops={"arrowstyle": "->", "color": "#8793A0", "lw": 0.9})

    fig.text(0.075, 0.13,
             "P7 change = 100 x (cache_proxy / fresh_proxy - 1). "
             "Positive values mean more proxy cost; these are not latency or LLM-cost measurements.",
             fontsize=9.7, ha="left", color="#536171")
    fig.text(0.075, 0.085,
             "Points are recorded observations; connecting segments are visual guides only. "
             "No fitted curve or additional experiment. Source: posthoc/results.json.",
             fontsize=9.7, ha="left", color="#536171")
    output_dir.mkdir(parents=True, exist_ok=True)
    metadata = {"Title": "Post-hoc constructed probe; not holdout, no timing",
                "Description": "Observed P7 proxy changes from the 18 recorded Phase07 post-hoc cells."}
    fig.savefig(output_dir / "cost_boundary.png", dpi=180, metadata=metadata)
    fig.savefig(output_dir / "cost_boundary.svg", metadata={**metadata, "Date": None})
    svg_path = output_dir / "cost_boundary.svg"
    svg_path.write_text("\n".join(line.rstrip() for line in
                                svg_path.read_text(encoding="utf-8").splitlines()) + "\n",
                        encoding="utf-8")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=HERE / "posthoc" / "results.json")
    parser.add_argument("--output-dir", type=Path, default=HERE / "figures")
    args = parser.parse_args()
    data = load_cells(args.results)
    plot(data, args.output_dir)
    print(json.dumps({"observed_cells": len(data["cells"]),
                      "files": [str(args.output_dir / "cost_boundary.png"),
                                str(args.output_dir / "cost_boundary.svg")]}, indent=2))


if __name__ == "__main__":
    main()
