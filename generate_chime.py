# Generate a short pleasant chime WAV using simple wave synthesis
import wave
import struct
import math

out_path = 'assets/sounds/info_modern.wav'
framerate = 44100
length_seconds = 0.6

# create combined tones (arpeggiated major third)
freqs = [880.0, 1108.73]  # A5 and C#6 (pleasant interval)
vol = 0.6

frames = []
for i in range(int(framerate * length_seconds)):
    t = i / framerate
    # amplitude envelope (fast attack, slow decay)
    env = (1.0 - t/length_seconds) ** 1.4
    sample = 0.0
    # additive synthesis with slight detune
    for f in freqs:
        detune = f * (1 + 0.002 * math.sin(2*math.pi*3*t))
        sample += math.sin(2 * math.pi * detune * t)
    # gentle click removal: apply ramp at start
    if i < 200:
        ramp = i / 200.0
    else:
        ramp = 1.0
    sample = sample * env * ramp * vol / len(freqs)
    # soft high-frequency fuzz
    sample += 0.01 * math.sin(2*math.pi*6000*t)
    frames.append(int(sample * 32767.0))

# ensure directory exists
import os
os.makedirs(os.path.dirname(out_path), exist_ok=True)

with wave.open(out_path, 'w') as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(framerate)
    wf.writeframes(struct.pack('<' + 'h'*len(frames), *frames))

print('Wrote', out_path)
