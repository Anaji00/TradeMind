import { useEffect } from "react";
import { type Candle } from "../services/api";


export interface CandleStreamMessage {
    type: "candle";
    symbol: string;
    resolution: string;
    candle: Candle;
    patterns: string[];
}


/**
 * Hook that opens a WebSocket to the backend and calls `onMessage`
 * whenever a new candle + patterns arrives.
 */

export function useCandleStream(
    symbol: string | null,
    resolution: string | undefined,
    onMessage: (message: CandleStreamMessage) => void
): void {
    useEffect(() => {
        if (!symbol || !resolution) return;
        const protocol = window.location.protocol === "https:" ? "wss" : "ws";
        const url = `${protocol}://localhost:8000/ws/candles/${encodeURIComponent(
            symbol
        )}?resolution=${encodeURIComponent(resolution)}`;

        const ws = new WebSocket(url);

        ws.onopen = () => {
            console.log("WebSocket opened", url);
        };

        ws.onmessage = (event: MessageEvent) => {
            try {
                const data = JSON.parse(event.data) as CandleStreamMessage;
                if (data.type === "candle") {
                    onMessage(data);
                } 
            } catch (err) {
                console.error("Error parsing candle from message", err);
            }
        
        };

        ws.onerror = (event) => {
            console.error("WebSocket error", event);
        };

        ws.onclose = () => {
            console.log("WebSocket closed", url);
        };
        return () => {
            ws.close();
        };
    

    }, [symbol, resolution, onMessage]);

}