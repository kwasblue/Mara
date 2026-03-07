from pathlib import Path
import pandas as pd

from robot_host.research.replay import SessionReplay

def main():
    jsonl = Path("logs/short_session.jsonl")
    outdir = Path("logs/artifacts")
    outdir.mkdir(parents=True, exist_ok=True)

    df = SessionReplay(str(jsonl)).to_dataframe()

    # focus on ack events for latency stats
    acks = df[df["event"] == "cmd.ack"].copy()

    # p50/p95/p99 on last_latency_ms
    if "last_latency_ms" in acks.columns and len(acks) > 0:
        p50 = acks["last_latency_ms"].quantile(0.50)
        p95 = acks["last_latency_ms"].quantile(0.95)
        p99 = acks["last_latency_ms"].quantile(0.99)
        print("p50/p95/p99 (ms):", p50, p95, p99)

    # export tables
    acks.to_csv(outdir / "acks.csv", index=False)

    try:
        acks.to_parquet(outdir / "acks.parquet", index=False)
    except Exception as e:
        print("Parquet export failed (need pyarrow):", e)

    print("Wrote:", outdir / "acks.csv")

if __name__ == "__main__":
    main()
