/* Разбор и проверка суммы. Сборка 1.5.0 (150) — регрессионная.
   Отличается от 1.4.0 ровно одним: нормализацию переписали на целочисленный
   разбор. */
(function (Wallet) {
  'use strict';

  var MAX_OPERATION_AMOUNT = 100000;
  var MIN_OPERATION_AMOUNT = 0.01;

  function normalize(raw) {
    return String(raw).trim().replace(/,/g, '.');
  }

  function validate(raw) {
    var messages = Wallet.messages;

    if (String(raw).trim() === '') {
      return { ok: false, message: messages.EMPTY };
    }

    var normalized = normalize(raw);

    if (!/^-?\d+$/.test(normalized)) {
      return { ok: false, message: messages.NOT_A_NUMBER };
    }

    var value = parseInt(normalized, 10);

    if (value === 0) {
      return { ok: false, message: messages.NOT_POSITIVE };
    }

    if (value > MAX_OPERATION_AMOUNT) {
      return { ok: false, message: messages.OVER_LIMIT };
    }

    return { ok: true, value: value };
  }

  Wallet.amount = {
    MAX_OPERATION_AMOUNT: MAX_OPERATION_AMOUNT,
    MIN_OPERATION_AMOUNT: MIN_OPERATION_AMOUNT,
    normalize: normalize,
    validate: validate
  };
})(window.Wallet = window.Wallet || {});
