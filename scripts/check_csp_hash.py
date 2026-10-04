"""Check that netlify.toml's CSP allows every inline script in a built page.

Usage (from the repo root, after a build):
    python3 scripts/check_csp_hash.py dist/index.html

src/securityHeaders.test.ts checks the source index.html; this checks what's
actually served, in case the build ever changes the script's bytes.
"""

import base64
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NETLIFY_TOML = ROOT / "netlify.toml"


def inline_script_hashes(html):
    scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
    return [f"'sha256-{base64.b64encode(hashlib.sha256(s.encode()).digest()).decode()}'" for s in scripts]


def missing_hashes(html, config):
    """The inline-script hashes in html that config doesn't allow."""
    return [h for h in inline_script_hashes(html) if h not in config]


def main(paths):
    config = NETLIFY_TOML.read_text()
    failed = False
    for path in paths:
        html = Path(path).read_text()
        if not inline_script_hashes(html):
            print(f"{path}: no inline scripts found; expected the trailing-slash redirect")
            failed = True
        for missing in missing_hashes(html, config):
            print(f"{path}: inline script {missing} isn't allowed by netlify.toml's CSP")
            failed = True
    if failed:
        sys.exit(1)
    print(f"CSP allows every inline script in {', '.join(paths)}")


if __name__ == "__main__":
    main(sys.argv[1:] or ["dist/index.html"])
