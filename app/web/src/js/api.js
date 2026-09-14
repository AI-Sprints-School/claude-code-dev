/* Тонкая обёртка над fetch. Ничего не кеширует и ничего не решает:
   запрос в DevTools выглядит ровно так, как он здесь написан. */
(function (Wallet) {
  'use strict';

  function base() {
    return (window.WALLET_CONFIG && window.WALLET_CONFIG.apiBase) || '/api';
  }

  /* Отличаем «сервер ответил ошибкой» от «запрос не дошёл». */
  function ApiError(status, payload) {
    this.name = 'ApiError';
    this.status = status;
    this.payload = payload;
    this.code = payload && payload.error && payload.error.code;
    this.serverMessage = payload && payload.error && payload.error.message;
  }
  ApiError.prototype = Object.create(Error.prototype);

  function NetworkError(cause) {
    this.name = 'NetworkError';
    this.cause = cause;
  }
  NetworkError.prototype = Object.create(Error.prototype);

  function request(method, path, body) {
    var headers = { 'Accept': 'application/json' };
    var token = Wallet.store.getToken();
    if (token) { headers['Authorization'] = 'Bearer ' + token; }

    var options = { method: method, headers: headers };
    if (body !== undefined) {
      headers['Content-Type'] = 'application/json';
      options.body = JSON.stringify(body);
    }

    var response;
    return fetch(base() + path, options)
      .catch(function (error) { throw new NetworkError(error); })
      .then(function (raw) {
        response = raw;
        return raw.text();
      })
      .then(function (text) {
        var payload = null;
        if (text) {
          try { payload = JSON.parse(text); } catch (error) { payload = null; }
        }
        if (!response.ok) { throw new ApiError(response.status, payload); }
        return payload;
      });
  }

  function query(params) {
    var parts = [];
    Object.keys(params).forEach(function (key) {
      if (params[key] === undefined || params[key] === null) { return; }
      parts.push(encodeURIComponent(key) + '=' + encodeURIComponent(params[key]));
    });
    return parts.length ? '?' + parts.join('&') : '';
  }

  Wallet.api = {
    ApiError: ApiError,
    NetworkError: NetworkError,

    login: function (login, password) {
      return request('POST', '/auth/login', { login: login, password: password });
    },
    balance: function () {
      return request('GET', '/wallet/balance');
    },
    topup: function (amount) {
      return request('POST', '/wallet/topup', { amount: amount });
    },
    withdraw: function (amount) {
      return request('POST', '/wallet/withdraw', { amount: amount });
    },
    operations: function (params) {
      return request('GET', '/wallet/operations' + query(params));
    },
    assistant: function (message) {
      return request('POST', '/assistant/message', { message: message });
    },
    sqlSchema: function () {
      return request('GET', '/sql/schema');
    },
    sqlQuery: function (sql) {
      return request('POST', '/sql/query', { sql: sql });
    }
  };
})(window.Wallet = window.Wallet || {});
