import csv
import os
from datetime import datetime
import json

from config import LOG_PATH, ACCESS_GRANTED_DURATION, STATUS_PATH


def ensure_log_dir_exists() -> None:
    directory = os.path.dirname(LOG_PATH)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


def write_status(name: str, decision: str, confidence: float | None) -> None:
    """
    Write the latest decision for the UI to display.
    """
    directory = os.path.dirname(STATUS_PATH)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

    payload = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "name": name,
        "decision": decision,
        "confidence": (round(float(confidence), 2) if confidence is not None else None),
    }
    with open(STATUS_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def log_access(name: str, decision: str, confidence: float | None) -> None:
    """
    Append an access attempt to the CSV log file.

    decision: "GRANTED" or "DENIED"
    confidence: LBPH confidence value (lower is better). Can be None if no prediction.
    """
    ensure_log_dir_exists()
    header = ["timestamp", "name", "decision", "confidence"]
    file_exists = os.path.exists(LOG_PATH)

    with open(LOG_PATH, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(header)
        timestamp = datetime.now().isoformat(timespec="seconds")
        writer.writerow([timestamp, name, decision, f"{confidence:.2f}" if confidence is not None else ""])


def grant_access(name: str, confidence: float) -> float:
    """
    Handle access granted event.
    Returns the duration (seconds) for which access is considered granted,
    so the caller can simulate a door unlock period.
    """
    print(f"[ACCESS GRANTED] {name} (confidence={confidence:.2f})")
    log_access(name=name, decision="GRANTED", confidence=confidence)
    write_status(name=name, decision="GRANTED", confidence=confidence)
    return ACCESS_GRANTED_DURATION


def deny_access(name: str, confidence: float | None) -> None:
    """
    Handle access denied event.
    """
    display_name = name or "Unknown"
    print(f"[ACCESS DENIED] {display_name} (confidence={confidence:.2f})" if confidence is not None else
          f"[ACCESS DENIED] {display_name}")
    log_access(name=display_name, decision="DENIED", confidence=confidence)
    write_status(name=display_name, decision="DENIED", confidence=confidence)
