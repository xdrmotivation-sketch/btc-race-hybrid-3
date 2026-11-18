"""Strategy notes and constants for the Minuteman Hybrid bot.

Kept beside the vendored wire shim so the entrypoint stays small: the numbers
here are the knobs the build tuned on the dev window.
"""

# Fees the replay charges on every fill (basis points).
FEE_BPS = 4
SLIPPAGE_MODEL_BPS = 2

# Schedule fits are re-derived per competition window; fractions above 0.55
# paid more in price impact on the 6 Nov window than they earned back.
MAX_FIT_FRACTION = 1.0

# Live race posture: the 2026-11-15 race showed fitted-DP bots bleeding
# -5..-7 percent live while low-turnover holders led the board, so the live
# mode buys once early and holds to the flatten.
LIVE_TURN = "hold"

# Price-impact guard: never send an order worth more than this share of the
# pool depth's last close without widening the slippage bound.
IMPACT_DEPTH_SHARE = 0.02
