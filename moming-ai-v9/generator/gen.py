#!/usr/bin/env python3
"""《莫名其妙的AI》v9 prompt 生成器：data/*.txt（页面内容） -> out/*.txt（每份4页的出图prompt）"""
import glob, os, re, sys, shutil

ROOT = os.path.dirname(os.path.abspath(__file__))
HEADER = open(os.path.join(ROOT, 'header.txt'), encoding='utf8').read().rstrip('\n')
COLORS = {'纸白': '#FAF8F2', '芥末黄': '#EBC85C', '雾霾蓝': '#8FB0C4', '砖红': '#C4483C',
          '深石墨灰': '#3A3F45', '灰绿': '#8FA882'}
DARK = {'深石墨灰', '砖红'}
BAR = '─' * 44
EQ = '=' * 60
KEY = re.compile(r'^([A-Z][A-Z0-9]*)(\*?):\s?(.*)$')

errors, warns = [], []


def parse():
    pages, ch, sec = [], '', ''
    for f in sorted(glob.glob(os.path.join(ROOT, 'data', '*.txt'))):
        cur, key = None, None
        for ln, raw in enumerate(open(f, encoding='utf8').read().split('\n'), 1):
            line = raw.rstrip()
            if line.startswith('#CH '):
                parts = [s.strip() for s in line[4:].split('|')]
                ch = parts[0]
                sec = parts[1] if len(parts) > 1 else parts[0]
                continue
            if line.startswith('#P '):
                parts = [s.strip() for s in line[3:].split('|')]
                while len(parts) < 4:
                    parts.append('-')
                cur = {'id': parts[0], 'layout': parts[1], 'type': parts[2], 'bg': parts[3],
                       'ch': ch, 'sec': sec, 'fields': [], 'src': f'{os.path.basename(f)}:{ln}'}
                pages.append(cur)
                key = None
                continue
            if line.startswith('//') or cur is None:
                continue
            m = KEY.match(line)
            if m:
                key = m.group(1)
                cur['fields'].append([key, m.group(3)])
            elif key is not None and line.strip():
                cur['fields'][-1][1] += '\n' + line
    return pages


def get(p, k, default=None):
    for kk, v in p['fields']:
        if kk == k:
            return v
    return default


def getall(p, k):
    return [v for kk, v in p['fields'] if kk == k]


def clen(s):
    return len(re.sub(r'\s', '', s))


def check(p, what, s, limit):
    if s is not None and clen(s) > limit:
        errors.append(f"P{p['n']:03d} {p['id']} {what} 超长 {clen(s)}>{limit}：{s[:30]}…")


def pno(n):
    return f'{n:02d}'


def safe(p):
    return (210, 1610) if p['n'] % 2 else (150, 1550)


def side(p):
    return '奇数页（右手页）' if p['n'] % 2 else '偶数页（左手页）'


def footer(p, dark):
    col = '米白' if dark else '墨黑'
    src = get(p, 'SRC')
    name = src if src else p['ch']
    if get(p, 'NOFOOT') is not None:
        return 'F 页脚：本页不排页脚。'
    if p['n'] % 2:
        return f"F 页脚（F级{col}，页码Bold）：右止「{name}　{pno(p['n'])}」"
    return f"F 页脚（F级{col}，页码Bold）：左起「{pno(p['n'])}　{name}」"


def canvas(p, extra):
    a, b = safe(p)
    return f"竖版单页，比例176:246，设计坐标1760×2460。{side(p)}，安全区 x {a}–{b}、y 180–2280。{extra}"


def bubbles(p, limit=2, total=45):
    out, tot = [], 0
    qs = getall(p, 'Q')
    for q in qs:
        who, _, txt = q.partition('：')
        tot += clen(txt)
        out.append(f"气泡（D级）　{who.strip()}：「{txt.strip()}」")
    if len(qs) > limit:
        errors.append(f"P{p['n']:03d} {p['id']} 气泡 {len(qs)} 个，超过 {limit}")
    if tot > total:
        errors.append(f"P{p['n']:03d} {p['id']} 对白合计 {tot} 字，超过 {total}")
    return out


