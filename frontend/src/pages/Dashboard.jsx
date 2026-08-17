import { useEffect, useState, useMemo } from "react";
import { useAuth } from "../context/AuthContext";
import * as api from "../api/client";
import ScoreDisplay from "../components/ScoreDisplay";
import { formatNumber } from "../utils/displayName";
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip } from "recharts";
import "./Dashboard.css";

/**
 * Format a UTC ISO timestamp to IST display string.
 * Always uses Asia/Kolkata regardless of browser timezone.
 */
function formatIST(utcStr) {
  try {
    const d = new Date(utcStr.endsWith("Z") ? utcStr : utcStr + "Z");
    if (isNaN(d.getTime())) return "";
    return d.toLocaleString("en-IN", {
      timeZone: "Asia/Kolkata",
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });
  } catch {
    return "";
  }
}

export default function Dashboard() {
  const { userId } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [sortBy, setSortBy] = useState("recent");

  useEffect(() => {
    if (!userId) return;
    api.getDashboard(userId).then(setData).catch(e => setError(e.message));
  }, [userId]);

  const sortedActivities = useMemo(() => {
    if (!data) return [];
    const items = data.activityHistory.slice(0, 20);
    switch (sortBy) {
      case "oldest":
        return [...items].sort((a, b) => (a.recordedAt || "").localeCompare(b.recordedAt || ""));
      case "most-pts":
        return [...items].sort((a, b) => b.points - a.points);
      case "least-pts":
        return [...items].sort((a, b) => a.points - b.points);
      default:
        return [...items].sort((a, b) => (b.recordedAt || "").localeCompare(a.recordedAt || ""));
    }
  }, [data, sortBy]);

  if (error) return <p className="dash-error">{error}</p>;
  if (!data) return <p className="dash-loading">Loading…</p>;

  const { totalPoints, activityHistory, volumeOverTime, sportBreakdown } = data;
  const maxSport = Math.max(...Object.values(sportBreakdown), 1);

  return (
    <div className="dash">
      <ScoreDisplay value={totalPoints} />

      {/* Sport breakdown */}
      <section className="dash__section">
        <h2 className="dash__heading">Sport Breakdown</h2>
        {Object.keys(sportBreakdown).length === 0 ? (
          <p className="dash__empty">No activities yet</p>
        ) : (
          <div className="breakdown">
            {Object.entries(sportBreakdown).sort((a,b) => b[1]-a[1]).map(([sport, pts]) => (
              <div key={sport} className="breakdown__row">
                <span className="breakdown__sport">{sport.replace(/_/g," ")}</span>
                <div className="breakdown__bar">
                  <div className="breakdown__fill" style={{ width: `${(pts/maxSport)*100}%` }} />
                </div>
                <span className="breakdown__pts mono">{formatNumber(pts)}</span>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Volume over time */}
      <section className="dash__section">
        <h2 className="dash__heading">Volume Over Time</h2>
        {volumeOverTime.length === 0 ? (
          <p className="dash__empty">No data yet</p>
        ) : (
          <div className="vol-chart" data-testid="vol-chart">
            <ResponsiveContainer width="100%" height={180}>
              <AreaChart data={volumeOverTime} margin={{top:8,right:0,left:0,bottom:0}}>
                <XAxis dataKey="date" tick={{fontSize:10,fill:"var(--ink-muted)"}} tickLine={false} axisLine={false} />
                <YAxis tick={{fontSize:10,fill:"var(--ink-muted)",fontFamily:"var(--font-mono)"}} tickLine={false} axisLine={false} width={36} />
                <Tooltip contentStyle={{background:"var(--ink)",border:"none",borderRadius:"var(--radius-sm)",color:"var(--bone)",fontSize:"0.75rem"}} />
                <Area type="monotone" dataKey="points" stroke="var(--lane-blue)" fill="var(--lane-blue-light)" strokeWidth={2} dot={{r:3,fill:"var(--lane-blue)"}} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>

      {/* Activity history */}
      <section className="dash__section">
        <div className="dash__section-header">
          <h2 className="dash__heading">Recent Activity</h2>
          {activityHistory.length > 0 && (
            <label className="dash__sort">
              <span className="dash__sort-label">Sort:</span>
              <select
                className="dash__sort-select"
                value={sortBy}
                onChange={e => setSortBy(e.target.value)}
                aria-label="Sort recent activity"
              >
                <option value="recent">Most Recent</option>
                <option value="oldest">Oldest</option>
                <option value="most-pts">Most Points</option>
                <option value="least-pts">Least Points</option>
              </select>
            </label>
          )}
        </div>
        {activityHistory.length === 0 ? (
          <p className="dash__empty">No activities logged yet</p>
        ) : (
          <table className="history" aria-label="Activity history">
            <tbody>
              {sortedActivities.map(a => (
                <tr key={a.activityId} className="history__row">
                  <td className="history__info">
                    <span className="history__sport">{a.sportType.replace(/_/g," ")}</span>
                    {a.recordedAt && (
                      <span className="history__time">{formatIST(a.recordedAt)}</span>
                    )}
                  </td>
                  <td className="history__pts mono">+{formatNumber(a.points)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
