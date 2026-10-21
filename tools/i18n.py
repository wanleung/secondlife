#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build the English, Japanese and Standard Chinese editions from the Cantonese source.

The Cantonese files at the repo root (index.html, paths.html) are the source of truth.
This tool cuts them into translatable units, looks each unit up in i18n/<lang>.json,
and writes <lang>/index.html and <lang>/paths.html.

Units
- Inside <script>: every top-level JS string or template literal that contains CJK.
  Long templates (the HTML views) are split further: each CJK-bearing static chunk
  and each nested literal becomes its own unit.
- Outside <script>: every line that contains CJK, plus lines tagged with i18n-line.
A unit's id is a hash of its exact source text, so identical text always gets the
same translation. That matters: some strings double as lookup keys (job names,
talents), and they must translate identically everywhere.

Translations keep ${...} expressions verbatim; they may reorder them.
Missing translations fall back to the Cantonese text and are reported.

Translations live in i18n/parts/*.jsonl as [id, en, ja, zh] ("=" = same as source);
i18n/merge.py turns them into i18n/<lang>.json.

Usage
  python3 i18n/merge.py                # parts -> i18n/<lang>.json
  python3 tools/i18n.py extract        # write i18n/source.json (id -> text) and report gaps
  python3 tools/i18n.py build          # write en/, ja/, zh/
"""
import hashlib, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LANGS = ['en', 'ja', 'zh']
HTML_LANG = {'en': 'en', 'ja': 'ja', 'zh': 'zh-TW'}  # source pages are zh-HK (Cantonese); also picks the save slot
PAGES = ['index.html', 'paths.html']
CJK = re.compile('[\u3000-\u303f\u3040-\u30ff\u3400-\u9fff\uff00-\uffef]')  # CJK, kana and full-width punctuation
SPLIT_OVER = 400  # templates longer than this are split into chunks

def uid(text):
    return hashlib.sha1(text.encode('utf-8')).hexdigest()[:10]

# ---------- JS tokenizer ----------
REGEX_PREV = set('(,=:[!&|?{};+-*%<>~^')
REGEX_WORDS = ('return', 'typeof', 'case', 'in', 'of', 'delete', 'void', 'throw', 'new')

def read_string(src, i):
    q = src[i]; j = i + 1
    while src[j] != q:
        j += 2 if src[j] == '\\' else 1
    return j + 1

def read_template(src, i):
    """Return (end, parts) where parts are ('s', start, end) static chunks and ('e', start, end) expressions."""
    j = i + 1; parts = []; s0 = j
    while True:
        c = src[j]
        if c == '\\': j += 2; continue
        if c == '`':
            parts.append(('s', s0, j)); return j + 1, parts
        if c == '$' and src[j+1] == '{':
            parts.append(('s', s0, j))
            e0 = j + 2; j = skip_code(src, e0, '}')
            parts.append(('e', e0, j)); j += 1; s0 = j; continue
        j += 1

def prev_sig(src, i):
    k = i - 1
    while k >= 0 and src[k] in ' \t\r\n': k -= 1
    return k

def is_regex(src, i):
    k = prev_sig(src, i)
    if k < 0 or src[k] in REGEX_PREV: return True
    m = re.search(r'([A-Za-z_$][\w$]*)$', src[:k+1])
    return bool(m and m.group(1) in REGEX_WORDS)

def read_regex(src, i):
    j = i + 1; cls = False
    while True:
        c = src[j]
        if c == '\\': j += 2; continue
        if c == '[': cls = True
        elif c == ']': cls = False
        elif c == '/' and not cls: break
        j += 1
    j += 1
    while j < len(src) and (src[j].isalnum()): j += 1
    return j

def skip_code(src, i, stop=None, on_literal=None):
    """Scan code from i; stop at an unmatched `stop` char. Calls on_literal(start, end) for top-level literals."""
    depth = 0; j = i
    while j < len(src):
        c = src[j]
        if stop and c == stop and depth == 0: return j
        if c in '{([': depth += 1
        elif c in '})]': depth -= 1
        if c in '\'"':
            e = read_string(src, j)
            if on_literal: on_literal(j, e)
            j = e; continue
        if c == '`':
            e, _ = read_template(src, j)
            if on_literal: on_literal(j, e)
            j = e; continue
        if c == '/' and src[j+1] == '/':
            j = src.index('\n', j); continue
        if c == '/' and src[j+1] == '*':
            j = src.index('*/', j) + 2; continue
        if c == '/' and is_regex(src, j):
            j = read_regex(src, j); continue
        j += 1
    return j

