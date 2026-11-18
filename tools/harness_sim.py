#!/usr/bin/env python3
"""Local harness for a bars-replay/v1 bot: replays a published bars file through
the bot's stdin/stdout and reports net PnL with the kit's fill model.

Usage: python3 harness_sim.py <bars.ndjson.gz> <bot_dir> [--live]
"""
import gzip, json, subprocess, sys

FEE = 0.0004
SLIP = 0.0002


def main():
    bars_path, bot_dir = sys.argv[1], sys.argv[2]
    live = "--live" in sys.argv

    with gzip.open(bars_path, "rt") as f:
        bars = [json.loads(l) for l in f]
    n = len(bars)

    hello = {
        "type": "hello",
        "protocol": "agent-fun/bars-replay/v1",
        "seed": "0",
        "symbols": [{"symbol": "CBBTC",
                     "mint": "cbbtcf3aa214zXHbiAZQwf4122FBYbraNdFqgw4iMij",
                     "price_scale": 8, "qty_scale": 8}],
        "capital": {"quote": "USDC", "quote_units": str(1000 * 10**6),
                    "quote_scale": 6},
        "bar_interval": "1m",
        "first_close_ms": bars[0]["t"],
        "caps": {"max_open_positions": 1, "max_orders_per_bar": 10,
                 "max_weight_bps": 10000, "shorts": False, "leverage": False},
        "fees": {"fee_bps": 4, "slippage_bps": 2, "min_notional_quote_units": "1000000"},
        "latency_bars": 1,
    }

    proc = subprocess.Popen([sys.executable, "-P", "-s", "main.py"], cwd=bot_dir,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, bufsize=1)
    proc.stdin.write(json.dumps(hello) + "\n")
    proc.stdin.flush()

    cash = 1000 * 10**6   # quote raw (6 dp)
    qty = 0               # base raw (8 dp)
    trades = 0
    equity_curve = []

    for seq in range(n):
        b = bars[seq]
        msg = {
            "type": "batch", "seq": seq, "t": b["t"],
            "bars": [{"symbol": "CBBTC", "t": b["t"], "o": b["o"], "h": b["h"],
                      "l": b["l"], "c": b["c"], "o_depth": b["o_depth"],
                      "c_depth": b["c_depth"]}],
            "account": {"cash_quote_units": str(int(cash)),
                        "positions": ([{"symbol": "CBBTC", "qty": str(int(qty)),
                                        "cost_quote_units": str(int(qty * 1e6 / 1e8))}] if qty > 0 else []),
                        "equity_quote_units": str(int(cash + (qty * int(b["c"]) / 1e8 if qty else 0)))},
            "fills": [],
        }
        proc.stdin.write(json.dumps(msg) + "\n")
        proc.stdin.flush()
        line = proc.stdout.readline()
        if not line:
            err = proc.stderr.read()
            print("BOT DIED:", err[:800], file=sys.stderr)
            sys.exit(1)
        rep = json.loads(line)
        orders = rep.get("orders", []) or []

        # fills at next bar's open, with fee, slip and constant-product impact
        if seq + 1 < n:
            nb = bars[seq + 1]
            opx = int(nb["o"]) / 1e8
            depth = int(nb["o_depth"][0]) / 1e6
            for o in orders:
                if o.get("side") == "buy":
                    amt = int(o["notional_quote_units"]) / 1e6
                    if amt <= 0 or cash <= 0:
                        continue
                    amt = min(amt, cash / 1e6)
                    imp = amt / (depth / 2)
                    px = opx * (1 + FEE + SLIP + imp)
                    bought = (amt / px) * 1e8
                    qty += bought
                    cash -= int(amt * 1e6)
                    trades += 1
                elif o.get("side") == "sell" and qty > 0:
                    sell_qty = int(o.get("qty", 0))
                    if sell_qty <= 0:
                        sell_qty = int(qty)
                    sell_qty = min(sell_qty, int(qty))
                    proceeds = (sell_qty / 1e8) * opx * (1 - FEE - SLIP)
                    cash += int(proceeds * 1e6)
                    qty -= sell_qty
                    trades += 1

        equity_curve.append((cash + (qty * int(b["c"]) / 1e8 * 1e6 if qty else 0)) / 1e6)

    # flatten at last close
    if qty > 0:
        last_c = int(bars[-1]["c"]) / 1e8
        cash += int((qty / 1e8) * last_c * (1 - FEE - SLIP) * 1e6)
        qty = 0

    proc.stdin.write(json.dumps({"type": "done", "seq": n}) + "\n")
    proc.stdin.flush()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()

    final = cash / 1e6
    peak = max(equity_curve) if equity_curve else 1000
    mdd = min((e - peak) / peak for e in equity_curve) if equity_curve else 0
    print(f"final equity: ${final:.2f} | PnL: ${final - 1000:+.2f} "
          f"({(final - 1000) / 10:+.2f}%) | trades: {trades} | maxDD: {mdd * 100:.2f}%")


if __name__ == "__main__":
    main()
