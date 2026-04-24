from __future__ import annotations

import asyncio
import re
from typing import Literal


VoiceGender = Literal["male", "female"]


VOICE_MAP: dict[str, str] = {
    "female": "vi-VN-HoaiMyNeural",
    "male": "vi-VN-NamMinhNeural",
}


def synthesize_edge_tts(
    text: str,
    *,
    gender: VoiceGender = "female",
    rate: str = "+0%",
    volume: str = "+0%",
) -> bytes:
    """Synthesize Vietnamese speech using edge-tts and return MP3 bytes.

    Raises RuntimeError when edge-tts is unavailable.
    """

    try:
        import edge_tts
    except Exception as exc:
        raise RuntimeError(
            "edge-tts is not installed. Install with: pip install edge-tts"
        ) from exc

    voice = VOICE_MAP.get(gender, VOICE_MAP["female"])

    def _normalize_text(raw: str) -> str:
        cleaned = re.sub(r"\s+", " ", raw or "").strip()
        return cleaned

    def _split_text(raw: str, max_chars: int = 350) -> list[str]:
        if len(raw) <= max_chars:
            return [raw]
        parts = re.split(r"(?<=[.!?…])\s+", raw)
        chunks: list[str] = []
        buffer: list[str] = []
        size = 0
        for part in parts:
            if not part:
                continue
            if size + len(part) + 1 > max_chars and buffer:
                chunks.append(" ".join(buffer))
                buffer = [part]
                size = len(part)
            else:
                buffer.append(part)
                size += len(part) + 1
        if buffer:
            chunks.append(" ".join(buffer))
        return chunks

    def _run_coroutine(coro: asyncio.Future) -> bytes:
        try:
            return asyncio.run(coro)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            try:
                asyncio.set_event_loop(loop)
                return loop.run_until_complete(coro)
            finally:
                loop.close()
                asyncio.set_event_loop(None)

    async def _synthesize_text_async(text_value: str) -> bytes:
        communicator = edge_tts.Communicate(
            text=text_value,
            voice=voice,
            rate=rate,
            volume=volume,
        )
        audio_chunks: list[bytes] = []
        async for chunk in communicator.stream():
            if chunk.get("type") == "audio":
                audio_data = chunk.get("data")
                if isinstance(audio_data, (bytes, bytearray)):
                    audio_chunks.append(bytes(audio_data))
        return b"".join(audio_chunks)

    normalized = _normalize_text(text)
    if not normalized:
        raise RuntimeError("TTS text is empty.")

    audio = b""
    for _ in range(2):
        audio = _run_coroutine(_synthesize_text_async(normalized))
        if audio:
            return audio

    chunks = _split_text(normalized)
    if len(chunks) > 1:
        audio_parts: list[bytes] = []
        for chunk in chunks:
            audio_chunk = _run_coroutine(_synthesize_text_async(chunk))
            if audio_chunk:
                audio_parts.append(audio_chunk)
        if audio_parts:
            return b"".join(audio_parts)

    raise RuntimeError(
        "Khong nhan duoc audio. Vui long kiem tra ket noi mang va thong so giong doc."
    )
