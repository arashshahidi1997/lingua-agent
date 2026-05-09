"""Voice-mode Protocols (Phase 9 — no implementation in MVP).

Mirroring Discute's STT → LLM → TTS seam from day one keeps the agent code
clean: `tutor/agent.py` will accept optional STT/TTS providers without
caring whether they're real or mocked.
"""
from .stt import STTProvider, TranscriptionResult
from .tts import SynthesisResult, TTSProvider

__all__ = ["STTProvider", "TranscriptionResult", "TTSProvider", "SynthesisResult"]
