/* Тексты сообщений продукта, в одном месте.
   Разряды разделены неразрывным пробелом, знак рубля — обычным. */
(function (Wallet) {
  'use strict';

  Wallet.messages = {
    EMPTY: 'Введите сумму',
    NOT_A_NUMBER: 'Сумма должна быть числом',
    NOT_POSITIVE: 'Сумма должна быть больше нуля',
    TOO_MANY_DECIMALS: 'Не больше двух знаков после запятой',
    OVER_LIMIT: 'Максимальная сумма одной операции — 100 000 ₽',
    INSUFFICIENT_FUNDS: 'Недостаточно средств на балансе',
    REQUEST_FAILED: 'Не удалось выполнить операцию, попробуйте ещё раз',
    INVALID_CREDENTIALS: 'Неверный логин или пароль',
    ASSISTANT_UNAVAILABLE: 'Ассистент временно недоступен, попробуйте позже'
  };

  /* Всплывающие сообщения об успехе (4.5). */
  Wallet.messages.topupSuccess = function (amount) {
    return 'Баланс пополнен на ' + Wallet.format.money(amount);
  };

  Wallet.messages.withdrawSuccess = function (amount, fee) {
    return 'Списано ' + Wallet.format.money(amount) +
      ', комиссия ' + Wallet.format.money(fee);
  };
})(window.Wallet = window.Wallet || {});
