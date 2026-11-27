"""Property P11 for the secret scanner (spec: dev-guardrails, Requirement 3).

P11: a credential embedded anywhere in arbitrary text is reported with its kind
and line, and no report ever contains the credential itself. In a diff, only
added lines are reported.
"""
import re
import string
import sys
import unittest
from pathlib import Path

from prop_support import assume, example, given, st  # Raises SkipTest when Hypothesis is missing.

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "kiro"))

import scan_secrets  # noqa: E402

ALNUM = string.ascii_letters + string.digits
UPPER_ALNUM = string.ascii_uppercase + string.digits
LINE_BREAKS = "\n\r\x0b\x0c\x1c\x1d\x1e\x85\u2028\u2029"

# One line of arbitrary text: any code point except surrogates and line boundaries.
LINE_TEXT = st.text(alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters=LINE_BREAKS),
                    max_size=40)


def fixed(alphabet, size):
    return st.text(alphabet=alphabet, min_size=size, max_size=size)


# Credentials are assembled from parts so this file never contains one.
GITHUB_CLASSIC = st.builds("{}_{}".format, st.sampled_from(["ghp", "gho", "ghu", "ghs", "ghr"]), fixed(ALNUM, 36))
GITHUB_FINE_GRAINED = st.builds(("github" + "_pat_{}").format, fixed(ALNUM + "_", 82))
AWS_KEY_ID = st.builds("{}{}".format, st.sampled_from(["AK" + "IA", "AS" + "IA"]), fixed(UPPER_ALNUM, 16))
PRIVATE_KEY = st.builds(("-----BEGIN " + "{}" + "PRIVATE KEY-----").format,
                        st.sampled_from(["", "RSA ", "OPENSSH ", "EC ", "DSA ", "ENCRYPTED "]))
SSH_PASSWORD = st.builds(('"ssh' + '_pass": "{}"').format,
                         st.text(alphabet=string.ascii_letters + string.digits + "!#$%&()*+,-./:;<=>?@[]^_{|}~ ",
                                 min_size=1, max_size=24))
URL_CREDENTIALS = st.builds("{}://{}:{}@{}".format,
                            st.sampled_from(["http", "https", "socks5", "socks5h", "ftp"]),
                            st.text(alphabet=ALNUM + "._-", min_size=1, max_size=16),
                            st.text(alphabet=ALNUM + "._~-", min_size=1, max_size=24),
                            st.from_regex(r"[a-z][a-z0-9.-]{0,20}", fullmatch=True))

CREDENTIALS = st.one_of(
    GITHUB_CLASSIC.map(lambda value: ("github-token", value)),
    GITHUB_FINE_GRAINED.map(lambda value: ("github-fine-grained-token", value)),
    AWS_KEY_ID.map(lambda value: ("aws-access-key-id", value)),
    PRIVATE_KEY.map(lambda value: ("private-key", value)),
    SSH_PASSWORD.map(lambda value: ("ssh-password", value)),
    URL_CREDENTIALS.map(lambda value: ("url-credentials", value)),
)

# Private identifiers like the ones in scratch/private-denylist.txt: addresses and host names.
DENYLIST_ENTRY = st.one_of(
    st.builds("10.{}.{}.{}".format, st.integers(0, 255), st.integers(0, 255), st.integers(0, 255)),
    st.from_regex(r"[a-z][a-z0-9-]{8,20}", fullmatch=True),
)


# A preview reveals at most four characters of what matched.
PREVIEW = re.compile(r"\A.{1,4}\.\.\. \(\d+ chars\)\Z", re.DOTALL)


def place(before, prefix, value, suffix, after):
    """Return the text and the 1-based line number that holds `value`."""
    lines = list(before) + [prefix + value + suffix] + list(after)
    return "\n".join(lines), len(before) + 1


class SecretScannerProperties(unittest.TestCase):
    @given(credential=CREDENTIALS, before=st.lists(LINE_TEXT, max_size=3), prefix=LINE_TEXT,
           suffix=LINE_TEXT, after=st.lists(LINE_TEXT, max_size=3))
    def test_embedded_credentials_are_found_and_masked(self, credential, before, prefix, suffix, after):
        kind, value = credential
        text, line = place(before, prefix, value, suffix, after)
        assume(not scan_secrets.ALLOW_MARKER.search(text))
        findings = scan_secrets.scan_text(text, "sample.txt")
        self.assertIn((kind, line), [(finding.kind, finding.line) for finding in findings])
        for finding in findings:
            self.assertRegex(finding.preview, PREVIEW)
        self.assertNotIn(value, scan_secrets.format_findings(findings))

    @given(entry=DENYLIST_ENTRY, prefix=LINE_TEXT, suffix=LINE_TEXT,
           flips=st.lists(st.booleans(), min_size=21, max_size=21))
    # U+0130 lower-cases to two code points; positions taken from text.lower() used to drift.
    @example(entry="10.1.2.3", prefix="\u0130" * 12, suffix="", flips=[True] * 21)
    def test_denylist_entries_match_in_any_case(self, entry, prefix, suffix, flips):
        shown = "".join(char.upper() if flip else char for char, flip in zip(entry, flips))
        text = prefix + shown + suffix
        assume(not scan_secrets.ALLOW_MARKER.search(text))
        findings = scan_secrets.scan_text(text, "sample.txt", denylist=(entry,))
        denied = [finding for finding in findings if finding.kind == "private-denylist"]
        self.assertEqual(len(denied), 1)
        for finding in findings:
            self.assertRegex(finding.preview, PREVIEW)
            self.assertNotIn(entry, finding.preview.lower())
        visible = entry[:4] if len(entry) > 8 else entry[:1]
        self.assertTrue(denied[0].preview.lower().startswith(visible), denied[0].preview)

    @given(credential=CREDENTIALS, context=st.integers(0, 5), added=st.booleans())
    def test_diff_scan_reports_added_lines_only(self, credential, context, added):
        kind, value = credential
        old = context + 1 + (0 if added else 1)
        new = context + 1 + (1 if added else 0)
        diff = ["diff --git a/web/x.py b/web/x.py", "--- a/web/x.py", "+++ b/web/x.py",
                "@@ -1,{} +1,{} @@".format(old, new)]
        diff += [" context {}".format(index) for index in range(context)]
        diff += [("+" if added else "-") + value, " tail"]
        findings = scan_secrets.scan_diff("\n".join(diff) + "\n")
        if added:
            self.assertIn((kind, "web/x.py", context + 1),
                          [(finding.kind, finding.source, finding.line) for finding in findings])
        else:
            self.assertEqual(findings, [])


if __name__ == "__main__":
    unittest.main()
