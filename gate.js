// Team Human private-preview gate.
// A velvet rope, not a vault: this is client-side and exists for the
// pre-release vibe, not for security.
(function () {
  var KEY = 'th_gate';
  var BUILTINS = {
    'dGVhbWh1bWFu': 'ZnJpZW5kIG9mIFRlYW0gSHVtYW4=',
    'bWFyaW8=': 'TWFyaW8=',
    'c2Ft': 'U2Ft',
    'b2xpdmVy': 'T2xpdmVy',
    'ZHJldw==': 'RHJldw==',
    'ZW1lcnNvbg==': 'RW1lcnNvbg=='
  };

  if (localStorage.getItem(KEY)) return;

  var css = '#gate{position:fixed;inset:0;z-index:400;background:#f6efe3;display:flex;align-items:center;justify-content:center;visibility:visible;text-align:center;padding:24px}' +
    '#gate .inner{max-width:400px;width:100%}' +
    '#gate img{width:52px;mix-blend-mode:multiply;opacity:.9;margin-bottom:26px}' +
    '#gate .k{font-size:.74rem;font-weight:700;letter-spacing:.26em;text-transform:uppercase;color:#ba5931;margin-bottom:12px}' +
    '#gate h2{font-family:Fraunces,Georgia,serif;font-weight:600;font-size:1.7rem;line-height:1.25;color:#201c17;margin-bottom:22px}' +
    '#gate input{width:100%;background:#fbf6ec;border:1px solid rgba(94,70,48,.25);border-radius:8px;padding:14px;font-size:1rem;font-family:inherit;text-align:center;color:#201c17}' +
    '#gate input:focus{outline:none;border-color:#ba5931}' +
    '#gate .err{color:#ba5931;font-size:.85rem;font-weight:600;min-height:22px;margin-top:8px}' +
    '#gate button{width:100%;margin-top:4px;background:#ba5931;color:#fbf6ec;border:none;border-radius:8px;padding:14px;font-weight:600;font-size:.88rem;letter-spacing:.12em;text-transform:uppercase;cursor:pointer;font-family:inherit}' +
    '#gate button:hover{background:#a34b27}' +
    '#gate .fine{font-size:.76rem;color:#8a7c66;margin-top:14px}' +
    '#welcomePlaque{position:fixed;top:82px;left:50%;transform:translateX(-50%);z-index:400;background:#fbf6ec;border:1px solid rgba(94,70,48,.2);border-radius:10px;padding:12px 22px;font-family:Fraunces,Georgia,serif;font-style:italic;font-size:1.05rem;color:#5e4630;box-shadow:0 10px 30px rgba(94,70,48,.18);transition:opacity .6s}';

  function ready(fn) {
    if (document.body) fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }

  ready(function () {
    var style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);

    var gate = document.createElement('div');
    gate.id = 'gate';
    gate.innerHTML = '<div class="inner">' +
      '<img src="brand/handprint.png" alt="">' +
      '<form id="gateForm"><input type="password" id="gatePw" placeholder="Password" autocomplete="off" autofocus>' +
      '<div class="err" id="gateErr"></div>' +
      '<button type="submit">Enter</button></form>' +
      '</div>';
    document.body.appendChild(gate);

    function lookupBuiltin(pw) {
      try {
        var k = btoa(pw);
        return BUILTINS[k] ? atob(BUILTINS[k]) : null;
      } catch (e) { return null; }
    }

    // The password IS the creator's name, exactly as the team sent it
    // (minted at /portal.html). If they typed it in all lowercase, dress it
    // up with title case for the greeting; otherwise respect their caps.
    function displayName(raw) {
      if (raw !== raw.toLowerCase()) return raw;
      return raw.replace(/\b[a-z]/g, function (c) { return c.toUpperCase(); });
    }

    document.getElementById('gateForm').addEventListener('submit', function (e) {
      e.preventDefault();
      var raw = document.getElementById('gatePw').value.trim();
      if (!raw) return;
      var finalName = lookupBuiltin(raw.toLowerCase()) || displayName(raw);
      localStorage.setItem(KEY, finalName);
      document.documentElement.classList.remove('locked');
      gate.remove();
      var plaque = document.createElement('div');
      plaque.id = 'welcomePlaque';
      plaque.textContent = 'Welcome, ' + finalName + '.';
      document.body.appendChild(plaque);
      setTimeout(function () { plaque.style.opacity = '0'; }, 4200);
      setTimeout(function () { plaque.remove(); }, 5000);
    });
  });
})();
