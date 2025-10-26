"""NotificationManager: centralizes notifications for desktop, voice and logging.

Simple MVP implementation:
- loads config from ../config/notifications.json
- notify(payload) will: check quiet hours, log, optionally show desktop notification (plyer) and optionally call speak callback
- supports setting speak callback via set_speak_callable(fn)

Payload example:
{
  'title': 'عنوان',
  'message': 'متن اعلان',
  'level': 'info|warning|error|reminder',
  'actions': [{'id': 'snooze', 'label': 'بعداً'}],
  'persistent': False,
  'voice': False
}
"""
from __future__ import annotations
import json
import logging
from pathlib import Path
from datetime import datetime, time
from typing import Optional, Callable
import threading
import uuid
import queue
import platform

try:
    if platform.system() == 'Windows':
        import winsound
    else:
        winsound = None
except Exception:
    winsound = None

try:
    from plyer import notification as plyer_notify
except Exception:
    plyer_notify = None

CONFIG_PATH = Path(__file__).resolve().parent.parent / 'config' / 'notifications.json'

_logger = logging.getLogger('io.notifications')
_speak_callable: Optional[Callable[..., None]] = None
_config = {
    'desktop': True,
    'voice': False,
    'voice_queue': True,
    'quiet_hours': {'start': '22:00', 'end': '07:00'},
    'group_window_seconds': 300,
    'levels': {'info': True, 'warning': True, 'error': True, 'reminder': True},
    'allow_remote': False
}

# Messages that should never produce a visible/sound notification
_SUPPRESSED_MESSAGES = {
    'متاسفم، متوجه نشدم.',
    'زمان دریافت فرمان به پایان رسید. لطفا دوباره تلاش کنید.',
    'متاسفم، متوجه نشدم. لطفا دوباره بگویید.',
    'متاسفم، متوجه نشدم، لطفا دوباره بگویید'
}


# Error indicators (kept similar to io.io.is_error_text)
_ERROR_INDICATORS = ['خطا', 'خطا در', 'exception', 'traceback', 'error']


def _is_error_text(text: str) -> bool:
    try:
        t = str(text).lower()
        for ind in _ERROR_INDICATORS:
            if ind in t:
                return True
    except Exception:
        pass
    return False

# pending actionable notifications: id -> payload
_PENDING: dict = {}

# action registry: optional global callbacks that can be referenced by name from actions
# mapping: name -> callable
_ACTION_REGISTRY: dict = {}

# TTS queue and worker
_tts_queue: 'queue.Queue[tuple[str, Optional[dict]]]' = queue.Queue()
_tts_worker_thread: threading.Thread | None = None

def _tts_worker() -> None:
    """Worker thread that consumes TTS queue and calls the speak callable serially."""
    while True:
        try:
            msg, opts = _tts_queue.get()
        except Exception:
            continue
        try:
            if _speak_callable:
                try:
                    _speak_callable(msg, **(opts or {}))
                except TypeError:
                    _speak_callable(msg)
            else:
                _logger.debug('No speak callable registered; dropping TTS message')
        except Exception:
            _logger.exception('Error in TTS worker while speaking')
        finally:
            try:
                _tts_queue.task_done()
            except Exception:
                pass

def _ensure_tts_worker_started():
    global _tts_worker_thread
    if _tts_worker_thread is None:
        t = threading.Thread(target=_tts_worker, daemon=True)
        t.start()
        _tts_worker_thread = t



def load_config():
    global _config
    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                # merge defaults
                _config.update(cfg)
                _logger.debug('Notifications config loaded: %s', _config)
    except Exception as e:
        _logger.exception('Failed to load notifications config: %s', e)


def set_speak_callable(fn: Callable[[str], None]):
    global _speak_callable
    _speak_callable = fn


def _normalize_voice(voice_cfg):
    """Normalize voice payload which may be bool or dict.

    Returns a dict of voice options or None.
    """
    if not voice_cfg:
        return None
    if isinstance(voice_cfg, bool):
        return _config.get('voice_options') if voice_cfg else None
    if isinstance(voice_cfg, dict):
        # merge with defaults
        defaults = _config.get('voice_options', {}) or {}
        result = defaults.copy()
        result.update(voice_cfg)
        return result
    return None


def _in_quiet_hours() -> bool:
    try:
        q = _config.get('quiet_hours', {})
        start = q.get('start')
        end = q.get('end')
        if not start or not end:
            return False
        fmt = '%H:%M'
        now = datetime.now().time()
        start_t = datetime.strptime(start, fmt).time()
        end_t = datetime.strptime(end, fmt).time()
        if start_t < end_t:
            return start_t <= now <= end_t
        else:
            # overnight (e.g., 22:00-07:00)
            return now >= start_t or now <= end_t
    except Exception:
        return False


