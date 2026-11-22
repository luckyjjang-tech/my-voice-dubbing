import os
import shutil
import logging
from downloader import download_youtube_media, extract_voice_prompt
from stt_transcribe import Transcriber
from translator import DubTranslator, TARGET_LANGUAGES
from voice_synthesizer import VoiceSynthesizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Pipeline")

class DubbingPipeline:
    def __init__(self, whisper_model: str = "base", device: str = None):
        self.device = device
        self.transcriber = Transcriber(model_size=whisper_model, device="cpu")
        self.translator = DubTranslator(source_lang="korean")
        self._synthesizer = None

    @property
    def synthesizer(self):
        if self._synthesizer is None:
            self._synthesizer = VoiceSynthesizer(device=self.device)
        return self._synthesizer

    def run(self, youtube_url: str,
            target_langs: list = None,
            voice_start_sec: float = 0.0,
            voice_duration: float = 20.0,
            output_base_dir: str = "outputs",
            progress_callback=None):
        """
        Full end-to-end execution of AI Dubbing:
        1. Download YouTube video & audio
        2. Extract reference voice prompt
        3. STT Transcription & timestamp alignment
        4. Multilingual translation & Chatterbox TTS generation
        5. Dubbed video & audio export + ZIP packaging
        """
        def update_progress(percent: float, message: str):
            logger.info(f"[{percent*100:.0f}%] {message}")
            if progress_callback:
                progress_callback(percent, message)

        if not target_langs:
            target_langs = list(TARGET_LANGUAGES.keys())

        update_progress(0.05, "유튜브 영상 및 오디오를 다운로드하는 중...")
        os.makedirs(output_base_dir, exist_ok=True)
        media_info = download_youtube_media(youtube_url, output_base_dir)
        
        video_path = media_info["video_path"]
        audio_path = media_info["audio_path"]
        video_duration = media_info.get("duration", 60.0)

        update_progress(0.20, f"화자의 고유 목소리 샘플(24kHz 모노, {voice_duration}초)을 추출하는 중...")
        voice_sample_path = os.path.join(output_base_dir, "my_voice.wav")
        extract_voice_prompt(audio_path, voice_sample_path, start_sec=voice_start_sec, duration_sec=voice_duration)

        update_progress(0.30, "Whisper AI를 사용하여 컨텐츠 음성 인식(STT) 및 자막 초 단위 추출 중...")
        stt_result = self.transcriber.transcribe(audio_path, language="ko")
        segments = stt_result["segments"]
        full_text = stt_result["full_text"]

        # Save original Korean subtitles
        ko_srt_path = os.path.join(output_base_dir, "subtitles_ko.srt")
        self.transcriber.export_srt(segments, ko_srt_path)

        update_progress(0.45, "로컬 AI 모델(Chatterbox Multilingual)을 준비하는 중...")
        _ = self.synthesizer  # ensure synthesizer is initialized

        results = {
            "title": media_info["title"],
            "duration": video_duration,
            "voice_sample": voice_sample_path,
            "original_video": video_path,
            "original_audio": audio_path,
            "subtitles_ko": ko_srt_path,
            "full_text": full_text,
            "segments": segments,
            "languages": {}
        }

        # Step through target languages
        lang_progress_step = 0.50 / max(len(target_langs), 1)
        current_progress = 0.45

        for i, lang_code in enumerate(target_langs):
            lang_info = TARGET_LANGUAGES.get(lang_code, {})
            lang_name = lang_info.get('name', lang_code)
            chatterbox_code = lang_info.get('chatterbox', lang_code)

            update_progress(current_progress, f"[{i+1}/{len(target_langs)}] '{lang_name}' 번역 및 AI 목소리 생성 준비 중...")

            # 1. Translate
            translated_segments = self.translator.translate_segments(segments, lang_code)
            tr_full_text = self.translator.translate_text(full_text, lang_code)

            # Save translated SRT
            srt_path = os.path.join(output_base_dir, f"subtitles_{lang_code}.srt")
            self.transcriber.export_srt(translated_segments, srt_path)

            # 2. Synthesize audio with sub-progress callback
            audio_out_path = os.path.join(output_base_dir, f"dubbed_{lang_code}.wav")
            
            def sub_prog(curr, total, text_preview):
                sub_pct = current_progress + (curr / max(total, 1)) * (lang_progress_step * 0.8)
                update_progress(sub_pct, f"[{i+1}/{len(target_langs)}] '{lang_name}' 음성 생성 중 ({curr}/{total} 구간)...")

            try:
                # If we have timed segments, generate synchronized dubbing with chunking
                if segments and len(segments) > 1:
                    self.synthesizer.synthesize_timed_dubbing(
                        translated_segments=translated_segments,
                        lang_code=chatterbox_code,
                        voice_sample_path=voice_sample_path,
                        total_duration=video_duration,
                        output_path=audio_out_path,
                        progress_callback=sub_prog
                    )
                else:
                    self.synthesizer.synthesize_text(
                        text=tr_full_text,
                        lang_code=chatterbox_code,
                        voice_sample_path=voice_sample_path,
                        output_path=audio_out_path,
                        progress_callback=sub_prog
                    )
            except Exception as e:
                logger.error(f"Failed to synthesize for {lang_code}: {e}")
                continue

            # 3. Create dubbed video
            video_out_path = os.path.join(output_base_dir, f"dubbed_{lang_code}.mp4")
            try:
                self.synthesizer.create_dubbed_video(video_path, audio_out_path, video_out_path)
            except Exception as e:
                logger.warning(f"Failed to merge dubbed video for {lang_code}: {e}")
                video_out_path = None

            results["languages"][lang_code] = {
                "name": lang_name,
                "translated_text": tr_full_text,
                "srt_path": srt_path,
                "audio_path": audio_out_path,
                "video_path": video_out_path
            }

            current_progress += lang_progress_step

        update_progress(0.95, "전체 결과를 하나의 압축파일(ZIP)로 패키징하는 중...")
        zip_base = os.path.join(output_base_dir, "dubbing_results_all")
        zip_path = shutil.make_archive(zip_base, 'zip', output_base_dir)
        results["zip_path"] = zip_path

        update_progress(1.0, "모든 언어 더빙 및 다운로드 파일 생성 완료! 🎉")
        return results

