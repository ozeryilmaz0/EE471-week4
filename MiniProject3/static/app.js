// DreamCanvas AI - frontend logic (paint, chat, mic, text-to-speech)
"use strict";

const $ = (id) => document.getElementById(id);
const els = {
  imageBox: $("imageBox"), placeholder: $("placeholder"), emptyHint: $("emptyHint"),
  resultImage: $("resultImage"), loading: $("loading"), infoChip: $("infoChip"),
  downloadBtn: $("downloadBtn"), paintBtn: $("paintBtn"), promptInput: $("promptInput"),
  chat: $("chat"), composer: $("composer"), micBtn: $("micBtn"),
  messageInput: $("messageInput"), sendBtn: $("sendBtn"), voiceToggle: $("voiceToggle"),
  toast: $("toast"), botTemplate: $("botTemplate"),
};

const CONTEXT_MESSAGES = 6;
const chatHistory = [];      // [{role: "user"|"assistant", content}]
let chatBusy = false;
let paintBusy = false;

// ---------- Helpers ----------
let toastTimer;
function showToast(message, kind = "error") {
  els.toast.textContent = message;
  els.toast.className = `toast ${kind === "info" ? "info" : ""}`;
  els.toast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { els.toast.hidden = true; }, 4000);
}

async function postJSON(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return readResponse(res);
}

async function readResponse(res) {
  let data = {};
  try { data = await res.json(); } catch { /* non-JSON error page */ }
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

function scrollChatToBottom() {
  els.chat.scrollTop = els.chat.scrollHeight;
}

// ---------- Text-to-speech ----------
let voiceOn = true;
try { voiceOn = localStorage.getItem("dc-voice") !== "off"; } catch { /* storage blocked */ }
let englishVoice = null;

function pickVoice() {
  const voices = window.speechSynthesis ? speechSynthesis.getVoices() : [];
  englishVoice =
    voices.find((v) => v.lang === "en-US" && /natural|online/i.test(v.name)) ||
    voices.find((v) => v.lang === "en-US") ||
    voices.find((v) => v.lang && v.lang.startsWith("en")) || null;
}
if (window.speechSynthesis) {
  pickVoice();
  speechSynthesis.onvoiceschanged = pickVoice;
}

function renderVoiceToggle() {
  els.voiceToggle.setAttribute("aria-pressed", String(voiceOn));
  els.voiceToggle.title = `Read replies aloud (${voiceOn ? "on" : "off"})`;
}

function speak(text) {
  if (!voiceOn || !window.speechSynthesis) return;
  speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = "en-US";
  if (englishVoice) utterance.voice = englishVoice;
  utterance.rate = 1.0;
  speechSynthesis.speak(utterance);
}

els.voiceToggle.addEventListener("click", () => {
  voiceOn = !voiceOn;
  try { localStorage.setItem("dc-voice", voiceOn ? "on" : "off"); } catch { /* ignore */ }
  if (!voiceOn && window.speechSynthesis) speechSynthesis.cancel();
  renderVoiceToggle();
});
renderVoiceToggle();

// ---------- Chat ----------
function addUserMessage(text) {
  const msg = document.createElement("div");
  msg.className = "msg user";
  msg.innerHTML = '<div class="bubble"><p class="text"></p></div>';
  msg.querySelector(".text").textContent = text;
  els.chat.appendChild(msg);
  scrollChatToBottom();
}

function addBotMessage(text, { withPromptButton = true } = {}) {
  const msg = els.botTemplate.content.firstElementChild.cloneNode(true);
  msg.querySelector(".text").textContent = text;
  const btn = msg.querySelector(".use-prompt");
  if (withPromptButton) {
    btn.addEventListener("click", () => usePrompt(text));
  } else {
    btn.remove();
  }
  els.chat.appendChild(msg);
  scrollChatToBottom();
}

function showTyping() {
  const msg = document.createElement("div");
  msg.className = "msg bot typing";
  msg.innerHTML = '<div class="bubble"><span class="dot"></span><span class="dot"></span><span class="dot"></span><span class="label">typing…</span></div>';
  els.chat.appendChild(msg);
  scrollChatToBottom();
  return msg;
}

function usePrompt(text) {
  els.promptInput.value = text;
  els.promptInput.focus();
  els.promptInput.setSelectionRange(0, 0);
  const box = els.promptInput.closest(".prompt-box");
  box.classList.remove("flash");
  void box.offsetWidth; // restart the animation
  box.classList.add("flash");
}

async function sendMessage() {
  const text = els.messageInput.value.trim();
  if (!text || chatBusy) return;
  chatBusy = true;
  els.sendBtn.disabled = true;
  els.messageInput.value = "";

  chatHistory.push({ role: "user", content: text });
  addUserMessage(text);
  const typing = showTyping();
  try {
    const data = await postJSON("/api/chat", { messages: chatHistory.slice(-CONTEXT_MESSAGES) });
    typing.remove();
    chatHistory.push({ role: "assistant", content: data.reply });
    addBotMessage(data.reply);
    speak(data.reply);
  } catch (err) {
    typing.remove();
    chatHistory.pop(); // let the user retry the same message
    showToast(err.message);
    els.messageInput.value = text;
  } finally {
    chatBusy = false;
    els.sendBtn.disabled = false;
    els.messageInput.focus();
  }
}

els.composer.addEventListener("submit", (e) => {
  e.preventDefault();
  sendMessage();
});

// ---------- Paint ----------
async function paint() {
  const prompt = els.promptInput.value.trim();
  if (!prompt) {
    showToast("Please enter a prompt first.");
    els.promptInput.focus();
    return;
  }
  if (paintBusy) return;
  paintBusy = true;
  els.paintBtn.classList.add("busy");
  els.loading.hidden = false;
  els.emptyHint.hidden = true;
  try {
    const data = await postJSON("/api/generate-image", { prompt });
    const src = `data:image/png;base64,${data.image}`;
    els.resultImage.src = src;
    els.resultImage.alt = prompt;
    els.resultImage.hidden = false;
    els.placeholder.style.opacity = "0";
    els.infoChip.textContent = `512 × 512 · ${data.seconds.toFixed(1)} s`;
    els.infoChip.hidden = false;
    els.downloadBtn.href = src;
    els.downloadBtn.download = data.file || "dreamcanvas.png";
    els.downloadBtn.hidden = false;
  } catch (err) {
    showToast(err.message);
    if (els.resultImage.hidden) els.emptyHint.hidden = false;
  } finally {
    els.loading.hidden = true;
    els.paintBtn.classList.remove("busy");
    paintBusy = false;
  }
}

els.paintBtn.addEventListener("click", paint);
els.promptInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") { e.preventDefault(); paint(); }
});

