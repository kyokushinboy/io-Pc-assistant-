import traceback
import difflib
import re
import sys
import io
import logging
from logging.handlers import RotatingFileHandler
import os
import subprocess
from pathlib import Path

# Avoid replacing sys.stdout during pytest collection/run which breaks capture.
try:
    is_pytest = 'pytest' in sys.modules
except Exception:
    is_pytest = False
if not is_pytest:
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except Exception:
        # If wrapping stdout fails (e.g., in some capture contexts), skip it.
        pass
# Logging setup
logs_dir = Path(__file__).resolve().parent.parent / 'logs'
logs_dir.mkdir(parents=True, exist_ok=True)
log_file = logs_dir / 'io.log'
logger = logging.getLogger('io')
logger.setLevel(logging.DEBUG)
if not logger.handlers:
    handler = RotatingFileHandler(str(log_file), maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
# اجرای برنامه ویندوزی با نمایش خطا و دیباگ
def run_exe(path, app_name="برنامه"):
    try:
        logger.debug(f"تلاش برای اجرای: {path}")
        if path.lower().endswith('.exe'):
            subprocess.Popen([path], shell=False)
        elif path.lower().endswith('.lnk'):
            subprocess.Popen(["explorer.exe", path], shell=False)
        else:
            subprocess.Popen([path], shell=False)
        logger.debug(f"اجرای subprocess انجام شد: {path}")
        speak(f"{app_name} اجرا شد.")
        logger.info(f"{app_name} اجرا شد: {path}")
    except Exception as e:
        # Log exception to file but do not vocalize (speak handles suppression for errors)
        logger.exception(f"خطا در اجرای {app_name}: {e}")
# تشخیص احساسات ساده بر اساس کلمات کلیدی
def detect_emotion(text):
    text = text.lower()
    sad_words = ["غمگین", "ناراحت", "افسرده", "دلگیر", "خسته", "بی‌حوصله", "گریه", "اشک"]
    happy_words = ["خوشحال", "شاد", "خنده", "لبخند", "سرحال", "موفق", "عالی"]
    angry_words = ["عصبانی", "خشمگین", "حرص", "داد", "فریاد", "ناراضی"]
    worried_words = ["نگران", "استرس", "اضطراب", "دلواپس"]
    for w in sad_words:
        if w in text:
            return "sad"
    for w in happy_words:
        if w in text:
            return "happy"
    for w in angry_words:
        if w in text:
            return "angry"
    for w in worried_words:
        if w in text:
            return "worried"
    return None

# واکنش به احساس کاربر
def react_to_emotion(emotion):
    if emotion == "sad":
        speak("متاسفم که ناراحت هستید. اگر دوست دارید می‌توانم یک جوک بگویم یا موزیک آرام پخش کنم.")
    elif emotion == "happy":
        speak("خیلی خوشحالم که حالتون خوبه! همیشه شاد باشید.")
    elif emotion == "angry":
        speak("درک می‌کنم که عصبانی هستید. اگر نیاز به آرامش دارید، می‌توانم موزیک آرام پخش کنم یا چند نفس عمیق پیشنهاد کنم.")
    elif emotion == "worried":
        speak("نگرانی طبیعی است. اگر دوست دارید می‌توانم چند جمله انگیزشی یا موزیک آرام پخش کنم.")
from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
import screen_brightness_control as sbc
import pywifi
import time
import typing
def set_volume(level):
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = cast(interface, POINTER(IAudioEndpointVolume))
    # appease static type checkers: treat the COM pointer as Any
    volume = typing.cast(typing.Any, volume)
    # سطح صدا بین 0.0 تا 1.0
    if hasattr(volume, "SetMasterVolumeLevelScalar"):
        volume.SetMasterVolumeLevelScalar(level, None)
    else:
        # تبدیل سطح به دسی‌بل (بین min و max)
        min_vol = volume.GetVolumeRange()[0]
        max_vol = volume.GetVolumeRange()[1]
        db_level = min_vol + (max_vol - min_vol) * float(level)
def change_volume(delta):
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = cast(interface, POINTER(IAudioEndpointVolume))
    # appease static type checkers: treat the COM pointer as Any
    volume = typing.cast(typing.Any, volume)
    current = volume.GetMasterVolumeLevelScalar()
    new_level = min(max(current + delta, 0.0), 1.0)
    try:
        if hasattr(volume, "SetMasterVolumeLevelScalar"):
            volume.SetMasterVolumeLevelScalar(new_level, None)
        else:
            # fallback: convert to dB and set if possible
            min_vol, max_vol = volume.GetVolumeRange()[0], volume.GetVolumeRange()[1]
            db_level = min_vol + (max_vol - min_vol) * float(new_level)
            try:
                volume.SetMasterVolumeLevel(db_level, None)
            except Exception:
                pass
    except Exception:
        # if setting fails, log but don't crash
        logger.exception("Failed to change volume")
def mute_volume(mute=True):
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = cast(interface, POINTER(IAudioEndpointVolume))
    # appease static type checkers: treat the COM pointer as Any
    volume = typing.cast(typing.Any, volume)
    try:
        try:
            volume.SetMute(int(mute), None)
        except AttributeError:
            # Fallback: set volume to 0 if mute, or restore to 1 if unmute
            if mute:
                volume.SetMasterVolumeLevelScalar(0.0, None)
            else:
                volume.SetMasterVolumeLevelScalar(1.0, None)
    except AttributeError:
        # Fallback: set volume to 0 if mute, or restore to 1 if unmute
        if mute:
            volume.SetMasterVolumeLevelScalar(0.0, None)
        else:
            volume.SetMasterVolumeLevelScalar(1.0, None)
        # Fallback: set volume to 0 if mute, or restore to 1 if unmute
        if mute:
            volume.SetMasterVolumeLevelScalar(0.0, None)
        else:
            volume.SetMasterVolumeLevelScalar(1.0, None)

# کنترل نور صفحه
def change_brightness(delta):
    try:
        current = sbc.get_brightness(display=0)[0]
        new_brightness = min(max(current + delta, 0), 100)
        sbc.set_brightness(new_brightness, display=0)
        speak(f"نور صفحه روی {new_brightness} درصد قرار گرفت.")
        logger.debug(f"Brightness set to {new_brightness}")
    except Exception as e:
        speak("خطا در تغییر نور صفحه.")
        logger.exception(f"Brightness error: {e}")

# کنترل وای‌فای
def set_wifi(enable=True):
    try:
        wifi = pywifi.PyWiFi()
        iface = wifi.interfaces()[0]
        if enable:
            # تلاش برای اتصال به اولین پروفایل ذخیره‌شده
            profiles = iface.network_profiles()
            if profiles:
                iface.connect(profiles[0])
                speak("وای‌فای روشن و متصل شد.")
                print("[DEBUG] WiFi connected to profile")
            else:
                speak("هیچ شبکه وای‌فای ذخیره‌شده‌ای یافت نشد.")
                print("[DEBUG] No WiFi profiles found")
        else:
            iface.disconnect()
            speak("وای‌فای قطع شد.")
            print("[DEBUG] WiFi disconnected")
        time.sleep(1)
    except Exception as e:
        speak("خطا در کنترل وای‌فای.")
        print(f"[DEBUG] WiFi error: {e}")
def get_today_events():
    """Return a list of Iranian events for today's Jalali date."""
    import jdatetime
    today = jdatetime.date.today()
    # نمونه مناسبت‌ها (می‌توانید کامل‌تر کنید)
    events = {
        (1, 1): ["جشن نوروز"],
        (1, 12): ["روز جمهوری اسلامی"],
        (1, 13): ["سیزده بدر"],
        (3, 14): ["رحلت امام خمینی"],
        (11, 22): ["پیروزی انقلاب اسلامی"],
        (12, 29): ["روز ملی شدن صنعت نفت"]
        # ... مناسبت‌های بیشتر را اضافه کنید ...
    }
    return events.get((today.month, today.day), [])
import jdatetime

# Removed duplicate speak function and misplaced joke logic
# تابع نمایش shortcutهای دسکتاپ
def list_desktop_shortcuts():
    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    if not os.path.exists(desktop_path):
        speak("پوشه دسکتاپ پیدا نشد.")
        logger.debug(f"Desktop folder not found: {desktop_path}")
        return
    files = os.listdir(desktop_path)
    logger.info("SHORTCUTS ON DESKTOP:")
    for f in files:
        logger.info(f)

import json
import pathlib

# Load APPS and APP_ALIASES from external config if available
config_path = pathlib.Path(__file__).resolve().parent.parent / 'config' / 'apps.json'
try:
    with open(config_path, 'r', encoding='utf-8') as cf:
        cfg = json.load(cf)
        APPS = cfg.get('apps', {})
        APP_ALIASES = cfg.get('aliases', {})
        # Normalize string entries to lists
        for k, v in list(APPS.items()):
            if isinstance(v, str):
                APPS[k] = [v]
except Exception as e:
    print(f"[DEBUG] Failed to load config/apps.json: {e}")
    APPS = {"notepad": [r"C:\\Windows\\System32\\notepad.exe"]}
    APP_ALIASES = {}

# --- Plugin loader ---------------------------------------------------------
import importlib
import pkgutil

PLUGINS = []

def load_plugins():
    plugins_pkg = 'plugins'
    try:
        pkg = importlib.import_module(plugins_pkg)
    except ModuleNotFoundError:
        # When running the script directly (python path/to/io.py), sys.path[0]
        # is the `io/` directory, so Python may not see the project root where
        # `plugins/` lives. Add the project root to sys.path and retry.
        try:
            project_root = Path(__file__).resolve().parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
                logger.debug('Added project root to sys.path for plugin import: %s', project_root)
            pkg = importlib.import_module(plugins_pkg)
        except Exception as e:
            logger.exception('Failed to import plugins package after adding project root: %s', e)
            return
    for finder, name, ispkg in pkgutil.iter_modules(pkg.__path__, prefix=plugins_pkg + '.'):
        try:
            mod = importlib.import_module(name)
            # plugin should expose can_handle() and handle()
            if hasattr(mod, 'can_handle') and hasattr(mod, 'handle'):
                PLUGINS.append(mod)
                logger.debug(f"Loaded plugin: {name}")
        except Exception as e:
            logger.exception(f"Error loading plugin {name}: {e}")

load_plugins()
# لیست سایت‌ها و کلیدواژه‌های مربوطه
SITES = {
    "google": "https://www.google.com",
    "گوگل": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "یوتیوب": "https://www.youtube.com",
    "github": "https://github.com",
    "گیت هاب": "https://github.com",
    "stackoverflow": "https://stackoverflow.com",
    "استک اورفلو": "https://stackoverflow.com",
    "wikipedia": "https://wikipedia.org",
    "ویکی پدیا": "https://wikipedia.org",
    "gmail": "https://mail.google.com",
    "جیمیل": "https://mail.google.com",
    "bing": "https://www.bing.com",
    "بینگ": "https://www.bing.com",
    "yahoo": "https://www.yahoo.com",
    "یاهو": "https://www.yahoo.com",
    "twitter": "https://twitter.com",
    "توییتر": "https://twitter.com",
    "instagram": "https://instagram.com",
    "اینستاگرام": "https://instagram.com",
    "facebook": "https://facebook.com",
    "فیسبوک": "https://facebook.com",
    "linkedin": "https://linkedin.com",
    "لینکدین": "https://linkedin.com",
    "aparat": "https://aparat.com",
    "آپارات": "https://aparat.com",
    "amazon": "https://amazon.com",
    "آمازون": "https://amazon.com",
    "digikala": "https://digikala.com",
    "دیجی کالا": "https://digikala.com"
}
def stop_music():
    if music_state["playing"]:
        pygame.mixer.music.stop()
        music_state["playing"] = False
        speak("Music stopped.")
        print("Music stopped.")
    else:
        speak("No music is playing.")
import pyttsx3
import datetime
import speech_recognition as sr  # Make sure SpeechRecognition is installed: pip install SpeechRecognition
import wikipedia
import webbrowser as wb
import os
import random
# Suppress the pygame support prompt which prints on import
os.environ.setdefault('PYGAME_HIDE_SUPPORT_PROMPT', '1')
import pygame
import pyautogui
import pyjokes
import subprocess

engine = pyttsx3.init()
# دیباگ نوع خروجی voices
voices = engine.getProperty('voices')
logger.debug(f"voices type: {type(voices)}")
# انتخاب صدای فارسی اگر موجود باشد
found_voice = False
try:
    from collections.abc import Iterable
    # Normalize voices into a list safely for static type checkers and non-iterable returns
    if isinstance(voices, Iterable) and not isinstance(voices, (str, bytes)):
        voices_list = list(voices)
    elif voices is None:
        voices_list = []
    else:
        voices_list = [voices]

    for v in voices_list:
        # Safely obtain id and name without assuming attribute types and coerce to strings
        v_id = getattr(v, 'id', None)
        v_name = getattr(v, 'name', '')
        try:
            if isinstance(v_id, bytes):
                id_str = v_id.decode(errors='ignore')
            else:
                id_str = str(v_id) if v_id is not None else ''
        except Exception:
            id_str = str(v_id) if v_id is not None else ''
        name_str = str(v_name).lower() if v_name is not None else ''
        if ('fa' in id_str) or ('persian' in name_str):
            engine.setProperty('voice', id_str)
            found_voice = True
            break

    if not found_voice and voices_list:
        first_id = getattr(voices_list[0], 'id', None)
        try:
            if isinstance(first_id, bytes):
                first_id_str = first_id.decode(errors='ignore')
            else:
                first_id_str = str(first_id) if first_id is not None else ''
        except Exception:
            first_id_str = str(first_id) if first_id is not None else ''
        engine.setProperty('voice', first_id_str)
except Exception:
    pass
engine.setProperty('rate', 150)
engine.setProperty('volume', 1)


# Import NotificationManager robustly: prefer package import, fallback to loading by file path
notify = None
set_speak_callable = None
try:
    from io.notification import notify, set_speak_callable  # type: ignore
except Exception:
    try:
        import importlib.util
        notif_path = Path(__file__).resolve().parent / 'notification.py'
        if notif_path.exists():
            spec = importlib.util.spec_from_file_location('io.notification', str(notif_path))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)  # type: ignore
                # Ensure the module we just loaded is discoverable via regular imports
                try:
                    import sys as _sys
                    _sys.modules['io.notification'] = mod
                except Exception:
                    logger.exception('Failed to register io.notification in sys.modules')
                notify = getattr(mod, 'notify', None)
                set_speak_callable = getattr(mod, 'set_speak_callable', None)
    except Exception:
        logger.exception('Failed to import notification module')


