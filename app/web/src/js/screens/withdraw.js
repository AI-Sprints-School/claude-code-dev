/* Списание. Поле «Сумма», подпись про комиссию, кнопка «Списать».
   Правила удержания комиссии описаны на странице /tariffs. */
(function (Wallet) {
  'use strict';

  function render(host) {
    host.innerHTML =
      '<section class="card card--narrow">' +
        '<h1>Списание</h1>' +
        '<form id="withdraw-form" novalidate>' +
          '<label class="field">' +
            '<span class="field-label">Сумма</span>' +
            '<input type="text" inputmode="decimal" maxlength="9" id="amount" name="amount" autocomplete="off">' +
          '</label>' +
          '<p class="hint">Комиссия 1,5%, минимум 10 ₽</p>' +
          '<p class="field-error" id="amount-error" hidden></p>' +
          '<button type="submit" class="button button--primary" id="withdraw-submit">Списать</button>' +
        '</form>' +
      '</section>';

    var form = document.getElementById('withdraw-form');
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

      /* Клиент сам отклоняет списание больше баланса. */
      var balance = Wallet.store.getBalance();
      if (balance !== null && balance !== undefined && result.value > balance) {
        Wallet.ui.setFieldError(errorNode, Wallet.messages.INSUFFICIENT_FUNDS);
        input.focus();
        return;
      }

      Wallet.ui.setFieldError(errorNode, '');

      Wallet.api.withdraw(result.value)
        .then(function (payload) {
          var spent = payload && payload.amount !== undefined ? payload.amount : result.value;
          var fee = payload && payload.fee !== undefined ? payload.fee : 0;

          if (payload && payload.balance !== undefined) {
            Wallet.store.setBalance(payload.balance);
          }

          Wallet.ui.toast(Wallet.messages.withdrawSuccess(spent, fee));
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
  Wallet.screens.withdraw = { title: 'Списание', render: render };
})(window.Wallet = window.Wallet || {});
