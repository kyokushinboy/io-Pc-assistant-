# Diagnostic script: inspect notification runtime state
import os
import sys
import importlib.util

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

NOTIF_PATH = os.path.join(ROOT, 'io', 'notification.py')
spec = importlib.util.spec_from_file_location('local_notification', NOTIF_PATH)
if spec is None:
    raise ImportError(f"Could not create module spec for {NOTIF_PATH}")
notification = importlib.util.module_from_spec(spec)
loader = getattr(spec, "loader", None)
if loader is None or not hasattr(loader, "exec_module"):
    raise ImportError(f"No loader available to execute module for {NOTIF_PATH}")
loader.exec_module(notification)

print('VOICE_CONFIG:', notification._config.get('voice'), 'VOICE_OPTIONS:', notification._config.get('voice_options'))
print('VOICE_QUEUE:', notification._config.get('voice_queue'))
print('_speak_callable set?:', getattr(notification, '_speak_callable') is not None)
print('ACTION_REGISTRY keys:', list(notification._ACTION_REGISTRY.keys()))
print('PENDING ids:', list(notification._PENDING.keys()))
print('TTS worker thread alive?:', getattr(notification, '_tts_worker_thread') is not None)
print('TTS queue size:', notification._tts_queue.qsize())

# If there is a pending notification, show its content
for nid, it in notification._PENDING.items():
    print('PENDING', nid, it)