def speak(audio, **voice_opts) -> None:
    # Do not speak or show notifications for error-like messages.
    def is_error_text(text: str) -> bool:
        t = str(text).lower()
        # Persian and English error indicators
        error_indicators = ['خطا', 'خطا در', 'exception', 'traceback', 'error']
        return any(ind in t for ind in error_indicators)

    if is_error_text(audio):
        # Print to terminal for debugging, log, but do not vocalize or notify
        try:
            print(f"[ERROR] {audio}")
        except Exception:
            pass
        logger.error(str(audio))
        return

    # For non-error text: speak and optionally notify (skip certain messages)
    # voice_opts may contain: lang, rate, volume
    # Ensure these are always defined so the finally block can safely reference them.
    old_rate = None
    old_volume = None
    try:
        # apply temporary properties if engine supports them
        if voice_opts:
            try:
                if 'rate' in voice_opts:
                    old_rate = engine.getProperty('rate')
                    rate_val = voice_opts.get('rate')
                    if rate_val is not None:
                        engine.setProperty('rate', int(rate_val))
            except Exception:
                pass
            try:
                if 'volume' in voice_opts:
                    old_volume = engine.getProperty('volume')
                    vol_val = voice_opts.get('volume')
                    if vol_val is not None:
                        engine.setProperty('volume', float(vol_val))
            except Exception:
                pass
        # Decide whether to use online TTS (gTTS) when Persian voice is requested
        did_online = False
        try:
            prefer_online = bool(voice_opts.get('prefer_online', False))
        except Exception:
            prefer_online = False

        # determine requested lang
        try:
            lang = str(voice_opts.get('lang', '')).lower()
        except Exception:
            lang = ''

        use_online = False
        if prefer_online:
            use_online = True
        elif lang.startswith('fa'):
            # check if a persian voice exists locally
            try:
                vs = engine.getProperty('voices')
                from collections.abc import Iterable
                has_fa = False
                if isinstance(vs, Iterable):
                    for v in vs:
                        v_id = getattr(v, 'id', '') or ''
                        v_name = getattr(v, 'name', '') or ''
                        s = f"{v_id} {v_name}".lower()
                        if 'fa' in s or 'farsi' in s or 'persian' in s:
                            has_fa = True
                            break
                if not has_fa:
                    use_online = True
            except Exception:
                use_online = True

        if use_online:
            try:
                from gtts import gTTS
                import tempfile
                import time as _t
                fd, path = tempfile.mkstemp(suffix='.mp3')
                os.close(fd)
                tts = gTTS(text=str(audio), lang=(lang or 'fa'))
                tts.save(path)
                try:
                    if not pygame.mixer.get_init():
                        pygame.mixer.init()
                except Exception:
                    try:
                        pygame.mixer.init()
                    except Exception:
                        logger.exception('Failed to init pygame.mixer for online TTS')
                try:
                    pygame.mixer.music.load(path)
                    pygame.mixer.music.play()
                    # wait until done playing (non-blocking to other threads)
                    while pygame.mixer.music.get_busy():
                        _t.sleep(0.1)
                except Exception:
                    logger.exception('Online TTS playback failed')
                finally:
                    try:
                        os.remove(path)
                    except Exception:
                        pass
                did_online = True
            except Exception:
                logger.exception('Online TTS failed; falling back to local pyttsx3')

        if not did_online:
            engine.say(audio)
            engine.runAndWait()
    finally:
        # restore previous properties
        try:
            if old_rate is not None:
                # ensure rate is an int (pyttsx3 expects a numeric rate)
                try:
                    # If old_rate is already an int use it directly; otherwise try a safe float->int conversion via str()
                    if isinstance(old_rate, int):
                        engine.setProperty('rate', old_rate)
                    else:
                        engine.setProperty('rate', int(float(str(old_rate))))
                except Exception:
                    try:
                        engine.setProperty('rate', int(float(str(old_rate))))
                    except Exception:
                        logger.debug(f"Could not restore rate property from {old_rate}")
            if old_volume is not None:
                # ensure volume is a float between 0.0 and 1.0
                try:
                    # Accept ints/floats directly, otherwise convert via str()
                    if isinstance(old_volume, (int, float)):
                        engine.setProperty('volume', float(old_volume))
                    else:
                        engine.setProperty('volume', float(str(old_volume)))
                except Exception:
                    try:
                        engine.setProperty('volume', float(old_volume) if isinstance(old_volume, (int, float, str)) else 1.0)
                    except Exception:
                        logger.debug(f"Could not restore volume property from {old_volume}")
        except Exception:
            pass
    skip_notify = [
        "متاسفم، متوجه نشدم.",
        "زمان دریافت فرمان به پایان رسید. لطفا دوباره تلاش کنید.",
        # Do not show the polite retry prompt as a desktop notification
        "متاسفم، متوجه نشدم. لطفا دوباره بگویید.",
        "متاسفم، متوجه نشدم، لطفا دوباره بگویید"
    ]
    if str(audio).strip() not in skip_notify:
        # use our NotificationManager to decide channels
        try:
            # notify may be None if the notification module failed to import;
            # ensure it's callable before invoking to avoid "Object of type 'None' cannot be called".
            if callable(notify):
                notify({
                    'title': 'iO',
                    'message': str(audio),
                    'level': 'info',
                    'voice': False,
                    'persistent': False
                })
            else:
                logger.debug('Notification manager not available; skipping notify call.')
        except Exception:
            logger.exception('Failed to send notification via NotificationManager')

