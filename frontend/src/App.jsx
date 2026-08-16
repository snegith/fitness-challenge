import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import Header from "./components/Header";
import Register from "./pages/Register";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import Leaderboard from "./pages/Leaderboard";
import LogActivity from "./pages/LogActivity";
import Help from "./pages/Help";
import "./styles/global.css";

function Protected({ children }) {
  const { token } = useAuth();
  return token ? children : <Navigate to="/login" replace />;
}

function Guest({ children }) {
  const { token } = useAuth();
  return token ? <Navigate to="/dashboard" replace /> : children;
}

function AppRoutes() {
  const { token } = useAuth();
  return (
    <>
      <Header />
      <main className="wrap" style={{ paddingTop: "var(--s5)", paddingBottom: "var(--s7)" }}>
        <Routes>
          <Route path="/register" element={<Guest><Register /></Guest>} />
          <Route path="/login" element={<Guest><Login /></Guest>} />
          <Route path="/dashboard" element={<Protected><Dashboard /></Protected>} />
          <Route path="/log" element={<Protected><LogActivity /></Protected>} />
          <Route path="/leaderboard" element={<Leaderboard />} />
          <Route path="/help" element={<Help />} />
          <Route path="*" element={<Navigate to={token ? "/dashboard" : "/leaderboard"} replace />} />
        </Routes>
      </main>
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
