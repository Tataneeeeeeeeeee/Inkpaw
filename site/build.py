#!/usr/bin/env python3
# =============================================================================
#  site/build.py — builds the Inkpaw website (English + French) from content/
# =============================================================================
#  Usage: python3 site/build.py        (no dependency, Python 3.8+)
#
#  Reads  content/en.json and content/fr.json (all the texts, same shape)
#  Writes en/{index,install,screenshots,docs}.html
#         fr/{index,install,screenshots,docs}.html
#         index.html  → sends the visitor to /fr/ or /en/ (browser language)
#  Shared files (hand-written, not generated): assets/css/site.css,
#  assets/js/site.js, assets/img/*.
#
#  The pages are plain static HTML: they work from any web server, from
#  GitHub Pages (publish the site/ folder) or opened as files. Texts in the
#  JSON may contain trusted inline HTML (<code>, <kbd>, <a>); code blocks are
#  escaped. Edit the JSON, run this script, commit the result.
# =============================================================================
import html
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LANGS = ("en", "fr")
PAGES = ("index", "install", "screenshots", "docs")
REPO = "https://github.com/Tataneeeeeeeeeee/Inkpaw"
INSTALL_CMD = "curl -fsSL https://raw.githubusercontent.com/Tataneeeeeeeeeee/Inkpaw/main/install.sh | bash"
SHOT_CATS = {"desktop": "desktop", "night-theme": "desktop", "lock-screen": "desktop",
             "spotlight": "apps", "quick-panel": "apps", "ai-assistant": "apps", "settings": "apps",
             "wallpapers": "menus", "themes": "menus", "keybindings": "menus", "power-menu": "menus"}
SHOT_ORDER = ["desktop", "night-theme", "spotlight", "quick-panel", "ai-assistant", "settings",
              "wallpapers", "themes", "keybindings", "power-menu", "lock-screen"]

esc = html.escape
IMG = "../assets/img"


# --- shared pieces ---------------------------------------------------------------
ICON_SUN = ('<svg class="sun" aria-hidden="true" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4.5"/>'
            '<path d="M12 2v2.5M12 19.5V22M4.2 4.2 6 6M18 18l1.8 1.8M2 12h2.5M19.5 12H22M4.2 19.8 6 18M18 6l1.8-1.8"/></svg>')
ICON_MOON = '<svg class="moon" aria-hidden="true" viewBox="0 0 24 24"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z"/></svg>'
ICON_GH = ('<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.9a3.4 3.4 0 0 0-.9-2.6c3.1-.4 '
           '6.4-1.5 6.4-6.9A5.4 5.4 0 0 0 20 4.8 5 5 0 0 0 19.9 1S18.7.7 16 2.5a13.4 13.4 0 0 0-7 0C6.3.7 5.1 1 5.1 1A5 5 0 0 0 '
           '5 4.8a5.4 5.4 0 0 0-1.5 3.7c0 5.4 3.3 6.5 6.4 6.9a3.4 3.4 0 0 0-.9 2.6V22"/></svg>')
ICON_GLOBE = ('<svg aria-hidden="true" viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/>'
              '<path d="M3 12h18M12 3c2.5 2.6 3.8 5.6 3.8 9s-1.3 6.4-3.8 9c-2.5-2.6-3.8-5.6-3.8-9S9.5 5.6 12 3Z"/></svg>')

# set the theme before the first paint (no flash of the wrong mode)
THEME_BOOT = ('<script>(function(){try{var t=localStorage.getItem("inkpaw-theme");'
              'if(t==="dark"||t==="light")document.documentElement.setAttribute("data-theme",t);}catch(e){}})();</script>')


def head(c, page):
    title, desc = c["meta"]["home" if page == "index" else page]
    other = c["other"]
    alt = "".join(f'<link rel="alternate" hreflang="{l}" href="../{l}/{page}.html">' for l in LANGS)
    return f"""<!doctype html>
<html lang="{c['lang']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="color-scheme" content="light dark">
<meta name="theme-color" content="#f1e7cf" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#1f1a16" media="(prefers-color-scheme: dark)">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:image" content="{IMG}/desktop.webp">
<meta property="og:locale" content="{c['locale']}">
{alt}
<link rel="alternate" hreflang="x-default" href="../en/{page}.html">
<link rel="icon" type="image/png" href="{IMG}/inkpaw-mark-32.png">
{THEME_BOOT}
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Caveat+Brush&family=Shantell+Sans:wght@400;500;600;700;800&family=Courier+Prime:wght@400;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../assets/css/site.css">
<script src="../assets/js/site.js" defer></script>
</head>
<body>
<a class="skip" href="#main">{esc(c['nav']['skip'])}</a>
"""


