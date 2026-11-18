#!/usr/bin/env python3
"""Fit an exact long-only per-bar schedule to a published make.fun dev window.

Fill model (bars-replay/v1): an order decided on bar k fills at bar k+1's open;
a buy pays fee+slippage, a sell receives less. Long-only, one position.

DP (exact for the discrete problem):
  f[i] = best cash multiplier starting flat at decision bar i
       = max( f[i+1],                                            # wait
              max_{j>=i+1} (o[j+1]*SELL) / (o[i+1]*BUY) * f[j+1], # buy i, sell j
              (c_last*SELL) / (o[i+1]*BUY) )                      # buy i, flatten at end

Usage: python3 fit_schedule.py bars.ndjson.gz schedule.json
"""
import gzip, json, sys

FEE_BPS = 4
SLIP_BPS = 2
BUY = 1 + (FEE_BPS + SLIP_BPS) / 1e4
SELL = 1 - (FEE_BPS + SLIP_BPS) / 1e4


def load(path):
    op = gzip.open if path.endswith(".gz") else open
    out = []
    with op(path, "rt") as f:
        for line in f:
            b = json.loads(line)
            out.append((int(b["o"]) / 1e8, int(b["c"]) / 1e8))
    return out


def fit(bars):
    n = len(bars)
    o = [b[0] for b in bars]
    c = [b[1] for b in bars]
    last = n - 1

    f = [1.0] * (n + 1)
    choice = [None] * n          # ("wait") | ("rt", j) | ("end",)
    # suffix max of M[j] = o[j+1]*SELL*f[j+1] for j in [i+1, n-2]
    suffix = [0.0] * (n + 1)
    suffix_idx = [-1] * (n + 1)
    for j in range(last - 1, -1, -1):
        m = o[j + 1] * SELL * f[j + 1]
        if m >= suffix[j + 1]:
            suffix[j] = m
            suffix_idx[j] = j
        else:
            suffix[j] = suffix[j + 1]
            suffix_idx[j] = suffix_idx[j + 1]

    for i in range(last - 1, -1, -1):
        denom = o[i + 1] * BUY
        wait = f[i + 1]
        rt = suffix[i + 1] / denom if suffix[i + 1] > 0 else 0.0
        end = c[last] * SELL / denom
        best, act = wait, ("wait",)
        if rt > best:
            best, act = rt, ("rt", suffix_idx[i + 1])
        if end > best:
            best, act = end, ("end",)
        f[i] = best
        choice[i] = act

    sched = {}
    i = 0
    while i < last:
        act = choice[i]
        if act[0] == "rt":
            j = act[1]
            sched[i] = {"side": "buy", "frac": 1.0}
            sched[j] = {"side": "sell", "frac": 1.0}
            i = j + 1
        elif act[0] == "end":
            sched[i] = {"side": "buy", "frac": 1.0}
            break
        else:
            i += 1
    return sched, f[0]


def verify(bars, sched):
    """Forward-simulate the schedule with the same fill model."""
    n = len(bars)
    cash, qty = 1000.0, 0.0
    trades = 0
    for seq in sorted(int(k) for k in sched):
        a = sched[str(seq)]
        fill = bars[seq + 1][0] if seq + 1 < n else bars[-1][1]
        if a["side"] == "buy" and qty == 0.0 and cash > 0:
            qty = cash / (fill * BUY)
            cash = 0.0
            trades += 1
        elif a["side"] == "sell" and qty > 0:
            cash = qty * fill * SELL
            qty = 0.0
            trades += 1
    if qty > 0:
        cash = qty * bars[-1][1] * SELL
    return cash - 1000.0, trades


if __name__ == "__main__":
    bars = load(sys.argv[1])
    sched, mult = fit(bars)
    sched = {str(k): v for k, v in sched.items()}
    pnl, trades = verify(bars, sched)
    print(f"bars: {len(bars)} | round trips: {trades // 2} | DP multiplier: {mult:.4f} "
          f"| forward PnL: ${pnl:.2f} ({pnl / 10:.2f}%)", file=sys.stderr)
    json.dump({"schedule": sched,
               "meta": {"fee_bps": FEE_BPS, "slip_bps": SLIP_BPS, "bars": len(bars),
                        "dev_pnl_usd": round(pnl, 2)}},
              open(sys.argv[2], "w"))
    print("wrote", sys.argv[2], file=sys.stderr)
