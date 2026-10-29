#!/bin/sh
# Dark, rough narrator: -3 semitones (timing kept), quiet octave-down layer,
# heavy lows, dulled highs, soft-clip grit, compression, short room echo.
# usage: sh voice_fx.sh vo_dmitri.wav vo_dark.wav
ffmpeg -y -loglevel error -i "$1" -filter_complex "
[0:a]asplit=2[a][b];
[a]asetrate=22050*0.84,aresample=44100,atempo=1.1905[main];
[b]asetrate=22050*0.6,aresample=44100,atempo=1.6667,lowpass=f=900,volume=0.22[sub];
[main][sub]amix=inputs=2:normalize=0,
highpass=f=55,
equalizer=f=120:t=q:w=1:g=4,equalizer=f=250:t=q:w=1:g=2,equalizer=f=1800:t=q:w=1.5:g=-2,equalizer=f=3500:t=q:w=1:g=1.5,
lowpass=f=6500,
volume=9dB,asoftclip=type=tanh,volume=-7dB,
acompressor=threshold=-22dB:ratio=4:attack=5:release=150:makeup=3,
aecho=0.85:0.5:45|90:0.16|0.08,volume=4.5dB" -ac 1 -ar 44100 "$2"
