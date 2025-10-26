import importlib.util, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path = os.path.join(ROOT,'io','notification.py')
spec = importlib.util.spec_from_file_location('local_notification', path)
if spec is None:
	raise ImportError(f"Cannot create module spec from path: {path}")
mod = importlib.util.module_from_spec(spec)
# spec.loader can be None in some environments; ensure it's present
if spec.loader is None:
	raise ImportError(f"No loader available for module spec from path: {path}")
spec.loader.exec_module(mod)
# register a speak callable that prints
mod.set_speak_callable(lambda t, **k: print('[SPEAK]', t, k))
print('Notify suppressed message...')
mod.notify({'title':'iO','message':'متاسفم، متوجه نشدم. لطفا دوباره بگویید.','level':'info','voice':True})
print('Done')
