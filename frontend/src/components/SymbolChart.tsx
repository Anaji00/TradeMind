import React, { useEffect, useState, type ChangeEvent } from "react";
import {
    type Preset,
    type Provider,
    type Candle,
    fetchCandlesByPreset,
} from "../services/api";
import ChartPanel from "./ChartPanel";
import { useDebounce } from "../hooks/useDebounce";
import Spinner from "./Spinner";

const PRESETS: Preset[] = ["1D", "5D", "1M", "3M", "6M", "1Y", "YTD", "ALL"];

interface SymbolChartProps {
    /** Default symbol to load on first render. */
    defaultSymbol?: string;
}

/**
 * Small helper to decide if / which resolution to use for streaming
 * based on the selected preset.
 */

function resolutionForPreset(preset: Preset): string | undefined {
    switch (preset) {
        case "1D":
            return "1";
        case "5D":
            return "5";
        default:
            return undefined
    }
}

const SymbolChart: React.FC<SymbolChartProps> = ({ defaultSymbol = "NVDA" }) => {
    const [symbol, setSymbol] = useState<string>(defaultSymbol);
    const [preset, setPreset] = useState<Preset>("1D");
    const [provider, setProvider] = useState<Provider>("auto");
    const [candles, setCandles] = useState<Candle[]>([]);
    const [loading, setLoading] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    const debouncedSymbol = useDebounce(symbol, 400);
    const effectiveSymbol = debouncedSymbol.trim().toUpperCase();

    useEffect(() => {
        if (!effectiveSymbol) {
            setCandles([]);
            setError(null);
            return;
        }
        let cancelled = false;
        const load = async () => {
            try {
                setLoading(true);
                setError(null);
                const data = await fetchCandlesByPreset(
                    effectiveSymbol,
                    preset,
                    provider
                );
                if (!cancelled) {
                    setCandles(data);
                };
            } catch (err: unknown) {
                if (!cancelled) {
                    const message =
                        err instanceof Error
                            ? err.message
                            : "Failed to load candles.";
                    setError(message);
                    setCandles([]);
                }
            } finally {
                if (!cancelled) {
                    setLoading(false);
                }
            }
        };
        load();

        return () => {
            cancelled = true;
        };
    }, [effectiveSymbol, preset, provider]);

    const handleSymbolChange = (e: ChangeEvent<HTMLInputElement>) => {
        setSymbol(e.target.value);
    };
    const streamingResolution = resolutionForPreset(preset);

    return (
        <div className="space-y-4">
            {/* Controls row */}
            <div className="flex flex-wrap items-center gap-3 rounded-lg border border-slate-800 bg-slate-900/60 px-4 py-3">
                {/* Symbol input */}
                <div className="flex items-center gap-2">
                    <label
                        htmlFor="symbol-input"
                        className="text-xs font-medium uppercase tracking-wide text-slate-400"
                    >
                        Symbol
                    </label>
                    <input
                        id="symbol-input"
                        type="text"
                        value={symbol}
                        onChange={handleSymbolChange}
                        className="w-28 rounded-md border border-slate-700 bg-slate-950 px-3 py-1 text-sm text-slate-100 placeholder:text-slate-500 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                        placeholder="NVDA"
                    />
                </div>
                {/* Timeframe buttons */}
                <div className="flex flex-wrap items-center gap-1">
                    {PRESETS.map((p) => {
                     const isActive = p === preset;
                     return (
                        <button
                        key = { p }
                        type = "button"
                        onClick = {() => setPreset(p)}
                        className = {`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                        isActive
                        ? "border-emerald-400 bg-emerald-500 text-slate-900"
                        : "border-slate-700 bg-slate-900 text-slate-200 hover:bg-slate-800"
                    }` }
                    >
                    {p}
                    </button>

                        );
                })}
            </div>
            {/* Provider select */}
            <div className="ml-auto flex items-center gap-2">
                <label
                    htmlFor="provider-select"
                    className="text-xs font-medium uppercase tracking-wide text-slate-400"
                >
                    Provider
                </label>
                <select
                    id="provider-select"
                    value={provider}
                    onChange={(e) => setProvider(e.target.value as Provider)}
                    className="rounded-md border border-slate-700 bg-slate-950 px-2 py-1 text-xs text-slate-100 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                    <option value="auto">Auto</option>
                    <option value="finnhub">Finnhub</option>
                    <option value="yahoo">Yahoo</option>
                </select>
            </div>
        </div>
        {/* Content / chart area */ }
    <div className="rounded-lg border border-slate-800 bg-slate-900/60 px-4 py-3">
        {!effectiveSymbol ? (
            <div className="text-sm text-slate-400">
                Enter a symbol to view the chart.
            </div>
        ) : loading ? (
            <div className="flex items-center gap-2 text-sm text-slate-400">
                <Spinner />
                <span> Loading candles...</span>
            </div>
        ) : error ? (
            <div className="rounded-md border border-red-500/40 bg-red-500/10 px-3 py-2 text-sm text-red-200">
                {error}
            </div>
        ) : candles.length === 0 ? (
            <div className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-300">
                No candles available for {effectiveSymbol}.
            </div>
        ) : (
            <ChartPanel
                symbol={effectiveSymbol}
                initialCandles={candles}
                resolution={streamingResolution}
            />
        )}

    </div>
    </div>

    );
    };
export default SymbolChart;



