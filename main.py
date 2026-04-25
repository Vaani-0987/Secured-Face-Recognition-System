import json
import os
import time
from pathlib import Path

import cv2
import tkinter as tk
from tkinter import simpledialog, messagebox

from access_control import grant_access, deny_access
from config import (
    DATASET_DIR,
    TRAINER_PATH,
    LABELS_PATH,
    RECOGNITION_CONFIDENCE_THRESHOLD,
    PINS_PATH,
)
_root: tk.Tk | None = None
_pins_cache: dict[str, str] | None = None

LIVENESS_WINDOW_SECONDS = 5.0
LIVENESS_MIN_MOVEMENT_PIXELS = 15.0
DECISION_COOLDOWN_SECONDS = 3.0
ENABLE_LIVENESS_CHECK = True
LIVENESS_RESET_IF_NOT_SEEN_SECONDS = 0.8
ENABLE_PIN_CHECK = True

# Show debug numbers in the video overlay (helps tune threshold / liveness)
SHOW_DEBUG_OVERLAY = True


def get_root() -> tk.Tk:
    global _root
    if _root is None:
        _root = tk.Tk()
        _root.withdraw()
    return _root


def load_labels() -> dict | None:
    if not os.path.exists(LABELS_PATH):
        return None
    with open(LABELS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_recognizer():
    if not os.path.exists(TRAINER_PATH):
        return None
    recognizer = cv2.face.LBPHFaceRecognizer_create()
    recognizer.read(TRAINER_PATH)
    return recognizer


def ensure_dataset_exists() -> bool:
    return Path(DATASET_DIR).exists()


def load_pins() -> dict[str, str]:
    global _pins_cache
    if _pins_cache is not None:
        return _pins_cache
    if os.path.exists(PINS_PATH):
        with open(PINS_PATH, "r", encoding="utf-8") as f:
            _pins_cache = json.load(f)
    else:
        _pins_cache = {}
    return _pins_cache


def save_pins(pins: dict[str, str]) -> None:
    os.makedirs(os.path.dirname(PINS_PATH), exist_ok=True)
    with open(PINS_PATH, "w", encoding="utf-8") as f:
        json.dump(pins, f, indent=2)


def set_pin_for_user(name: str) -> str | None:
    root = get_root()
    while True:
        pin1 = simpledialog.askstring("Set PIN", f"Set new PIN for {name}:", show="*", parent=root)
        if pin1 is None:
            return None
        pin2 = simpledialog.askstring("Confirm PIN", "Confirm PIN:", show="*", parent=root)
        if pin2 is None:
            return None
        if pin1 != pin2:
            messagebox.showerror("PIN mismatch", "PINs do not match, please try again.", parent=root)
            continue
        if not pin1:
            messagebox.showerror("Invalid PIN", "PIN cannot be empty.", parent=root)
            continue
        return pin1


def prompt_pin(name: str) -> str | None:
    root = get_root()
    return simpledialog.askstring("Enter PIN", f"Enter PIN for {name}:", show="*", parent=root)


def show_welcome_screen(name: str) -> None:
    root = get_root()
    root.deiconify()
    root.title("Welcome")

    # Clear any previous widgets
    for widget in root.winfo_children():
        widget.destroy()

    label = tk.Label(root, text=f"Welcome, {name}!", font=("Arial", 28))
    label.pack(padx=40, pady=40)

    subtitle = tk.Label(
        root,
        text="Access Granted to Secure Area",
        font=("Arial", 16),
    )
    subtitle.pack(pady=(0, 30))

    close_btn = tk.Button(root, text="Close", font=("Arial", 14), command=root.destroy)
    close_btn.pack(pady=10)

    root.mainloop()


def should_emit_decision(
    last_emitted: dict[tuple[str, str], float],
    name: str,
    decision: str,
    now: float,
    cooldown_seconds: float = DECISION_COOLDOWN_SECONDS,
) -> bool:
    key = (name, decision)
    last = last_emitted.get(key)
    if last is not None and now - last < cooldown_seconds:
        return False
    last_emitted[key] = now
    return True


def main() -> None:
    if not ensure_dataset_exists():
        print("Dataset directory not found. Please run enroll.py first.")
        return

    labels = load_labels()
    if not labels:
        print("No labels found. Please run enroll.py to enroll at least one user.")
        return

    recognizer = load_recognizer()
    if recognizer is None:
        print("Trained model not found. Please run enroll.py to train the recognizer.")
        return

    # Map numeric IDs to names
    id_to_name = {int(k): v for k, v in labels.items()}

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    # Try DirectShow backend first (often more stable than default MSMF on Windows)
    cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cam.isOpened():
        cam = cv2.VideoCapture(0)

    if not cam.isOpened():
        print("Error: Could not open camera.")
        return

    print("Starting access control loop. Press 'q' to quit.")

    last_grant_time = 0.0
    granted_duration = 0.0
    current_status = "Idle"
    current_name = ""
    pins = load_pins()
    liveness_state: dict[str, dict[str, object]] = {}
    last_emitted_decisions: dict[tuple[str, str], float] = {}

    while True:
        ret, frame = cam.read()
        if not ret:
            # If a frame fails, skip this iteration but keep the window open
            print("Warning: failed to read frame from camera.")
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(100, 100))

        name_to_display = "Unknown"
        status_to_display = "Access Denied"

        if len(faces) > 0:
            for (x, y, w, h) in faces:
                face_img = gray[y:y + h, x:x + w]

                label_id, confidence = recognizer.predict(face_img)

                if confidence < RECOGNITION_CONFIDENCE_THRESHOLD and label_id in id_to_name:
                    recognized_name = id_to_name[label_id]
                    now = time.time()

                    if ENABLE_LIVENESS_CHECK:
                        # --- Liveness: collect movement for a fixed time window, then decide ---
                        cx = x + w / 2.0
                        cy = y + h / 2.0

                        state = liveness_state.get(recognized_name)
                        if state is None:
                            state = {
                                "start": now,
                                "last_seen": now,
                                "points": [(now, cx, cy)],
                            }
                            liveness_state[recognized_name] = state
                        else:
                            last_seen = float(state.get("last_seen", now))  # type: ignore[arg-type]
                            if now - last_seen > LIVENESS_RESET_IF_NOT_SEEN_SECONDS:
                                # Face/name wasn't stable in view; restart the liveness window.
                                state["start"] = now
                                state["points"] = [(now, cx, cy)]
                            else:
                                points = list(state.get("points", []))  # type: ignore[arg-type]
                                points.append((now, cx, cy))
                                state["points"] = points
                            state["last_seen"] = now

                        start = float(state["start"])  # type: ignore[arg-type]
                        elapsed = now - start
                        if elapsed < LIVENESS_WINDOW_SECONDS:
                            name_to_display = recognized_name
                            status_to_display = "Checking liveness..."
                            current_status = status_to_display
                            current_name = recognized_name
                            continue

                        points = list(state.get("points", []))  # type: ignore[arg-type]
                        if len(points) >= 2:
                            xs = [p[1] for p in points]
                            ys = [p[2] for p in points]
                            movement = ((max(xs) - min(xs)) ** 2 + (max(ys) - min(ys)) ** 2) ** 0.5
                        else:
                            movement = 0.0

                        # Reset so next attempt can re-check liveness cleanly
                        liveness_state.pop(recognized_name, None)

                        if movement < LIVENESS_MIN_MOVEMENT_PIXELS:
                            name_to_display = recognized_name
                            status_to_display = "Access Denied (liveness failed)"
                            if should_emit_decision(last_emitted_decisions, recognized_name, "DENIED", now):
                                deny_access(recognized_name, confidence)
                            current_status = status_to_display
                            current_name = recognized_name
                            continue

                    # If PIN check is disabled, decide immediately after recognition (+ optional liveness)
                    if not ENABLE_PIN_CHECK:
                        name_to_display = recognized_name
                        status_to_display = "Access Granted"
                        if now - last_grant_time > granted_duration:
                            if should_emit_decision(last_emitted_decisions, recognized_name, "GRANTED", now):
                                granted_duration = grant_access(recognized_name, confidence)
                                last_grant_time = now
                        current_status = "Access Granted"
                        current_name = recognized_name
                        continue

                    # If this user already has an active granted period, don't ask for PIN again
                    if (
                        recognized_name == current_name
                        and now - last_grant_time <= granted_duration
                        and current_status.startswith("Access Granted")
                    ):
                        name_to_display = recognized_name
                        status_to_display = "Access Granted"
                        continue

                    # Multi-factor: first time user sets a PIN, then must enter it
                    # --- Multi-factor: PIN check (after liveness passes) ---
                    if recognized_name not in pins:
                        new_pin = set_pin_for_user(recognized_name)
                        if new_pin is None:
                            name_to_display = recognized_name
                            status_to_display = "Access Denied"
                            if should_emit_decision(last_emitted_decisions, recognized_name, "DENIED", now):
                                deny_access(recognized_name, confidence)
                            current_status = "Access Denied (no PIN set)"
                            current_name = recognized_name
                            continue
                        pins[recognized_name] = new_pin
                        save_pins(pins)

                    entered_pin = prompt_pin(recognized_name)
                    if entered_pin is None:
                        name_to_display = recognized_name
                        status_to_display = "Access Denied"
                        if should_emit_decision(last_emitted_decisions, recognized_name, "DENIED", now):
                            deny_access(recognized_name, confidence)
                        current_status = "Access Denied (PIN cancelled)"
                        current_name = recognized_name
                    elif entered_pin == pins[recognized_name]:
                        name_to_display = recognized_name
                        status_to_display = "Access Granted"

                        # Grant access only if not already recently granted
                        if now - last_grant_time > granted_duration:
                            if should_emit_decision(last_emitted_decisions, recognized_name, "GRANTED", now):
                                granted_duration = grant_access(recognized_name, confidence)
                                last_grant_time = now
                        current_status = "Access Granted"
                        current_name = recognized_name
                    else:
                        name_to_display = recognized_name
                        status_to_display = "Access Denied"
                        if should_emit_decision(last_emitted_decisions, recognized_name, "DENIED", now):
                            deny_access(recognized_name, confidence)
                        current_status = "Access Denied (wrong PIN)"
                        current_name = recognized_name
                else:
                    now = time.time()
                    name_to_display = "Unknown"
                    status_to_display = "Access Denied"
                    if should_emit_decision(last_emitted_decisions, "Unknown", "DENIED", now):
                        deny_access("Unknown", confidence)
                    current_status = "Access Denied"
                    current_name = "Unknown"

                # Draw rectangle and text for each detected face
                color = (0, 255, 0) if status_to_display == "Access Granted" else (0, 0, 255)
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                cv2.putText(frame, name_to_display, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                cv2.putText(
                    frame,
                    status_to_display,
                    (x, y + h + 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    color,
                    2,
                )
                if SHOW_DEBUG_OVERLAY:
                    dbg = f"conf={confidence:.1f} thr={RECOGNITION_CONFIDENCE_THRESHOLD:.1f}"
                    cv2.putText(frame, dbg, (x, y + h + 55), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 0), 2)

        # Overall status bar at top
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 40), (50, 50, 50), -1)
        status_text = f"Status: {current_status} ({current_name})"
        cv2.putText(frame, status_text, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        cv2.imshow("Face Recognition Access Control - Press 'q' to quit", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cam.release()
    cv2.destroyAllWindows()

    # If access was granted, show a welcome page
    if current_status.startswith("Access Granted") and current_name:
        show_welcome_screen(current_name)


if __name__ == "__main__":
    main()

