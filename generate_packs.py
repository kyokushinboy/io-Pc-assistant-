# Generate simple pack sounds for modern, minimal and retro
import os, wave, struct, math
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
packs = {
    'modern': {'info': [880, 1108], 'warning': [660,880], 'error': [220,330]},
    'minimal': {'info': [880], 'warning': [660], 'error': [440]},
    'retro': {'info': [660,880], 'warning': [440,550], 'error': [220,110]}
}
framerate = 44100
length = 0.5

os.makedirs(os.path.join(ROOT,'assets','sounds','packs'), exist_ok=True)
for pack, levels in packs.items():
    pack_dir = os.path.join(ROOT,'assets','sounds','packs',pack)
    os.makedirs(pack_dir, exist_ok=True)
    for level, freqs in levels.items():
        frames = []
        for i in range(int(framerate*length)):
            t = i/framerate
            env = (1.0 - t/length)**1.2
            s = 0.0
            for f in freqs:
                s += math.sin(2*math.pi*(f + (5*math.sin(2*math.pi*3*t))) * t)
            s = s * env * 0.6 / len(freqs)
            frames.append(int(s*32767))
        path = os.path.join(pack_dir, f"{level}.wav")
        with wave.open(path,'w') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(framerate)
            wf.writeframes(struct.pack('<' + 'h'*len(frames), *frames))
        print('Wrote', path)
print('done')