// ---------- Microphone ----------
let recorder = null;
let chunks = [];
let micStream = null;

function pickMimeType() {
  const types = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"];
  return types.find((t) => window.MediaRecorder && MediaRecorder.isTypeSupported(t)) || "";
}

async function startRecording() {
  if (!navigator.mediaDevices || !window.MediaRecorder) {
    showToast("This browser cannot record audio.");
    return;
  }
  if (window.speechSynthesis) speechSynthesis.cancel(); // do not record the bot's voice
  try {
    micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch {
    showToast("Microphone access was denied. Allow it in the browser and try again.");
    return;
  }
  const mimeType = pickMimeType();
  recorder = new MediaRecorder(micStream, mimeType ? { mimeType } : undefined);
  chunks = [];
  recorder.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
  recorder.onstop = onRecordingStopped;
  recorder.start();
  els.micBtn.classList.add("recording");
  els.micBtn.title = "Stop recording";
  els.messageInput.placeholder = "Listening… tap the mic to stop";
}

function stopRecording() {
  if (recorder && recorder.state !== "inactive") recorder.stop();
  if (micStream) micStream.getTracks().forEach((t) => t.stop());
  els.micBtn.classList.remove("recording");
  els.micBtn.title = "Record voice message";
}

async function onRecordingStopped() {
  const type = recorder.mimeType || "audio/webm";
  const blob = new Blob(chunks, { type });
  const ext = type.includes("ogg") ? "ogg" : type.includes("mp4") ? "m4a" : "webm";
  recorder = null;

  els.micBtn.classList.add("busy");
  els.messageInput.placeholder = "Transcribing…";
  const form = new FormData();
  form.append("audio", blob, `recording.${ext}`);
  try {
    const data = await readResponse(await fetch("/api/transcribe", { method: "POST", body: form }));
    const current = els.messageInput.value.trim();
    els.messageInput.value = current ? `${current} ${data.text}` : data.text;
    els.messageInput.focus();
  } catch (err) {
    showToast(err.message);
  } finally {
    els.micBtn.classList.remove("busy");
    els.messageInput.placeholder = "Type or tap the mic…";
  }
}

els.micBtn.addEventListener("click", () => {
  if (recorder && recorder.state === "recording") stopRecording();
  else startRecording();
});

// ---------- Start ----------
addBotMessage("Hi! I'm DreamCanvas. Ask me for an image prompt, or just chat with me.", { withPromptButton: false });
