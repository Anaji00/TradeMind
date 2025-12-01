import axios from "axios";

/**
 * Base URL for the backend FastAPI server. 
 */
export const API_BASE_URL = "http://localhost:8000";

/**
 * Candle represents a single OHLCV candle returned from the backend.
 *
 * - `t` is a Unix timestamp in seconds (UTC)
 * - `o` is the open price
 * - `h` is the high price
 * - `l` is the low price
 * - `c` is the close price
 * - `v` is the volume
 */
export interface Candle {
    t: number;
    o: number;
    h: number;
    l: number;
    c: number;
    v: number;
}

export type Preset = "1D" | "5D" | "1M" | "3M" | "6M" | "1Y" | "YTD" | "ALL";
export type Provider = "auto" | "finnhub" | "yahoo"; 


export async function fetchHistoricalCandles(
    symbol: string,
    minutes = 120,
    resolution: "1" | "5" | "15" | "30" | "60" = "1"
): Promise<Candle[]> {
    const res = await axios.get<Candle[]>(`${API_BASE_URL}/candles/history`, {
        params: {symbol, minutes, resolution},
    });
    return res.data;
}

/**
* High-level helper used by the timeframe buttons. Uses the backend
* `preset` parameter, and optionally a specific provider.
*/

export async function fetchCandlesByPreset(
    symbol: string,
    preset: Preset,
    provider: Provider = "auto"
): Promise<Candle[]> {
    try {
        const res = await axios.get<Candle[]>(`${API_BASE_URL}/candles/history`, {
            params: { symbol, preset, provider },
        });
        return res.data;
    } catch (error: unknown) {
        if (axios.isAxiosError(error) && error.response) {
            const status = error.response.status;
            const detail =
                (error.response.data as { detail?: string } | undefined)?.detail
            let message: string;
            switch (status) {
                case 400:
                    message =
                        detail ??
                        "Invalid range or parameters. Try a shorter range or higher timeframe.";
                    break;
                case 404:
                    message =
                        detail ??
                        "No candles found for this symbol and range. Try another symbol or timeframe.";
                    break;
                case 429:
                    message =
                        detail ??
                        "Rate limit exceeded. Please wait a moment before trying again.";
                    break;
                default:
                    message =
                        detail ?? `Unexpected error from server (status ${status}).`;
                    break;
            }
            throw new Error(message);
        }
        throw new Error("Network error or server is unreachable.");
    }
}