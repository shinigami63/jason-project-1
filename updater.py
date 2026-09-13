"""Checks GitHub for a newer build and installs it.

The app knows its own version from a version.txt stamped into the bundle at
build time, and asks GitHub's API what the latest release is. The installer
is downloaded over HTTPS and checked against the SHA-256 GitHub publishes for
the asset before it is allowed to run -- TLS already authenticates the
download, the digest catches a truncated or swapped file as well.

Nothing here is Windows-specific except actually launching the installer, so
the check works when running from source too (it just reports version 'dev',
which is never newer or older than anything).
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

REPO = 'shinigami63/jason-project-1'
LATEST_RELEASE_API = f'https://api.github.com/repos/{REPO}/releases/latest'
INSTALLER_ASSET = 'KebzetZamenSetup.exe'
# GitHub rejects API requests without one.
USER_AGENT = 'KebbetZamen-Updater'
DEV_VERSION = 'dev'


def _bundle_dir():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def current_version():
    """The version stamped in at build time, or 'dev' when run from source."""
    try:
        with open(os.path.join(_bundle_dir(), 'version.txt'), encoding='utf-8') as f:
            return f.read().strip() or DEV_VERSION
    except OSError:
        return DEV_VERSION


def parse_version(text):
    """Pulls 1.2.3 out of whatever shape the string is ('KebzetZamen 1.0.57',
    'v1.0.57', '1.0.57'). Returns None if there is no version in it."""
    m = re.search(r'(\d+)\.(\d+)\.(\d+)', text or '')
    return tuple(int(g) for g in m.groups()) if m else None


def is_newer(latest_text, current_text):
    latest, current = parse_version(latest_text), parse_version(current_text)
    if latest is None or current is None:
        # A dev build, or a release whose name carries no version: never
        # offer an update rather than guess wrong.
        return False
    return latest > current


def _get_json(url, timeout):
    req = urllib.request.Request(url, headers={
        'User-Agent': USER_AGENT,
        'Accept': 'application/vnd.github+json',
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def check(timeout=10):
    """Asks GitHub about the latest release. Never raises -- the caller is a
    button in the app, and a dead network shouldn't look like a crash."""
    current = current_version()
    try:
        release = _get_json(LATEST_RELEASE_API, timeout)
    except (urllib.error.URLError, OSError, ValueError, TimeoutError) as e:
        return {'ok': False, 'current': current,
                'error': f'Could not reach GitHub: {e}'}

    asset = next((a for a in release.get('assets') or []
                  if a.get('name') == INSTALLER_ASSET), None)
    # The release is tagged 'latest' (a rolling tag), so the version lives in
    # its name instead.
    latest = release.get('name') or release.get('tag_name') or ''
    info = {
        'ok': True,
        'current': current,
        'latest': latest,
        'newer': bool(asset) and is_newer(latest, current),
        'url': (asset or {}).get('browser_download_url'),
        'digest': (asset or {}).get('digest'),
        'size': (asset or {}).get('size'),
    }
    if not asset:
        info['error'] = f'The latest release has no {INSTALLER_ASSET} to install.'
    return info


def _sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def download_installer(url, digest=None, timeout=120, dest_dir=None):
    """Downloads the installer and checks it against GitHub's digest.

    Returns (path, None) or (None, error). A file that fails the digest check
    is deleted rather than left somewhere it could be run by hand."""
    if not url:
        return None, 'No installer to download.'
    dest_dir = dest_dir or tempfile.mkdtemp(prefix='kebzet_update_')
    path = os.path.join(dest_dir, INSTALLER_ASSET)
    req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r, open(path, 'wb') as f:
            while True:
                chunk = r.read(1 << 20)
                if not chunk:
                    break
                f.write(chunk)
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        return None, f'Download failed: {e}'

    if digest:
        expected = digest.split(':', 1)[-1].strip().lower()
        actual = _sha256(path)
        if actual != expected:
            try:
                os.remove(path)
            except OSError:
                pass
            return None, ('The downloaded installer does not match what GitHub '
                          'published, so it was discarded. Try again.')
    return path, None


def launch_installer(path):
    """Starts the installer and returns -- the caller then has to exit, since
    the installer replaces the files this process is running from.

    /SILENT shows progress but asks nothing; the installer's own [Run] entry
    starts the app again when it finishes."""
    if not sys.platform.startswith('win'):
        return 'Installing from inside the app only works on Windows.'
    try:
        subprocess.Popen([path, '/SILENT', '/SUPPRESSMSGBOXES',
                          '/CLOSEAPPLICATIONS', '/NORESTART'],
                         close_fds=True)
    except OSError as e:
        return f'Could not start the installer: {e}'
    return None
