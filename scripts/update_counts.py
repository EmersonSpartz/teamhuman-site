#!/usr/bin/env python3
"""Refresh counts.json for teamhuman.org.

  total = Team Human signatures (our Action Network petition)
        + the Superintelligence Statement headline count
          (which already includes the 5,000 credited to Ekō's mirror petition)

Runs hourly in GitHub Actions (.github/workflows/counts.yml). Both sources are
parsed defensively: if a page changes shape or a number looks wrong, that
source keeps its last good value and the problem is recorded under "errors"
instead of publishing garbage. Exit code 2 = ran with errors (the workflow
still commits whatever was good, then turns the run red so someone looks).
"""
import datetime as dt
import html
import json
import os
import pathlib
import re
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "counts.json"
AN_PAGE = "https://actionnetwork.org/petitions/teamhuman-pledge"
AN_API = "https://actionnetwork.org/api/v2/petitions/70dd6a23-f948-4ebf-8fac-1f7b2e453e31/"
FLI_PAGE = "https://superintelligence-statement.org/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; TeamHumanCounter/1.0; +https://teamhuman.org)",
    "Accept": "text/html,application/json",
}


def fetch(url, extra=None):
    req = urllib.request.Request(url, headers={**HEADERS, **(extra or {})})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", "replace")


def find_key(obj, key):
    """Depth-first search for a key anywhere in nested JSON (Next.js moves things around)."""
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            hit = find_key(v, key)
            if hit is not None:
                return hit
    elif isinstance(obj, list):
        for v in obj:
            hit = find_key(v, key)
            if hit is not None:
                return hit
    return None


def visible_text(page):
    page = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", page, flags=re.S | re.I)
    page = re.sub(r"<[^>]+>", " ", page)
    return re.sub(r"\s+", " ", html.unescape(page))


def num(s):
    return int(s.replace(",", ""))


def team_human():
    """Our own petition. Uses the API when a key is present, else the public page's running total."""
    key = os.environ.get("ACTIONNETWORK_API_KEY")
    if key:
        data = json.loads(fetch(AN_API, {"OSDI-API-Token": key}))
        n = data.get("total_signatures")
        if not isinstance(n, int):
            raise ValueError("API response had no total_signatures")
        return n, "api"
    page = fetch(AN_PAGE)
    m = re.search(r"action_status_running_total[^>]*>\s*([\d,]+)\s+Signatures?", page, re.I)
    if not m:
        raise ValueError("running total not found on the petition page")
    return num(m.group(1)), "page"


FLI_DIRECT_API = "https://superintelligence-statement.org/api/signatureCount?letterName=asi-statement"
FLI_EKO_API = "https://superintelligence-statement.org/api/open/fli/ASIEkoCount"


def statement():
    """FLI's Superintelligence Statement. Returns (headline_total, direct, eko).

    The homepage HTML is statically prerendered and can lag by hours, so the two
    JSON endpoints the page itself calls after load are the source of truth; the
    HTML parse is only a fallback if those endpoints disappear.
    """
    try:
        direct = int(fetch(FLI_DIRECT_API).strip())
        eko = json.loads(fetch(FLI_EKO_API))["count"]
        if not isinstance(eko, int):
            raise ValueError("ASIEkoCount had no integer count")
        return direct + eko, direct, eko
    except Exception as api_err:
        page = fetch(FLI_PAGE)
        m = re.search(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', page, re.S)
        if not m:
            raise ValueError(f"API failed ({api_err}) and __NEXT_DATA__ missing")
        direct = find_key(json.loads(m.group(1)), "initialSignatureCount")
        if not isinstance(direct, int):
            raise ValueError(f"API failed ({api_err}) and initialSignatureCount missing")
        text = visible_text(page)
        eko_m = re.search(r"Including\s+([\d,]+)\s+from the same petition by Ek", text)
        eko = num(eko_m.group(1)) if eko_m else 0
        return direct + eko, direct, eko


def sane(name, new, prev, lo, hi, max_drop):
    if not (lo <= new <= hi):
        raise ValueError(f"{name}={new} is outside {lo}..{hi}")
    if isinstance(prev, int) and new < prev * (1 - max_drop):
        raise ValueError(f"{name} dropped from {prev} to {new}; refusing")
    return new


def main():
    prev = json.loads(OUT.read_text()) if OUT.exists() else {}
    out = {k: prev.get(k) for k in ("total", "teamhuman", "statement", "statement_direct", "eko", "updated")}
    errors = []
    try:
        n, how = team_human()
        out["teamhuman"] = sane("teamhuman", n, prev.get("teamhuman"), 0, 10**8, 0.5)
        out["teamhuman_source"] = how
    except Exception as e:  # keep last good value, report
        errors.append(f"teamhuman: {e}")
    try:
        total, direct, eko = statement()
        out["statement"] = sane("statement", total, prev.get("statement"), 50_000, 10**8, 0.10)
        out["statement_direct"], out["eko"] = direct, eko
    except Exception as e:
        errors.append(f"statement: {e}")

    if not isinstance(out["teamhuman"], int) or not isinstance(out["statement"], int):
        print("no usable numbers and nothing previous to fall back on:", errors, file=sys.stderr)
        return 1
    out["total"] = out["teamhuman"] + out["statement"]
    changed = any(out.get(k) != prev.get(k) for k in ("total", "teamhuman", "statement", "statement_direct", "eko"))
    if changed or not out.get("updated"):
        out["updated"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out["errors"] = errors
    out["about"] = ("total = Team Human signatures + Superintelligence Statement headline count "
                    "(which already includes Ekō's mirror petition). Refreshed hourly by GitHub Actions.")
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(f"total={out['total']:,}  teamhuman={out['teamhuman']}  statement={out['statement']:,} "
          f"(direct {out['statement_direct']:,} + eko {out['eko']:,})  changed={changed}  errors={errors}")
    return 2 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
