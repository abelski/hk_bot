import os
import subprocess
import tempfile

from helpers.translation_helper import translate_to_russian


def process_youtube_video(url: str, video_bytes: bytes) -> bytes | None:
    """Full pipeline: extract subtitles (or transcribe), translate, add voiceover.
    Returns processed video bytes, or None if any step fails."""
    from helpers.youtube_helper import extract_subtitles
    transcript = extract_subtitles(url)
    if not transcript:
        transcript = transcribe_video(video_bytes)
    if not transcript:
        return None
    return add_russian_voiceover(video_bytes, transcript)


def transcribe_video(video_bytes: bytes) -> str | None:
    """Transcribe video audio via faster-whisper tiny model. Returns plain text or None."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None

    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, "video.mp4")
        audio_path = os.path.join(tmpdir, "audio.wav")
        with open(video_path, "wb") as f:
            f.write(video_bytes)
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vn", "-ar", "16000", "-ac", "1", audio_path,
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        if result.returncode != 0:
            return None
        try:
            model = WhisperModel("tiny", device="cpu", compute_type="int8")
            segments, _ = model.transcribe(audio_path, beam_size=1)
            text = " ".join(seg.text.strip() for seg in segments)
            return text.strip() or None
        except Exception:
            return None


def add_russian_voiceover(video_bytes: bytes, text_en: str) -> bytes | None:
    """Translate text to Russian, generate TTS, mix into video. Returns bytes or None."""
    text_ru = translate_to_russian(text_en)
    if not text_ru:
        return None
    audio_bytes = _generate_tts(text_ru)
    if not audio_bytes:
        return None
    return _mix_audio(video_bytes, audio_bytes)


def _generate_tts(text: str) -> bytes | None:
    """Generate Russian TTS MP3 bytes using gTTS (Google TTS, free, requires internet)."""
    try:
        import io
        from gtts import gTTS
        buf = io.BytesIO()
        gTTS(text=text, lang="ru", slow=False).write_to_fp(buf)
        return buf.getvalue()
    except Exception:
        return None


def _mix_audio(video_bytes: bytes, audio_bytes: bytes) -> bytes | None:
    """Replace video audio with TTS audio using ffmpeg. Returns processed video bytes or None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, "input.mp4")
        audio_path = os.path.join(tmpdir, "tts.mp3")
        output_path = os.path.join(tmpdir, "output.mp4")
        with open(video_path, "wb") as f:
            f.write(video_bytes)
        with open(audio_path, "wb") as f:
            f.write(audio_bytes)
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path, "-i", audio_path,
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if result.returncode != 0:
            return None
        with open(output_path, "rb") as f:
            return f.read()
