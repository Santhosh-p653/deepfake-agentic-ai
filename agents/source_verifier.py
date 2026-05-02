from shared.signal import Signal
from shared.logger import get_logger

logger = get_logger("agents.source_verifier")

# Minimum file size thresholds (bytes) — below these is suspicious
MIN_SIZE = {
    ".jpg": 1024,
    ".jpeg": 1024,
    ".png": 512,
    ".mp4": 10240,
}


def verify(preprocessing: Signal) -> Signal:
    logger.info("Source verifier invoked", extra={"status": "called"})

    source = preprocessing.metadata.get("source")

    if not source:
        logger.warning(
            "No source metadata in preprocessing signal",
            extra={"status": "error"}
        )
        return Signal(
            score=0.5,
            reliability=0.0,
            module="agents.source_verifier",
            metadata={"error": "source metadata missing from preprocessing"},
        )

    flags = []
    score = 0.0  # 0.0 = clean, 1.0 = suspicious

    # Check 1 — metadata stripped
    if not source.get("has_metadata", True):
        flags.append("metadata_stripped")
        score += 0.4

    # Check 2 — file suspiciously small
    ext = source.get("extension", "")
    min_size = MIN_SIZE.get(ext, 512)
    file_size = source.get("file_size_bytes", min_size)
    if file_size < min_size:
        flags.append(f"file_too_small ({file_size} bytes)")
        score += 0.3

    # Check 3 — extension mismatch already caught by input_validator
    # but double-check here using the source extension vs signal type
    signal_type = preprocessing.metadata.get("type", "")
    if ext and signal_type and ext != signal_type:
        flags.append(f"extension_mismatch (source={ext} signal={signal_type})")
        score += 0.3

    # Check 4 — no file hash (shouldn't happen, but guard)
    if not source.get("file_hash"):
        flags.append("file_hash_missing")
        score += 0.2

    score = min(round(score, 4), 1.0)

    # Reliability is high — this is deterministic logic
    reliability = 0.8 if not flags else 0.7

    logger.info(
        f"Source verification complete — score={score} flags={flags}",
        extra={"status": "success"}
    )

    return Signal(
        score=score,
        reliability=reliability,
        module="agents.source_verifier",
        metadata={
            "flags": flags,
            "file_hash": source.get("file_hash"),
            "file_size_bytes": file_size,
            "has_metadata": source.get("has_metadata"),
            "extension": ext,
        },
    )
