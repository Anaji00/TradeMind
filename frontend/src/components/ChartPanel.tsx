import React, {useEffect, useRef, useState} from "react";
import {
    createChart, 
    type IChartApi,
    type CandlestickData,
    type Time,
} from "lightweight-charts"
import {type  Candle } from "../services/api";
import {type  CandleStreamMessage, useCandleStream } from "../hooks/useCandleStream";

interface ChartPanelProps {
    symbol: string;
    initialCandles: Candle[];
}

/**
 * Renders a candlestick chart and listens for live updates via WS.
 */

const ChartPanel: React.FC<ChartPanelProps> = ({ symbol, initialCandles }) => {
    const containerRef = useRef<HTMLDivElement | null>(null);
    const [chart, setChart] = useState<IChartApi | null>(null);
    const [series, setSeries] = 
        useState<ReturnType<IChartApi["addCandlestickSeries"]> | null>(null);
    const [lastPattern, setLastPattern] = useState<string>("");
    
    useEffect(() => {
        if (!containerRef.current) return;

        const chartInstance = createChart(containerRef.current, {
            width: containerRef.current.clientWidth,
            height: 400,
        });

        const candlestickSeries = chartInstance.addCandlestickSeries();
        setChart(chartInstance);
        setSeries(candlestickSeries);

        const handleResize = () => {
            if (containerRef.current) {
                chartInstance.applyOptions({
                    width: containerRef.current.clientWidth
                });
            }
        };

        window.addEventListener("resize", handleResize);

        return () => {
            window.removeEventListener("resize", handleResize);
            chartInstance.remove();
        };
    }, []);
    
    useEffect(() => {
        if (!series) return;

        const data: CandlestickData[] = initialCandles.map((c) => ({
            time: c.t as Time,
            open: c.o,
            high: c.h,
            low: c.l,
            close: c.c,
        }));

        series.setData(data);
    }, [initialCandles, series]);

    useCandleStream(symbol, "1", (msg: CandleStreamMessage) => {
        if (!series) return;
        const candle = msg.candle;


    

        const bar: CandlestickData = {
            time: candle.t as Time,
            open: candle.o,
            high: candle.h,
            low: candle.l,
            close: candle.c
        };

        series.update(bar);

        if (msg.patterns.length > 0) {
            const displayPatterns = msg.patterns.map((p) => 
                p === "gravestone_doji" ? "inverse doji" : p
        );
        setLastPattern(displayPatterns.join(", "));
        }
    
    });
    

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
      <div
        ref={containerRef}
        style={{
          width: "100%",
          border: "1px solid #334155",
          borderRadius: "8px",
        }}
      />
      <div style={{ fontSize: "0.9rem", color: "#e5e7eb" }}>
        <strong>{symbol}</strong>{" "}
        {lastPattern
          ? `→ Latest pattern: ${lastPattern}`
          : "→ Waiting for a candle pattern..."}
      </div>
    </div>
  );
};

export default ChartPanel;