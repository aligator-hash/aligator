#!/usr/bin/env python3
"""Собирает газетную полосу из issue.json.

    python3 build.py issue.json gazeta.html

Рядом с gazeta.html появится archive/<slug>.html — копия выпуска для архива.
Отдельно можно обернуть готовую полосу в архивную страницу:

    python3 build.py --wrap old.html archive/<slug>.html [lang]

В текстах [[...]] превращается в цифру с табличным начертанием (<span class="figs">).
"""
import html, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, '..', 'assets', 'base.html')
SCENES = {'river', 'orbit', 'bars', 'pipes', 'level', 'ticker', 'grid', 'sea',
          'calls', 'range', 'waves', 'flow', 'vote', 'pulse', 'rocket'}

UI = {
    'ru': {'masthead': 'Главные новости', 'edition': 'Утренний выпуск', 'live': 'Живая иллюстрация',
           'last': 'На последней полосе', 'joke': 'Анекдот дня', 'sources': 'Источники',
           'archive': 'Архив выпусков', 'back': '← К свежему выпуску', 'more': 'Показаны последние {n} выпусков',
           'months': ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа',
                      'сентября', 'октября', 'ноября', 'декабря']},
    'en': {'masthead': 'Top Stories', 'edition': 'Morning edition', 'live': 'Living illustration',
           'last': 'On the back page', 'joke': 'Joke of the day', 'sources': 'Sources',
           'archive': 'Past issues', 'back': '← Latest issue', 'more': 'Showing the last {n} issues',
           'months': ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
                      'September', 'October', 'November', 'December']},
}
ARCHIVE_SHOWN = 60
SLUG = re.compile(r'(\d{4})-(\d{2})-(\d{2})(?:-(\d{2})(\d{2}))?$')


def ui_for(d):
    lang = (d.get('lang') or 'ru').lower()
    u = dict(UI.get(lang, UI['en']))
    u.update(d.get('ui', {}))
    return lang, u


def t(s):
    s = html.escape(str(s), quote=False)
    return re.sub(r'\[\[(.+?)\]\]', r'<span class="figs">\1</span>', s)


def slug_label(slug, u):
    m = SLUG.match(slug)
    if not m:
        return slug
    y, mo, dd, hh, mi = m.groups()
    lab = f'{int(dd)} {u["months"][int(mo) - 1]} {y}'
    return lab + (f' · {hh}:{mi}' if hh else '')


def fig(art, u):
    if not art:
        return ''
    sc = art.get('scene')
    if sc not in SCENES:
        raise SystemExit(f'Неизвестная сцена: {sc}. Доступны: {", ".join(sorted(SCENES))}')
    cap = html.escape(art.get('caption', ''), quote=True)
    prm = html.escape(json.dumps(art.get('params', {}), ensure_ascii=False), quote=True)
    return (f'<figure><div class="art" data-art="{sc}" data-params="{prm}" role="img" aria-label="{cap}"></div>'
            f'<figcaption>{t(u["live"])} · {cap}</figcaption></figure>\n')


def article(it, u, head='h3', label=True):
    out = ['<article>']
    if label and it.get('label'):
        out.append(f'<span class="label">{t(it["label"])}</span>')
    out.append(fig(it.get('art'), u))
    out.append(f'<{head}>{t(it["title"])}</{head}>')
    out += [f'<p>{t(p)}</p>' for p in it.get('paras', [])]
    if it.get('src'):
        out.append(f'<div class="src">{t(it["src"])}</div>')
    out.append('</article>')
    return '\n'.join(out)


def archive_html(paths, own, u):
    slugs = []
    for pth in paths:
        name = os.path.basename(pth)
        if name.endswith('.html') and SLUG.match(name[:-5]) and name[:-5] != own:
            slugs.append(name[:-5])
    slugs = sorted(set(slugs), reverse=True)
    if not slugs:
        return ''
    o = ['<nav class="archive" aria-label="' + html.escape(u['archive'], quote=True) + '">',
         f'<span class="label">{t(u["archive"])}</span><ul>']
    o += [f'<li><a href="archive/{s}.html">{t(slug_label(s, u))}</a></li>' for s in slugs[:ARCHIVE_SHOWN]]
    o.append('</ul>')
    if len(slugs) > ARCHIVE_SHOWN:
        o.append(f'<span class="more">{t(u["more"].format(n=ARCHIVE_SHOWN))}</span>')
    o.append('</nav>')
    return '\n'.join(o)


