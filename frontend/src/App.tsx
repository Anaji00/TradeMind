import SymbolChart from "./components/SymbolChart";
import ExplorePage from "./components/ExplorePage";
import { 
  BrowserRouter,
  Routes,
  Route,
  Navigate,
  NavLink,
  Link 
} from "react-router-dom";
const DEFAULT_SYMBOL = "NVDA";


function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-950">
        <header className="border-b border-slate-800 bg-slate-950/80 px-4 py-3 shadow-sm">
          <Link to="/chart" className = "flex items-baseline gap-2">
            <h1 className="text-lg font-semibold tracking-light">
              TradeMind
            </h1>
            <span className="text-xs text-slate-400">
              Charts &amp; social, WIP
            </span>
          </Link>
          <nav className="flex gap-4 text-sm">
            <NavLink
              to="/chart"
              className={({ isActive }: { isActive: boolean }) =>
                isActive
                  ? "text-emerald-400 font-medium"
                  : "text-slate-300 hover:text-emerald-300"
              }
            >
              Chart
            </NavLink>
            <NavLink
              to="/explore"
              className={({ isActive }: { isActive: boolean }) =>
                isActive
                  ? "text-emerald-400 font-medium"
                  : "text-slate-300 hover:text-emerald-300"
              }
            >
              Explore
            </NavLink>
          </nav>
        </header>
      </div>

      <main className="mx-auto flex max-w-5xl flex-col gap-4 px-4 py-4">
        <Routes>
          <Route
            path="/" element={<Navigate to="/chart" replace />} />
          <Route
            path="/chart" element={<SymbolChart defaultSymbol={DEFAULT_SYMBOL} />} />
          <Route
            path="/explore" element={<ExplorePage />} />
          <Route
            path="*" element={<Navigate to="/chart" replace />} />
        </Routes>
      </main>
    </BrowserRouter>
  );
}

export default App;