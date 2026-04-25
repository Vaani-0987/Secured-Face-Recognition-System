import json
import os
import sys
from pathlib import Path

import cv2
import numpy as np

from config import DATASET_DIR, TRAINER_PATH, LABELS_PATH, IMAGES_PER_USER


def ensure_directories() -> None:
    Path(DATASET_DIR).mkdir(parents=True, exist_ok=True)
    Path(os.path.dirname(TRAINER_PATH)).mkdir(parents=True, exist_ok=True)


def load_labels() -> dict:
    if os.path.exists(LABELS_PATH):
        with open(LABELS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_labels(labels: dict) -> None:
    Path(os.path.dirname(LABELS_PATH)).mkdir(parents=True, exist_ok=True)
    with open(LABELS_PATH, "w", encoding="utf-8") as f:
        json.dump(labels, f, indent=2)


def get_or_create_label_id(labels: dict, name: str) -> int:
    # Invert mapping: name -> id
    name_to_id = {v: int(k) for k, v in labels.items()}
    if name in name_to_id:
        return name_to_id[name]
    new_id = max(name_to_id.values(), default=-1) + 1
    labels[str(new_id)] = name
    return new_id


def capture_images_for_user(name: str, label_id: int) -> None:
    dataset_path = Path(DATASET_DIR) / name
    dataset_path.mkdir(parents=True, exist_ok=True)

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    cam = cv2.VideoCapture(0)

    if not cam.isOpened():
        print("Error: Could not open camera.")
        return

    print("Camera opened. Look at the camera.")
    print(f"Capturing {IMAGES_PER_USER} face images for user: {name}")
    count = 0

    while True:
        ret, frame = cam.read()
        if not ret:
            print("Failed to capture frame from camera. Exiting.")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(100, 100))

        for (x, y, w, h) in faces:
            count += 1
            face_img = gray[y:y + h, x:x + w]
            img_path = dataset_path / f"user_{label_id}_{count}.jpg"
            cv2.imwrite(str(img_path), face_img)

            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(frame, f"{name} #{count}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            print(f"Captured image {count}/{IMAGES_PER_USER}")

            if count >= IMAGES_PER_USER:
                break

        cv2.imshow("Enrollment - Press ESC to cancel", frame)
        key = cv2.waitKey(1) & 0xFF
        if key == 27:  # ESC key
            print("Enrollment cancelled by user.")
            break

        if count >= IMAGES_PER_USER:
            print("Finished capturing images.")
            break

    cam.release()
    cv2.destroyAllWindows()


def train_recognizer() -> None:
    print("Training recognizer from dataset...")

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    face_samples = []
    ids = []

    labels = load_labels()
    # name -> id mapping
    name_to_id = {v: int(k) for k, v in labels.items()}

    for name, label_id in name_to_id.items():
        person_dir = Path(DATASET_DIR) / name
        if not person_dir.exists():
            continue
        for img_file in person_dir.glob("*.jpg"):
            img = cv2.imread(str(img_file), cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            face_samples.append(img)
            ids.append(label_id)

    if not face_samples:
        print("No training images found. Please enroll at least one user.")
        return

    recognizer.train(face_samples, np.array(ids))
    recognizer.write(TRAINER_PATH)
    print(f"Training complete. Model saved to {TRAINER_PATH}")


def main() -> None:
    ensure_directories()

    name = (" ".join(sys.argv[1:]).strip() if len(sys.argv) > 1 else "").strip()
    if not name:
        name = input("Enter user name to enroll: ").strip()
    if not name:
        print("Name cannot be empty.")
        return

    labels = load_labels()
    label_id = get_or_create_label_id(labels, name)
    save_labels(labels)

    capture_images_for_user(name, label_id)
    train_recognizer()


if __name__ == "__main__":
    main()

