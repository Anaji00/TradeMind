import React, { useEffect, useRef, useState } from "react";
import {
    createChart,
    type IChartApi,
    type CandlestickData,
    type Time,
} from "lightweight-charts";
import type { Candle } from "../services/api";
import {
    useCandleStream,
    type CandleStreamMessage,
} from "../hooks/useCandleStream";

interface ChartPanelProps {
    symbol: string;
    initialCandles: Candle[];
    /**
     * Resolution for the WebSocket stream. If undefined, live streaming
     * is disabled and only the initial candles are shown.
     */
    resolution?: string;
}

/**
 * Renders a candlestick chart using lightweight-charts and optionally
 * listens for live candle updates over WebSocket.
 */
const ChartPanel: React.FC<ChartPanelProps> = ({
    symbol,
    initialCandles,
    resolution,
}) => {
    const containerRef = useRef<HTMLDivElement | null>(null);
    const [series, setSeries] =
        useState<ReturnType<IChartApi["addCandlestickSeries"]> | null>(null);
    const [lastPattern, setLastPattern] = useState<string>("");

    // Initialize chart
    useEffect(() => {
        if (!containerRef.current) return;

        const container = containerRef.current;
        const chartInstance: IChartApi =createChart(container, {
            width: container.clientWidth,
            height: container.clientHeight || 400,
            layout: {
                background: { color: "#020617" },
                textColor: "#e5e7eb",
            },
            grid: {
                vertLines: { color: "#1f2933" },
                horzLines: { color: "#1f2933" },
            },
            timeScale: {
                borderColor: "#1f2933",
            },
            rightPriceScale: {
                borderColor: "#1f2933",
            },
        });

        const candlestickSeries = chartInstance.addCandlestickSeries({
            upColor: "#22c55e",
            downColor: "#ef4444",
            borderUpColor: "#22c55e",
            borderDownColor: "#ef4444",
            wickUpColor: "#22c55e",
            wickDownColor: "#ef4444",
        });

        setSeries(candlestickSeries);

        const handleResize = () => {
            if (!containerRef.current) return;
            chartInstance.applyOptions({
                width: containerRef.current.clientWidth,
                height: containerRef.current.clientHeight || 400,
            });
        };

        window.addEventListener("resize", handleResize);

        return () => {
            window.removeEventListener("resize", handleResize);
            chartInstance.remove();
        };
    }, []);

    // Apply initial candles
    useEffect(() => {
        if (!series) return;

        const data: CandlestickData[] = initialCandles.map((c) => ({
            time: c.t as Time, // backend already gives unix seconds
            open: c.o,
            high: c.h,
            low: c.l,
            close: c.c,
        }));

        series.setData(data);
    }, [initialCandles, series]);

    // Live updates via WebSocket, if resolution is provided
    useCandleStream(symbol, resolution, (msg: CandleStreamMessage) => {
        if (!series) return;
        const { candle, patterns } = msg;

        const bar: CandlestickData = {
            time: candle.t as Time,
            open: candle.o,
            high: candle.h,
            low: candle.l,
            close: candle.c,
        };

        series.update(bar);

        if (patterns.length > 0) {
            const displayPatterns = patterns.map((p) =>
                p === "gravestone_doji" ? "inverse doji" : p
            );
            setLastPattern(displayPatterns.join(", "));
        }
    });

    return (
        <div className="flex flex-col gap-2">
            <div
                ref={containerRef}
                className="h-[400px] w-full rounded-lg border border-slate-700 bg-slate-950"
            />
            <div className="text-sm text-slate-200">
                <span className="font-semibold">{symbol}</span>{" "}
                {lastPattern
                    ? `→ Latest pattern: ${lastPattern}`
                    : "→ Waiting for a candle pattern..."}
            </div>
        </div>
    );
};

export default ChartPanel;
