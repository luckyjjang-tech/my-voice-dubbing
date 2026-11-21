import os
import re
import sys
import subprocess
import logging
import torch
import torchaudio

# Ensure FFmpeg is accessible
WINGET_LINKS = r"C:\Users\User\AppData\Local\Microsoft\WinGet\Links"
if os.path.exists(WINGET_LINKS) and WINGET_LINKS not in os.environ.get("PATH", ""):
    os.environ["PATH"] = WINGET_LINKS + os.pathsep + os.environ.get("PATH", "")

from pydub import AudioSegment
from chatterbox.mtl_tts import ChatterboxMultilingualTTS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VoiceSynthesizer")

class VoiceSynthesizer:
    _instance = None
    _tts_model = None

    def __init__(self, device: str = None):
        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device
            
        if VoiceSynthesizer._tts_model is None:
            logger.info(f"Loading ChatterboxMultilingualTTS model on {self.device}...")
            VoiceSynthesizer._tts_model = ChatterboxMultilingualTTS.from_pretrained(device=self.device)
            logger.info("ChatterboxMultilingualTTS loaded successfully.")
            
        self.tts = VoiceSynthesizer._tts_model
        self.sr = self.tts.sr

    def split_into_sentences(self, text: str, max_chars: int = 150) -> list:
        """Splits text into naturally speakable sentences or clauses."""
        raw_sentences = re.split(r'([.?!,\n\r]+)', text)
        sentences = []
        current = ""
        for part in raw_sentences:
            if not part:
                continue
            if re.match(r'^[.?!,\n\r]+$', part):
                current += part
                if len(current.strip()) > 0:
                    sentences.append(current.strip())
                    current = ""
            else:
                if len(current) + len(part) > max_chars:
                    if current.strip():
                        sentences.append(current.strip())
                    current = part
                else:
                    current += part
        if current.strip():
            sentences.append(current.strip())
        return sentences or [text]

    def synthesize_text(self, text: str, lang_code: str, voice_sample_path: str,
                        output_path: str, exaggeration: float = 0.5, cfg_weight: float = 0.5):
        """
        Synthesizes text in target language using user's voice reference.
        Saves output as WAV audio.
        """
        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
            
        sentences = self.split_into_sentences(text)
        audio_chunks = []
        
        for sent in sentences:
            if not sent.strip():
                continue
            logger.info(f"Synthesizing [{lang_code}]: {sent}")
            try:
                wav = self.tts.generate(
                    sent,
                    language_id=lang_code,
                    audio_prompt_path=voice_sample_path,
                    exaggeration=exaggeration,
                    cfg_weight=cfg_weight
                )
                audio_chunks.append(wav.cpu())
            except Exception as e:
                logger.error(f"Error synthesizing chunk '{sent}': {e}")
                
        if not audio_chunks:
            raise RuntimeError(f"No audio generated for text: {text}")
            
        if len(audio_chunks) == 1:
            full_wav = audio_chunks[0]
        else:
            full_wav = torch.cat(audio_chunks, dim=-1)
            
        torchaudio.save(output_path, full_wav, self.sr)
        logger.info(f"Saved synthesized audio to {output_path}")
        return output_path

    def synthesize_timed_dubbing(self, translated_segments: list, lang_code: str,
                                 voice_sample_path: str, total_duration: float,
                                 output_path: str, exaggeration: float = 0.5, cfg_weight: float = 0.5):
        """
        Synthesizes each translated segment and aligns it on the timeline matching original video timestamps.
        Creates an exact sync audio track of the entire video length.
        """
        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
            
        # Create a silent audio track of total_duration in milliseconds
        timeline_ms = int(total_duration * 1000) + 1000
        combined_audio = AudioSegment.silent(duration=timeline_ms, frame_rate=self.sr)
        
        temp_dir = os.path.join(out_dir if out_dir else ".", f"temp_{lang_code}")
        os.makedirs(temp_dir, exist_ok=True)
        
        for seg in translated_segments:
            seg_text = seg['text'].strip()
            if not seg_text:
                continue
                
            seg_wav_path = os.path.join(temp_dir, f"seg_{seg['id']}.wav")
            try:
                wav = self.tts.generate(
                    seg_text,
                    language_id=lang_code,
                    audio_prompt_path=voice_sample_path,
                    exaggeration=exaggeration,
                    cfg_weight=cfg_weight
                )
                torchaudio.save(seg_wav_path, wav.cpu(), self.sr)
                
                # Overlay onto timeline at segment start time
                seg_audio = AudioSegment.from_file(seg_wav_path)
                start_ms = int(seg['start'] * 1000)
                combined_audio = combined_audio.overlay(seg_audio, position=start_ms)
            except Exception as e:
                logger.error(f"Error on segment {seg['id']} ('{seg_text}'): {e}")
                
        # Export final combined audio track
        combined_audio.export(output_path, format="wav")
        return output_path

    @staticmethod
    def create_dubbed_video(video_path: str, audio_path: str, output_video_path: str):
        """
        Replaces video audio track with the new dubbed audio using FFmpeg.
        Fast stream copy for video and AAC encoding for audio.
        """
        out_dir = os.path.dirname(output_video_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
            
        cmd = [
            'ffmpeg', '-y', '-v', 'error',
            '-i', video_path,
            '-i', audio_path,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-b:a', '192k',
            '-map', '0:v:0',
            '-map', '1:a:0',
            '-shortest',
            output_video_path
        ]
        subprocess.run(cmd, check=True)
        return output_video_path


