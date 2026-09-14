/* Тарифы и правила. Публичная документация продукта: текст дословный,
   правкам не подлежит. */
(function (Wallet) {
  'use strict';

  var TARIFFS_TEXT = "Тариф BASIC (по умолчанию)\n  Пополнение счёта — без комиссии.\n  Списание — 1,5% от суммы, минимум 10 ₽. Комиссия показывается\n  отдельной строкой в истории операций.\n  Максимальная сумма одной операции — 100 000 ₽.\n  Минимальная сумма одной операции — 0,01 ₽.\n\nТариф FREE (демонстрационный)\n  Все операции без комиссии. Лимиты те же.";

  function render(host) {
    host.innerHTML =
      '<section class="card">' +
        '<h1>Тарифы и правила</h1>' +
        '<pre class="tariffs-text">' + Wallet.ui.escapeHtml(TARIFFS_TEXT) + '</pre>' +
      '</section>';
  }

  Wallet.screens = Wallet.screens || {};
  Wallet.screens.tariffs = { title: 'Тарифы и правила', render: render, public: true };
})(window.Wallet = window.Wallet || {});
