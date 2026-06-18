/* loader.js — window.STUDY registry + ordered <script src> bootstrap.
   Zero-dependency. Identical behavior on file:// and https (no protocol branches).
   Data files call STUDY.register(...); the generated manifest calls
   STUDY.expect(n) + STUDY.use([...]); boot fires when every file settles
   (onload OR onerror) or a ~3s watchdog elapses, whichever comes first. */
(function () {
  "use strict";

  // Clickjacking guard: a <meta> CSP cannot set frame-ancestors and GitHub Pages
  // cannot send X-Frame-Options, so refuse to run when embedded in a frame. Fails
  // safe: any throw reading window.top (cross-origin / sandboxed frame) is treated
  // as framed. A sandboxed iframe can still defeat any JS framebuster — header-level
  // frame-ancestors/XFO is the complete fix where the host supports it.
  var framed = true;
  try { framed = (window.top !== window.self); } catch (e) { framed = true; }
  if (framed) {
    var noop = function () {};
    window.STUDY = {
      register: noop, expect: noop, use: noop, onBoot: noop,
      grouped: function () { return { subjects: [], allCards: [] }; },
    };
    try { window.top.location = window.self.location; } catch (e) {}  // break out if allowed
    try {                                                            // else neutralize, don't just hide
      document.documentElement.style.display = "none";
      if (document.body) document.body.replaceChildren();
    } catch (e) {}
    return;
  }

  var reg = Object.create(null);   // slug -> { meta, modules: { module -> [items] } }
  var expected = 0;
  var settled = 0;
  var booted = false;
  var watchdog = null;
  var grouped = null;              // memoized view; busted on register()
  var bootHandlers = [];

  function register(payload) {
    if (!payload || !payload.subject || !payload.module || !Array.isArray(payload.items)) return;
    var s = reg[payload.subject] ||
      (reg[payload.subject] = { meta: null, modules: Object.create(null) });
    if (payload.subjectMeta && !s.meta) s.meta = payload.subjectMeta;  // first writer wins
    var bucket = s.modules[payload.module] || (s.modules[payload.module] = []);
    for (var i = 0; i < payload.items.length; i++) bucket.push(payload.items[i]);
    grouped = null;
    if (booted) rerender();        // late file after boot -> re-render
  }

  function expect(n) { expected += n; }     // additive (expected FILE count)

  function use(files) {
    if (!watchdog) watchdog = setTimeout(boot, 3000);
    for (var i = 0; i < files.length; i++) {
      var el = document.createElement("script");
      el.src = files[i];
      el.async = false;            // ordered execution among injected scripts
      el.onload = onSettle;
      el.onerror = onSettle;       // missing .private file 404 is swallowed here
      document.head.appendChild(el);
    }
  }

  function onSettle() {            // counts FILES resolved, not register() calls
    settled++;
    if (expected > 0 && settled >= expected) boot();
  }

  function boot() {
    if (booted) return;           // idempotent: at most once, despite counter/watchdog race
    booted = true;
    if (watchdog) { clearTimeout(watchdog); watchdog = null; }
    rerender();
  }

  function rerender() {
    var view;
    try { view = buildGrouped(); }
    catch (e) { view = { subjects: [], allCards: [] }; }  // a poison card must not blank the app
    for (var i = 0; i < bootHandlers.length; i++) {
      try { bootHandlers[i](view); } catch (e) { /* one bad handler must not kill the app */ }
    }
  }

  function onBoot(fn) {
    bootHandlers.push(fn);
    if (booted) { try { fn(buildGrouped()); } catch (e) {} }
  }

  function leafOf(deck) {
    deck = String(deck);
    return deck.indexOf("::") >= 0 ? deck.split("::").slice(1).join("::") : deck;
  }

  function buildGrouped() {
    if (grouped) return grouped;
    var subjects = [];
    var allCards = [];
    var slugs = Object.keys(reg);
    for (var i = 0; i < slugs.length; i++) {
      var slug = slugs[i];
      var s = reg[slug];
      var modules = {};
      var mkeys = Object.keys(s.modules);
      for (var m = 0; m < mkeys.length; m++) {
        var mod = mkeys[m];
        var items = s.modules[mod];
        var byDeck = Object.create(null);
        var byCategory = Object.create(null);
        for (var c = 0; c < items.length; c++) {
          var it = items[c];
          (byDeck[it.deck] = byDeck[it.deck] || []).push(it);
          var cat = String(it.deck).split("::")[0];
          var leaf = leafOf(it.deck);
          var cobj = byCategory[cat] || (byCategory[cat] = { decks: [] });
          if (cobj.decks.indexOf(leaf) < 0) cobj.decks.push(leaf);
          if (mod === "cards") {
            allCards.push({
              subject: slug, deck: it.deck, id: it.id, q: it.q, a: it.a,
              tags: it.tags || [], source: it.source, verified: it.verified,
              refs: it.refs || [],
            });
          }
        }
        modules[mod] = { items: items, byDeck: byDeck, byCategory: byCategory };
      }
      subjects.push({ slug: slug, meta: s.meta || { slug: slug, title: slug }, modules: modules });
    }
    subjects.sort(function (a, b) {
      var oa = (a.meta && typeof a.meta.order === "number") ? a.meta.order : 999;
      var ob = (b.meta && typeof b.meta.order === "number") ? b.meta.order : 999;
      if (oa !== ob) return oa - ob;
      return a.slug < b.slug ? -1 : (a.slug > b.slug ? 1 : 0);
    });
    grouped = { subjects: subjects, allCards: allCards };
    return grouped;
  }

  window.STUDY = {
    register: register, expect: expect, use: use, onBoot: onBoot, grouped: buildGrouped,
  };

  // Last-resort boot: if the manifest never calls expect()/use() (missing/empty manifest,
  // or index.html opened without a build), still boot after ~3s so the empty-state renders
  // instead of a permanently blank page. use() won't re-arm (it guards on !watchdog).
  watchdog = setTimeout(boot, 3000);
})();
