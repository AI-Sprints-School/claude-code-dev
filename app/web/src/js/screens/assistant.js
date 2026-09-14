/* AI-ассистент. Веб-клиент здесь — только окно чата: инструменты,
   системный промпт и лимиты живут на бэкенде.
   Контракт эндпоинта минимальный:
   POST {apiBase}/assistant/message  {"message": "..."} -> {"reply": "..."} */
(function (Wallet) {
  'use strict';

  var MAX_CHARS = 1000; // 6.3

  function render(host) {
    host.innerHTML =
      '<section class="card">' +
        '<h1>Ассистент</h1>' +
        '<div class="chat" id="chat"></div>' +
        '<form id="chat-form" novalidate>' +
          '<label class="field">' +
            '<span class="field-label">Сообщение</span>' +
            '<input type="text" id="chat-input" maxlength="' + MAX_CHARS + '" autocomplete="off">' +
          '</label>' +
          '<div class="actions">' +
            '<button type="submit" class="button button--primary">Отправить</button>' +
            '<button type="button" class="button" id="chat-retry" hidden>Повторить</button>' +
          '</div>' +
        '</form>' +
      '</section>';

    var chat = document.getElementById('chat');
    var form = document.getElementById('chat-form');
    var input = document.getElementById('chat-input');
    var retry = document.getElementById('chat-retry');
    var lastMessage = null;

    function append(role, text) {
      var node = document.createElement('div');
      node.className = 'chat-message chat-message--' + role;
      node.textContent = text;
      chat.appendChild(node);
      chat.scrollTop = chat.scrollHeight;
    }

    function send(text) {
      lastMessage = text;
      retry.hidden = true;
      Wallet.api.assistant(text)
        .then(function (payload) {
          append('assistant', (payload && payload.reply) || '');
        })
        .catch(function (error) {
          if (Wallet.ui.isUnauthorized(error)) { Wallet.router.navigate('/login'); return; }
          append('assistant', Wallet.ui.serverMessageText(
            error, Wallet.messages.ASSISTANT_UNAVAILABLE
          ));
          retry.hidden = false;
        });
    }

    form.addEventListener('submit', function (event) {
      event.preventDefault();
      var text = input.value.trim();
      if (!text) { return; }
      append('user', text);
      input.value = '';
      send(text);
    });

    retry.addEventListener('click', function () {
      if (lastMessage) { send(lastMessage); }
    });

    input.focus();
  }

  Wallet.screens = Wallet.screens || {};
  Wallet.screens.assistant = { title: 'Ассистент', render: render };
})(window.Wallet = window.Wallet || {});
