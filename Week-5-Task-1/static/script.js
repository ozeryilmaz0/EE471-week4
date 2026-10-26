const languageSelect = document.getElementById("language-select");
const recordBtn = document.getElementById("record-btn");
const stopBtn = document.getElementById("stop-btn");
const fileInput = document.getElementById("file-input");
const recordingIndicator = document.getElementById("recording-indicator");
const recordingStatus = document.getElementById("recording-status");
const transcribeBtn = document.getElementById("transcribe-btn");
const clearBtn = document.getElementById("clear-btn");
const message = document.getElementById("message");
const resultSection = document.getElementById("result-section");
const resultText = document.getElementById("result-text");
const copyBtn = document.getElementById("copy-btn");

const TRANSCRIBE_LABEL = transcribeBtn.textContent;
const COPY_LABEL = copyBtn.textContent;

let mediaRecorder = null;
let audioChunks = [];
let recordedBlob = null;

// Show a success or error message box
function showMessage(text, type) {
    message.textContent = text;
    message.className = `message ${type}`;
}

// Hide the message box
function hideMessage() {
    message.className = "message hidden";
}

// Show or hide the small status line under the recording controls
function setStatus(text) {
    recordingStatus.textContent = text;
    recordingStatus.classList.toggle("hidden", !text);
}

// Toggle the loading state of the transcribe button
function setLoading(isLoading) {
    transcribeBtn.disabled = isLoading;
    transcribeBtn.textContent = isLoading ? "Transcribing..." : TRANSCRIBE_LABEL;
}

// Toggle the recording controls and indicator
function setRecordingUI(isRecording) {
    recordBtn.disabled = isRecording;
    stopBtn.disabled = !isRecording;
    recordingIndicator.classList.toggle("hidden", !isRecording);
}

// Start recording from the microphone with MediaRecorder
async function startRecording() {
    hideMessage();

    if (!navigator.mediaDevices || !window.MediaRecorder) {
        showMessage("Audio recording is not supported in this browser.", "error");
        return;
    }

    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        audioChunks = [];
        recordedBlob = null;
        fileInput.value = "";
        setStatus("");

        const recorder = new MediaRecorder(stream);
        mediaRecorder = recorder;
        recorder.addEventListener("dataavailable", (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        });
        recorder.addEventListener("stop", () => {
            stream.getTracks().forEach((track) => track.stop());
            // Ignore the result if the recording was cleared in the meantime
            if (mediaRecorder !== recorder) return;
            recordedBlob = new Blob(audioChunks, { type: recorder.mimeType || "audio/webm" });
            setStatus("✓ Recording ready to transcribe.");
        });

        recorder.start();
        setRecordingUI(true);
    } catch (err) {
        showMessage(`Could not access the microphone: ${err.message}`, "error");
    }
}

// Stop the current recording
function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
        mediaRecorder.stop();
    }
    setRecordingUI(false);
}

// Pick a file extension that matches the recorded MIME type
function recordingFilename(blob) {
    if (blob.type.includes("ogg")) return "recording.ogg";
    if (blob.type.includes("mp4")) return "recording.mp4";
    return "recording.webm";
}

// Send the recording (or the selected file) to the backend for transcription
async function transcribe() {
    const file = fileInput.files[0];
    if (!recordedBlob && !file) {
        showMessage("Please record audio or choose an audio file first.", "error");
        return;
    }

    const formData = new FormData();
    if (recordedBlob) {
        formData.append("audio", recordedBlob, recordingFilename(recordedBlob));
    } else {
        formData.append("audio", file);
    }
    formData.append("language", languageSelect.value);

    hideMessage();
    setLoading(true);

    try {
        const response = await fetch("/api/stt", { method: "POST", body: formData });
        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            throw new Error(data.error || `Request failed with status ${response.status}`);
        }

        resultText.textContent = data.text;
        resultSection.classList.remove("hidden");
        showMessage("✓ Audio transcribed successfully!", "success");
    } catch (err) {
        showMessage(err.message, "error");
    } finally {
        setLoading(false);
    }
}

// Copy the transcription to the clipboard
async function copyText() {
    try {
        await navigator.clipboard.writeText(resultText.textContent);
        copyBtn.textContent = "✓ Copied!";
        setTimeout(() => (copyBtn.textContent = COPY_LABEL), 1500);
    } catch (err) {
        showMessage("Could not copy text to the clipboard.", "error");
    }
}

// Reset the recording, file, messages and transcription
function clearAll() {
    stopRecording();
    mediaRecorder = null;
    recordedBlob = null;
    audioChunks = [];
    fileInput.value = "";
    setStatus("");
    hideMessage();
    resultText.textContent = "";
    resultSection.classList.add("hidden");
}

// Choosing a new file replaces any previous recording
function onFileChange() {
    if (fileInput.files.length > 0) {
        recordedBlob = null;
        setStatus("");
    }
}

recordBtn.addEventListener("click", startRecording);
stopBtn.addEventListener("click", stopRecording);
transcribeBtn.addEventListener("click", transcribe);
clearBtn.addEventListener("click", clearAll);
copyBtn.addEventListener("click", copyText);
fileInput.addEventListener("change", onFileChange);
