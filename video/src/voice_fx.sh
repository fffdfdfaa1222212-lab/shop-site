#!/bin/sh
# Horror-trailer narrator: -4.7 semitones (timing kept), loud octave-down layer,
# slightly detuned double for an "not quite one voice" feel, heavy lows, dulled highs,
# hard atan saturation, strong compression, long dark multi-tap echo.
# Then rasp.py adds a gravel/vocal-fry layer that follows the voice.
# usage: sh voice_fx.sh vo_dmitri.wav vo_horror_base.wav && python3 -I rasp.py vo_horror_base.wav vo_proc.wav vo_horror.wav
ffmpeg -y -loglevel error -i "$1" -filter_complex "
[0:a]asplit=3[a][b][c];
[a]asetrate=22050*0.76,aresample=44100,atempo=1.3158[main];
[b]asetrate=22050*0.5,aresample=44100,atempo=2.0,lowpass=f=700,volume=0.42[sub];
[c]asetrate=22050*0.73,aresample=44100,atempo=1.3699,adelay=18,volume=0.30[dbl];
[main][sub][dbl]amix=inputs=3:normalize=0,
highpass=f=45,
equalizer=f=90:t=q:w=1:g=5,equalizer=f=200:t=q:w=1:g=3,equalizer=f=1500:t=q:w=1.5:g=-3,equalizer=f=3000:t=q:w=1:g=2,
lowpass=f=5200,
volume=14dB,asoftclip=type=atan,volume=-11dB,
acompressor=threshold=-24dB:ratio=6:attack=3:release=180:makeup=4,
aecho=0.8:0.55:60|120|210:0.22|0.13|0.07" -ac 1 -ar 44100 "$2"
