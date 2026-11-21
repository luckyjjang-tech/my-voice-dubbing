# 🎙️ AI 유튜브 다국어 목소리 더빙 스튜디오 - 작업 보고서 (Work Report)

## 📌 1. 프로젝트 개요 및 목표

본 프로젝트는 유튜브 영상 링크를 입력받아 화자의 고유 목소리 음색을 유지한 채 **11개 국어**(영어, 일본어, 중국어, 힌두어, 아랍어, 프랑스어, 독일어, 스페인어, 히브리어, 튀르키예어, 말레이어)로 자동 번역 및 AI 더빙 음성/영상을 생성하고 다운로드할 수 있는 **풀스택 로컬 AI 웹 애플리케이션**입니다.

### 🎯 핵심 요구사항 구현 현황
1. **유튜브 링크 입력 처리**: `yt-dlp`를 연동하여 최고 화질 영상 및 오디오를 자동으로 추출.
2. **컨텐츠 STT (자막의 보이스, 초 단위 추출)**: `Faster-Whisper`를 활용하여 원본 한국어 음성에서 초 단위(타임스탬프)와 텍스트를 정확하게 추출하고 표준 `SRT` 파일로 생성.
3. **로컬 AI 체터박스(Chatterbox Multilingual) 음성 복제**:
   - 영상에서 10~30초 분량의 깨끗한 음성을 24kHz 모노 포맷(`my_voice.wav`)으로 자동 추출.
   - 원본 화자의 톤/억양을 유지한 채 11개 국어로 음성 합성.
   - **일본어 최적화**: 한자 오독을 방지하도록 `pykakasi`를 통해 자연스러운 히라가나로 자동 변환.
4. **다운로드 가능한 형태 제공**:
   - 언어별 개별 더빙 음성(`WAV`), 더빙 영상(`MP4`), 자막(`SRT`) 다운로드.
   - 모든 결과물을 묶은 원클릭 전체 다운로드(`ZIP`) 패키징.
5. **웹사이트 형태 구축**:
   - `FastAPI` 기반 비동기 백엔드 서버 + `Tailwind CSS` 기반 모던 글래스모피즘 웹 프론트엔드.
   - 원클릭 실행 스크립트(`run_website.bat`).

---

## 🏗️ 시스템 아키텍처 및 모듈 구성

```text
my voice dubbing/
├── .venv/                   # Python 3.11 가상환경 (PyTorch 2.6, Chatterbox-TTS, Faster-Whisper 등)
├── static/
│   └── app.js               # 웹 프론트엔드 비동기 통신, 상태 폴링, 플레이어 제어 스크립트
├── templates/
│   └── index.html           # Tailwind CSS 기반 모던 다크 글래스모피즘 웹 대시보드
├── server.py                # FastAPI 웹 애플리케이션 서버 (REST API & 웹페이지 서빙)
├── downloader.py            # yt-dlp & FFmpeg 기반 영상/오디오 다운로드 및 보이스 샘플 추출
├── stt_transcribe.py        # Faster-Whisper 기반 음성인식(STT) 및 타임스탬프 SRT 생성
├── translator.py            # 11개 국어 번역 엔진 및 일본어 pykakasi 발음 전처리
├── voice_synthesizer.py     # ChatterboxMultilingualTTS 음성 복제 및 FFmpeg 영상 합성
├── pipeline.py              # 전체 파이프라인 자동화 및 ZIP 압축 패키징
├── cli.py                   # 터미널용 명령줄 인터페이스(CLI)
├── app.py                   # Gradio 기반 대체 UI
├── run_website.bat          # 웹사이트 원클릭 자동 실행 스크립트
├── run_webui.bat            # Gradio 웹 UI 실행 스크립트
├── README.md                # 프로젝트 안내 문서
└── WORK_REPORT.md           # 본 작업 보고서
```

---

## 🌐 지원 언어 상세 매핑 (11개 국어)

