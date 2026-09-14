/* Пополнение. Поле суммы — <input type="text" inputmode="decimal">
   с ограничением длины; разбор и проверка значения живут в js/amount.js.
   Проверка выполняется при отправке формы: ни масок ввода, ни проверки по
   потере фокуса здесь нет. */
(function (Wallet) {
  'use strict';

  function render(host) {
    host.innerHTML =
      '<section class="card card--narrow">' +
        '<h1>Пополнение</h1>' +
        '<form id="topup-form" novalidate>' +
          '<label class="field">' +
            '<span class="field-label">Сумма</span>' +
            '<input type="text" inputmode="decimal" maxlength="9" id="amount" name="amount" autocomplete="off">' +
          '</label>' +
          '<p class="field-error" id="amount-error" hidden></p>' +
          '<button type="submit" class="button button--primary" id="topup-submit">Пополнить</button>' +
        '</form>' +
      '</section>';

    var form = document.getElementById('topup-form');
    var input = document.getElementById('amount');
    var errorNode = document.getElementById('amount-error');

    form.addEventListener('submit', function (event) {
      event.preventDefault();

      var result = Wallet.amount.validate(input.value);
      if (!result.ok) {
        Wallet.ui.setFieldError(errorNode, result.message);
        input.focus();
        return;
      }
      Wallet.ui.setFieldError(errorNode, '');

      Wallet.api.topup(result.value)
        .then(function (payload) {
          var credited = payload && payload.amount !== undefined
            ? payload.amount
            : result.value;

          if (payload && payload.balance !== undefined) {
            Wallet.store.setBalance(payload.balance);
          }

          Wallet.ui.toast(Wallet.messages.topupSuccess(credited));
          input.value = '';
        })
        .catch(function (error) {
          if (Wallet.ui.isUnauthorized(error)) { Wallet.router.navigate('/login'); return; }
          Wallet.ui.setFieldError(errorNode, Wallet.ui.serverErrorText(error));
          input.focus();
        });
    });

    input.focus();
  }

  Wallet.screens = Wallet.screens || {};
  Wallet.screens.topup = { title: 'Пополнение', render: render };
})(window.Wallet = window.Wallet || {});
