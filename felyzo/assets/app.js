/* FELYZO — interactions de la page produit */
(function () {
  "use strict";

  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  };

  /* ── Galerie ─────────────────────────── */
  var mainImg = $("[data-gallery-main]");
  $$(".gallery__thumbs button").forEach(function (btn) {
    btn.addEventListener("click", function () {
      $$(".gallery__thumbs button").forEach(function (b) {
        b.classList.remove("is-active");
      });
      btn.classList.add("is-active");
      if (mainImg) mainImg.src = btn.dataset.thumb;
    });
  });

  /* ── Sélecteurs couleur / taille ─────── */
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

  var state = { color: "Noir", size: "M" };
  var colorLabel = $("[data-color-label]");

  group(".swatch", function (el) {
    state.color = el.dataset.color;
    if (colorLabel) colorLabel.textContent = state.color;
  });
  group(".size", function (el) {
    state.size = el.dataset.size;
  });

  /* ── Panier (démo) ───────────────────── */
  var count = 0;
  var addBtn = $("[data-add-to-cart]");
  var counter = $("[data-cart-count]");
  var added = $("[data-added]");
  var addedLabel = $("[data-added-label]");

  if (addBtn) {
    addBtn.addEventListener("click", function () {
      count += 1;
      if (counter) counter.textContent = String(count);
      if (added && addedLabel) {
        addedLabel.textContent =
          "Harnais Anti-Fugue — " + state.color + ", taille " + state.size;
        added.hidden = false;
      }
    });
  }

  /* ── Guide des tailles ───────────────── */
  var guide = $("[data-guide]");
  var openGuide = $("[data-open-guide]");
  var closeGuide = $("[data-close-guide]");

  if (guide && openGuide) {
    openGuide.addEventListener("click", function () {
      if (typeof guide.showModal === "function") guide.showModal();
      else guide.setAttribute("open", "");
    });
  }
  if (guide && closeGuide) {
    closeGuide.addEventListener("click", function () {
      if (typeof guide.close === "function") guide.close();
      else guide.removeAttribute("open");
    });
  }
  if (guide) {
    guide.addEventListener("click", function (e) {
      if (e.target === guide) guide.close();
    });
  }

  /* ── Accordéon : une seule réponse ouverte ── */
  var items = $$(".accordion details");
  items.forEach(function (d) {
    d.addEventListener("toggle", function () {
      if (!d.open) return;
      items.forEach(function (other) {
        if (other !== d) other.open = false;
      });
    });
  });

  /* ── Newsletter (démo) ───────────────── */
  var form = $("[data-newsletter]");
  if (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var input = $("input", form);
      form.innerHTML =
        '<p style="margin:0;font-size:.9rem;color:var(--vert-700)">' +
        "Merci ! Un e-mail de confirmation part vers " +
        (input ? input.value : "votre adresse") +
        ".</p>";
    });
  }
})();
