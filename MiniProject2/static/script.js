// Library page: item table and the voice librarian panel.

const micButton = document.getElementById("mic-button");
const micStatus = document.getElementById("mic-status");
const textForm = document.getElementById("text-form");
const textInput = document.getElementById("text-input");
const resultCard = document.getElementById("result-card");
const resultTranscript = document.getElementById("result-transcript");
const resultApi = document.getElementById("result-api");
const resultStatus = document.getElementById("result-status");
const resultMessage = document.getElementById("result-message");
const replayButton = document.getElementById("replay-button");
const historyList = document.getElementById("history-list");
const itemsBody = document.getElementById("items-body");
const refreshButton = document.getElementById("refresh-button");
const replyAudio = document.getElementById("reply-audio");

const HISTORY_SIZE = 5;
const history = [];

let recorder = null;
let chunks = [];
let busy = false;

// ---------- Items table ----------

function cell(text, className) {
  const td = document.createElement("td");
  td.textContent = text;
  if (className) td.className = className;
  return td;
}

function itemDetails(item) {
  if (item.type === "book") return `${item.page_count} pages`;
  if (item.type === "dvd") return `${item.duration} min`;
  return "";
}

async function loadItems() {
  try {
    const response = await fetch("/api/items");
    const items = await response.json();
    itemsBody.replaceChildren();
    if (!items.length) {
      const row = document.createElement("tr");
      const td = cell("The library is empty.", "empty");
      td.colSpan = 6;
      row.append(td);
      itemsBody.append(row);
      return;
    }
    for (const item of items) {
      const row = document.createElement("tr");
      const status = item.is_available ? "Available" : "Checked out";
      row.append(
        cell(item.id),
        cell(item.type === "dvd" ? "DVD" : "Book"),
        cell(item.title),
        cell(item.author),
        cell(itemDetails(item)),
        cell(status, `status-pill ${item.is_available ? "available" : "out"}`),
      );
      itemsBody.append(row);
    }
  } catch (error) {
    itemsBody.innerHTML = '<tr><td colspan="6" class="empty">Could not load items.</td></tr>';
  }
}

// ---------- Result card and history ----------

function badgeClass(status) {
  if (status >= 200 && status < 300) return "badge ok";
  if (status >= 400) return "badge error";
  return "badge";
}

function setBadge(element, status) {
  element.className = badgeClass(status);
  element.textContent = status ?? "no API call";
}

function playAudio(base64) {
  if (!base64) return;
  replyAudio.src = `data:audio/wav;base64,${base64}`;
  replyAudio.play().catch(() => {
    // Autoplay can be blocked; the Replay button still works.
  });
}

function addHistory(data) {
  history.unshift(data);
  history.length = Math.min(history.length, HISTORY_SIZE);
  historyList.replaceChildren();
  for (const entry of history) {
    const li = document.createElement("li");
    const badge = document.createElement("span");
    setBadge(badge, entry.status);
    const said = document.createElement("span");
    said.className = "said";
    said.textContent = `“${entry.transcript || "(nothing heard)"}”`;
    li.append(badge, said, document.createTextNode(` — ${entry.message}`));
    historyList.append(li);
  }
}

function showResult(data) {
  resultCard.hidden = false;
  resultTranscript.textContent = data.transcript || "(nothing heard)";
  resultApi.textContent = data.api_call || "—";
  setBadge(resultStatus, data.status);
  resultMessage.textContent = data.message;
  replayButton.hidden = !data.audio;
  replayButton.onclick = () => playAudio(data.audio);
  playAudio(data.audio);
  addHistory(data);
  loadItems();
}

function setBusy(isBusy, message) {
  busy = isBusy;
  micButton.disabled = isBusy;
  micButton.classList.toggle("busy", isBusy);
  textForm.querySelector("button").disabled = isBusy;
  if (message) micStatus.textContent = message;
}

async function sendCommand(url, options) {
  setBusy(true, "Working on it…");
  try {
    const response = await fetch(url, options);
    const data = await response.json();
    showResult(data);
    setBusy(false, "Click the microphone and say a command.");
  } catch (error) {
    setBusy(false, "Something went wrong. Is the server running?");
  }
}

// ---------- Typed commands ----------

textForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = textInput.value.trim();
  if (!text || busy) return;
  textInput.value = "";
  sendCommand("/api/voice/text", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
});

// ---------- Recording ----------

async function startRecording() {
  if (!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
    micStatus.textContent = "This browser cannot record audio.";
    return;
  }
  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (error) {
    micStatus.textContent = "Microphone access was denied.";
    return;
  }

  chunks = [];
  recorder = new MediaRecorder(stream);
  recorder.addEventListener("dataavailable", (event) => {
    if (event.data.size > 0) chunks.push(event.data);
  });
  recorder.addEventListener("stop", () => {
    stream.getTracks().forEach((track) => track.stop());
    const type = recorder.mimeType || "audio/webm";
    const extension = type.includes("ogg") ? "ogg" : type.includes("mp4") ? "mp4" : "webm";
    const blob = new Blob(chunks, { type });
    recorder = null;
    // "dataavailable" always fires before "stop", so all chunks are here now.
    if (blob.size === 0) {
      micStatus.textContent = "I didn't hear anything. Please try again.";
      return;
    }
    const form = new FormData();
    form.append("audio", blob, `recording.${extension}`);
    sendCommand("/api/voice", { method: "POST", body: form });
  });

  recorder.start();
  micButton.classList.add("recording");
  micButton.setAttribute("aria-label", "Stop recording");
  micStatus.textContent = "Listening… click again to stop.";
}

function stopRecording() {
  micButton.classList.remove("recording");
  micButton.setAttribute("aria-label", "Start recording");
  recorder.stop();
}

micButton.addEventListener("click", () => {
  if (busy) return;
  if (recorder && recorder.state === "recording") {
    stopRecording();
  } else {
    startRecording();
  }
});

refreshButton.addEventListener("click", loadItems);

loadItems();
