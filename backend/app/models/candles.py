from typing import List
from pydantic import BaseModel

class Candle(BaseModel):
    t: int
    o: float
    h: float
    l: float
    c: float
    v: float


class CandleWithPatterns(BaseModel):
    symbol: str
    resolution: str
    candle: Candle
    patterns: List[str]
