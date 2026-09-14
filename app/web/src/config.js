/* Адрес API. Меняется на сборке: переменная окружения WALLET_API_BASE.
   По умолчанию '/api' — тот же origin, что и веб-клиент (в проде так и есть:
   один nginx отдаёт статику и проксирует /api, /sql, /docs в бэкенд). */
window.WALLET_CONFIG = {
  apiBase: '{{API_BASE}}'
};
