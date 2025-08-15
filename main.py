import os
import requests
import tarfile
import zipfile
from pathlib import Path
from typing import Optional
import numpy as np
import wave
import contextlib

from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import deepspeech
import aiofiles

# Import configuration
from config import *

app = FastAPI(title="Bluleap AI - Speech to Text System", version="1.0.0")

# Create directories
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Global variables for model
model = None
scorer = None

def download_file(url: str, filepath: str) -> bool:
    """Download a file from URL to filepath"""
    try:
        print(f"Downloading {url} to {filepath}")
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Downloaded {filepath}")
        return True
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return False

def download_models():
    """Download DeepSpeech models if they don't exist"""
    global model, scorer
    
    # Download model if not exists
    if not os.path.exists(MODEL_PATH):
        print("Downloading DeepSpeech model...")
        if not download_file(DEEPSPEECH_MODEL_URL, MODEL_PATH):
            raise Exception("Failed to download DeepSpeech model")
    
    # Download scorer if not exists
    if not os.path.exists(SCORER_PATH):
        print("Downloading DeepSpeech scorer...")
        if not download_file(DEEPSPEECH_SCORER_URL, SCORER_PATH):
            raise Exception("Failed to download DeepSpeech scorer")
    
    # Load model
    print("Loading DeepSpeech model...")
    model = deepspeech.Model(MODEL_PATH)
    model.enableExternalScorer(SCORER_PATH)
    print("Model loaded successfully!")

def download_librispeech():
    """Download LibriSpeech dataset if it doesn't exist"""
    if not os.path.exists(LIBRISPEECH_DIR):
        print("Downloading LibriSpeech dataset...")
        tar_path = os.path.join(DATA_DIR, "dev-clean.tar.gz")
        
        if not os.path.exists(tar_path):
            if not download_file(LIBRISPEECH_URL, tar_path):
                raise Exception("Failed to download LibriSpeech dataset")
        
        # Extract tar file
        print("Extracting LibriSpeech dataset...")
        with tarfile.open(tar_path, 'r:gz') as tar:
            tar.extractall(DATA_DIR)
        print("LibriSpeech dataset extracted!")

def audio_to_text(audio_file_path: str) -> str:
    """Convert audio file to text using DeepSpeech"""
    global model
    
    if model is None:
        raise Exception("Model not loaded")
    
    # Read audio file
    with contextlib.closing(wave.open(audio_file_path, 'rb')) as wf:
        frames = wf.getnframes()
        sample_rate = wf.getframerate()
        audio_data = wf.readframes(frames)
    
    # Convert to numpy array
    audio = np.frombuffer(audio_data, dtype=np.int16)
    
    # Perform speech recognition
    text = model.stt(audio)
    return text

@app.on_event("startup")
async def startup_event():
    """Initialize models and dataset on startup"""
    try:
        download_models()
        download_librispeech()
    except Exception as e:
        print(f"Error during startup: {e}")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Main page with HTML interface"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload-audio")
async def upload_audio(audio_file: UploadFile = File(...)):
    """Upload and process audio file"""
    if not audio_file.filename.endswith('.wav'):
        raise HTTPException(status_code=400, detail="Only WAV files are supported")
    
    # Save uploaded file temporarily
    temp_path = f"temp_{audio_file.filename}"
    try:
        async with aiofiles.open(temp_path, 'wb') as f:
            content = await audio_file.read()
            await f.write(content)
        
        # Convert audio to text
        text = audio_to_text(temp_path)
        
        return {"text": text, "filename": audio_file.filename}
    
    finally:
        # Clean up temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.get("/sample-audio")
async def get_sample_audio():
    """Get a sample audio file from LibriSpeech for testing"""
    try:
        # Find first available audio file
        for root, dirs, files in os.walk(LIBRISPEECH_DIR):
            for file in files:
                if file.endswith('.flac'):
                    audio_path = os.path.join(root, file)
                    # Convert flac to wav for easier processing
                    wav_path = audio_path.replace('.flac', '.wav')
                    
                    # Use ffmpeg if available, otherwise return path
                    if os.path.exists(wav_path):
                        return {"audio_path": wav_path, "filename": os.path.basename(wav_path)}
                    else:
                        return {"audio_path": audio_path, "filename": os.path.basename(audio_path)}
        
        return {"error": "No audio files found"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "model_loaded": model is not None}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT)
