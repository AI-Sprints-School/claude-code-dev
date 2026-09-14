/* SQL-консоль только на чтение (2.7): поле запроса, панель схемы сбоку,
   таблица результата и кнопка «Скопировать как markdown».
   Запрос уходит на бэкенд как есть — он же и решает, что пропускать:
   роль qa_student, BEGIN READ ONLY, statement_timeout 5s, потолок 300 строк.
   Клиент ничего не фильтрует: пользователь должен видеть отказ сервера,
   а не свою же догадку о том, что разрешено. */
(function (Wallet) {
  'use strict';

  /* Запасной запрос на случай, если сервер не прислал свой. Основной
     приходит в default_query вместе со схемой: источник правды один. */
  var FALLBACK_QUERY = 'SELECT * FROM wallets LIMIT 5;';

  /* История последних десяти запросов: длинный запрос по памяти никто
     переписывать не станет. Хранится в localStorage: она нужна только этому
     пользователю в этом браузере, серверу до неё дела нет. Любое обращение
     в try — приватное окно, запрет на данные сайта и превью бросают прямо
     на чтении. */
  var HISTORY_KEY = 'wallet.sql.history';
  var HISTORY_LIMIT = 10;

  function loadHistory() {
    try {
      var raw = window.localStorage.getItem(HISTORY_KEY);
      var list = raw ? JSON.parse(raw) : [];
      return Array.isArray(list) ? list.filter(function (x) { return typeof x === 'string'; }) : [];
    } catch (e) {
      return [];
    }
  }

  function rememberQuery(sql) {
    var list = loadHistory().filter(function (item) { return item !== sql; });
    list.unshift(sql);
    list = list.slice(0, HISTORY_LIMIT);
    try {
      window.localStorage.setItem(HISTORY_KEY, JSON.stringify(list));
    } catch (e) {
      /* Место кончилось или запись запрещена — история не обязательна. */
    }
    return list;
  }

  function historyHtml(list) {
    if (!list.length) {
      return '<p class="empty">Пока пусто. Выполненные запросы появятся здесь.</p>';
    }
    return '<ol class="sql-history-list">' + list.map(function (sql, index) {
      var oneLine = sql.replace(/\s+/g, ' ');
      var short = oneLine.length > 90 ? oneLine.slice(0, 89) + '…' : oneLine;
      return '<li><button type="button" class="sql-history-item" data-index="' + index +
        '" title="Подставить в поле запроса">' + Wallet.ui.escapeHtml(short) + '</button></li>';
    }).join('') + '</ol>';
  }

  function schemaHtml(schema) {
    return schema.tables.map(function (table) {
      var columns = table.columns.map(function (column) {
        return '<li><code>' + Wallet.ui.escapeHtml(column.name) + '</code>' +
          '<span class="sql-type">' + Wallet.ui.escapeHtml(column.type) + '</span></li>';
      }).join('');
      return '<div class="sql-table">' +
        '<h3><code>' + Wallet.ui.escapeHtml(table.name) + '</code></h3>' +
        '<ul>' + columns + '</ul></div>';
    }).join('');
  }

  function resultHtml(result) {
    if (!result.columns.length) { return '<p class="empty">Запрос не вернул колонок.</p>'; }

    var head = result.columns.map(function (name) {
      return '<th>' + Wallet.ui.escapeHtml(name) + '</th>';
    }).join('');

    var body = result.rows.map(function (row) {
      var cells = row.map(function (cell) {
        var text = cell === null ? 'NULL' : String(cell);
        var nullClass = cell === null ? ' class="sql-null"' : '';
        return '<td' + nullClass + '>' + Wallet.ui.escapeHtml(text) + '</td>';
      }).join('');
      return '<tr>' + cells + '</tr>';
    }).join('');

    var notice = result.notice
      ? '<p class="sql-notice">' + Wallet.ui.escapeHtml(result.notice) + '</p>'
      : '';

    return '<div class="sql-meta">Строк: ' + result.row_count +
      ' · ' + result.duration_ms + ' мс</div>' + notice +
      '<div class="sql-scroll"><table class="sql-result">' +
      '<thead><tr>' + head + '</tr></thead><tbody>' + body + '</tbody></table></div>';
  }

  function render(host) {
    host.innerHTML =
      '<section class="card sql-console">' +
        '<h1>SQL-консоль</h1>' +
        '<p class="sql-hint">Только чтение: доступны <code>SELECT</code> и <code>WITH</code>. ' +
        'Одна инструкция за раз, не больше 300 строк в ответе.</p>' +
        '<div class="sql-layout">' +
          '<div class="sql-main">' +
            '<label for="sql-input">Запрос</label>' +
            '<textarea id="sql-input" rows="7" spellcheck="false"></textarea>' +
            '<div class="sql-actions">' +
              '<button type="button" class="button" id="sql-run">Выполнить</button>' +
              '<button type="button" class="button secondary" id="sql-copy" hidden>Скопировать как markdown</button>' +
              '<span class="sql-copied" id="sql-copied" hidden>Скопировано</span>' +
            '</div>' +
            '<div id="sql-output"></div>' +
            '<section class="sql-history">' +
              '<h2>Последние запросы</h2>' +
              '<div id="sql-history-box"></div>' +
            '</section>' +
          '</div>' +
          '<aside class="sql-schema">' +
            '<h2>Схема</h2>' +
            '<div id="sql-schema-body"><p class="empty">Загрузка…</p></div>' +
          '</aside>' +
        '</div>' +
      '</section>';

    var input = document.getElementById('sql-input');
    var output = document.getElementById('sql-output');
    var runButton = document.getElementById('sql-run');
    var copyButton = document.getElementById('sql-copy');
    var copied = document.getElementById('sql-copied');
    var schemaBody = document.getElementById('sql-schema-body');
    var historyBox = document.getElementById('sql-history-box');
    var lastMarkdown = '';

    function paintHistory(list) {
      historyBox.innerHTML = historyHtml(list);
    }

    paintHistory(loadHistory());

    historyBox.addEventListener('click', function (event) {
      var button = event.target.closest('.sql-history-item');
      if (!button) { return; }
      input.value = loadHistory()[Number(button.getAttribute('data-index'))] || '';
      input.focus();
    });

    input.value = FALLBACK_QUERY;

    function fail(error) {
      if (Wallet.ui.isUnauthorized(error)) { Wallet.router.navigate('/login'); return; }
      copyButton.hidden = true;
      var text = error && error.serverMessage
        ? error.serverMessage
        : Wallet.messages.REQUEST_FAILED;
      output.innerHTML = '<p class="field-error">' + Wallet.ui.escapeHtml(text) + '</p>';
    }

    function run() {
      var sql = input.value.trim();
      if (!sql) {
        output.innerHTML = '<p class="field-error">Введите запрос</p>';
        copyButton.hidden = true;
        return;
      }
      output.innerHTML = '<p class="empty">Выполняется…</p>';
      copyButton.hidden = true;
      copied.hidden = true;

      Wallet.api.sqlQuery(sql)
        .then(function (result) {
          /* Запоминаем только то, что сервер принял: история из отвергнутых
             запросов студенту не поможет. */
          paintHistory(rememberQuery(sql));
          lastMarkdown = result.markdown || '';
          output.innerHTML = resultHtml(result);
          copyButton.hidden = !lastMarkdown;
        })
        .catch(fail);
    }

    runButton.addEventListener('click', run);

    /* Ctrl+Enter — привычная комбинация любой консоли. */
    input.addEventListener('keydown', function (event) {
      if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') { run(); }
    });

    copyButton.addEventListener('click', function () {
      if (!lastMarkdown) { return; }
      navigator.clipboard.writeText(lastMarkdown).then(function () {
        copied.hidden = false;
        setTimeout(function () { copied.hidden = true; }, 2000);
      });
    });

    Wallet.api.sqlSchema()
      .then(function (schema) {
        schemaBody.innerHTML = schemaHtml(schema);
        /* Подставляем только в нетронутое поле: студент мог начать печатать
           раньше, чем пришла схема, и затирать его ввод нельзя. */
        if (schema.default_query && input.value === FALLBACK_QUERY) {
          input.value = schema.default_query;
        }
      })
      .catch(function (error) {
        if (Wallet.ui.isUnauthorized(error)) { Wallet.router.navigate('/login'); return; }
        schemaBody.innerHTML = '<p class="field-error">Схема недоступна</p>';
      });
  }

  Wallet.screens = Wallet.screens || {};
  Wallet.screens.sql = { title: 'SQL-консоль', render: render };
})(window.Wallet = window.Wallet || {});
