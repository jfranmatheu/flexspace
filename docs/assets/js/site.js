/* FlexSpace site: theme toggle, sticky nav state, reveal on scroll, lightbox, theme compare, sub-nav highlight.
   No dependencies. Everything on the page works without it; this only adds comfort. */
(function () {
  "use strict";

  /* ---- Links set in one place (docs/_design/build_docs.py reads SUPERHIVE_URL from here too, so the docs
     follow). Fill SUPERHIVE_URL in when the product page is live, then rerun build_docs.py. ---- */
  // TODO(author): the FlexSpace product URL on Superhive. Until then, links go to the Superhive home page.
  var SUPERHIVE_URL = "https://superhivemarket.com/";
  var CHANGELOG_URL = "https://github.com/franb3d/flexspace/releases";
  var ISSUES_URL = "https://github.com/franb3d/flexspace/issues";
  var BUG_FORM_URL = "https://github.com/franb3d/flexspace/issues/new?template=flexspace.yml";

  var links = { superhive: SUPERHIVE_URL, changelog: CHANGELOG_URL, issues: ISSUES_URL, bug: BUG_FORM_URL };
  document.querySelectorAll("a[data-link]").forEach(function (a) {
    var url = links[a.getAttribute("data-link")];
    if (url) a.href = url;
  });

  var root = document.documentElement;
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)");

  /* ---- Theme: a saved choice wins, else dark (DESIGN.md: dark by default, the same as the docs). The <head>
     script already applied it before paint. ---- */
  var KEY = "fs-theme";
  function stored() { try { return localStorage.getItem(KEY); } catch (e) { return null; } }
  function save(v) { try { localStorage.setItem(KEY, v); } catch (e) { /* private mode: keep it for this page */ } }
  function apply(theme) {
    if (theme === "light") root.setAttribute("data-theme", "light");
    else root.setAttribute("data-theme", "dark");
    var meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", theme === "light" ? "#f7f5f1" : "#0a0a0c");
    document.querySelectorAll(".fs-theme").forEach(function (b) {
      var light = theme === "light";
      b.setAttribute("aria-pressed", light ? "true" : "false");
      b.setAttribute("aria-label", light ? "Switch to the dark theme" : "Switch to the light theme");
      b.title = b.getAttribute("aria-label");
    });
  }
  apply(stored() === "light" ? "light" : "dark");
  document.querySelectorAll(".fs-theme").forEach(function (b) {
    b.addEventListener("click", function () {
      var next = root.getAttribute("data-theme") === "light" ? "dark" : "light";
      save(next);
      apply(next);
    });
  });

  /* ---- Sticky nav: a hairline once the page scrolls ---- */
  var nav = document.querySelector(".fs-nav");
  if (nav) {
    var onScroll = function () { nav.classList.toggle("is-scrolled", window.scrollY > 8); };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  /* close the mobile menu on Escape or after picking a link */
  document.querySelectorAll(".fs-menu").forEach(function (menu) {
    menu.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && menu.open) { menu.open = false; menu.querySelector("summary").focus(); }
    });
    menu.querySelectorAll("a").forEach(function (a) { a.addEventListener("click", function () { menu.open = false; }); });
    document.addEventListener("click", function (e) { if (menu.open && !menu.contains(e.target)) menu.open = false; });
  });

  /* ---- Reveal on scroll ---- */
  var reveals = document.querySelectorAll(".fs-reveal");
  if ("IntersectionObserver" in window && !reduce.matches) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) { en.target.classList.add("is-in"); io.unobserve(en.target); }
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });
    reveals.forEach(function (el) { io.observe(el); });
  } else {
    reveals.forEach(function (el) { el.classList.add("is-in"); });
  }

  /* ---- Lightbox: any <a data-zoom href="big.webp"> holding an <img> ---- */
  var zooms = document.querySelectorAll("a[data-zoom]");
  if (zooms.length && typeof HTMLDialogElement === "function") {
    var dlg = document.createElement("dialog");
    dlg.className = "fs-lightbox";
    dlg.setAttribute("aria-label", "Image viewer");
    dlg.innerHTML =
      '<button class="fs-lightbox__close" type="button" aria-label="Close">' +
      '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>' +
      "</button><figure><img alt=\"\"><video controls loop muted playsinline hidden></video><figcaption></figcaption></figure>";
    document.body.appendChild(dlg);
    var big = dlg.querySelector("img");
    var vid = dlg.querySelector("video");
    var cap = dlg.querySelector("figcaption");
    var opener = null;
    var close = function () { dlg.close(); };
    dlg.querySelector(".fs-lightbox__close").addEventListener("click", close);
    dlg.addEventListener("click", function (e) { if (e.target === dlg || e.target.tagName === "FIGURE") close(); });
    dlg.addEventListener("close", function () {
      big.removeAttribute("src");
      vid.pause(); vid.removeAttribute("src"); vid.load();
      if (opener) opener.focus();
    });
    zooms.forEach(function (a) {
      a.addEventListener("click", function (e) {
        if (e.metaKey || e.ctrlKey || e.shiftKey || e.button === 1) return;
        e.preventDefault();
        var img = a.querySelector("img");
        var inline = a.querySelector("video");
        opener = a;
        var text = a.getAttribute("data-caption") || (img ? img.alt : inline ? inline.getAttribute("aria-label") || "" : "");
        var isVideo = a.hasAttribute("data-video");
        big.hidden = isVideo;
        vid.hidden = !isVideo;
        if (isVideo) {
          big.removeAttribute("src");
          vid.poster = inline ? inline.getAttribute("poster") || "" : "";
          vid.src = a.getAttribute("href");
          vid.setAttribute("aria-label", text);
          if (!reduce.matches) { var p = vid.play(); if (p && p.catch) p.catch(function () {}); }
        } else {
          big.src = a.getAttribute("href");
        }
        big.alt = text;
        var fc = a.closest("figure") && a.closest("figure").querySelector("figcaption");
        cap.textContent = fc ? fc.textContent.trim() : text;
        cap.hidden = !cap.textContent;
        dlg.showModal();
      });
    });
  }

  /* ---- Real loops: <video class="fs-loop" data-src="x.mp4" poster="x.webp">. The file is fetched only when the
     video scrolls near the view, plays while it is visible and pauses when it leaves. With reduced motion only the
     poster shows (a click opens the loop in the lightbox, with controls). ---- */
  var loops = document.querySelectorAll("video.fs-loop[data-src]");
  if (loops.length && "IntersectionObserver" in window) {
    var lo = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        var v = en.target;
        var frame = v.closest(".fs-real__frame");
        if (en.isIntersecting && !reduce.matches) {
          if (!v.getAttribute("src")) { v.src = v.getAttribute("data-src"); }
          var p = v.play();
          if (p && p.then) p.then(function () { if (frame) frame.classList.add("is-playing"); }).catch(function () {});
        } else if (!v.paused) {
          v.pause();
          if (frame) frame.classList.remove("is-playing");
        }
      });
    }, { rootMargin: "120px 0px", threshold: 0.25 });
    loops.forEach(function (v) { v.muted = true; lo.observe(v); });
  }

  /* ---- Themes compare: the range moves the split ---- */
  document.querySelectorAll(".fs-compare").forEach(function (box) {
    var r = box.querySelector('input[type="range"]');
    if (!r) return;
    var set = function () { box.style.setProperty("--pos", r.value + "%"); };
    r.addEventListener("input", set);
    set();
  });

  /* ---- Sub-nav: highlight the group in view ---- */
  var sub = document.querySelector(".fs-subnav");
  if (sub && "IntersectionObserver" in window) {
    var map = {};
    sub.querySelectorAll('a[href^="#"]').forEach(function (a) { map[a.getAttribute("href").slice(1)] = a; });
    var current = null;
    var so = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        var a = map[en.target.id];
        if (!a || a === current) return;
        if (current) { current.classList.remove("is-active"); current.removeAttribute("aria-current"); }
        current = a;
        a.classList.add("is-active");
        a.setAttribute("aria-current", "true");
        var ul = a.parentElement && a.parentElement.parentElement;
        if (ul && ul.scrollWidth > ul.clientWidth) {
          ul.scrollTo({ left: a.offsetLeft - 16, behavior: reduce.matches ? "auto" : "smooth" });
        }
      });
    }, { rootMargin: "-30% 0px -60% 0px" });
    Object.keys(map).forEach(function (id) { var el = document.getElementById(id); if (el) so.observe(el); });
  }

  /* ---- Year in the footer ---- */
  document.querySelectorAll("[data-year]").forEach(function (el) { el.textContent = String(new Date().getFullYear()); });
})();
