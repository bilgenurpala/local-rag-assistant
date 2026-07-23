const statusElement = document.getElementById("model-status");
const statusContainer = statusElement.parentElement;
const sourceList = document.getElementById("source-list");
const form = document.getElementById("ask-form");
const input = document.getElementById("question");
const sendButton = document.getElementById("send-button");
const requestState = document.getElementById("request-state");
const chatBody = document.getElementById("chat-body");
const copyButton = document.getElementById("copy-code");
const quickstartCode = document.getElementById("quickstart-code");

function createMessage(role, text) {
  const wrapper = document.createElement("div");
  wrapper.className = role === "user" ? "user-message" : "assistant-message";

  const paragraph = document.createElement("p");
  paragraph.textContent = text;
  wrapper.appendChild(paragraph);

  chatBody.appendChild(wrapper);
  chatBody.scrollTop = chatBody.scrollHeight;
}

async function loadHealth() {
  try {
    const response = await fetch("/api/health");
    const data = await response.json();
    statusElement.textContent = data.status === "ready" ? "Local models ready" : "Models load on first question";
    statusContainer.classList.add("ready");
  } catch {
    statusElement.textContent = "Local API unavailable";
  }
}

async function loadSources() {
  try {
    const response = await fetch("/api/sources");
    const sources = await response.json();
    sourceList.replaceChildren();
    sources.forEach((source) => {
      const item = document.createElement("span");
      item.className = "source-item";
      item.textContent = source.title;
      sourceList.appendChild(item);
    });
  } catch {
    sourceList.textContent = "Local sources could not be loaded.";
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = input.value.trim();
  if (!question) {
    return;
  }

  createMessage("user", question);
  input.value = "";
  input.disabled = true;
  sendButton.disabled = true;
  requestState.textContent = "Searching local documentation and generating an answer...";

  try {
    const response = await fetch("/api/ask", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({question})
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "The assistant could not answer.");
    }
    createMessage("assistant", data.answer);
    statusElement.textContent = "Local models ready";
    statusContainer.classList.add("ready");
    requestState.textContent = "";
  } catch (error) {
    createMessage("assistant", error.message);
    requestState.textContent = "Check the local runtime and try again.";
  } finally {
    input.disabled = false;
    sendButton.disabled = false;
    input.focus();
  }
});

document.querySelectorAll(".suggestions button").forEach((button) => {
  button.addEventListener("click", () => {
    input.value = button.textContent.trim();
    input.focus();
  });
});

copyButton.addEventListener("click", async () => {
  await navigator.clipboard.writeText(quickstartCode.textContent);
  copyButton.textContent = "Copied";
  window.setTimeout(() => {
    copyButton.textContent = "Copy";
  }, 1200);
});

loadHealth();
loadSources();
