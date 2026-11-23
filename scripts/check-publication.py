#!/usr/bin/env python3
"""Conservative pre-publication scan; complements, never replaces, human review."""
from __future__ import annotations
import re
import sys
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {'.git', '__pycache__', '.venv', 'venv'}
PRIVATE_DIRS = {'reports', 'demo-reports', 'artifacts', 'fixtures-private', 'private', 'credentials'}
DANGEROUS_SUFFIXES = {'.html', '.pdf', '.csv', '.sqlite', '.db', '.har', '.pcap', '.pcapng', '.gz', '.zip', '.pem', '.key', '.p12', '.pfx'}
ALLOWED_DOMAINS = {'github.com', 'img.shields.io', 'example.org', 'example.com', 'example.net', 'fsf.org', 'www.gnu.org', 'gnu.org'}
ALLOWED_SUFFIXES = ('.example.org', '.example.com', '.example.net')
EXTENSIONS = {'.md', '.mdc', '.txt', '.json', '.yaml', '.yml', '.py', '.toml', '.ini', '.sh', '.example'}
BAD_PATTERNS = {
 'private keys': re.compile(r'-----BEGIN (?:OPENSSH|RSA|EC|DSA|PGP|PRIVATE) [A-Z ]*KEY-----'),
 'cloud/token secrets': re.compile(r'(?i)(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9_-]{20,}|eyJ[A-Za-z0-9_-]{50,})'),
 'local home paths': re.compile(r'(?i)/home/(?!user/|example/)[a-z0-9_.-]+/'),
 'email address': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'),
 'private network address': re.compile(r'(?<![0-9])(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})(?![0-9])'),
 'access assignment': re.compile(r'(?im)^(?!\s*#).*\b(?:api[_-]?token|client_secret|password|access_key)\b\s*[:=]\s*["\']?(?!\$\{|\{\{|<|\s*$)[A-Za-z0-9_+/.=-]{12,}'),
}
# URLs may contain domain paths. HTML/JSON text is scanned too.
URL_RE = re.compile(r'(?i)https?://([^/\s<>)"\']+)')
HOST_RE = re.compile(r'(?<![\w.])(?:[A-Za-z0-9-]+\.){2,}[A-Za-z]{2,}(?![\w.])')
UUID_RE = re.compile(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', re.I)
PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'
MAX_PUBLIC_IMAGE_BYTES = 10 * 1024 * 1024

def scan():
    issues=[]
    files=0
    for p in sorted(ROOT.rglob('*')):
        if not p.is_file() or any(x in EXCLUDE_DIRS for x in p.relative_to(ROOT).parts):
            continue
        rel=p.relative_to(ROOT)
        # The README illustration is allowed only in its documented directory.
        # A PNG still requires human review of its visible content and provenance.
        if (p.suffix.lower() == '.png' and rel.parts[:2] == ('docs', 'images')
                and not any(x in PRIVATE_DIRS for x in rel.parts)):
            data = p.read_bytes()
            if not data.startswith(PNG_SIGNATURE) or len(data) > MAX_PUBLIC_IMAGE_BYTES:
                issues.append((str(rel), 'invalid or oversized public PNG'))
            else:
                # Reject common text/EXIF chunks that may contain sensitive metadata.
                # Other binary chunks (including content provenance) require manual review.
                import struct
                offset = 8
                forbidden = {b'tEXt', b'iTXt', b'zTXt', b'eXIf'}
                png_bad = False
                ended = False
                while offset + 12 <= len(data):
                    chunk_len = struct.unpack('>I', data[offset:offset+4])[0]
                    chunk_type = data[offset+4:offset+8]
                    if chunk_type in forbidden or offset + 12 + chunk_len > len(data):
                        png_bad = True
                        break
                    offset += 12 + chunk_len
                    if chunk_type == b'IEND':
                        ended = True
                        break
                if png_bad or not ended or offset != len(data):
                    issues.append((str(rel), 'PNG metadata or integrity requires manual cleanup'))
            files += 1
            continue
        if any(x in PRIVATE_DIRS for x in rel.parts) or p.suffix.lower() in DANGEROUS_SUFFIXES:
            issues.append((str(rel), 'private report/artifact or risky file type'))
            continue
        if p.suffix not in EXTENSIONS and p.name not in {'.gitignore', 'SECURITY.md', 'README.md', 'LICENSE'}:
            issues.append((str(p.relative_to(ROOT)), 'unknown file type'))
            continue
        files+=1
        data=p.read_bytes()
        if b'\0' in data:
            issues.append((str(p.relative_to(ROOT)), 'binary file'))
            continue
        content=data.decode('utf-8',errors='replace')
        for label,regex in BAD_PATTERNS.items():
            if p.name == "check-publication.py" and label in ("access assignment", "email address"):
                # The scanner contains literal regex samples, not actual leaked data.
                continue
            if label == "email address" and "git@github.com" in content and p.name == "publish-demo-html-report.py":
                if regex.search(content.replace("git@github.com", "")): issues.append((str(p.relative_to(ROOT)), label))
                continue
            if regex.search(content):
                # Print only a category and path, never sensitive raw material.
                issues.append((str(p.relative_to(ROOT)), label))
        if p.name == "check-publication.py":
            continue  # regex examples inside scanner are not URL/domain content
        for match in URL_RE.finditer(content):
            if "\\" in match.group(0): continue  # regex literal in source
            host=match.group(1).split('@')[-1].split(':')[0].rstrip('`\"\'').lower()
            if host not in ALLOWED_DOMAINS and not host.endswith(ALLOWED_SUFFIXES):
                issues.append((str(p.relative_to(ROOT)), 'non-example URL host'))
        for match in HOST_RE.finditer(content):
            h=match.group(0).lower()
            if h in ALLOWED_DOMAINS or h.endswith(ALLOWED_SUFFIXES): continue
            if h in {"git@github.com"}: continue
            if h.startswith(('ansible.', 'os.path.', 'urllib.', 'pathlib.', 'datetime.', 'json.', 'subprocess.', 'argparse.', 'ssl.', 'sys.', 'str.', 're.', 'proc.', 'self.', 'response.', 'data.', 'result.', 'errors.', 'p.', 'out.', 'print.', 'file.', 'fetch.', 'path.', 'repo.', 'target.', 'output.', 'args.', 'commit.', 'push.', 'status.', 'verify.', 'os.environ.')): continue
            if re.match(r'\d{4}\.\d',h): continue
            # Dotted Python symbols are reviewed manually if flagged.
            issues.append((str(p.relative_to(ROOT)), 'unapproved dotted domain/string'))
        for m in UUID_RE.finditer(content):
            # No UUIDs are necessary in this public snapshot.
            issues.append((str(p.relative_to(ROOT)), 'UUID present'))
    # Also inspect the Git index: .gitignore is bypassable with git add -f.
    if (ROOT / '.git').exists():
        p = subprocess.run(['git', '-C', str(ROOT), 'ls-files', '-z'], capture_output=True)
        if p.returncode == 0:
            for relbytes in p.stdout.split(b'\0'):
                if not relbytes: continue
                rel = Path(relbytes.decode('utf-8', errors='replace'))
                if any(x in PRIVATE_DIRS for x in rel.parts) or rel.suffix.lower() in DANGEROUS_SUFFIXES:
                    issues.append((str(rel), 'forbidden file staged or tracked in Git'))
    return files,sorted(set(issues))

if __name__ == '__main__':
    n,issues=scan()
    print(f'Publication scan: {n} files checked; {len(issues)} issue categories')
    for p,kind in issues: print(f'  {p}: {kind}')
    if issues: sys.exit(1)
    print('No matching sensitive patterns detected (manual review still required).')
