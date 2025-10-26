import json, os, importlib.util, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
cfg_path = os.path.join(ROOT,'config','notifications.json')
with open(cfg_path,'r',encoding='utf-8') as f:
    cfg = json.load(f)
print('Current sound_pack:', cfg.get('sound_pack'))
if cfg.get('sound_pack') != 'soft':
    cfg['sound_pack'] = 'soft'
    with open(cfg_path,'w',encoding='utf-8') as f:
        json.dump(cfg,f,ensure_ascii=False,indent=2)
    print('Set sound_pack -> soft')
else:
    print('Already set to soft')
# load notification module and send a sample notify
path = os.path.join(ROOT,'io','notification.py')
spec = importlib.util.spec_from_file_location('local_notification', path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.set_speak_callable(lambda t,**k: print('[SPEAK]',t))
print('Sending sample info notification...')
mod.notify({'title':'iO','message':'تست صدای ملایم','level':'info'})
# wait a bit for async sound play
time.sleep(1)
print('Done')
