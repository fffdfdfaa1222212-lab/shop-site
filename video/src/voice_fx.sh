#!/bin/sh
# Natural horror narrator (current version).
# Base: Piper voice "ruslan" (naturally low, ~117 Hz), synthesized with: python3 -I tts.py ruslan <out> 1.2 0.75
# Processing is deliberately light: -1 semitone with formants preserved, close-mic warmth,
# de-essing, gentle compression, barely-there room. No doubling, no distortion.
# usage: sh voice_fx.sh vo_ruslan.wav vo_natural.wav
ffmpeg -y -loglevel error -i "$1" -af "aresample=44100,rubberband=pitch=0.94:formant=preserved:transients=smooth,highpass=f=65,equalizer=f=110:t=q:w=1:g=2.5,equalizer=f=380:t=q:w=1.2:g=-2.5,equalizer=f=4200:t=q:w=1:g=1.5,deesser=i=0.4,acompressor=threshold=-20dB:ratio=3:attack=10:release=150:makeup=2,aecho=0.9:0.5:22:0.07,volume=6dB" -ac 1 "$2"
