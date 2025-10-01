const openBtn = document.getElementById('open-chat');
const closeBtn = document.getElementById('close-chat');
const chatArea = document.getElementById('chat-area');
const sendBtn = document.getElementById('send-chat');
const clearBtn = document.getElementById('clear-chat');
const input = document.getElementById('chat-input');
const messages = document.getElementById('messages');
const header = document.querySelector('.support-header');

function loadMessages() {
  fetch('/get_messages')
    .then(res => res.json())
    .then(data => {
      messages.innerHTML = '';
      data.forEach(item => {
        const div = document.createElement('div');
        div.className = 'message ' + item.sender;
        div.textContent = item.content;
        messages.appendChild(div);
      });
      messages.scrollTop = messages.scrollHeight;
    })
    .catch(err => console.error('Load messages error:', err));
}

openBtn.addEventListener('click', () => {
  if (!userEmail || userEmail === "None") {
    alert("Bạn cần đăng nhập để nhắn tin!");
    return;
  }
  document.querySelector('.support-widget').classList.add('open');
  header.classList.remove('hidden');
  chatArea.classList.remove('hidden');
  closeBtn.classList.remove('hidden');
  openBtn.style.display = 'none';
  loadMessages();
});

closeBtn.addEventListener('click', () => {
   document.querySelector('.support-widget').classList.remove('open');
  header.classList.add('hidden');
  chatArea.classList.add('hidden');
  closeBtn.classList.add('hidden');
  openBtn.style.display = 'inline-flex';
});

sendBtn.addEventListener('click', () => {
  const msg = input.value.trim();
  if (msg === '') return;

  fetch('/send_message', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: msg, sender: 'user' })
  })
    .then(() => {
      input.value = '';
      loadMessages();

      let sentCount = parseInt(localStorage.getItem('sentCount')) || 0;
      sentCount++;
      localStorage.setItem('sentCount', sentCount);

      if (sentCount === 1) {
        setTimeout(() => {
          fetch('/send_message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: 'Xin chào! Tôi có thể giúp gì cho bạn?', sender: 'agent' })
          }).then(loadMessages);
        }, 500);
      }

      if (sentCount === 2) {
        setTimeout(() => {
          fetch('/send_message', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: 'Bạn đợi chút nhé, nhân viên sẽ trả lời bạn sau.', sender: 'agent' })
          }).then(loadMessages);
        }, 500);
      }
    })
    .catch(err => console.error('Send message error:', err));
});

clearBtn.addEventListener('click', () => {
  if (!userEmail || userEmail === "None") {
    alert("Bạn chưa đăng nhập!");
    return;
  }

  fetch('/clear_messages', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email: userEmail })
  })
    .then(() => {
      localStorage.removeItem('sentCount');
      loadMessages();
    })
    .catch(err => console.error('Clear messages error:', err));
});