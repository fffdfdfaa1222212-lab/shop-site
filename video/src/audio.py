"""Build the final soundtrack: processed voice + breaths + procedural sound design.

usage: python3 -I audio.py <voice_processed.wav (44.1k mono)> <cues.json> <total_seconds> <out.wav>
"""
import json
import sys

import numpy as np
import soundfile as sf

SR = 44100
vo_path, cues_path, total, out_path = sys.argv[1], sys.argv[2], float(sys.argv[3]), sys.argv[4]
C = json.load(open(cues_path))
N = int(total * SR)
rng = np.random.default_rng(7)

vo, sr = sf.read(vo_path)
assert sr == SR
if vo.ndim > 1:
    vo = vo.mean(axis=1)
vo = np.pad(vo, (0, max(0, N - len(vo))))[:N]

sfx = np.zeros(N)
bed = np.zeros(N)


def tt(d):
    return np.arange(int(d * SR)) / SR


def add(buf, t0, sig, gain=1.0):
    i = int(t0 * SR)
    if i >= N:
        return
    sig = sig[: N - i]
    buf[i: i + len(sig)] += sig * gain


def lowpass(x, cutoff):
    # one-pole, good enough for sound design
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for k in range(len(x)):
        acc = (1 - a) * x[k] + a * acc
        y[k] = acc
    return y


def bandnoise(d, lo, hi):
    n = rng.standard_normal(int(d * SR))
    return lowpass(n, hi) - lowpass(lowpass(n, hi), lo)


def env(d, attack, release_pow=3.0):
    t = tt(d)
    e = np.minimum(t / max(attack, 1e-4), 1.0) * (1 - t / d) ** release_pow
    return e


def impact(d=2.2):
    t = tt(d)
    sub = np.sin(2 * np.pi * (38 + 40 * np.exp(-t * 8)) * t) * np.exp(-t * 1.6)
    crack = lowpass(rng.standard_normal(len(t)), 2500) * np.exp(-t * 14) * 2.5
    tail = lowpass(rng.standard_normal(len(t)), 400) * np.exp(-t * 2.2) * 0.6
    return np.tanh((sub + crack + tail) * 1.4)


def power_down(d=1.6):
    t = tt(d)
    f = 320 * np.exp(-t * 2.4) + 30
    ph = 2 * np.pi * np.cumsum(f) / SR
    return (np.sin(ph) + 0.4 * np.sin(2 * ph)) * env(d, 0.01, 1.5)


def click(d=0.03, tone=3000):
    t = tt(d)
    return (np.sin(2 * np.pi * tone * t) * 0.4 + rng.standard_normal(len(t)) * 0.6) * np.exp(-t * 180)


def glitch(d=0.12):
    t = tt(d)
    sq = np.sign(np.sin(2 * np.pi * rng.uniform(120, 900) * t))
    return (sq * 0.5 + rng.standard_normal(len(t)) * 0.5) * (rng.random(len(t)) > 0.3) * env(d, 0.002, 1)


def whoosh(d=0.5, rev=False):
    s = bandnoise(d, 300, 3000) * np.sin(np.pi * tt(d) / d) ** 2
    return s[::-1] if rev else s


def thump(d=0.25, f=52):
    t = tt(d)
    return np.sin(2 * np.pi * f * t * (1 + 0.6 * np.exp(-t * 30))) * np.exp(-t * 16)


def step():
    return lowpass(rng.standard_normal(int(0.09 * SR)), 900) * np.exp(-tt(0.09) * 45) * 1.5


def breath(d=0.32):
    # soft in-breath: band-limited noise with a swell; quiet, just enough to feel human
    return bandnoise(d, 500, 2400) * np.sin(np.pi * tt(d) / d) ** 1.5


end = C["end"]

# ---------- bed: low drone + wind, swelling toward the double ----------
t = np.arange(N) / SR
drone = (np.sin(2 * np.pi * 55 * t) + 0.7 * np.sin(2 * np.pi * 55.6 * t) + 0.35 * np.sin(2 * np.pi * 82.4 * t))
drone *= 0.6 + 0.4 * np.sin(2 * np.pi * 0.17 * t)
wind = lowpass(rng.standard_normal(N), 350)
level = np.interp(t, [0, C["city"], C["man"], C["face"] - 0.05, C["face"] + 0.6, C["twin"], end, total],
                  [0.5, 0.6, 0.85, 1.0, 0.0, 1.0, 1.2, 0.0])
bed += (drone * 0.12 + wind * 0.5) * level

# ---------- hook ----------
add(sfx, 0.05, impact(), 0.9)
for k in np.arange(0, C["city"], 0.9):  # alarm-clock blink beeps
    add(sfx, k, np.sin(2 * np.pi * 1760 * tt(0.08)) * env(0.08, 0.005, 1), 0.07)
