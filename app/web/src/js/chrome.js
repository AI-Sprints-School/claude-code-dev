/* Шапка с балансом и навигация. Перерисовывается при смене маршрута
   и при смене режима вёрстки. */
(function (Wallet) {
  'use strict';

  var NAV = [
    { path: '/', title: 'Главная' },
    { path: '/topup', title: 'Пополнить' },
    { path: '/withdraw', title: 'Списать' },
    { path: '/history', title: 'История' },
    { path: '/assistant', title: 'Ассистент' },
    { path: '/tariffs', title: 'Тарифы' }
  ];

  function balanceText() {
    var balance = Wallet.store.getBalance();
    return balance === null || balance === undefined
      ? '—'
      : Wallet.format.money(balance);
  }

  function navHtml(route) {
    return '<nav class="app-nav">' + NAV.map(function (item) {
      var active = item.path === route ? ' class="active"' : '';
      return '<a href="' + Wallet.router.href(item.path) + '" data-link' + active + '>' +
        Wallet.ui.escapeHtml(item.title) + '</a>';
    }).join('') + '</nav>';
  }

  function render(route) {
    var host = document.getElementById('app-chrome');

    /* Подписан на баланс только текущий хедер. Старые слушатели снимаем,
       иначе после смены маршрута их накопится сколько угодно. */
    Wallet.store.clearBalanceListeners();

    if (!Wallet.store.isAuthorized()) {
      host.innerHTML = '<header class="app-header app-header--plain">' +
        '<div class="brand">Кошелёк</div>' +
        (route === '/login' ? '' :
          '<a class="link-button" href="' + Wallet.router.href('/login') + '" data-link>Войти</a>') +
        '</header>';
      return;
    }

    var session = Wallet.store.getSession() || {};
    var tariff = Wallet.store.getTariff();
    var meta = Wallet.ui.escapeHtml(session.login || '') +
      (tariff ? ' · тариф ' + Wallet.ui.escapeHtml(tariff) : '');

    if (Wallet.ui.isMobile()) {
      /* Компактный (мобильный) хедер. */
      host.innerHTML =
        '<header class="app-header app-header--mobile">' +
          '<div class="brand">Кошелёк</div>' +
          '<div class="balance-compact">' +
            '<span class="balance-label">Баланс</span>' +
            '<span class="balance-value" id="header-balance">' +
              Wallet.ui.escapeHtml(balanceText()) +
            '</span>' +
          '</div>' +
          '<div class="header-meta">' + meta + '</div>' +
        '</header>' +
        navHtml(route) +
        '<button type="button" class="link-button logout-standalone" id="logout">Выйти</button>';
    } else {
      host.innerHTML =
        '<header class="app-header app-header--desktop">' +
          '<div class="brand">Кошелёк</div>' +
          '<div class="balance-block">' +
            '<span class="balance-label">Баланс</span>' +
            '<span class="balance-value" id="header-balance">' +
              Wallet.ui.escapeHtml(balanceText()) +
            '</span>' +
          '</div>' +
          '<div class="header-meta">' + meta + '</div>' +
          '<button type="button" class="link-button" id="logout">Выйти</button>' +
        '</header>' +
        navHtml(route);

      Wallet.store.onBalanceChange(function () {
        var node = document.getElementById('header-balance');
        if (node) { node.textContent = balanceText(); }
      });
    }

    var logout = document.getElementById('logout');
    if (logout) {
      logout.addEventListener('click', function () {
        Wallet.store.endSession();
        Wallet.router.navigate('/login');
      });
    }
  }

  Wallet.chrome = { render: render };
})(window.Wallet = window.Wallet || {});
