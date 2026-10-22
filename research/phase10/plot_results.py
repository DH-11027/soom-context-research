"""Optional publication figure from saved Phase10 results; no new experiment."""
import argparse
import json
from pathlib import Path
import hashlib
import math


def main(output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    here = Path(__file__).resolve().parent
    output.mkdir(parents=True, exist_ok=False)
    load = lambda p: json.loads(p.read_text())
    combined = load(here / "combined_results.json")
    predictions = {r["stream_id"]:r["predicted_delta_us"]["trace_ridge"]
                   for r in load(here / "results/predictions.json")["predictions"]}
    timing = [load(here / "results/timing.json"), load(here / "reproduction_timing.json")]
    extents = [100*v for t in timing for row in t["streams"]
               for v in row["summary"]["delta_interval_divided_by_fixed_fresh_median"]]
    extents += [100*predictions[row["stream_id"]]/row["summary"]["fresh_median_us"]
                for t in timing for row in t["streams"]]
    limits = (5*math.floor((min(extents)-2)/5), 5*math.ceil((max(extents)+2)/5))
    plt.rcParams.update({"font.family":"DejaVu Sans", "font.size":10,
                         "axes.spines.top":False,"axes.spines.right":False,
                         "svg.hashsalt":"soom-phase10-fixed-results"})
    fig = plt.figure(figsize=(12, 9.5), layout="constrained")
    grid = fig.add_gridspec(2, 2, height_ratios=[.8, 1.3])
    ax = fig.add_subplot(grid[0, :])
    models = ("trace_ridge", "zero_change", "per_query", "p8_calibrated")
    labels = ("Trace ridge", "Zero change", "Per query", "Calibrated P8")
    for index, (session, color) in enumerate((("primary", "#126a8d"), ("reproduction", "#76b4c4"))):
        values = [100*combined["numerical_errors"][session][m] for m in models]
        xs = [i + (index-.5)*.34 for i in range(4)]
        bars = ax.bar(xs, values, .32, label=session.capitalize(), color=color)
        ax.bar_label(bars, labels=[f"{v:.2f}%" for v in values], padding=4, fontsize=10)
    ax.axhline(10, color="#aa4b29", linestyle="--", linewidth=1,
               label="Prespecified absolute-error limit")
    ax.set_xticks(range(4), labels)
    ax.set_ylim(0, 26)
    ax.set_ylabel("Mean absolute error / fresh time (%)")
    ax.set_title("A. Numerical prediction passes in both sessions", loc="left", weight="bold")
    ax.legend(frameon=False, ncols=3, loc="upper left")
    ax.grid(axis="y", alpha=.15)
    ax.set_axisbelow(True)
    colors = {"slowdown":"#bd672b", "unresolved":"#717b86", "speedup":"#27856c"}
    for index, data in enumerate(timing):
        ax = fig.add_subplot(grid[1, index])
        for row in data["streams"]:
            s = row["summary"]
            x = 100*s["delta_over_fresh_median"]
            y = 100*predictions[row["stream_id"]]/s["fresh_median_us"]
            lo, hi = [100*v for v in s["delta_interval_divided_by_fixed_fresh_median"]]
            ax.plot([lo, hi], [y, y], color=colors[s["material_label"]], alpha=.35, linewidth=1)
            ax.scatter([x], [y], color=colors[s["material_label"]],
                       marker="^" if row["queries"]==64 else "o", s=35, alpha=.85,
                       edgecolors="white", linewidths=.4, zorder=3)
        ax.plot(limits, limits, color="#253a48", linestyle="--", linewidth=1)
        ax.axvspan(-3, 3, color="#d9e1e5", alpha=.35)
        ax.axhline(0, color="#909090", linewidth=.6)
        ax.axvline(0, color="#909090", linewidth=.6)
        ax.set_xlim(*limits)
        ax.set_ylim(*limits)
        ax.set_aspect("equal", adjustable="box")
        ax.set_xlabel("Observed paired time difference / fresh (%)")
        ax.set_ylabel("Frozen prediction / fresh (%)")
        counts = combined["material_label_counts"][data["session"]]
        ax.set_title(f"{'B' if index==0 else 'C'}. {data['session'].capitalize()}: {counts.get('speedup',0)} material speedups",
                     loc="left", weight="bold")
        ax.grid(alpha=.15)
        legend = [Line2D([0],[0],marker="o",linestyle="",color=colors[k],label=k.capitalize())
                  for k in ("slowdown","unresolved")]
        legend += [Line2D([0],[0],marker="^",linestyle="",color="#283747",label="64-step stream")]
        ax.legend(handles=legend,frameon=False,fontsize=9,loc="upper left")
    fig.suptitle("Phase10: accurate magnitude prediction; two-direction sign claim unresolved",fontsize=15,weight="bold")
    fig.supxlabel("48 fixed synthetic streams per session, equal-weight numerical error. Horizontal lines: individual cycle-bootstrap intervals.\n"
                  "Intervals are not simultaneous; fresh denominator is fixed. Complete-stream diagnostic features, not an online gate.",fontsize=9)
    fig.savefig(output / "phase10_results.png", dpi=180)
    fig.savefig(output / "phase10_results.svg", metadata={"Date":None})
    plt.close(fig)
    digest = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    receipt = {"matplotlib":matplotlib.__version__,
               "source_hashes":{str(p.relative_to(here)):digest(p) for p in
                                (here/"combined_results.json", here/"results/predictions.json",
                                 here/"results/timing.json",here/"reproduction_timing.json")},
               "figure_hashes":{p.name:digest(p) for p in sorted(output.iterdir())},
               "boundary":"Postfreeze descriptive figure only. No new timing, fitting, or inference."}
    (output / "receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",required=True,type=Path)
    main(parser.parse_args().output)
