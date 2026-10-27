// Offer the Linux bundle first to visitors on desktop Linux; the Windows ZIP stays the default.
(function () {
  var ua = navigator.userAgent;
  if (!/Linux/.test(ua) || /Android/.test(ua)) return;
  var win = document.querySelector('[data-platform="windows"]');
  var linux = document.querySelector('[data-platform="linux"]');
  if (!win || !linux) return;
  win.classList.remove('primary');
  linux.classList.add('primary');
  win.parentNode.insertBefore(linux, win);
})();

// Show key columns in guide tables with the manager's key-value styling.
document.querySelectorAll('.prose table').forEach(function (table) {
  var first = table.querySelector('th');
  if (!first || first.textContent.trim() !== 'Key') return;
  table.classList.add('key-table');
  table.querySelectorAll('tbody td:first-child').forEach(function (cell) {
    var chip = document.createElement('span');
    chip.className = 'key';
    while (cell.firstChild) chip.appendChild(cell.firstChild);
    cell.appendChild(chip);
  });
});
