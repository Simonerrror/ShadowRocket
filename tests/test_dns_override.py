import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class DNSOverrideTests(unittest.TestCase):
    def test_override_provides_manual_dns_fields_without_arguments(self):
        text = (ROOT / 'modules/dns_override.module').read_text()
        general = text.split('[General]', 1)[1]
        values = dict(line.split('=', 1) for line in general.splitlines()
                      if '=' in line and not line.startswith('#'))
        values = {key.strip(): value.strip() for key, value in values.items()}
        self.assertEqual(values, {'dns-server': '9.9.9.9', 'direct-dns-server': '', 'dns-direct-system': 'false'})
        self.assertNotIn('#!arguments', text)
        self.assertNotIn('{{{', text)

    def test_google_ai_routes_web_dependencies_through_direct_dns(self):
        text = (ROOT / 'modules/google_ai_smart_dns_mobile.module').read_text()
        rules = [line.split(',') for line in text.splitlines()
                 if line.startswith(('DOMAIN,', 'DOMAIN-SUFFIX,'))]

        def policy(host):
            for kind, domain, target in rules:
                if host == domain or (kind == 'DOMAIN-SUFFIX' and
                                      host.endswith('.' + domain)):
                    return target
            return None

        for host, expected in {
            'gemini.google.com': 'DIRECT',
            'waa-pa.clients6.google.com': 'DIRECT',
            'geminiweb-pa.clients6.google.com': 'DIRECT',
            'youtubei.googleapis.com': 'PROXY',
            'unrelated.clients6.google.com': None,
            'www.google.com': None,
        }.items():
            with self.subTest(host=host):
                self.assertEqual(policy(host), expected)
