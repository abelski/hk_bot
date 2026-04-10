import os
import re
import subprocess
import tempfile

from helpers.translation_helper import translate_to_russian


def process_youtube_video(url: str, video_bytes: bytes) -> bytes | None:
    """Extract subtitles (or transcribe), translate to Russian, burn into video.
    Returns processed video bytes, or None if any step fails."""
    from helpers.youtube_helper import extract_subtitles_vtt
    srt = None
    vtt = extract_subtitles_vtt(url)
    if vtt:
        srt = _vtt_to_translated_srt(vtt)
    if not srt:
        srt = _whisper_to_translated_srt(video_bytes)
    if not srt:
        return None
    return burn_subtitles(video_bytes, srt)


def burn_subtitles(video_bytes: bytes, srt_content: str) -> bytes | None:
    """Burn SRT subtitles into video using ffmpeg. Returns processed bytes or None."""
    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, "input.mp4")
        srt_path = os.path.join(tmpdir, "subs.srt")
        output_path = os.path.join(tmpdir, "output.mp4")
        with open(video_path, "wb") as f:
            f.write(video_bytes)
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vf", f"subtitles={srt_path}:force_style='FontName=DejaVu Sans,FontSize=18,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=2,Shadow=1'",
            "-c:a", "copy",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=300)
        if result.returncode != 0:
            return None
        with open(output_path, "rb") as f:
            return f.read()


def _vtt_to_translated_srt(vtt_text: str) -> str | None:
    """Parse VTT with timing, translate each segment to Russian, return SRT string."""
    segments = _parse_vtt_segments(vtt_text)
    if not segments:
        return None
    srt_lines = []
    for i, (start, end, text) in enumerate(segments, 1):
        translated = translate_to_russian(text) or text
        srt_lines.append(f"{i}\n{start} --> {end}\n{translated}\n")
    return "\n".join(srt_lines)


def _parse_vtt_segments(vtt_text: str) -> list:
    """Parse VTT into list of (start_srt, end_srt, text) tuples, deduplicated."""
    segments = []
    seen_texts = set()
    lines = vtt_text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if "-->" in line:
            timing = re.sub(r"\s+(align|position|line|size):\S+", "", line)
            parts = timing.split("-->")
            if len(parts) == 2:
                start = _vtt_time_to_srt(parts[0].strip())
                end = _vtt_time_to_srt(parts[1].strip())
                i += 1
                text_lines = []
                while i < len(lines) and lines[i].strip():
                    cleaned = re.sub(r"<[^>]+>", "", lines[i]).strip()
                    if cleaned:
                        text_lines.append(cleaned)
                    i += 1
                text = " ".join(text_lines).strip()
                if text and text not in seen_texts:
                    seen_texts.add(text)
                    segments.append((start, end, text))
                continue
        i += 1
    return segments


def _vtt_time_to_srt(vtt_time: str) -> str:
    """Convert VTT timestamp (00:00:01.000) to SRT format (00:00:01,000)."""
    return vtt_time.replace(".", ",")


def _whisper_to_translated_srt(video_bytes: bytes) -> str | None:
    """Transcribe with faster-whisper, translate segments, return SRT or None."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None

    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, "video.mp4")
        audio_path = os.path.join(tmpdir, "audio.wav")
        with open(video_path, "wb") as f:
            f.write(video_bytes)
        cmd = ["ffmpeg", "-y", "-i", video_path, "-vn", "-ar", "16000", "-ac", "1", audio_path]
        result = subprocess.run(cmd, capture_output=True, timeout=60)
        if result.returncode != 0:
            return None
        try:
            model = WhisperModel("tiny", device="cpu", compute_type="int8")
            segments, _ = model.transcribe(audio_path, beam_size=1)
            srt_lines = []
            for i, seg in enumerate(segments, 1):
                start = _seconds_to_srt(seg.start)
                end = _seconds_to_srt(seg.end)
                translated = translate_to_russian(seg.text.strip()) or seg.text.strip()
                srt_lines.append(f"{i}\n{start} --> {end}\n{translated}\n")
            return "\n".join(srt_lines) if srt_lines else None
        except Exception:
            return None


def _seconds_to_srt(seconds: float) -> str:
    """Convert float seconds to SRT timestamp (HH:MM:SS,mmm)."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
