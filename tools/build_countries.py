#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Rebuild the COUNTRIES table in index.html from UN data.

Sources
- World Bank API (WDI), which republishes UN figures:
    SP.POP.TOTL     population            (UN WPP / national)
    SP.DYN.CBRT.IN  crude birth rate      (UN WPP)
    SH.DYN.MORT     under-5 mortality     (UN IGME)
    SP.DYN.LE00.IN  life expectancy       (UN WPP)
    NY.GNP.PCAP.CD  GNI per capita        (World Bank, Atlas method) -> game income scale
    NY.GDP.PCAP.CD  GDP per capita        fallback where GNI is missing
    country metadata: income group, region
- Our World in Data (UN WPP 2024) for Taiwan, which the World Bank does not list.
- Pew Research Center, Religious Composition by Country 2010-2020 (2025), via the
  Our World in Data download of the same dataset: share of population by religion
  in 2020 -> rel:[none, christian, muslim, hindu, buddhist, jewish, other] in %.
  "Other" is mostly folk religions (Chinese folk religion, Taoism), Sikhs, Baha'is etc.
  Territories Pew does not list fall back to REL_FALLBACK (a neighbour), marked rest:1.
- V-Dem Regimes of the World (via Our World in Data, political-regime), latest year:
  rg 0 closed autocracy, 1 electoral autocracy, 2 electoral democracy, 3 liberal democracy.
  Territories take their sovereign's value; small states V-Dem does not cover use
  RG_EST (our own judgement). Both are marked rgest:1.

Under-5 mortality is missing for Taiwan, Hong Kong, Macao and some small
territories (UN IGME does not publish them). For those we estimate it from
life expectancy with a log-linear fit over every country that has both, and
mark the row with est:1.

Income (g, US$ per person per year) falls back to GDP per capita, then to the
rough estimates in GNI_EST, then to the median of the same income group; any
fallback row is marked gest:1.

The war flag is a game design judgement, not data.

