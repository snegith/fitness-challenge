import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import * as api from "../api/client";
import { titleCase, formatNumber } from "../utils/displayName";
import "./Leaderboard.css";

function Trend({ value }) {
  if (value === null || value === undefined)
    return <span className="lb-trend lb-trend--new" aria-label="New">NEW</span>;
  if (value > 0) return <span className="lb-trend lb-trend--up" aria-label={`Up ${value}`}>↑{value}</span>;
  if (value < 0) return <span className="lb-trend lb-trend--down" aria-label={`Down ${Math.abs(value)}`}>↓{Math.abs(value)}</span>;
  return <span className="lb-trend" aria-label="No change">—</span>;
}

export default function Leaderboard() {
  const { userId } = useAuth();
  const [entries, setEntries] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.getLeaderboard().then(setEntries).catch(e => setError(e.message));
  }, []);

  if (error) return <p style={{color:"var(--pr-red)",padding:"var(--s7) 0"}}>{error}</p>;
  if (!entries) return <p style={{color:"var(--ink-muted)",padding:"var(--s7) 0"}}>Loading…</p>;

  return (
    <div className="lb">
      <h1 className="lb__title">Leaderboard</h1>
      {entries.length === 0 ? (
        <p className="lb__empty">No participants yet.</p>
      ) : (
        <table className="lb__table" aria-label="Leaderboard">
          <thead>
            <tr>
              <th className="lb__th lb__th--rank">#</th>
              <th className="lb__th lb__th--name">Player</th>
              <th className="lb__th lb__th--pts">Points</th>
              <th className="lb__th lb__th--trend">Trend</th>
            </tr>
          </thead>
          <tbody>
            {entries.map(e => (
              <tr key={e.userId} className={`lb__row ${e.userId === userId ? "lb__row--self" : ""}`}>
                <td className="lb__rank mono">{String(e.rank).padStart(2,"0")}</td>
                <td className="lb__name">{titleCase(e.name)}</td>
                <td className="lb__pts mono">{formatNumber(e.totalPoints)}</td>
                <td className="lb__td-trend"><Trend value={e.rankTrend} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
