/* Runtime común de las plantillas de motion graphics.
 *
 * - Lee los parámetros del hash (#p=<json url-encoded>).
 * - Expone MG.seek(t): congela TODAS las animaciones CSS/WAAPI y las coloca en el segundo t.
 *   Así cada fotograma es determinista (no depende de la velocidad de captura).
 * - MG.onFrame(fn) para lo que se anima con JS (contadores, trazos, etc.).
 * - Variables CSS de marca: --accent, --accent2, --ink, --panel, --text, --font, --dur, --out.
 */
(function () {
  const hash = new URLSearchParams(location.hash.slice(1));
  let params = {};
  try { params = JSON.parse(hash.get('p') || '{}'); }
  catch (e) { window.__mgError = 'Parámetros JSON inválidos: ' + e.message; }

  const root = document.documentElement;
  const dur = Number(params.duration ?? root.dataset.duration ?? 3);
  const hooks = [];
  const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
  const ease = {
    linear: x => x,
    outCubic: x => 1 - Math.pow(1 - x, 3),
    outExpo: x => (x >= 1 ? 1 : 1 - Math.pow(2, -10 * x)),
    inOutCubic: x => (x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2),
    outBack: x => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); },
  };

  const theme = {
    '--accent': params.accent || '#00D4FF',
    '--accent2': params.accent2 || '#FFD400',
    '--ink': params.ink || '#0B1020',
    '--panel': params.panel || 'rgba(11,16,32,.86)',
    '--text': params.text_color || '#FFFFFF',
    '--font': params.font ? `'${params.font}', 'Montserrat', sans-serif` : `'Montserrat', 'Segoe UI', Arial, sans-serif`,
    '--dur': dur + 's',
    '--out': Math.max(0, dur - 0.45) + 's',
  };
  for (const [k, v] of Object.entries(theme)) root.style.setProperty(k, v);
  if (params.tone) root.classList.add(params.tone);   // p. ej. 'sobrio' (Infinite Process): sin mayúsculas ni rebotes

  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  window.MG = {
    params, duration: dur, ease, clamp, esc,
    get: (k, d) => (params[k] === undefined || params[k] === null || params[k] === '' ? d : params[k]),
    /** progreso 0..1 de un tramo [a, a+len] con easing */
    span: (t, a, len, fn = ease.outCubic) => fn(clamp((t - a) / len)),
    onFrame: fn => hooks.push(fn),
    seek(t) {
      for (const a of document.getAnimations()) { a.pause(); a.currentTime = t * 1000; }
      for (const fn of hooks) fn(t);
    },
    async ready() {
      try {
        await document.fonts.ready;
        // fuerza la carga de los pesos usados aunque aún no estén en pantalla
        await Promise.all(['500', '600', '800', '900'].map(w => document.fonts.load(`${w} 40px Montserrat`)));
      } catch (e) { /* sin fuentes extra: sigue */ }
      MG.seek(0);
      window.__mgReady = true;
    },
  };
  window.__mgSeek = t => window.MG.seek(t);
  window.addEventListener('error', e => { window.__mgError = e.message; });
})();
