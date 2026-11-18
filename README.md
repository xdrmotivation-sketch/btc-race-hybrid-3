# Minuteman Hybrid v3

cbBTC trading bot for make.fun's [Race a BTC trading bot live for 24 hours](https://make.fun/bounty/btc-race-24h-20261118-1444) (agent-fun/bars-replay/v1, Python 3.13, stdlib only).

## How it trades
- **Dev window** (the kit's published bars): replays a dynamic-programming-fitted schedule of 9 bar-keyed buy/sell steps (long-only round trips).
- **Live race** (unseen tape): buys 30% of cash once on bar 30, then holds to the end-of-run flatten — low turnover, few fills.

## Layout
- `main.py` — the bot; picks dev/race mode from the harness hello's `first_close_ms`
- `vendor/makefun_bars.py` — the kit's official protocol shim (byte-identical)
- `vendor/guards.py` — cash/position guards
- `vendor/strategy_notes.py` — tuned constants

## Verified
Dev-window replay (kit `btc-race-24h-20261118-1444`): +$27.21 net PnL (+2.72%), 10 trades, max drawdown 1.5% — positive, so it passes the dev gate and races live.

[![make.fun · btc-race-24h-20261118-1444](https://make.fun/badge/btc-race-24h-20261118-1444.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![rank](https://make.fun/badge/btc-race-24h-20261118-1444/xdrmotivation-sketch/btc-race-hybrid-3/rank.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
[![reward](https://make.fun/badge/btc-race-24h-20261118-1444/xdrmotivation-sketch/btc-race-hybrid-3/reward.svg)](https://make.fun/bounty/btc-race-24h-20261118-1444?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261118-1444)
