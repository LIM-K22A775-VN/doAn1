const chatList = document.getElementById('chat-list');
const messages = document.getElementById('messages');
const sendBtn = document.getElementById('send-chat');
const input = document.getElementById('chat-input');
let currentReceiver = null;

// Load danh sách đoạn chat
function loadChatList() {
  fetch('/admin_nt/get_conversations')
    .then(res => res.json())
    .then(data => {
      chatList.innerHTML = '';
      data.forEach(item => {
        const div = document.createElement('div');
        div.className = 'chat-item';
        // Sử dụng avatar từ backend, fallback nếu không có
        const avatar = item.avatar ? item.avatar : 'default.jpg';
div.innerHTML = `
  <img src="/static/avatars/${avatar}" alt="Avatar">
  <div class="info">
    <div class="name">${item.name}</div>
    <div class="last-message">${item.last_message}</div>
  </div>
`;

        div.addEventListener('click', () => {
          currentReceiver = item.id;
          loadMessages(currentReceiver);
        });
        chatList.appendChild(div);
      });
    });
}

// Load tin nhắn chi tiết
function loadMessages(receiver) {
  fetch(`/admin_nt/get_messages?user_id=${receiver}`)
    .then(res => res.json())
    .then(data => {
      messages.innerHTML = '';
      data.forEach(msg => {
        const div = document.createElement('div');
        div.className = 'message ' + msg.sender;
        div.textContent = msg.content;
        messages.appendChild(div);
      });
      messages.scrollTop = messages.scrollHeight;
    });
}

// Gửi tin nhắn
sendBtn.addEventListener('click', () => {
  const msg = input.value.trim();
  if (msg && currentReceiver) {
    fetch('/admin_nt/send_message', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        receiver_id: currentReceiver,
        message: msg,
        sender: 'agent'
      })
    }).then(() => {
      input.value = '';
      loadMessages(currentReceiver);
    });
  }
});

// Tải danh sách khi vào trang
loadChatList();
