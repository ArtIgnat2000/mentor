if ('serviceWorker' in navigator && location.protocol.indexOf('http') === 0) {
  window.addEventListener('load', function () {
    var path = location.pathname;
    var swUrl = (path.endsWith('/') || path.endsWith('.html')) ? './sw.js' : '/sw.js';
    navigator.serviceWorker.register(swUrl).catch(function () {});
  });
}

document.addEventListener('click', function (event) {
  if (event.target.closest('[data-print]')) window.print();
});

function normalize(value) {
  return (value || '').toLowerCase().replace(/ё/g, 'е').trim();
}

function openHashTarget() {
  var id = decodeURIComponent(location.hash.replace('#', ''));
  if (!id) return;
  var target = document.getElementById(id);
  if (target && target.tagName === 'DETAILS') target.open = true;
}
window.addEventListener('hashchange', openHashTarget);
openHashTarget();

document.querySelectorAll('[data-search]').forEach(function (input) {
  var targetSelector = input.getAttribute('data-search-target') || '.search-item';
  var items = Array.prototype.slice.call(document.querySelectorAll(targetSelector));
  var noResults = document.querySelector('[data-no-results]');
  var clear = document.querySelector('[data-search-clear]');
  var activeFilter = 'all';

  function apply() {
    var query = normalize(input.value);
    var visible = 0;
    items.forEach(function (item) {
      var group = item.getAttribute('data-group') || '';
      var haystack = normalize(item.textContent + ' ' + (item.getAttribute('data-keywords') || ''));
      var matchesQuery = !query || haystack.indexOf(query) !== -1;
      var matchesFilter = activeFilter === 'all' || group === activeFilter;
      var show = matchesQuery && matchesFilter;
      item.hidden = !show;
      if (show) {
        visible += 1;
        if (query && item.tagName === 'DETAILS') item.open = true;
      }
    });
    document.querySelectorAll('[data-group-section]').forEach(function (section) {
      var groupItems = section.querySelectorAll(targetSelector);
      var anyVisible = Array.prototype.some.call(groupItems, function (item) { return !item.hidden; });
      section.hidden = !anyVisible;
    });
    if (noResults) noResults.hidden = visible !== 0;
  }

  input.addEventListener('input', apply);
  if (clear) {
    clear.addEventListener('click', function () {
      input.value = '';
      apply();
      input.focus();
    });
  }
  document.querySelectorAll('[data-filter]').forEach(function (chip) {
    chip.addEventListener('click', function () {
      activeFilter = chip.getAttribute('data-filter') || 'all';
      document.querySelectorAll('[data-filter]').forEach(function (other) {
        other.classList.toggle('is-active', other === chip);
      });
      apply();
    });
  });
  apply();
});
