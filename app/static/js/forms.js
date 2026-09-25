(function () {
  function textFor(field) {
    const state = field.validity;
    if (state.valueMissing) return "This field is required.";
    if (state.typeMismatch && field.type === "email") return "Enter a real email address.";
    if (state.typeMismatch) return "Enter a link that starts with http:// or https://.";
    if (state.tooShort) return "Use at least " + field.minLength + " characters.";
    if (state.tooLong) return "Use at most " + field.maxLength + " characters.";
    if (state.patternMismatch) return field.title || "Use letters, numbers, spaces, and & ' . / -.";
    if (state.rangeUnderflow || state.rangeOverflow) return "That value is out of range.";
    return "Check this field.";
  }

  function clear(form) {
    form.querySelectorAll(".field-error.js").forEach(function (node) {
      node.remove();
    });
    form.querySelectorAll(".is-invalid").forEach(function (node) {
      node.classList.remove("is-invalid");
      node.removeAttribute("aria-invalid");
    });
  }

  function show(field) {
    const note = document.createElement("small");
    note.className = "field-error js";
    note.setAttribute("role", "alert");
    note.textContent = textFor(field);
    field.insertAdjacentElement("afterend", note);
    field.classList.add("is-invalid");
    field.setAttribute("aria-invalid", "true");
  }

  function mediaKind(value) {
    if (value === "video" || value === "trailer" || value === "explainer") return "video";
    if (value === "audio") return "audio";
    if (value === "image") return "image";
    return "";
  }

  function syncMedia(form) {
    const picker = form.querySelector('[name="content_type"]');
    if (!picker || !form.querySelector("[data-media]")) return;
    const kind = mediaKind(picker.value);
    form.querySelectorAll("[data-media]").forEach(function (slot) {
      const show = slot.getAttribute("data-media") === kind;
      slot.hidden = !show;
      slot.querySelectorAll("input, textarea, select").forEach(function (field) {
        field.disabled = !show;
      });
    });
  }

  function fitHeader() {
    var bar = document.querySelector(".header-bar");
    var fit = bar && bar.querySelector(".header-fit");
    if (!fit) return;
    fit.style.transform = "none";
    bar.style.height = "";
    var available = bar.clientWidth;
    var needed = fit.scrollWidth;
    if (!available || !needed) return;
    var scale = needed > available + 1 ? available / needed : 1;
    if (scale < 1) {
      var height = fit.offsetHeight;
      fit.style.transform = "scale(" + scale + ")";
      bar.style.height = Math.ceil(height * scale) + "px";
    }
  }

  fitHeader();
  window.addEventListener("resize", fitHeader);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(fitHeader);

  function rememberPlace() {
    try {
      sessionStorage.setItem("fanhub-scroll", JSON.stringify({ path: location.pathname, y: window.scrollY }));
    } catch (err) {}
  }

  document.querySelectorAll("form.filters, form.bookmark-bar, form.case-bar").forEach(function (form) {
    form.addEventListener("submit", rememberPlace);
  });

  document.querySelectorAll(".chip-row a, .news-filters a").forEach(function (link) {
    link.addEventListener("click", function () {
      var next = new URL(link.href, location.href);
      if (next.pathname === location.pathname) rememberPlace();
    });
  });

  document.querySelectorAll("form").forEach(function (form) {
    syncMedia(form);
    const picker = form.querySelector('[name="content_type"]');
    if (picker) picker.addEventListener("change", function () { syncMedia(form); });
  });

  document.querySelectorAll("form").forEach(function (form) {
    if (form.classList.contains("support-form")) return;
    form.noValidate = true;
    form.addEventListener("submit", function (event) {
      clear(form);
      const fields = Array.prototype.filter.call(form.elements, function (field) {
        return field.willValidate && !field.disabled && !field.checkValidity();
      });
      if (!fields.length) return;
      event.preventDefault();
      fields.forEach(show);
      const drawer = form.closest("details");
      if (drawer) drawer.open = true;
      fields[0].focus();
    });
    form.addEventListener("input", function (event) {
      const field = event.target;
      const next = field.nextElementSibling;
      if (next && next.classList.contains("field-error") && next.classList.contains("js")) next.remove();
      field.classList.remove("is-invalid");
      field.removeAttribute("aria-invalid");
    });
  });
})();
