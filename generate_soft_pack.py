# Generate a 'soft' sound pack with gentle bells and fade
import os, wave, struct, math
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pack = 'soft'
pack_dir = os.path.join(ROOT,'assets','sounds','packs',pack)
os.makedirs(pack_dir, exist_ok=True)
framerate = 44100
length = 0.7

levels = {
    'info': [880.0, 1320.0],
    'warning': [660.0, 880.0],
    'error': [440.0, 660.0]
}

for level, freqs in levels.items():
    frames = []
    for i in range(int(framerate*length)):
        t = i/framerate
        env = (1.0 - t/length)**1.6
        s = 0.0
        for j,f in enumerate(freqs):
            # soft bell: exponential decay + slight inharmonicity
            det = f * (1 + 0.001*j)
            s += math.sin(2*math.pi*det*t) * math.exp(-3.0*t)
        # apply gentle lowpass-ish by scaling HF
        s = s * env * 0.35
        frames.append(int(s*32767))
    path = os.path.join(pack_dir, f"{level}.wav")
    with wave.open(path,'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(framerate)
        wf.writeframes(struct.pack('<' + 'h'*len(frames), *frames))
    print('Wrote', path)
print('done')
