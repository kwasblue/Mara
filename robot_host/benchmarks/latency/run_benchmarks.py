from pathlib import Path
import json
import pandas as pd
import matplotlib.pyplot as plt

from robot_host.research.replay import SessionReplay

def main():
    session = Path("logs/short_session.jsonl")
    outdir = Path("logs/benchmarks/latency")
    outdir.mkdir(parents=True, exist_ok=True)

    df = SessionReplay(str(session)).to_dataframe()
    acks = df[df["event"] == "cmd.ack"].copy()

    if len(acks) == 0 or "last_latency_ms" not in acks.columns:
        raise RuntimeError("No cmd.ack events with last_latency_ms found")

    lat = acks["last_latency_ms"].astype(float)

    metrics = {
        "n": int(lat.shape[0]),
        "p50_ms": float(lat.quantile(0.50)),
        "p95_ms": float(lat.quantile(0.95)),
        "p99_ms": float(lat.quantile(0.99)),
        "mean_ms": float(lat.mean()),
        "max_ms": float(lat.max()),
    }

    # Write metrics JSON
    with open(outdir / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    # Write metrics CSV (one row)
    pd.DataFrame([metrics]).to_csv(outdir / "metrics.csv", index=False)

    # Plot histogram
    plt.figure()
    plt.hist(lat, bins=30)
    plt.title("Command Latency Histogram (last_latency_ms)")
    plt.xlabel("Latency (ms)")
    plt.ylabel("Count")
    plt.tight_layout()
    plt.savefig(outdir / "latency_hist.png", dpi=150)
    plt.close()

    print("Wrote:", outdir)

if __name__ == "__main__":
    main()
