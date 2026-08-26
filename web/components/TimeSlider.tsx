"use client";
import { useEffect, useRef, useState } from "react";

interface Props {
  dates: string[];
  index: number;
  onChange: (index: number) => void;
}

export default function TimeSlider({ dates, index, onChange }: Props) {
  const [playing, setPlaying] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!playing) return;
    timer.current = setInterval(() => {
      onChange(index + 1 <= dates.length - 1 ? index + 1 : index);
      if (index + 1 >= dates.length - 1) setPlaying(false);
    }, 650);
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, [playing, index, dates.length, onChange]);

  const fmt = (d: string) => d.slice(5).replace("-", ".");

  return (
    <div className="time-bar">
      <button
        className="play-btn"
        aria-label={playing ? "Pause" : "Play"}
        onClick={() => {
          if (!playing && index >= dates.length - 1) onChange(0);
          setPlaying(!playing);
        }}
      >
        {playing ? (
          <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor">
            <rect x="1" y="0" width="3" height="10" />
            <rect x="6" y="0" width="3" height="10" />
          </svg>
        ) : (
          <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor">
            <path d="M1 0 L9 5 L1 10 Z" />
          </svg>
        )}
      </button>
      <div className="slider-wrap">
        <input
          className="scrub"
          type="range"
          min={0}
          max={dates.length - 1}
          step={1}
          value={index}
          aria-label="Observation date"
          onChange={(e) => {
            setPlaying(false);
            onChange(Number(e.target.value));
          }}
        />
        <div className="slider-dates">
          <span>{fmt(dates[0])}</span>
          <span>{fmt(dates[dates.length - 1])}</span>
        </div>
      </div>
      <div className="time-readout">{dates[index]}</div>
    </div>
  );
}