def eslot(p, must=True):
    e = get(p, 'E')
    if e is None:
        if must:
            errors.append(f"P{p['n']:03d} {p['id']} 缺少机动栏 E")
        return []
    a = [s.strip() for s in e.split('|')]
    t = a[0]
    if t == '名词卡':
        if len(a) != 6:
            errors.append(f"P{p['n']:03d} 名词卡字段数不对：{e}")
            return []
        check(p, '名词卡定义', a[3], 22)
        p['term'] = (a[1], a[2], a[3], a[4])
        return [f"E 机动栏·名词卡（砖红竖条）：行1「{a[1]}」＋「{a[2]}」；行2「{a[3]}」；行3左「{a[4]}」，右端「{a[5]}」"]
    if t == '课本连接':
        check(p, '课本连接正文', a[2], 44)
        p['link'] = (a[1], a[2])
        return [f"E 机动栏·课本连接（雾霾蓝竖条）：栏目名「课本连接」，标题（S级）「{a[1]}」；正文（B级）「{a[2]}」"]
    if t == '成语':
        check(p, '成语正文', a[2], 44)
        p['idiom'] = (a[1], a[2])
        return [f"E 机动栏·成语里的AI（芥末黄竖条）：栏目名「成语里的AI」，标题（S级）「{a[1]}」；正文（B级）「{a[2]}」"]
    if t == '冷知识':
        check(p, '冷知识正文', a[1], 44)
        return [f"E 机动栏·墨团冷知识（深石墨灰竖条）：栏目名「墨团冷知识」＋猫爪印小图标；正文（B级）「{a[1]}」"]
    if t == '试一试':
        check(p, '试一试正文', a[1], 44)
        return [f"E 机动栏·试一试（灰绿竖条）：栏目名「试一试」＋铅笔小图标；正文（B级）「{a[1]}」"]
    if t == '翻页':
        check(p, '翻页正文', a[1], 40)
        return [f"E 机动栏·翻页（砖红竖条）：栏目名「翻页之前」；正文（B级）「{a[1]}」，句末一个砖红箭头「→」"]
    errors.append(f"P{p['n']:03d} 未知机动栏类型：{t}")
    return []


def redline(p, c):
    r = get(p, 'R')
    if r is None:
        return []
    if r not in c:
        errors.append(f"P{p['n']:03d} {p['id']} 强调句不在导语里：{r}")
    return [f"　其中「{r}」一句用B级Bold砖红。"]


def bgline(p):
    bg = p['bg']
    if bg not in COLORS:
        errors.append(f"P{p['n']:03d} {p['id']} 底色不在色库：{bg}")
        return bg
    return f"{bg} {COLORS[bg]}"


