// All arithmetic is done by the Flask backend. Resolves with the result,
// or rejects with the "error" message sent by the server.
async function calculate(x, operation, y) {
    let response;
    try {
        response = await fetch("/api/calculate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ x: x, y: y, operation: operation }),
        });
    } catch (err) {
        throw new Error("Server unavailable");
    }

    let data = null;
    try {
        data = await response.json();
    } catch (err) {
        // Not a JSON reply (e.g. an HTML error page); handled below
    }

    if (!response.ok || data === null || typeof data !== "object") {
        throw new Error((data && data.error) || "Server error (" + response.status + ")");
    }
    return data.result;
}

const MAX_DIGITS = 16;

const display = document.getElementById("display");

let current = "0";        // number currently being typed / shown
let firstNumber = null;   // stored left-hand operand
let operation = null;     // stored operation name
let startNew = true;      // next digit starts a fresh number
let waiting = false;      // a request to the server is in progress
let hasError = false;     // an error message is shown instead of a number

function updateDisplay() {
    hasError = false;
    display.classList.remove("error");
    display.textContent = current;
}

function clearAll() {
    current = "0";
    firstNumber = null;
    operation = null;
    startNew = true;
    updateDisplay();
}

function showError(message) {
    clearAll();   // next digit starts a fresh number
    hasError = true;
    display.classList.add("error");
    display.textContent = message;
}

function inputDigit(digit) {
    if (waiting) return;
    if (startNew) {
        current = digit === "." ? "0." : digit;
        startNew = false;
    } else if (digit === ".") {
        if (current.includes(".")) return;
        current += ".";
    } else if (current === "0") {
        current = digit;
    } else {
        if (current.replace(/[-.]/g, "").length >= MAX_DIGITS) return;
        current += digit;
    }
    updateDisplay();
}

// Asks the server for firstNumber <operation> current; returns false on an error.
async function evaluatePending() {
    waiting = true;
    try {
        const result = await calculate(firstNumber, operation, parseFloat(current));
        current = String(result);
        updateDisplay();
        return true;
    } catch (err) {
        showError(err.message);
        return false;
    } finally {
        waiting = false;
    }
}

async function chooseOperation(op) {
    // After an error there is no number to operate on; wait for a digit
    if (waiting || hasError) return;
    // A second operator after typing another number chains the calculation (2 + 3 + → 5)
    if (operation !== null && !startNew) {
        if (!(await evaluatePending())) return;
    }
    firstNumber = parseFloat(current);
    operation = op;
    startNew = true;
}

async function equals() {
    if (waiting || operation === null) return;
    if (!(await evaluatePending())) return;
    firstNumber = null;
    operation = null;
    startNew = true;
}

function backspace() {
    if (waiting || startNew) return;   // don't edit a result
    current = current.slice(0, -1);
    if (current === "" || current === "-") {
        current = "0";
    }
    updateDisplay();
}

// Mouse input
document.querySelectorAll(".digit").forEach((button) => {
    button.addEventListener("click", () => inputDigit(button.dataset.value));
});

document.querySelectorAll(".operator").forEach((button) => {
    button.addEventListener("click", () => chooseOperation(button.dataset.op));
});

document.getElementById("equals").addEventListener("click", equals);

display.addEventListener("click", clearAll);

// Keyboard input
const KEY_OPERATIONS = {
    "+": "add",
    "-": "subtract",
    "*": "multiply",
    "/": "divide",
};

document.addEventListener("keydown", (event) => {
    // Leave browser shortcuts such as Ctrl + / Ctrl - (zoom) alone
    if (event.ctrlKey || event.metaKey || event.altKey) return;

    const key = event.key;

    if (/^[0-9.]$/.test(key)) {
        inputDigit(key);
    } else if (key in KEY_OPERATIONS) {
        chooseOperation(KEY_OPERATIONS[key]);
    } else if (key === "Enter" || key === "=") {
        equals();
    } else if (key === "Backspace") {
        backspace();
    } else if (key === "Escape") {
        clearAll();
    } else {
        return;
    }

    // Stops "/" opening quick-find and Enter re-clicking a focused button
    event.preventDefault();
});
