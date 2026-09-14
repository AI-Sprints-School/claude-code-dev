/* Мелкие помощники интерфейса: точка останова вёрстки, всплывающие
   сообщения, вывод ошибки под полем. */
(function (Wallet) {
  'use strict';

  var MOBILE_BREAKPOINT = 600; // ниже этой ширины включается мобильная вёрстка

  function isMobile() {
    return window.innerWidth < MOBILE_BREAKPOINT;
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /* Всплывающее сообщение об успехе (4.5). Держится 5 секунд.
     Каждый вызов добавляет отдельное сообщение. */
  function toast(text) {
    var host = document.getElementById('toasts');
    if (!host) { return; }
    var node = document.createElement('div');
    node.className = 'toast';
    node.textContent = text;
    host.appendChild(node);
    window.setTimeout(function () {
      if (node.parentNode) { node.parentNode.removeChild(node); }
    }, 5000);
  }

  function setFieldError(errorNode, text) {
    errorNode.textContent = text || '';
    errorNode.hidden = !text;
  }

  /* Отрисовка ошибки, пришедшей от сервера. */
  function serverErrorText(error) {
    if (error instanceof Wallet.api.ApiError && error.code) {
      return error.code;
    }
    return Wallet.messages.REQUEST_FAILED;
  }

  /* Вход и ассистент: человеческий текст сообщения. */
  function serverMessageText(error, fallback) {
    if (error instanceof Wallet.api.ApiError && error.serverMessage) {
      return error.serverMessage;
    }
    return fallback || Wallet.messages.REQUEST_FAILED;
  }

  function isUnauthorized(error) {
    return error instanceof Wallet.api.ApiError && error.status === 401;
  }

  Wallet.ui = {
    MOBILE_BREAKPOINT: MOBILE_BREAKPOINT,
    isMobile: isMobile,
    escapeHtml: escapeHtml,
    toast: toast,
    setFieldError: setFieldError,
    serverErrorText: serverErrorText,
    serverMessageText: serverMessageText,
    isUnauthorized: isUnauthorized
  };
})(window.Wallet = window.Wallet || {});