# Tell NotificationManager how to call back into speak() for voice notifications
try:
    if callable(set_speak_callable):
        set_speak_callable(speak)
    else:
        logger.debug('set_speak_callable is not available or not callable; skipping setting speak callback.')
except Exception:
    logger.exception('Failed to set speak callable on NotificationManager')

def show_ip():
    import socket
    import requests
    # آیپی داخلی
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
    except Exception:
        local_ip = 'نامشخص'
    # آیپی عمومی
    try:
        public_ip = requests.get('https://api.ipify.org').text
    except Exception:
        public_ip = 'نامشخص'
    ip_text = f"آیپی داخلی: {local_ip}\nآیپی عمومی: {public_ip}"
    speak("آیپی سیستم:")
    speak(f"آیپی داخلی {local_ip} و آیپی عمومی {public_ip}")
    print(ip_text)

def system_status():
    import psutil
    # درصد باتری
    try:
        battery = psutil.sensors_battery()
        battery_percent = battery.percent if battery else 'نامشخص'
    except Exception:
        battery_percent = 'نامشخص'
    # رم
    ram = psutil.virtual_memory()
    ram_total = round(ram.total / (1024**3), 2)
    ram_used = round(ram.used / (1024**3), 2)
    ram_percent = ram.percent
    # CPU
    cpu_percent = psutil.cpu_percent(interval=1)
    cpu_count = psutil.cpu_count(logical=True)
    # هارد
    disk = psutil.disk_usage('/')
    disk_total = round(disk.total / (1024**3), 2)
    disk_used = round(disk.used / (1024**3), 2)
    disk_percent = disk.percent
    status_text = f"درصد باتری: {battery_percent} درصد\nرم: {ram_used} از {ram_total} گیگابایت ({ram_percent}%)\nپردازنده: {cpu_percent}% از {cpu_count} هسته\nهارد: {disk_used} از {disk_total} گیگابایت ({disk_percent}%)"
    speak("وضعیت سیستم:")
    speak(f"باتری {battery_percent} درصد، رم {ram_percent} درصد، پردازنده {cpu_percent} درصد، هارد {disk_percent} درصد.")
    print(status_text)

