"""Generate committed static pages; no runtime dependencies or network calls."""
import argparse
import html
import json
import posixpath
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://alexlee2046.github.io/plainpage/"
STORE = "https://apps.apple.com/app/id6815329484"
ISSUES = "https://github.com/alexlee2046/plainpage/issues"
LANGUAGES = {"zh-Hans": "简体中文", "zh-Hant": "繁體中文", "en": "English", "ja": "日本語", "ko": "한국어", "fr": "Français", "es": "Español", "pt-BR": "Português (Brasil)", "it": "Italiano", "ru": "Русский"}
PAGES = ("index.html", "support.html", "privacy.html")


def e(value):
    return html.escape(value, quote=True)


def route(lang, page):
    directory = "" if lang == "zh-Hans" else lang + "/"
    return directory + ("" if page == "index.html" else page)


def output_path(lang, page):
    return ("" if lang == "zh-Hans" else lang + "/") + page


def relative(current, target):
    result = posixpath.relpath(target or ".", posixpath.dirname(current) or ".")
    if target == "" or target.endswith("/"):
        return result.rstrip("/") + "/"
    return result


def paragraphs(texts):
    return "\n".join(f"<p>{e(text)}</p>" for text in texts)


def questions(pairs):
    return "\n".join(f"<h3>{e(question)}</h3><p>{e(answer)}</p>" for question, answer in pairs)


def faq_schema(lang, url, pairs):
    return {"@type": "FAQPage", "@id": url + "#faq", "inLanguage": lang,
            "mainEntity": [{"@type": "Question", "name": q,
                            "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in pairs]}


def render(lang, page, data):
    current = output_path(lang, page)
    url = BASE + route(lang, page)
    key = {"index.html": "home", "support.html": "support", "privacy.html": "privacy"}[page]
    title, description = data[key + "Title"], data[key + "Description"]
    nav = "".join(f'<a href="{e(relative(current, route(lang, p)))}"' +
                  (' aria-current="page"' if p == page else '') + f'>{e(label)}</a>'
                  for p, label in zip(PAGES, data["nav"]))
    language_links = "".join(f'<a href="{e(relative(current, route(other, page)))}" lang="{other}" hreflang="{other}"' +
                             (' aria-current="page"' if other == lang else '') + f'>{label}</a>'
                             for other, label in LANGUAGES.items())
    alternates = "\n".join(f'<link rel="alternate" hreflang="{other}" href="{BASE + route(other, page)}">'
                           for other in LANGUAGES)
    alternates += f'\n<link rel="alternate" hreflang="x-default" href="{BASE + route("en", page)}">'
    support = relative(current, route(lang, "support.html"))
    privacy = relative(current, route(lang, "privacy.html"))
    schemas = [{"@type": "WebPage", "@id": url + "#page", "url": url,
                "name": title, "description": description, "inLanguage": lang}]
    if page == "index.html":
        schemas.append({"@type": "SoftwareApplication", "@id": url + "#app", "name": data["name"],
                        "alternateName": "Plainpage", "url": url, "downloadUrl": STORE,
                        "applicationCategory": "UtilitiesApplication", "operatingSystem": "iOS 17 or later",
                        "inLanguage": lang, "description": description,
                        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD", "url": STORE}})
        schemas.append(faq_schema(lang, url, data["faq"]))
        content = f'''<h1>{e(data['name'])}</h1>
<p class="muted">{e(data['tagline'])}</p>
<p>{e(description)}</p>
<p><a href="{STORE}">{e(data['download'])}</a> · <a href="{e(support)}">{e(data['setupLink'])}</a></p>
<section aria-labelledby="methods"><h2 id="methods">{e(data['methodTitle'])}</h2>
<ul>{''.join('<li>' + e(text) + '</li>' for text in data['methods'])}</ul>
<p>{e(data['limits'])}</p></section>
<section aria-labelledby="faq"><h2 id="faq">{e(data['faqTitle'])}</h2>
{questions(data['faq'])}</section>
<p><a href="{e(support)}">{e(data['nav'][1])}</a> · <a href="{e(privacy)}">{e(data['nav'][2])}</a></p>'''
    elif page == "support.html":
        schemas.append(faq_schema(lang, url, data["troubleshooting"]))
        content = f'''<h1>{e(title)}</h1>
<h2>{e(data['setupTitle'])}</h2>
<ol>{''.join('<li>' + e(text) + '</li>' for text in data['steps'])}</ol>
<section aria-labelledby="faq"><h2 id="faq">{e(data['supportFaqTitle'])}</h2>
{questions(data['troubleshooting'])}</section>
<h2>{e(data['feedbackTitle'])}</h2>
<p><a href="{ISSUES}">{e(data['feedbackLink'])}</a></p>
<p>{e(data['feedbackWarning'])}</p>\n<p>{e(data['feedbackNotice'])}</p>'''
    else:
        sections = "\n".join(f'<section><h2>{e(heading)}</h2>\n{paragraphs(texts)}</section>'
                             for heading, texts in data["privacySections"])
        content = f'''<h1>{e(title)}</h1>
<p class="muted">{e(data['effectiveDate'])}</p>
<p>{e(data['privacyScope'])}</p>
{sections}
<p><a href="{e(support)}">{e(data['nav'][1])}</a></p>'''
    graph = json.dumps({"@context": "https://schema.org", "@graph": schemas}, ensure_ascii=False, indent=2)
    graph = graph.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return f'''<!doctype html>
<!-- Generated by tools/build_site.py from content/locales.json. -->
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<link rel="canonical" href="{url}">
{alternates}
<meta property="og:type" content="website">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{url}">
<meta property="og:site_name" content="{e(data['name'])}">
<link rel="stylesheet" href="{e(relative(current, 'style.css'))}">
<script type="application/ld+json">
{graph}
</script>
</head>
<body><main>
<nav aria-label="{e(data['nav'][0])}">{nav}</nav>
<nav class="languages" aria-label="{e(data['languageLabel'])}">{language_links}</nav>
{content}
</main></body>
</html>
'''


def generate():
    locales = json.loads((ROOT / "content/locales.json").read_text(encoding="utf-8"))
    if set(locales) != set(LANGUAGES):
        raise ValueError("Expected exactly ten languages")
    files = {output_path(lang, page): render(lang, page, locales[lang])
             for lang in LANGUAGES for page in PAGES}
    urls = [BASE + route(lang, page) for lang in LANGUAGES for page in PAGES]
    files["sitemap.xml"] = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(
        f"  <url><loc>{escape(url)}</loc></url>\n" for url in urls) + "</urlset>\n"
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Read-only check of committed generated output")
    args = parser.parse_args()
    stale = []
    for filename, content in generate().items():
        path = ROOT / filename
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                stale.append(filename)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    if stale:
        raise SystemExit("Stale generated files: " + ", ".join(stale))
    print("Checked" if args.check else "Generated", f"{len(LANGUAGES) * len(PAGES)} pages and sitemap.xml")


if __name__ == "__main__":
    main()
