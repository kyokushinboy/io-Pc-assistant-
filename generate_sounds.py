"""Generate short WAV sound files for notifications.
Creates assets/sounds/info.wav, warn.wav, error.wav (mono, 44100Hz, 16-bit) with short tones.
Run: python tools/generate_sounds.py
"""
import os
import wave
import struct
import math

out_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'sounds')
os.makedirs(out_dir, exist_ok=True)

def write_tone(path, freq=440.0, duration=0.2, volume=0.5, samplerate=44100):
    n_samples = int(samplerate * duration)
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(samplerate)
        for i in range(n_samples):
            t = float(i) / samplerate
            sample = volume * math.sin(2 * math.pi * freq * t)
            # 16-bit PCM
            val = int(sample * 32767.0)
            data = struct.pack('<h', val)
            wf.writeframesraw(data)
        wf.writeframes(b'')

files = [
    ('info.wav', 880.0),
    ('warn.wav', 660.0),
    ('error.wav', 440.0),
]
for name, freq in files:
    path = os.path.join(out_dir, name)
    write_tone(path, freq=freq, duration=0.2)
    print('Wrote', path)
print('Done')
