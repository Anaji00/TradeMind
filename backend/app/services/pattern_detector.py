from __future__ import annotations

from typing import List, Optional
from app.models.candles import Candle


def classify_candle(latest: Candle, previous: Optional[Candle] = None)-> List[str]:
    """
    Basic pattern classifier for a single candle, optionally using previous candle.

    This is intentionally simple & transparent:
    - doji, gravestone_doji (inverse doji), dragonfly_doji
    - bullish_engulfing / bearish_engulfing
    - fallback: bullish / bearish / neutral
    """
    patterns = List[str] = []

    o = latest.o
    h = latest.h
    l = latest.l
    c = latest.c

    candle_range = max(h - l, 0.0000001)
    body = abs(c-o)
    upper_shadow = h - max(o,c)
    lower_shadow = min(o,c) - l

    body_ratio = body / candle_range
    upper_ratio = upper_shadow / candle_range
    lower_ratio = lower_shadow / candle_range

    # doji
    if body_ratio < 0.1:
        patterns.append("doji")

        if upper_ratio >= 0.6 and lower_ratio <= 0.1:
            patterns.append("gravestone_doji")

        elif lower_ratio >= 0.6 and upper_ratio <= 0.1:
            patterns.append("dragonfly_doji")

    # Engulfing patterns
    if previous is not None:
        prev_o = previous.o
        prev_c = previous.c
        prev_body = abs(prev_c - prev_o)


        if prev_body > 0 and body > prev_body * 1.1:
            # Bullish engulfing: previous red, current green, and current body fully
            # covers previous body.
            if (
                c > o and
                prev_c < prev_o and
                o < prev_c and
                c > prev_o
            ):
                patterns.append("bullish_engulfing")

            # Bearish engulfing: previous green, current red, and current body fully
            # covers previous body.
            if not patterns:
                if c>o:
                    patterns.append("bullish")
                elif c < o:
                    patterns.append("bearish")
                else:
                    patterns.append("neutral")

    return patterns




