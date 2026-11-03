// Cat Kind Classifier: pick a photo, send it to /api/classify, show the result.

const dropZone = document.getElementById("drop-zone");
const fileInput = document.getElementById("file-input");
const dropHint = document.getElementById("drop-hint");
const preview = document.getElementById("preview");
const classifyButton = document.getElementById("classify-button");
const loading = document.getElementById("loading");
const errorBox = document.getElementById("error");
const result = document.getElementById("result");
const catResult = document.getElementById("cat-result");
const notCatResult = document.getElementById("not-cat-result");
const catKind = document.getElementById("cat-kind");
const catConfidence = document.getElementById("cat-confidence");
const bars = document.getElementById("bars");
const top3 = document.getElementById("top3");

let selectedFile = null;

function percent(value) {
  return `${(value * 100).toFixed(1)}%`;
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = !message;
}

// ---------- Choosing a photo ----------

function selectFile(file) {
  if (!file || !file.type.startsWith("image/")) {
    showError("Please choose an image file.");
    return;
  }
  selectedFile = file;
  preview.src = URL.createObjectURL(file);
  preview.hidden = false;
  dropHint.hidden = true;
  result.hidden = true;
  showError("");
  classifyButton.disabled = false;
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

// ---------- Showing the result ----------

function showCat(output) {
  catKind.textContent = output.cat_kind;
  catConfidence.textContent = percent(output.cat_confidence);

  // Bars show each kind's share of the total cat probability,
  // so the top bar matches the big percentage above.
  const entries = Object.entries(output.cat_probabilities);
  const total = entries.reduce((sum, [, p]) => sum + p, 0) || 1;
  entries.sort((a, b) => b[1] - a[1]);

  bars.replaceChildren();
  for (const [name, probability] of entries) {
    const share = probability / total;
    const li = document.createElement("li");
    if (name === output.cat_kind) li.className = "top";

    const label = document.createElement("div");
    label.className = "bar-label";
    const nameSpan = document.createElement("span");
    nameSpan.textContent = name;
    const valueSpan = document.createElement("span");
    valueSpan.textContent = percent(share);
    label.append(nameSpan, valueSpan);

    const track = document.createElement("div");
    track.className = "bar-track";
    const fill = document.createElement("div");
    fill.className = "bar-fill";
    track.append(fill);

    li.append(label, track);
    bars.append(li);
    // Set the width after insertion so the CSS transition animates it.
    requestAnimationFrame(() => { fill.style.width = `${share * 100}%`; });
  }

  catResult.hidden = false;
  notCatResult.hidden = true;
}

function showNotCat(output) {
  top3.replaceChildren();
  for (const { label, probability } of output.top3_imagenet) {
    const li = document.createElement("li");
    const prob = document.createElement("span");
    prob.className = "prob";
    prob.textContent = ` — ${percent(probability)}`;
    li.append(document.createTextNode(label), prob);
    top3.append(li);
  }
  catResult.hidden = true;
  notCatResult.hidden = false;
}

// ---------- Classifying ----------

classifyButton.addEventListener("click", async () => {
  if (!selectedFile) return;
  classifyButton.disabled = true;
  loading.hidden = false;
  result.hidden = true;
  showError("");

  const form = new FormData();
  form.append("image", selectedFile);

  try {
    const response = await fetch("/api/classify", { method: "POST", body: form });
    const data = await response.json();
    if (!response.ok) {
      showError(data.error || "Something went wrong.");
      return;
    }
    if (data.is_cat) {
      showCat(data);
    } else {
      showNotCat(data);
    }
    result.hidden = false;
  } catch (error) {
    showError("Could not reach the server.");
  } finally {
    loading.hidden = true;
    classifyButton.disabled = false;
  }
});