def header(c, page):
    n = c["nav"]
    def link(href, label, here):
        cur = ' aria-current="page"' if here else ""
        return f'<a href="{href}"{cur}>{esc(label)}</a>'
    return f"""<header class="site-header">
  <nav class="wrap site-nav" aria-label="Main">
    <a class="brand" href="index.html"><img src="{IMG}/inkpaw-mark-128.png" alt="" width="40" height="40"><span>Inkpaw</span></a>
    <div class="nav-links">
      {link('index.html#features', n['features'], False)}
      {link('screenshots.html', n['screenshots'], page == 'screenshots')}
      {link('install.html', n['install'], page == 'install')}
      {link('docs.html', n['docs'], page == 'docs')}
    </div>
    <div class="nav-tools">
      <a class="icon-btn" href="../{c['other']}/{page}.html" hreflang="{c['other']}" lang="{c['other']}" aria-label="{esc(n['language'])}">{ICON_GLOBE}{c['other_short']}</a>
      <button class="icon-btn theme-toggle" type="button" data-theme-toggle aria-label="{esc(n['theme'])}">{ICON_SUN}{ICON_MOON}</button>
      <a class="icon-btn" href="{REPO}">{ICON_GH}<span>{esc(n['github'])}</span></a>
    </div>
  </nav>
</header>
"""


def footer(c):
    n, f = c["nav"], c["footer"]
    return f"""<footer class="site-footer">
  <img class="basket" src="{IMG}/basket.png" alt="" width="150">
  <div class="wrap footer-grid">
    <div class="footer-brand">
      <div class="row"><img src="{IMG}/inkpaw-mark-flat-256.png" alt="" width="64"><span>Inkpaw</span></div>
      <p>{f['about']}</p>
    </div>
    <nav class="footer-links" aria-label="Footer">
      <div><strong>{esc(f['project'])}</strong><a href="install.html">{esc(n['install'])}</a><a href="screenshots.html">{esc(n['screenshots'])}</a><a href="{REPO}">GitHub</a></div>
      <div><strong>{esc(f['docs'])}</strong>{''.join(f'<a href="docs.html#{g["id"]}">{esc(g["title"])}</a>' for g in c['docs']['guides'][1:4])}</div>
    </nav>
  </div>
  <div class="footer-bottom">{esc(f['credits'])}</div>
</footer>
</body>
</html>
"""


def command(c, title_tag="h2", title=None, cat=True):
    n = c["nav"]
    t = f'<{title_tag} class="display">{esc(title)}</{title_tag}>' if title else ""
    kitty = f'<img class="cat" src="{IMG}/peek-gribouille.png" alt="" width="92">' if cat else ""
    return (f'<div class="cmd">{t}<code><span class="prompt">$</span> {esc(INSTALL_CMD)}</code>'
            f'<button class="copy" type="button" data-copy="{esc(INSTALL_CMD)}" data-copied="{esc(n["copied"])}">{esc(n["copy"])}</button>{kitty}</div>')


def shot_meta(c, key):
    title, keys, text, alt = c["shots"]["items"][key]
    return title, keys, text, alt


