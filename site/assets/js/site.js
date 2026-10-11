// =============================================================================
//  site/assets/js/site.js — small progressive enhancements of the Inkpaw site
// =============================================================================
//  The pages work without it; with it:
//    * the light/dark toggle (remembered in localStorage; the system choice
//      is used until the toggle is pressed — see the inline <head> snippet)
//    * "Copy" buttons next to commands  ([data-copy] = the text to copy)
//    * the screenshot gallery: filters + a large viewer
//    * the docs sidebar highlights the guide being read
// =============================================================================
(function () {
  "use strict";
  var root = document.documentElement;
  var KEY = "inkpaw-theme";

  function store(v) { try { localStorage.setItem(KEY, v); } catch (e) { /* private mode */ } }
  function isDark() {
    var t = root.getAttribute("data-theme");
    if (t) return t === "dark";
    return window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  }

  // --- theme toggle ------------------------------------------------------------
  document.querySelectorAll("[data-theme-toggle]").forEach(function (btn) {
    function label() {
      btn.setAttribute("aria-pressed", isDark() ? "true" : "false");
    }
    label();
    btn.addEventListener("click", function () {
      var next = isDark() ? "light" : "dark";
      root.setAttribute("data-theme", next);
      store(next);
      label();
    });
  });

  // --- copy buttons --------------------------------------------------------------
  document.querySelectorAll("[data-copy]").forEach(function (btn) {
    var idle = btn.textContent;
    btn.addEventListener("click", function () {
      var text = btn.getAttribute("data-copy");
      var done = function () {
        btn.textContent = btn.getAttribute("data-copied") || "Copied!";
        setTimeout(function () { btn.textContent = idle; }, 1600);
      };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(done, done);
      } else {
        var ta = document.createElement("textarea");
        ta.value = text; document.body.appendChild(ta); ta.select();
        try { document.execCommand("copy"); } catch (e) { /* ignore */ }
        ta.remove(); done();
      }
    });
  });

  // --- gallery -----------------------------------------------------------------------
  var viewer = document.querySelector("[data-viewer]");
  if (viewer) {
    var vImg = viewer.querySelector("img");
    var vTitle = viewer.querySelector("[data-v-title]");
    var vText = viewer.querySelector("[data-v-text]");
    var vKeys = viewer.querySelector("[data-v-keys]");
    var links = document.querySelectorAll("[data-shot]");
    links.forEach(function (a) {
      a.addEventListener("click", function (ev) {
        ev.preventDefault();
        vImg.src = a.getAttribute("href");
        vImg.alt = a.getAttribute("data-alt");
        vTitle.textContent = a.getAttribute("data-title");
        vText.textContent = a.getAttribute("data-text");
        var k = a.getAttribute("data-keys");
        vKeys.textContent = k; vKeys.hidden = !k;
        links.forEach(function (o) { o.removeAttribute("aria-current"); });
        a.setAttribute("aria-current", "true");
        viewer.scrollIntoView({ block: "nearest" });
      });
    });
    document.querySelectorAll("[data-filter]").forEach(function (btn, _, all) {
      btn.addEventListener("click", function () {
        var f = btn.getAttribute("data-filter");
        all.forEach(function (b) { b.setAttribute("aria-pressed", b === btn ? "true" : "false"); });
        document.querySelectorAll("[data-cat]").forEach(function (li) {
          li.hidden = !(f === "all" || li.getAttribute("data-cat") === f);
        });
      });
    });
  }

  // --- docs: highlight the guide in view ------------------------------------------------
  var navLinks = document.querySelectorAll(".docs-nav a[href^='#']");
  if (navLinks.length && "IntersectionObserver" in window) {
    var byId = {};
    navLinks.forEach(function (a) { byId[a.getAttribute("href").slice(1)] = a; });
    var obs = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        navLinks.forEach(function (a) { a.classList.remove("active"); a.removeAttribute("aria-current"); });
        var a = byId[en.target.id];
        if (a) { a.classList.add("active"); a.setAttribute("aria-current", "location"); }
      });
    }, { rootMargin: "-20% 0px -70% 0px" });
    document.querySelectorAll(".doc[id]").forEach(function (s) { obs.observe(s); });
  }
})();
