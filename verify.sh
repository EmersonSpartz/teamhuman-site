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
echo "$HTML" | grep -q "AI should serve"              ; check "statement band present" $?
if echo "$HTML" | grep -qi "corporate arms race"; then echo "  FAIL  stale Figma copy leaked"; FAIL=1; else echo "  PASS  no stale Figma copy"; fi
if echo "$HTML" | grep -q "—"; then echo "  FAIL  em dash found (Emerson: AI slop coded)"; FAIL=1; else echo "  PASS  no em dashes"; fi

# 2. All referenced images resolve (against live host when live)
if [ "$SRC" != "local" ]; then
  IMGS=$(echo "$HTML" | grep -oE 'src="[^"]+\.(jpg|png)"' | sed 's/src="//;s/"//' | sort -u)
  BAD=0
  for img in $IMGS; do
    code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "${LIVE}${img}")
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
  JOIN=$(curl -sfL --max-time 20 "${LIVE}join/" 2>/dev/null)
  [ -n "$JOIN" ] ; check "/join reachable" $?
  echo "$JOIN" | grep -q "docs.google.com/forms" ; check "/join embeds the creator form" $?
  echo "$JOIN" | grep -q "over the finish line" ; check "/join copy present" $?
  # The form link must be reachable for invited creators: this page is intentionally ungated.
  if echo "$JOIN" | grep -q "gate.js"; then echo "  FAIL  /join is gated (creators with the link would be locked out)"; FAIL=1; else echo "  PASS  /join ungated (by design)"; fi
  if echo "$JOIN" | grep -q "—"; then echo "  FAIL  em dash on /join"; FAIL=1; else echo "  PASS  no em dashes on /join"; fi
  JBAD=0
  for img in $(echo "$JOIN" | grep -oE 'src="\.\./[^"]+\.(jpg|png)"' | sed 's/src="\.\.\///;s/"//' | sort -u); do
    code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "${LIVE}${img}")
    [ "$code" != "200" ] && JBAD=1 && echo "         missing on /join: $img ($code)"
  done
  check "/join assets resolve" $JBAD
fi

echo "======================"
if [ $FAIL -eq 0 ]; then echo "VERIFY: PASS"; else echo "VERIFY: FAIL"; exit 1; fi
