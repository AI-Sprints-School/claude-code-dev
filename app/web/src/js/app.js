/* Сборка приложения: таблица маршрутов, охрана маршрутов, подвал с версией
   и перерисовка при смене размеров окна. */
(function (Wallet) {
  'use strict';

  var ROUTES = {
    '/': 'home',
    '/login': 'login',
    '/topup': 'topup',
    '/withdraw': 'withdraw',
    '/history': 'history',
    '/assistant': 'assistant',
    '/tariffs': 'tariffs',
    '/sql': 'sql'
  };

  var screenHost = null;

  function versionLine() {
    return 'Кошелёк ' + window.WALLET_BUILD.version +
      ' (сборка ' + window.WALLET_BUILD.build + ')';
  }

  function notFound(host) {
    host.innerHTML = '<section class="card"><h1>Страница не найдена</h1>' +
      '<p><a href="' + Wallet.router.href('/') + '" data-link>На главную</a></p></section>';
  }

  function paint(route) {
    var name = ROUTES[route];
    var screen = name ? Wallet.screens[name] : null;

    Wallet.chrome.render(route);

    if (!screen) {
      document.title = 'Кошелёк';
      notFound(screenHost);
      return;
    }

    document.title = screen.title + ' — Кошелёк';
    screen.render(screenHost);
  }

  function handleRoute(route) {
    var name = ROUTES[route];
    var screen = name ? Wallet.screens[name] : null;
    var authorized = Wallet.store.isAuthorized();

    if (screen && screen.guest && authorized) {
      Wallet.router.navigate('/', { replace: true });
      return;
    }
    if (screen && !screen.guest && !screen.public && !authorized) {
      Wallet.router.navigate('/login', { replace: true });
      return;
    }
    if (!screen && !authorized) {
      Wallet.router.navigate('/login', { replace: true });
      return;
    }

    paint(route);
  }

  /* Перерисовка при смене режима вёрстки. */
  function watchViewport() {
    var lastWidth = window.innerWidth;
    var lastMobile = Wallet.ui.isMobile();

    function apply() {
      var width = window.innerWidth;
      var nowMobile = width < Wallet.ui.MOBILE_BREAKPOINT;
      var mobileInvolved = lastMobile || nowMobile;
      lastWidth = width;
      lastMobile = nowMobile;
      if (!mobileInvolved) { return; }
      paint(Wallet.router.path());
    }

    window.addEventListener('resize', function () {
      /* Мобильные браузеры шлют resize при скрытии адресной строки —
         там меняется высота, а не ширина. Такие события пропускаем. */
      if (window.innerWidth === lastWidth) { return; }
      apply();
    });

    /* Поворот экрана: часть браузеров к моменту события ещё не пересчитала
       innerWidth, поэтому проверку ширины здесь не делаем. */
    function onOrientationChange() {
      window.setTimeout(apply, 0);
    }

    window.addEventListener('orientationchange', onOrientationChange);
    if (window.screen && window.screen.orientation &&
        window.screen.orientation.addEventListener) {
      window.screen.orientation.addEventListener('change', onOrientationChange);
    }
  }

  function start() {
    screenHost = document.getElementById('app-screen');
    document.getElementById('app-version').textContent = versionLine();

    watchViewport();

    if (!Wallet.store.isAuthorized()) {
      Wallet.router.start(handleRoute);
      return;
    }

    /* Баланс подтягиваем до первой отрисовки, иначе шапка мигнёт прочерком. */
    Wallet.store.loadBalance()
      .catch(function (error) {
        if (Wallet.ui.isUnauthorized(error)) { Wallet.store.endSession(); }
      })
      .then(function () {
        Wallet.router.start(handleRoute);
      });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
})(window.Wallet = window.Wallet || {});