def render(p):
    L, lay = [], p['layout']
    V = get(p, 'V', '')
    if lay == 'T1':
        L.append(canvas(p, '严格按总则版式T1。'))
        L.append(f"A 主视觉区（y 0–1150）底色：{bgline(p)}")
        L += V.split('\n') if V else []
        L += bubbles(p)
        b, c, d = get(p, 'B'), get(p, 'C'), get(p, 'D')
        check(p, '主标题', b, 14); check(p, '导语', c, 70); check(p, '再想一层', d, 64)
        L.append(f"B 主标题（T级墨黑）：「{b}」")
        L.append(f"C 导语（B级墨黑）：「{c}」")
        L += redline(p, c)
        L.append(f"D 再想一层（B级墨黑）：「{d}」")
        L += eslot(p)
        L.append(footer(p, False))
    elif lay == 'T2':
        L.append(canvas(p, '严格按总则版式T2，全页纸白#FAF8F2，不出现三位主角、无气泡。'))
        b, s = get(p, 'B'), get(p, 'S')
        check(p, '主标题', b, 14); check(p, '副标题', s, 24)
        L.append(f"栏目标签：「{get(p, 'TAG')}」")
        L.append(f"主标题（T级）：「{b}」")
        if s:
            L.append(f"副标题（B级）：「{s}」")
        pc = get(p, 'PC')
        if pc:
            L.append(f"人物卡（y 500–950）：{pc}")
            L.append("模块区（y 1000–2280）：")
        else:
            L.append("模块区（y 500–2280）：")
        L += get(p, 'M', '').split('\n')
        e = eslot(p, must=False)
        if e:
            L.append("页面底部（y 2040–2280）放一张机动栏卡，规格同T1的E区；模块区内容止于 y 2015：")
            L += e
        L.append(footer(p, False))
    elif lay == 'T3':
        L.append(canvas(p, '严格按总则版式T3，全页深石墨灰#3A3F45，字为米白，无角色。'))
        L.append(f"章节标签：「{get(p, 'TAG', p['ch'])}」")
        L.append("「你已经知道：」")
        k = [s.strip() for s in re.split(r'[|｜]', get(p, 'K'))]
        for x in k:
            check(p, '已知', x, 22)
        L.append("已知两行：" + ''.join(f"「{x}」" for x in k))
        L.append(f"问题条：「{get(p, 'QBAR')}」")
        L.append("列表区（每行问题＋右端页码）：")
        for it in getall(p, 'L'):
            q, _, pg = it.partition('|')
            check(p, '列表问题', q, 19)
            L.append(f"　「{q.strip()}」　「{pg.strip()}」")
        L.append(f"收尾句：「{get(p, 'END')}」")
        L.append(footer(p, True))
    elif lay == 'T4':
        bg = p['bg']
        if bg not in ('深石墨灰', '砖红', '纸白'):
            errors.append(f"P{p['n']:03d} T4 底色只能是深石墨灰/砖红/纸白")
        dark = bg in DARK
        col = '米白' if dark else '墨黑'
        L.append(canvas(p, '严格按总则版式T4。'))
        L.append(f"全页底色：{bgline(p)}，纯色平涂铺满到页面四边。无角色、无气泡。")
        tag = get(p, 'TAG')
        if tag:
            L.append(f"章节标签（y 180–240，砖红色块内G级米白字）：「{tag}」")
        h = get(p, 'H')
        if h:
            hs = [s.strip() for s in re.split(r'[|｜]', h)]
            for x in hs:
                check(p, '大字', x, 11)
            L.append(f"大字（H级{col}）：" + ''.join(f"「{x}」" for x in hs))
        else:
            L.append("本页无大字。")
        ic = get(p, 'ICON')
        L.append(f"小图标（y 1500–1660）：{ic}" if ic else "小图标：无。")
        L.append("其余区域为纯色背景，不放任何文字或图形。")
        L.append(footer(p, dark))
    elif lay in ('T5L', 'T5R'):
        left = lay == 'T5L'
        if left and p['n'] % 2:
            errors.append(f"P{p['n']:03d} {p['id']} 跨页左半落在奇数页")
        if not left and not p['n'] % 2:
            errors.append(f"P{p['n']:03d} {p['id']} 跨页右半落在偶数页")
        mate = p['n'] + 1 if left else p['n'] - 1
        L.append(canvas(p, f"整幅跨页的{'左' if left else '右'}半页，与P{mate:03d}拼成整幅跨页，严格按总则版式T5与第二条跨页衔接规则。"))
        L.append(f"主视觉区（y 0–1840）底色：{bgline(p)}")
        tag = get(p, 'TAG')
        if tag:
            L.append(f"章节标签（y 180–240，砖红色块内G级米白字）：「{tag}」")
        L += V.split('\n') if V else []
        L += bubbles(p)
        if left:
            b, c = get(p, 'B'), get(p, 'C')
            check(p, '主标题', b, 14); check(p, '导语', c, 46)
            L.append(f"文字带主标题（T级墨黑）：「{b}」")
            if c:
                L.append(f"文字带导语（B级墨黑，最多2行）：「{c}」")
        else:
            c, r = get(p, 'C'), get(p, 'R')
            check(p, '续文', c, 46); check(p, '强调句', r, 23)
            L.append(f"文字带续文（B级墨黑，最多2行）：「{c}」")
            L.append(f"强调句（B级Bold砖红）：「{r}」")
        L.append(footer(p, False))
    elif lay in ('T6L', 'T6R'):
        left = lay == 'T6L'
        if left and p['n'] % 2:
            errors.append(f"P{p['n']:03d} {p['id']} 漫画左页落在奇数页")
        if not left and not p['n'] % 2:
            errors.append(f"P{p['n']:03d} {p['id']} 漫画右页落在偶数页")
        mate = p['n'] + 1 if left else p['n'] - 1
        L.append(canvas(p, f"漫画页「墨团剧场」{'左页' if left else '右页'}，与P{mate:03d}是同一出戏，严格按总则版式T6与第十条戏服规则。"))
        acc = p['bg']
        L.append(f"全页纸白#FAF8F2。格内点缀色：{bgline(p)}。")
        if left:
            b = get(p, 'B'); check(p, '剧名', b, 14)
            L.append("栏目标签：「墨团剧场」")
            L.append(f"剧名（T级墨黑）：「{b}」")
            L.append(f"演员表（C级墨黑，单行）：「{get(p, 'CAST')}」")
            for i, yy in ((1, '470–1050'), (2, '1090–1670'), (3, '1710–2280')):
                g = get(p, f'G{i}')
                L.append(f"格{i}（y {yy}）：" + g)
        else:
            L.append("栏目标签：「墨团剧场　接上页」")
            for i, yy in ((4, '270–830'), (5, '870–1430')):
                g = get(p, f'G{i}')
                L.append(f"格{i}（y {yy}）：" + g)
            xt, x = get(p, 'XT'), get(p, 'X')
            check(p, '戏外话标题', xt, 22); check(p, '戏外话正文', x, 110)
            L.append("「戏外话」底板（y 1480–2280）：")
            L.append(f"　小标题（S级墨黑）：「{xt}」")
            L.append(f"　正文（B级墨黑，最多5行）：「{x}」")
            r = get(p, 'R')
            if r:
                if r not in x:
                    errors.append(f"P{p['n']:03d} 戏外话强调句不在正文里")
                L.append(f"　其中「{r}」一句用B级Bold砖红。")
            L.append(f"　故事出处（F级墨黑）：「{get(p, 'ORI')}」")
        for i in range(1, 6):
            g = get(p, f'G{i}')
            if g:
                nb = len(re.findall(r'气泡', g))
                if nb > 2:
                    errors.append(f"P{p['n']:03d} 格{i} 气泡 {nb} 个")
                for m in re.finditer(r'气泡　[^：]+：「([^」]*)」', g):
                    check(p, f'格{i}气泡', m.group(1), 20)
                for m in re.finditer(r'旁白条：「([^」]*)」', g):
                    check(p, f'格{i}旁白', m.group(1), 22)
        L.append(footer(p, False))
    elif lay == 'T7':
        L.append(canvas(p, '严格按总则版式T7「硬核时间」，不出现三位主角、无气泡。'))
        b, c = get(p, 'B'), get(p, 'C')
        check(p, '主标题', b, 14); check(p, '导语', c, 46)
        L.append(f"栏目标签：「{get(p, 'TAG')}」")
        L.append(f"主标题（T级米白，在深石墨灰顶带内）：「{b}」")
        L.append(f"导语（B级墨黑，最多2行）：「{c}」")
        L += redline(p, c)
        L.append("图示区（y 740–1500）：")
        L += get(p, 'M', '').split('\n')
        calc = getall(p, 'CALC')
        if len(calc) > 4:
            errors.append(f"P{p['n']:03d} 算一算超过4行")
        for x in calc:
            check(p, '算一算', x, 24)
        L.append("「算一算」底板（y 1540–2015），B级墨黑，逐行照排：" + ''.join(f"「{x}」" for x in calc))
        e = eslot(p)
        if 'link' not in p:
            errors.append(f"P{p['n']:03d} T7 的机动栏必须是课本连接")
        L += e
        L.append(footer(p, False))
    elif lay == 'T8':
        if p['n'] % 2:
            errors.append(f"P{p['n']:03d} {p['id']} 章首页落在奇数页")
        L.append(canvas(p, '严格按总则版式T8章首悬案页。'))
        L.append(f"主视觉区（y 0–1700）底色：{bgline(p)}")
        L.append(f"章号牌：米白圆牌内墨黑大数字「{get(p, 'NUM')}」")
        L.append(f"悬案标签（砖红色块内G级米白字）：「{get(p, 'CASE')}」")
        L += V.split('\n') if V else []
        L += bubbles(p)
        hs = [s.strip() for s in re.split(r'[|｜]', get(p, 'H'))]
        for x in hs:
            check(p, '悬念大字', x, 11)
        c = get(p, 'C'); check(p, '引子', c, 24)
        L.append("悬念大字（H级墨黑）：" + ''.join(f"「{x}」" for x in hs))
        L.append(f"引子（B级墨黑，单行）：「{c}」")
        L.append(footer(p, False))
    elif lay == 'X':
        a, b = safe(p) if p['n'] > 0 else (150, 1610)
        if p['n'] > 0:
            L.append(canvas(p, get(p, 'NOTE', '本页为特殊版式，按下列位置排。')))
        else:
            L.append(f"竖版单页，比例176:246，设计坐标1760×2460。文字与关键图形放在 x 150–1610、y 180–2280。{get(p, 'NOTE', '')}")
        L += get(p, 'RAW', '').split('\n')
        L += bubbles(p, limit=3, total=60)
        if p['n'] > 0:
            dark = get(p, 'DARKFOOT') is not None
            L.append(footer(p, dark))
    else:
        errors.append(f"{p['id']} 未知版式 {lay}")
    return L


