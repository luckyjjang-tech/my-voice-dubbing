import os
import subprocess
import yt_dlp
import logging

# Ensure FFmpeg is accessible
WINGET_LINKS = r"C:\Users\User\AppData\Local\Microsoft\WinGet\Links"
if os.path.exists(WINGET_LINKS) and WINGET_LINKS not in os.environ.get("PATH", ""):
    os.environ["PATH"] = WINGET_LINKS + os.pathsep + os.environ.get("PATH", "")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Downloader")

def download_youtube_media(url: str, output_dir: str):
    """
    Downloads YouTube video and extracts high quality audio using yt-dlp.
    Returns a dictionary containing paths to downloaded media and video metadata.
    """
    os.makedirs(output_dir, exist_ok=True)
    video_output_template = os.path.join(output_dir, "original_video.%(ext)s")
    
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': video_output_template,
        'merge_output_format': 'mp4',
        'noplaylist': True,
        'quiet': False,
        'no_warnings': True,
    }
    
    logger.info(f"Downloading YouTube media from {url}...")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        title = info_dict.get('title', 'video')
        duration = info_dict.get('duration', 0)
        thumbnail = info_dict.get('thumbnail', '')
        
    final_video_path = os.path.join(output_dir, "original_video.mp4")
    
    # Extract clean WAV audio (16kHz or 24kHz) for STT and voice processing
    clean_audio_path = os.path.join(output_dir, "original_audio.wav")
    logger.info(f"Extracting audio track to {clean_audio_path}...")
    
    cmd = [
        'ffmpeg', '-y', '-v', 'error',
        '-i', final_video_path,
        '-vn',
        '-ac', '1',
        '-ar', '24000',
        clean_audio_path
    ]
    subprocess.run(cmd, check=True)
    
    return {
        "title": title,
        "duration": duration,
        "thumbnail": thumbnail,
        "video_path": final_video_path,
        "audio_path": clean_audio_path
    }

def extract_voice_prompt(audio_path: str, output_path: str, start_sec: float = 0.0, duration_sec: float = 20.0):
    """
    Extracts 10~30 seconds clean voice prompt as required by ChatterboxMultilingualTTS:
    Mono, 24kHz WAV.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cmd = [
        'ffmpeg', '-y', '-v', 'error',
        '-ss', str(start_sec),
        '-i', audio_path,
        '-ac', '1',
        '-ar', '24000',
        '-t', str(duration_sec),
        output_path
    ]
    subprocess.run(cmd, check=True)
    return output_path