| 언어명 | 언어 코드 | Chatterbox ID | 특이사항 및 최적화 |
|:---|:---:|:---:|:---|
| **영어 (English)** | `en` | `en` | 글로벌 범용 기본 음성 |
| **일본어 (Japanese)** | `ja` | `ja` | 한자 오독 방지용 `pykakasi` 히라가나 발음 변환 적용 |
| **중국어 (Chinese)** | `zh` | `zh` | 간체자 표준 발음 적용 |
| **힌두어 (Hindi)** | `hi` | `hi` | 데바나가리 문자 음소 매핑 |
| **아랍어 (Arabic)** | `ar` | `ar` | 표준 아랍어(MSA) 억양 적용 |
| **프랑스어 (French)** | `fr` | `fr` | 자연스러운 연음 지원 |
| **독일어 (German)** | `de` | `de` | 명확한 자음 발음 지원 |
| **스페인어 (Spanish)** | `es` | `es` | 표준 에스파냐어 억양 |
| **히브리어 (Hebrew)** | `he` | `he` | 히브리어 음성 합성 |
| **튀르키예어 (Turkish)** | `tr` | `tr` | 튀르키예어 모음 조화 반영 |
| **말레이어 (Malay)** | `ms` | `ms` | 표준 말레이어 지원 |

---

## ⚙️ 주요 핵심 로직 설명

### 1. 유튜브 다운로드 및 보이스 추출 (`downloader.py`)
- `yt_dlp.YoutubeDL`을 통해 비디오와 오디오 트랙을 고음질로 다운로드.
- `ffmpeg`를 호출하여 모노, 24kHz, 10~30초 구간을 잘라내어 Chatterbox 레퍼런스 규격(`my_voice.wav`)으로 자동 변환.

### 2. 타임스탬프 STT 추출 (`stt_transcribe.py`)
- `faster_whisper.WhisperModel`의 VAD(Voice Activity Detection) 필터를 적용하여 잡음을 제거하고 각 발화 구간의 시작/종료 초(`start`, `end`) 및 텍스트를 정확하게 추출.
- `format_timestamp()`를 통해 표준 자막 파일(`subtitles_ko.srt`) 생성.

### 3. 다국어 번역 및 일본어 전처리 (`translator.py`)
- `deep_translator` 엔진을 연동하여 11개 대상 언어로 번역.
- 일본어 번역문의 경우 `pykakasi`를 적용하여 형태소별 한자를 히라가나로 변환, 음성 모델이 어색한 한자 음독을 읽는 문제를 해결.

### 4. Chatterbox AI 음성 복제 및 비디오 합성 (`voice_synthesizer.py`)
- `ChatterboxMultilingualTTS.from_pretrained(device=DEVICE)` 모델 활용.
- 긴 문장의 경우 자연스러운 어절 단위로 자동 분할 합성 후 병합.
- `AudioSegment`를 통해 원본 영상의 타임라인(초 단위)에 맞춰 무음(Silence) 패딩과 함께 정밀 동기화.
- `ffmpeg` 스트림 복사(`-c:v copy -c:a aac`)를 통해 원본 화질 손실 없이 고속으로 더빙 비디오(`dubbed_{lang}.mp4`) 생성.

### 5. FastAPI 비동기 웹 서버 & 모던 웹 UI (`server.py`, `templates/index.html`)
- 실시간 영상 정보 미리보기 API (`/api/video-info`).
- 백그라운드 스레드에서 더빙 작업을 수행하고 프론트엔드에서 1.2초 주기로 상태를 폴링하여 0~100% 프로그레스 바와 터미널 로그를 실시간 갱신.
- 결과 룸에서 내 목소리 청취, STT 자막 표 확인, 언어별 탭 전환식 플레이어(오디오/영상) 및 개별/전체 다운로드 제공.

---

## 🚀 실행 방법

### 웹사이트 실행 (가장 추천)
폴더 내의 **`run_website.bat`** 파일을 더블클릭합니다.
서버가 켜지고 브라우저(`http://localhost:8000`)가 자동으로 열립니다.

### 터미널 CLI 실행
```powershell
.\.venv\Scripts\python.exe cli.py --url "https://www.youtube.com/watch?v=..." --langs en,ja,zh
```