def title_of(p):
    for k in ('B', 'H', 'NAME'):
        v = get(p, k)
        if v:
            return v.replace('|', '').replace('｜', '')
    return ''


def main():
    pages = parse()
    n = 0
    ids = {}
    for p in pages:
        if p['type'] in ('封面', '封底'):
            p['n'] = 0
        else:
            n += 1
            p['n'] = n
        if p['id'] in ids:
            errors.append(f"重复 id {p['id']}")
        ids[p['id']] = p
    total = n
    for i, p in enumerate(pages, 1):
        p['fig'] = i

    # 解析 {id} 页码引用
    ref = re.compile(r'\{([a-z0-9_]+)\}')

    def sub(s, p):
        def r(m):
            k = m.group(1)
            if k not in ids:
                errors.append(f"P{p['n']:03d} {p['id']} 引用了不存在的页 {{{k}}}")
                return '??'
            return str(ids[k]['n'])
        return ref.sub(r, s)

    # 预扫描：名词卡、硬核页，供章末与附录自动汇总
    CN = '零一二三四五六七八九十'

    def cn(x):
        if x <= 10:
            return CN[x]
        if x < 20:
            return '十' + (CN[x % 10] if x % 10 else '')
        return CN[x // 10] + '十' + (CN[x % 10] if x % 10 else '')

    terms = []
    for p in pages:
        e = get(p, 'E')
        if e and e.startswith('名词卡'):
            a = [x.strip() for x in e.split('|')]
            terms.append((p, a[1], a[2], a[3]))
    for pp, t, py, d in terms:
        if len(t) + clen(d) > 25:
            errors.append(f"名词表一行放不下：{t} {d}")
    nhard = sum(1 for p in pages if p['layout'] == 'T7')
    nplay = sum(1 for p in pages if p['layout'] == 'T6L')
    half = (len(terms) + 1) // 2

    def gl(ts):
        return '\n'.join(f"「{t}」「{d}」「第{pp['n']}页」" for pp, t, py, d in ts)

    # 列表页覆盖检查（替换前按 id 检查）
    def rawtext(*idl):
        return '\n'.join(v for i in idl for k, v in ids[i]['fields'])

    def cover(need, where, what):
        txt = rawtext(*where)
        for q in need:
            if '{' + q['id'] + '}' not in txt:
                errors.append(f"{what} 缺少 {q['id']}（P{q['n']:03d}）")

    if 'sources1' in ids:
        cover([p for p in pages if get(p, 'SRC')], ['sources1', 'sources2'], '资料来源附录')
        cover([p for p in pages if p['layout'] == 'T6L'], ['sources1', 'sources2'], '资料来源附录(剧场出处)')
        cover([p for p in pages if p['layout'] == 'T7'], ['links'], '课本连接附录')
        cover([p for p in pages if p['layout'] == 'T7'], ['answers2'], '答案附录')
        cover([p for p in pages if p['layout'] == 'T6L'], ['idioms'], '成语附录(剧场)')
        cover([p for p in pages if (get(p, 'E') or '').startswith('成语')], ['idioms'], '成语附录')

    def sub2(s, p):
        if '{' not in s:
            return s
        mine = [t for t in terms if t[0]['ch'] == p['ch']]
        s = s.replace('{NTERMS_ALL}', cn(len(terms))).replace('{NHARD}', cn(nhard)).replace('{NPLAY}', cn(nplay))
        s = s.replace('{NTERMS}', cn(len(mine)))
        s = s.replace('{TERMLIST}', ''.join(f"「{t} · 第{pp['n']}页」" for pp, t, py, d in mine))
        s = s.replace('{GLOSS1}', gl(terms[:half])).replace('{GLOSS2}', gl(terms[half:]))
        return s

    for p in pages:
        p['fields'] = [[k, sub2(sub(v, p), p)] for k, v in p['fields']]
    print('名词卡', len(terms), '硬核页', nhard, '剧场', nplay)

    def label(p):
        if p['n'] == 0:
            return f"图{p['fig']:03d}　{p['type']}　竖版单页"
        lay = p['layout']
        note = ''
        if lay in ('T5L', 'T6L'):
            note = f"　与P{p['n'] + 1:03d}拼成跨页"
        if lay in ('T5R', 'T6R'):
            note = f"　与P{p['n'] - 1:03d}拼成跨页"
        layname = {'T5L': 'T5（跨页左半）', 'T5R': 'T5（跨页右半）', 'T6L': 'T6（漫画左页）',
                   'T6R': 'T6（漫画右页）', 'X': '特殊'}.get(lay, lay)
        return f"图{p['fig']:03d}　P{p['n']:03d}　{p['type']}　版式{layname}{note}"

    rendered = {p['id']: render(p) for p in pages}

    # 分份：第1份＝封面、封底、P001；其后每份4页（偶数页起，跨页不拆）
    groups = [[p for p in pages if p['n'] <= 1]]
    rest = [p for p in pages if p['n'] > 1]
    for i in range(0, len(rest), 4):
        groups.append(rest[i:i + 4])
    out = os.path.join(ROOT, 'out')
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(out)
    for gi, g in enumerate(groups, 1):
        if gi == 1:
            name = '封面封底扉页'
        else:
            name = f"P{g[0]['n']:03d}-P{g[-1]['n']:03d}"
        T = [HEADER, '', EQ, '【本份含】']
        T += ['　　' + label(p) for p in g]
        T += [EQ, '']
        for p in g:
            T += [BAR, label(p), BAR, 'Prompt：']
            T += [x for x in rendered[p['id']] if x.strip()]
            T += ['']
        T += [EQ, '本份完', EQ, '']
        open(os.path.join(out, f"莫名其妙的AI_v9_{gi:02d}_{name}.txt"), 'w', encoding='utf8').write('\n'.join(T))

    # 页面清单
    O = ['《莫名其妙的AI》v9　全书页面清单（由生成器自动汇总）', f'内文 {total} 页＋封面＋封底＝{len(pages)} 张图', '']
    sec = None
    for p in pages:
        if p['n'] == 0:
            O.append(f"图{p['fig']:03d}　{p['type']}")
            continue
        if p['sec'] != sec:
            sec = p['sec']
            O += ['', f'—— {sec} ——']
        extra = []
        if 'term' in p: extra.append('名词卡：' + p['term'][0])
        if 'link' in p: extra.append('课本连接：' + p['link'][0])
        if 'idiom' in p: extra.append('成语：' + p['idiom'][0])
        lay = p['layout'].replace('T5L', 'T5左').replace('T5R', 'T5右').replace('T6L', 'T6左').replace('T6R', 'T6右').replace('X', '特殊')
        O.append(f"P{p['n']:03d}　图{p['fig']:03d}　{lay:<4}　{p['type']}　{title_of(p)}" + ('　［' + '；'.join(extra) + '］' if extra else ''))
    open(os.path.join(ROOT, 'pagelist.txt'), 'w', encoding='utf8').write('\n'.join(O) + '\n')

    # 汇总表（供附录核对）
    S = ['【名词卡】'] + [f"P{p['n']:03d}　{p['term'][0]}　{p['term'][1]}　{p['term'][2]}　{p['term'][3]}" for p in pages if 'term' in p]
    S += ['', '【课本连接】'] + [f"P{p['n']:03d}　{p['link'][0]}　{p['link'][1]}" for p in pages if 'link' in p]
    S += ['', '【成语里的AI】'] + [f"P{p['n']:03d}　{p['idiom'][0]}　{p['idiom'][1]}" for p in pages if 'idiom' in p]
    S += ['', '【资料来源页脚】'] + [f"P{p['n']:03d}　{get(p, 'SRC')}" for p in pages if get(p, 'SRC')]
    S += ['', '【id → 页码】'] + [f"{p['id']} = P{p['n']:03d}" for p in pages]
    open(os.path.join(ROOT, 'summary.txt'), 'w', encoding='utf8').write('\n'.join(S) + '\n')

    # 版式统计
    from collections import Counter
    cnt = Counter(p['type'] for p in pages)
    print('总页数', total, '图数', len(pages), '份数', len(groups))
    print(dict(cnt))
    if total % 16:
        warns.append(f'内文页数 {total} 不是16的倍数')
    # 跨页配对检查
    for i, p in enumerate(pages):
        if p['layout'] in ('T5L', 'T6L'):
            nx = pages[i + 1] if i + 1 < len(pages) else None
            if not nx or nx['layout'] != p['layout'][:2] + 'R':
                errors.append(f"P{p['n']:03d} {p['id']} 跨页左半后面不是右半")
    for w in warns:
        print('WARN', w)
    for e in errors:
        print('ERR ', e)
    print('errors', len(errors))


if __name__ == '__main__':
    main()
