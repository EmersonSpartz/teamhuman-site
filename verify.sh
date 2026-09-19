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

# 9. Live signature counter: the hero number must come from counts.json (Team Human
# + Superintelligence Statement), never from the old simulated counter.
echo "$HTML" | grep -q "fetch('counts.json'" ; check "hero counter reads counts.json" $?
echo "$HTML" | grep -q "this count is simulated" ; [ $? -ne 0 ] ; check "simulated-counter copy is gone" $?
echo "$HTML" | grep -q "total += 1" ; [ $? -ne 0 ] ; check "fake heartbeat tick is gone" $?
if curl -sf --max-time 10 -o /dev/null "$LIVE"; then
  COUNTS=$(curl -sfL --max-time 20 "${LIVE}counts.json" 2>/dev/null)
  [ -n "$COUNTS" ] ; check "counts.json is served live" $?
  python3 - "$COUNTS" <<'PYEOF'
import json, sys
try:
    d = json.loads(sys.argv[1])
    ok = isinstance(d.get("total"), int) and d["total"] >= 70000 and isinstance(d.get("teamhuman"), int) and d["teamhuman"] >= 1 and d["total"] == d["teamhuman"] + d["statement"]
    print(f"  {'ok  ' if ok else 'FAIL'}  counts.json adds up: {d.get('teamhuman')} + {d.get('statement')} = {d.get('total')}")
    sys.exit(0 if ok else 1)
except Exception as e:
    print("  FAIL  counts.json unreadable:", e); sys.exit(1)
PYEOF
  [ $? -eq 0 ] || FAIL=1
fi
[ -f .github/workflows/counts.yml ] && [ -x scripts/update_counts.py ] ; check "hourly counts workflow + script present" $?

# 10. Sign-up guard: Action Network's own failure path posts the form raw into a
# new tab (their 500 page). Our guard must hold early submits and replace that
# fallback; both pieces have to be in the live page.
echo "$HTML" | grep -q "function anWired" ; check "sign-up guard (anWired) present" $?
echo "$HTML" | grep -q "form.submit = function" ; check "raw-submit fallback overridden" $?
echo "$HTML" | grep -q "th-fallback" ; check "fallback message styles present" $?

# 11. After signing, people land on /act directly (no popup). The act page carries
# the short copy Emerson asked for and the share row that used to live in the modal.
echo "$HTML" | grep -q "location.assign('act/')" ; check "sign-up success redirects to /act" $?
echo "$HTML" | grep -q "thanksVeil" ; [ $? -ne 0 ] ; check "post-signup modal is gone" $?
ACT=$(curl -sfL --max-time 20 "${LIVE}act/" 2>/dev/null)
echo "$ACT" | grep -q "<h1>What to do next</h1>" ; check "act page: plain 'What to do next' heading" $?
echo "$ACT" | grep -q "Drop comments on your favorite creators" ; check "act page: one-line creator ask" $?
echo "$ACT" | grep -q "Change your profile photo to Team Human for 30 days" ; check "act page: one-line profile-photo ask" $?
echo "$ACT" | grep -q 'id="phoneBlock" style' && ! echo "$ACT" | grep -q 'togglePhone' ; check "act page: phone script shown, not behind a click" $?
echo "$ACT" | grep -q 'twitter.com/intent/tweet' ; check "act page: share row present" $?

# 12. Creator kit: /kit is the web version, the PDF sits next to it, and the invite
# page points at it (the "send your toolkit" line is gone).
KIT=$(curl -sfL --max-time 20 "${LIVE}kit/" 2>/dev/null)
echo "$KIT" | grep -q "Things you can talk about" ; check "kit page live with the talking points" $?
echo "$KIT" | grep -q 'href="TeamHuman-Creator-Kit.pdf"' ; check "kit page links the PDF" $?
PDFTYPE=$(curl -sIL --max-time 20 "${LIVE}kit/TeamHuman-Creator-Kit.pdf" 2>/dev/null | grep -i "^content-type" | tail -1)
echo "$PDFTYPE" | grep -qi "application/pdf" ; check "kit PDF served as PDF" $?
INV=$(curl -sfL --max-time 20 "${LIVE}invite/" 2>/dev/null)
echo "$INV" | grep -q "send your toolkit" ; [ $? -ne 0 ] ; check "invite: toolkit line removed" $?
echo "$INV" | grep -q 'href="../kit/"' ; check "invite links to the kit" $?
IV=$(curl -sfL --max-time 20 "${LIVE}invitevideo/" 2>/dev/null)
echo "$IV" | grep -q "drive.google.com/drive/folders/1ABYVXtB6sZLTl5WjJNr1AwkNAub8ShTx" ; check "/invitevideo forwards to the Drive folder" $?

# 13. Profile-frame maker: /frame page, the shared script, and the act page embed.
FR=$(curl -sfL --max-time 20 "${LIVE}frame/" 2>/dev/null)
echo "$FR" | grep -q 'THFrame.mount' ; check "frame page mounts the tool" $?
FJS=$(curl -sfL --max-time 20 "${LIVE}frame.js" 2>/dev/null)
echo "$FJS" | grep -q "SLOW DOWN AI" && echo "$FJS" | grep -q "#TEAMHUMAN" ; check "frame.js live with the ring copy" $?
echo "$ACT" | grep -q 'id="frameTool"' ; check "act page embeds the frame tool" $?
echo "$ACT" | grep -q 'teamhuman-pfp-parchment' ; [ $? -ne 0 ] ; check "act page: old handprint tiles gone" $?

echo "======================"
if [ $FAIL -eq 0 ]; then echo "VERIFY: PASS"; else echo "VERIFY: FAIL"; exit 1; fi
