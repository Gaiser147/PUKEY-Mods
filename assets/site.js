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
