/* Клиентский стор: сессия, баланс, кеш истории операций.
   Живёт в памяти вкладки, поэтому F5 его обнуляет. Токен — единственное,
   что переживает перезагрузку (иначе после F5 пришлось бы входить заново). */
(function (Wallet) {
  'use strict';

  var TOKEN_KEY = 'wallet.token';
  var SESSION_KEY = 'wallet.session';
  var PAGE_SIZE = 20;

  var state = {
    token: null,
    session: null,      // { wallet_id, login, expires_at }
    balance: null,
    currency: 'RUB',
    tariff: null,
    operations: {}      // кеш истории по ключу фильтра
  };

  var balanceListeners = [];

  function readStorage(key) {
    try { return window.localStorage.getItem(key); } catch (error) { return null; }
  }

  function writeStorage(key, value) {
    try {
      if (value === null) { window.localStorage.removeItem(key); }
      else { window.localStorage.setItem(key, value); }
    } catch (error) { /* приватный режим — работаем без сохранения */ }
  }

  state.token = readStorage(TOKEN_KEY);
  try { state.session = JSON.parse(readStorage(SESSION_KEY) || 'null'); }
  catch (error) { state.session = null; }

  /* --- Сессия ------------------------------------------------------------ */

  function getToken() { return state.token; }
  function isAuthorized() { return Boolean(state.token); }
  function getSession() { return state.session; }

  function startSession(payload) {
    state.token = payload.token;
    state.session = {
      wallet_id: payload.wallet_id,
      login: payload.login,
      expires_at: payload.expires_at
    };
    writeStorage(TOKEN_KEY, state.token);
    writeStorage(SESSION_KEY, JSON.stringify(state.session));
  }

  function endSession() {
    state.token = null;
    state.session = null;
    state.balance = null;
    state.tariff = null;
    state.operations = {};
    writeStorage(TOKEN_KEY, null);
    writeStorage(SESSION_KEY, null);
  }

  /* --- Баланс ------------------------------------------------------------ */

  function getBalance() { return state.balance; }
  function getTariff() { return state.tariff; }

  function setWallet(payload) {
    state.balance = payload.balance;
    state.currency = payload.currency || state.currency;
    if (payload.tariff) { state.tariff = payload.tariff; }
    notifyBalance();
  }

  function setBalance(value) {
    state.balance = value;
    notifyBalance();
  }

  function notifyBalance() {
    balanceListeners.slice().forEach(function (listener) {
      listener(state.balance);
    });
  }

  /* Подписка на изменения баланса. */
  function onBalanceChange(listener) {
    balanceListeners.push(listener);
    return function unsubscribe() {
      var index = balanceListeners.indexOf(listener);
      if (index !== -1) { balanceListeners.splice(index, 1); }
    };
  }

  function clearBalanceListeners() {
    balanceListeners.length = 0;
  }

  function loadBalance() {
    return Wallet.api.balance().then(function (payload) {
      setWallet(payload);
      return payload;
    });
  }

  /* --- История операций -------------------------------------------------- */

  var FILTERS = {
    ALL: { label: 'Все', type: null },
    TOPUP: { label: 'Пополнения', type: 'TOPUP' },
    WITHDRAW: { label: 'Списания', type: 'WITHDRAW' }
  };

  function emptyPage() {
    return { items: [], total: 0, loaded: false };
  }

  function getCached(filterKey) {
    return state.operations[filterKey] || null;
  }

  function fetchPage(filterKey, offset) {
    return Wallet.api.operations({
      limit: PAGE_SIZE,
      offset: offset,
      type: FILTERS[filterKey].type
    });
  }

  /* Первая страница истории. */
  function loadOperations(filterKey, options) {
    var force = Boolean(options && options.force);
    var cached = getCached(filterKey);
    if (cached && cached.loaded && !force) {
      return Promise.resolve(cached);
    }
    return fetchPage(filterKey, 0).then(function (payload) {
      var page = emptyPage();
      page.items = payload.items || [];
      page.total = payload.total || 0;
      page.loaded = true;
      state.operations[filterKey] = page;
      return page;
    });
  }

  function loadMoreOperations(filterKey) {
    var page = getCached(filterKey) || emptyPage();
    return fetchPage(filterKey, page.items.length).then(function (payload) {
      page.items = page.items.concat(payload.items || []);
      page.total = payload.total || page.total;
      page.loaded = true;
      state.operations[filterKey] = page;
      return page;
    });
  }

  Wallet.store = {
    PAGE_SIZE: PAGE_SIZE,
    FILTERS: FILTERS,

    getToken: getToken,
    isAuthorized: isAuthorized,
    getSession: getSession,
    startSession: startSession,
    endSession: endSession,

    getBalance: getBalance,
    getTariff: getTariff,
    setWallet: setWallet,
    setBalance: setBalance,
    onBalanceChange: onBalanceChange,
    clearBalanceListeners: clearBalanceListeners,
    loadBalance: loadBalance,

    getCached: getCached,
    loadOperations: loadOperations,
    loadMoreOperations: loadMoreOperations
  };
})(window.Wallet = window.Wallet || {});
