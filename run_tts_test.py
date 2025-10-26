"""Run a small TTS test on Windows using the project's speak() and notification voice flow.

This script will:
- load io/io.py module
- enable voice in notification config
- set speak callable to a wrapper that prints and calls engine if available
- call io_module.speak(...) with voice options
- call notify with voice: True to exercise NotificationManager->speak
"""
import importlib.util
import importlib.machinery
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
IO_PATH = os.path.join(PROJECT_ROOT, 'io', 'io.py')
loader = importlib.machinery.SourceFileLoader('assist_io', IO_PATH)
spec = importlib.util.spec_from_loader('assist_io', loader)
if spec is None:
    raise ImportError(f"Could not create module spec for {IO_PATH!r}")
io_module = importlib.util.module_from_spec(spec)
loader.exec_module(io_module)

# Enable voice in notification config for test
# ensure the project root is on sys.path so the local `io.notification` can be loaded from file
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import importlib.util
notif_path = os.path.join(PROJECT_ROOT, 'io', 'notification.py')
spec2 = importlib.util.spec_from_file_location('io.notification', notif_path)
if spec2 is None:
    raise ImportError(f"Could not create module spec for {notif_path!r}")
notif = importlib.util.module_from_spec(spec2)
if spec2.loader is None:
    raise ImportError(f"Could not create loader for {notif_path!r}")
spec2.loader.exec_module(notif)  # type: ignore

notif._config['voice'] = True

print('Calling speak directly (with voice options)...')
try:
    io_module.speak('این یک تست صدای فارسی است', rate=140, volume=0.9)
    print('speak() completed')
except Exception as e:
    print('speak() error:', e)

print('Calling notify with voice: True...')
try:
    notif.notify({'title':'TTS Test','message':'این اعلان با TTS خوانده می‌شود','level':'info','voice':True})
    print('notify completed')
except Exception as e:
    print('notify error:', e)

print('Done')