def tell_joke_fa():
    # جوک فارسی از لیست
    jokes = [
        "یه روز یه مورچه می‌ره رستوران، گارسون می‌گه چی میل دارید؟ مورچه می‌گه یه قاشق غذا و یه قطره آب!",
        "یه روز یه پشه می‌ره دکتر، دکتر می‌گه چی شده؟ پشه می‌گه خوابم نمی‌بره، دکتر می‌گه برو رو دیوار بشین!",
        "یه روز یه لاک‌پشت می‌ره مسابقه دو، همه می‌خندن! لاک‌پشت می‌گه صبر کنید، تازه گرم کردم!",
        "یه روز یه گوسفند می‌ره بانک، می‌گه حساب علفی باز کنید!"
    ]
    import random
    joke = random.choice(jokes)
    speak(joke)
    print(joke)


def tell_time() -> None:
    """Tells the current time."""
    current_time = datetime.datetime.now().strftime("%H:%M:%S")
    speak("ساعت فعلی:")
    speak(current_time)
    print("ساعت فعلی:", current_time)


def date() -> None:
    """Tells the current date in both Gregorian and Jalali (Shamsi)."""
    now = datetime.datetime.now()
    # تاریخ میلادی
    miladi_str = f"{now.day} {now.strftime('%B')} {now.year}"
    # تاریخ شمسی
    shamsi = jdatetime.date.fromgregorian(date=now.date())
    shamsi_str = f"{shamsi.day} {shamsi.strftime('%B')} {shamsi.year}"
    speak("تاریخ امروز:")
    speak(f"میلادی: {miladi_str}")
    speak(f"شمسی: {shamsi_str}")
    print(f"تاریخ امروز (میلادی): {miladi_str}")
    print(f"تاریخ امروز (شمسی): {shamsi_str}")


