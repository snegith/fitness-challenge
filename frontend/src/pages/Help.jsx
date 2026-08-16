import "./Help.css";

export default function Help() {
  return (
    <div className="help">
      <h1 className="help__title">How NGOV Works</h1>
      <p className="help__intro">
        NGOV converts different physical activities into a single comparable point score.
        Log your activities, earn points, and compete on the global leaderboard.
      </p>

      <section className="help__section">
        <h2>Scoring System</h2>
        <p>Every activity you log is converted to points using these rules:</p>
        <table className="help__table">
          <thead>
            <tr><th>Activity</th><th>Rate</th><th>Example</th></tr>
          </thead>
          <tbody>
            <tr><td>Running</td><td className="mono">100 pts / km</td><td>5.3 km → 530 pts</td></tr>
            <tr><td>Walking</td><td className="mono">50 pts / km</td><td>2 km → 100 pts</td></tr>
            <tr><td>Cycling</td><td className="mono">25 pts / km</td><td>10 km → 250 pts</td></tr>
            <tr><td>Swimming</td><td className="mono">15 pts / min</td><td>30 min → 450 pts</td></tr>
            <tr><td>Gym</td><td className="mono">5 pts / min</td><td>60 min → 300 pts</td></tr>
            <tr><td>Daily Steps</td><td className="mono">1 pt / 100 steps</td><td>8,342 steps → 83 pts</td></tr>
          </tbody>
        </table>
        <p className="help__note">
          Points are always rounded down (floored). Partial minutes don't count for swimming and gym —
          only complete minutes earn points.
        </p>
      </section>

      <section className="help__section">
        <h2>Logging Activities</h2>
        <p>
          Go to <strong>Log Activity</strong>, select your sport, enter the measurement, and hit Record.
          Points are calculated instantly and added to your total.
        </p>
        <p>
          For running, walking, and cycling: enter the distance in kilometers.<br/>
          For swimming and gym: enter hours and minutes.<br/>
          For daily steps: enter your cumulative step count for the day.
        </p>
      </section>

      <section className="help__section">
        <h2>Daily Steps</h2>
        <p>
          Daily steps work differently from other activities. Each submission <strong>replaces</strong> your
          previous step count for the day — it doesn't add to it.
          Submit your device's cumulative daily total.
        </p>
      </section>

      <section className="help__section">
        <h2>Your Dashboard</h2>
        <p>
          Your dashboard shows your total score, a breakdown by sport, your points over time,
          and your recent activity history. It updates instantly after logging.
        </p>
      </section>

      <section className="help__section">
        <h2>Leaderboard &amp; Ranking</h2>
        <p>
          The leaderboard shows all participants ranked by total points.
          Rankings update live after every activity.
        </p>
        <p>
          <strong>Rank trend</strong> shows how your position changed compared to the previous day's
          snapshot. A daily snapshot is taken at midnight (IST) to establish the baseline.
        </p>
        <p>
          Ties are broken by registration date (earlier = higher) then by user ID.
        </p>
      </section>

      <section className="help__section">
        <h2>Account</h2>
        <p>
          Register with your first and last name. That same name is used to log back in.
          No password is required — this is a name-based identification system for the challenge.
        </p>
      </section>
    </div>
  );
}
