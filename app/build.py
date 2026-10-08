#!/usr/bin/env python3
"""Собирает app/index.html — один самодостаточный файл (данные внутри), открывается двойным кликом.
Опционально: build.py <путь> — фрагмент без <html>/<head>/<body> для публикации артефактом."""
import sys,pathlib
d=pathlib.Path(__file__).parent
src=(d/'index.src.html').read_text().replace('/*DATA*/',(d/'data.js').read_text())
if len(sys.argv)>1: pathlib.Path(sys.argv[1]).write_text(src)
else: (d/'index.html').write_text('<!doctype html>\n<html lang="ru"><head><meta charset="utf-8"></head><body>\n'+src+'\n</body></html>\n')