def wishme() -> None:
    """Greets the user based on the time of day."""
    hour = datetime.datetime.now().hour
    if 4 <= hour < 12:
        speak("سلام، صبح بخیر!")
        print("سلام، صبح بخیر!")
    elif 12 <= hour < 16:
        speak("سلام، ظهر بخیر!")
        print("سلام، ظهر بخیر!")
    elif 16 <= hour < 24:
        speak("سلام، عصر بخیر!")
        print("سلام، عصر بخیر!")
    else:
        speak("شب بخیر، فردا می‌بینمتون.")
    assistant_name = load_name()
    speak(f"{assistant_name} در خدمت شماست. لطفا بفرمایید چه کمکی می‌توانم بکنم؟")
    print(f"{assistant_name} در خدمت شماست. لطفا بفرمایید چه کمکی می‌توانم بکنم؟")


def screenshot() -> None:
    """Takes a screenshot and saves it."""
    img = pyautogui.screenshot()
    img_path = os.path.expanduser("~\\Pictures\\screenshot.png")
    # Ensure the directory exists
    os.makedirs(os.path.dirname(img_path), exist_ok=True)
    img.save(img_path)
    speak(f"عکس صفحه ذخیره شد در {img_path}.")
    print(f"عکس صفحه ذخیره شد در {img_path}.")

def takecommand() -> str:
    """Takes microphone input from the user and returns it as text."""
    # Improved recognizer settings with retries and microphone selection.
    r = sr.Recognizer()
    # Keep dynamic energy to adapt to environment; tune pause threshold for natural speech
    r.dynamic_energy_threshold = True
    r.pause_threshold = 0.8

    # Timeouts and limits
    listen_timeout = 7
    phrase_time_limit = 10
    ambient_duration = 1.5
    retries = 2

    # Try to pick a reasonable microphone index (avoid loopback/stereo-mix if possible)
    mic_index = None
    try:
        mic_names = sr.Microphone.list_microphone_names()
        for i, name in enumerate(mic_names):
            n = (name or '').lower()
            if 'loopback' in n or 'stereo mix' in n:
                continue
            if 'microphone' in n or 'mic' in n or len(mic_names) == 1:
                mic_index = i
                break
    except Exception:
        mic_index = None

    for attempt in range(retries):
        try:
            with sr.Microphone(device_index=mic_index) as source:
                print("Listening...")
                # Calibrate to ambient noise; a slightly longer duration helps in noisy envs
                try:
                    # adjust_for_ambient_noise type stubs may require an int; cast to int to satisfy static checkers
                    r.adjust_for_ambient_noise(source, duration=int(ambient_duration))
                except Exception:
                    pass
                try:
                    audio = r.listen(source, timeout=listen_timeout, phrase_time_limit=phrase_time_limit)
                except sr.WaitTimeoutError:
                    speak("زمان دریافت فرمان به پایان رسید. لطفا دوباره تلاش کنید.")
                    # return empty string to indicate no command (consistent with `if not query` checks)
                    return ""

            try:
                print("در حال تشخیص...")
                query = typing.cast(typing.Any, r).recognize_google(audio, language="fa-IR")
                print(query)
                return query.lower()
            except sr.UnknownValueError:
                # If recognition failed, give a polite prompt and retry a limited number of times
                if attempt < retries - 1:
                    speak("متاسفم، متوجه نشدم. لطفا دوباره بگویید.")
                    continue
                speak("متاسفم، متوجه نشدم.")
                return ""
            except sr.RequestError:
                speak("سرویس تشخیص گفتار در دسترس نیست.")
                return ""
            except Exception as e:
                speak(f"خطا رخ داد: {e}")
                print(f"خطا: {e}")
                return ""
        except Exception as e:
            # Opening the microphone failed; report and abort
            logger.exception('Microphone handling failed: %s', e)
            speak("خطا در دسترسی به میکروفون. لطفا تنظیمات سخت‌افزاری را بررسی کنید.")
            return ""
    # If loop completes without returning, return empty string to satisfy -> str annotation
    return ""

