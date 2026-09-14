/* Форматирование сумм и дат.
   Правило продукта: неразрывный пробел между разрядами, запятая перед
   копейками, знак рубля через пробел — 1 000,00 ₽. */
(function (Wallet) {
  'use strict';

  var GROUP_SEPARATOR = ' '; // неразрывный пробел между разрядами
  var RUBLE_SEPARATOR = ' ';      // обычный пробел перед знаком рубля

  function groupDigits(digits) {
    var head = digits;
    var groups = [];
    while (head.length > 3) {
      groups.unshift(head.slice(-3));
      head = head.slice(0, -3);
    }
    groups.unshift(head);
    return groups.join(GROUP_SEPARATOR);
  }

  /* 1000 -> «1 000,00» */
  function amount(value) {
    var number = Number(value);
    if (isNaN(number)) { return String(value); }
    var sign = number < 0 ? '-' : '';
    var fixed = Math.abs(number).toFixed(2).split('.');
    return sign + groupDigits(fixed[0]) + ',' + fixed[1];
  }

  /* 1000 -> «1 000,00 ₽» */
  function money(value) {
    return amount(value) + RUBLE_SEPARATOR + '₽';
  }

  function pad(number) {
    return number < 10 ? '0' + number : String(number);
  }

  /* '2026-09-08T12:04:11Z' -> «08.09.2026, 12:04» (локальное время браузера) */
  function dateTime(iso) {
    var date = new Date(iso);
    if (isNaN(date.getTime())) { return String(iso); }
    return pad(date.getDate()) + '.' + pad(date.getMonth() + 1) + '.' +
      date.getFullYear() + ', ' + pad(date.getHours()) + ':' + pad(date.getMinutes());
  }

  var OPERATION_TYPES = {
    TOPUP: 'Пополнение',
    WITHDRAW: 'Списание',
    FEE: 'Комиссия'
  };

  function operationType(type) {
    return OPERATION_TYPES[type] || type;
  }

  Wallet.format = {
    amount: amount,
    money: money,
    dateTime: dateTime,
    operationType: operationType
  };
})(window.Wallet = window.Wallet || {});
