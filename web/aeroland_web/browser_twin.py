"""Self-contained animated browser twin for public AeroLand deployments."""

from __future__ import annotations

import pandas as pd


_REQUIRED_COLUMNS = (
    "elapsed_seconds",
    "x_m",
    "y_m",
    "altitude_m",
    "mission_state",
    "landing_confidence",
    "marker_sigma_radial_m",
    "marker_detected",
    "safe_to_descend",
)


def browser_twin_html(frame: pd.DataFrame) -> str:
    """Return an animated, dependency-free mission viewer for one telemetry frame."""

    missing = [column for column in _REQUIRED_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(f"Browser twin telemetry is missing: {', '.join(missing)}")
    if frame.empty:
        raise ValueError("Browser twin telemetry cannot be empty")

    payload = (
        frame.loc[:, _REQUIRED_COLUMNS]
        .copy()
        .to_json(orient="records", double_precision=6)
        .replace("</", "<\\/")
    )
    return _TEMPLATE.replace("__TELEMETRY__", payload)


_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  :root {
    color-scheme: dark;
    --bg: #05080c;
    --panel: rgba(8, 13, 19, .88);
    --line: #30353a;
    --text: #f2f0ea;
    --muted: #a8a8a3;
    --gold: #d6a34a;
    --green: #67d391;
    --red: #ff6b78;
  }
  * { box-sizing: border-box; }
  html, body { width: 100%; height: 100%; margin: 0; overflow: hidden; background: var(--bg); }
  body { color: var(--text); font-family: Inter, ui-sans-serif, system-ui, sans-serif; }
  .shell {
    position: relative; width: 100%; height: 638px; overflow: hidden;
    border: 1px solid #2c2e30; border-radius: 3px;
    background: radial-gradient(circle at 50% 15%, #18222d 0, #080d13 42%, #030507 100%);
  }
  canvas { display: block; width: 100%; height: 100%; cursor: grab; touch-action: none; }
  canvas:active { cursor: grabbing; }
  .hud {
    position: absolute; z-index: 2; top: 16px; left: 16px; right: 16px;
    display: flex; justify-content: space-between; align-items: flex-start; pointer-events: none;
  }
  .hud-card {
    min-width: 235px; padding: 11px 13px; border: 1px solid rgba(116, 124, 132, .38);
    background: rgba(2, 5, 8, .78); backdrop-filter: blur(8px);
    box-shadow: 0 12px 30px rgba(0, 0, 0, .22);
  }
  .eyebrow {
    color: var(--gold); font: 700 10px/1.2 ui-monospace, SFMono-Regular, Menlo, monospace;
    letter-spacing: .15em; text-transform: uppercase;
  }
  .state { margin-top: 6px; font-size: 21px; font-weight: 760; letter-spacing: .04em; }
  .source {
    color: var(--muted); font: 600 10px/1.5 ui-monospace, SFMono-Regular, Menlo, monospace;
    letter-spacing: .08em; text-align: right;
  }
  .source strong { display: block; color: var(--green); font-size: 11px; }
  .readouts {
    position: absolute; z-index: 2; top: 102px; left: 16px; display: grid; gap: 6px;
    pointer-events: none;
  }
  .readout {
    width: 168px; padding: 7px 10px; border-left: 2px solid #4d545a;
    background: rgba(2, 5, 8, .66); color: var(--muted);
    font: 600 10px/1.2 ui-monospace, SFMono-Regular, Menlo, monospace;
  }
  .readout b { float: right; color: var(--text); font-size: 11px; }
  .readout.good { border-left-color: var(--green); }
  .readout.warn { border-left-color: var(--gold); }
  .controls {
    position: absolute; z-index: 3; left: 16px; right: 16px; bottom: 14px;
    display: grid; grid-template-columns: auto auto minmax(150px, 1fr) auto; gap: 9px;
    align-items: center; padding: 10px; border: 1px solid rgba(116, 124, 132, .38);
    background: rgba(2, 5, 8, .88); backdrop-filter: blur(9px);
  }
  button, select {
    height: 34px; border: 1px solid #50555a; border-radius: 2px;
    color: var(--text); background: #11171d; font: 700 10px/1 ui-monospace, monospace;
    letter-spacing: .08em; text-transform: uppercase;
  }
  button { min-width: 86px; cursor: pointer; }
  button.primary { border-color: var(--gold); color: #17120a; background: var(--gold); }
  button:hover, select:hover { border-color: #d8d8d3; }
  input[type="range"] { width: 100%; accent-color: var(--gold); cursor: pointer; }
  .time { min-width: 102px; color: var(--text); text-align: right; font: 700 11px ui-monospace, monospace; }
  .hint {
    position: absolute; right: 18px; bottom: 72px; color: rgba(210, 214, 216, .6);
    font: 600 9px ui-monospace, monospace; letter-spacing: .08em; pointer-events: none;
  }
  @media (max-width: 700px) {
    .shell { height: 580px; }
    .hud-card { min-width: 190px; }
    .source { display: none; }
    .controls { grid-template-columns: auto auto 1fr; }
    .controls select { display: none; }
  }
</style>
</head>
<body>
<div class="shell" id="shell">
  <canvas id="scene" aria-label="Animated AeroLand drone mission"></canvas>
  <div class="hud">
    <div class="hud-card">
      <div class="eyebrow">Animated browser twin</div>
      <div class="state" id="state">WAITING</div>
    </div>
    <div class="source"><strong>● SIMULATION ONLINE</strong>SYNTHETIC TELEMETRY / 10 HZ</div>
  </div>
  <div class="readouts">
    <div class="readout"><span>ALTITUDE</span><b id="altitude">0.00 m</b></div>
    <div class="readout"><span>CONFIDENCE</span><b id="confidence">0.00</b></div>
    <div class="readout"><span>RADIAL σ</span><b id="sigma">—</b></div>
    <div class="readout warn" id="gateRow"><span>DESCENT GATE</span><b id="gate">HOLD</b></div>
  </div>
  <div class="controls">
    <button class="primary" id="play">Pause</button>
    <button id="restart">Restart</button>
    <input id="timeline" type="range" min="0" max="1" step="0.01" value="0" aria-label="Mission timeline">
    <div style="display:flex;align-items:center;gap:9px">
      <select id="speed" aria-label="Playback speed">
        <option value="0.5">0.5×</option>
        <option value="1">1×</option>
        <option value="2" selected>2×</option>
        <option value="4">4×</option>
      </select>
      <div class="time" id="time">T+ 0.0 s</div>
    </div>
  </div>
  <div class="hint">DRAG TO ORBIT · SCROLL TO ZOOM</div>
</div>
<script>
(() => {
  const telemetry = __TELEMETRY__;
  const canvas = document.getElementById('scene');
  const shell = document.getElementById('shell');
  const ctx = canvas.getContext('2d');
  const timeline = document.getElementById('timeline');
  const playButton = document.getElementById('play');
  const restartButton = document.getElementById('restart');
  const speedSelect = document.getElementById('speed');
  const duration = Number(telemetry[telemetry.length - 1].elapsed_seconds || 0);
  let width = 0;
  let height = 0;
  let dpr = 1;
  let playhead = 0;
  let playing = true;
  let speed = 2;
  let lastStamp = performance.now();
  let yaw = -0.73;
  let zoom = 1;
  let dragging = false;
  let dragX = 0;

  timeline.max = String(duration);

  function resize() {
    const rect = shell.getBoundingClientRect();
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    width = rect.width;
    height = rect.height;
    canvas.width = Math.max(1, Math.round(width * dpr));
    canvas.height = Math.max(1, Math.round(height * dpr));
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function rowAt(time) {
    if (time <= 0) return {...telemetry[0], _index: 0};
    if (time >= duration) return {...telemetry[telemetry.length - 1], _index: telemetry.length - 1};
    let low = 0;
    let high = telemetry.length - 1;
    while (low + 1 < high) {
      const mid = (low + high) >> 1;
      if (Number(telemetry[mid].elapsed_seconds) <= time) low = mid;
      else high = mid;
    }
    const a = telemetry[low];
    const b = telemetry[high];
    const span = Math.max(Number(b.elapsed_seconds) - Number(a.elapsed_seconds), 0.0001);
    const f = Math.max(0, Math.min(1, (time - Number(a.elapsed_seconds)) / span));
    const lerp = key => Number(a[key] || 0) + (Number(b[key] || 0) - Number(a[key] || 0)) * f;
    return {
      ...a,
      elapsed_seconds: time,
      x_m: lerp('x_m'),
      y_m: lerp('y_m'),
      altitude_m: lerp('altitude_m'),
      landing_confidence: lerp('landing_confidence'),
      marker_sigma_radial_m: a.marker_sigma_radial_m == null ? null : lerp('marker_sigma_radial_m'),
      _index: low,
    };
  }

  function project(x, y, z) {
    const centerX = 0.65;
    const centerY = 0.65;
    const dx = Number(x) - centerX;
    const dy = Number(y) - centerY;
    const c = Math.cos(yaw);
    const s = Math.sin(yaw);
    const rx = dx * c - dy * s;
    const ry = dx * s + dy * c;
    const groundScale = Math.min(width * 0.30, height * 0.33) * zoom;
    const altitudeScale = Math.min(78, height * 0.145) * zoom;
    return {
      x: width * 0.54 + rx * groundScale,
      y: height * 0.73 + ry * groundScale * 0.43 - Number(z) * altitudeScale,
    };
  }

  function strokePath(points, color, lineWidth, dash = []) {
    if (!points.length) return;
    ctx.beginPath();
    points.forEach((point, index) => {
      if (index === 0) ctx.moveTo(point.x, point.y);
      else ctx.lineTo(point.x, point.y);
    });
    ctx.setLineDash(dash);
    ctx.strokeStyle = color;
    ctx.lineWidth = lineWidth;
    ctx.stroke();
    ctx.setLineDash([]);
  }

  function drawGrid() {
    const minor = 'rgba(125, 139, 150, .13)';
    const major = 'rgba(125, 139, 150, .23)';
    for (let value = -0.5; value <= 1.75; value += 0.25) {
      const strong = Math.abs(value % 0.5) < 0.01;
      strokePath([project(value, -0.5, 0), project(value, 1.75, 0)], strong ? major : minor, strong ? 1.1 : 0.7);
      strokePath([project(-0.5, value, 0), project(1.75, value, 0)], strong ? major : minor, strong ? 1.1 : 0.7);
    }
    const pad = [];
    for (let i = 0; i <= 80; i += 1) {
      const theta = i / 80 * Math.PI * 2;
      pad.push(project(0.15 * Math.cos(theta), 0.15 * Math.sin(theta), 0.006));
    }
    strokePath(pad, 'rgba(214, 163, 74, .90)', 2.4);
    strokePath([project(-0.13, 0, .008), project(.13, 0, .008)], 'rgba(214, 163, 74, .60)', 1.4);
    strokePath([project(0, -.13, .008), project(0, .13, .008)], 'rgba(214, 163, 74, .60)', 1.4);
  }

  function drawDrone(point, heading, rotorPhase) {
    const scale = Math.max(.78, Math.min(1.18, width / 980));
    ctx.save();
    ctx.translate(point.x, point.y);
    ctx.rotate(heading);
    ctx.scale(scale, scale);
    ctx.shadowColor = 'rgba(0, 0, 0, .55)';
    ctx.shadowBlur = 12;
    ctx.lineCap = 'round';

    const arms = [[-27,-20,27,20],[-27,20,27,-20]];
    ctx.strokeStyle = '#707982';
    ctx.lineWidth = 6;
    arms.forEach(a => { ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(a[2], a[3]); ctx.stroke(); });
    ctx.strokeStyle = '#252a30';
    ctx.lineWidth = 3.4;
    arms.forEach(a => { ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(a[2], a[3]); ctx.stroke(); });

    const motors = [[-29,-21],[29,21],[-29,21],[29,-21]];
    motors.forEach((m, i) => {
      ctx.fillStyle = '#363d44';
      ctx.strokeStyle = '#9ba4aa';
      ctx.lineWidth = 1.2;
      ctx.beginPath(); ctx.arc(m[0], m[1], 5.4, 0, Math.PI * 2); ctx.fill(); ctx.stroke();
      ctx.save();
      ctx.translate(m[0], m[1]);
      ctx.rotate(rotorPhase * (i % 2 ? -1 : 1));
      ctx.strokeStyle = 'rgba(157, 168, 176, .78)';
      ctx.lineWidth = 2;
      ctx.beginPath(); ctx.ellipse(0, 0, 16, 3.2, 0, 0, Math.PI * 2); ctx.stroke();
      ctx.restore();
    });

    const body = ctx.createLinearGradient(-14, -12, 15, 14);
    body.addColorStop(0, '#59626a');
    body.addColorStop(.48, '#2d3339');
    body.addColorStop(1, '#171b1f');
    ctx.fillStyle = body;
    ctx.strokeStyle = '#a4adb3';
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.moveTo(-16, -8); ctx.lineTo(9, -11); ctx.lineTo(17, 0);
    ctx.lineTo(9, 11); ctx.lineTo(-16, 8); ctx.lineTo(-20, 0); ctx.closePath();
    ctx.fill(); ctx.stroke();

    ctx.fillStyle = '#0d1013';
    ctx.strokeStyle = '#737d84';
    ctx.beginPath(); ctx.roundRect(-5, -5, 12, 10, 2); ctx.fill(); ctx.stroke();
    ctx.fillStyle = '#d6a34a';
    ctx.beginPath(); ctx.arc(-19, 0, 2.6, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#68d59a';
    ctx.beginPath(); ctx.arc(13, 0, 2, 0, Math.PI * 2); ctx.fill();

    ctx.strokeStyle = '#677078';
    ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(-10, 9); ctx.lineTo(-13, 17); ctx.lineTo(-4, 17); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(10, 8); ctx.lineTo(13, 16); ctx.lineTo(4, 16); ctx.stroke();
    ctx.restore();
  }

  function draw(current) {
    ctx.clearRect(0, 0, width, height);
    const sky = ctx.createLinearGradient(0, 0, 0, height);
    sky.addColorStop(0, '#101922');
    sky.addColorStop(.52, '#080d13');
    sky.addColorStop(1, '#030507');
    ctx.fillStyle = sky;
    ctx.fillRect(0, 0, width, height);

    for (let i = 0; i < 44; i += 1) {
      const x = (i * 83 + 17) % Math.max(width, 1);
      const y = (i * 47 + 31) % Math.max(height * .57, 1);
      ctx.fillStyle = i % 5 === 0 ? 'rgba(214,163,74,.33)' : 'rgba(235,240,244,.24)';
      ctx.fillRect(x, y, 1, 1);
    }

    drawGrid();
    const allPoints = telemetry.map(row => project(row.x_m, row.y_m, row.altitude_m));
    strokePath(allPoints, 'rgba(132, 145, 154, .27)', 2, [5, 7]);
    const flown = telemetry.slice(0, current._index + 1).map(row => project(row.x_m, row.y_m, row.altitude_m));
    flown.push(project(current.x_m, current.y_m, current.altitude_m));
    strokePath(flown, 'rgba(214, 163, 74, .92)', 3.2);

    const shadow = project(current.x_m, current.y_m, 0.015);
    ctx.save();
    ctx.translate(shadow.x, shadow.y);
    ctx.scale(1, .34);
    const shadowAlpha = Math.max(.08, .28 - Number(current.altitude_m) * .045);
    ctx.fillStyle = `rgba(0, 0, 0, ${shadowAlpha})`;
    ctx.beginPath(); ctx.arc(0, 0, 25, 0, Math.PI * 2); ctx.fill();
    ctx.restore();

    const next = telemetry[Math.min(current._index + 1, telemetry.length - 1)];
    const here = project(current.x_m, current.y_m, current.altitude_m);
    const ahead = project(next.x_m, next.y_m, next.altitude_m);
    const heading = Math.atan2(ahead.y - here.y, ahead.x - here.x);
    drawDrone(here, Number.isFinite(heading) ? heading : 0, playhead * 11);

    document.getElementById('state').textContent = String(current.mission_state || 'WAITING');
    document.getElementById('altitude').textContent = `${Number(current.altitude_m).toFixed(2)} m`;
    document.getElementById('confidence').textContent = Number(current.landing_confidence || 0).toFixed(2);
    document.getElementById('sigma').textContent = current.marker_sigma_radial_m == null
      ? '—' : `${Number(current.marker_sigma_radial_m).toFixed(3)} m`;
    const gateOpen = Boolean(current.safe_to_descend);
    document.getElementById('gate').textContent = gateOpen ? 'APPROVED' : 'HOLD';
    document.getElementById('gateRow').className = `readout ${gateOpen ? 'good' : 'warn'}`;
    document.getElementById('time').textContent = `T+ ${playhead.toFixed(1)} s`;
    timeline.value = String(playhead);
  }

  function tick(stamp) {
    const delta = Math.min((stamp - lastStamp) / 1000, .1);
    lastStamp = stamp;
    if (playing) {
      playhead += delta * speed;
      if (playhead >= duration) {
        playhead = duration;
        playing = false;
        playButton.textContent = 'Replay';
      }
    }
    draw(rowAt(playhead));
    requestAnimationFrame(tick);
  }

  playButton.addEventListener('click', () => {
    if (!playing && playhead >= duration) playhead = 0;
    playing = !playing;
    playButton.textContent = playing ? 'Pause' : (playhead >= duration ? 'Replay' : 'Play');
  });
  restartButton.addEventListener('click', () => {
    playhead = 0;
    playing = true;
    playButton.textContent = 'Pause';
  });
  timeline.addEventListener('input', event => {
    playhead = Number(event.target.value);
    playing = false;
    playButton.textContent = playhead >= duration ? 'Replay' : 'Play';
  });
  speedSelect.addEventListener('change', event => { speed = Number(event.target.value); });
  canvas.addEventListener('pointerdown', event => {
    dragging = true; dragX = event.clientX; canvas.setPointerCapture(event.pointerId);
  });
  canvas.addEventListener('pointermove', event => {
    if (!dragging) return;
    yaw += (event.clientX - dragX) * .008;
    dragX = event.clientX;
  });
  canvas.addEventListener('pointerup', () => { dragging = false; });
  canvas.addEventListener('pointercancel', () => { dragging = false; });
  canvas.addEventListener('wheel', event => {
    event.preventDefault();
    zoom = Math.max(.68, Math.min(1.45, zoom * (event.deltaY > 0 ? .94 : 1.06)));
  }, {passive: false});

  new ResizeObserver(resize).observe(shell);
  resize();
  requestAnimationFrame(tick);
})();
</script>
</body>
</html>
"""
