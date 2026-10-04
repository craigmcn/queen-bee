"""Tests for check_csp_hash.py. Run from the repo root:

    python3 -m unittest discover scripts
"""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import check_csp_hash

PAGE = "<head><script>console.log(1)</script></head>"


class CheckCspHashTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.toml = self.dir / "netlify.toml"
        patcher = mock.patch.object(check_csp_hash, "NETLIFY_TOML", self.toml)
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_check(self, html, config):
        page = self.dir / "index.html"
        page.write_text(html)
        self.toml.write_text(config)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            try:
                check_csp_hash.main([str(page)])
                code = 0
            except SystemExit as error:
                code = error.code
        return code, output.getvalue()

    def test_passes_when_every_inline_script_is_allowed(self):
        (allowed,) = check_csp_hash.inline_script_hashes(PAGE)
        code, output = self.run_check(PAGE, f"script-src 'self' {allowed}")
        self.assertEqual(code, 0)
        self.assertIn("allows every inline script", output)

    def test_fails_naming_the_hash_when_the_script_changed(self):
        (allowed,) = check_csp_hash.inline_script_hashes(PAGE)
        code, output = self.run_check(PAGE.replace("1", "2"), f"script-src 'self' {allowed}")
        self.assertEqual(code, 1)
        self.assertRegex(output, r"inline script 'sha256-[^']+' isn't allowed")

    def test_fails_when_the_redirect_script_is_missing(self):
        code, output = self.run_check("<head></head>", "script-src 'self'")
        self.assertEqual(code, 1)
        self.assertIn("no inline scripts found", output)

    def test_real_source_page_is_allowed(self):
        root = check_csp_hash.ROOT
        html = (root / "index.html").read_text()
        config = (root / "netlify.toml").read_text()
        self.assertEqual(check_csp_hash.missing_hashes(html, config), [])


if __name__ == "__main__":
    unittest.main()
