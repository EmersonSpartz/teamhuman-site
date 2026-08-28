#!/bin/bash
# verify.sh — TeamHuman campaign site
# Checks the LIVE deployed site (falls back to local file if offline).
set -u
LIVE="https://teamhuman.org/"
DIR="$(cd "$(dirname "$0")" && pwd)"
FAIL=0

check() { # check <label> <condition-exit-code>
  if [ "$2" -eq 0 ]; then echo "  PASS  $1"; else echo "  FAIL  $1"; FAIL=1; fi
}

# HTTP status with retries: a single CDN blip during a fresh deploy used to fail the run
code() { # code <url>
  local url="$1" c=""
  for _ in 1 2 3; do
    c=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "$url")
    [ "$c" = "200" ] && break
    sleep 2
  done
  echo "$c"
}

echo "== TeamHuman verify =="

# 1. Live page reachable and serving current copy
HTML=$(curl -sfL --max-time 20 "$LIVE" 2>/dev/null)
if [ -n "$HTML" ]; then
  SRC="live ($LIVE)"
else
  echo "  WARN  live site unreachable — checking local file instead"
  HTML=$(cat "$DIR/index.html")
  SRC="local"
fi
echo "  source: $SRC"

echo "$HTML" | grep -q "Keep Humans in Control of AI" ; check "title copy present" $?
echo "$HTML" | grep -q "Join the movement to keep"    ; check "hero copy (doc VERSION FOR CLAUDE)" $?
echo "$HTML" | grep -q "Add your name to the chorus" ; check "pledge copy" $?
echo "$HTML" | grep -q '<section id="voices">' ; check "quotes section present" $?
QC=$(echo "$HTML" | grep -c 'class="qcard reveal"')
[ "$QC" = "5" ] ; check "all 5 signer quotes present (found $QC)" $?
if echo "$HTML" | grep -qE 'EXAMPLE|PLACEHOLDER'; then echo "  FAIL  placeholder markers back on the page"; FAIL=1; else echo "  PASS  no placeholder markers"; fi
echo "$HTML" | grep -q "AI should serve"              ; check "statement band present" $?
if echo "$HTML" | grep -qi "corporate arms race"; then echo "  FAIL  stale Figma copy leaked"; FAIL=1; else echo "  PASS  no stale Figma copy"; fi
if echo "$HTML" | grep -q "—"; then echo "  FAIL  em dash found (Emerson: AI slop coded)"; FAIL=1; else echo "  PASS  no em dashes"; fi

# 2. All referenced images resolve (against live host when live)
if [ "$SRC" != "local" ]; then
  IMGS=$(echo "$HTML" | grep -oE 'src="[^"]+\.(jpg|png)"' | sed 's/src="//;s/"//' | sort -u)
  BAD=0
  for img in $IMGS; do
    code=$(code "${LIVE}${img}")
    [ "$code" != "200" ] && BAD=1 && echo "         missing: $img ($code)"
  done
  check "all $(echo "$IMGS" | wc -l | tr -d ' ') referenced images return 200" $BAD
fi

# 3. Inline JS is syntactically valid
# Multi-line blocks: lines between a bare <script> line and its </script>.
# Single-line blocks (<script>...</script> on one line): extracted separately.
{
  echo "$HTML" | awk '/^[[:space:]]*<script>[[:space:]]*$/{f=1;next} /^[[:space:]]*<\/script>/{f=0} f'
  echo "$HTML" | grep -oE '<script>[^<]+</script>' | sed 's/<script>//;s|</script>||'
} > /tmp/th-inline.js
[ -s /tmp/th-inline.js ] && node --check /tmp/th-inline.js 2>/dev/null ; check "inline JS syntax (node --check, non-empty)" $?

# 4. No duplicate element IDs
DUPES=$(echo "$HTML" | grep -oE 'id="[^"]+"' | sort | uniq -d | wc -l | tr -d ' ')
[ "$DUPES" = "0" ] ; check "no duplicate element IDs" $?

