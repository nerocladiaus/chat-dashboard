// load & post messages in a single chat room
document.addEventListener('DOMContentLoaded', () => {
  const feed = document.getElementById('feed');
  const form = document.getElementById('postForm');
  const chatId = document.getElementById('chatId').value;
  const socket = io();

  // join Socket.IO room
  socket.emit('join', {chat_id: chatId});
  socket.on('new_message', m => addMsg(m));

  // load history
  fetch(`/api/chats/${chatId}/messages`)
    .then(r=>r.json())
    .then(msgs=>msgs.forEach(addMsg));

  // post form
  form.addEventListener('submit', e => {
    e.preventDefault();
    const user = document.getElementById('user').value.trim();
    const text = document.getElementById('text').value.trim();
    if (!user||!text) return;
    fetch(`/api/chats/${chatId}/messages`, {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({user,text})
    });
  });

  function addMsg(m) {
    const li = document.createElement('li');
    const time = new Date(m.ts||Date.now()).toLocaleTimeString();
    li.textContent = `[${time}] ${m.user}: ${m.text}`;
    feed.appendChild(li);
    feed.scrollTop = feed.scrollHeight;
  }
});