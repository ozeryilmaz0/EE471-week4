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
const sttLanguage = document.getElementById("stt-language");
const transcribeBtn = document.getElementById("transcribe-btn");
const sttClearBtn = document.getElementById("stt-clear-btn");
const sttMessage = document.getElementById("stt-message");
const resultSection = document.getElementById("result-section");
const resultText = document.getElementById("result-text");
const copyBtn = document.getElementById("copy-btn");

// ---------- Diarization elements ----------
const diarizeLanguage = document.getElementById("diarize-language");
const diarizeBtn = document.getElementById("diarize-btn");
const diarizeClearBtn = document.getElementById("diarize-clear-btn");
const diarizeMessage = document.getElementById("diarize-message");
const conversationSection = document.getElementById("conversation-section");
const conversation = document.getElementById("conversation");

const COPY_LABEL = copyBtn.textContent;
const SPEAKER_COLOR_COUNT = 6;

let audioUrl = null;

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

// ---------- Shared record / upload control ----------

// Pick a file extension that matches the recorded MIME type
function recordingFilename(blob) {
    if (blob.type.includes("ogg")) return "recording.ogg";
    if (blob.type.includes("mp4")) return "recording.mp4";
    return "recording.webm";
}

// Wire up a record / upload block and return an object to read or clear its audio
function createAudioInput(container, messageBox) {
    const recordBtn = container.querySelector(".record-btn");
    const stopBtn = container.querySelector(".stop-btn");
    const fileInput = container.querySelector(".file-input");
    const indicator = container.querySelector(".recording-indicator");
    const status = container.querySelector(".status");

    let mediaRecorder = null;
    let audioChunks = [];
    let recordedBlob = null;

    // Show or hide the small status line under the recording controls
    function setStatus(text) {
        status.textContent = text;
        status.classList.toggle("hidden", !text);
    }

    // Toggle the recording controls and indicator
    function setRecordingUI(isRecording) {
        recordBtn.disabled = isRecording;
        stopBtn.disabled = !isRecording;
        indicator.classList.toggle("hidden", !isRecording);
    }

    // Start recording from the microphone with MediaRecorder
    async function startRecording() {
        hideMessage(messageBox);

        if (!navigator.mediaDevices || !window.MediaRecorder) {
            showMessage(messageBox, "Audio recording is not supported in this browser.", "error");
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
                setStatus("✓ Recording ready.");
            });

            recorder.start();
            setRecordingUI(true);
        } catch (err) {
            showMessage(messageBox, `Could not access the microphone: ${err.message}`, "error");
        }
    }

    // Stop the current recording
    function stopRecording() {
        if (mediaRecorder && mediaRecorder.state !== "inactive") {
            mediaRecorder.stop();
        }
        setRecordingUI(false);
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
    fileInput.addEventListener("change", onFileChange);

    return {
        // Return the recording if there is one, otherwise the selected file
        getAudio() {
            if (recordedBlob) {
                return { blob: recordedBlob, filename: recordingFilename(recordedBlob) };
            }
            const file = fileInput.files[0];
            return file ? { blob: file, filename: file.name } : null;
        },

        // Stop any recording and forget the recorded or selected audio
        clear() {
            stopRecording();
            mediaRecorder = null;
            recordedBlob = null;
            audioChunks = [];
            fileInput.value = "";
            setStatus("");
        },
    };
}

// Send the audio from a record / upload block to an API endpoint and return its JSON
async function postAudio(url, audioInput, language) {
    const audio = audioInput.getAudio();
    if (!audio) {
        throw new Error("Please record audio or choose an audio file first.");
    }

    const formData = new FormData();
    formData.append("audio", audio.blob, audio.filename);
    formData.append("language", language);

    const response = await fetch(url, { method: "POST", body: formData });
    if (!response.ok) {
        throw new Error(await getErrorMessage(response));
    }
    return response.json();
}

const sttAudio = createAudioInput(document.getElementById("stt-audio-input"), sttMessage);
const diarizeAudio = createAudioInput(document.getElementById("diarize-audio-input"), diarizeMessage);

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

// Send the recording (or the selected file) to the backend for transcription
async function transcribe() {
    hideMessage(sttMessage);
    setLoading(transcribeBtn, true, "Transcribing...");

    try {
        const data = await postAudio("/api/stt", sttAudio, sttLanguage.value);
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
    sttAudio.clear();
    hideMessage(sttMessage);
    resultText.textContent = "";
    resultSection.classList.add("hidden");
}

// ---------- Diarization ----------

// Render the segments as chat bubbles, one color and side per speaker
function renderConversation(segments) {
    const speakerIndex = new Map();
    conversation.innerHTML = "";

    segments.forEach(({ speaker, text }) => {
        if (!speakerIndex.has(speaker)) {
            speakerIndex.set(speaker, speakerIndex.size);
        }
        const index = speakerIndex.get(speaker);

        const row = document.createElement("div");
        row.className = `bubble-row speaker-${index % SPEAKER_COLOR_COUNT}`;
        row.classList.toggle("right", index % 2 === 1);

        const name = document.createElement("span");
        name.className = "speaker-name";
        name.textContent = speaker;

        const bubble = document.createElement("div");
        bubble.className = "bubble";
        bubble.textContent = text;

        row.append(name, bubble);
        conversation.appendChild(row);
    });

    conversationSection.classList.remove("hidden");
    return speakerIndex.size;
}

// Send the recording (or the selected file) to the backend for speaker diarization
async function identifySpeakers() {
    hideMessage(diarizeMessage);
    setLoading(diarizeBtn, true, "Identifying speakers...");

    try {
        const data = await postAudio("/api/diarize", diarizeAudio, diarizeLanguage.value);
        const speakerCount = renderConversation(data.segments);
        const label = speakerCount === 1 ? "speaker" : "speakers";
        showMessage(diarizeMessage, `✓ Identified ${speakerCount} ${label}!`, "success");
    } catch (err) {
        showMessage(diarizeMessage, err.message, "error");
    } finally {
        setLoading(diarizeBtn, false);
    }
}

// Reset the recording, file, messages and conversation
function clearDiarize() {
    diarizeAudio.clear();
    hideMessage(diarizeMessage);
    conversation.innerHTML = "";
    conversationSection.classList.add("hidden");
}

// ---------- Event listeners ----------
tabs.forEach((tab) => tab.addEventListener("click", () => switchTab(tab.dataset.tab)));

synthesizeBtn.addEventListener("click", synthesize);
ttsClearBtn.addEventListener("click", clearTts);

transcribeBtn.addEventListener("click", transcribe);
sttClearBtn.addEventListener("click", clearStt);
copyBtn.addEventListener("click", copyText);

diarizeBtn.addEventListener("click", identifySpeakers);
diarizeClearBtn.addEventListener("click", clearDiarize);
