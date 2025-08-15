import os
import subprocess
import uuid
from pathlib import Path
from typing import Tuple

from config import TARGET_SAMPLE_RATE, TARGET_CHANNELS

FFMPEG_BIN = os.environ.get("FFMPEG_BIN", "ffmpeg")


def ensure_wav_pcm16(input_path: str) -> Tuple[str, bool]:
    """
    Convert any supported audio to 16kHz mono 16-bit PCM WAV using ffmpeg.
    Returns (wav_path, created_temp) where created_temp indicates whether a new
    temp file was created and should be deleted by the caller.
    """
    in_path = Path(input_path)
    out_path = in_path
    created_temp = False

    # Always write to a temp .wav to guarantee format
    tmp_wav = in_path.parent / f"conv_{uuid.uuid4().hex}.wav"

    cmd = [
        FFMPEG_BIN,
        "-y",
        "-i",
        str(in_path),
        "-ac",
        str(TARGET_CHANNELS),
        "-ar",
        str(TARGET_SAMPLE_RATE),
        "-f",
        "wav",
        "-acodec",
        "pcm_s16le",
        str(tmp_wav),
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out_path = tmp_wav
        created_temp = True
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg conversion failed: {e.stderr.decode(errors='ignore')}")

    return str(out_path), created_temp