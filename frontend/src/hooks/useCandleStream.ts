import { useEffect } from "react";
import { Candle } from "../services/api";


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
    symbol: string,
    resolution: string,
    onMessage: (message: CandleStreamMessage) => void
) {
    useEffect(() => {
        const url = `ws://localhost:8000/ws/candles/${symbol}?resolution=${resolution}`;
        const ws = new WebSocket(url);

        ws.onopen = () => {
            console.log("WebSocket opened", url);
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data) as CandleStreamMessage;
                if (data.type === "candle") {
                    onMessage(data);
                } 
            } catch (err) {
                console.error("Error parsing message", err);
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