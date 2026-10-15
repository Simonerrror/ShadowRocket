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
