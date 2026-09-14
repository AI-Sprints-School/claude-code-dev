/* История операций (4.2): таблица, фильтр «Все / Пополнения / Списания»,
   постранично по 20 с кнопкой «Показать ещё». */
(function (Wallet) {
  'use strict';

  var FILTER_ORDER = ['ALL', 'TOPUP', 'WITHDRAW'];
  var currentFilter = 'ALL';

  function filtersHtml() {
    return '<div class="filters" role="group" aria-label="Фильтр операций">' +
      FILTER_ORDER.map(function (key) {
        var active = key === currentFilter ? ' active' : '';
        return '<button type="button" class="filter' + active + '" data-filter="' + key + '">' +
          Wallet.ui.escapeHtml(Wallet.store.FILTERS[key].label) + '</button>';
      }).join('') + '</div>';
  }

  function render(host) {
    host.innerHTML =
      '<section class="card">' +
        '<h1>История операций</h1>' +
        filtersHtml() +
        '<div id="history-list"><p class="empty">Загрузка…</p></div>' +
        '<div class="more-box">' +
          '<button type="button" class="button" id="show-more" hidden>Показать ещё</button>' +
          '<span class="counter" id="history-counter"></span>' +
        '</div>' +
      '</section>';

    var list = document.getElementById('history-list');
    var moreButton = document.getElementById('show-more');
    var counter = document.getElementById('history-counter');

    function paint(page) {
      list.innerHTML = Wallet.operationsView.render(page.items);
      moreButton.hidden = page.items.length >= page.total;
      counter.textContent = page.total
        ? 'Показано ' + page.items.length + ' из ' + page.total
        : '';
    }

    function fail(error) {
      if (Wallet.ui.isUnauthorized(error)) { Wallet.router.navigate('/login'); return; }
      list.innerHTML = '<p class="field-error">' +
        Wallet.ui.escapeHtml(Wallet.messages.REQUEST_FAILED) + '</p>';
    }

    function load() {
      Wallet.store.loadOperations(currentFilter, { force: Wallet.ui.isMobile() })
        .then(paint)
        .catch(fail);
    }

    host.querySelectorAll('[data-filter]').forEach(function (button) {
      button.addEventListener('click', function () {
        currentFilter = button.getAttribute('data-filter');
        host.querySelectorAll('[data-filter]').forEach(function (other) {
          other.classList.toggle('active', other === button);
        });
        list.innerHTML = '<p class="empty">Загрузка…</p>';
        moreButton.hidden = true;
        load();
      });
    });

    moreButton.addEventListener('click', function () {
      Wallet.store.loadMoreOperations(currentFilter).then(paint).catch(fail);
    });

    load();
  }

  Wallet.screens = Wallet.screens || {};
  Wallet.screens.history = { title: 'История операций', render: render };
})(window.Wallet = window.Wallet || {});