add(sfx, C["hook2"] - 0.45, whoosh(0.45, rev=True), 0.35)
add(sfx, C["hook2"], impact(), 0.8)
add(sfx, C["hook2"] + 0.1, click(0.05, 1200), 0.4)  # hand flinches off the switch

# ---------- city blackout ----------
add(sfx, C["city"] + 0.15, power_down(), 0.6)
for i in range(10):
    add(sfx, C["city"] + 0.25 + i * 0.11, click(0.02, 2500 + i * 90), 0.12)

# ---------- substation: 50 Hz hum that dies with the lamps ----------
d = C["phone"] - C["max"]
th = tt(d)
hum = sum(np.sin(2 * np.pi * 50 * h * th) / h for h in (1, 2, 3, 5, 7))
hum_env = np.clip((C["max3"] + 0.15 + 8 * 0.13 - (C["max"] + th)) * 3, 0, 1)
add(sfx, C["max"], hum * hum_env, 0.05)
for i in range(8):
    add(sfx, C["max3"] + 0.15 + i * 0.13, click(0.04, 1800), 0.25)
add(sfx, C["max3"] + 0.15 + 8 * 0.13, power_down(0.8), 0.25)

# ---------- montage ----------
add(sfx, C["phone"] + 0.28, glitch(0.15), 0.25)
dcar = 0.6
eng = np.sin(2 * np.pi * 34 * tt(dcar)) * (0.6 + 0.4 * np.sign(np.sin(2 * np.pi * 9 * tt(dcar))))
add(sfx, C["car"], lowpass(eng, 300) * np.linspace(1, 0, len(eng)) ** 2, 0.8)  # engine coughs and dies
for k in np.arange(0, C["walk"] - C["clock"], 0.25):  # stuck second hand twitching
    add(sfx, C["clock"] + k, click(0.025, 4200 if int(k * 4) % 2 else 3600), 0.18)

# ---------- walk: footsteps, flashlight click ----------
add(sfx, C["walk"] + 0.05, click(0.03, 900), 0.4)
for k in np.arange(0.1, C["floor"] - C["walk"], 0.524):
    add(sfx, C["walk"] + k, step(), 0.35)
# rising tone while the camera climbs the building
dr = C["man"] - C["floor"]
rise = np.sin(2 * np.pi * np.cumsum(np.linspace(110, 220, int(dr * SR))) / SR) * np.linspace(0, 1, int(dr * SR)) ** 2
add(sfx, C["floor"], rise, 0.08)
add(sfx, C["third"], impact(1.4), 0.35)

# ---------- the double: silence, then heartbeat ----------
add(sfx, C["man"], whoosh(0.5), 0.25)
beat = 1 / 1.1
k = C["face"] + 0.12
while k < C["twin"] + 0.3:
    add(sfx, k, thump(), 0.9)
    add(sfx, k + 0.18, thump(0.2, 46), 0.6)
    k += beat

# ---------- 3:06, time runs backwards ----------
add(sfx, C["twin"] + 0.3, whoosh(0.8), 0.2)  # arm rising
add(sfx, C["306"] - 0.6, whoosh(0.6, rev=True), 0.45)
add(sfx, C["306"], impact(2.0), 1.0)
add(sfx, C["306"], glitch(0.3), 0.3)
for i, k in enumerate(np.arange(0.2, 1.6, 0.11)):  # ticks rushing backwards
    add(sfx, C["306"] + k, click(0.025, 3800)[::-1], 0.15 * (1 - i / 14))
add(sfx, end + 0.35, impact(2.0), 0.7)  # "ЧАСТЬ 2"

# ---------- human breaths before some phrases ----------
for cid in ("hook", "city", "max", "walk", "man", "face", "twin"):
    add(sfx, max(0.0, C[cid] - 0.36), breath(), 0.035)

# ---------- mix: duck bed and sfx under the voice ----------
win = int(0.05 * SR)
v_env = np.sqrt(np.convolve(vo ** 2, np.ones(win) / win, mode="same"))
duck = 1 - 0.55 * np.clip(v_env / (v_env.max() * 0.25), 0, 1)
duck = np.convolve(duck, np.ones(int(0.12 * SR)) / int(0.12 * SR), mode="same")

mix_l = vo * 1.0 + (bed * 0.55 + sfx * 0.55) * duck
# light stereo width for the bed only
mix_r = vo * 1.0 + (np.roll(bed, int(0.012 * SR)) * 0.55 + sfx * 0.55) * duck
out = np.stack([mix_l, mix_r], axis=1)
out = np.tanh(out / np.max(np.abs(out)) * 1.2) * 0.9
sf.write(out_path, out, SR)
print("ok", out.shape[0] / SR)
