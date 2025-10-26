# Simple test for actionable notifications and registry
import logging
import time
import sys
import os

# Ensure project root is first on sys.path so 'io' package resolves to local package
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import importlib.util

# Load notification module directly from file to avoid stdlib 'io' conflict
NOTIF_PATH = os.path.join(ROOT, 'io', 'notification.py')
spec = importlib.util.spec_from_file_location('local_notification', NOTIF_PATH)
if spec is None or spec.loader is None:
    raise ImportError(f"Cannot load module spec or loader from {NOTIF_PATH}")
notification = importlib.util.module_from_spec(spec)
spec.loader.exec_module(notification)

logging.basicConfig(level=logging.DEBUG)

RESULT = {'called': False}

def my_action():
    print('my_action called')
    RESULT['called'] = True

# register under a name
notification.register_action('test.snooze', my_action)

# send a notification with an action that references the registry name
payload = {
    'title': 'Test Action',
    'message': 'Click to run action',
    'level': 'info',
    'actions': [
        {'id': 'snooze', 'label': 'Snooze', 'callback': 'test.snooze'}
    ]
}

notification.notify(payload)

# find the pending notification id
nids = list(notification._PENDING.keys())
print('Pending ids:', nids)
if not nids:
    print('No pending notifications; test failed')
else:
    nid = nids[0]
    print('Executing action...')
    ok = notification.execute_action(nid, 'snooze')
    print('execute_action returned', ok)
    print('RESULT:', RESULT)

# cleanup
notification.unregister_action('test.snooze')
