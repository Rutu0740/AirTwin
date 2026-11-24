/* UrbanAir Twin — shared front-end helpers. Every number on screen comes from the API. */
(function () {
  const T = {};
  window.Twin = T;

  T.get = async (url) => {
    const r = await fetch(url);
    const j = await r.json();
    if (!r.ok) throw new Error(j.detail ? (typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail)) : r.statusText);
    return j;
  };
  T.post = async (url, body) => {
    const r = await fetch(url, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
    const j = await r.json();
    if (!r.ok) throw new Error(j.detail ? (typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail)) : r.statusText);
    return j;
  };

  // CPCB National AQI sub-index breakpoints for PM2.5 (µg/m³, 24-h basis)
  T.bands = [
    { max: 30, label: 'Good', color: '#4f9d69' },
    { max: 60, label: 'Satisfactory', color: '#a3c45a' },
    { max: 90, label: 'Moderate', color: '#e8c547' },
    { max: 120, label: 'Poor', color: '#e8893a' },
    { max: 250, label: 'Very poor', color: '#d6453d' },
    { max: Infinity, label: 'Severe', color: '#8e2a52' },
  ];
  T.pmBand = (v) => T.bands.find((b) => v <= b.max);
  T.pmColor = (v) => `rgb(${T.ramp(T.PM_RAMP, v).map(Math.round).join(',')})`;
  T.deltaColor = (d) => {
    if (d <= -2) return '#2f8f6b';
    if (d <= -0.5) return '#5fb38c';
    if (d < -0.05) return '#a6d9bf';
    if (d < 0.05) return '#6b716c';
    return '#e8893a';
  };

  T.fmt = (v, d = 1) => (v === null || v === undefined || Number.isNaN(v) ? '—' : Number(v).toFixed(d));
  T.signed = (v, d = 1) => (v === null || v === undefined ? '—' : (v > 0 ? '+' : v < 0 ? '−' : '±') + Math.abs(v).toFixed(d));
  T.ist = (iso) => {
    const d = new Date(iso);
    return d.toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false }) + ' IST';
  };
  T.esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  // datetime-local value <-> API "YYYY-MM-DD HH:00"
  T.toApiTime = (v) => (v ? v.replace('T', ' ').slice(0, 13) + ':00' : null);
  T.toInput = (s) => s.replace(' ', 'T').slice(0, 16);

  // OpenStreetMap standard tiles; the page CSS dims .leaflet-layer in dark mode.
  const tileUrl = () => 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';

  T.maps = [];
  T.makeMap = (id, opts = {}) => {
    const m = L.map(id, { zoomControl: true, preferCanvas: true, zoomSnap: 0.25, zoomDelta: 0.5, attributionControl: true, ...opts }).setView([18.55, 73.86], 11);
    m._tiles = L.tileLayer(tileUrl(), { attribution: '&copy; OpenStreetMap contributors', maxZoom: 18 }).addTo(m);
    T.maps.push(m);
    setTimeout(() => m.invalidateSize(), 200);
    return m;
  };

  T.cellBounds = (lat, lon, deg) => [[lat - deg[0] / 2, lon - deg[1] / 2], [lat + deg[0] / 2, lon + deg[1] / 2]];
  T.CELL = [0.0045, 0.00475];

  T.drawCells = (map, cells, colorFn, opts = {}) => {
    const g = L.layerGroup();
    const renderer = L.canvas({ padding: 0.3 });
    cells.forEach((c, i) => {
      const r = L.rectangle(T.cellBounds(c.lat, c.lon, T.CELL), {
        renderer, stroke: !!opts.stroke, weight: 0.4, color: '#000', fillColor: colorFn(c),
        fillOpacity: opts.opacityFn ? opts.opacityFn(c) : 0.55,
      });
      if (opts.onClick) r.on('click', () => opts.onClick(c, i));
      if (opts.tooltip) r.bindTooltip(opts.tooltip(c), { sticky: true });
      g.addLayer(r);
    });
    return g.addTo(map);
  };

  // ---------------------------------------------------------------- smooth heat map
  // Continuous colour ramps (anchored on the CPCB PM2.5 breakpoints) instead of hard bands.
  T.PM_RAMP = [[0, [46, 133, 96]], [30, [140, 190, 88]], [60, [236, 200, 70]], [90, [238, 140, 56]], [120, [216, 66, 58]], [180, [168, 40, 76]], [250, [110, 28, 74]]];
  T.DELTA_RAMP = [[-3, [24, 112, 84]], [-1.2, [64, 160, 120]], [-0.4, [130, 200, 165]], [-0.05, [200, 230, 214]], [0, [150, 156, 151]], [0.5, [238, 140, 56]]];
  T.PM_CONTOURS = [30, 60, 90, 120, 250];
  T.ramp = (stops, v) => {
    if (v <= stops[0][0]) return stops[0][1];
    for (let i = 1; i < stops.length; i++) {
      if (v <= stops[i][0]) {
        const [a, ca] = stops[i - 1], [b, cb] = stops[i];
        const t = (v - a) / (b - a), s = t * t * (3 - 2 * t);   // smoothstep for softer transitions
        return [0, 1, 2].map((k) => ca[k] + (cb[k] - ca[k]) * s);
      }
    }
    return stops[stops.length - 1][1];
  };
  const rgb = (c) => `rgb(${c.map(Math.round).join(',')})`;

  /* Renders cells as one smooth raster: the value field is bilinearly up-sampled
     (values, not colours, are interpolated), coloured on a continuous ramp, with
     faint isolines at the CPCB breakpoints. Hover / click resolve to the nearest cell. */
  T.drawHeat = (map, cells, valueFn, opts = {}) => {
    const dLat = T.CELL[0], dLon = T.CELL[1];
    const stops = opts.ramp || T.PM_RAMP;
    const contours = opts.contours === undefined ? T.PM_CONTOURS : opts.contours;
    const k = opts.upscale || 10;
    const baseAlpha = opts.opacity ?? 0.72;
    const feather = opts.feather ?? 3;   // cells
    let latMin = Infinity, latMax = -Infinity, lonMin = Infinity, lonMax = -Infinity;
    cells.forEach((c) => { latMin = Math.min(latMin, c.lat); latMax = Math.max(latMax, c.lat); lonMin = Math.min(lonMin, c.lon); lonMax = Math.max(lonMax, c.lon); });
    const nI = Math.round((latMax - latMin) / dLat) + 1, nJ = Math.round((lonMax - lonMin) / dLon) + 1;
    const V = new Float32Array(nI * nJ).fill(NaN), A = new Float32Array(nI * nJ), idx = new Int32Array(nI * nJ).fill(-1);
    cells.forEach((c, n) => {
      const i = nI - 1 - Math.round((c.lat - latMin) / dLat), j = Math.round((c.lon - lonMin) / dLon);   // row 0 = north
      V[i * nJ + j] = valueFn(c); A[i * nJ + j] = opts.alphaFn ? opts.alphaFn(c) : 1; idx[i * nJ + j] = n;
    });
    const W = nJ * k, H = nI * k;
    const field = new Float32Array(W * H).fill(NaN), alpha = new Float32Array(W * H);
    for (let y = 0; y < H; y++) {
      const v = (y + 0.5) / k - 0.5, i0 = Math.floor(v), fy = v - i0;
      for (let x = 0; x < W; x++) {
        const u = (x + 0.5) / k - 0.5, j0 = Math.floor(u), fx = u - j0;
        let sv = 0, sa = 0, sw = 0, cov = 0;
        for (let di = 0; di <= 1; di++) for (let dj = 0; dj <= 1; dj++) {
          const i = i0 + di, j = j0 + dj;
          const w = (di ? fy : 1 - fy) * (dj ? fx : 1 - fx);
          if (i < 0 || j < 0 || i >= nI || j >= nJ) continue;
          const val = V[i * nJ + j];
          if (Number.isNaN(val)) continue;
          sv += val * w; sa += A[i * nJ + j] * w; sw += w;
        }
        if (sw > 0) {
          // feather the outer edge of the raster so the grid doesn't end in a hard rectangle
          const e = Math.min(x, W - 1 - x, y, H - 1 - y) / (k * feather);
          const fe = e >= 1 ? 1 : e * e * (3 - 2 * e);
          field[y * W + x] = sv / sw; alpha[y * W + x] = (sa / sw) * Math.min(1, sw * 1.6) * fe;
        }
      }
    }
    const cv = document.createElement('canvas'); cv.width = W; cv.height = H;
    const ctx = cv.getContext('2d'), img = ctx.createImageData(W, H), px = img.data;
    const band = (v) => { let b = 0; while (b < contours.length && v > contours[b]) b++; return b; };
    for (let p = 0; p < W * H; p++) {
      const v = field[p];
      if (Number.isNaN(v)) continue;
      let c = stops === null ? [255, 180, 171] : T.ramp(stops, v), a = baseAlpha * alpha[p];
      if (contours.length) {
        const x = p % W, b = band(v);
        const r = x + 1 < W ? field[p + 1] : v, d = p + W < W * H ? field[p + W] : v;
        const edge = (!Number.isNaN(r) && band(r) !== b) || (!Number.isNaN(d) && band(d) !== b);
        if (opts.contourOnly !== undefined) { if (!edge) continue; c = [255, 120, 110]; a = 0.95 * alpha[p]; }
        else if (edge) { c = c.map((q) => q * 0.55); a = Math.min(1, a + 0.15); }
      } else if (opts.contourOnly !== undefined) continue;
      px[p * 4] = c[0]; px[p * 4 + 1] = c[1]; px[p * 4 + 2] = c[2]; px[p * 4 + 3] = Math.round(a * 255);
    }
    ctx.putImageData(img, 0, 0);
    const bounds = [[latMin - dLat / 2, lonMin - dLon / 2], [latMax + dLat / 2, lonMax + dLon / 2]];
    const overlay = L.imageOverlay(cv.toDataURL('image/png'), bounds, { className: 'twin-heat', interactive: false });
    const group = L.layerGroup([overlay]);
    const pick = (ll) => {
      const i = nI - 1 - Math.round((ll.lat - latMin) / dLat), j = Math.round((ll.lng - lonMin) / dLon);
      if (i < 0 || j < 0 || i >= nI || j >= nJ) return null;
      const n = idx[i * nJ + j];
      return n < 0 ? null : cells[n];
    };
    const tip = L.tooltip({ sticky: true, direction: 'top', offset: [0, -8], className: 'twin-tip' });
    const onMove = (e) => {
      const c = opts.tooltip && pick(e.latlng);
      if (!c) { map.closeTooltip(tip); return; }
      tip.setLatLng(e.latlng).setContent(opts.tooltip(c));
      if (!map.hasLayer(tip)) tip.addTo(map);
    };
    const onClick = (e) => { const c = opts.onClick && pick(e.latlng); if (c) opts.onClick(c); };
    group.on('add', () => { map.on('mousemove', onMove); map.on('click', onClick); });
    group.on('remove', () => { map.off('mousemove', onMove); map.off('click', onClick); map.closeTooltip(tip); });
    group.addTo(map);
    return group;
  };

  T.rampLegend = (el, stops, ticks, unit, title) => {
    const lo = stops[0][0], hi = stops[stops.length - 1][0];
    const grad = Array.from({ length: 24 }, (_, n) => rgb(T.ramp(stops, lo + (hi - lo) * n / 23)) + ` ${(n / 23 * 100).toFixed(1)}%`).join(',');
    el.innerHTML = `<div class="flex items-center gap-3 flex-wrap"><span class="whitespace-nowrap">${title || ''}</span>
      <div class="relative flex-1 min-w-[220px] max-w-[460px] pt-0.5 pb-4">
        <div class="h-2.5 rounded-full" style="background:linear-gradient(90deg,${grad})"></div>
        ${ticks.map((t) => `<span class="absolute text-[10px] tabular-nums -translate-x-1/2" style="left:${((t - lo) / (hi - lo) * 100).toFixed(1)}%;top:14px">${t}</span>`).join('')}
      </div><span class="whitespace-nowrap">${unit}</span></div>`;
  };

  T.legend = (el) => {
    T.rampLegend(el, T.PM_RAMP, [0, 30, 60, 90, 120, 180, 250], 'µg/m³ PM2.5', 'Good → Severe (CPCB breakpoints)');
  };

  T.stateBadge = (state) => {
    const map = {
      OBSERVED: 'bg-tertiary-container/30 text-tertiary',
      MODELED: 'bg-primary/20 text-primary',
      MODELED_FORECAST: 'bg-secondary/20 text-secondary',
      MODELED_SCENARIO: 'bg-primary/20 text-primary',
      MODEL_ATTRIBUTED: 'bg-primary/20 text-primary',
      NO_READING: 'bg-surface-container-high text-outline',
    };
    return `<span class="px-1.5 py-0.5 rounded text-[10px] uppercase font-semibold tracking-wider ${map[state] || ''}">${state.replace(/_/g, ' ')}</span>`;
  };

  T.error = (el, e) => {
    el.innerHTML = `<div class="p-3 rounded-lg bg-error/10 text-error text-sm">${T.esc(e.message || e)}</div>`;
  };

  // Header: replace static clock / "live feed" claim with the data timestamp.
  T.setHeaderTime = (iso) => {
    document.querySelectorAll('header .font-code-metric').forEach((el) => (el.textContent = T.ist(iso).replace(/^.*, /, '')));
    document.querySelectorAll('header span').forEach((el) => {
      if (el.textContent.trim() === 'Municipal Live Feed') el.textContent = 'Hindcast replay (2025 data)';
    });
  };

  T.meta = null;
  T.loadMeta = async () => (T.meta = T.meta || (await T.get('/api/meta')));
  T.stationsCache = null;
  T.stationList = async () => (T.stationsCache = T.stationsCache || (await T.get('/api/stations')).stations);
})();

/* heat-map presentation */
(function () {
  const css = document.createElement('style');
  css.textContent = `.twin-heat{image-rendering:auto;mix-blend-mode:normal;transition:opacity .25s}
  .leaflet-tooltip.twin-tip{background:rgba(18,20,19,.92);color:#e2e3e0;border:1px solid #424843;border-radius:8px;padding:6px 9px;font:12px/1.35 Inter,sans-serif;box-shadow:0 4px 14px rgba(0,0,0,.35)}
  .leaflet-tooltip.twin-tip:before{display:none}
  /* Leaflet panes use z-index 200-1000; keep them inside the map so they never cover the fixed header */
  .leaflet-container{position:relative;z-index:0;isolation:isolate}
  header.fixed{z-index:2000 !important}`;
  document.head.appendChild(css);
})();