# --- pages ---------------------------------------------------------------------------------
def page_index(c):
    h = c["home"]
    feats = "".join(f"""<article class="card feature"><header><span class="num tint-{t}">{i + 1:02d}</span>
<h3 class="display">{esc(title)}</h3></header><p>{text}</p></article>""" for i, (t, title, text) in enumerate(h["features"]))
    steps = "".join(f'<li class="card"><span class="n">{i + 1}</span><div><strong>{esc(t)}</strong><span>{x}</span></div></li>'
                    for i, (t, x) in enumerate(h["how_steps"]))
    tiles = ""
    for key in h["gallery"]:
        title, _k, text, alt = shot_meta(c, key)
        tiles += (f'<figure class="card tile"><img src="{IMG}/{key}.webp" alt="{esc(alt)}" loading="lazy" width="1920" height="1080">'
                  f'<figcaption><strong>{esc(title)}</strong><span>{esc(text)}</span></figcaption></figure>')
    pills = "".join(f'<span class="pill {cls}">{esc(p)}</span>' for p, cls in zip(h["duo_pills"], ("tint-ochre", "tint-moss", "tint-brick")))
    return head(c, "index") + header(c, "index") + f"""<main id="main">
  <section class="wrap hero">
    <div class="hero-text">
      <span class="tag">{esc(h['tag'])}</span>
      <h1 class="display">{esc(h['title'])}</h1>
      <p>{esc(h['lead'])}</p>
      <div class="actions">
        <a class="btn btn-ink" href="install.html">{esc(h['cta_install'])}</a>
        <a class="btn btn-paper" href="screenshots.html">{esc(h['cta_shots'])}</a>
      </div>
    </div>
    <div class="hero-logo">
      <img class="only-light" src="{IMG}/inkpaw-signature-600.png" alt="{esc(h['logo_alt'])}" width="600" height="520">
      <img class="only-dark" src="{IMG}/inkpaw-signature-dark-600.png" alt="{esc(h['logo_alt'])}" width="600" height="520">
    </div>
  </section>

  <section class="wrap" aria-label="{esc(h['oneline'])}">
    {command(c, 'h2', h['oneline'])}
    <p class="note">{h['oneline_note']} <a href="install.html"><strong>{h['oneline_more']}</strong></a></p>
  </section>

  <section class="wrap section" style="padding-bottom: 0">
    <figure class="card shot">
      <img class="only-light" src="{IMG}/desktop.webp" alt="{esc(h['hero_alt'])}" width="1920" height="1080">
      <img class="only-dark" src="{IMG}/night-theme.webp" alt="{esc(h['hero_alt_dark'])}" width="1920" height="1080">
      <figcaption>{esc(h['hero_caption'])}</figcaption>
    </figure>
  </section>

  <section id="features" class="wrap section" aria-labelledby="feat-title">
    <div class="section-head"><h2 id="feat-title" class="display">{esc(h['features_title'])}</h2><p>{h['features_lead']}</p></div>
    <div class="grid">{feats}</div>
  </section>

  <section class="band" aria-labelledby="how-title">
    <div class="wrap">
      <div class="text"><h2 id="how-title" class="display">{esc(h['how_title'])}</h2><p>{h['how_p1']}</p><p>{h['how_p2']}</p></div>
      <ol class="steps">{steps}</ol>
    </div>
  </section>

  <section class="wrap section" aria-labelledby="gal-title">
    <div class="section-head"><h2 id="gal-title" class="display">{esc(h['gallery_title'])}</h2><a href="screenshots.html"><strong>{esc(h['gallery_all'])}</strong></a></div>
    <div class="tiles">{tiles}</div>
  </section>

  <section class="wrap" style="padding-bottom: 90px" aria-labelledby="duo-title">
    <div class="card duo">
      <div><h2 id="duo-title" class="display">{esc(h['duo_title'])}</h2><p>{h['duo_text']}</p><div class="pills">{pills}</div></div>
      <div class="pics"><img src="{IMG}/night-theme.webp" alt="{esc(h['hero_alt_dark'])}" loading="lazy" width="1920" height="1080"></div>
    </div>
  </section>
</main>
""" + footer(c)