def body(d, u, slug):
    o = ['<div class="page">', '<header class="masthead">',
         f'<div class="top"><span>{t(d["date_line"])}</span><span>{t(d.get("edition", u["edition"]))}</span><span>{t(d.get("city", ""))}</span></div>',
         f'<h1>{t(d.get("masthead", u["masthead"]))}</h1>',
         f'<div class="window">{t(d["window"])}</div>', '</header>',
         f'<section class="brief"><p>{t(d["brief"])}</p></section>',
         '<section class="lead">', article(d['lead'], u, 'h2'), '<aside>']
    o += [article(a, u) for a in d.get('aside', [])]
    o += ['</aside>', '</section>', '<section class="sections">']
    for c in d.get('columns', []):
        if not c.get('items'):
            continue
        o += ['<div class="col">', f'<span class="label">{t(c["label"])}</span>']
        o += [article(it, u, label=False) for it in c['items']]
        o.append('</div>')
    o.append('</section>')
    j = d.get('joke')
    if j:
        o.append(f'<aside class="joke" aria-label="{html.escape(u["joke"], quote=True)}"><span class="label">{t(u["last"])}</span><h2>{t(u["joke"])}</h2>')
        o += [f'<p>{t(line)}</p>' for line in j['lines']]
        o.append(f'<span class="note">{t(j.get("note", ""))}</span></aside>')
    o.append('<!--ARCHIVE-->')
    o.append(f'<footer><span class="label">{t(u["sources"])}</span><ol>')
    o += [f'<li><a href="{html.escape(s["url"], quote=True)}">{t(s["title"])}</a></li>' for s in d.get('sources', [])]
    o += ['</ol></footer>', '</div>']
    return '\n'.join(o)


def lang_script(lang):
    return f'<script>document.documentElement.lang={json.dumps(lang)};</script>\n'


def standalone(page, lang, u):
    """Архивная страница: свой doctype и база, ссылка на свежий выпуск, без блока архива."""
    page = re.sub(r'<nav class="archive".*?</nav>', '', page, flags=re.S).replace('<!--ARCHIVE-->', '')
    back = f'<div class="backbar"><a href="../index.html">{t(u["back"])}</a></div>'
    page = page.replace('<div class="page">', '<div class="page">\n' + back, 1)
    head = ('<!doctype html>\n<html lang="' + html.escape(lang, quote=True) + '"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
            '<style>body{margin:0;font-size:14px}img{max-width:100%}[hidden]{display:none!important}'
            '.backbar{font-family:"PT Sans Narrow","Arial Narrow",Arial,sans-serif;font-size:14px;letter-spacing:.04em;text-transform:uppercase;padding-bottom:10px}'
            '.backbar a{color:var(--accent,#1f3d6b)}</style>\n')
    return head + page + '\n</html>\n'


def main():
    a = sys.argv[1:]
    if a and a[0] == '--wrap':
        if len(a) < 3:
            raise SystemExit(__doc__)
        lang = a[3] if len(a) > 3 else 'ru'
        u = UI.get(lang, UI['en'])
        os.makedirs(os.path.dirname(a[2]) or '.', exist_ok=True)
        open(a[2], 'w', encoding='utf-8').write(standalone(open(a[1], encoding='utf-8').read(), lang, u))
        print(f'OK: {a[2]}')
        return
    if len(a) != 2:
        raise SystemExit(__doc__)
    d = json.load(open(a[0], encoding='utf-8'))
    lang, u = ui_for(d)
    slug = d.get('slug') or str(d.get('seed', 'issue'))
    base = open(BASE, encoding='utf-8').read()
    page = base.replace('{{BODY}}', lang_script(lang) + body(d, u, slug)).replace('{{SEED}}', str(int(d.get('seed', 1))))
    page = page.replace('<title>Главные новости</title>', f'<title>{t(d.get("title", u["masthead"]))}</title>', 1)
    main_page = page.replace('<!--ARCHIVE-->', archive_html(d.get('archive', []), slug, u))
    open(a[1], 'w', encoding='utf-8').write(main_page)
    arch_dir = os.path.join(os.path.dirname(os.path.abspath(a[1])), 'archive')
    os.makedirs(arch_dir, exist_ok=True)
    arch = os.path.join(arch_dir, slug + '.html')
    open(arch, 'w', encoding='utf-8').write(standalone(page, lang, u))
    n = main_page.count('class="art"')
    print(f'OK: {a[1]} · иллюстраций: {n} · {len(main_page) // 1024} КБ')
    print(f'OK: archive/{slug}.html — опубликуй его вместе со страницей через files')


if __name__ == '__main__':
    main()
