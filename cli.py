import argparse
import sys
from pipeline import DubbingPipeline
from translator import TARGET_LANGUAGES

def main():
    parser = argparse.ArgumentParser(description="YouTube AI Multilingual Dubbing CLI with Chatterbox")
    parser.add_argument("--url", type=str, required=True, help="YouTube video URL")
    parser.add_argument("--langs", type=str, default="en,ja,zh,hi,ar,fr,de,es,he,tr,ms",
                        help="Comma-separated target language codes (default: all 11 languages)")
    parser.add_argument("--voice_start", type=float, default=0.0,
                        help="Start offset in seconds for extracting voice sample (default: 0.0)")
    parser.add_argument("--voice_duration", type=float, default=20.0,
                        help="Duration in seconds of voice sample (default: 20.0)")
    parser.add_argument("--output_dir", type=str, default="dubbing_output",
                        help="Output directory path (default: dubbing_output)")

    args = parser.parse_args()

    selected_langs = [l.strip() for l in args.langs.split(",") if l.strip()]
    invalid_langs = [l for l in selected_langs if l not in TARGET_LANGUAGES]
    if invalid_langs:
        print(f"Error: Unknown language codes: {invalid_langs}")
        print(f"Available codes: {list(TARGET_LANGUAGES.keys())}")
        sys.exit(1)

    print("="*60)
    print("🎙️ AI 유튜브 다국어 목소리 더빙 시작")
    print(f"URL: {args.url}")
    print(f"언어 목록: {selected_langs}")
    print(f"출력 경로: {args.output_dir}")
    print("="*60)

    pipeline = DubbingPipeline(whisper_model="base")
    results = pipeline.run(
        youtube_url=args.url,
        target_langs=selected_langs,
        voice_start_sec=args.voice_start,
        voice_duration=args.voice_duration,
        output_base_dir=args.output_dir
    )

    print("\n" + "="*60)
    print("🎉 더빙 완료!")
    print(f"📦 전체 결과 압축 파일: {results.get('zip_path')}")
    for lang, data in results.get("languages", {}).items():
        print(f"  - [{lang}] {data['name']}")
        print(f"      자막: {data['srt_path']}")
        print(f"      오디오: {data['audio_path']}")
        if data.get('video_path'):
            print(f"      영상: {data['video_path']}")
    print("="*60)

if __name__ == "__main__":
    main()

