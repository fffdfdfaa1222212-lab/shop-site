"""Add a gravelly rasp layer that follows the voice, and check phrase alignment.

usage: python3 -I rasp.py <base.wav> <reference.wav> <out.wav>
"""
import sys

import numpy as np
import soundfile as sf

base_p, ref_p, out_p = sys.argv[1:4]
x, sr = sf.read(base_p)
ref, rsr = sf.read(ref_p)
assert sr == rsr == 44100


def band(sig, lo, hi):
    S = np.fft.rfft(sig)
    f = np.fft.rfftfreq(len(sig), 1 / sr)
    S[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(S, len(sig))


def envelope(sig, ms=15):
    w = int(sr * ms / 1000)
    return np.sqrt(np.convolve(sig ** 2, np.ones(w) / w, mode="same"))


# alignment check: lag of base vs reference envelopes, via cross-correlation over the whole file
n = min(len(x), len(ref))
ea, eb = envelope(x[:n], 30)[::100], envelope(ref[:n], 30)[::100]
ea, eb = ea - ea.mean(), eb - eb.mean()
lags = np.arange(-40, 41)
corr = [np.dot(ea[max(0, l):len(ea) + min(0, l)], eb[max(0, -l):len(eb) - max(0, l)]) for l in lags]
print("lag vs previous voice, ms:", lags[int(np.argmax(corr))] * 100 / sr * 1000)

# rasp: noise in the 1.2-5 kHz band, amplitude-modulated by the voice's own mid band
# plus a 38 Hz flutter so it reads as vocal fry / gravel rather than hiss
env = envelope(band(x, 300, 3000), 12)
env = env / env.max()
gate = np.clip((env - 0.08) / 0.5, 0, 1)
t = np.arange(len(x)) / sr
flutter = 0.55 + 0.45 * np.sign(np.sin(2 * np.pi * 38 * t + 2 * np.sin(2 * np.pi * 3 * t)))
noise = band(np.random.default_rng(3).standard_normal(len(x)), 1200, 5000)
noise /= np.abs(noise).max()
rasp = noise * gate * flutter

y = x / np.abs(x).max() * 0.85 + rasp * 0.10
y = y / np.abs(y).max() * 0.6
sf.write(out_p, y, sr)
print("written", round(len(y) / sr, 2), "s")
