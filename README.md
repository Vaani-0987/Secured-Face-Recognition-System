Embedded Face Recognition Access Control (Simulated)
===================================================

This project implements a basic **embedded-style face recognition access control system** using your laptop webcam.  
The same software structure can later be deployed on embedded hardware such as a Raspberry Pi.

Main features
-------------
- Real-time face detection from webcam using OpenCV.
- Face enrollment tool to register authorized users.
- Face recognition using the LBPH algorithm (OpenCV).
- Access control logic that simulates a door lock:
  - **Access Granted** when a known user is recognized.
  - **Access Denied** for unknown faces.
- CSV log file with timestamp, user name / "Unknown", confidence, and decision.

High-level workflow
-------------------
1. Install dependencies:
   - Create and activate a virtual environment (optional but recommended).
   - Install Python packages:

     ```bash
     pip install -r requirements.txt
     ```

2. Enroll one or more users:
   - Run:

     ```bash
     python enroll.py
     ```

   - Enter the user name when asked.
   - Look at the webcam; the script will capture multiple face images and then train a recognizer model.

3. Run the access control loop:
   - After enrollment and training complete, start the main script:

     ```bash
     python main.py
     ```

   - The webcam window will open.
   - When an enrolled face is seen, the overlay will show **Access Granted** with the recognized name.
   - Otherwise it will show **Access Denied**.
   - All attempts are logged in `access_log.csv`.

Project structure
-----------------
- `enroll.py` – capture training images and train the LBPH recognizer.
- `main.py` – real-time recognition and access decision loop.
- `ui.py` – simple UI to launch enrollment or recognition.
- `access_control.py` – logic for granting/denying access and logging.
- `config.py` – thresholds and configurable parameters.
- `requirements.txt` – Python dependencies.
- `data/`
  - `dataset/` – subfolders with training images per user (created automatically).
  - `trainer.yml` – saved trained recognizer model (created automatically).
  - `labels.json` – mapping between numeric IDs and user names (created automatically).
  - `access_log.csv` – log file with access attempts (created automatically).

How this maps to an embedded system
-----------------------------------
- **Camera**: laptop webcam here, but could be a Raspberry Pi Camera Module.
- **Processor**: your laptop CPU here, but could be a Raspberry Pi 4 or similar SBC.
- **Door lock / relay**: simulated in software by printed messages and on-screen overlays.
- **GPIO control** (for real hardware):
  - When `grant_access` is called, a Raspberry Pi could activate a GPIO pin connected to a relay module, unlocking an electric strike or solenoid lock for a few seconds.
  - When `deny_access` is called, a buzzer or red LED could be activated.

You can describe this mapping, plus a block diagram and GPIO table, in your college project report to emphasize that this is designed as an **embedded security system**, even though it is demonstrated on a normal computer.

Quick start (UI)
----------------
Run:

```bash
python ui.py
```

Then click:
- **Enroll New Person** to add a user
- **Start Recognition** to run the access control loop
