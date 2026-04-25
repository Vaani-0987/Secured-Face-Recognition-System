const video = document.getElementById('video');
const statusText = document.getElementById('status');
const MODEL_URL = 'https://raw.githubusercontent.com/justadudewhohacks/face-api.js/master/weights';

let faceMatcher = null;

async function init() {
    addLog("System starting...", "primary");
    try {
        await Promise.all([
            faceapi.nets.tinyFaceDetector.loadFromUri(MODEL_URL),
            faceapi.nets.faceLandmark68Net.loadFromUri(MODEL_URL),
            faceapi.nets.faceRecognitionNet.loadFromUri(MODEL_URL),
            faceapi.nets.ssdMobilenetv1.loadFromUri(MODEL_URL)
        ]);
        statusText.innerText = "BIOMETRIC MODELS LOADED";
        addLog("Neural networks online.", "success");
        startVideo();
    } catch (err) {
        statusText.innerText = "LOAD ERROR";
        addLog("Critical failure: " + err, "deny");
    }
}

function startVideo() {
    navigator.mediaDevices.getUserMedia({ video: {} })
        .then(stream => {
            video.srcObject = stream;
            video.onplay = () => {
                refreshMatcher();
                refreshUserList();
                runRecognition();
            };
        });
}

async function refreshMatcher() {
    const db = JSON.parse(localStorage.getItem('faceDb') || '[]');
    if (db.length === 0) {
        faceMatcher = null;
        return;
    }
    const labeledDescriptors = db.map(user => {
        return new faceapi.LabeledFaceDescriptors(user.name, [new Float32Array(user.descriptor)]);
    });
    faceMatcher = new faceapi.FaceMatcher(labeledDescriptors, 0.6);
}

async function runRecognition() {
    const canvas = faceapi.createCanvasFromMedia(video);
    document.getElementById('video-wrapper').append(canvas);
    const displaySize = { width: video.width, height: video.height };
    faceapi.matchDimensions(canvas, displaySize);

    setInterval(async () => {
        const detections = await faceapi.detectAllFaces(video, new faceapi.TinyFaceDetectorOptions())
            .withFaceLandmarks()
            .withFaceDescriptors();
        
        const resizedDetections = faceapi.resizeResults(detections, displaySize);
        canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);

        resizedDetections.forEach(detection => {
            let label = "Unknown";
            let color = "#ef4444";

            if (faceMatcher) {
                const result = faceMatcher.findBestMatch(detection.descriptor);
                if (result.label !== 'unknown') {
                    label = `Authorized: ${result.label.toUpperCase()}`;
                    color = "#00f2ff";
                    statusText.innerHTML = `<span class="grant">ACCESS GRANTED: ${result.label}</span>`;
                } else {
                    statusText.innerHTML = `<span class="deny">ACCESS DENIED</span>`;
                }
            }

            const drawBox = new faceapi.draw.DrawBox(detection.detection.box, { label, boxColor: color });
            drawBox.draw(canvas);
        });
    }, 200);
}

async function registerFace() {
    const name = document.getElementById('userName').value;
    if (!name) return alert("Enter name");

    statusText.innerText = "SCANNING...";
    const detection = await faceapi.detectSingleFace(video, new faceapi.TinyFaceDetectorOptions()).withFaceLandmarks().withFaceDescriptor();

    if (detection) {
        const db = JSON.parse(localStorage.getItem('faceDb') || '[]');
        db.push({ name, descriptor: Array.from(detection.descriptor) });
        localStorage.setItem('faceDb', JSON.stringify(db));
        addLog(`Enrolled: ${name}`, "success");
        await refreshMatcher();
        refreshUserList();
        document.getElementById('userName').value = "";
    } else {
        alert("Face not detected. Stand closer.");
    }
}

function refreshUserList() {
    const container = document.getElementById('user-list');
    const db = JSON.parse(localStorage.getItem('faceDb') || '[]');
    container.innerHTML = db.map((u, i) => `
        <div class="user-item">
            <span>${u.name}</span>
            <span style="color:red; cursor:pointer;" onclick="deleteUser(${i})">REVOKE</span>
        </div>
    `).join('');
}

function deleteUser(i) {
    let db = JSON.parse(localStorage.getItem('faceDb') || '[]');
    db.splice(i, 1);
    localStorage.setItem('faceDb', JSON.stringify(db));
    refreshMatcher();
    refreshUserList();
    addLog("Personnel Revoked", "deny");
}

function addLog(msg, type) {
    const logs = document.getElementById('logs');
    const time = new Date().toLocaleTimeString();
    logs.innerHTML += `<div class="${type}">[${time}] ${msg}</div>`;
    logs.scrollTop = logs.scrollHeight;
}

function resetDatabase() {
    if (confirm("Wipe all biometric data?")) {
        localStorage.removeItem('faceDb');
        location.reload();
    }
}

init();