def js_units(src, base):
    """Yield (start, end, text) for translatable pieces of a JS source string. Offsets are absolute (base + local)."""
    out = []
    def lit(s, e):
        raw = src[s:e]
        if not CJK.search(raw): return
        if raw[0] != '`' or len(raw) <= SPLIT_OVER:
            out.append((base + s, base + e, raw)); return
        _, parts = read_template(src, s)
        for kind, a, b in parts:
            if kind == 's':
                if CJK.search(src[a:b]): out.append((base + a, base + b, src[a:b]))
            else:
                skip_code(src, a, '}', on_literal=lambda x, y: lit(x, y))
    skip_code(src, 0, on_literal=lit)
    return out

# ---------- pages ----------
def units(page):
    html = (ROOT / page).read_text(encoding='utf-8')
    out = []
    scripts = []; k = html.find('<script>')
    while k >= 0:
        e = html.index('</script>', k); scripts.append((k, e)); k = html.find('<script>', e)
    st_open = html.find('<style>'); st_close = html.find('</style>')
    pos = 0
    for line in html.splitlines(keepends=True):
        a, b = pos, pos + len(line); pos = b
        if any(a > s and b <= e for s, e in scripts): continue
        if a > st_open and b <= st_close: continue  # CSS comments stay Cantonese
        if CJK.search(line) or 'i18n-line' in line:
            body = line.rstrip('\n')
            out.append((a, a + len(body), body))
    for s, e in scripts:
        start = s + len('<script>')
        out += js_units(html[start:e], start)
    out.sort()
    return html, out

def load(lang):
    p = ROOT / 'i18n' / f'{lang}.json'
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}

def extract():
    src = {}
    for page in PAGES:
        _, us = units(page)
        for _, _, t in us: src[uid(t)] = t
    (ROOT / 'i18n').mkdir(exist_ok=True)
    (ROOT / 'i18n' / 'source.json').write_text(json.dumps(src, ensure_ascii=False, indent=0), encoding='utf-8')
    print(f'{len(src)} units, {sum(len(CJK.findall(t)) for t in src.values())} CJK chars')
    for lang in LANGS:
        tr = load(lang)
        missing = [k for k in src if k not in tr]
        stale = [k for k in tr if k not in src]
        print(f'{lang}: {len(src) - len(missing)} translated, {len(missing)} missing, {len(stale)} stale')

def build():
    gaps = 0
    for lang in LANGS:
        tr = load(lang)
        (ROOT / lang).mkdir(exist_ok=True)
        for page in PAGES:
            html, us = units(page)
            out = []; last = 0
            for a, b, t in us:
                out.append(html[last:a]); out.append(tr.get(uid(t), t)); last = b
                if uid(t) not in tr: gaps += 1
            out.append(html[last:])
            page_out = ''.join(out).replace('<html lang="zh-HK">', f'<html lang="{HTML_LANG[lang]}">', 1)
            (ROOT / lang / page).write_text(page_out, encoding='utf-8')
    print('built', ', '.join(LANGS), f'({gaps} untranslated units fell back to Cantonese)' if gaps else '')

if __name__ == '__main__':
    {'extract': extract, 'build': build}[sys.argv[1] if len(sys.argv) > 1 else 'extract']()
