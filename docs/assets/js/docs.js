/* FlexSpace online docs: theme toggle, search (docs/docs/search-index.json), "On this page" highlight, picture zoom.
   Everything works without it except search. Theme key shared with the rest of the site. */
(function () {
  'use strict';
  var root = document.documentElement;
  var KEY = 'fs-theme';

  function ready(fn) {
    if (document.readyState !== 'loading') fn(); else document.addEventListener('DOMContentLoaded', fn);
  }

  ready(function () {
    // ---------------------------------------------------------------- theme (dark default, light opt-in)
    function isLight() { return root.getAttribute('data-theme') === 'light'; }
    function label() {
      var meta = document.querySelector('meta[name="theme-color"]');
      if (meta) meta.setAttribute('content', isLight() ? '#f7f5f1' : '#0a0a0c');
      document.querySelectorAll('[data-theme-toggle]').forEach(function (b) {
        b.setAttribute('aria-label', isLight() ? 'Switch to the dark theme' : 'Switch to the light theme');
      });
    }
    document.querySelectorAll('[data-theme-toggle]').forEach(function (b) {
      b.addEventListener('click', function () {
        var next = isLight() ? 'dark' : 'light';
        root.setAttribute('data-theme', next);
        try { localStorage.setItem(KEY, next); } catch (e) {}
        label();
      });
    });
    label();

    // ---------------------------------------------------------------- on this page
    var tocLinks = Array.prototype.slice.call(document.querySelectorAll('.fs-doc__toc .fs-toc a'));
    if (tocLinks.length) {
      var heads = tocLinks.map(function (a) {
        return document.getElementById(decodeURIComponent(a.getAttribute('href').slice(1)));
      });
      var ticking = false;
      var update = function () {
        ticking = false;
        // The section being read: the last heading above 30 % of the viewport (a fixed 140 px line lagged a
        // section behind once a heading had scrolled into the upper part of the page).
        var line = Math.max(140, window.innerHeight * 0.3);
        var current = -1;
        for (var i = 0; i < heads.length; i++) {
          if (heads[i] && heads[i].getBoundingClientRect().top < line) current = i; else if (heads[i]) break;
        }
        if (window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 4) current = heads.length - 1;
        tocLinks.forEach(function (a, j) { a.classList.toggle('is-active', j === current); });
      };
      window.addEventListener('scroll', function () {
        if (!ticking) { ticking = true; requestAnimationFrame(update); }
      }, { passive: true });
      update();
    }
    // Close the mobile "On this page" after a jump.
    document.querySelectorAll('.fs-doc__mtoc a').forEach(function (a) {
      a.addEventListener('click', function () { a.closest('details').removeAttribute('open'); });
    });

    // ---------------------------------------------------------------- picture zoom
    var box = document.getElementById('fs-lightbox');
    if (box) {
      var bImg = box.querySelector('img');
      var bVid = box.querySelector('video');
      var bCap = box.querySelector('figcaption');
      var calm = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
      document.querySelectorAll('[data-zoom]').forEach(function (a) {
        a.addEventListener('click', function (e) {
          if (e.ctrlKey || e.metaKey || e.shiftKey || e.button !== 0) return;
          e.preventDefault();
          var img = a.querySelector('img');
          var inline = a.querySelector('video');
          var cap = a.parentNode.querySelector('figcaption');
          var isVideo = !!bVid && a.hasAttribute('data-video');
          bImg.hidden = isVideo;
          if (bVid) bVid.hidden = !isVideo;
          if (isVideo) {
            bImg.removeAttribute('src');
            bVid.poster = inline ? inline.getAttribute('poster') || '' : '';
            bVid.src = a.getAttribute('href');
            bVid.setAttribute('aria-label', inline ? inline.getAttribute('aria-label') || '' : '');
            if (!calm) { var pl = bVid.play(); if (pl && pl.catch) pl.catch(function () {}); }
          } else {
            bImg.src = a.getAttribute('href');
            bImg.alt = img ? img.alt : '';
          }
          bCap.textContent = cap ? cap.textContent : '';
          box.hidden = false;
        });
      });
      box.addEventListener('click', function (e) {
        if (bVid && e.target === bVid) return;
        box.hidden = true;
        if (bVid) { bVid.pause(); bVid.removeAttribute('src'); bVid.load(); }
      });
    }

    // ---------------------------------------------------------------- real loops (load and play only in view)
    var loops = document.querySelectorAll('video.fs-loop[data-src]');
    if (loops.length && 'IntersectionObserver' in window && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      var lo = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          var v = en.target;
          if (en.isIntersecting) {
            if (!v.getAttribute('src')) v.src = v.getAttribute('data-src');
            var p = v.play();
            if (p && p.catch) p.catch(function () {});
          } else if (!v.paused) {
            v.pause();
          }
        });
      }, { rootMargin: '120px 0px', threshold: 0.25 });
      loops.forEach(function (v) { v.muted = true; lo.observe(v); });
    }

    // ---------------------------------------------------------------- search
    var panel = document.getElementById('fs-search');
    if (!panel) return;
    var input = panel.querySelector('input');
    var list = panel.querySelector('.fs-search__results');
    var empty = panel.querySelector('.fs-search__empty');
    var index = null, loading = null, selected = 0, lastFocus = null;

    function load() {
      if (index || loading) return loading;
      loading = fetch('search-index.json', { cache: 'force-cache' })
        .then(function (r) { return r.json(); })
        .then(function (d) { index = d.entries || []; run(); })
        .catch(function () {
          index = [];
          empty.textContent = 'Search needs the site to be served over http(s).';
          empty.hidden = false;
        });
      return loading;
    }
    function escapeHtml(s) {
      return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; });
    }
    function highlight(text, words) {
      var ws = words.filter(Boolean).slice().sort(function (a, b) { return b.length - a.length; });
      if (!ws.length) return escapeHtml(text);
      var re = new RegExp(ws.map(function (w) { return w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }).join('|'), 'ig');
      var out = '', last = 0, m;
      while ((m = re.exec(text)) !== null) {
        if (!m[0].length) { re.lastIndex++; continue; }
        out += escapeHtml(text.slice(last, m.index)) + '<mark>' + escapeHtml(m[0]) + '</mark>';
        last = m.index + m[0].length;
      }
      return out + escapeHtml(text.slice(last));
    }
    function snippet(text, words) {
      var at = text.toLowerCase().indexOf(words[0]);
      if (at < 0) return text.slice(0, 150) + (text.length > 150 ? '…' : '');
      var start = Math.max(0, at - 50);
      return (start ? '…' : '') + text.slice(start, start + 170) + (start + 170 < text.length ? '…' : '');
    }
    function run() {
      var q = input.value.trim().toLowerCase();
      var words = q.split(/\s+/).filter(Boolean);
      list.innerHTML = '';
      selected = 0;
      empty.hidden = true;
      if (!words.length || !index) return;
      var hits = [];
      index.forEach(function (e) {
        var h = (e.h || '').toLowerCase(), p = e.p.toLowerCase(), t = (e.t || '').toLowerCase();
        var score = 0;
        for (var i = 0; i < words.length; i++) {
          var w = words[i];
          if ((p + ' ' + h + ' ' + t).indexOf(w) < 0) return;
          if (h.indexOf(w) >= 0) score += h.indexOf(w) === 0 ? 9 : 6;
          if (p.indexOf(w) >= 0) score += 3;
          score += Math.min(3, t.split(w).length - 1);
        }
        if (!e.h) score += 1;
        hits.push([score, e]);
      });
      hits.sort(function (a, b) { return b[0] - a[0]; });
      hits.slice(0, 14).forEach(function (hit, i) {
        var e = hit[1];
        var li = document.createElement('li');
        li.setAttribute('role', 'option');
        li.setAttribute('aria-selected', String(i === 0));
        li.innerHTML = '<a href="' + escapeHtml(e.u) + '"><span class="r-title">' + highlight(e.h || e.p, words) +
          (e.h ? ' <span>&middot; ' + escapeHtml(e.p) + '</span>' : '') + '</span><span class="r-text">' +
          highlight(snippet(e.t || '', words), words) + '</span></a>';
        li.querySelector('a').addEventListener('click', close);
        list.appendChild(li);
      });
      empty.hidden = hits.length > 0;
      if (!hits.length) empty.textContent = 'No results. Try another word.';
    }
    function select(i) {
      var items = list.children;
      if (!items.length) return;
      selected = (i + items.length) % items.length;
      Array.prototype.forEach.call(items, function (li, j) { li.setAttribute('aria-selected', String(j === selected)); });
      items[selected].scrollIntoView({ block: 'nearest' });
    }
    function open() {
      lastFocus = document.activeElement;
      panel.hidden = false;
      document.body.style.overflow = 'hidden';
      input.focus();
      input.select();
      load();
      run();
    }
    function close() {
      panel.hidden = true;
      document.body.style.overflow = '';
      if (lastFocus && lastFocus.focus) lastFocus.focus();
    }
    document.querySelectorAll('[data-search-open]').forEach(function (b) {
      b.addEventListener('click', function () {
        var menu = b.closest('details');
        if (menu) menu.removeAttribute('open');
        open();
      });
    });
    panel.addEventListener('click', function (e) { if (e.target === panel) close(); });
    input.addEventListener('input', run);
    input.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowDown') { e.preventDefault(); select(selected + 1); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); select(selected - 1); }
      else if (e.key === 'Enter') {
        var a = list.children[selected] && list.children[selected].querySelector('a');
        if (a) { e.preventDefault(); close(); location.href = a.getAttribute('href'); }
      }
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') {
        if (!panel.hidden) close();
        if (box && !box.hidden) { box.hidden = true; var bv = box.querySelector('video'); if (bv) { bv.pause(); bv.removeAttribute('src'); bv.load(); } }
        return;
      }
      var tag = (document.activeElement || {}).tagName || '';
      var typing = /^(INPUT|TEXTAREA|SELECT)$/.test(tag) || (document.activeElement && document.activeElement.isContentEditable);
      if (panel.hidden && !typing && (e.key === '/' || ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k'))) {
        e.preventDefault();
        open();
      }
    });
    // Warm the index when the pointer heads for the search button.
    document.querySelectorAll('[data-search-open]').forEach(function (b) {
      b.addEventListener('pointerenter', load, { once: true });
    });
  });
})();
