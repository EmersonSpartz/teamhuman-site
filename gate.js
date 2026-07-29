// Team Human private-preview gate.
// A velvet rope, not a vault: this is client-side and exists for the
// pre-release vibe, not for security.
(function () {
  var KEY = 'th_gate';
  // Portal: a Google Sheet published as CSV (columns: password, name).
  // Mario/Sam add rows there; paste the published-CSV URL below.
  var SHEET_CSV_URL = '';
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
    '#gate img{width:46px;mix-blend-mode:multiply;opacity:.9;margin-bottom:14px}' +
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
      '<div class="k">Private Preview</div>' +
      '<h2>You\u2019ve been invited behind the curtain.</h2>' +
      '<form id="gateForm"><input type="password" id="gatePw" placeholder="Your password" autocomplete="off" autofocus>' +
      '<div class="err" id="gateErr"></div>' +
      '<button type="submit">Enter</button></form>' +
      '<p class="fine">Your password is a personal invitation from the Team Human crew.</p>' +
      '</div>';
    document.body.appendChild(gate);

    function lookupBuiltin(pw) {
      try {
        var k = btoa(pw);
        return BUILTINS[k] ? atob(BUILTINS[k]) : null;
      } catch (e) { return null; }
    }

    function lookupSheet(pw) {
      if (!SHEET_CSV_URL) return Promise.resolve(null);
      return fetch(SHEET_CSV_URL, { cache: 'no-store' })
        .then(function (r) { return r.text(); })
        .then(function (text) {
          var lines = text.split(/\r?\n/);
          for (var i = 0; i < lines.length; i++) {
            var parts = lines[i].split(',');
            if (parts[0] && parts[0].trim().toLowerCase() === pw) {
              return (parts[1] || 'friend of Team Human').trim();
            }
          }
          return null;
        })
        .catch(function () { return null; });
    }

    document.getElementById('gateForm').addEventListener('submit', function (e) {
      e.preventDefault();
      var pw = document.getElementById('gatePw').value.trim().toLowerCase();
      if (!pw) return;
      var name = lookupBuiltin(pw);
      (name ? Promise.resolve(name) : lookupSheet(pw)).then(function (finalName) {
        if (!finalName) {
          document.getElementById('gateErr').textContent = 'That password isn\u2019t on the list. Ask the team for yours.';
          return;
        }
        localStorage.setItem(KEY, finalName);
        document.documentElement.classList.remove('locked');
        gate.remove();
        var plaque = document.createElement('div');
        plaque.id = 'welcomePlaque';
        plaque.textContent = 'Welcome behind the curtain, ' + finalName + '.';
        document.body.appendChild(plaque);
        setTimeout(function () { plaque.style.opacity = '0'; }, 4200);
        setTimeout(function () { plaque.remove(); }, 5000);
      });
    });
  });
})();
