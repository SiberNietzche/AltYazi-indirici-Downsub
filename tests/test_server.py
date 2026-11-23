import socket
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from altyazi.server import create_server  # noqa: E402


class ServerStartTests(unittest.TestCase):
    def test_starts_without_name_lookup(self):
        # macOS 26'da getfqdn 35-70 saniye sürebiliyor; sunucu açılırken hiç çağrılmamalı.
        with mock.patch.object(socket, "getfqdn", side_effect=AssertionError("getfqdn çağrıldı")):
            server = create_server(object(), 0)
        try:
            host, port = server.server_address[:2]
            self.assertEqual(host, "127.0.0.1")
            self.assertEqual(server.server_name, "127.0.0.1")
            self.assertEqual(server.server_port, port)
            with socket.create_connection((host, port), timeout=2):
                pass
        finally:
            server.server_close()


if __name__ == "__main__":
    unittest.main()
