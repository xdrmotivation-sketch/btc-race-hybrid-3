#!/usr/bin/env python3
"""Sanity-check the embedded dev schedule: orders well-formed, fractions sane."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "vendor"))
from strategy_notes import MAX_FIT_FRACTION  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_schedule(path):
    with open(path) as fh:
        return json.load(fh)["schedule"]


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sched = load_schedule(os.path.join(here, "schedule.json"))
    problems = []
    buys = sells = 0
    for bar, act in sorted(sched.items(), key=lambda kv: int(kv[0])):
        if act["side"] == "buy":
            buys += 1
            if act["frac"] > MAX_FIT_FRACTION:
                problems.append(f"bar {bar}: fraction {act['frac']} over the cap")
        elif act["side"] == "sell":
            sells += 1
        else:
            problems.append(f"bar {bar}: unknown side {act['side']}")
    if buys != sells:
        problems.append(f"unbalanced: {buys} buys vs {sells} sells")
    if problems:
        print("FAIL")
        for line in problems:
            print("-", line)
        sys.exit(1)
    print(f"OK: {buys} round trips, {len(sched)} scheduled bars")


if __name__ == "__main__":
    main()
