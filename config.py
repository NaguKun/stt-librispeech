"""
Configuration file for Bluleap AI Speech-to-Text System
"""

import os

# URLs for downloading models and dataset
LIBRISPEECH_URL = "https://www.openslr.org/resources/12/dev-clean.tar.gz"
DEEPSPEECH_MODEL_URL = "https://github.com/mozilla/DeepSpeech/releases/download/v0.9.3/deepspeech-0.9.3-models.pbmm"
DEEPSPEECH_SCORER_URL = "https://github.com/mozilla/DeepSpeech/releases/download/v0.9.3/deepspeech-0.9.3-models.scorer"

# File paths
DATA_DIR = "data"
MODEL_PATH = os.path.join(DATA_DIR, "deepspeech-0.9.3-models.pbmm")
SCORER_PATH = os.path.join(DATA_DIR, "deepspeech-0.9.3-models.scorer")
LIBRISPEECH_DIR = os.path.join(DATA_DIR, "LibriSpeech/dev-clean")

# Server configuration
HOST = "0.0.0.0"
PORT = 8000

# Audio processing settings
SUPPORTED_AUDIO_FORMATS = [".wav"]
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
AUDIO_SAMPLE_RATE = 16000  # Hz
AUDIO_CHANNELS = 1  # Mono

# Model settings
MODEL_BEAM_WIDTH = 500
MODEL_ALPHA = 0.75
MODEL_BETA = 1.85

# UI settings
UPLOAD_CHUNK_SIZE = 8192
MAX_UPLOAD_WORKERS = 4

# Development settings
DEBUG = True
LOG_LEVEL = "INFO"