music_state = {
    "songs": [],
    "current": 0,
    "playing": False
}

def init_music():
    song_dir = os.path.expanduser("~\\Music")
    logger.debug(f"مسیر موزیک: {song_dir}")
    if not os.path.exists(song_dir):
        logger.debug("پوشه موزیک وجود ندارد!")
        music_state["songs"] = []
        return song_dir
    songs = [f for f in os.listdir(song_dir) if f.lower().endswith((".mp3", ".wav", ".ogg"))]
    logger.debug(f"لیست آهنگ‌ها: {songs}")
    music_state["songs"] = songs
    music_state["current"] = 0
    try:
        pygame.mixer.init()
    except Exception as e:
        logger.exception(f"خطا در init میکسر: {e}")
    return song_dir

def play_music(song_name=None):
    """Play music, optionally by name."""
    song_dir = os.path.expanduser("~\\Music")
    logger.debug(f"اجرای play_music با song_name: {song_name}")
    if not music_state["songs"]:
        logger.debug("music_state['songs'] خالی است، فراخوانی init_music...")
        init_music()
    songs = music_state["songs"]
    logger.debug(f"songs: {songs}")
    if song_name:
        matches = [i for i, song in enumerate(songs) if song_name.lower() in song.lower()]
        logger.debug(f"matches: {matches}")
        if matches:
            music_state["current"] = matches[0]
        else:
            speak("آهنگی با این نام پیدا نشد.")
            logger.debug("آهنگ با این نام پیدا نشد.")
            return
    if songs:
        song_path = os.path.join(song_dir, songs[music_state["current"]])
        logger.debug(f"song_path: {song_path}")
        try:
            pygame.mixer.music.load(song_path)
            pygame.mixer.music.play()
            music_state["playing"] = True
            speak(f"در حال پخش {songs[music_state['current']]}")
            logger.info(f"در حال پخش {songs[music_state['current']]}" )
        except Exception as e:
            logger.exception(f"خطا در پخش آهنگ: {e}")
            speak("خطا در پخش آهنگ.")
    else:
        logger.debug("هیچ آهنگی پیدا نشد!")
        speak("هیچ آهنگی پیدا نشد.")

def pause_music():
    if music_state["playing"]:
        pygame.mixer.music.pause()
        music_state["playing"] = False
        speak("موزیک متوقف شد.")
        logger.info("موزیک متوقف شد.")
    else:
        speak("موزیکی در حال پخش نیست.")

def resume_music():
    if not music_state["playing"]:
        pygame.mixer.music.unpause()
        music_state["playing"] = True
        speak("موزیک ادامه یافت.")
        logger.info("موزیک ادامه یافت.")
    else:
        speak("موزیک در حال پخش است.")

def next_music():
    if music_state["songs"]:
        pygame.mixer.music.stop()
        music_state["current"] = (music_state["current"] + 1) % len(music_state["songs"])
        play_music()
    else:
        speak("آهنگی موجود نیست.")

def previous_music():
    if music_state["songs"]:
        pygame.mixer.music.stop()
        music_state["current"] = (music_state["current"] - 1) % len(music_state["songs"])
        play_music()
    else:
        speak("آهنگی موجود نیست.")

def set_name() -> None:
    """Sets a new name for the assistant."""
    speak("چه اسمی برای من انتخاب می‌کنید؟")
    name = takecommand()
    if name:
        with open("assistant_name.txt", "w") as file:
            file.write(name)
        speak(f"از این به بعد اسم من {name} است.")
    else:
        speak("متاسفم، متوجه نشدم.")

def load_name() -> str:
    """Loads the assistant's name from a file, or uses a default name."""
    try:
        with open("assistant_name.txt", "r") as file:
            return file.read().strip()
    except FileNotFoundError:
                return "iO"  # نام پیش‌فرض


def search_wikipedia(query):
    """Searches Wikipedia and returns a summary."""
    try:
        speak("در حال جستجو در ویکی‌پدیا ...")
        result = wikipedia.summary(query, sentences=2)
        speak(result)
        print(result)
    except wikipedia.exceptions.DisambiguationError:
        speak("نتایج زیادی یافت شد، لطفا دقیق‌تر بپرسید.")
    except Exception:
        speak("چیزی در ویکی‌پدیا پیدا نشد.")