# 5. Subpages: /join (creator contact form) must load, embed the form, stay ungated, and be brand-clean
if [ "$SRC" != "local" ]; then
  JOIN=$(curl -sfL --max-time 20 "${LIVE}invite/" 2>/dev/null)
  [ -n "$JOIN" ] ; check "/invite reachable" $?
  echo "$JOIN" | grep -q "docs.google.com/forms" ; check "/invite embeds the creator form" $?
  echo "$JOIN" | grep -q "over the finish line" ; check "/invite copy present" $?
  # The form link must be reachable for invited creators: this page is intentionally ungated.
  if echo "$JOIN" | grep -q "gate.js"; then echo "  FAIL  /invite is gated (creators with the link would be locked out)"; FAIL=1; else echo "  PASS  /invite ungated (by design)"; fi
  if echo "$JOIN" | grep -q "—"; then echo "  FAIL  em dash on /invite"; FAIL=1; else echo "  PASS  no em dashes on /invite"; fi
  JBAD=0
  for img in $(echo "$JOIN" | grep -oE 'src="\.\./[^"]+\.(jpg|png)"' | sed 's/src="\.\.\///;s/"//' | sort -u); do
    code=$(code "${LIVE}${img}")
    [ "$code" != "200" ] && JBAD=1 && echo "         missing on /invite: $img ($code)"
  done
  check "/invite assets resolve" $JBAD
  echo "$HTML" | grep -q 'class="creator-link" href="invite/"' ; check "creator link points at /invite" $?
  RD=$(code "${LIVE}join/")
  [ "$RD" = "200" ] ; check "old /join URL still resolves (redirects to /invite)" $?

  # 6. The signature form must be the real Action Network embed, not the old
  #    simulated one, which accepted input and stored nothing.
  echo "$HTML" | grep -q "widgets/v6/petition/teamhuman-pledge" ; check "hero form loads the Action Network widget" $?
  echo "$HTML" | grep -q "can-petition-area-teamhuman-pledge" ; check "widget has its target container" $?
  WCODE=$(code "https://actionnetwork.org/widgets/v6/petition/teamhuman-pledge?format=js&source=widget")
  [ "$WCODE" = "200" ] ; check "Action Network widget reachable (got $WCODE)" $?
  if echo "$HTML" | grep -qE 'id="firstName"|const COUNTRIES'; then
    echo "  FAIL  the simulated signup form is back (it stores nothing)"; FAIL=1
  else
    echo "  PASS  simulated signup form is gone"
  fi

  # 7. Creator admin: the team adds creators through this page + a published sheet.
  ADM=$(code "${LIVE}creators-admin.html")
  [ "$ADM" = "200" ] ; check "/creators-admin.html reachable" $?
  # The copy button must stay blocked while a handle is unverified, not just after a
  # failed lookup: an in-flight or hung avatar request is exactly when a bad row slips out.
  ADMHTML=$(curl -sfL --max-time 20 "${LIVE}creators-admin.html" 2>/dev/null)
  echo "$ADMHTML" | grep -q "Checking the channel" ; check "admin blocks copying while a handle is still unverified" $?
  echo "$ADMHTML" | grep -q "Check the handle first" ; check "admin blocks copying on a failed handle lookup" $?
  echo "$HTML" | grep -q "output=csv" ; check "site reads the creator sheet" $?
  SHEET_CSV=$(echo "$HTML" | grep -oE "https://docs.google.com/spreadsheets/d/e/[^']+pub\?output=csv" | head -1)
  if [ -n "$SHEET_CSV" ]; then
    CSVHEAD=$(curl -sfL --max-time 20 "$SHEET_CSV" 2>/dev/null | head -1 | tr -d '\r')
    echo "$CSVHEAD" | grep -q "youtube,name,followers,featured" ; check "creator sheet published and serving expected columns" $?
  else
    echo "  FAIL  could not find the published sheet URL in the page"; FAIL=1
  fi
  # The sheet supplements the roster; it must never be the only source, or a sheet
  # outage would empty the wall of creators.
  BAKED=$(echo "$HTML" | grep -c 'class="rn"')
  [ "$BAKED" -ge 35 ] ; check "roster still baked into the HTML ($BAKED chips, sheet is additive)" $?
  # unavatar must be asked for a hard 404 on a bad handle, not a generic placeholder face
  if echo "$HTML" | grep -q "unavatar.io"; then
    echo "$HTML" | grep -q "fallback=false" ; check "avatar lookups use fallback=false (no placeholder faces)" $?
  fi
fi

echo "======================"
if [ $FAIL -eq 0 ]; then echo "VERIFY: PASS"; else echo "VERIFY: FAIL"; exit 1; fi