def page_install(c):
    p = c["install"]
    steps = "".join(f'<li class="card"><span class="n">{i + 1}</span><div><strong>{esc(t)}</strong><span>{x}</span></div></li>'
                    for i, (t, x) in enumerate(p["steps"]))
    rows = "".join(f"<tr><td><code>{esc(k)}</code></td><td>{esc(v)}</td></tr>" for k, v in p["options"])
    needs = "".join(f"<li>{x}</li>" for x in p["needs"])
    manual = (f'<span class="c">{esc(p["manual_c1"])}</span>\ngit clone {REPO}.git ~/Inkpaw\ncd ~/Inkpaw\n'
              f'<span class="c">{esc(p["manual_c2"])}</span>\n./test.sh deps\n./test.sh verify\n'
              'hyprtheme/generate-wallpapers.sh\nsudo ./session/install.sh --sddm-theme')
    return head(c, "install") + header(c, "install") + f"""<main id="main" class="wrap page" style="max-width: 1048px">
  <section class="page-head">
    <h1 class="display">{esc(p['title'])}</h1>
    <p>{p['lead']}</p>
    <img class="cat" src="{IMG}/head-moumoute.png" alt="" width="110">
  </section>

  <section class="block" aria-labelledby="cmd-title">
    <h2 id="cmd-title" class="display">{esc(p['cmd_title'])}</h2>
    {command(c, cat=False)}
    <p class="muted">{p['cmd_note']}</p>
  </section>

  <section class="block" aria-labelledby="steps-title">
    <h2 id="steps-title" class="display">{esc(p['steps_title'])}</h2>
    <ol class="steps steps-grid">{steps}</ol>
  </section>

  <section class="block" aria-labelledby="opt-title">
    <h2 id="opt-title" class="display">{esc(p['opt_title'])}</h2>
    <p class="muted">{p['opt_note']}</p>
    <div class="card table-box"><table><thead><tr><th scope="col">{esc(p['opt_head'][0])}</th><th scope="col">{esc(p['opt_head'][1])}</th></tr></thead><tbody>{rows}</tbody></table></div>
  </section>

  <section class="cols">
    <div class="block"><h2 class="display">{esc(p['manual_title'])}</h2><pre>{manual}</pre></div>
    <div class="block"><h2 class="display">{esc(p['needs_title'])}</h2><ul class="card list">{needs}</ul><p class="muted">{p['needs_note']}</p></div>
  </section>

  <section class="callout" aria-labelledby="un-title">
    <div><h2 id="un-title" class="display">{esc(p['un_title'])}</h2><p>{p['un_text']}</p></div>
    <pre>sudo ~/.local/share/inkpaw/repo/session/uninstall.sh --sddm-theme
rm -rf ~/.local/share/inkpaw ~/.local/state/inkpaw ~/.cache/inkpaw</pre>
  </section>

  <a class="btn btn-ink" href="docs.html" style="align-self: flex-start">{esc(p['next'])}</a>
</main>
""" + footer(c)


def page_screenshots(c):
    s = c["shots"]
    first = SHOT_ORDER[0]
    t0, k0, x0, a0 = shot_meta(c, first)
    filters = "".join(f'<button type="button" data-filter="{fid}" aria-pressed="{"true" if fid == "all" else "false"}">{esc(lab)}</button>'
                      for fid, lab in s["filters"])
    thumbs = ""
    for key in SHOT_ORDER:
        t, k, x, a = shot_meta(c, key)
        cur = ' aria-current="true"' if key == first else ""
        thumbs += (f'<li data-cat="{SHOT_CATS[key]}"><a href="{IMG}/{key}.webp" data-shot data-title="{esc(t)}" data-text="{esc(x)}" '
                   f'data-keys="{esc(k)}" data-alt="{esc(a)}"{cur} aria-label="{esc(s["show"])} — {esc(t)}">'
                   f'<img src="{IMG}/{key}.webp" alt="" loading="lazy" width="1920" height="1080"><span>{esc(t)}</span></a></li>')
    keys0 = f'<kbd data-v-keys>{esc(k0)}</kbd>' if k0 else '<kbd data-v-keys hidden></kbd>'
    return head(c, "screenshots") + header(c, "screenshots") + f"""<main id="main" class="wrap page" style="gap: 34px">
  <section class="section-head" style="margin: 0">
    <div class="page-head"><h1 class="display">{esc(s['title'])}</h1><p>{esc(s['lead'])}</p></div>
    <div class="filters" role="group" aria-label="{esc(s['filters_label'])}">{filters}</div>
  </section>

  <figure class="card viewer" data-viewer>
    <img src="{IMG}/{first}.webp" alt="{esc(a0)}" width="1920" height="1080">
    <figcaption><strong data-v-title>{esc(t0)}</strong><span class="muted" data-v-text>{esc(x0)}</span>{keys0}</figcaption>
  </figure>

  <ul class="thumbs">{thumbs}</ul>

  <section class="callout aside-cat">
    <img src="{IMG}/head-clafoutis.png" alt="" width="96">
    <div><h2 class="display">{esc(s['aside_title'])}</h2><p>{esc(s['aside_text'])}</p></div>
  </section>
</main>
""" + footer(c)


