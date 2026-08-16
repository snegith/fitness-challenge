import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import "./Header.css";

export default function Header() {
  const { token, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <header className="header">
      <div className="header__inner wrap">
        <NavLink to={token ? "/dashboard" : "/leaderboard"} className="header__brand">
          NGOV
        </NavLink>
        <nav className="header__nav" aria-label="Main navigation">
          {token && (
            <>
              <NavLink to="/dashboard" className="header__link">Dashboard</NavLink>
              <NavLink to="/log" className="header__link">Log Activity</NavLink>
            </>
          )}
          <NavLink to="/leaderboard" className="header__link">Leaderboard</NavLink>
          <NavLink to="/help" className="header__link">Help</NavLink>
        </nav>
        <div className="header__actions">
          {token ? (
            <button className="header__logout" onClick={handleLogout}>Log Out</button>
          ) : (
            <NavLink to="/login" className="header__link header__link--cta">Login</NavLink>
          )}
        </div>
      </div>
    </header>
  );
}
