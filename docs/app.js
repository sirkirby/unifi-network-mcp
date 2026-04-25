/* Tabs */
function switchTab(id) {
  var tabs = document.querySelectorAll('.install-tabs [role="tab"]');
  var panels = document.querySelectorAll('.install-panel');
  tabs.forEach(function(t) {
    var sel = t.id === 'tab-' + id;
    t.setAttribute('aria-selected', sel ? 'true' : 'false');
    t.tabIndex = sel ? 0 : -1;
  });
  panels.forEach(function(p) {
    var act = p.id === 'panel-' + id;
    p.classList.toggle('active', act);
    if (act) p.removeAttribute('hidden'); else p.setAttribute('hidden', '');
  });
}

/* Copy */
function copyCode(btn) {
  var panel = btn.closest('.install-panel');
  var code = panel.querySelector('code').innerText;
  var done = function() {
    btn.classList.add('copied');
    btn.textContent = 'Copied';
    setTimeout(function(){ btn.classList.remove('copied'); btn.textContent = 'Copy'; }, 1800);
  };
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(code).then(done).catch(function() {
      var ta = document.createElement('textarea'); ta.value = code; document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy'); done(); } catch(e){}
      document.body.removeChild(ta);
    });
  }
}

/* Marquee duplicate for seamless loop — clones DOM nodes (avoids innerHTML re-parsing) */
(function () {
  var m = document.getElementById('marquee');
  if (!m) return;
  var items = Array.from(m.children);
  items.forEach(function (el) { m.appendChild(el.cloneNode(true)); });
})();

/* Live versions (PyPI + npm) and GitHub star count */
(function () {
  function setText(sel, text) {
    var nodes = document.querySelectorAll(sel);
    for (var i = 0; i < nodes.length; i++) nodes[i].textContent = text;
  }
  function fetchJSON(url) {
    return fetch(url, { headers: { 'Accept': 'application/json' } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .catch(function () { return null; });
  }
  ['unifi-network-mcp', 'unifi-protect-mcp', 'unifi-access-mcp', 'unifi-mcp-relay'].forEach(function (pkg) {
    fetchJSON('https://pypi.org/pypi/' + pkg + '/json').then(function (d) {
      if (d && d.info && d.info.version) setText('[data-pkg-version="' + pkg + '"]', 'v' + d.info.version);
    });
  });
  fetchJSON('https://registry.npmjs.org/unifi-mcp-worker/latest').then(function (d) {
    if (d && d.version) setText('[data-npm-version="unifi-mcp-worker"]', 'v' + d.version);
  });
  fetchJSON('https://api.github.com/repos/sirkirby/unifi-mcp').then(function (d) {
    if (d && typeof d.stargazers_count === 'number') {
      setText('[data-stars]', '★ ' + d.stargazers_count.toLocaleString());
    }
  });
})();
