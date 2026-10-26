const textInput = document.getElementById("text-input");
const voiceSelect = document.getElementById("voice-select");
const synthesizeBtn = document.getElementById("synthesize-btn");
const clearBtn = document.getElementById("clear-btn");
const message = document.getElementById("message");
const audioSection = document.getElementById("audio-section");
const audioPlayer = document.getElementById("audio-player");
const downloadBtn = document.getElementById("download-btn");

const SYNTHESIZE_LABEL = synthesizeBtn.textContent;
let audioUrl = null;

// Show a success or error message box
function showMessage(text, type) {
    message.textContent = text;
    message.className = `message ${type}`;
}

// Hide the message box
function hideMessage() {
    message.className = "message hidden";
}

// Toggle the loading state of the synthesize button
function setLoading(isLoading) {
    synthesizeBtn.disabled = isLoading;
    synthesizeBtn.textContent = isLoading ? "Synthesizing..." : SYNTHESIZE_LABEL;
}

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
        showMessage("Text cannot be empty", "error");
        return;
    }

    hideMessage();
    setLoading(true);

    try {
        const response = await fetch("/api/tts", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text, voice: voiceSelect.value }),
        });

        if (!response.ok) {
            const data = await response.json().catch(() => ({}));
            throw new Error(data.error || `Request failed with status ${response.status}`);
        }

        const blob = await response.blob();
        resetAudio();
        audioUrl = URL.createObjectURL(blob);
        audioPlayer.src = audioUrl;
        downloadBtn.href = audioUrl;
        audioSection.classList.remove("hidden");
        showMessage("✓ Speech synthesized successfully!", "success");
    } catch (err) {
        showMessage(err.message, "error");
    } finally {
        setLoading(false);
    }
}

// Clear the text, message and generated audio
function clearAll() {
    textInput.value = "";
    hideMessage();
    resetAudio();
    textInput.focus();
}

synthesizeBtn.addEventListener("click", synthesize);
clearBtn.addEventListener("click", clearAll);
