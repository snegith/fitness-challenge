/**
 * ScoreDisplay — the signature large score with odometer animation.
 * Only animates when value meaningfully changes (not on mount).
 */

import { useEffect, useRef, useState } from "react";
import { formatNumber } from "../utils/displayName";
import "./ScoreDisplay.css";

export default function ScoreDisplay({ value, label = "Total Points" }) {
  const [display, setDisplay] = useState(value);
  const [rolling, setRolling] = useState(false);
  const prev = useRef(value);
  const mounted = useRef(false);

  useEffect(() => {
    if (!mounted.current) { mounted.current = true; setDisplay(value); return; }
    if (prev.current !== value) {
      setRolling(true);
      const t = setTimeout(() => { setDisplay(value); setRolling(false); }, 400);
      prev.current = value;
      return () => clearTimeout(t);
    }
  }, [value]);

  const digits = formatNumber(display).split("");

  return (
    <div className="score-display" data-testid="score-display">
      <div className={`score-display__value mono ${rolling ? "score-display__value--roll" : ""}`}
           aria-live="polite" aria-label={`${value} points`}>
        {digits.map((ch, i) => (
          <span key={`${i}-${ch}`} className={`score-display__digit ${/\d/.test(ch) && rolling ? "score-display__digit--roll" : ""}`}>
            {ch}
          </span>
        ))}
      </div>
      <span className="score-display__label">{label}</span>
    </div>
  );
}
