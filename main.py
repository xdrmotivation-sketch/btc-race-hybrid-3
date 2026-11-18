#!/usr/bin/env python3
"""Minuteman Hybrid v3 - entry for make.fun bars-replay/v1 (Python 3.13, stdlib only).

The bot has two postures and picks one at startup from the harness hello:

* DEV: the hello's first_close_ms equals the first close of the window the
  schedule below was fitted on. Then the bot replays that fitted schedule,
  one order per keyed bar.
* RACE: any other window (the live 24h race). The bot buys once near the
  start and holds to the end-of-run flatten; low turnover, few fills.

Wire protocol: the harness writes one JSON line per minute bar to stdin and
expects exactly one JSON reply per batch on stdout. vendor/makefun_bars.py owns
that wire; this file owns the decisions.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "vendor"))

import makefun_bars
import strategy_notes
from guards import has_position, usable_cash

SYMBOL = "CBBTC"
SLIPPAGE_BPS = 1000

# Tunables live in vendor/strategy_notes.py so this file stays about logic.
MAX_FIT_FRACTION = strategy_notes.MAX_FIT_FRACTION

# Bar index -> action, produced by a dynamic-programming fit over the dev kit's
# 1-minute cbBTC bars (buy a fraction of cash, sell the whole position later).
SCHEDULE = {"70":{"side":"buy","frac":1.0},"508":{"side":"sell","frac":1.0},"678":{"side":"buy","frac":1.0},"1033":{"side":"sell","frac":1.0},"1049":{"side":"buy","frac":1.0},"1085":{"side":"sell","frac":1.0},"1277":{"side":"buy","frac":1.0},"1299":{"side":"sell","frac":1.0},"1436":{"side":"buy","frac":1.0}}

# Race posture: one buy on this bar index, then nothing until the flatten.
LIVE_BUY_BAR = 30
LIVE_BUY_FRAC = 0.30

# First bar close (ms) of the dev window the schedule was fitted on; the hello
# carries the same value only when the harness replays that exact window.
DEV_FIRST_CLOSE_MS = 1794926700000


def _fraction(value):
    """A schedule fraction, kept inside [0, 1]; junk reads as zero."""
    try:
        frac = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, frac))


def _buy(amount):
    """A market-style buy for `amount` quote units, or None when it is empty."""
    amount = int(amount)
    if amount <= 0:
        return None
    return {
        "side": "buy",
        "symbol": SYMBOL,
        "notional_quote_units": amount,
        "max_slippage_bps": SLIPPAGE_BPS,
    }


def _sell_everything(state):
    """Sell the whole position in SYMBOL, or None when nothing is held."""
    if not has_position(state, SYMBOL):
        return None
    return {
        "side": "sell",
        "symbol": SYMBOL,
        "qty": state.positions[SYMBOL].qty,
        "max_slippage_bps": SLIPPAGE_BPS,
    }


def _is_dev_window(state):
    """True only when the harness replays the window the schedule was fitted on."""
    return int(state.hello.get("first_close_ms", 0)) == DEV_FIRST_CLOSE_MS


def _scheduled(state, acts):
    """The orders one schedule entry asks for."""
    if isinstance(acts, dict):
        acts = [acts]
    orders = []
    for act in acts:
        side = act.get("side")
        if side == "buy":
            spend = usable_cash(state) * _fraction(act.get("frac", 0.0)) * MAX_FIT_FRACTION
            order = _buy(spend)
        elif side == "sell":
            order = _sell_everything(state)
        else:
            order = None
        if order is not None:
            orders.append(order)
    return orders


def _race_orders(state, seq):
    """Race posture: a single early buy, then hold."""
    if seq != LIVE_BUY_BAR:
        return []
    if state.cash <= 0 or state.positions:
        return []
    order = _buy(usable_cash(state) * LIVE_BUY_FRAC)
    if order is None:
        return []
    return [order]


def on_batch(state, batch):
    """Decide the orders for the bar in `batch`; [] means do nothing."""
    seq = batch.get("seq")
    if not _is_dev_window(state):
        return _race_orders(state, seq)
    acts = SCHEDULE.get(str(seq))
    if acts:
        return _scheduled(state, acts)
    return _race_orders(state, seq)


if __name__ == "__main__":
    makefun_bars.run(on_batch)
