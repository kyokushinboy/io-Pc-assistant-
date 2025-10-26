import importlib.util, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path = os.path.join(ROOT,'io','notification.py')
spec = importlib.util.spec_from_file_location('local_notification', path)
if spec is None or spec.loader is None:
    raise ImportError(f"Cannot create module spec or loader from {path!r}")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

sound = os.path.join(ROOT, 'assets','sounds','info_modern.wav')
print('Playing', sound)
try:
    import winsound
    winsound.PlaySound(sound, winsound.SND_FILENAME)
    print('Played via winsound')
except Exception as e:
    print('winsound failed:', e)
    try:
        import pygame
        pygame.mixer.init()
        pygame.mixer.music.load(sound)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pass
        print('Played via pygame')
    except Exception as e2:
        print('pygame failed:', e2)