def notify(payload: dict) -> None:
    """Show or log a notification based on payload and config."""
    try:
        load_config()
        title = payload.get('title', 'iO')
        message = payload.get('message', '')
        level = payload.get('level', 'info')
        voice = payload.get('voice', False)
        persistent = payload.get('persistent', False)

        # always log
        _logger.info('Notification (%s): %s - %s', level, title, message)

        # If the message is in suppressed set, do not show desktop/sound/voice
        if str(message).strip() in _SUPPRESSED_MESSAGES:
            _logger.debug('Message suppressed from visible notification: %s', message)
            return

        # If the message appears to be an error, do not show or speak it (only log)
        if _is_error_text(message):
            _logger.debug('Error-like message suppressed from visible notification: %s', message)
            return

        # respect level setting
        levels_cfg = _config.get('levels', {})
        if not levels_cfg.get(level, True):
            _logger.debug('Notification level %s disabled in config', level)
            return

        # quiet hours
        if _in_quiet_hours() and not payload.get('bypass_quiet', False):
            _logger.debug('In quiet hours, skipping desktop/voice for notification: %s', title)
            # still logged
            return

        # desktop
        if _config.get('desktop', True) and plyer_notify is not None:
            notify_fn = getattr(plyer_notify, 'notify', None)
            if callable(notify_fn):
                try:
                    notify_fn(title=title, message=message, app_name='iO')
                except Exception:
                    _logger.exception('Desktop notification failed')
            else:
                _logger.debug('Plyer notify function not available; skipping desktop notification')

        # play sound file if configured or provided
        try:
            sounds_cfg = _config.get('sounds', {}) or {}
            pack = _config.get('sound_pack')
            pack_path = None
            if pack:
                candidate = Path(__file__).resolve().parent.parent / 'assets' / 'sounds' / 'packs' / str(pack) / f"{level}.wav"
                if candidate.exists():
                    pack_path = str(candidate)

            sound_file = payload.get('sound_file') or pack_path or sounds_cfg.get(level)
            play_sound_flag = payload.get('play_sound', True) if sound_file else False
            if play_sound_flag and sound_file:
                # non-blocking play
                try:
                    _play_sound_async(sound_file)
                except Exception:
                    _logger.exception('Failed to play notification sound')
        except Exception:
            _logger.exception('Error while handling notification sound')

        # store actionable notification if actions provided
        actions = payload.get('actions')
        if actions:
            nid = str(uuid.uuid4())
            # actions are list of dicts: {id, label, callback? (callable or registry name)}
            _PENDING[nid] = {'title': title, 'message': message, 'actions': actions, 'payload': payload}
            _logger.debug('Stored actionable notification %s', nid)

        # voice (support bool or dict).
        # Per-payload 'voice': True should request speaking even if global config 'voice' is False.
        voice_opts = _normalize_voice(voice)
        # Determine if we should speak: if voice_opts present and either global voice enabled,
        # or payload.force_voice True, or payload explicitly set voice True.
        should_voice = False
        try:
            if voice_opts:
                if _config.get('voice', False) or payload.get('force_voice', False) or (voice is True):
                    should_voice = True
        except Exception:
            should_voice = False
        if should_voice:
            _logger.debug('Voice requested for notification %s (opts=%s)', title, voice_opts)
        if should_voice:
            try:
                # if queueing is enabled, enqueue; otherwise spawn a background speak
                if _config.get('voice_queue', True):
                    _ensure_tts_worker_started()
                    _tts_queue.put((message, voice_opts))
                else:
                    # fallback: start a background thread for immediate speak
                    def _do_speak(msg, opts):
                        try:
                            if _speak_callable:
                                try:
                                    _speak_callable(msg, **(opts or {}))
                                except TypeError:
                                    _speak_callable(msg)
                            else:
                                _logger.debug('No speak callable registered; dropping immediate TTS')
                        except Exception:
                            _logger.exception('Voice notification failed')

                    t = threading.Thread(target=_do_speak, args=(message, voice_opts), daemon=True)
                    t.start()
            except Exception:
                _logger.exception('Voice notification handling failed')
        else:
            if voice_opts:
                # voice requested but not enabled by config or flags; log debug info
                _logger.debug('Voice options provided but speaking not enabled for notification %s', title)

    except Exception:
        _logger.exception('Notification dispatch failed')


# initialize config at import
load_config()


def _play_sound_async(path: str) -> None:
    """Play a sound file asynchronously. Windows-only (winsound)."""
    def _play(p: str):
        try:
            if winsound is not None:
                # SND_FILENAME: p is filename. SND_ASYNC plays asynchronously.
                winsound.PlaySound(p, winsound.SND_FILENAME | winsound.SND_ASYNC)
            else:
                _logger.debug('winsound not available; cannot play sound: %s', p)
        except Exception:
            _logger.exception('Exception in sound playback for %s', p)

    t = threading.Thread(target=_play, args=(path,), daemon=True)
    t.start()


def register_action(name: str, cb: Callable) -> None:
    """Register a global action callback available to notifications via name."""
    try:
        if not callable(cb):
            raise TypeError('callback must be callable')
        _ACTION_REGISTRY[name] = cb
        _logger.debug('Registered action %s', name)
    except Exception:
        _logger.exception('Failed to register action %s', name)


def unregister_action(name: str) -> None:
    try:
        _ACTION_REGISTRY.pop(name, None)
        _logger.debug('Unregistered action %s', name)
    except Exception:
        _logger.exception('Failed to unregister action %s', name)


def execute_action(nid: str, action_id: str) -> bool:
    """Execute an action for a pending notification.

    Looks up the notification by nid, finds the action with action_id, and then:
    - if action['callback'] is callable, call it
    - if action['callback'] is a string, look up in _ACTION_REGISTRY and call

    Returns True if an action was found and executed (or scheduled), False otherwise.
    """
    try:
        item = _PENDING.get(nid)
        if not item:
            _logger.debug('No pending notification %s', nid)
            return False
        for a in item.get('actions', []):
            if a.get('id') == action_id:
                cb = a.get('callback')
                try:
                    if callable(cb):
                        cb()
                    elif isinstance(cb, str):
                        reg = _ACTION_REGISTRY.get(cb)
                        if callable(reg):
                            reg()
                        else:
                            _logger.info('Action registry entry not callable or missing for %s', cb)
                    else:
                        _logger.info('Non-callable action callback for %s: %r', action_id, cb)
                except Exception:
                    _logger.exception('Error executing callback %s for notification %s', action_id, nid)
                # remove pending after action
                _PENDING.pop(nid, None)
                return True
        _logger.debug('Action id %s not found in notification %s', action_id, nid)
        return False
    except Exception:
        _logger.exception('execute_action failed for %s / %s', nid, action_id)
        return False