if __name__ == "__main__":
        # کنترل سخت‌افزار
    import sys
    if sys.platform == "win32":
        import os
        import subprocess
        try:
            # Try to change the console code page to UTF-8 if the chcp command is available
            subprocess.run(["chcp", "65001"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            # If chcp isn't available, try to reconfigure Python stdout to UTF-8 (Python 3.7+)
            try:
                # Some static analyzers don't know TextIO has reconfigure; use getattr or a safe fallback.
                reconfig = getattr(sys.stdout, "reconfigure", None)
                if callable(reconfig):
                    reconfig(encoding='utf-8')
                else:
                    # Fallback: replace stdout with a TextIOWrapper if possible (preserves buffer if present)
                    try:
                        import io as _io
                        if hasattr(sys.stdout, "buffer"):
                            sys.stdout = _io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
                    except Exception:
                        pass
            except Exception:
                pass
    wishme()

    query = ""
    while True:
        # دیباگ مقدار فرمان صوتی
        print(f"[DEBUG] query: {query}")
        if "list shortcuts" in query or "show shortcuts" in query or "لیست شورتکات" in query:
            list_desktop_shortcuts()
            speak("Desktop shortcuts listed in terminal.")
            continue
        query = takecommand()
        if not query:
            continue

        # تشخیص احساسات و واکنش
        emotion = detect_emotion(query)
        if emotion:
            react_to_emotion(emotion)
            # ادامه اجرای دستیار بعد از واکنش

        # Plugin dispatch: give plugins first chance to handle the query.
        try:
            plugin_handled = False
            for mod in PLUGINS:
                try:
                    if hasattr(mod, 'can_handle') and mod.can_handle(query):
                        try:
                            result = mod.handle(query)
                            # Treat True, None, or dict with handled=True as handled
                            if result is True or result is None or (isinstance(result, dict) and result.get('handled')):
                                plugin_handled = True
                            else:
                                # If plugin returns a truthy value treat as handled
                                plugin_handled = bool(result)
                        except Exception as pe:
                            logger.exception(f"Plugin {getattr(mod, '__name__', str(mod))} error in handle: {pe}")
                        if plugin_handled:
                            logger.debug(f"Query handled by plugin {getattr(mod, '__name__', str(mod))}")
                            break
                except Exception:
                    logger.exception(f"Plugin {getattr(mod, '__name__', str(mod))} error in can_handle")
            if plugin_handled:
                # Skip built-in handlers when a plugin handled the query
                continue
        except Exception:
            logger.exception("Error during plugin dispatch")

        # Synonyms map for common commands (used by keyword_in_query)
        SYNONYMS = {
            'volume_down': ['کم کن صدا', 'کاهش صدا', 'volume down', 'صدای کمتر', 'کمش کن'],
            'volume_up': ['زیاد کن صدا', 'افزایش صدا', 'volume up', 'صدای بیشتر', 'زیادش کن'],
            'volume_small_up': ['صدا زیاد', 'یکم زیاد کن صدا', '۵ درصد زیاد'],
            'volume_small_down': ['صدا کم', 'یکم کم کن صدا', '۵ درصد کم'],
            'mute': ['قطع صدا', 'mute', 'بی‌صدا', 'قطع کن صدا'],
            'unmute': ['وصل صدا', 'unmute', 'صدا وصل'],
            'brightness_down': ['کم کن نور', 'کاهش نور', 'brightness down', 'نور کم کن'],
            'brightness_up': ['زیاد کن نور', 'افزایش نور', 'brightness up', 'نور زیاد کن'],
            'wifi_on': ['وای فای روشن', 'wifi on', 'وایفای روشن', 'اتصال وای فای'],
            'wifi_off': ['وای فای خاموش', 'wifi off', 'قطع وای فای', 'وایفای خاموش'],
            'play_music': ['پخش موزیک', 'پخش آهنگ', 'play music', 'پخش کن موزیک'],
            'pause_music': ['توقف موزیک', 'توقف آهنگ', 'pause music', 'توقف'],
            'resume_music': ['ادامه موزیک', 'ادامه آهنگ', 'resume music', 'دوباره پخش کن'],
            'next': ['بعدی', 'بعدی آهنگ', 'next'],
            'previous': ['قبلی', 'آهنگ قبلی', 'previous'],
            'stop_music': ['قطع موزیک', 'قطع آهنگ', 'stop music']
        }

        def keyword_in_query(q: str, keys, fuzzy_thresh: float = 0.78) -> bool:
            """Return True if any keyword or its synonym appears in q.

            keys may be a single string or an iterable of strings.
            Uses exact word-boundary match and a lightweight fuzzy compare on words.
            """
            if not q:
                return False
            qq = q.lower()
            if isinstance(keys, str):
                keys = [keys]
            for key in keys:
                # if key maps to synonyms list in SYNONYMS, expand
                candidates = []
                if isinstance(key, str) and key in SYNONYMS:
                    candidates = SYNONYMS[key]
                elif isinstance(key, (list, tuple)):
                    candidates = list(key)
                else:
                    candidates = [str(key)]

                for cand in candidates:
                    c = cand.lower()
                    # word-boundary regex
                    try:
                        if re.search(r'\b' + re.escape(c) + r'\b', qq):
                            return True
                    except re.error:
                        # fallback to substring if regex fails on unicode
                        if c in qq:
                            return True
                    if c in qq:
                        return True
                    # fuzzy compare by words (unicode-aware)
                    words = re.findall(r"\w+", qq, flags=re.UNICODE)
                    for w in words:
                        if difflib.SequenceMatcher(None, w, c).ratio() >= fuzzy_thresh:
                            return True
            return False

        # کنترل سخت‌افزار با پشتیبانی از هم‌معنی‌ها
        if keyword_in_query(query, 'volume_down'):
            change_volume(-0.1)
            speak("صدا کم شد.")
            continue
        if keyword_in_query(query, 'volume_up'):
            change_volume(0.1)
            speak("صدا زیاد شد.")
            continue
        if keyword_in_query(query, 'volume_small_up'):
            change_volume(0.05)
            speak("صدا ۵ درصد زیاد شد.")
            continue
        if keyword_in_query(query, 'volume_small_down'):
            change_volume(-0.05)
            speak("صدا ۵ درصد کم شد.")
            continue
        if keyword_in_query(query, 'mute'):
            mute_volume(True)
            speak("صدا قطع شد.")
            continue
        if keyword_in_query(query, 'unmute'):
            mute_volume(False)
            speak("صدا وصل شد.")
            continue
        if keyword_in_query(query, 'brightness_down'):
            change_brightness(-10)
            continue
        if keyword_in_query(query, 'brightness_up'):
            change_brightness(10)
            continue
        if keyword_in_query(query, 'wifi_on'):
            set_wifi(True)
            continue
        if keyword_in_query(query, 'wifi_off'):
            set_wifi(False)
            continue

        if "ساعت" in query:
            tell_time()

        elif "تاریخ" in query:
            date()

        elif "وضعیت" in query:
            system_status()

        elif "آیپی" in query or "آی پی" in query or "ip" in query:
            show_ip()

        elif "ویکی پدیا" in query:
            query = query.replace("ویکی پدیا", "").strip()
            search_wikipedia(query)

        elif keyword_in_query(query, 'play_music'):
            # extract song name by removing known verbs
            song_name = query
            for v in SYNONYMS.get('play_music', []):
                song_name = song_name.replace(v, '')
            song_name = song_name.replace('پخش', '').replace('موزیک', '').replace('آهنگ', '').strip()
            play_music(song_name)

        elif "توقف موزیک" in query or "توقف آهنگ" in query or query.strip() == "توقف":
            pause_music()

        elif "ادامه موزیک" in query or "ادامه آهنگ" in query or "دوباره پخش کن" in query:
            resume_music()

        elif "بعدی" in query:
            next_music()

        elif "قبلی" in query:
            previous_music()

        elif "قطع موزیک" in query or "قطع آهنگ" in query:
            stop_music()

        elif "مناسبت" in query:
            today_events = get_today_events()
            if today_events:
                speak("مناسبت‌های امروز:")
                for event in today_events:
                    speak(event)
                    print(event)
            else:
                speak("امروز مناسبت خاصی ثبت نشده است.")
                print("امروز مناسبت خاصی ثبت نشده است.")
        # باز کردن نرم‌افزارها فقط با گفتن نام برنامه (پشتیبانی از معادل‌های فارسی)
        elif any(app in query for app in APPS) or any(alias in query for alias in APP_ALIASES):
            # پیدا کردن کلید canonical از روی query با بررسی کلیدهای APPS و معادل‌ها
            found_key = None
            for app_key in APPS.keys():
                if app_key in query:
                    found_key = app_key
                    break
            if not found_key:
                for alias, canonical in APP_ALIASES.items():
                    if alias in query:
                        found_key = canonical
                        break

            if found_key:
                username = os.getlogin()
                candidates = APPS.get(found_key, [])
                desktop = os.path.join(os.path.expanduser("~"), "Desktop")
                found = False
                for candidate in candidates:
                    candidate_path = candidate.replace("{username}", username)
                    # Check .lnk explicitly and also the path itself
                    print(f"[DEBUG] بررسی نامزد: {candidate_path}")
                    if os.path.exists(candidate_path):
                        print(f"[DEBUG] پیدا شد: {candidate_path}")
                        # Prefer os.startfile on Windows for better integration
                        try:
                            if sys.platform == 'win32':
                                try:
                                    os.startfile(candidate_path)
                                except OSError as oe:
                                    # Common case: WinError 1223 (operation canceled by user) or other OS-level cancels
                                    print(f"[DEBUG] os.startfile failed with OSError: {oe}")
                                    # Fallback: use cmd start which uses the shell
                                    try:
                                        subprocess.Popen(["cmd", "/c", "start", "", f'"{candidate_path}"'], shell=False)
                                    except Exception as e2:
                                        print(f"[DEBUG] fallback start failed: {e2}")
                                        raise
                            else:
                                subprocess.Popen([candidate_path], shell=False)
                            speak(f"{found_key} اجرا شد.")
                        except Exception as e:
                            print(f"[DEBUG] خطا در اجرای {candidate_path}: {e}")
                            traceback.print_exc()
                            speak(f"خطا در اجرای {found_key}: {e}")
                        found = True
                        break
                    # try candidate + .lnk if not found and no extension provided
                    if not os.path.splitext(candidate_path)[1] and os.path.exists(candidate_path + ".lnk"):
                        lnk = candidate_path + ".lnk"
                        try:
                            print(f"[DEBUG] پیدا شد: {lnk}")
                            if sys.platform == 'win32':
                                os.startfile(lnk)
                            else:
                                subprocess.Popen([lnk], shell=False)
                            speak(f"{found_key} اجرا شد.")
                        except Exception as e:
                            print(f"[DEBUG] خطا در اجرای {lnk}: {e}")
                            traceback.print_exc()
                            speak(f"خطا در اجرای {found_key}: {e}")
                        found = True
                        break
                if not found:
                    speak(f"{found_key} نصب نیست یا مسیر اشتباه است.")
                    print(f"[DEBUG] {found_key} هیچ یک از مسیرهای پیشنهادی پیدا نشد: {candidates}")

        # باز کردن سایت‌ها فقط با گفتن نام سایت (تطابق دقیق)
        elif query.strip() in SITES:
            url = SITES[query.strip()]
            wb.open(url)
            speak(f"سایت {query.strip()} باز شد.")
            print(f"سایت {query.strip()} باز شد: {url}")

        elif "تغییر نام" in query:
            set_name()

        elif "اسکرین شات" in query:
            screenshot()
            speak("اسکرین‌شات گرفته شد، لطفا بررسی کنید.")

        elif "جوک" in query:
            tell_joke_fa()

        elif "خاموش" in query:
            speak("سیستم خاموش می‌شود، خداحافظ!")
            os.system("C:\\Windows\\System32\\shutdown.exe /s /f /t 1")
            break

        elif "ریستارت" in query:
            speak("سیستم ریستارت می‌شود، لطفا صبر کنید!")
            os.system("shutdown /r /f /t 1")
            break

        elif "خروج" in query or "آفلاین" in query:
            speak("دستیار آفلاین شد. روز خوبی داشته باشید!")
            break
