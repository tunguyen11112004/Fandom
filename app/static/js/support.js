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

function wait(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function showTyping() {
  const item = document.createElement("article");
  item.className = "support-msg assistant typing";
  item.innerHTML = "<p>Mina is typing<span></span><span></span><span></span></p>";
  log.appendChild(item);
  log.scrollTop = log.scrollHeight;
  return item;
}

async function send(message) {
  addMessage("user", message);
  input.value = "";
  const typing = showTyping();
  const response = await fetch("/support/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });
  const data = await response.json();
  const text = data.text || data.error || "Sorry, that didn't go through. Try me again?";
  const pause = window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ? 0
    : Math.min(1600, 500 + text.length * 12);
  await wait(pause);
  typing.remove();
  addMessage("assistant", text, data.links || []);
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
