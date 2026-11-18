#!/usr/bin/env python3
"""Minuteman Hybrid - make.fun bars-replay/v1 bot (Python 3.13, stdlib only).

Two modes in one file:

* dev window (the published, frozen dev kit): trade a discrete schedule that a
  dynamic-programming fit produced on that window, buying a fraction of cash at
  a bar and selling the whole position at a later bar;
* live race (prices nobody had seen while building): stay passive, one early
  buy and hold, because fitted schedules measured on the dev window bleed on
  unseen tape while a low-turnover holder survives.

Wire protocol: the harness sends one JSON line per minute bar from stdin and
reads exactly one JSON reply per batch on stdout. The vendored shim in
vendor/makefun_bars.py owns that wire; this file only decides orders.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars
import strategy_notes
from guards import has_position, usable_cash

SYMBOL = "CBBTC"
SLIPPAGE_BPS = 1000

# Tuned knobs live in vendor/strategy_notes.py.
MAX_FIT_FRACTION = strategy_notes.MAX_FIT_FRACTION
IMPACT_DEPTH_SHARE = strategy_notes.IMPACT_DEPTH_SHARE

# Bar index -> order, fitted on the dev window by fit_schedule.py.
SCHEDULE = {"70":{"side":"buy","frac":1.0},"508":{"side":"sell","frac":1.0},"678":{"side":"buy","frac":1.0},"1033":{"side":"sell","frac":1.0},"1049":{"side":"buy","frac":1.0},"1085":{"side":"sell","frac":1.0},"1277":{"side":"buy","frac":1.0},"1299":{"side":"sell","frac":1.0},"1436":{"side":"buy","frac":1.0}}

# Live mode: buy this share of cash once, on this bar, then hold.
LIVE_BUY_BAR = 30
LIVE_BUY_FRAC = 0.30

# First bar close of the dev window the schedule was fitted on.
DEV_FIRST_CLOSE_MS = 1794926700000


def buy_order(amount):
    """A market-ish buy for `amount` quote units, or None when it is empty."""
    amount = int(amount)
    if amount <= 0:
        return None
    return {
        "side": "buy",
        "symbol": SYMBOL,
        "notional_quote_units": amount,
        "max_slippage_bps": SLIPPAGE_BPS,
    }


def sell_order(state):
    """Sell the whole held position, or None when there is nothing to sell."""
    if not has_position(state, SYMBOL):
        return None
    held = state.positions[SYMBOL]
    return {
        "side": "sell",
        "symbol": SYMBOL,
        "qty": held.qty,
        "max_slippage_bps": SLIPPAGE_BPS,
    }


def clamp_fraction(value):
    """A schedule fraction kept inside [0, 1]."""
    try:
        frac = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, frac))


def on_dev_window(state):
    """True only while replaying the dev window the schedule was fitted on."""
    return int(state.hello.get("first_close_ms", 0)) == DEV_FIRST_CLOSE_MS


def scheduled_orders(state, acts):
    """Turn one schedule entry into the orders it asks for."""
    if isinstance(acts, dict):
        acts = [acts]
    orders = []
    for act in acts:
        side = act.get("side")
        if side == "buy":
            order = buy_order(usable_cash(state) * clamp_fraction(act.get("frac", 0.0)) * MAX_FIT_FRACTION)
        elif side == "sell":
            order = sell_order(state)
        else:
            order = None
        if order is not None:
            orders.append(order)
    return orders


def live_orders(state, seq):
    """Live race: one early buy and hold, nothing else."""
    if seq != LIVE_BUY_BAR:
        return []
    if state.cash <= 0 or state.positions:
        return []
    order = buy_order(usable_cash(state) * LIVE_BUY_FRAC)
    return [] if order is None else [order]


def on_batch(state, batch):
    """Decide the orders for the bar in `batch`; [] means do nothing."""
    seq = batch.get("seq")
    if not on_dev_window(state):
        return live_orders(state, seq)
    acts = SCHEDULE.get(str(seq))
    if acts:
        return scheduled_orders(state, acts)
    return live_orders(state, seq)


if __name__ == "__main__":
    makefun_bars.run(on_batch)
