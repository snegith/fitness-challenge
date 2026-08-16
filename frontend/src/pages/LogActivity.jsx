import { useState } from "react";
import { useNavigate } from "react-router-dom";
import * as api from "../api/client";
import ScoreDisplay from "../components/ScoreDisplay";
import "./LogActivity.css";

const SPORTS = [
  { key: "running", label: "Running", type: "distance" },
  { key: "walking", label: "Walking", type: "distance" },
  { key: "cycling", label: "Cycling", type: "distance" },
  { key: "swimming", label: "Swimming", type: "duration" },
  { key: "gym", label: "Gym", type: "duration" },
  { key: "daily_steps", label: "Daily Steps", type: "steps" },
];

export default function LogActivity() {
  const [selected, setSelected] = useState(null);
  const [distance, setDistance] = useState("");
  const [hours, setHours] = useState("");
  const [minutes, setMinutes] = useState("");
  const [steps, setSteps] = useState("");
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const sport = SPORTS.find(s => s.key === selected);

  function reset() {
    setDistance(""); setHours(""); setMinutes(""); setSteps("");
    setError(null);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null); setResult(null);

    let payload = { sportType: selected };

    if (sport.type === "distance") {
      const km = parseFloat(distance);
      if (!km || km <= 0) { setError("Enter a distance greater than 0."); return; }
      payload.distanceKm = km;
    } else if (sport.type === "duration") {
      const h = parseInt(hours) || 0;
      const m = parseInt(minutes) || 0;
      const sec = h * 3600 + m * 60;
      if (sec < 0) { setError("Duration cannot be negative."); return; }
      payload.durationSec = sec;
    } else {
      const count = parseInt(steps);
      if (isNaN(count) || count < 0) { setError("Enter a valid step count."); return; }
      payload.stepCount = count;
    }

    setLoading(true);
    try {
      const data = await api.logActivity(payload);
      setResult(data);
      reset();
    } catch (err) {
      setError(err.data?.message || err.message);
    } finally { setLoading(false); }
  }

  return (
    <div className="log">
      <h1 className="log__title">Log Activity</h1>

      <div className="log__sports" role="radiogroup" aria-label="Select sport">
        {SPORTS.map(s => (
          <button key={s.key} type="button" role="radio" aria-checked={selected===s.key}
            className={`log__sport ${selected===s.key ? "log__sport--active" : ""}`}
            onClick={() => { setSelected(s.key); setResult(null); setError(null); reset(); }}>
            {s.label}
          </button>
        ))}
      </div>

      {sport && !result && (
        <form className="log__form" onSubmit={handleSubmit}>
          {sport.type === "distance" && (
            <label className="log__field">
              <span className="log__label">Distance (km)</span>
              <input type="number" step="0.01" min="0" value={distance}
                onChange={e => setDistance(e.target.value)} placeholder="e.g. 5.3" autoFocus />
            </label>
          )}
          {sport.type === "duration" && (
            <div className="log__duration">
              <label className="log__field">
                <span className="log__label">Hours</span>
                <input type="number" min="0" value={hours}
                  onChange={e => setHours(e.target.value)} placeholder="0" autoFocus />
              </label>
              <label className="log__field">
                <span className="log__label">Minutes</span>
                <input type="number" min="0" max="59" value={minutes}
                  onChange={e => setMinutes(e.target.value)} placeholder="30" />
              </label>
            </div>
          )}
          {sport.type === "steps" && (
            <label className="log__field">
              <span className="log__label">Step count</span>
              <input type="number" min="0" value={steps}
                onChange={e => setSteps(e.target.value)} placeholder="e.g. 8342" autoFocus />
            </label>
          )}
          {error && <p className="log__error">{error}</p>}
          <button type="submit" className="log__submit" disabled={loading}>
            {loading ? "Recording…" : "Record Activity"}
          </button>
        </form>
      )}

      {result && (
        <div className="log__result" aria-live="polite">
          <ScoreDisplay value={result.points} label="Points Earned" />
          <button className="log__again" onClick={() => { setResult(null); setSelected(null); }}>
            Log Another
          </button>
          <button className="log__todash" onClick={() => navigate("/dashboard")}>
            View Dashboard
          </button>
        </div>
      )}
    </div>
  );
}
