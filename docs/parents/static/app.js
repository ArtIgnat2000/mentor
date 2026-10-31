if ('serviceWorker' in navigator && location.protocol.indexOf('http') === 0) {
  window.addEventListener('load', function () {
    navigator.serviceWorker.register('./sw.js').catch(function () {});
  });
}
document.addEventListener('click', function (event) {
  if (event.target.closest('[data-print]')) window.print();
});
