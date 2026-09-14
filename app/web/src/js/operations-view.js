/* Отрисовка списка операций. Десктоп — таблица (дата, тип, сумма,
   комментарий), мобильная вёрстка — карточки: на экране 360 px таблица
   в четыре колонки нечитаема. */
(function (Wallet) {
  'use strict';

  var escape = function (value) { return Wallet.ui.escapeHtml(value); };

  function amountCell(operation) {
    var sign = operation.type === 'TOPUP' ? '+' : '−';
    return sign + ' ' + Wallet.format.money(Math.abs(Number(operation.amount)));
  }

  function desktopTable(items) {
    if (!items.length) {
      return '<p class="empty">Операций нет</p>';
    }
    var rows = items.map(function (operation) {
      return '<tr>' +
        '<td>' + escape(Wallet.format.dateTime(operation.created_at)) + '</td>' +
        '<td>' + escape(Wallet.format.operationType(operation.type)) + '</td>' +
        '<td class="amount amount--' + escape(operation.type) + '">' +
          escape(amountCell(operation)) + '</td>' +
        '<td>' + escape(operation.comment || '') + '</td>' +
      '</tr>';
    }).join('');

    return '<table class="operations">' +
      '<thead><tr><th>Дата</th><th>Тип</th><th>Сумма</th><th>Комментарий</th></tr></thead>' +
      '<tbody>' + rows + '</tbody></table>';
  }

  function mobileList(items) {
    if (!items.length) {
      return '<p class="empty">Операций нет</p>';
    }
    return '<ul class="operations-list">' + items.map(function (operation) {
      return '<li class="operation-card">' +
        '<div class="operation-card__top">' +
          '<span class="operation-card__type">' +
            escape(Wallet.format.operationType(operation.type)) + '</span>' +
          '<span class="amount amount--' + escape(operation.type) + '">' +
            escape(amountCell(operation)) + '</span>' +
        '</div>' +
        '<div class="operation-card__bottom">' +
          '<span>' + escape(Wallet.format.dateTime(operation.created_at)) + '</span>' +
          '<span>' + escape(operation.comment || '') + '</span>' +
        '</div>' +
      '</li>';
    }).join('') + '</ul>';
  }

  function render(items) {
    return Wallet.ui.isMobile() ? mobileList(items) : desktopTable(items);
  }

  Wallet.operationsView = { render: render };
})(window.Wallet = window.Wallet || {});
