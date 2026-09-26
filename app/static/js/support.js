const toggle = document.querySelector(".support-toggle");
const panel = document.querySelector(".support-panel");
const log = document.querySelector(".support-log");
const form = document.querySelector(".support-form");
const input = document.querySelector("#support-q");
const closeButton = document.querySelector(".support-close");

function addMessage(role, text, links) {
  const item = document.createElement("article");
  item.className = `support-msg ${role}`;
  const body = document.createElement("p");
  body.textContent = text;
  item.appendChild(body);
  if (links && links.length) {
    const list = document.createElement("p");
    list.className = "support-links";
    links.forEach((link) => {
      const anchor = document.createElement("a");
      anchor.href = link.href;
      anchor.textContent = link.label;
      list.appendChild(anchor);
    });
    item.appendChild(list);
  }
  log.appendChild(item);
  log.scrollTop = log.scrollHeight;
}

function setOpen(open) {
  panel.hidden = !open;
  toggle.setAttribute("aria-expanded", open ? "true" : "false");
  if (open) input.focus();
}

async function send(message) {
  addMessage("user", message);
  input.value = "";
  const item = document.createElement("article");
  item.className = "support-msg assistant";
  const body = document.createElement("p");
  item.appendChild(body);
  log.appendChild(item);
  const csrf = document.querySelector('meta[name="csrf"]');
  try {
    const response = await fetch("/support/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrf ? csrf.getAttribute("content") || "" : "",
      },
      body: JSON.stringify({ message }),
    });
    if (!response.ok || !response.body) {
      const failed = await response.json().catch(() => ({}));
      body.textContent = failed.error || "Sorry, that didn't go through. Try me again?";
      return;
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";
      lines.forEach((line) => {
        if (!line.startsWith("data: ")) return;
        const raw = line.slice(6).trim();
        if (!raw) return;
        const parsed = JSON.parse(raw);
        if (parsed.text) {
          body.textContent += parsed.text;
          log.scrollTop = log.scrollHeight;
        }
        if (parsed.links && parsed.links.length) {
          const list = document.createElement("p");
          list.className = "support-links";
          parsed.links.forEach((link) => {
            const anchor = document.createElement("a");
            anchor.href = link.href;
            anchor.textContent = link.label;
            list.appendChild(anchor);
          });
          item.appendChild(list);
        }
        if (parsed.error) body.textContent = parsed.error;
      });
    }
    if (!body.textContent) body.textContent = "Sorry, that didn't go through. Try me again?";
  } catch (err) {
    body.textContent = "Sorry, that didn't go through. Try me again?";
  }
}

toggle.addEventListener("click", () => setOpen(panel.hidden));
document.querySelectorAll(".footer-chat").forEach((button) => {
  button.addEventListener("click", () => setOpen(true));
});
closeButton.addEventListener("click", () => setOpen(false));

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const message = input.value.trim();
  if (message) send(message);
});

document.querySelectorAll("[data-prompt]").forEach((button) => {
  button.addEventListener("click", () => send(button.dataset.prompt));
});

fetch("/support/history")
  .then((response) => response.json())
  .then((data) => {
    (data.messages || []).forEach((message) => addMessage(message.role, message.text));
    if (!data.messages || !data.messages.length) {
      addMessage(
        "assistant",
        "Hey, Mina here. One Piece, Naruto, or something newer? Tell me what you're in the mood for."
      );
    }
  });
