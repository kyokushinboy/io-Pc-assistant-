# Diagnostic: compare module instances and registration points
import os, sys, importlib
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# import package-style
try:
    pkg = importlib.import_module('io')
    print('Imported package io as', pkg)
except Exception as e:
    print('Package import failed:', e)

# check sys.modules for notification entries
notif_keys = [k for k in sys.modules.keys() if 'notification' in k]
print('notification-like modules in sys.modules:', notif_keys)

# attempt to import io.notification
try:
    mod1 = importlib.import_module('io.notification')
    print('io.notification module:', mod1, 'id:', id(mod1))
except Exception as e:
    print('Failed to import io.notification:', e)

# load by path
import importlib.util
NOTIF_PATH = os.path.join(ROOT, 'io', 'notification.py')
spec = importlib.util.spec_from_file_location('local_notification', NOTIF_PATH)
assert spec is not None, f"Could not create module spec for {NOTIF_PATH}"
assert spec.loader is not None, f"No loader available for spec of {NOTIF_PATH}"
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
print('local_notification module:', local, 'id:', id(local))

# compare important attributes
for m_name, m in [('io.notification', sys.modules.get('io.notification')),
                  ('local', local)]:
    if m is None:
        print(m_name, 'is None')
        continue
    print('module', m_name, 'has _speak_callable?', hasattr(m, '_speak_callable') and getattr(m,'_speak_callable') is not None)
    print('module', m_name, 'action registry keys:', list(getattr(m,'_ACTION_REGISTRY', {}).keys()))
    print('module', m_name, 'pending ids:', list(getattr(m,'_PENDING', {}).keys()))

# Print reference equality
print('io.notification is local_notification?', sys.modules.get('io.notification') is local)
