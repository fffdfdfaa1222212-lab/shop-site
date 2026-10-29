"""Synthesize the voice-over phrase by phrase with per-phrase tempo and pauses.

usage: python3 -I tts.py <voice> <out_dir> [speed_mult] [pause_mult]
Writes <out_dir>/vo_<voice>.wav and <out_dir>/cues_<voice>.json (start time of each phrase).
"""
import json
import sys

import numpy as np
import sherpa_onnx
import soundfile as sf

MODELS = "/tmp/claude-0/-home-user-shop-site/4dc961c5-5583-5974-bd53-f2014b01b55f/scratchpad/models"
voice, out_dir = sys.argv[1], sys.argv[2]
SPEED = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
PAUSE = float(sys.argv[4]) if len(sys.argv) > 4 else 1.0
d = f"{MODELS}/vits-piper-ru_RU-{voice}-medium"

tts = sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(
    model=sherpa_onnx.OfflineTtsModelConfig(
        vits=sherpa_onnx.OfflineTtsVitsModelConfig(
            model=f"{d}/ru_RU-{voice}-medium.onnx",
            tokens=f"{d}/tokens.txt",
            data_dir=f"{d}/espeak-ng-data",
            # more variation in intonation and rhythm than the defaults -> less robotic
            noise_scale=0.75,
            noise_scale_w=0.95,
        ),
        num_threads=4,
    ),
))

# (cue id, text, speed, pause after in seconds). speed < 1 = slower.
LINES = [
    ("hook",   "Если в три ноль семь ночи у тебя погас свет,", 0.92, 0.22),
    ("hook2",  "не включай его.", 0.80, 0.55),
    ("city",   "Той ночью погас весь город.", 1.00, 0.25),
    ("city2",  "Весь,", 0.85, 0.18),
    ("window", "кроме одного окна.", 0.88, 0.45),
    ("max",    "Макс, дежурный электрик, проверил подстанцию.", 1.08, 0.18),
    ("max2",   "Ток был.", 0.95, 0.30),
    ("max3",   "Но свет не горел нигде.", 0.92, 0.40),
    ("phone",  "Телефоны мертвы.", 1.05, 0.12),
    ("car",    "Машины заглохли.", 1.05, 0.12),
    ("clock",  "Все часы в городе встали на три ноль семь.", 1.02, 0.45),
    ("walk",   "Он пошёл на единственный свет.", 1.02, 0.18),
    ("floor",  "Девятый этаж.", 0.95, 0.15),
    ("third",  "Третье окно.", 0.90, 0.55),
    ("man",    "В окне стоял человек.", 0.95, 0.40),
    ("jacket", "В его куртке.", 0.88, 0.40),
    ("face",   "С его лицом.", 0.78, 0.90),
    ("twin",   "Двойник поднял руку и показал на часы.", 1.00, 0.35),
    ("was",    "На них было", 0.92, 0.35),
    ("306",    "три ноль шесть.", 0.80, 0.30),
]

sr = None
chunks, cues, t = [], {}, 0.35  # small lead-in before the first word
chunks.append(None)
for cid, text, speed, pause in LINES:
    audio = tts.generate(text, sid=0, speed=speed * SPEED)
    sr = audio.sample_rate
    a = np.asarray(audio.samples, dtype=np.float32)
    # trim leading/trailing near-silence so pauses are exactly what we set
    idx = np.where(np.abs(a) > 0.01)[0]
    a = a[max(idx[0] - int(0.02 * sr), 0): idx[-1] + int(0.06 * sr)]
    cues[cid] = round(t, 3)
    chunks.append(a)
    chunks.append(np.zeros(int(pause * PAUSE * sr), dtype=np.float32))
    t += len(a) / sr + pause * PAUSE

chunks[0] = np.zeros(int(0.35 * sr), dtype=np.float32)
out = np.concatenate(chunks)
out = out / np.max(np.abs(out)) * 0.9
sf.write(f"{out_dir}/vo_{voice}.wav", out, sr)
cues["end"] = round(t, 3)
json.dump(cues, open(f"{out_dir}/cues_{voice}.json", "w"), ensure_ascii=False, indent=1)
print(voice, "duration", round(t, 2), "s")
