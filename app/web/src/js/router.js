/* Маршрутизация через History API.
   Сборка 1.5.0 живёт под префиксом /next, поэтому все ссылки строятся
   через href(). */
(function (Wallet) {
  'use strict';

  var handler = null;

  function base() {
    return window.WALLET_BUILD.routeBase || '';
  }

  function href(path) {
    return base() + path;
  }

  function path() {
    var pathname = window.location.pathname;
    var prefix = base();
    if (prefix && pathname.indexOf(prefix) === 0) {
      pathname = pathname.slice(prefix.length);
    }
    if (pathname.length > 1 && pathname.charAt(pathname.length - 1) === '/') {
      pathname = pathname.slice(0, -1);
    }
    return pathname || '/';
  }

  function navigate(to, options) {
    var url = href(to);
    if (options && options.replace) {
      window.history.replaceState({}, '', url);
    } else {
      window.history.pushState({}, '', url);
    }
    if (handler) { handler(path()); }
  }

  function start(onRoute) {
    handler = onRoute;

    document.addEventListener('click', function (event) {
      var link = event.target.closest && event.target.closest('a[data-link]');
      if (!link) { return; }
      if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) { return; }
      event.preventDefault();
      var url = new URL(link.href, window.location.origin);
      if (url.pathname === window.location.pathname) { return; }
      window.history.pushState({}, '', url.pathname);
      handler(path());
    });

    window.addEventListener('popstate', function () {
      handler(path());
    });

    handler(path());
  }

  Wallet.router = {
    base: base,
    href: href,
    path: path,
    navigate: navigate,
    start: start
  };
})(window.Wallet = window.Wallet || {});
