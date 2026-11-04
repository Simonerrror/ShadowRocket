from __future__ import annotations

import re
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, unquote, urljoin, urlsplit

from scripts.build_site import build_page, read_deeplink


ROOT = Path(__file__).resolve().parents[1]
SITE_URL = "https://simonerrror.github.io/ShadowRocket/"
PUBLIC = "https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main"


class Page(HTMLParser):
    def __init__(self, text: str):
        super().__init__()
        self.links: dict[str, str] = {}
        self.ids: set[str] = set()
        self.assets: list[str] = []
        self.navigation: list[dict[str, str]] = []
        self._in_navigation = False
        self._nav_link = None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "nav" and attrs.get("aria-label") == "Разделы сайта":
            self._in_navigation = True
        if "id" in attrs:
            self.ids.add(attrs["id"])
        if tag == "a":
            self.links[attrs.get("id", attrs["href"])] = attrs["href"]
            if self._in_navigation:
                self._nav_link = {"href": attrs["href"], "label": "", "current": attrs.get("aria-current", "")}
                self.navigation.append(self._nav_link)
        if tag == "img":
            self.assets.append(attrs["src"])
        if tag == "link" and attrs.get("rel") == "icon":
            self.assets.append(attrs["href"])

    def handle_data(self, data):
        if self._nav_link is not None:
            self._nav_link["label"] += data

    def handle_endtag(self, tag):
        if tag == "a":
            self._nav_link = None
        elif tag == "nav":
            self._in_navigation = False


class PublicSiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "docs/index.html").read_text()
        cls.page = Page(cls.html)

    def test_shared_navigation_connects_all_sections_from_both_pages(self):
        targets = {"Главная": "", "Shadowrocket": "#shadowrocket", "Clash": "clash/", "INCY": "#incy"}
        for relative, active in (("", "Главная"), ("clash/", "Clash")):
            html = (ROOT / "docs" / relative / "index.html").read_text()
            page = Page(html)
            self.assertEqual([link["label"] for link in page.navigation], list(targets))
            self.assertEqual([link["label"] for link in page.navigation if link["current"] == "page"], [active])
            for link in page.navigation:
                destination = urlsplit(urljoin(SITE_URL + relative, link["href"]))
                expected = urlsplit(urljoin(SITE_URL, targets[link["label"]]))
                self.assertEqual((destination.scheme, destination.netloc, destination.path),
                                 (expected.scheme, expected.netloc, expected.path))
                if expected.fragment:
                    self.assertEqual(destination.fragment, expected.fragment)
                if destination.fragment:
                    target_path = destination.path.removeprefix("/ShadowRocket/")
                    target = Page((ROOT / "docs" / target_path / "index.html").read_text())
                    self.assertIn(destination.fragment, target.ids)
            first_action = html.index("<form") if relative else html.index("Добавить в Shadowrocket")
            self.assertLess(html.index('<nav aria-label="Разделы сайта"'), first_action)

    def test_generated_page_is_current_and_embeds_both_incy_profiles(self):
        default = read_deeplink(ROOT / "INCY/DEFAULT.DEEPLINK")
        ru = read_deeplink(ROOT / "INCY/RU-VPN.DEEPLINK")
        self.assertEqual(self.html, build_page((ROOT / "site/index.html").read_text(), default, ru))
        self.assertEqual(self.page.links["incy-default"], default)
        self.assertEqual(self.page.links["incy-ru"], ru)
        self.assertNotIn("{{", self.html)

    def test_buttons_import_the_public_config_and_all_numbered_modules_directly(self):
        self.assertIn(f"shadowrocket://config/add/{PUBLIC}/shadowrocket.conf", self.page.links.values())
        buttons = re.findall(r'<a id="module-[^"]+" class="button" href="([^"]+)"><span><span class="num">([^<]+)</span>([^<]+)<small', self.html)
        shown = {}
        numbers = []
        for href, number, name in buttons:
            if href.startswith("shadowrocket://install?"):
                source = parse_qs(urlsplit(href).query)["module"][0]
            else:
                source = href
                self.assertEqual(source, f"{PUBLIC}/modules/dns_override.module")
            self.assertTrue(source.startswith(f"{PUBLIC}/modules/"))
            filename = unquote(urlsplit(source).path.rsplit("/", 1)[1])
            shown[filename] = f"{number} · {name}"
            numbers.append(number)
        actual = {p.name: re.search(r"^#!name=(.+)$", p.read_text(), re.M)[1]
                  for p in (ROOT / "modules").glob("*.module")}
        self.assertEqual(shown, actual)
        self.assertEqual(numbers, sorted(set(numbers)))
        self.assertTrue(numbers[0].startswith("01_"))
        self.assertTrue(numbers[-1].startswith("90_"))

    def test_images_and_favicon_work_under_the_project_path(self):
        self.assertTrue((ROOT / "docs/.nojekyll").is_file())
        self.assertGreater(len(self.page.assets), 1)
        for asset in self.page.assets:
            with self.subTest(asset=asset):
                resolved = urlsplit(urljoin(SITE_URL, asset))
                self.assertEqual(resolved.netloc, "simonerrror.github.io")
                self.assertTrue(resolved.path.startswith("/ShadowRocket/"))
                self.assertTrue((ROOT / "docs" / resolved.path.removeprefix("/ShadowRocket/")).is_file())

    def test_readme_and_documentation_links_land_on_existing_buttons(self):
        for path in ("README.md", "docs/setup.md", "docs/shadowrocket-modules.md", "INCY/README.md"):
            text = (ROOT / path).read_text()
            self.assertNotIn("workers.dev", text)
            for fragment in re.findall(re.escape(SITE_URL) + r"#([a-z0-9-]+)", text):
                with self.subTest(path=path, fragment=fragment):
                    self.assertIn(fragment, self.page.ids)
        self.assertIn(SITE_URL, (ROOT / "README.md").read_text())
        self.assertNotIn("workers.dev", self.html)
        self.assertTrue(all(href and href != "#" for href in self.page.links.values()))
        self.assertLess(self.html.index("Добавить в Shadowrocket"), self.html.index("Блог ↗"))
        self.assertIn('lang="ru"', self.html)
        self.assertIn('name="viewport"', self.html)
