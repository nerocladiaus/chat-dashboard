const socket = io();
const feed = document.getElementById("feed");
const form = document.getElementById("postForm");
const inpUser = document.getElementById("user");
const inpText = document.getElementById("text");

// Load history
fetch("/api/messages")
  .then((r) => r.json())
  .then((msgs) => msgs.forEach(addMsg));

// Listen for new messages
socket.on("new_message", addMsg);

// Post form handler
form.addEventListener("submit", (e) => {
  e.preventDefault();
  const user = inpUser.value.trim();
  const text = inpText.value.trim();
  if (!user || !text) return;

  fetch("/api/messages", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user, text }),
  })
    .then((r) => {
      if (!r.ok) throw new Error("Post failed");
      inpText.value = "";
      inpText.focus();
    })
    .catch(console.error);
});

function addMsg(m) {
  const li = document.createElement("li");
  const ts = new Date(m.ts || Date.now()).toLocaleTimeString();
  li.textContent = `[${ts}] ${m.user}: ${m.text}`;
  feed.appendChild(li);
  // keep scroll at bottom
  feed.scrollTop = feed.scrollHeight;
}
