import importlib.util, os, time, json
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# ensure packs exist
packs_dir = os.path.join(ROOT,'assets','sounds','packs')
packs = [d for d in os.listdir(packs_dir) if os.path.isdir(os.path.join(packs_dir,d))]
print('Found packs:', packs)

# load notification module
path = os.path.join(ROOT,'io','notification.py')
spec = importlib.util.spec_from_file_location('local_notification', path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

# set a speak callable that reports
mod.set_speak_callable(lambda t,**k: print('[SPEAK]',t))

levels = ['info','warning','error']
for p in packs:
    print('\n--- PACK:', p, '---')
    for l in levels:
        f = os.path.join(ROOT,'assets','sounds','packs',p,f"{l}.wav")
        if os.path.exists(f):
            print('Playing', p, l)
            try:
                import winsound
                winsound.PlaySound(f, winsound.SND_FILENAME)
            except Exception as e:
                print('winsound failed:', e)
                try:
                    import pygame
                    pygame.mixer.init()
                    pygame.mixer.music.load(f)
                    pygame.mixer.music.play()
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.05)
                except Exception as e2:
                    print('pygame failed:', e2)
            time.sleep(0.2)
        else:
            print('Missing', f)
print('\nDone')
