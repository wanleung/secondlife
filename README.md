# 輪迴 Samsara

A browser game about reincarnation. You are reborn according to real-world birth statistics, live one life from birth to death, and the merit and sin you build up follow you into the next life.

**Play:** [粵語](https://www.wanleung.net/secondlife/) · [中文](https://www.wanleung.net/secondlife/zh/) · [English](https://www.wanleung.net/secondlife/en/) · [日本語](https://www.wanleung.net/secondlife/ja/)

**Life map** (every career, faith, regime and choice, with its karma): [粵語](https://www.wanleung.net/secondlife/paths.html) · [中文](https://www.wanleung.net/secondlife/zh/paths.html) · [English](https://www.wanleung.net/secondlife/en/paths.html) · [日本語](https://www.wanleung.net/secondlife/ja/paths.html)

## What it models

- **Birth:** 218 countries, weighted by UN birth counts. Most people are born poor. Higher karma lets you choose between several births.
- **Religion:** drawn from each country's real religious composition (Pew Research Center). Everyone is reborn whether they believe in it or not. Each faith has its own clergy ladder and its own way out of the cycle.
- **Politics:** each country's regime type comes from V-Dem's Regimes of the World. Democracies promote politicians by election. One-party states, monarchies, juntas and theocracies promote them through loyalty, family or faction. Protesting, dissent and Freemasonry carry different risks in each.
- **Money and migration:** pay scales with each country's GNI per capita. You can study abroad, work as a migrant, gain residency and naturalise.
- **Karma:** every choice is recorded as merit or sin. Some choices are good intentions with bad means, and they record both. After death, your new karma is 60% of your old karma plus this life's net.

## Repository layout

| Path | What it is |
|---|---|
| `index.html` | The game: one self-contained file, vanilla JavaScript, no backend. Saves to `localStorage`. **Cantonese source of truth.** |
| `paths.html` | The life map page (Cantonese source). |
| `en/`, `ja/`, `zh/` | Generated English, Japanese and Traditional Chinese editions. Do not edit by hand. |
| `og.png`, `*/og.png` | 1200×630 link-preview images. |
| `tools/build_countries.py` | Builds the `COUNTRIES` table from World Bank and Our World in Data downloads. |
| `tools/i18n.py` | Extracts translatable strings and builds the language editions. |
| `tools/og_image.py` | Draws the preview images. |
| `i18n/parts/*.jsonl` | Translations, one `[id, en, ja, zh]` row per string (`"="` means same as the source). |
| `i18n/merge.py` | Merges the parts into `i18n/{en,ja,zh}.json`. |

## Changing the game

Edit the Cantonese files at the repo root, then rebuild the other editions:

```sh
python3 tools/i18n.py extract   # lists new or changed strings
# add rows for the missing ids to a file in i18n/parts/
python3 i18n/merge.py
python3 tools/i18n.py build     # writes en/, ja/, zh/
```

Each string's id is a hash of its exact Cantonese text, so editing a string gives it a new id. Untranslated strings fall back to Cantonese, so a partial translation never breaks the game. Each language keeps its own save slot.

To redraw the preview images, install Pillow and the [LXGW WenKai TC](https://fonts.google.com/specimen/LXGW+WenKai+TC) font:

```sh
python3 tools/og_image.py LXGWWenKaiTC-Bold.ttf LXGWWenKaiTC-Regular.ttf
```

The site is served from the `main` branch with GitHub Pages.

## Translations

The English, Japanese and Traditional Chinese editions have not yet been reviewed by native speakers. Corrections are welcome as issues or pull requests against `i18n/parts/`.

## Data sources

The game embeds figures derived from the following data. These figures keep their original licences, and attribution is required:

| Data | Source | Licence |
|---|---|---|
| Population, birth rate, life expectancy | United Nations, *World Population Prospects*, via World Bank (Taiwan via Our World in Data) | CC BY 3.0 IGO / CC BY 4.0 |
| Under-five mortality | UN Inter-agency Group for Child Mortality Estimation, via World Bank | CC BY 4.0 |
| GNI per capita, income groups | World Bank, World Development Indicators | CC BY 4.0 |
| Religious composition, 2010–2020 | Pew Research Center, via Our World in Data | CC BY 4.0 (as published by OWID); used with attribution to Pew Research Center |
| Regime type | V-Dem Institute, *Regimes of the World*, via Our World in Data | CC BY-SA 4.0 |

Our World in Data's own processing is CC BY 4.0. Political sub-types (one-party, monarchy, junta and so on), Freemasonry bans, war zones and event odds are game settings, not data.

## Disclaimer

This is a work of fiction. "Everyone is reborn" is a game rule, not a statement about any religion, belief or non-belief. Clergy, holy places, afterlife scenes, Freemasonry and national politics are simplified and fictionalised. They do not represent any doctrine, lodge, nation or group.

## Licence

Copyright © 2026 Wan Leung Wong

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version. See [`LICENSE`](LICENSE).

This covers the code, story text and translations. The embedded data keeps the licences listed above. Fonts are loaded from Google Fonts under the SIL Open Font License, and are not part of this repository.
