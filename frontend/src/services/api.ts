import axios from "axios";

export const API_BASE_URL = "http://localhost:8000";

export interface Candle {
    t: number;
    o: number;
    h: number;
    l: number;
    c: number;
    v: number;
}

export async function fetchHistoricalCandles(
    symbol: string,
    minutes = 120,
    resolution = "1"
): Promise<Candle[]> {
    const res = await axios.get<Candle[]>(`${API_BASE_URL}/candles/history`, {
        params: {symbol, minutes, resolution},
    });
    return res.data;
}