import { createContext, useContext, useState, useCallback } from "react";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem("token"));
  const [userId, setUserId] = useState(() => {
    const s = localStorage.getItem("userId");
    return s ? Number(s) : null;
  });
  const [userName, setUserName] = useState(() => localStorage.getItem("userName") || "");

  const login = useCallback((newToken, newUserId, name = "") => {
    localStorage.setItem("token", newToken);
    localStorage.setItem("userId", String(newUserId));
    if (name) localStorage.setItem("userName", name);
    setToken(newToken);
    setUserId(newUserId);
    setUserName(name);
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("token");
    localStorage.removeItem("userId");
    localStorage.removeItem("userName");
    setToken(null);
    setUserId(null);
    setUserName("");
  }, []);

  return (
    <AuthContext.Provider value={{ token, userId, userName, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be inside AuthProvider");
  return ctx;
}
