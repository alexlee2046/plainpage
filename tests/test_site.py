"""Static ten-language checks: python3 -m unittest discover -s tests -v.

These check coverage and source/output consistency, not native-speaker accuracy.
"""
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path
import sys
import unittest
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_site as site

LOCALES = json.loads((ROOT / "content/locales.json").read_text(encoding="utf-8"))


class Page(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.text = []
        self.json_ld = []
        self.in_json = False
        self.feed(source)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags.append((tag, attrs))
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self.in_json = True

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_json = False

    def handle_data(self, data):
        (self.json_ld if self.in_json else self.text).append(data)

    def attrs(self, tag):
        return [attrs for t, attrs in self.tags if t == tag]

    @property
    def visible(self):
        return "".join("".join(self.text).split())


def load_page(lang, page):
    return Page((ROOT / site.output_path(lang, page)).read_text(encoding="utf-8"))


class SiteTests(unittest.TestCase):
    def test_generated_output_is_current(self):
        files = site.generate()
        self.assertEqual(len(files), 31)
        for filename, content in files.items():
            with self.subTest(file=filename):
                self.assertEqual((ROOT / filename).read_text(encoding="utf-8"), content)

    def test_all_page_metadata(self):
        for lang in site.LANGUAGES:
            for filename in site.PAGES:
                with self.subTest(lang=lang, page=filename):
                    page = load_page(lang, filename)
                    url = site.BASE + site.route(lang, filename)
                    self.assertEqual(page.attrs("html"), [{"lang": lang}])
                    self.assertEqual([a["href"] for a in page.attrs("link") if a.get("rel") == "canonical"], [url])
                    descriptions = [a.get("content") for a in page.attrs("meta") if a.get("name") == "description"]
                    self.assertEqual(len(descriptions), 1)
                    self.assertTrue(descriptions[0])
                    self.assertEqual([a.get("content") for a in page.attrs("meta") if a.get("property") == "og:url"], [url])
                    self.assertFalse(any(a.get("name") == "robots" and "noindex" in a.get("content", "") for a in page.attrs("meta")))

    def test_reciprocal_hreflang_and_same_page_switches(self):
        for lang in site.LANGUAGES:
            for filename in site.PAGES:
                with self.subTest(lang=lang, page=filename):
                    page = load_page(lang, filename)
                    alternates = [a for a in page.attrs("link") if a.get("rel") == "alternate"]
                    expected = {other: site.BASE + site.route(other, filename) for other in site.LANGUAGES}
                    expected["x-default"] = site.BASE + site.route("en", filename)
                    self.assertEqual(len(alternates), 11)
                    self.assertEqual({a["hreflang"]: a["href"] for a in alternates}, expected)
                    switches = [a for a in page.attrs("a") if "hreflang" in a]
                    self.assertEqual(len(switches), 10)
                    current_url = site.BASE + site.route(lang, filename)
                    for a in switches:
                        self.assertEqual(a["lang"], a["hreflang"])
                        self.assertEqual(urljoin(current_url, a["href"]), expected[a["hreflang"]])
                        self.assertEqual(a.get("aria-current") == "page", a["lang"] == lang)

    def test_all_local_links_and_styles_exist(self):
        for lang in site.LANGUAGES:
            for filename in site.PAGES:
                current_url = site.BASE + site.route(lang, filename)
                page = load_page(lang, filename)
                for tag, attrs in page.tags:
                    if tag not in ("a", "link") or "href" not in attrs:
                        continue
                    url = urljoin(current_url, attrs["href"])
                    if url.startswith(site.BASE):
                        path = urlparse(url).path.removeprefix("/plainpage/")
                        path += "index.html" if not path or path.endswith("/") else ""
                        self.assertTrue((ROOT / path).is_file(), (lang, filename, attrs["href"]))

    def test_schema_matches_visible_content_in_all_languages(self):
        for lang in site.LANGUAGES:
            for filename in site.PAGES:
                with self.subTest(lang=lang, page=filename):
                    page = load_page(lang, filename)
                    graph = json.loads("".join(page.json_ld))
                    self.assertEqual(graph["@context"], "https://schema.org")
                    schemas = {node["@type"]: node for node in graph["@graph"]}
                    for node in schemas.values():
                        self.assertEqual(node["inLanguage"], lang)
                        self.assertTrue(node["@id"].startswith(site.BASE + site.route(lang, filename) + "#"))
                        self.assertNotIn("aggregateRating", node)
                        self.assertNotIn("review", node)
                    if filename == "privacy.html":
                        self.assertNotIn("FAQPage", schemas)
                        continue
                    faq = schemas["FAQPage"]
                    expected = LOCALES[lang]["faq" if filename == "index.html" else "troubleshooting"]
                    self.assertEqual(len(faq["mainEntity"]), len(expected))
                    self.assertEqual(len(page.attrs("h3")), len(expected))
                    for q, pair in zip(faq["mainEntity"], expected):
                        self.assertEqual([q["name"], q["acceptedAnswer"]["text"]], pair)
                        self.assertIn("".join(q["name"].split()), page.visible)
                        self.assertIn("".join(q["acceptedAnswer"]["text"].split()), page.visible)
                    if filename == "index.html":
                        app = schemas["SoftwareApplication"]
                        self.assertEqual(app["downloadUrl"], site.STORE)
                        self.assertEqual(app["offers"]["price"], "0")
                        self.assertEqual(app["operatingSystem"], "iOS 17 or later")

    def test_sitemap_and_legacy_urls(self):
        tree = ET.parse(ROOT / "sitemap.xml")
        urls = [n.text for n in tree.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url/{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
        expected = [site.BASE + site.route(lang, page) for lang in site.LANGUAGES for page in site.PAGES]
        self.assertEqual(len(urls), 30)
        self.assertCountEqual(urls, expected)
        for filename in site.PAGES:
            self.assertTrue((ROOT / filename).is_file())
            self.assertEqual(load_page("zh-Hans", filename).attrs("html"), [{"lang": "zh-Hans"}])

    def test_original_chinese_and_english_policy_body_is_preserved(self):
        # SHA-256 of whitespace-normalized six paragraphs in git baseline
        # 29a87949461a80ab6096565c39c2a95bb8f6777c:privacy.html.
        expected = {
            "zh-Hans": "a5e36c6acbd9c1299879a12fe5c5735ee9e77aa0405ad8595b4d559d52fbaf70",
            "en": "11001c776c4f3fc576e49bcbc716a6069692b2a4de0ab995e6675068b95ea906",
        }
        for lang, digest in expected.items():
            paragraphs = [text for _, texts in LOCALES[lang]["privacySections"] for text in texts]
            normalized = "".join("".join(text.split()) for text in paragraphs)
            self.assertEqual(hashlib.sha256(normalized.encode()).hexdigest(), digest, lang)

    def test_privacy_and_feedback_translation_coverage(self):
        # Original policy order: no collection, local detection, permissions,
        # no network requests, children, changes/contact. Exact text is self-reviewed
        # in locales.json; this does not certify semantic/native-language accuracy.
        anchors = {
            "zh-Hans": ["不收集、不存储、不上传、不出售", "没有账号系统", "不含任何统计、广告或追踪 SDK", "只存在于你的设备上", "不会读取或传输表单内容、密码、Cookie 或浏览记录", "不发起网络请求", "通过 App Store 下发", "包括儿童", "修改生效日期", "2026-09-24"],
            "zh-Hant": ["不收集、不儲存、不上傳、不出售", "沒有帳號系統", "不含任何統計、廣告或追蹤 SDK", "只存在於你的裝置上", "不會讀取或傳輸表單內容、密碼、Cookie 或瀏覽紀錄", "不發起網路請求", "透過 App Store 提供", "包括兒童", "修改生效日期", "2026-09-24"],
            "en": ["does not collect, store, upload, or sell", "no accounts", "no analytics, advertising, or tracking SDKs", "stay on your device", "does not read or transmit form contents, passwords, cookies, or browsing history", "makes no network requests", "through the App Store", "including children", "effective date will be updated", "2026-09-24"],
            "ja": ["収集、保存、アップロード、販売しません", "アカウントシステムはなく", "トラッキングの SDK", "端末上にのみ存在", "読み取ったり送信したりしません", "ネットワークリクエストを行いません", "App Store を通じて配信", "子どもを含め", "発効日を更新", "2026-09-24"],
            "ko": ["수집, 저장, 업로드 또는 판매하지 않습니다", "계정 시스템이 없으며", "추적 SDK를 포함하지 않습니다", "기기에만 존재", "읽거나 전송하지 않습니다", "네트워크 요청을 하지 않습니다", "App Store를 통해 배포", "아동을 포함", "시행일을 업데이트", "2026-09-24"],
            "fr": ["ne collecte, ne stocke, n’envoie ni ne vend", "pas de système de comptes", "SDK d’analyse, de publicité ou de suivi", "uniquement sur votre appareil", "ne lit ni ne transmet", "aucune requête réseau", "via l’App Store", "enfants", "date d’entrée en vigueur", "2026-09-24"],
            "es": ["no recopila, almacena, sube ni vende", "No hay un sistema de cuentas", "SDK de análisis, publicidad o seguimiento", "únicamente en tu dispositivo", "no lee ni transmite", "no realiza solicitudes de red", "a través del App Store", "menores", "fecha de entrada en vigor", "2026-09-24"],
            "pt-BR": ["não coleta, armazena, envia nem vende", "Não há sistema de contas", "SDKs de análise, publicidade ou rastreamento", "apenas no seu dispositivo", "não lê nem transmite", "não faz solicitações de rede", "pela App Store", "crianças", "data de vigência", "2026-09-24"],
            "it": ["non raccoglie, memorizza, carica né vende", "Non esiste un sistema di account", "SDK di analisi, pubblicità o tracciamento", "solo sul dispositivo", "non legge né trasmette", "non effettua richieste di rete", "tramite App Store", "minori", "data di entrata in vigore", "2026-09-24"],
            "ru": ["не собирает, не хранит, не загружает на серверы и не продаёт", "Нет системы учётных записей", "SDK аналитики, рекламы или отслеживания", "только на вашем устройстве", "не читает и не передаёт", "не делает сетевых запросов", "через App Store", "включая детей", "дата вступления в силу", "2026-09-24"]
        }
        for lang, data in LOCALES.items():
            with self.subTest(lang=lang):
                self.assertEqual(set(data), set(LOCALES["zh-Hans"]))
                self.assertEqual(len(data["privacySections"]), 6)
                self.assertEqual([len(texts) for _, texts in data["privacySections"]], [1, 1, 1, 1, 1, 1])
                privacy = load_page(lang, "privacy.html")
                for heading, texts in data["privacySections"]:
                    for text in [heading] + texts:
                        self.assertIn("".join(text.split()), privacy.visible)
                source = (ROOT / site.output_path(lang, "privacy.html")).read_text(encoding="utf-8")
                for anchor in anchors[lang]:
                    self.assertIn(anchor, source)
                support = load_page(lang, "support.html")
                self.assertIn("".join(data["feedbackWarning"].split()), support.visible)
                self.assertIn("GitHub Issues", data["feedbackWarning"])
                self.assertIn("".join(data["feedbackNotice"].split()), support.visible)
                self.assertIn(site.ISSUES, [a["href"] for a in support.attrs("a")])
                self.assertIn("".join(data["privacyScope"].split()), privacy.visible)


if __name__ == "__main__":
    unittest.main()
