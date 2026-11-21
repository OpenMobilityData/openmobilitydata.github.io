// Filter of the « All documents » table. No data leaves the page.
(function () {
  var q = document.getElementById('q');
  var kind = document.getElementById('kind');
  var n = document.getElementById('n');
  if (!q || !kind) return;
  var rows = Array.prototype.slice.call(document.querySelectorAll('table.all tbody tr'));
  function apply() {
    var words = q.value.toLowerCase().split(/\s+/).filter(Boolean);
    var k = kind.value;
    var shown = 0;
    rows.forEach(function (r) {
      var text = r.getAttribute('data-text');
      var ok = (!k || r.getAttribute('data-status') === k) &&
        words.every(function (w) { return text.indexOf(w) !== -1; });
      r.hidden = !ok;
      if (ok) shown += 1;
    });
    n.textContent = shown + ' of ' + rows.length;
  }
  q.addEventListener('input', apply);
  kind.addEventListener('change', apply);
  apply();
})();
