// load list of chats & handle creation
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('newChatForm');
  const list = document.getElementById('chatsList');

  fetch('/api/chats')
    .then(r => r.json())
    .then(chats => chats.forEach(c => addChat(c)));

  form.addEventListener('submit', e => {
    e.preventDefault();
    const name = document.getElementById('chatName').value.trim();
    if (!name) return;
    fetch('/api/chats', {
      method: 'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({name})
    })
      .then(r=>r.json())
      .then(c => addChat(c));
  });

  function addChat(c) {
    const li = document.createElement('li');
    li.innerHTML = `<a href="/chat/${c.id}">${c.name}</a>`;
    list.appendChild(li);
  }
});