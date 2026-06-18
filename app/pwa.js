/* pwa.js — service-worker registration, storage persistence, install hint.
   No-ops on file:// (service workers require http/https; offline-from-disk needs no SW). */
(function () {
  "use strict";

  var proto = location.protocol;
  if (proto !== "https:" && proto !== "http:") return;  // file:// — already offline, skip SW

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("./sw.js").catch(function () {});
    });
  }

  // Opportunistically request durable storage (helps resist eviction).
  if (navigator.storage && navigator.storage.persist) {
    navigator.storage.persisted()
      .then(function (persisted) { if (!persisted) return navigator.storage.persist(); })
      .catch(function () {});
  }

  var DISMISS_KEY = "secstudy:install-dismissed";
  function dismissed() {
    try { return localStorage.getItem(DISMISS_KEY) === "1"; } catch (e) { return false; }
  }
  function el(id) { return document.getElementById(id); }
  function show(msg, withButton) {
    var hint = el("installHint"), m = el("installMsg"), b = el("installBtn");
    if (!hint || !m || !b || dismissed()) return;
    m.textContent = msg;
    b.hidden = !withButton;
    hint.hidden = false;
  }
  function hide() { var hint = el("installHint"); if (hint) hint.hidden = true; }
  function dismiss() {
    try { localStorage.setItem(DISMISS_KEY, "1"); } catch (e) {}
    hide();
  }

  var deferredPrompt = null;
  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    deferredPrompt = e;
    show("Install for durable, offline study.", true);
  });
  window.addEventListener("appinstalled", function () { dismiss(); });

  function wire() {
    var b = el("installBtn");
    var d = el("installDismiss");
    if (b) b.addEventListener("click", function () {
      if (!deferredPrompt) return;
      deferredPrompt.prompt();
      deferredPrompt.userChoice.finally(function () { deferredPrompt = null; hide(); });
    });
    if (d) d.addEventListener("click", dismiss);

    // iOS Safari has no beforeinstallprompt; home-screen install is the durability
    // switch (exempts study state from ITP's ~7-day eviction), so hint how.
    var ua = navigator.userAgent || "";
    var isIos = /iPad|iPhone|iPod/.test(ua) && !window.MSStream;
    var standalone = ("standalone" in navigator) && navigator.standalone;
    if (isIos && !standalone) {
      show("Add to Home Screen (Share → Add to Home Screen) for durable offline study.", false);
    }
  }

  if (document.readyState !== "loading") wire();
  else document.addEventListener("DOMContentLoaded", wire);
})();
