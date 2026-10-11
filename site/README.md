# Inkpaw website

The project's website, in the “encre” art direction (parchment, ink outlines,
brush titles, cats), in **English** and **French**, with a **light and a dark
mode**. Plain static HTML + CSS + a little JavaScript: no framework, no build
tool to install.

```
site/
├── index.html            # sends visitors to fr/ or en/ (browser language)
├── en/  fr/              # GENERATED pages: index, install, screenshots, docs
├── content/en.json       # ★ every English text of the site
├── content/fr.json       # ★ the same keys, in French
├── build.py              # builds en/ and fr/ from content/ (Python 3, stdlib only)
└── assets/
    ├── css/site.css      # the whole look; colors are tokens (light / dark)
    ├── js/site.js        # theme toggle, Copy buttons, gallery, docs sidebar
    └── img/              # screenshots, logo and cats (copies from the repo)
```

## Editing

Change a text in `content/en.json` **and** `content/fr.json`, then:

```bash
python3 site/build.py
```

and commit the regenerated `en/` and `fr/` pages with it. Texts may contain
inline HTML (`<code>`, `<kbd>`, `<a>`); code blocks are escaped. Layout lives in
`build.py` (one function per page), style in `assets/css/site.css`.

Images are copies: after retaking the screenshots (`docs/screenshots/`) or
rebuilding the logo (`logo/`), copy the new files to `assets/img/`.

## Light / dark

The site follows the system preference (`prefers-color-scheme`). The ☀/☾ button
forces one mode and remembers it (`localStorage`, key `inkpaw-theme`); a tiny
script in each page's `<head>` applies it before the first paint. Dark mode uses
the “encre nuit” palette, and the home page shows the night screenshot.

## Trying it locally

```bash
cd site && python3 -m http.server 8000      # then open http://localhost:8000
```

(Opening the files directly works too, except the language redirect of the root
`index.html` in some browsers: open `en/index.html` or `fr/index.html`.)

## Publishing on GitHub Pages

Settings → Pages → *Build and deployment* → **GitHub Actions**, then add a
workflow that uploads the `site/` folder (`actions/upload-pages-artifact` with
`path: site`, then `actions/deploy-pages`). The site will be at
`https://<user>.github.io/Inkpaw/`. All links are relative, so it works in a
sub-folder and on any static host as well.
