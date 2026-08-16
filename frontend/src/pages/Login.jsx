import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import * as api from "../api/client";
import "./Auth.css";

export default function Login() {
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault(); setError(null);
    if (!firstName.trim() || !lastName.trim()) { setError("Both names are required."); return; }
    setLoading(true);
    try {
      const data = await api.login(firstName.trim(), lastName.trim());
      login(data.token, data.userId, `${data.firstName} ${data.lastName}`);
      navigate("/dashboard");
    } catch (err) { setError(err.data?.message || err.message); }
    finally { setLoading(false); }
  }

  return (
    <div className="auth">
      <h1 className="auth__title">Login</h1>
      <p className="auth__sub">Enter your name to continue</p>
      <form className="auth__form" onSubmit={handleSubmit}>
        <label className="auth__field"><span>First Name</span>
          <input type="text" value={firstName} onChange={e=>setFirstName(e.target.value)} autoFocus />
        </label>
        <label className="auth__field"><span>Last Name</span>
          <input type="text" value={lastName} onChange={e=>setLastName(e.target.value)} />
        </label>
        {error && <p className="auth__error">{error}</p>}
        <button type="submit" className="auth__submit" disabled={loading}>
          {loading ? "Logging in…" : "Continue"}
        </button>
      </form>
      <p className="auth__switch">New here? <Link to="/register">Register</Link></p>
    </div>
  );
}