def block(b):
    kind = b[0]
    if kind == "h":
        return f'<h3>{esc(b[1])}</h3>'
    if kind == "p":
        return f'<p>{b[1]}</p>'
    if kind == "code":
        return f'<pre>{esc(b[1])}</pre>'
    if kind == "tip":
        return f'<aside class="tip"><img src="{IMG}/peek-gribouille.png" alt="" width="56"><p>{b[1]}</p></aside>'
    if kind == "table":
        (h1, h2), rows = b[1], b[2]
        body = "".join(f"<tr><td><code>{k}</code></td><td>{v}</td></tr>" for k, v in rows)
        return f'<div class="card table-box"><table><thead><tr><th scope="col">{esc(h1)}</th><th scope="col">{esc(h2)}</th></tr></thead><tbody>{body}</tbody></table></div>'
    raise ValueError(f"unknown block {kind}")


def page_docs(c):
    d = c["docs"]
    nav = "".join(f'<a href="#{g["id"]}"{" class=\"active\"" if i == 0 else ""}><span class="n">{i + 1:02d}</span>{esc(g["title"])}</a>'
                  for i, g in enumerate(d["guides"]))
    guides = "".join(f"""<section class="doc" id="{g['id']}" aria-labelledby="{g['id']}-t">
  <span class="crumb">{esc(d['crumb'])} / {esc(g['title'].upper())}</span>
  <h2 id="{g['id']}-t" class="display">{esc(g['title'])}</h2>
  <p class="lead">{esc(g['lead'])}</p>
  {''.join(block(b) for b in g['blocks'])}
</section>""" for g in d["guides"])
    return head(c, "docs") + header(c, "docs") + f"""<div class="wrap docs" style="max-width: 1240px">
  <nav class="card docs-nav" aria-label="{esc(d['title'])}">
    <img class="paw" src="{IMG}/paw-croquette.png" alt="" width="70">
    <span class="title">{esc(d['nav_title'])}</span>
    {nav}
    <a href="{REPO}/tree/main/docs" style="margin-top: 6px; font-size: 14.5px">{esc(d['edit'])}</a>
  </nav>
  <main id="main" class="docs-main">
    <h1 class="sr-only">{esc(d['title'])}</h1>
    {guides}
  </main>
</div>
""" + footer(c)


ROOT_INDEX = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Inkpaw</title>
<link rel="alternate" hreflang="en" href="en/index.html">
<link rel="alternate" hreflang="fr" href="fr/index.html">
<link rel="icon" type="image/png" href="assets/img/inkpaw-mark-32.png">
<script>
  // French browsers go to /fr/, everyone else to /en/
  (function () {
    var langs = navigator.languages || [navigator.language || "en"];
    var fr = langs.some(function (l) { return /^fr\\b/i.test(l); });
    location.replace((fr ? "fr" : "en") + "/index.html");
  })();
</script>
<noscript><meta http-equiv="refresh" content="0; url=en/index.html"></noscript>
<style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#f1e7cf;color:#2a2420;font-family:sans-serif}</style>
</head>
<body>
<p><a href="en/index.html">English</a> · <a href="fr/index.html">Français</a></p>
</body>
</html>
"""


def main():
    builders = {"index": page_index, "install": page_install, "screenshots": page_screenshots, "docs": page_docs}
    for lang in LANGS:
        with open(os.path.join(HERE, "content", f"{lang}.json"), encoding="utf-8") as f:
            c = json.load(f)
        out = os.path.join(HERE, lang)
        os.makedirs(out, exist_ok=True)
        for page in PAGES:
            with open(os.path.join(out, f"{page}.html"), "w", encoding="utf-8") as f:
                f.write(builders[page](c))
    with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as f:
        f.write(ROOT_INDEX)
    print(f"site built: {', '.join(LANGS)} × {len(PAGES)} pages in {HERE}")


if __name__ == "__main__":
    main()
