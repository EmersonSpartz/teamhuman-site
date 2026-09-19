/* Team Human profile-frame maker. Everything happens in the visitor's browser:
   the photo comes from a public avatar lookup (unavatar.io, CORS-enabled) or a
   local file, gets drawn into a canvas with the ring, and is handed back as a
   PNG. Nothing is uploaded to us. Used by /frame and /act. */
(function () {
  const SIZE = 1024;
  const TOP = 'SLOW DOWN AI';
  const BOTTOM = '#TEAMHUMAN';
  const STYLES = {
    brick:    { ring: '#9c3a26', text: '#fbf6ec', edge: 'rgba(251,246,236,.55)' },
    charcoal: { ring: '#201c17', text: '#f6efe3', edge: 'rgba(246,239,227,.45)' }
  };
  const CSS = `
  .thf{max-width:560px}
  .thf-row{display:flex;gap:8px;flex-wrap:wrap}
  .thf-row input{flex:1 1 240px;min-width:0;padding:13px 14px;border:1px solid rgba(94,70,48,.28);border-radius:10px;background:#fbf6ec;color:#201c17;font:inherit;font-size:16px}
  .thf-row input:focus-visible{outline:2px solid #9c3a26;outline-offset:2px}
  .thf-btn{display:inline-block;padding:13px 20px;border-radius:10px;border:1px solid #9c3a26;background:#9c3a26;color:#fbf6ec;font:inherit;font-weight:700;font-size:.92rem;letter-spacing:.06em;text-transform:uppercase;cursor:pointer;text-decoration:none;text-align:center}
  .thf-btn:hover{background:#83301f;border-color:#83301f}
  .thf-btn.ghost{background:transparent;color:#9c3a26}
  .thf-btn.ghost:hover{background:rgba(156,58,38,.08)}
  .thf-btn[aria-pressed="true"]{background:#201c17;border-color:#201c17;color:#f6efe3}
  .thf-or{margin:10px 0 0;font-size:.92rem;color:#5e4630}
  .thf-or label{color:#9c3a26;font-weight:600;cursor:pointer;text-decoration:underline;text-underline-offset:3px}
  .thf-status{min-height:1.4em;margin:10px 0 0;font-size:.92rem;color:#5e4630}
  .thf-status.err{color:#9c3a26}
  .thf-result{margin-top:18px;display:grid;grid-template-columns:200px 1fr;gap:18px;align-items:start}
  .thf-preview{width:200px;height:200px;border-radius:50%;display:block;background:#f6efe3}
  .thf-styles{display:flex;gap:8px;margin-bottom:12px}
  .thf-styles .thf-btn{padding:9px 14px;font-size:.78rem}
  .thf-actions{display:flex;gap:8px;flex-wrap:wrap}
  .thf-fine{margin:12px 0 0;font-size:.82rem;color:#5e4630;line-height:1.45}
  @media(max-width:520px){.thf-result{grid-template-columns:1fr;justify-items:center;text-align:center}.thf-actions,.thf-styles{justify-content:center}}
  `;

  function ensureFont() {
    if (!document.querySelector('link[href*="family=Inter"]')) {
      const l = document.createElement('link'); l.rel = 'stylesheet';
      l.href = 'https://fonts.googleapis.com/css2?family=Inter:wght@800&display=swap';
      document.head.appendChild(l);
    }
    return (document.fonts && document.fonts.load) ? document.fonts.load('800 64px "Inter"').catch(() => {}) : Promise.resolve();
  }

  // Which public avatar to ask for, from whatever the person pasted.
  function parseInput(raw) {
    let s = (raw || '').trim();
    if (!s) return null;
    if (!/^https?:\/\//i.test(s) && /\.(com|be|tv)\//i.test(s)) s = 'https://' + s;
    if (/^https?:\/\//i.test(s)) {
      let u; try { u = new URL(s); } catch (e) { return { error: 'That link did not parse. Try pasting it again.' }; }
      const host = u.hostname.replace(/^www\.|^m\.|^mobile\./, '');
      const parts = u.pathname.split('/').filter(Boolean);
      if (/(^|\.)(x|twitter)\.com$/.test(host)) return parts[0] ? { tries: [['x', parts[0]]] } : { error: 'Add your username to the link.' };
      if (/(^|\.)tiktok\.com$/.test(host)) { const h = (parts.find(p => p.startsWith('@')) || '').slice(1); return h ? { tries: [['tiktok', h]] } : { error: 'Add your @username to the link.' }; }
      if (/(^|\.)youtube\.com$/.test(host)) {
        const p0 = parts[0] || '';
        if (p0.startsWith('@')) return { tries: [['youtube', p0]] };
        if ((p0 === 'channel' || p0 === 'c' || p0 === 'user') && parts[1]) return { tries: [['youtube', parts[1]]] };
        return { error: 'Use your channel link, the one with @ in it.' };
      }
      if (/(^|\.)instagram\.com$/.test(host) || /(^|\.)(facebook|linkedin|threads)\.(com|net)$/.test(host)) return { error: 'That site blocks photo lookups. Upload the photo instead, it takes one tap.' };
      return { error: 'Paste an X, YouTube or TikTok link, or upload a photo.' };
    }
    const h = s.replace(/^@/, '');
    if (!/^[\w.\-]{1,60}$/.test(h)) return { error: 'Paste a link, or upload a photo.' };
    return { tries: [['x', h], ['youtube', '@' + h], ['tiktok', h]] };
  }

  function loadImage(src, cors) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      if (cors) img.crossOrigin = 'anonymous';
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error('load failed: ' + src));
      img.src = src;
    });
  }

  async function fetchAvatar(tries) {
    let lastErr;
    for (const [provider, handle] of tries) {
      try {
        return await loadImage('https://unavatar.io/' + provider + '/' + encodeURIComponent(handle) + '?fallback=false', true);
      } catch (e) { lastErr = e; }
    }
    throw lastErr || new Error('no avatar');
  }

  // Text along a circle. side=1 draws across the top (reads clockwise),
  // side=-1 across the bottom (reads counter-clockwise, so it stays upright).
  function arcText(ctx, text, cx, cy, r, centerAngle, side, spacing) {
    const widths = [...text].map(ch => ctx.measureText(ch).width);
    const total = widths.reduce((a, w) => a + w, 0) + spacing * (widths.length - 1);
    let angle = centerAngle - side * (total / 2) / r;
    [...text].forEach((ch, i) => {
      const w = widths[i];
      const a = angle + side * (w / 2) / r;
      ctx.save();
      ctx.translate(cx + r * Math.cos(a), cy + r * Math.sin(a));
      ctx.rotate(a + side * Math.PI / 2);
      ctx.fillText(ch, 0, 0);
      ctx.restore();
      angle += side * (w + spacing) / r;
    });
  }

  function draw(canvas, img, styleName) {
    const st = STYLES[styleName] || STYLES.brick;
    canvas.width = SIZE; canvas.height = SIZE;
    const ctx = canvas.getContext('2d');
    const c = SIZE / 2, R = SIZE / 2, inner = R * 0.80;
    ctx.clearRect(0, 0, SIZE, SIZE);
    // ring
    ctx.save(); ctx.beginPath(); ctx.arc(c, c, R, 0, Math.PI * 2); ctx.closePath(); ctx.fillStyle = st.ring; ctx.fill(); ctx.restore();
    // photo, cover-fitted into the inner circle
    ctx.save(); ctx.beginPath(); ctx.arc(c, c, inner, 0, Math.PI * 2); ctx.closePath(); ctx.clip();
    ctx.fillStyle = '#f6efe3'; ctx.fillRect(0, 0, SIZE, SIZE);
    const d = inner * 2, s = Math.max(d / img.naturalWidth, d / img.naturalHeight);
    const w = img.naturalWidth * s, h = img.naturalHeight * s;
    ctx.drawImage(img, c - w / 2, c - h / 2, w, h);
    ctx.restore();
    // hairline between photo and ring
    ctx.save(); ctx.beginPath(); ctx.arc(c, c, inner, 0, Math.PI * 2); ctx.lineWidth = SIZE * 0.006; ctx.strokeStyle = st.edge; ctx.stroke(); ctx.restore();
    // words
    ctx.save();
    ctx.fillStyle = st.text; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.font = '800 ' + Math.round(SIZE * 0.066) + 'px Inter, "Helvetica Neue", Arial, sans-serif';
    const mid = (R + inner) / 2;
    arcText(ctx, TOP, c, c, mid, -Math.PI / 2, 1, SIZE * 0.012);
    arcText(ctx, BOTTOM, c, c, mid, Math.PI / 2, -1, SIZE * 0.012);
    ctx.restore();
    return canvas;
  }

  function toBlob(canvas) { return new Promise(res => canvas.toBlob(res, 'image/jpeg', 0.92)); }

  function mount(root, opts) {
    opts = opts || {};
    if (!document.getElementById('thf-css')) { const s = document.createElement('style'); s.id = 'thf-css'; s.textContent = CSS; document.head.appendChild(s); }
    root.classList.add('thf');
    root.innerHTML =
      '<form class="thf-row" novalidate>' +
        '<input type="text" inputmode="url" autocomplete="off" autocapitalize="off" spellcheck="false" placeholder="Paste your X, YouTube or TikTok link" aria-label="Your profile link">' +
        '<button class="thf-btn" type="submit">Make it</button>' +
      '</form>' +
      '<p class="thf-or">or <label>upload a photo<input type="file" accept="image/*" hidden></label></p>' +
      '<p class="thf-status" aria-live="polite"></p>' +
      '<div class="thf-result" hidden>' +
        '<img class="thf-preview" alt="Your framed profile photo" width="200" height="200">' +
        '<div>' +
          '<div class="thf-styles"><button type="button" class="thf-btn" data-style="brick" aria-pressed="true">Brick</button><button type="button" class="thf-btn" data-style="charcoal" aria-pressed="false">Charcoal</button></div>' +
          '<div class="thf-actions"><a class="thf-btn thf-dl" download="teamhuman-profile.jpg" href="#">Download</a><button type="button" class="thf-btn ghost thf-share" hidden>Share</button></div>' +
          '<p class="thf-fine">On a phone, press and hold the picture to save it. Nothing is uploaded, it is made right here on your device.</p>' +
        '</div>' +
      '</div>';
    const form = root.querySelector('form'), input = root.querySelector('input[type=text]'), file = root.querySelector('input[type=file]');
    const status = root.querySelector('.thf-status'), result = root.querySelector('.thf-result'), preview = root.querySelector('.thf-preview');
    const dl = root.querySelector('.thf-dl'), share = root.querySelector('.thf-share');
    const canvas = document.createElement('canvas');
    let source = null, styleName = 'brick', blobUrl = null, lastBlob = null;

    const say = (msg, err) => { status.textContent = msg || ''; status.classList.toggle('err', !!err); };

    async function render() {
      if (!source) return;
      await ensureFont();
      draw(canvas, source, styleName);
      const blob = await toBlob(canvas);
      if (!blob) { say('Could not build the image. Try uploading the photo instead.', true); return; }
      if (blobUrl) URL.revokeObjectURL(blobUrl);
      blobUrl = URL.createObjectURL(blob); lastBlob = blob;
      preview.src = blobUrl; dl.href = blobUrl; result.hidden = false;
      const f = new File([blob], 'teamhuman-profile.jpg', { type: 'image/jpeg' });
      share.hidden = !(navigator.canShare && navigator.canShare({ files: [f] }));
      if (opts.onRender) opts.onRender(blob);
    }

    form.addEventListener('submit', async e => {
      e.preventDefault();
      const parsed = parseInput(input.value);
      if (!parsed) { say('Paste your profile link first, or upload a photo.', true); return; }
      if (parsed.error) { say(parsed.error, true); return; }
      say('Finding your photo…');
      try { source = await fetchAvatar(parsed.tries); }
      catch (err) { say('Could not find a public photo for that link. Upload the photo instead, it takes one tap.', true); return; }
      say(''); await render();
    });
    file.addEventListener('change', async () => {
      const f = file.files && file.files[0]; if (!f) return;
      say('One second…');
      try { const url = URL.createObjectURL(f); source = await loadImage(url, false); URL.revokeObjectURL(url); }
      catch (err) { say('That file did not open as an image. Try a JPG or PNG.', true); return; }
      say(''); await render();
    });
    root.querySelectorAll('.thf-styles .thf-btn').forEach(b => b.addEventListener('click', async () => {
      styleName = b.dataset.style;
      root.querySelectorAll('.thf-styles .thf-btn').forEach(x => x.setAttribute('aria-pressed', String(x === b)));
      await render();
    }));
    share.addEventListener('click', async () => {
      if (!lastBlob) return;
      try { await navigator.share({ files: [new File([lastBlob], 'teamhuman-profile.jpg', { type: 'image/jpeg' })], title: 'Team Human' }); } catch (e) { /* user closed the sheet */ }
    });

    // A sample so the frame is visible before anyone types: the handprint on parchment.
    if (opts.sample) {
      loadImage(opts.sample, false).then(img => { source = img; return render(); }).then(() => { source = null; }).catch(() => {});
    }
    return { render, setSource: img => { source = img; return render(); }, canvas };
  }

  window.THFrame = { mount, draw, parseInput };
})();
