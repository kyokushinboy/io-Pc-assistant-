"""Lightweight simulation harness for exercising safe assistant scenarios without microphone or TTS.

This script:
- Loads the assistant module from `io/io.py` (as tests do)
- Replaces `speak` with a no-op printer to avoid TTS audio
- Runs: detect_emotion, notification dispatch (voice=False), plugin dispatch simulation, list_desktop_shortcuts, get_today_events

Run: python tools/simulate_scenarios.py
"""
import importlib.util
import importlib.machinery
import os
import sys
from types import SimpleNamespace

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
IO_PATH = os.path.join(PROJECT_ROOT, 'io', 'io.py')
loader = importlib.machinery.SourceFileLoader('assist_io', IO_PATH)
spec = importlib.util.spec_from_loader('assist_io', loader)
if spec is None:
    raise ImportError("Failed to create module spec for assist_io")
io_module = importlib.util.module_from_spec(spec)
loader.exec_module(io_module)

# Monkeypatch speak to avoid TTS during simulation
def fake_speak(text):
    print(f"[SPEAK] {text}")

try:
    setattr(io_module, 'speak', fake_speak)
except Exception:
    print("Could not monkeypatch speak; continuing.")

print("--- simulate: detect_emotion ---")
for txt in ['من خیلی خوشحال هستم', 'امروز غمگینم و خسته', 'این یک جمله عادی است بدون احساس خاص']:
    res = io_module.detect_emotion(txt)
    print(f"input: {txt} -> emotion: {res}")

print('\n--- simulate: notifications ---')
try:
    # Try to import the project's notification module as a package
    import importlib
    try:
        notif = importlib.import_module('io.notification')
    except Exception:
        # If 'io' is not a package, load notification.py by path
        notif_path = os.path.join(PROJECT_ROOT, 'io', 'notification.py')
        spec = importlib.util.spec_from_file_location('io.notification', notif_path)
        if spec is None:
            raise ImportError(f"Failed to create module spec for io.notification from {notif_path}")
        notif = importlib.util.module_from_spec(spec)
        loader = spec.loader
        if loader is None:
            raise ImportError(f"No loader available for io.notification spec from {notif_path}")
        loader.exec_module(notif)  # type: ignore

    notif.notify({'title': 'SIM', 'message': 'این یک اعلان تستی است', 'level': 'info', 'voice': False, 'persistent': False})
    notif.notify({'title': 'SIM', 'message': 'این یک اعلان اخطار است', 'level': 'warning', 'voice': False, 'persistent': False})
    print('Notifications dispatched (logged).')
except Exception as e:
    print('Notification test failed:', e)

print('\n--- simulate: plugin dispatch (mock) ---')
mod = SimpleNamespace()
mod.__name__ = 'plugins.mock_sim'
def can_handle(q):
    return 'simme' in q

def handle(q):
    print('[mock plugin] handling', q)
    return True
mod.can_handle = can_handle
mod.handle = handle

original_plugins = list(getattr(io_module, 'PLUGINS', []))
io_module.PLUGINS.insert(0, mod)
try:
    q = 'please simme now'
    handled = False
    for m in io_module.PLUGINS:
        if hasattr(m, 'can_handle') and m.can_handle(q):
            r = m.handle(q)
            handled = bool(r)
            break
    print('Plugin handled:', handled)
finally:
    io_module.PLUGINS[:] = original_plugins

print('\n--- simulate: list_desktop_shortcuts ---')
try:
    io_module.list_desktop_shortcuts()
    print('Listed desktop shortcuts (check logs).')
except Exception as e:
    print('list_desktop_shortcuts failed:', e)

print('\n--- simulate: get_today_events ---')
try:
    events = io_module.get_today_events()
    print('Today events:', events)
except Exception as e:
    print('get_today_events failed:', e)

print('\n--- simulation complete ---')
