import json
import os

import cv2

from config import DATASET_DIR, TRAINER_PATH, LABELS_PATH, RECOGNITION_CONFIDENCE_THRESHOLD


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


def main() -> None:
    if not os.path.exists(DATASET_DIR):
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

    id_to_name = {int(k): v for k, v in labels.items()}

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    cam = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cam.isOpened():
        cam = cv2.VideoCapture(0)

    if not cam.isOpened():
        print("Error: Could not open camera.")
        return

    print("Starting simple real-time demo. Press 'q' to quit.")

    while True:
        ret, frame = cam.read()
        if not ret:
            print("Warning: failed to read frame from camera.")
            continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(100, 100))

        for (x, y, w, h) in faces:
            face_img = gray[y:y + h, x:x + w]
            label_id, confidence = recognizer.predict(face_img)

            if confidence < RECOGNITION_CONFIDENCE_THRESHOLD and label_id in id_to_name:
                name = id_to_name[label_id]
                color = (0, 255, 0)
                label_text = f"{name} ({confidence:.1f})"
            else:
                name = "Unknown"
                color = (0, 0, 255)
                label_text = f"{name}"

            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            cv2.putText(
                frame,
                label_text,
                (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2,
            )

        cv2.imshow("Simple Face Recognition Demo - Press 'q' to quit", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cam.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()

