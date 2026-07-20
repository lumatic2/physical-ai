import * as React from "react";

const WIDTH = 1000;
const HEIGHT = 176;
const PAD_X = 8;
const PAD_Y = 20;

function pointsFor(frames, selectValue) {
  if (!frames.length) return "";
  const values = frames.map(selectValue);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  return values
    .map((value, index) => {
      const x = PAD_X + (index / Math.max(1, frames.length - 1)) * (WIDTH - PAD_X * 2);
      const y = HEIGHT - PAD_Y - ((value - min) / span) * (HEIGHT - PAD_Y * 2);
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
}

export function TraceChart({ frames, frameIndex }) {
  const statePoints = React.useMemo(() => pointsFor(frames, (frame) => frame.state[2]), [frames]);
  const actionPoints = React.useMemo(() => pointsFor(frames, (frame) => frame.action[6]), [frames]);
  const cursorX = PAD_X + (frameIndex / Math.max(1, frames.length - 1)) * (WIDTH - PAD_X * 2);

  return (
    <div className="arm-chart-wrap" data-testid="trace-chart">
      <div className="arm-chart-legend" aria-label="그래프 범례">
        <span><i className="arm-legend-line is-state" />상태 · 말단 높이 eef_z (m)</span>
        <span><i className="arm-legend-line is-action" />행동 · gripper (-1~1)</span>
      </div>
      <svg
        className="arm-chart"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label={`전체 ${frames.length} 프레임의 상태와 행동 그래프. 현재 ${frameIndex} 프레임`}
        preserveAspectRatio="none"
      >
        <line className="arm-chart-grid" x1={PAD_X} y1={HEIGHT / 2} x2={WIDTH - PAD_X} y2={HEIGHT / 2} />
        <polyline className="arm-chart-line is-state" points={statePoints} />
        <polyline className="arm-chart-line is-action" points={actionPoints} />
        <line className="arm-chart-cursor" x1={cursorX} y1={0} x2={cursorX} y2={HEIGHT} />
      </svg>
    </div>
  );
}
