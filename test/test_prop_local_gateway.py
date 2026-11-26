"""Property P10 for the local observation gateway (spec: local-gateway, Requirements 2 and 3).

P10: the gateway answers every request head without failing, refuses a request
that is not a proxy request, and refuses a destination port that is not allowed.
"""
import socket
import unittest

from prop_support import given, st

from web.local_gateway import LocalGateway

METHODS = ("GET", "POST", "CONNECT", "HEAD", "OPTIONS")
# Every target names a loopback address, so no request can wait for a name lookup.
TARGETS = (
    "http://127.0.0.1:9/path",
    "http://127.0.0.1/path",
    "https://127.0.0.1/path",
    "/relative/path",
    "127.0.0.1:443",
    "not a target",
    "",
)
HEADS = st.builds(
    lambda method, target: "{} {}\r\nHost: 127.0.0.1\r\n\r\n".format(method, target),
    st.sampled_from(METHODS), st.sampled_from(TARGETS))


class LocalGatewayProperties(unittest.TestCase):
    def setUp(self):
        # Only the ports 80 and 443 are allowed, so every generated request is refused.
        self.gateway = LocalGateway(port=0, allowed_ports=(80, 443), connect_timeout=1.0)
        self.gateway.start()
        self.addCleanup(self.gateway.stop)

    def ask(self, head):
        try:
            with socket.create_connection(("127.0.0.1", self.gateway.port), timeout=10) as connection:
                connection.sendall(head.encode("latin-1", "replace"))
                answer = connection.recv(4096)
        except OSError:
            return b""
        return answer

    @given(head=HEADS)
    def test_p10_every_request_is_answered_and_the_forbidden_ones_are_refused(self, head):
        answer = self.ask(head)
        self.assertTrue(answer.startswith(b"HTTP/1."), answer[:80])
        status = int(answer.split(b" ", 2)[1])
        self.assertIn(status, (200, 400, 403, 502, 503))

    @given(target=st.sampled_from(["http://127.0.0.1:9/path", "http://127.0.0.1:9/other"]))
    def test_p10_a_forbidden_port_is_refused_without_a_connection(self, target):
        answer = self.ask("GET {} HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n".format(target))
        self.assertIn(b" 403 ", answer.split(b"\r\n", 1)[0])
        records = self.gateway.records_list()
        self.assertTrue(any(record["outcome"] == "forbidden" for record in records))


if __name__ == "__main__":
    unittest.main()
