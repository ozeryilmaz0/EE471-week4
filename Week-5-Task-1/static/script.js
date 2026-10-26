// ---------- Tabs ----------
const tabs = document.querySelectorAll(".tab");
const panels = document.querySelectorAll(".panel");

// ---------- Text to Speech elements ----------
const textInput = document.getElementById("text-input");
const voiceSelect = document.getElementById("voice-select");
const synthesizeBtn = document.getElementById("synthesize-btn");
const ttsClearBtn = document.getElementById("tts-clear-btn");
const ttsMessage = document.getElementById("tts-message");
const audioSection = document.getElementById("audio-section");
const audioPlayer = document.getElementById("audio-player");
const downloadBtn = document.getElementById("download-btn");

// ---------- Speech to Text elements ----------
const languageSelect = document.getElementById("language-select");
const recordBtn = document.getElementById("record-btn");
const stopBtn = document.getElementById("stop-btn");
const fileInput = document.getElementById("file-input");
const recordingIndicator = document.getElementById("recording-indicator");
const recordingStatus = document.getElementById("recording-status");
const transcribeBtn = document.getElementById("transcribe-btn");
const sttClearBtn = document.getElementById("stt-clear-btn");
const sttMessage = document.getElementById("stt-message");
const resultSection = document.getElementById("result-section");
const resultText = document.getElementById("result-text");
const copyBtn = document.getElementById("copy-btn");

const COPY_LABEL = copyBtn.textContent;

let audioUrl = null;
let mediaRecorder = null;
let audioChunks = [];
let recordedBlob = null;

// ---------- Shared helpers ----------

// Show the selected tab's panel and hide the others
function switchTab(name) {
    tabs.forEach((tab) => {
        const isActive = tab.dataset.tab === name;
        tab.classList.toggle("active", isActive);
        tab.setAttribute("aria-selected", isActive);
    });
    panels.forEach((panel) => {
        panel.classList.toggle("hidden", panel.id !== `${name}-panel`);
    });
}

// Show a success or error message in the given box
function showMessage(box, text, type) {
    box.textContent = text;
    box.className = `message ${type}`;
}

// Hide the given message box
function hideMessage(box) {
    box.className = "message hidden";
}

// Toggle a button's loading state and restore its original label afterwards
function setLoading(button, isLoading, loadingText) {
    if (isLoading) {
        button.dataset.label = button.textContent;
        button.textContent = loadingText;
    } else if (button.dataset.label) {
        button.textContent = button.dataset.label;
    }
    button.disabled = isLoading;
}

// Read the error message from a failed API response
async function getErrorMessage(response) {
    const data = await response.json().catch(() => ({}));
    return data.error || `Request failed with status ${response.status}`;
}

// ---------- Text to Speech ----------

// Release the previous audio blob URL and hide the audio section
function resetAudio() {
    if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
        audioUrl = null;
    }
    audioPlayer.removeAttribute("src");
    downloadBtn.removeAttribute("href");
    audioSection.classList.add("hidden");
}

// Send the text to the backend and play the returned audio
async function synthesize() {
    const text = textInput.value.trim();
    if (!text) {
        showMessage(ttsMessage, "Text cannot be empty", "error");
        return;
    }

    hideMessage(ttsMessage);
    setLoading(synthesizeBtn, true, "Synthesizing...");

    try {
        const response = await fetch("/api/tts", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text, voice: voiceSelect.value }),
        });

        if (!response.ok) {
            throw new Error(await getErrorMessage(response));
        }

        const blob = await response.blob();
        resetAudio();
        audioUrl = URL.createObjectURL(blob);
        audioPlayer.src = audioUrl;
        downloadBtn.href = audioUrl;
        audioSection.classList.remove("hidden");
        showMessage(ttsMessage, "✓ Speech synthesized successfully!", "success");
    } catch (err) {
        showMessage(ttsMessage, err.message, "error");
    } finally {
        setLoading(synthesizeBtn, false);
    }
}

// Clear the text, message and generated audio
function clearTts() {
    textInput.value = "";
    hideMessage(ttsMessage);
    resetAudio();
    textInput.focus();
}

// ---------- Speech to Text ----------

// Show or hide the small status line under the recording controls
function setStatus(text) {
    recordingStatus.textContent = text;
    recordingStatus.classList.toggle("hidden", !text);
}

// Toggle the recording controls and indicator
function setRecordingUI(isRecording) {
    recordBtn.disabled = isRecording;
    stopBtn.disabled = !isRecording;
    recordingIndicator.classList.toggle("hidden", !isRecording);
}

// Start recording from the microphone with MediaRecorder
async function startRecording() {
    hideMessage(sttMessage);

    if (!navigator.mediaDevices || !window.MediaRecorder) {
        showMessage(sttMessage, "Audio recording is not supported in this browser.", "error");
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
        showMessage(sttMessage, `Could not access the microphone: ${err.message}`, "error");
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
        showMessage(sttMessage, "Please record audio or choose an audio file first.", "error");
        return;
    }

    const formData = new FormData();
    if (recordedBlob) {
        formData.append("audio", recordedBlob, recordingFilename(recordedBlob));
    } else {
        formData.append("audio", file);
    }
    formData.append("language", languageSelect.value);

    hideMessage(sttMessage);
    setLoading(transcribeBtn, true, "Transcribing...");

    try {
        const response = await fetch("/api/stt", { method: "POST", body: formData });

        if (!response.ok) {
            throw new Error(await getErrorMessage(response));
        }

        const data = await response.json();
        resultText.textContent = data.text;
        resultSection.classList.remove("hidden");
        showMessage(sttMessage, "✓ Audio transcribed successfully!", "success");
    } catch (err) {
        showMessage(sttMessage, err.message, "error");
    } finally {
        setLoading(transcribeBtn, false);
    }
}

// Copy the transcription to the clipboard
async function copyText() {
    try {
        await navigator.clipboard.writeText(resultText.textContent);
        copyBtn.textContent = "✓ Copied!";
        setTimeout(() => (copyBtn.textContent = COPY_LABEL), 1500);
    } catch (err) {
        showMessage(sttMessage, "Could not copy text to the clipboard.", "error");
    }
}

// Reset the recording, file, messages and transcription
function clearStt() {
    stopRecording();
    mediaRecorder = null;
    recordedBlob = null;
    audioChunks = [];
    fileInput.value = "";
    setStatus("");
    hideMessage(sttMessage);
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

// ---------- Event listeners ----------
tabs.forEach((tab) => tab.addEventListener("click", () => switchTab(tab.dataset.tab)));

synthesizeBtn.addEventListener("click", synthesize);
ttsClearBtn.addEventListener("click", clearTts);

recordBtn.addEventListener("click", startRecording);
stopBtn.addEventListener("click", stopRecording);
transcribeBtn.addEventListener("click", transcribe);
sttClearBtn.addEventListener("click", clearStt);
copyBtn.addEventListener("click", copyText);
fileInput.addEventListener("change", onFileChange);
