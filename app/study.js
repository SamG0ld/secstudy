/* study.js — controller: state, deck logic, persistence, event wiring.
   Consumes the registry via STUDY.onBoot; renders through Cards.* (view layer).
   localStorage is keyed by the stable card id, namespaced per subject. */
(function () {
  "use strict";

  var $ = function (id) { return document.getElementById(id); };
  function setText(el, s) { el.textContent = (s == null) ? "" : s; }

  var state = {
    view: null,
    subject: null,
    subjectObj: null,
    cards: [],
    deck: [],
    i: 0,
    revealed: false,
    known: new Set(),
    topic: "ALL",
    hideKnown: false,
  };

  function knownKey(subject) { return "secstudy:" + subject + ":known"; }
  function prefsKey(subject) { return "secstudy:" + subject + ":prefs"; }

  function loadPersisted(subject) {
    try { state.known = new Set(JSON.parse(localStorage.getItem(knownKey(subject)) || "[]")); }
    catch (e) { state.known = new Set(); }
    try {
      var p = JSON.parse(localStorage.getItem(prefsKey(subject)) || "{}");
      state.topic = p.topic || "ALL";
      state.hideKnown = !!p.hideKnown;
    } catch (e) { state.topic = "ALL"; state.hideKnown = false; }
  }
  function saveKnown() {
    var arr = [];
    state.known.forEach(function (v) { arr.push(v); });
    try { localStorage.setItem(knownKey(state.subject), JSON.stringify(arr)); } catch (e) {}
  }
  function savePrefs() {
    try {
      localStorage.setItem(prefsKey(state.subject),
        JSON.stringify({ topic: state.topic, hideKnown: state.hideKnown }));
    } catch (e) {}
  }

  function shuffle(a) {
    var r = a.slice();
    for (var k = r.length - 1; k > 0; k--) {
      var j = Math.floor(Math.random() * (k + 1));
      var t = r[k]; r[k] = r[j]; r[j] = t;
    }
    return r;
  }

  function scopeCards() {
    var list = state.cards;
    if (state.topic.indexOf("CAT:") === 0) {
      var cat = state.topic.slice(4);
      list = list.filter(function (c) { return String(c.deck).split("::")[0] === cat; });
    } else if (state.topic.indexOf("SD:") === 0) {
      var d = state.topic.slice(3);
      list = list.filter(function (c) { return c.deck === d; });
    }
    if (state.hideKnown) list = list.filter(function (c) { return !state.known.has(c.id); });
    return list;
  }

  function mixFromEach() {
    var bySd = Object.create(null);
    for (var i = 0; i < state.cards.length; i++) {
      var c = state.cards[i];
      if (state.hideKnown && state.known.has(c.id)) continue;
      (bySd[c.deck] = bySd[c.deck] || []).push(c);
    }
    var sds = Object.keys(bySd);
    var per = sds.length > 8 ? 3 : 5;
    var out = [];
    for (var s = 0; s < sds.length; s++) out = out.concat(shuffle(bySd[sds[s]]).slice(0, per));
    return shuffle(out);
  }

  function setDeck(list) { state.deck = list; state.i = 0; state.revealed = false; render(); }
  function load() { setDeck(shuffle(scopeCards())); }
  function current() { return state.deck[state.i]; }

  function render() {
    var c = current();
    Cards.renderCard(c, state.revealed, c ? state.known.has(c.id) : false);
    setText($("pos"), state.deck.length ? (state.i + 1) + " / " + state.deck.length : "0 / 0");
    setText($("tag"), c ? String(c.deck).replace("::", " / ") : "");
    setText($("knownCount"), state.known.size + " known");
  }

  function flip() { state.revealed = !state.revealed; render(); }
  function next() {
    if (!state.deck.length) return;
    state.i = (state.i + 1) % state.deck.length; state.revealed = false; render();
  }
  function prev() {
    if (!state.deck.length) return;
    state.i = (state.i - 1 + state.deck.length) % state.deck.length; state.revealed = false; render();
  }
  function toggleKnown() {
    var c = current(); if (!c) return;
    if (state.known.has(c.id)) state.known.delete(c.id); else state.known.add(c.id);
    saveKnown();
    if (state.hideKnown && state.known.has(c.id)) {   // just became known -> drop it from view now
      var i = state.i;
      load();
      state.i = Math.min(i, Math.max(0, state.deck.length - 1));
      render();
    } else {
      render();
    }
  }

  function buildSubjectSelect() {
    var sel = $("subject");
    var label = $("subjectLabel");
    sel.replaceChildren();
    for (var i = 0; i < state.view.subjects.length; i++) {
      var s = state.view.subjects[i];
      var opt = document.createElement("option");
      opt.value = s.slug;
      opt.textContent = (s.meta && s.meta.title) || s.slug;
      sel.appendChild(opt);
    }
    // With a single subject the dropdown has nothing to pick — show a plain
    // label instead, and only reveal the real <select> once there are 2+.
    var single = state.view.subjects.length < 2;
    sel.hidden = single;
    if (label) {
      label.hidden = !single;
      label.textContent = (single && sel.options.length) ? sel.options[0].textContent : "";
    }
  }

  function buildTopicSelect() {
    var sel = $("topic");
    sel.replaceChildren();
    var opts = Cards.topicOptions(state.cards);
    for (var i = 0; i < opts.length; i++) {
      var opt = document.createElement("option");
      opt.value = opts[i].value;
      opt.textContent = opts[i].label;
      sel.appendChild(opt);
    }
    sel.value = state.topic;
    if (sel.value !== state.topic) { state.topic = "ALL"; sel.value = "ALL"; }  // saved topic gone
  }

  function selectSubject(slug, defer) {
    var s = null;
    for (var i = 0; i < state.view.subjects.length; i++) {
      if (state.view.subjects[i].slug === slug) { s = state.view.subjects[i]; break; }
    }
    if (!s) s = state.view.subjects[0];
    state.subject = s.slug;
    state.subjectObj = s;
    state.cards = (s.modules.cards && s.modules.cards.items) || [];
    loadPersisted(state.subject);
    $("subject").value = state.subject;
    buildTopicSelect();
    $("hideKnown").checked = state.hideKnown;
    if (!defer) load();   // jumpTo defers: it sets its own full-subject deck
  }

  function renderCards(items) { setDeck(items.slice()); }  // standalone (per plan)

  function openDrawer() {
    var c = current(); if (!c) return;
    Cards.renderDrawer(c, state.subjectObj && state.subjectObj.meta);
    $("drawer").hidden = false;
    $("scrim").hidden = false;
    $("detailsBtn").setAttribute("aria-expanded", "true");
  }
  function closeDrawer() {
    $("drawer").hidden = true;
    $("scrim").hidden = true;
    $("detailsBtn").setAttribute("aria-expanded", "false");
  }

  function doSearch(q) {
    q = q.trim().toLowerCase();
    if (q.length < 2) { Cards.renderSearchResults([], function () {}); return; }
    var matches = state.view.allCards.filter(function (c) {
      return (c.q && c.q.toLowerCase().indexOf(q) >= 0) ||
        (c.a && c.a.toLowerCase().indexOf(q) >= 0) ||
        (c.deck && c.deck.toLowerCase().indexOf(q) >= 0) ||
        (c.tags && c.tags.join(" ").toLowerCase().indexOf(q) >= 0);
    });
    Cards.renderSearchResults(matches, jumpTo);
  }

  function jumpTo(m) {
    if (m.subject !== state.subject) selectSubject(m.subject, true);  // defer load; we set deck below
    state.topic = "ALL"; $("topic").value = "ALL"; savePrefs();       // keep dropdown coherent with deck
    var deck = state.cards.slice();                                   // full-subject deck, source order
    var idx = 0;
    for (var i = 0; i < deck.length; i++) { if (deck[i].id === m.id) { idx = i; break; } }
    state.deck = deck; state.i = idx; state.revealed = false;
    $("search").value = "";
    Cards.renderSearchResults([], function () {});
    render();
  }

  function isTypingTarget(el) {
    return el && (el.tagName === "INPUT" || el.tagName === "SELECT" || el.tagName === "TEXTAREA");
  }

  function wire() {
    var x0 = null, y0 = 0, swiped = false;
    $("card").addEventListener("click", function () { if (swiped) { swiped = false; return; } flip(); });
    $("flip").addEventListener("click", function (e) { e.stopPropagation(); flip(); });
    $("next").addEventListener("click", next);
    $("prev").addEventListener("click", prev);
    $("know").addEventListener("click", toggleKnown);
    $("shuffle").addEventListener("click", function () {
      setDeck(shuffle(state.deck.length ? state.deck : scopeCards()));
    });
    $("mix").addEventListener("click", function () {
      state.topic = "ALL"; $("topic").value = "ALL"; savePrefs();  // Mix spans all subdecks
      setDeck(mixFromEach());
    });
    $("hideKnown").addEventListener("change", function (e) {
      state.hideKnown = e.target.checked; savePrefs(); load();
    });
    $("resetKnown").addEventListener("click", function () {
      if (confirm("Reset known cards for this subject?")) { state.known.clear(); saveKnown(); load(); }
    });
    $("topic").addEventListener("change", function (e) { state.topic = e.target.value; savePrefs(); load(); });
    $("subject").addEventListener("change", function (e) { selectSubject(e.target.value); });
    $("detailsBtn").addEventListener("click", function (e) { e.stopPropagation(); openDrawer(); });
    $("drawerClose").addEventListener("click", closeDrawer);
    $("scrim").addEventListener("click", closeDrawer);
    $("search").addEventListener("input", function (e) { doSearch(e.target.value); });

    document.addEventListener("keydown", function (e) {
      if (isTypingTarget(e.target)) {
        if (e.key === "Escape") { e.target.blur(); }
        return;
      }
      if (!$("drawer").hidden) {              // drawer open: don't drive the deck behind it
        if (e.key === "Escape") closeDrawer();
        return;
      }
      if (e.key === " ") { e.preventDefault(); flip(); }
      else if (e.key === "ArrowRight") next();
      else if (e.key === "ArrowLeft") prev();
      else if (e.key.toLowerCase() === "k") toggleKnown();
      else if (e.key.toLowerCase() === "s") setDeck(shuffle(state.deck.length ? state.deck : scopeCards()));
      else if (e.key === "Escape") closeDrawer();
    });

    var cd = $("card");
    cd.addEventListener("touchstart", function (e) {
      x0 = e.touches[0].clientX; y0 = e.touches[0].clientY; swiped = false;
    }, { passive: true });
    cd.addEventListener("touchend", function (e) {
      if (x0 === null) return;
      var dx = e.changedTouches[0].clientX - x0;
      var dy = e.changedTouches[0].clientY - y0;
      if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy)) {  // horizontal swipe, not a scroll
        swiped = true;                                          // suppress the trailing click -> flip
        if (dx < 0) next(); else prev();
      }
      x0 = null;
    });
  }

  STUDY.onBoot(function (view) {
    state.view = view;
    wire();
    buildSubjectSelect();
    if (view.subjects.length) selectSubject(view.subjects[0].slug);
    else Cards.renderCard(null, false, false);
  });

  window.App = { selectSubject: selectSubject, renderCards: renderCards };
})();
