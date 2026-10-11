/* Live visitor count over WebSocket, with graceful fallback. */
(function () {
  if (window.SHOPBAZAR_ENABLE_WS === false) return;
  var nodes = function () { return document.querySelectorAll('[data-live-count]'); };
  if (!nodes().length) return;

  var scheme = location.protocol === 'https:' ? 'wss://' : 'ws://';
  var url = scheme + location.host + '/ws/visitors/';
  var socket;
  var retry = 0;

  function connect() {
    try {
      socket = new WebSocket(url);
    } catch (e) {
      return;
    }
    socket.onmessage = function (event) {
      nodes().forEach(function (n) { n.textContent = event.data; });
    };
    socket.onclose = function () {
      retry += 1;
      if (retry < 10) setTimeout(connect, Math.min(30000, retry * 2000));
    };
  }

  document.addEventListener('DOMContentLoaded', connect);
})();
