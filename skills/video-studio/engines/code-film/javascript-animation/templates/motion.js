// motion.js: closed-form springs that stay a pure function of time.
// Paste into the page's <script> (the page must stay a single self-contained file).
// Every function takes absolute or local time in seconds and returns a value; nothing is simulated,
// so frame 812 renders without frames 0-811 and the film stays deterministic.

const clamp01 = (x) => Math.min(1, Math.max(0, x));

// Damped spring step response, 0 -> 1, starting at t = 0. k = stiffness, d = damping (mass 1).
// z = d / (2 sqrt k): below 1 overshoots, 1 and above settles without overshoot.
function spring(t, k = 170, d = 26) {
  if (t <= 0) return 0;
  const w0 = Math.sqrt(k), z = d / (2 * w0);
  if (z < 1) {
    const wd = w0 * Math.sqrt(1 - z * z);
    return 1 - Math.exp(-z * w0 * t) * (Math.cos(wd * t) + (z * w0 / wd) * Math.sin(wd * t));
  }
  return 1 - Math.exp(-w0 * t) * (1 + w0 * t);     // critical (z >= 1 treated as critical)
}

// Presets by what moves. Measured overshoot / time to settle within 2% (2026-09-28):
//   snappy  0.8% / 0.23 s   buttons, toggles, leading edges, cursors
//   base    0%   / 0.44 s   cards, containers, camera
//   heavy   0%   / 0.58 s   big type, logo lockups, 3D objects (no overshoot on type)
//   playful 23%  / 0.59 s   mascots, stickers (visible overshoot)
const SPRING = { snappy: [320, 30], base: [170, 26], heavy: [100, 20], playful: [200, 12] };
const springOf = (name) => (t) => spring(t, ...SPRING[name]);

// A value whose target changes several times: sum one spring per change, each from its own time.
// keys: [[time, value], ...] sorted by time. Motion stays continuous; nothing restarts.
function track(t, keys, k = 170, d = 26) {
  let v = keys[0][1];
  for (let i = 1; i < keys.length; i++) v += (keys[i][1] - keys[i - 1][1]) * spring(t - keys[i][0], k, d);
  return v;
}

// A tab indicator / highlight that stretches as it moves: the leading edge is stiffer than the trailing one.
// stops: [[time, x], ...]; width: indicator width at rest.
function indicator(t, stops, width = 120) {
  const lead = track(t, stops, 320, 30), trail = track(t, stops, 140, 22);
  return { left: Math.min(lead, trail), right: Math.max(lead, trail) + width };
}

// Text inside a morphing container: enters just after the morph starts, leaves just before the next one.
// Returns alpha 0..1. Stops two texts from overlapping during a swap.
function swapAlpha(t, tIn, tOut, fadeIn = 0.12, fadeOut = 0.1, lag = 0.08) {
  return Math.min(clamp01((t - tIn - lag) / fadeIn), clamp01((tOut - fadeOut - t) / fadeOut));
}

// Seamless loop time. For a loop, also make the last keyframe equal the first (position and velocity).
const loopT = (t, dur) => ((t % dur) + dur) % dur;
