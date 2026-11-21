import os
import gradio as gr
from translator import TARGET_LANGUAGES
from pipeline import DubbingPipeline

pipeline = None

def get_pipeline():
    global pipeline
    if pipeline is None:
        pipeline = DubbingPipeline(whisper_model="base")
    return pipeline

def run_dubbing_process(
    youtube_url: str,
    selected_langs: list,
    voice_start: float,
    voice_duration: float,
    progress=gr.Progress(track_tqdm=True)
):
    if not youtube_url or not youtube_url.strip():
        return (
            "⚠️ 유튜브 링크를 입력해 주세요.",
            None,  # voice sample
            None,  # zip file
            None,  # df preview
            gr.update(visible=False), # audio container
            gr.update(visible=False), # video container
        )

    if not selected_langs:
        return (
            "⚠️ 더빙을 진행할 언어를 최소 1개 이상 선택해 주세요.",
            None, None, None,
            gr.update(visible=False),
            gr.update(visible=False),
        )

    try:
        def update_ui_progress(pct, msg):
            progress(pct, desc=msg)

        app_pipeline = get_pipeline()
        
        # Clean safe folder name for output
        output_dir = os.path.abspath("dubbing_output")
        os.makedirs(output_dir, exist_ok=True)
        
        results = app_pipeline.run(
            youtube_url=youtube_url.strip(),
            target_langs=selected_langs,
            voice_start_sec=float(voice_start),
            voice_duration=float(voice_duration),
            output_base_dir=output_dir,
            progress_callback=update_ui_progress
        )

        # Build table data of segments
        segments_data = []
        for seg in results.get("segments", []):
            segments_data.append([
                seg["id"],
                f"{seg['start']}s ~ {seg['end']}s",
                seg["text"]
            ])

        status_msg = f"""### ✅ 더빙 완료!
- **영상 제목**: {results.get('title', 'YouTube Video')}
- **영상 길이**: {int(results.get('duration', 0))}초
- **생성된 언어**: {', '.join([TARGET_LANGUAGES[l]['name'] for l in selected_langs if l in TARGET_LANGUAGES])}
- **압축 파일**: 모든 오디오/영상/자막 파일이 아래 ZIP에 담겨 있습니다.
"""

        zip_file = results.get("zip_path")
        voice_sample = results.get("voice_sample")

        # Pick first available language for preview player
        first_lang = selected_langs[0] if selected_langs else 'en'
        lang_data = results["languages"].get(first_lang, {})
        audio_preview = lang_data.get("audio_path")
        video_preview = lang_data.get("video_path")

        return (
            status_msg,
            voice_sample,
            zip_file,
            segments_data,
            gr.update(value=audio_preview, visible=True),
            gr.update(value=video_preview, visible=True)
        )

    except Exception as e:
        import traceback
        err_msg = f"❌ 처리 중 오류가 발생했습니다: {str(e)}\n\n{traceback.format_exc()}"
        return (
            err_msg,
            None, None, None,
            gr.update(visible=False),
            gr.update(visible=False)
        )

# Gradio Interface Customization
theme = gr.themes.Soft(
    primary_hue="blue",
    secondary_hue="slate"
)

lang_choices = [(info['name'], code) for code, info in TARGET_LANGUAGES.items()]
default_langs = list(TARGET_LANGUAGES.keys())

with gr.Blocks(theme=theme, title="AI 유튜브 다국어 목소리 더빙 스튜디오") as demo:
    gr.Markdown("""
    # 🎙️ AI 유튜브 다국어 목소리 더빙 스튜디오
    ### 유튜브 영상에서 내 목소리를 복제하여 **11개 국어**(영어, 일본어, 중국어, 힌두어, 아랍어 등)로 자동 더빙 & 다운로드
    """)

    with gr.Row():
        with gr.Column(scale=4):
            yt_url_input = gr.Textbox(
                label="📺 1. 유튜브 링크 입력",
                placeholder="https://www.youtube.com/watch?v=...",
                lines=1
            )
            with gr.Accordion("⚙️ 목소리 추출 세부 설정 (내 목소리 구간)", open=False):
                with gr.Row():
                    voice_start_slider = gr.Slider(
                        minimum=0, maximum=120, value=0, step=1,
                        label="목소리 추출 시작 지점 (초)",
                        info="영상에서 깨끗하게 말소리가 나오는 시작 초"
                    )
                    voice_duration_slider = gr.Slider(
                        minimum=10, maximum=30, value=20, step=1,
                        label="목소리 추출 길이 (초)",
                        info="Chatterbox 권장: 10~30초 (모노 24kHz로 자동 변환)"
                    )

            target_langs_checkbox = gr.CheckboxGroup(
                choices=lang_choices,
                value=default_langs,
                label="🌐 2. 생성할 언어 선택 (한국어 -> 다국어)",
                info="선택한 언어별로 각각 목소리가 생성됩니다."
            )

            with gr.Row():
                select_all_btn = gr.Button("전체 선택", size="sm")
                deselect_all_btn = gr.Button("전체 해제", size="sm")

            submit_btn = gr.Button("🚀 AI 다국어 더빙 시작하기", variant="primary", size="lg")

        with gr.Column(scale=3):
            status_box = gr.Markdown("준비 완료. 유튜브 링크를 입력하고 시작 버튼을 눌러주세요.")
            
            with gr.Group():
                gr.Markdown("#### 📥 결과 다운로드")
                zip_download = gr.File(label="모든 결과물 전체 다운로드 (.ZIP)", file_count="single")
                
            with gr.Group():
                gr.Markdown("#### 👤 추출된 내 목소리 레퍼런스")
                voice_audio_preview = gr.Audio(label="My Voice Sample (24kHz Mono)", type="filepath")

    with gr.Row():
        with gr.Column(scale=1):
            audio_preview_comp = gr.Audio(label="🎧 생성된 다국어 더빙 음성 미리듣기", visible=False)
        with gr.Column(scale=1):
            video_preview_comp = gr.Video(label="🎬 생성된 다국어 더빙 영상 미리보기", visible=False)

    with gr.Accordion("📝 인식된 컨텐츠 STT 자막 (보이스 및 초 단위)", open=True):
        stt_table = gr.Dataframe(
            headers=["번호", "시간 구간 (초)", "한국어 자막 내용"],
            datatype=["number", "str", "str"],
            label="컨텐츠 STT 타임스탬프 자막"
        )

    # Event handlers for Select/Deselect all
    def select_all():
        return default_langs

    def deselect_all():
        return []

    select_all_btn.click(select_all, outputs=target_langs_checkbox)
    deselect_all_btn.click(deselect_all, outputs=target_langs_checkbox)

    submit_btn.click(
        fn=run_dubbing_process,
        inputs=[
            yt_url_input,
            target_langs_checkbox,
            voice_start_slider,
            voice_duration_slider
        ],
        outputs=[
            status_box,
            voice_audio_preview,
            zip_download,
            stt_table,
            audio_preview_comp,
            video_preview_comp
        ]
    )

if __name__ == "__main__":
    demo.queue().launch(server_name="127.0.0.1", server_port=7860, share=False, inbrowser=True)

