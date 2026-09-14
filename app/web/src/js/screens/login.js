/* Экран входа. Регистрации в продукте нет: логин и пароль выдаются
   пользователю. Ссылок «Зарегистрироваться» и «Забыли пароль» на экране
   нет сознательно. */
(function (Wallet) {
  'use strict';

  function render(host) {
    host.innerHTML =
      '<section class="card card--narrow">' +
        '<h1>Вход</h1>' +
        '<form id="login-form" novalidate>' +
          '<label class="field">' +
            '<span class="field-label">Логин</span>' +
            '<input type="text" id="login" name="login" autocomplete="username" autocapitalize="off" spellcheck="false">' +
          '</label>' +
          '<label class="field">' +
            '<span class="field-label">Пароль</span>' +
            '<input type="password" id="password" name="password" autocomplete="current-password">' +
          '</label>' +
          '<p class="field-error" id="login-error" hidden></p>' +
          '<button type="submit" class="button button--primary">Войти</button>' +
        '</form>' +
      '</section>';

    var form = document.getElementById('login-form');
    var loginInput = document.getElementById('login');
    var passwordInput = document.getElementById('password');
    var errorNode = document.getElementById('login-error');

    form.addEventListener('submit', function (event) {
      event.preventDefault();
      Wallet.ui.setFieldError(errorNode, '');

      Wallet.api.login(loginInput.value.trim(), passwordInput.value)
        .then(function (payload) {
          Wallet.store.startSession(payload);
          return Wallet.store.loadBalance();
        })
        .then(function () {
          Wallet.router.navigate('/');
        })
        .catch(function (error) {
          Wallet.ui.setFieldError(
            errorNode,
            Wallet.ui.serverMessageText(error, Wallet.messages.REQUEST_FAILED)
          );
          passwordInput.value = '';
          loginInput.focus();
        });
    });

    loginInput.focus();
  }

  Wallet.screens = Wallet.screens || {};
  Wallet.screens.login = { title: 'Вход', render: render, guest: true };
})(window.Wallet = window.Wallet || {});
