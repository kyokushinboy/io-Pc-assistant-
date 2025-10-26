"""Minimal local HTTP UI to view and trigger actionable notifications stored in notification manager.

Usage: run this module (python -m io.notification_server) and visit http://localhost:5001
It is intentionally minimal and not started automatically by the assistant.
"""
from __future__ import annotations
import logging
from pathlib import Path

try:
    from flask import Flask, render_template_string, redirect, url_for
except Exception:
    Flask = None
    render_template_string = None
    redirect = None
    url_for = None

_logger = logging.getLogger('io.notification_server')

TEMPLATE = """
<html>
<head><meta charset='utf-8'><title>iO Notifications</title></head>
<body>
<h1>Pending Notifications</h1>
{% if pending %}
  <ul>
  {% for nid, n in pending.items() %}
    <li><strong>{{n.title}}</strong>: {{n.message}}
      <ul>
      {% for a in n.actions %}
        <li><a href="/action/{{nid}}/{{a.id}}">{{a.label}}</a></li>
      {% endfor %}
      </ul>
    </li>
  {% endfor %}
  </ul>
{% else %}
  <p>No pending notifications.</p>
{% endif %}
</body>
</html>
"""


def run_server(host='127.0.0.1', port=5001):
    if Flask is None:
        _logger.error('Flask not installed. Install flask to use notification_server: pip install flask')
        return
    # ensure type checkers know Flask helpers are available when Flask is present
    assert render_template_string is not None, "Flask import succeeded but render_template_string is not available"
    assert redirect is not None, "Flask import succeeded but redirect is not available"
    assert url_for is not None, "Flask import succeeded but url_for is not available"
    # local aliases so static type checkers treat them as callables
    render_template = render_template_string
    redirect_fn = redirect
    url_for_fn = url_for
    app = Flask('io.notification_server')
    # import notification module here to avoid circular imports at package import time
    import importlib
    try:
        notif = importlib.import_module('io.notification')
    except Exception:
        # fallback to relative import when running inside the package
        from . import notification as notif  # type: ignore

    @app.route('/action/<nid>/<action_id>')
    def action(nid, action_id):
        # delegate to notification.execute_action which handles registry lookup and removal
        try:
            executed = False
            if hasattr(notif, 'execute_action'):
                executed = notif.execute_action(nid, action_id)
            if not executed:
                _logger.debug('Action %s for notification %s not executed', action_id, nid)
        except Exception:
            _logger.exception('Error executing action %s for notification %s via server', action_id, nid)
        return redirect_fn(url_for_fn('index'))

    app.run(host=host, port=port)


if __name__ == '__main__':
    run_server()
