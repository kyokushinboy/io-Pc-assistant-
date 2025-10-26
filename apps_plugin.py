"""Simple plugin to handle launching apps defined in config/apps.json

Plugin contract:
- provide function `can_handle(query: str) -> bool`
- provide function `handle(query: str) -> dict|bool` which performs action and returns
  {'handled': True, 'candidate': path} on success (or True) and False if not handled.
"""
import os
import sys
import typing
import logging
import importlib
import json
import re
from pathlib import Path

# Prefer to reuse main logger if available; otherwise create a plugin logger
def _get_logger():
    # Try to retrieve the logger object from loaded modules (avoid importing stdlib io)
    try:
        # If main package loaded as `io.io`, try that first
        mod = sys.modules.get('io.io') or sys.modules.get('io')
        if mod and hasattr(mod, 'logger'):
            return getattr(mod, 'logger')
    except Exception:
        pass
    # Fallback to module-specific logger
    return logging.getLogger('io.plugins.apps')

logger = _get_logger()

CONFIG = Path(__file__).resolve().parent.parent / 'config' / 'apps.json'


def load_config():
    apps = {}
    aliases = {}
    try:
        with open(CONFIG, 'r', encoding='utf-8') as f:
            data = json.load(f)
            apps = data.get('apps', {}) or {}
            aliases = data.get('aliases', {}) or {}
            # Normalize string entries to lists
            for k, v in list(apps.items()):
                if isinstance(v, str):
                    apps[k] = [v]
                elif isinstance(v, list):
                    apps[k] = v
                else:
                    apps[k] = []
    except Exception as e:
        logger.exception('Failed to load apps config: %s', e)
    return apps, aliases


APPS, ALIASES = load_config()


def _normalize_text(t: str) -> str:
    return (t or '').lower().strip()


def can_handle(query: str) -> bool:
    q = _normalize_text(query)
    # match whole words for keys and aliases to reduce false positives
    for k in APPS.keys():
        if re.search(r'\b' + re.escape(k) + r'\b', q):
            return True
    for a in ALIASES.keys():
        if re.search(r'\b' + re.escape(a) + r'\b', q):
            return True
    # also common verbs + app name patterns
    verbs = ['باز', 'باز کن', 'open', 'اجرای', 'اجرا کن', 'run']
    for v in verbs:
        if v in q:
            # if any known app key appears with a verb, claim it
            for k in list(APPS.keys()) + list(ALIASES.keys()):
                if k in q:
                    return True
    return False


def resolve_candidate(app_key: str, username: str) -> list:
    candidates = APPS.get(app_key, [])
    resolved = []
    for c in candidates:
        # Expand environment variables and user placeholder
        c_expanded = os.path.expandvars(c)
        c_expanded = c_expanded.replace('{username}', username)
        c_expanded = os.path.expanduser(c_expanded)
        resolved.append(c_expanded)
    return resolved


def _try_launch(path: str) -> tuple[bool, str]:
    """Try to launch given path. Returns (success, errmsg or '')"""
    try:
        if sys.platform.startswith('win'):
            try:
                os.startfile(path)
            except OSError:
                # Fallback to cmd start which can handle some shell shortcuts
                import subprocess
                subprocess.Popen(['cmd', '/c', 'start', '""', path], shell=False)
        else:
            import subprocess
            subprocess.Popen([path], shell=False)
        return True, ''
    except Exception as e:
        logger.exception('Launch failed for %s: %s', path, e)
        return False, str(e)


def handle(query: str) -> typing.Union[bool, dict]:
    """Try to launch an app based on the query.

    Returns:
      - {'handled': True, 'candidate': path} on success
      - False if the plugin did not handle the query
      - {'handled': False, 'error': '...'} if attempted but failed
    """
    q = _normalize_text(query)
    username = None
    try:
        username = os.getlogin()
    except Exception:
        username = os.environ.get('USERNAME') or os.environ.get('USER') or ''

    app_key = None
    # Find by key
    for k in APPS.keys():
        if re.search(r'\b' + re.escape(k) + r'\b', q):
            app_key = k
            break
    # Find by alias
    if not app_key:
        for a, k in ALIASES.items():
            if re.search(r'\b' + re.escape(a) + r'\b', q):
                app_key = k
                break
    if not app_key:
        return False

    candidates = resolve_candidate(app_key, username)
    # Try candidates first
    for candidate in candidates:
        if os.path.exists(candidate):
            ok, err = _try_launch(candidate)
            if ok:
                logger.info('Launched %s: %s', app_key, candidate)
                return {'handled': True, 'candidate': candidate}
            else:
                # attempt next candidate
                continue

    # Try common default locations for well-known apps
    fallback_map = {
        'steam': [r'C:\Program Files (x86)\Steam\steam.exe', r'C:\Program Files\Steam\steam.exe'],
        'vscode': [r'C:\Program Files\Microsoft VS Code\Code.exe'],
        'chrome': [r'C:\Program Files\Google\Chrome\Application\chrome.exe'],
        'firefox': [r'C:\Program Files\Mozilla Firefox\firefox.exe']
    }
    defaults = fallback_map.get(app_key, [])
    for d in defaults:
        if os.path.exists(d):
            ok, err = _try_launch(d)
            if ok:
                logger.info('Launched %s via default: %s', app_key, d)
                return {'handled': True, 'candidate': d}

    # nothing launched
    logger.debug('No candidate launched for app_key=%s (query=%s)', app_key, query)
    return {'handled': False, 'error': 'no_candidate_found'}
