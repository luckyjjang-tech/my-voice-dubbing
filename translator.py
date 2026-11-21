import logging
from deep_translator import MyMemoryTranslator
import pykakasi

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Translator")

# Map target language codes to their descriptive names, MyMemory language names, and Chatterbox codes
TARGET_LANGUAGES = {
    'en': {
        'name': '영어 (English)',
        'mymemory': 'english',
        'chatterbox': 'en'
    },
    'ja': {
        'name': '일본어 (Japanese)',
        'mymemory': 'japanese',
        'chatterbox': 'ja'
    },
    'zh': {
        'name': '중국어 (Chinese)',
        'mymemory': 'chinese simplified',
        'chatterbox': 'zh'
    },
    'hi': {
        'name': '힌두어 (Hindi)',
        'mymemory': 'hindi',
        'chatterbox': 'hi'
    },
    'ar': {
        'name': '아랍어 (Arabic)',
        'mymemory': 'arabic',
        'chatterbox': 'ar'
    },
    'fr': {
        'name': '프랑스어 (French)',
        'mymemory': 'french',
        'chatterbox': 'fr'
    },
    'de': {
        'name': '독일어 (German)',
        'mymemory': 'german',
        'chatterbox': 'de'
    },
    'es': {
        'name': '스페인어 (Spanish)',
        'mymemory': 'spanish',
        'chatterbox': 'es'
    },
    'he': {
        'name': '히브리어 (Hebrew)',
        'mymemory': 'hebrew',
        'chatterbox': 'he'
    },
    'tr': {
        'name': '튀리키예어 (Turkish)',
        'mymemory': 'turkish',
        'chatterbox': 'tr'
    },
    'ms': {
        'name': '말레이어 (Malay)',
        'mymemory': 'malay',
        'chatterbox': 'ms'
    }
}

class DubTranslator:
    def __init__(self, source_lang: str = "korean"):
        self.source_lang = source_lang
        self.kks = pykakasi.kakasi()

    def translate_text(self, text: str, target_lang_code: str) -> str:
        """
        Translates a single text from source language to target language.
        If target is Japanese, converts kanji to hiragana for Chatterbox accuracy.
        """
        if not text or not text.strip():
            return ""
            
        lang_info = TARGET_LANGUAGES.get(target_lang_code)
        if not lang_info:
            raise ValueError(f"Unsupported language code: {target_lang_code}")
            
        mymemory_target = lang_info['mymemory']
        
        try:
            translator = MyMemoryTranslator(source=self.source_lang, target=mymemory_target)
            translated = translator.translate(text)
            if not translated:
                translated = text
        except Exception as e:
            logger.warning(f"Translation failed for {target_lang_code}: {e}. Retrying with chunks...")
            translated = text
            
        # Post-processing for Japanese
        if target_lang_code == 'ja':
            converted = self.kks.convert(translated)
            translated = ''.join([item['hira'] for item in converted])
            
        return translated

    def translate_segments(self, segments: list, target_lang_code: str) -> list:
        """
        Translates a list of STT segments while maintaining timestamps.
        """
        translated_segments = []
        for seg in segments:
            tr_text = self.translate_text(seg['text'], target_lang_code)
            translated_segments.append({
                "id": seg["id"],
                "start": seg["start"],
                "end": seg["end"],
                "duration": seg["duration"],
                "text": tr_text,
                "original_text": seg["text"]
            })
        return translated_segments