Usage: python3 tools/build_countries.py   (rewrites index.html in place)
"""
import csv, io, json, math, re, sys, urllib.request, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / 'index.html'
UA = {'User-Agent': 'Mozilla/5.0 (samsara-game data build)'}

def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read().decode('utf-8')

def wb(ind):
    rows = json.loads(get(f'https://api.worldbank.org/v2/country/all/indicator/{ind}?format=json&per_page=20000&mrnev=1'))[1]
    return {r['countryiso3code']: (r['value'], r['date']) for r in rows if r['value'] is not None}

def owid(slug, entity):
    text = get(f'https://ourworldindata.org/grapher/{slug}.csv?v=1&csvType=full&useColumnShortNames=true')
    best = None
    for row in csv.reader(io.StringIO(text)):
        if row and row[0] == entity and len(row) > 3 and row[3]:
            if best is None or int(row[2]) > int(best[0]):
                best = (row[2], float(row[3]))
    return best  # (year, value) of latest historical estimate

# Chinese names (Traditional, Taiwan-style transliteration to match the rest of the game)
ZH = {
 'ABW':'阿魯巴','AFG':'阿富汗','AGO':'安哥拉','ALB':'阿爾巴尼亞','AND':'安道爾','ARE':'阿聯酋','ARG':'阿根廷','ARM':'亞美尼亞',
 'ASM':'美屬薩摩亞','ATG':'安地卡及巴布達','AUS':'澳洲','AUT':'奧地利','AZE':'亞塞拜然','BDI':'蒲隆地','BEL':'比利時','BEN':'貝南',
 'BFA':'布吉納法索','BGD':'孟加拉','BGR':'保加利亞','BHR':'巴林','BHS':'巴哈馬','BIH':'波士尼亞與赫塞哥維納','BLR':'白俄羅斯','BLZ':'貝里斯',
 'BMU':'百慕達','BOL':'玻利維亞','BRA':'巴西','BRB':'巴貝多','BRN':'汶萊','BTN':'不丹','BWA':'波札那','CAF':'中非共和國',
 'CAN':'加拿大','CHE':'瑞士','CHI':'海峽群島','CHL':'智利','CHN':'中國','CIV':'象牙海岸','CMR':'喀麥隆','COD':'剛果民主共和國',
 'COG':'剛果共和國','COL':'哥倫比亞','COM':'葛摩','CPV':'維德角','CRI':'哥斯大黎加','CUB':'古巴','CUW':'古拉索','CYM':'開曼群島',
 'CYP':'賽普勒斯','CZE':'捷克','DEU':'德國','DJI':'吉布地','DMA':'多米尼克','DNK':'丹麥','DOM':'多明尼加','DZA':'阿爾及利亞',
 'ECU':'厄瓜多','EGY':'埃及','ERI':'厄利垂亞','ESP':'西班牙','EST':'愛沙尼亞','ETH':'衣索比亞','FIN':'芬蘭','FJI':'斐濟',
 'FRA':'法國','FRO':'法羅群島','FSM':'密克羅尼西亞','GAB':'加彭','GBR':'英國','GEO':'喬治亞','GHA':'迦納','GIB':'直布羅陀',
 'GIN':'幾內亞','GMB':'甘比亞','GNB':'幾內亞比索','GNQ':'赤道幾內亞','GRC':'希臘','GRD':'格瑞那達','GRL':'格陵蘭','GTM':'瓜地馬拉',
 'GUM':'關島','GUY':'蓋亞那','HKG':'香港','HND':'宏都拉斯','HRV':'克羅埃西亞','HTI':'海地','HUN':'匈牙利','IDN':'印尼',
 'IMN':'曼島','IND':'印度','IRL':'愛爾蘭','IRN':'伊朗','IRQ':'伊拉克','ISL':'冰島','ISR':'以色列','ITA':'義大利',
 'JAM':'牙買加','JOR':'約旦','JPN':'日本','KAZ':'哈薩克','KEN':'肯亞','KGZ':'吉爾吉斯','KHM':'柬埔寨','KIR':'吉里巴斯',
 'KNA':'聖克里斯多福及尼維斯','KOR':'南韓','KWT':'科威特','LAO':'寮國','LBN':'黎巴嫩','LBR':'賴比瑞亞','LBY':'利比亞','LCA':'聖露西亞',
 'LIE':'列支敦斯登','LKA':'斯里蘭卡','LSO':'賴索托','LTU':'立陶宛','LUX':'盧森堡','LVA':'拉脫維亞','MAC':'澳門','MAF':'法屬聖馬丁',
 'MAR':'摩洛哥','MCO':'摩納哥','MDA':'摩爾多瓦','MDG':'馬達加斯加','MDV':'馬爾地夫','MEX':'墨西哥','MHL':'馬紹爾群島','MKD':'北馬其頓',
 'MLI':'馬利','MLT':'馬爾他','MMR':'緬甸','MNE':'蒙特內哥羅','MNG':'蒙古','MNP':'北馬利安納群島','MOZ':'莫三比克','MRT':'茅利塔尼亞',
 'MUS':'模里西斯','MWI':'馬拉威','MYS':'馬來西亞','NAM':'納米比亞','NCL':'新喀里多尼亞','NER':'尼日','NGA':'奈及利亞','NIC':'尼加拉瓜',
 'NLD':'荷蘭','NOR':'挪威','NPL':'尼泊爾','NRU':'諾魯','NZL':'紐西蘭','OMN':'阿曼','PAK':'巴基斯坦','PAN':'巴拿馬',
 'PER':'秘魯','PHL':'菲律賓','PLW':'帛琉','PNG':'巴布亞紐幾內亞','POL':'波蘭','PRI':'波多黎各','PRK':'北韓','PRT':'葡萄牙',
 'PRY':'巴拉圭','PSE':'巴勒斯坦','PYF':'法屬玻里尼西亞','QAT':'卡達','ROU':'羅馬尼亞','RUS':'俄羅斯','RWA':'盧安達','SAU':'沙烏地阿拉伯',
 'SDN':'蘇丹','SEN':'塞內加爾','SGP':'新加坡','SLB':'索羅門群島','SLE':'獅子山','SLV':'薩爾瓦多','SMR':'聖馬利諾','SOM':'索馬利亞',
 'SRB':'塞爾維亞','SSD':'南蘇丹','STP':'聖多美普林西比','SUR':'蘇利南','SVK':'斯洛伐克','SVN':'斯洛維尼亞','SWE':'瑞典','SWZ':'史瓦帝尼',
 'SXM':'荷屬聖馬丁','SYC':'塞席爾','SYR':'敘利亞','TCA':'土克凱可群島','TCD':'查德','TGO':'多哥','THA':'泰國','TJK':'塔吉克',
 'TKM':'土庫曼','TLS':'東帝汶','TON':'東加','TTO':'千里達及托巴哥','TUN':'突尼西亞','TUR':'土耳其','TUV':'吐瓦魯','TZA':'坦尚尼亞',
 'UGA':'烏干達','UKR':'烏克蘭','URY':'烏拉圭','USA':'美國','UZB':'烏茲別克','VCT':'聖文森及格瑞那丁','VEN':'委內瑞拉','VGB':'英屬維京群島',
 'VIR':'美屬維京群島','VNM':'越南','VUT':'萬那杜','WSM':'薩摩亞','XKX':'科索沃','YEM':'葉門','ZAF':'南非','ZMB':'尚比亞',
 'ZWE':'辛巴威','TWN':'臺灣',
}

# Game-design flag (not data): ongoing armed conflict
WAR = set('COD MMR SDN SSD SOM SYR UKR YEM MLI BFA HTI PSE CAF LBY'.split())

# Region code -> name pool used by the game
REGION_OVERRIDE = {'CHN':'cn','HKG':'hk','MAC':'hk','TWN':'tw','JPN':'jp','KOR':'kr','PRK':'kr',
  'AUS':'west','NZL':'west','PAK':'sa','MLT':'west','ISR':'west',
  'RUS':'ru','UKR':'ru','BLR':'ru','MDA':'ru','KAZ':'ru','UZB':'ru','KGZ':'ru','TJK':'ru','TKM':'ru',
  'TUR':'me','AZE':'me','ARM':'ru','GEO':'ru','MNG':'cn'}
REGION_BY_WB = {'SAS':'sa','EAS':'sea','SSF':'af','MEA':'me','LCN':'la','ECS':'west','NAC':'west'}

# No World Bank/IMF series reachable for these; rough estimates, marked gest:1 in the game
GNI_EST = {
  'TWN': 34000,  # 行政院主計總處公布 2024 年平均每人 GNI 約 3.4 萬美元（約數）
  'PRK': 1200,   # 南韓央行估算北韓人均收入約 1,000–1,500 美元
}

PEW_ZIP = 'https://api.ourworldindata.org/v1/mdim-downloads/religious-composition.complete-dataset.zip'
REL_COLS = ['No religion','Christians','Muslims','Hindus','Buddhists','Jews','Other religions']
REL_CODE = {'XKX':'OWID_KOS','CHI':'OWID_CIS'}  # OWID's own codes
REL_FALLBACK = {  # Pew/OWID has no row for these small territories; borrow a neighbour
  'IMN':'GBR','GIB':'GBR','AND':'ESP','MCO':'FRA','SMR':'ITA','LIE':'CHE',
  'FRO':'DNK','GRL':'DNK','ATG':'BRB','DMA':'LCA','KNA':'BRB','CYM':'JAM','TCA':'BHS','BMU':'BHS',
  'VGB':'VIR','SXM':'CUW','MAF':'CUW','ASM':'WSM','MNP':'GUM','MHL':'FSM','PLW':'FSM','NRU':'KIR','TUV':'KIR',
}

def pew():
    with urllib.request.urlopen(urllib.request.Request(PEW_ZIP, headers=UA), timeout=120) as r:
        z = zipfile.ZipFile(io.BytesIO(r.read()))
    rows = list(csv.reader(io.TextIOWrapper(z.open('religious-composition.csv'), encoding='utf-8')))
    head = [h.replace('\n', '').strip() for h in rows[0]]
    idx = [head.index(f'Share of the population - {c}') for c in REL_COLS]
    out = {}
    for row in rows[1:]:
        if row[2] == '2020' and row[1]:
            out[row[1]] = [round(float(row[i] or 0), 1) for i in idx]
    return out

VDEM = 'https://ourworldindata.org/grapher/political-regime.csv?v=1&csvType=full&useColumnShortNames=true'
RG_ENTITY = {'XKX':'Kosovo', 'PSE':'Palestine/West Bank'}  # rows OWID lists by name only / without our code
RG_SOVEREIGN = {  # territories: same regime as the governing state
  'PRI':'USA','GUM':'USA','VIR':'USA','ASM':'USA','MNP':'USA','NCL':'FRA','PYF':'FRA','MAF':'FRA',
  'ABW':'NLD','CUW':'NLD','SXM':'NLD','CHI':'GBR','IMN':'GBR','GIB':'GBR','CYM':'GBR','BMU':'GBR','TCA':'GBR','VGB':'GBR',
  'GRL':'DNK','FRO':'DNK','MAC':'HKG',
}
RG_EST = {  # small independent states V-Dem does not cover; our judgement
  'BRN':0,  # absolute monarchy
  'BLZ':2,'WSM':2,'BHS':3,'KIR':2,'FSM':2,'TON':2,'LCA':3,'GRD':3,'VCT':3,'ATG':3,'MHL':2,'DMA':3,
  'AND':3,'KNA':3,'MCO':2,'LIE':3,'NRU':2,'TUV':2,'PLW':3,'SMR':3,
}

def vdem():
    by_code, by_name = {}, {}
    for r in csv.DictReader(io.StringIO(get(VDEM))):
        if r['regime_row_owid'] == '' or int(r['year']) < 2000: continue
        v = (int(r['year']), int(r['regime_row_owid']))
        for d, k in ((by_code, r['code']), (by_name, r['entity'])):
            if k and (k not in d or v[0] > d[k][0]): d[k] = v
    return by_code, by_name

def tier(income, gni):
    if income == 'LIC': return 1
    if income == 'LMC': return 2
    if income == 'UMC': return 3
    if income == 'HIC': return 4 if (gni is not None and gni < 30000) else 5
    return 3

def main():
    meta = [c for c in json.loads(get('https://api.worldbank.org/v2/country?format=json&per_page=400'))[1]
            if c['region']['value'] != 'Aggregates']
    pop, cbr, u5, le, gni, gdp = (wb(i) for i in ['SP.POP.TOTL','SP.DYN.CBRT.IN','SH.DYN.MORT','SP.DYN.LE00.IN','NY.GNP.PCAP.CD','NY.GDP.PCAP.CD'])

    rows = []
    for c in meta:
        k = c['id']
        if k not in pop or k not in cbr or k not in le:
            print('skip (missing data):', k, c['name'], file=sys.stderr); continue
        rows.append(dict(iso=k, pop=pop[k][0], births=pop[k][0]*cbr[k][0]/1000, le=le[k][0],
                         u5=u5[k][0] if k in u5 else None, inc=c['incomeLevel']['id'],
                         g=gni[k][0] if k in gni else (gdp[k][0] if k in gdp else GNI_EST.get(k)),
                         gest=k not in gni and k not in gdp,
                         t=tier(c['incomeLevel']['id'], gni.get(k, (None,))[0]),
                         reg=REGION_OVERRIDE.get(k, REGION_BY_WB.get(c['region']['id'], 'west'))))

    # Taiwan from OWID (UN WPP). High income per IMF/its own GNI (~US$33k), so tier 5.
    tw_pop = owid('population', 'Taiwan'); tw_b = owid('number-of-births-per-year', 'Taiwan'); tw_le = owid('life-expectancy', 'Taiwan')
    rows.append(dict(iso='TWN', pop=tw_pop[1], births=tw_b[1], le=tw_le[1], u5=None, t=5, reg='tw', inc='HIC', g=GNI_EST['TWN'], gest=True))

    # Remaining income gaps: median of same income group
    for r in rows:
        if r['g'] is None:
            peers = sorted(x['g'] for x in rows if x['inc']==r['inc'] and x['g'] is not None and not x['gest'])
            r['g'] = peers[len(peers)//2]

    # Fill missing under-5 mortality: log(u5) = a + b*le
    xs = [(r['le'], math.log(r['u5'])) for r in rows if r['u5']]
    n = len(xs); mx = sum(x for x,_ in xs)/n; my = sum(y for _,y in xs)/n
    b = sum((x-mx)*(y-my) for x,y in xs) / sum((x-mx)**2 for x,_ in xs); a = my - b*mx
    for r in rows:
        r['est'] = r['u5'] is None
        if r['est']: r['u5'] = math.exp(a + b*r['le'])

    REL = pew()
    for r in rows:
        k = r['iso']
        k = REL_CODE.get(k, k)
        r['rest'] = k not in REL
        r['rel'] = REL.get(k) or REL.get(REL_FALLBACK.get(k, ''))
        if r['rel'] is None: sys.exit(f'no religion data for {k}; add it to REL_FALLBACK')

    RG, RG_NAME = vdem()
    for r in rows:
        k = r['iso']
        hit = RG_NAME.get(RG_ENTITY[k]) if k in RG_ENTITY else RG.get(k)
        r['rgest'] = hit is None
        if hit: r['rg'] = hit[1]
        elif k in RG_SOVEREIGN: r['rg'] = RG[RG_SOVEREIGN[k]][1]
        elif k in RG_EST: r['rg'] = RG_EST[k]
        else: sys.exit(f'no regime data for {k}; add it to RG_SOVEREIGN or RG_EST')

    rows.sort(key=lambda r: -r['births'])
    lines = []
    for r in rows:
        f = [f"n:'{ZH[r['iso']]}'", f"iso:'{r['iso']}'", f"w:{round(r['births']/1000, 1)}", f"p:{round(r['pop']/1e6, 2)}",
             f"t:{r['t']}", f"g:{int(round(r['g'], -1))}", f"u5:{round(r['u5'], 1)}", f"le:{round(r['le'], 1)}", f"reg:'{r['reg']}'"]
        f.append('rel:[' + ','.join(f'{v:g}' for v in r['rel']) + ']')
        if r['rest']: f.append('rest:1')
        f.append(f"rg:{r['rg']}")
        if r['rgest']: f.append('rgest:1')
        if r['est']: f.append('est:1')
        if r['gest']: f.append('gest:1')
        if r['iso'] in WAR: f.append('war:1')
        lines.append('  {' + ','.join(f) + '},')

    yr_rg = max(v[0] for v in RG.values())
    yr_pop = max(v[1] for v in pop.values()); yr_b = max(v[1] for v in cbr.values())
    block = ("/* COUNTRIES:BEGIN — generated by tools/build_countries.py, do not edit by hand */\n"
             f"// w: 每年出生人數（千）, p: 人口（百萬）, g: 人均國民所得 US$（gest:1 = 估算）, u5: 五歲前死亡率 ‰（est:1 = 由預期壽命估算）, le: 預期壽命\n"
             f"// rel: 宗教人口比例 %（無宗教、基督教、伊斯蘭教、印度教、佛教、猶太教、其他／民間信仰；rest:1 = 借用鄰近地區）\n"
             f"// rg: V-Dem 政體 0 封閉專制、1 選舉專制、2 選舉民主、3 自由民主（rgest:1 = 按宗主國或估算）\n"
             f"// t: 經濟層級 1–5（世界銀行收入組別；高收入按人均國民所得再分兩級）, war: 遊戲設定\n"
             f"const DATA_SOURCE = '聯合國《世界人口展望》（出生、人口、壽命）及聯合國兒童死亡率估算小組（五歲前死亡率）、世界銀行（人均國民所得），經世界銀行及 Our World in Data 取得；宗教人口比例來自皮尤研究中心《各國宗教組成 2010–2020》（2020 年數字）；政體來自 V-Dem《世界政體分類》（{yr_rg} 年）；人口 {yr_pop}、出生及壽命 {yr_b}（臺灣為 {tw_b[0]}）。';\n"
             "const COUNTRIES = [\n" + '\n'.join(lines) + "\n];\n/* COUNTRIES:END */")
    html = HTML.read_text(encoding='utf-8')
    new, k = re.subn(r'/\* COUNTRIES:BEGIN.*?/\* COUNTRIES:END \*/', lambda m: block, html, flags=re.S)
    if k != 1: sys.exit('COUNTRIES markers not found in index.html')
    HTML.write_text(new, encoding='utf-8')
    print(f'{len(rows)} countries, {sum(r["births"] for r in rows)/1e6:.1f}M births/yr, '
          f'{sum(r["est"] for r in rows)} with estimated u5 (fit: ln u5 = {a:.2f} {b:+.4f}·le)')

if __name__ == '__main__':
    main()
