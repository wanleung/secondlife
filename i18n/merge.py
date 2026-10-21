#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Merge i18n/parts/*.jsonl ([id, en, ja, zh]; "=" means same as the Cantonese source) into en/ja/zh.json."""
import glob, json
from pathlib import Path
D = Path(__file__).resolve().parent
src = json.loads((D / 'source.json').read_text(encoding='utf-8'))
out = {'en': {}, 'ja': {}, 'zh': {}}
for f in sorted(glob.glob(str(D / 'parts' / '*.jsonl'))):
    for line in open(f, encoding='utf-8'):
        if not line.strip(): continue
        k, *vals = json.loads(line)
        if k not in src: continue  # stale
        for lang, v in zip(['en', 'ja', 'zh'], vals):
            out[lang][k] = src[k] if v == '=' else v
for lang, d in out.items():
    (D / f'{lang}.json').write_text(json.dumps(d, ensure_ascii=False, indent=0, sort_keys=True), encoding='utf-8')
print({l: len(d) for l, d in out.items()}, 'of', len(src))
