import os
import tarfile
import contextlib
import wave
from pathlib import Path
from typing import Optional

import numpy as np
import requests
import aiofiles
from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import deepspeech

from config import (
    DATA_DIR,
    MODEL_PATH,
    SCORER_PATH,
    LIBRISPEECH_DIR,
    DEEPSPEECH_MODEL_URL,
    DEEPSPEECH_SCORER_URL,
    LIBRISPEECH_URL,
    SUPPORTED_AUDIO_FORMATS,
    MAX_FILE_SIZE,
    MODEL_BEAM_WIDTH,
    MODEL_ALPHA,
    MODEL_BETA,
    HOST,
    PORT,
)
from audio_utils import ensure_wav_pcm16

app = FastAPI(title="Bluleap AI - Speech to Text System", version="1.0.0")

# Create directories
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Global variable for model
model: Optional[deepspeech.Model] = None


def download_file(url: str, filepath: str) -> None:
    resp = requests.get(url, stream=True, timeout=180)
    resp.raise_for_status()
    tmp_path = f"{filepath}.part"
    with open(tmp_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    os.replace(tmp_path, filepath)


def download_models() -> None:
    # Download model
    if not os.path.exists(MODEL_PATH):
        print("Downloading DeepSpeech model…")
        download_file(DEEPSPEECH_MODEL_URL, MODEL_PATH)
    # Download scorer
    if not os.path.exists(SCORER_PATH):
        print("Downloading DeepSpeech scorer…")
        download_file(DEEPSPEECH_SCORER_URL, SCORER_PATH)

    # Load model
    global model
    print("Loading DeepSpeech model…")
    m = deepspeech.Model(MODEL_PATH)
    m.setBeamWidth(MODEL_BEAM_WIDTH)
    m.enableExternalScorer(SCORER_PATH)
    m.setScorerAlphaBeta(MODEL_ALPHA, MODEL_BETA)
    global model
    model = m
    print("Model loaded successfully!")


def download_librispeech() -> None:
    if os.path.exists(LIBRISPEECH_DIR):
        return
    print("Downloading LibriSpeech dev-clean…")
    tar_path = os.path.join(DATA_DIR, "dev-clean.tar.gz")
    if not os.path.exists(tar_path):
        download_file(LIBRISPEECH_URL, tar_path)
    print("Extracting LibriSpeech…")
    with tarfile.open(tar_path, "r:gz") as tar:
        tar.extractall(DATA_DIR)


def stt_from_wav(wav_path: str) -> str:
    if model is None:
        raise RuntimeError("Model not loaded")
    with contextlib.closing(wave.open(wav_path, "rb")) as wf:
        frames = wf.getnframes()
        audio = np.frombuffer(wf.readframes(frames), dtype=np.int16)
    return model.stt(audio)


@app.on_event("startup")
async def startup_event():
    try:
        download_models()
        download_librispeech()
    except Exception as e:
        print(f"Startup error: {e}")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/upload-audio")
async def upload_audio(audio_file: UploadFile = File(...)):
    ext = Path(audio_file.filename).suffix.lower()
    if ext not in SUPPORTED_AUDIO_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type {ext}. Supported: {SUPPORTED_AUDIO_FORMATS}",
        )

    temp_in = Path(f"/tmp/in_{os.getpid()}_{audio_file.filename}")
    try:
        async with aiofiles.open(temp_in, "wb") as f:
            content = await audio_file.read()
            if len(content) > MAX_FILE_SIZE:
                raise HTTPException(status_code=413, detail="File too large")
            await f.write(content)

        wav_path, created = ensure_wav_pcm16(str(temp_in))
        try:
            text = stt_from_wav(wav_path)
        finally:
            if created and os.path.exists(wav_path):
                os.remove(wav_path)

        return {"text": text, "filename": audio_file.filename}
    finally:
        if os.path.exists(temp_in):
            os.remove(temp_in)


@app.get("/sample-audio")
async def get_sample_audio():
    # Return the first FLAC/WAV found in LibriSpeech and its on-the-fly transcript
    for root, _, files in os.walk(LIBRISPEECH_DIR):
        for file in files:
            if file.lower().endswith((".flac", ".wav")):
                src = os.path.join(root, file)
                wav_path, created = ensure_wav_pcm16(src)
                try:
                    text = stt_from_wav(wav_path)
                finally:
                    if created and os.path.exists(wav_path) and not src.endswith(".wav"):
                        os.remove(wav_path)
                return {"sample_file": file, "transcript": text}
    return {"error": "No audio files found in LibriSpeech/dev-clean"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "model_loaded": model is not None}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)