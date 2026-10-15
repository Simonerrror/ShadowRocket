import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class DNSOverrideTests(unittest.TestCase):
    def test_override_keeps_main_and_fallback_dns_from_profile(self):
        text = (ROOT / 'modules/dns_override.module').read_text()
        general = text.split('[General]', 1)[1]
        values = dict(line.split(' = ', 1) for line in general.splitlines() if ' = ' in line)
        self.assertEqual(values, {'direct-dns-server': '{{{SmartDNS}}}', 'dns-direct-system': 'false'})
        self.assertIn('#!arguments=SmartDNS:', text)
        self.assertIn('Smart DNS', text)
