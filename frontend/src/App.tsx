import {useEffect, useState} from "react";
import { type Candle, fetchHistoricalCandles } from "./services/api";
import ChartPanel from "./components/ChartPanel";

const DEFAULT_SYMBOL = "NVDA";


function App() {
  const [symbol] = useState<string>(DEFAULT_SYMBOL);
  const [candles, setCandles] = useState<Candle[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);


  useEffect(() => {
    async function load() {
      try {
        setLoading(true);
        setError(null);
        const data = await fetchHistoricalCandles(symbol, 120, "1");
        setCandles(data);
      } catch (err) {
      console.log(err);
      setError("Failed to load candles from backend");

      } finally {
        setLoading(false);
      }
    }
    load();
  }, [symbol]);

  return (
    <div
      style={{
        minHeight: "100vh",
        backgroundColor: "#020617",
        color: "#e5e7eb",
        padding: "1rem",
      }}
    >
      <header
        style={{
          maxWidth: "960px",
          margin: "0 auto 1rem",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <h1 style={{ fontSize: "1.25rem", fontWeight: 600}}>TradeMind</h1>
        <div style={{ fontSize:"0.9rem", color: "#9ca3af"}}>
          Real-Time Candles & Pattern Loading
        </div>
      </header>

      <main style={{ maxWidth: "960 px", margin: "0 auto"}}>
        {error && (
          <div style={{ marginBottom: "0.75rem", color: "#f87171"}}>
            {error}
          </div>
        )}

        {loading ? (
          <div>Loading Candles....</div>
        ): candles.length === 0 ? (
          <div>No candles available for {symbol}</div>
        ) : (
          <ChartPanel symbol={symbol} initialCandles={candles} />
        )}
      </main>
      </div>
  );
}

export default App;