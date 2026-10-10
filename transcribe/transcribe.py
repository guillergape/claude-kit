"""Transcribe an audio file locally with Whisper (0 tokens, nothing leaves the PC).

Usage: <venv python> -I transcribe.py <audio> ["hint words"] [--model small]
  venv python = Windows %USERPROFILE%\\.whisper\\Scripts\\python.exe · Mac/Linux ~/.whisper/bin/python
Hint words (names, jargon) fix proper nouns, e.g. "Fourier, Valgrind".
"""
import argparse, sys, time
import av, numpy as np
from faster_whisper import WhisperModel

p = argparse.ArgumentParser()
p.add_argument("audio")
p.add_argument("hint", nargs="?")
p.add_argument("--model", default="large-v3-turbo")
p.add_argument("--lang", default="es")
a = p.parse_args()
sys.stdout.reconfigure(encoding="utf-8")

# ponytail: own decode because faster-whisper 1.2.1 passes an arg PyAV 19 dropped; drop when fixed upstream
with av.open(a.audio) as c:
    rs = av.AudioResampler(format="s16", layout="mono", rate=16000)
    audio = np.concatenate([f.to_ndarray().ravel() for fr in c.decode(audio=0) for f in rs.resample(fr)]).astype(np.float32) / 32768

t = time.time()
segs, info = WhisperModel(a.model, device="cpu", compute_type="int8").transcribe(
    audio, language=a.lang, vad_filter=True, initial_prompt=a.hint)
text = " ".join(s.text.strip() for s in segs)
print(f"[{a.model}] {info.duration:.0f}s audio, {time.time() - t:.0f}s", file=sys.stderr)
print(text)
