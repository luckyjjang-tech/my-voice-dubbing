import os
import logging
from faster_whisper import WhisperModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("STT")

def format_timestamp(seconds: float) -> str:
    """Converts seconds into SRT timestamp format: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

class Transcriber:
    def __init__(self, model_size: str = "base", device: str = "cpu", compute_type: str = "int8"):
        logger.info(f"Initializing WhisperModel ({model_size}) on {device} ({compute_type})...")
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)

    def transcribe(self, audio_path: str, language: str = "ko"):
        """
        Transcribes audio file and returns segments with timestamps and full text.
        """
        logger.info(f"Transcribing {audio_path} (language={language})...")
        segments_gen, info = self.model.transcribe(
            audio_path,
            language=language,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )
        
        segments = []
        full_text_list = []
        for i, seg in enumerate(segments_gen, start=1):
            text = seg.text.strip()
            if not text:
                continue
            seg_data = {
                "id": i,
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
                "duration": round(seg.end - seg.start, 2),
                "text": text
            }
            segments.append(seg_data)
            full_text_list.append(text)
            
        full_text = " ".join(full_text_list)
        return {
            "language": info.language,
            "language_probability": info.language_probability,
            "duration": info.duration,
            "segments": segments,
            "full_text": full_text
        }

    def export_srt(self, segments: list, srt_path: str):
        """Exports segments list to standard SRT format."""
        os.makedirs(os.path.dirname(srt_path), exist_ok=True)
        with open(srt_path, "w", encoding="utf-8") as f:
            for seg in segments:
                f.write(f"{seg['id']}\n")
                f.write(f"{format_timestamp(seg['start'])} --> {format_timestamp(seg['end'])}\n")
                f.write(f"{seg['text']}\n\n")
        return srt_path

