/* Разбор и проверка суммы. Сборка 1.4.0 (140).

   Порядок проверок:
     пусто -> не число -> больше двух знаков -> ноль -> меньше минимума ->
     больше максимума. */
(function (Wallet) {
  'use strict';

  var MAX_OPERATION_AMOUNT = 100000;
  var MIN_OPERATION_AMOUNT = 0.01;

  /* Запятая и точка равноправны, нормализуются в точку (4.3). */
  function normalize(raw) {
    return String(raw).trim().replace(/,/g, '.');
  }

  function validate(raw) {
    var messages = Wallet.messages;

    if (String(raw).trim() === '') {
      return { ok: false, message: messages.EMPTY };
    }

    var normalized = normalize(raw);

    /* Пробел внутри числа, буквы, разделители разрядов — всё сюда. */
    if (!/^-?\d+(\.\d+)?$/.test(normalized)) {
      return { ok: false, message: messages.NOT_A_NUMBER };
    }

    var dot = normalized.indexOf('.');
    if (dot !== -1 && normalized.length - dot - 1 > 2) {
      return { ok: false, message: messages.TOO_MANY_DECIMALS };
    }

    /* Ведущие нули отбрасываются здесь: '007' -> 7 (4.3). */
    var value = parseFloat(normalized);

    if (value === 0) {
      return { ok: false, message: messages.NOT_POSITIVE };
    }

    /* Проверки на минимум здесь нет намеренно: до неё нельзя добраться.
       Проверка на два знака после запятой стоит выше и перехватывает любой
       ввод меньше копейки. Минимум в 0,01 ₽ ею и обеспечен. */

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
