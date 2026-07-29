#!/usr/bin/env python3
"""Grade every visible sentence on the TeamHuman site for ease of understanding.

Usage:  python3 grade-copy.py [index.html]  ->  writes copy-report.html

Per sentence: Flesch-Kincaid grade level, passive-voice detection, length,
complex-word share. Letter grade A-F (A = anyone gets it on first read).
Also tests the "last sentence of each paragraph is the worst" hypothesis.
"""
import html.parser, re, sys, html as htmlmod

SRC = sys.argv[1] if len(sys.argv) > 1 else 'index.html'
OUT = 'copy-report.html'

BLOCK_TAGS = {'p', 'h1', 'h2', 'h3', 'h4', 'li', 'blockquote'}
BLOCK_DIV_CLASSES = {'plank', 'fog-quote', 'ph-note', 'also-label', 'demand-lead'}
SKIP_TAGS = {'script', 'style', 'svg', 'select', 'noscript'}

IRREGULAR_PARTICIPLES = {
    'built', 'made', 'kept', 'given', 'taken', 'written', 'known', 'shown',
    'held', 'left', 'lost', 'set', 'put', 'sent', 'told', 'found', 'brought',
    'caught', 'chosen', 'done', 'driven', 'drawn', 'gone', 'grown', 'heard',
    'hidden', 'led', 'meant', 'paid', 'run', 'said', 'seen', 'sold', 'spent',
    'spoken', 'stolen', 'thought', 'understood', 'won', 'reserved', 'locked',
}


