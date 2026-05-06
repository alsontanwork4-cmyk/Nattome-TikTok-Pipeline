# Use Evidence-First Video Analysis Tool Stack

The TikTok OCR pipeline will use evidence-first analysis: downloaded videos, extracted frames, OCR, speech transcript, audio/music review, and metadata must feed the creative report. The default tool stack is Apify for TikTok discovery/download, FFmpeg for video/audio extraction, PaddleOCR as primary OCR, Tesseract as fallback, Whisper-style multilingual transcription, and markdown, JSON, and XLSX outputs. This is heavier than metadata-only analysis, but it prevents unsupported claims about hooks, pacing, subtitles, and on-screen content.
