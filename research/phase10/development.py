"""Known Phase09 streams at predetermined horizons. Never opens Phase10 holdout."""
from copy import deepcopy
from bridge import P9, load, save_gzip

HORIZONS = (1, 4, 12, 36)

def build():
    original = load(P9 / "data/holdout.json.gz")
    result = []
    for stream in original:
        for horizon in HORIZONS:
            out = {"id": "cal-" + stream["id"] + "-h" + str(horizon),
                   "family": stream["family"], "base_stream": stream["id"],
                   "split": "known_phase09_calibration", "horizon": horizon, "steps": []}
            for index in range(horizon):
                step = deepcopy(stream["steps"][index % len(stream["steps"])])
                step["step_id"] = out["id"] + "-s" + str(index)
                out["steps"].append(step)
            result.append(out)
    assert len(result) == 144 and sum(len(s["steps"]) for s in result) == 1908
    return result

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    save_gzip(args.output, build())
    print("144 derived calibration streams /1908 prefixes; 36 known base streams, not independent 144 conversations.")