class Extract(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.blocks = []          # (section, tag, text)
        self.section = 'top'
        self.buf = None
        self.block_depth = 0
        self.skip_depth = 0
        self.stack = []           # (tag, classes)

    VOID = {'img', 'br', 'hr', 'input', 'meta', 'link', 'source', 'area',
            'base', 'col', 'embed', 'param', 'track', 'wbr'}

    def handle_starttag(self, tag, attrs):
        if tag in self.VOID:
            if tag == 'br' and self.buf is not None:
                self.buf.append(' ')
            return
        a = dict(attrs)
        classes = set((a.get('class') or '').split())
        self.stack.append((tag, classes))
        if tag in ('section', 'header', 'footer') and a.get('id'):
            self.section = a['id']
        elif tag == 'footer':
            self.section = 'footer'
        if tag in SKIP_TAGS:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        parent_classes = self.stack[-2][1] if len(self.stack) >= 2 else set()
        is_block = (
            tag in BLOCK_TAGS
            or (tag == 'div' and (classes & BLOCK_DIV_CLASSES or 'litany' in parent_classes))
        )
        if is_block and self.buf is None:
            self.buf = []
            self.block_tag = tag + ('.' + '.'.join(sorted(classes)) if classes else '')
            self.block_depth = len(self.stack)

    def handle_endtag(self, tag):
        if self.stack and self.stack[-1][0] == tag:
            self.stack.pop()
        if tag in SKIP_TAGS:
            self.skip_depth = max(0, self.skip_depth - 1)
            return
        if self.buf is not None and len(self.stack) < self.block_depth:
            text = re.sub(r'\s+', ' ', ''.join(self.buf)).strip()
            if len(text.split()) >= 3:
                self.blocks.append((self.section, self.block_tag, text))
            self.buf = None

    def handle_data(self, data):
        if self.buf is not None and not self.skip_depth:
            self.buf.append(data)


def sentences(text):
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z“"‘“])', text)
    return [p.strip() for p in parts if len(p.split()) >= 4]


def syllables(word):
    w = re.sub(r'[^a-z]', '', word.lower())
    if not w:
        return 0
    groups = len(re.findall(r'[aeiouy]+', w))
    if w.endswith('e') and not w.endswith(('le', 'ee', 'ye')) and groups > 1:
        groups -= 1
    return max(1, groups)


def analyze(sent):
    words = re.findall(r"[A-Za-z][A-Za-z'’-]*", sent)
    n = len(words)
    if n == 0:
        return None
    syl = sum(syllables(w) for w in words)
    complex_words = [w for w in words if syllables(w) >= 3]
    fk = 0.39 * n + 11.8 * (syl / n) - 15.59
    passive = bool(re.search(
        r"\b(is|are|was|were|be|been|being)\b(\s+\w+ly)?\s+(\w+ed|" + '|'.join(IRREGULAR_PARTICIPLES) + r")\b",
        sent.lower()))
    reasons = []
    if passive:
        reasons.append('passive voice')
    if n > 25:
        reasons.append(f'long ({n} words)')
    if n and len(complex_words) / n > 0.25 and len(complex_words) >= 3:
        reasons.append(f'{len(complex_words)} complex words')
    score = fk + (2.5 if passive else 0) + (2 if n > 25 else 0)
    grade = 'A' if score <= 6 else 'B' if score <= 9 else 'C' if score <= 12 else 'D' if score <= 15 else 'F'
    return {'sent': sent, 'words': n, 'fk': round(fk, 1), 'passive': passive,
            'reasons': reasons, 'score': round(score, 1), 'grade': grade}


def main():
    parser = Extract()
    parser.feed(open(SRC, encoding='utf-8').read())
    results = []   # (section, tag, [sentence dicts])
    for section, tag, text in parser.blocks:
        graded = [g for g in (analyze(s) for s in sentences(text)) if g]
        if graded:
            results.append((section, tag, graded))

    all_s = [g for _, _, gs in results for g in gs]
    worst = sorted(all_s, key=lambda g: -g['score'])[:10]

    multi = [gs for _, _, gs in results if len(gs) >= 2]
    first_avg = sum(gs[0]['score'] for gs in multi) / len(multi) if multi else 0
    last_avg = sum(gs[-1]['score'] for gs in multi) / len(multi) if multi else 0

    colors = {'A': '#3f7d4e', 'B': '#7d9a3f', 'C': '#d69e45', 'D': '#c96f2f', 'F': '#b03a2e'}
    def chip(g):
        return (f'<span class="chip" style="background:{colors[g["grade"]]}">{g["grade"]}</span>')
    def esc(t):
        return htmlmod.escape(t)

    rows = []
    cur = None
    for section, tag, gs in results:
        if section != cur:
            rows.append(f'<h2>#{esc(section)}</h2>')
            cur = section
        cells = ''.join(
            f'<div class="s g{g["grade"]}">{chip(g)}<span class="txt">{esc(g["sent"])}</span>'
            f'<span class="meta">FK {g["fk"]} · {g["words"]}w'
            + (' · ' + ', '.join(g['reasons']) if g['reasons'] else '') + '</span></div>'
            for g in gs)
        rows.append(f'<div class="block"><div class="tag">{esc(tag)}</div>{cells}</div>')

    worst_rows = ''.join(
        f'<div class="s g{g["grade"]}">{chip(g)}<span class="txt">{esc(g["sent"])}</span>'
        f'<span class="meta">score {g["score"]} · ' + (', '.join(g['reasons']) or 'dense wording') + '</span></div>'
        for g in worst)

    counts = {k: sum(1 for g in all_s if g['grade'] == k) for k in 'ABCDF'}
    summary = ' · '.join(f'{k}: {v}' for k, v in counts.items())
    hypothesis = (f'First sentences avg score {first_avg:.1f} vs last sentences {last_avg:.1f} '
                  f'({"last IS worse" if last_avg > first_avg else "last is NOT worse"} across {len(multi)} multi-sentence blocks)')

    open(OUT, 'w', encoding='utf-8').write(f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>TeamHuman copy grades</title><style>
body{{font-family:-apple-system,sans-serif;background:#f6efe3;color:#201c17;max-width:880px;margin:40px auto;padding:0 20px;line-height:1.5}}
h1{{font-size:1.6rem}} h2{{margin:34px 0 10px;color:#ba5931;font-size:1.05rem;letter-spacing:.08em;text-transform:uppercase}}
.block{{background:#fbf6ec;border:1px solid rgba(94,70,48,.18);border-radius:10px;padding:14px 16px;margin-bottom:12px}}
.tag{{font-size:.68rem;color:#8a7c66;letter-spacing:.1em;margin-bottom:6px}}
.s{{display:flex;gap:10px;align-items:baseline;padding:6px 0;border-top:1px dashed rgba(94,70,48,.12)}}
.s:first-of-type{{border-top:none}}
.chip{{flex:none;color:#fff;font-weight:700;font-size:.72rem;border-radius:4px;padding:1px 7px}}
.txt{{flex:1}} .meta{{flex:none;font-size:.7rem;color:#8a7c66;max-width:200px;text-align:right}}
.gD .txt,.gF .txt{{font-weight:600}}
.banner{{background:#fbf6ec;border:1.5px dashed #5b7d8f;border-radius:10px;padding:12px 18px;margin:18px 0}}
</style></head><body>
<h1>Copy readability report</h1>
<p>{len(all_s)} sentences graded. {summary}</p>
<div class="banner"><strong>Hypothesis check:</strong> {hypothesis}</div>
<h2>Worst 10 sentences</h2><div class="block">{worst_rows}</div>
{''.join(rows)}
</body></html>""")
    print(f'{len(all_s)} sentences -> {OUT}')
    print(hypothesis)
    for g in worst[:5]:
        print(f'  [{g["grade"]} {g["score"]}] {g["sent"][:90]}')


main()
