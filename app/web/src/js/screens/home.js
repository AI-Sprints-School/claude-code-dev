/* Главная (4.2): шапка с балансом (см. js/chrome.js), кнопки «Пополнить»
   и «Списать», последние 5 операций. */
(function (Wallet) {
  'use strict';

  var LAST_OPERATIONS = 5;

  function render(host) {
    host.innerHTML =
      '<section class="card">' +
        '<h1>Главная</h1>' +
        '<div class="actions">' +
          '<a class="button button--primary" href="' + Wallet.router.href('/topup') + '" data-link>Пополнить</a>' +
          '<a class="button" href="' + Wallet.router.href('/withdraw') + '" data-link>Списать</a>' +
        '</div>' +
      '</section>' +
      '<section class="card">' +
        '<div class="card-head">' +
          '<h2>Последние операции</h2>' +
          '<a href="' + Wallet.router.href('/history') + '" data-link>Вся история</a>' +
        '</div>' +
        '<div id="home-operations"><p class="empty">Загрузка…</p></div>' +
      '</section>';

    var box = document.getElementById('home-operations');

    Wallet.store.loadOperations('ALL', { force: Wallet.ui.isMobile() })
      .then(function (page) {
        box.innerHTML = Wallet.operationsView.render(page.items.slice(0, LAST_OPERATIONS));
      })
      .catch(function (error) {
        if (Wallet.ui.isUnauthorized(error)) { Wallet.router.navigate('/login'); return; }
        box.innerHTML = '<p class="field-error">' +
          Wallet.ui.escapeHtml(Wallet.messages.REQUEST_FAILED) + '</p>';
      });
  }

  Wallet.screens = Wallet.screens || {};
  Wallet.screens.home = { title: 'Главная', render: render };
})(window.Wallet = window.Wallet || {});
