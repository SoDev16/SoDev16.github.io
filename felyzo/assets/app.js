/* FELYZO — interactions de la fiche produit */
(function () {
  "use strict";

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  var state = { color: "Noir", size: "M", offer: "1 harnais", price: "34,90 €" };

  /* ── Galerie ───────────────────────────────── */
  var mainImg = $("[data-gallery-main]");
  var counter = $("[data-gallery-counter]");
  var thumbs = $$(".gallery__thumbs button");

  thumbs.forEach(function (btn, i) {
    btn.addEventListener("click", function () {
      thumbs.forEach(function (b) { b.classList.remove("is-active"); });
      btn.classList.add("is-active");
      if (mainImg) mainImg.src = btn.dataset.thumb;
      if (counter) counter.textContent = i + 1 + "/" + thumbs.length;
    });
  });

  /* ── Groupes de choix ──────────────────────── */
  function group(selector, onPick) {
    var items = $$(selector);
    items.forEach(function (item) {
      item.addEventListener("click", function () {
        items.forEach(function (i) {
          i.classList.remove("is-active");
          i.setAttribute("aria-checked", "false");
        });
        item.classList.add("is-active");
        item.setAttribute("aria-checked", "true");
        onPick(item);
      });
    });
  }

  var colorLabel = $("[data-color-label]");
  var sizeLabel = $("[data-size-label]");

  group(".swatch", function (el) {
    state.color = el.dataset.color;
    if (colorLabel) colorLabel.textContent = state.color;
  });

  group(".size", function (el) {
    state.size = el.dataset.size;
    if (sizeLabel) sizeLabel.textContent = state.size;
  });

  /* ── Offres : les deux sélecteurs restent synchronisés ── */
  var stickyOffer = $("[data-sticky-offer]");
  var stickyPrice = $("[data-sticky-price]");

  function selectOffer(offer, price) {
    state.offer = offer;
    state.price = price;
    $$(".offer").forEach(function (o) {
      var on = o.dataset.offer === offer;
      o.classList.toggle("is-active", on);
      o.setAttribute("aria-checked", on ? "true" : "false");
    });
    if (stickyOffer) stickyOffer.textContent = offer;
    if (stickyPrice) stickyPrice.textContent = price;
  }

  $$(".offer").forEach(function (o) {
    o.addEventListener("click", function () {
      selectOffer(o.dataset.offer, o.dataset.price);
    });
  });

  /* ── Panier (démonstration) ────────────────── */
  var count = 0;
  var cartCount = $("[data-cart-count]");
  var added = $("[data-added]");
  var addedLabel = $("[data-added-label]");

  $$("[data-add-to-cart]").forEach(function (btn) {
    btn.addEventListener("click", function () {
      count += 1;
      if (cartCount) cartCount.textContent = String(count);
      if (added && addedLabel) {
        addedLabel.textContent =
          state.offer + " — " + state.color + ", taille " + state.size + " · " + state.price;
        added.hidden = false;
      }
    });
  });

  /* ── Barre d'achat collante ────────────────── */
  var bar = $("[data-stickybar]");
  var product = $("#produit");

  if (bar && product && "IntersectionObserver" in window) {
    bar.hidden = false;
    var sentinel = product.querySelector(".offers");
    var lastSection = $(".final");

    var show = function (on) { bar.classList.toggle("is-visible", on); };
    var passedOffers = false;
    var atFinal = false;
    var sync = function () { show(passedOffers && !atFinal); };

    new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        passedOffers = e.boundingClientRect.top < 0;
        sync();
      });
    }, { threshold: 0 }).observe(sentinel || product);

    if (lastSection) {
      new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          atFinal = e.isIntersecting;
          sync();
        });
      }, { threshold: 0.35 }).observe(lastSection);
    }
  }

  /* ── Guide des tailles ─────────────────────── */
  var guide = $("[data-guide]");
  var open = $("[data-open-guide]");
  var close = $("[data-close-guide]");

  if (guide && open) {
    open.addEventListener("click", function () {
      if (typeof guide.showModal === "function") guide.showModal();
      else guide.setAttribute("open", "");
    });
  }
  if (guide && close) {
    close.addEventListener("click", function () {
      if (typeof guide.close === "function") guide.close();
      else guide.removeAttribute("open");
    });
  }
  if (guide) {
    guide.addEventListener("click", function (e) {
      if (e.target === guide) guide.close();
    });
  }

  /* ── Accordéon : une seule réponse ouverte ─── */
  var items = $$(".accordion details");
  items.forEach(function (d) {
    d.addEventListener("toggle", function () {
      if (!d.open) return;
      items.forEach(function (o) { if (o !== d) o.open = false; });
    });
  });

  /* ── Vidéo (emplacement) ───────────────────── */
  var play = $(".video__play");
  if (play) {
    play.addEventListener("click", function () {
      play.insertAdjacentHTML(
        "afterend",
        '<p class="note" style="margin-top:10px">Emplacement vidéo : remplacez le poster et branchez le lecteur (vidéo verticale 9:16).</p>'
      );
      play.remove();
    });
  }

  /* ── Newsletter (démonstration) ────────────── */
  var form = $("[data-newsletter]");
  if (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      form.innerHTML = '<p style="margin:0;font-size:.85rem">Merci, votre inscription est enregistrée.</p>';
    });
  }
})();
