import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import * as api from "../api/client";
import ScoreDisplay from "../components/ScoreDisplay";
import "./LogActivity.css";

/* Scoring rate hints (static display only — NOT used for calculation) */
const SPORTS = [
  { key: "running", label: "Running", type: "distance", hint: "1 km = 100 pts", icon: "run" },
  { key: "walking", label: "Walking", type: "distance", hint: "1 km = 50 pts", icon: "walk" },
  { key: "cycling", label: "Cycling", type: "distance", hint: "1 km = 25 pts", icon: "cycle" },
  { key: "swimming", label: "Swimming", type: "duration", hint: "15 pts / minute", icon: "swim" },
  { key: "gym", label: "Gym", type: "duration", hint: "5 pts / minute", icon: "gym" },
  { key: "daily_steps", label: "Steps", type: "steps", hint: "100 steps = 1 pt", icon: "steps", ariaLabel: "Daily Steps" },
];

/* Simple monoline SVG icons */
function SportSVG({ icon, size = 28 }) {
  const paths = {
    run: <path d="M13 4a2 2 0 1 0 0-4 2 2 0 0 0 0 4Zm-1.5 3L8 10l-3 1.5.7 1.3L9 11l2.5-1.5L13 14l-3 5h2l2.5-4.5L17 18h2l-3.5-7 1-3-2.5-1Z"/>,
    walk: <path d="M12 4a2 2 0 1 0 0-4 2 2 0 0 0 0 4Zm-1 3L8 11l-2 1 .7 1.3L9 12l1.5-2L12 14l-2 6h2l1.5-4.5L15 18h2l-2.5-6 .5-3-2-2Z"/>,
    cycle: <><circle cx="6" cy="17" r="3.5" fill="none" stroke="currentColor" strokeWidth="1.5"/><circle cx="18" cy="17" r="3.5" fill="none" stroke="currentColor" strokeWidth="1.5"/><path d="M6 17l4-7h4l2 3h2M14 10l-2-4" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/><circle cx="13" cy="4" r="1.5"/></>,
    swim: <path d="M2 18c1.5 0 2.5-1 4-1s2.5 1 4 1 2.5-1 4-1 2.5 1 4 1 2.5-1 4-1v-2c-1.5 0-2.5 1-4 1s-2.5-1-4-1-2.5 1-4 1-2.5-1-4-1-2.5 1-4 1v2Zm8-6 4-3-1-1-3 2-3-3-4 4 1.5 1L8 9l2 3Zm7-8a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z"/>,
    gym: <path d="M20.57 14.86L22 13.43 20.57 12 17 15.57 8.43 7 12 3.43 10.57 2 9.14 3.43 7.71 2 5.57 4.14 4.14 2.71 2.71 4.14l1.43 1.43L2 7.71l1.43 1.43L2 10.57 3.43 12 7 8.43 15.57 17 12 20.57 13.43 22l1.43-1.43 1.43 1.43 2.14-2.14 1.43 1.43 1.43-1.43-1.43-1.43L22 16.29Z"/>,
    steps: <path d="M4 18l4-4 4 4 4-4 4 4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>,
  };
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      {paths[icon]}
    </svg>
  );
}

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
  const inputRef = useRef(null);

  const sport = SPORTS.find(s => s.key === selected);

  // Focus the first input when sport is selected
  useEffect(() => {
    if (sport && !result && inputRef.current) {
      inputRef.current.focus();
    }
  }, [selected, result]);

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
      <div className="log__card">
        <h1 className="log__title">Log Activity</h1>
        <p className="log__subtitle">What did you do?</p>

        <div className="log__grid" role="radiogroup" aria-label="Select sport">
          {SPORTS.map(s => (
            <button key={s.key} type="button" role="radio" aria-checked={selected===s.key}
              aria-label={s.ariaLabel || s.label}
              className={`log__sport-btn ${selected===s.key ? "log__sport-btn--active" : ""}`}
              onClick={() => { setSelected(s.key); setResult(null); setError(null); reset(); }}>
              <SportSVG icon={s.icon} />
              <span className="log__sport-label">{s.label}</span>
            </button>
          ))}
        </div>

        {sport && !result && (
          <>
            <div className="log__divider" />
            <div className="log__input-section" aria-live="polite">
              <div className="log__input-header">
                <SportSVG icon={sport.icon} size={20} />
                <div>
                  <span className="log__input-title">
                    {sport.type === "distance" && "Distance in km"}
                    {sport.type === "duration" && "Duration"}
                    {sport.type === "steps" && "Step count"}
                  </span>
                  <span className="log__input-hint mono">{sport.hint}</span>
                </div>
              </div>

              <form className="log__form" onSubmit={handleSubmit}>
                {sport.type === "distance" && (
                  <input ref={inputRef} type="number" step="0.01" min="0" value={distance}
                    className="log__input" onChange={e => setDistance(e.target.value)}
                    placeholder="e.g. 5.3" />
                )}
                {sport.type === "duration" && (
                  <div className="log__duration">
                    <div className="log__dur-field">
                      <label className="log__dur-label">Hours</label>
                      <input ref={inputRef} type="number" min="0" value={hours}
                        className="log__input" onChange={e => setHours(e.target.value)} placeholder="0" />
                    </div>
                    <div className="log__dur-field">
                      <label className="log__dur-label">Minutes</label>
                      <input type="number" min="0" max="59" value={minutes}
                        className="log__input" onChange={e => setMinutes(e.target.value)} placeholder="30" />
                    </div>
                  </div>
                )}
                {sport.type === "steps" && (
                  <input ref={inputRef} type="number" min="0" value={steps}
                    className="log__input" onChange={e => setSteps(e.target.value)}
                    placeholder="e.g. 8342" />
                )}
                {error && <p className="log__error" role="alert">{error}</p>}
                <button type="submit" className="log__submit" disabled={loading}>
                  {loading ? "Recording…" : "Log Activity"}
                </button>
              </form>
            </div>
          </>
        )}

        {result && (
          <div className="log__success" aria-live="polite">
            <p className="log__success-label">Activity Logged</p>
            <ScoreDisplay value={result.points} label="Points Earned" />
            <p className="log__success-sport">
              {sport?.label} {sport?.type === "distance" && `· ${distance} km`}
            </p>
            <div className="log__success-actions">
              <button className="log__btn-secondary" onClick={() => { setResult(null); setSelected(null); }}>
                Log Another
              </button>
              <button className="log__btn-primary" onClick={() => navigate("/dashboard")}>
                View Dashboard
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
