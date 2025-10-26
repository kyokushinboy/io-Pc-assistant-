# Diagnostic: verify notify calls speak when voice=True
import os, sys, importlib.util, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

NOTIF_PATH = os.path.join(ROOT, 'io', 'notification.py')
spec = importlib.util.spec_from_file_location('local_notification', NOTIF_PATH)
if spec is None or spec.loader is None:
    raise ImportError(f"Cannot load module spec from {NOTIF_PATH!r}")
notif = importlib.util.module_from_spec(spec)
spec.loader.exec_module(notif)

# set a speak callable that prints
called = {'count': 0}

def my_speak(text, **opts):
    print('[SPEAK CALLED]', text, opts)
    called['count'] += 1

notif.set_speak_callable(my_speak)

print('pre PENDING:', list(notif._PENDING.keys()))
print('pre registry keys:', list(notif._ACTION_REGISTRY.keys()))

notif.notify({'title':'diag','message':'این یک اعلان تستی است','level':'info','voice': True})

# allow background worker to process
for i in range(10):
    time.sleep(0.2)
    if called['count']>0:
        break
print('called count:', called['count'])
print('post PENDING:', list(notif._PENDING.keys()))
