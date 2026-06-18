/* cards.js — view layer for the cards module. Renders a card, its provenance,
   the detail drawer, topic options, and search results. All card content is
   written via textContent (never innerHTML); the only data-driven attribute is
   a validated https:// link href with rel="noopener noreferrer". */
(function () {
  "use strict";

  var $ = function (id) { return document.getElementById(id); };

  function setText(el, s) { el.textContent = (s == null) ? "" : s; }
  function isHttps(u) { return typeof u === "string" && /^https:\/\//.test(u); }

  function hostOf(u) {
    try { return new URL(u).hostname; } catch (e) { return "source"; }
  }

  function freshnessClass(dateStr) {
    var then = Date.parse(dateStr);
    if (isNaN(then)) return "stale";
    var days = (Date.now() - then) / 86400000;
    if (days <= 120) return "fresh";
    if (days <= 365) return "aging";
    return "stale";
  }

  function renderCard(card, revealed, isKnown) {
    if (!card) {
      setText($("front"), "No cards in this set.");
      setText($("back"), "");
      $("back").className = "a";
      $("prov").hidden = true;
      $("hint").style.display = "none";
      setText($("flip"), "Reveal");
      return;
    }
    $("hint").style.display = "";
    setText($("front"), card.q);
    setText($("back"), card.a);
    $("back").className = revealed ? "a show" : "a";
    setText($("flip"), revealed ? "Hide" : "Reveal");
    setText($("know"), isKnown ? "Known ✓" : "Known");
    $("card").classList.toggle("known", !!isKnown);
    $("prov").hidden = false;
    renderProvenance(card);
  }

  function renderProvenance(card) {
    var link = $("srcLink");
    var ver = $("verified");
    if (isHttps(card.source)) {
      link.href = card.source;
      link.hidden = false;
      setText(link, "source: " + hostOf(card.source));
    } else {
      link.hidden = true;
      link.removeAttribute("href");
    }
    if (card.unverified) {
      ver.hidden = false;
      setText(ver, "⚠ unverified source");
      ver.className = "verified unverified";
    } else if (card.verified) {
      ver.hidden = false;
      setText(ver, "verified " + card.verified);
      ver.className = "verified " + freshnessClass(card.verified);
    } else {
      ver.hidden = true;
    }
  }

  function topicOptions(cards) {
    var byCat = Object.create(null);
    var catCount = Object.create(null);
    for (var i = 0; i < cards.length; i++) {
      var deck = String(cards[i].deck);
      var cat = deck.split("::")[0];
      (byCat[cat] = byCat[cat] || {});
      byCat[cat][deck] = (byCat[cat][deck] || 0) + 1;
      catCount[cat] = (catCount[cat] || 0) + 1;
    }
    var opts = [{ value: "ALL", label: "All (" + cards.length + ")" }];
    var cats = Object.keys(byCat).sort();
    for (var c = 0; c < cats.length; c++) {
      var cat = cats[c];
      opts.push({ value: "CAT:" + cat, label: cat + " (" + catCount[cat] + ")" });
      var decks = Object.keys(byCat[cat]).sort();
      for (var d = 0; d < decks.length; d++) {
        var deck = decks[d];
        var leaf = deck.indexOf("::") >= 0 ? deck.split("::").slice(1).join("::") : deck;
        opts.push({ value: "SD:" + deck, label: "  " + leaf + " (" + byCat[cat][deck] + ")" });
      }
    }
    return opts;
  }

  function renderDrawer(card, subjectMeta) {
    var body = $("drawerBody");
    body.replaceChildren();
    function add(cls, text) {
      var el = document.createElement("div");
      el.className = cls; el.textContent = text; body.appendChild(el);
    }
    add("drawer-deck", card.deck);
    if (subjectMeta && subjectMeta.blurb) add("drawer-blurb", subjectMeta.blurb);

    var links = [];
    if (isHttps(card.source)) links.push({ label: "Primary source (" + hostOf(card.source) + ")", url: card.source });
    var refs = card.refs || [];
    for (var i = 0; i < refs.length; i++) if (isHttps(refs[i].url)) links.push(refs[i]);
    if (links.length) {
      add("drawer-h", "Proof");
      for (var j = 0; j < links.length; j++) {
        var a = document.createElement("a");
        a.href = links[j].url;
        a.target = "_blank";
        a.rel = "noopener noreferrer";
        a.className = "drawer-link";
        a.textContent = links[j].label;
        body.appendChild(a);
      }
    }
    if (card.unverified) add("drawer-verified", "⚠ Source not independently verified" + (card.verified ? " (added " + card.verified + ")" : ""));
    else if (card.verified) add("drawer-verified", "Verified " + card.verified);
    if (card.tags && card.tags.length) add("drawer-tags", "Tags: " + card.tags.join(", "));
  }

  function renderSearchResults(matches, onPick) {
    var box = $("searchResults");
    box.replaceChildren();
    if (!matches.length) { box.hidden = true; return; }
    var shown = matches.slice(0, 30);
    for (var i = 0; i < shown.length; i++) {
      (function (m) {
        var item = document.createElement("button");
        item.type = "button";
        item.className = "search-item";
        item.textContent = "[" + m.subject + " / " + m.deck + "] " + m.q;
        item.addEventListener("click", function () { onPick(m); });
        box.appendChild(item);
      })(shown[i]);
    }
    if (matches.length > shown.length) {
      var more = document.createElement("div");
      more.className = "search-more";
      more.textContent = "+" + (matches.length - shown.length) + " more — refine your search";
      box.appendChild(more);
    }
    box.hidden = false;
  }

  window.Cards = {
    renderCard: renderCard,
    topicOptions: topicOptions,
    renderDrawer: renderDrawer,
    renderSearchResults: renderSearchResults,
    isHttps: isHttps,
  };
})();
