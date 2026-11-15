// Model comparison: pick an image, send it to /api/classify, show both models side by side.

const $ = (id) => document.getElementById(id);
const dropZone = $("drop-zone");
const fileInput = $("file-input");
const dropHint = $("drop-hint");
const preview = $("preview");
const fileName = $("file-name");
const classifyButton = $("classify-button");
const errorBox = $("error");
const verdict = $("verdict");
const samples = $("samples");
const cards = { baseline: $("card-baseline"), optimized: $("card-optimized") };

let selectedFile = null;

const percent = (value) => `${(value * 100).toFixed(1)}%`;

function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = !message;
}

// "03_dress_1.png" -> "dress"
function sampleLabel(name) {
  return name.replace(/\.[^.]+$/, "").replace(/^\d+_/, "").replace(/_\d+$/, "").replace(/_/g, " ");
}

// ---------- Page setup ----------

async function loadConfig() {
  try {
    const response = await fetch("/api/config");
    const config = await response.json();
    $("title").textContent = config.title;
    document.title = config.title;
    for (const name of config.samples) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "sample";
      button.title = `Classify ${name}`;
      const img = document.createElement("img");
      img.src = `/samples/${encodeURIComponent(name)}`;
      img.alt = sampleLabel(name);
      img.loading = "lazy";
      const caption = document.createElement("span");
      caption.textContent = sampleLabel(name);
      button.append(img, caption);
      button.addEventListener("click", () => useSample(name));
      samples.append(button);
    }
    if (!config.samples.length) samples.textContent = "No sample images found.";
  } catch {
    showError("Could not load the page settings.");
  }
}

// ---------- Choosing an image ----------

function selectFile(file, label) {
  if (!file || !file.type.startsWith("image/")) {
    showError("Please choose an image file.");
    return false;
  }
  selectedFile = file;
  preview.src = URL.createObjectURL(file);
  preview.hidden = false;
  dropHint.hidden = true;
  fileName.textContent = label || file.name;
  fileName.hidden = false;
  showError("");
  classifyButton.disabled = false;
  return true;
}

async function useSample(name) {
  try {
    const response = await fetch(`/samples/${encodeURIComponent(name)}`);
    const blob = await response.blob();
    const file = new File([blob], name, { type: blob.type || "image/png" });
    if (selectFile(file, `Sample: ${name} (true class: ${sampleLabel(name)})`)) classify();
  } catch {
    showError("Could not load the sample image.");
  }
}

fileInput.addEventListener("change", () => selectFile(fileInput.files[0]));

["dragenter", "dragover"].forEach((type) =>
  dropZone.addEventListener(type, (event) => {
    event.preventDefault();
    dropZone.classList.add("dragging");
  }));

["dragleave", "drop"].forEach((type) =>
  dropZone.addEventListener(type, (event) => {
    event.preventDefault();
    dropZone.classList.remove("dragging");
  }));

dropZone.addEventListener("drop", (event) => selectFile(event.dataTransfer.files[0]));

// ---------- Showing results ----------

function setLoading(card) {
  card.classList.add("loading");
  card.querySelector('[data-field="body"]').innerHTML =
    '<div class="spinner" aria-hidden="true"></div><p class="placeholder">Classifying…</p>';
}

function renderResult(card, result) {
  card.classList.remove("loading");
  const body = card.querySelector('[data-field="body"]');
  body.replaceChildren();

  if (!result.ok) {
    const p = document.createElement("p");
    p.className = "card-error";
    p.textContent = result.error || "Prediction failed.";
    body.append(p);
    return;
  }
  const out = result.output;
  card.querySelector('[data-field="accuracy"]').textContent = percent(out.model_test_accuracy);

  const prediction = document.createElement("p");
  prediction.className = "prediction";
  prediction.textContent = out.predicted_class;
  const confidence = document.createElement("p");
  confidence.className = "confidence";
  confidence.textContent = `${percent(out.confidence)} confident`;

  const list = document.createElement("ul");
  list.className = "bars";
  const entries = Object.entries(out.top3).sort((a, b) => b[1] - a[1]);
  entries.forEach(([name, probability], index) => {
    const li = document.createElement("li");
    if (index === 0) li.className = "top";
    const label = document.createElement("div");
    label.className = "bar-label";
    const nameSpan = document.createElement("span");
    nameSpan.textContent = name;
    const valueSpan = document.createElement("span");
    valueSpan.textContent = percent(probability);
    label.append(nameSpan, valueSpan);
    const track = document.createElement("div");
    track.className = "bar-track";
    const fill = document.createElement("div");
    fill.className = "bar-fill";
    track.append(fill);
    li.append(label, track);
    list.append(li);
    // Set the width after insertion so the CSS transition animates it.
    requestAnimationFrame(() => { fill.style.width = `${probability * 100}%`; });
  });

  const meta = document.createElement("dl");
  meta.className = "meta";
  for (const [term, value] of [["Response time", `${result.time_ms} ms`],
                               ["Model", out.model_name],
                               ["Test accuracy", percent(out.model_test_accuracy)]]) {
    const dt = document.createElement("dt");
    dt.textContent = term;
    const dd = document.createElement("dd");
    dd.textContent = value;
    meta.append(dt, dd);
  }
  body.append(prediction, confidence, list, meta);
}

function renderVerdict(agree) {
  verdict.hidden = agree === null;
  verdict.className = `verdict ${agree ? "agree" : "disagree"}`;
  verdict.textContent = agree ? "✓ Agree — both models predict the same class"
                              : "✗ Disagree — the models predict different classes";
}

// ---------- Classifying ----------

async function classify() {
  if (!selectedFile) return;
  classifyButton.disabled = true;
  verdict.hidden = true;
  showError("");
  Object.values(cards).forEach(setLoading);

  const form = new FormData();
  form.append("image", selectedFile);
  try {
    const response = await fetch("/api/classify", { method: "POST", body: form });
    const data = await response.json();
    if (!response.ok) {
      showError(data.error || "Something went wrong.");
      Object.values(cards).forEach((card) => renderResult(card, { ok: false, error: "—" }));
      return;
    }
    renderResult(cards.baseline, data.baseline);
    renderResult(cards.optimized, data.optimized);
    renderVerdict(data.agree);
  } catch {
    showError("Could not reach the server.");
    Object.values(cards).forEach((card) => renderResult(card, { ok: false, error: "No answer." }));
  } finally {
    classifyButton.disabled = false;
  }
}

classifyButton.addEventListener("click", classify);
loadConfig();
