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

  function chosenType(form) {
    const checked = form.querySelector('[name="content_type"]:checked');
    if (checked) return checked.value;
    const picker = form.querySelector('[name="content_type"]');
    return picker ? picker.value : "";
  }

  function syncMedia(form) {
    if (!form.querySelector("[data-media]")) return;
    const kind = mediaKind(chosenType(form));
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

  function hideToast(note) {
    window.setTimeout(function () {
      note.classList.add("toast-out");
      window.setTimeout(function () { note.remove(); }, 280);
    }, 3000);
  }

  document.querySelectorAll(".toast").forEach(hideToast);

  const copyLink = document.querySelector("#copy-link");
  if (copyLink) {
    copyLink.addEventListener("click", function () {
      navigator.clipboard.writeText(location.href).then(function () {
        let stack = document.querySelector(".toast-stack");
        if (!stack) {
          stack = document.createElement("div");
          stack.className = "toast-stack";
          stack.setAttribute("aria-live", "polite");
          document.body.appendChild(stack);
        }
        const note = document.createElement("p");
        note.className = "toast";
        note.setAttribute("role", "status");
        note.textContent = "Link copied.";
        stack.appendChild(note);
        hideToast(note);
      });
    });
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

  document.querySelectorAll("[data-otp]").forEach(function (row) {
    const boxes = Array.prototype.slice.call(row.querySelectorAll("input"));
    const form = row.closest("form");
    const hidden = form && form.querySelector('[name="code"]');
    if (!hidden) return;
    function write() {
      hidden.value = boxes.map(function (box) { return box.value; }).join("");
    }
    boxes.forEach(function (box, index) {
      box.addEventListener("input", function () {
        const digits = box.value.replace(/\D/g, "");
        if (digits.length > 1) {
          digits.slice(0, boxes.length - index).split("").forEach(function (digit, offset) {
            if (boxes[index + offset]) boxes[index + offset].value = digit;
          });
          const next = boxes[Math.min(index + digits.length, boxes.length - 1)];
          if (next) next.focus();
        } else {
          box.value = digits;
          if (digits && boxes[index + 1]) boxes[index + 1].focus();
        }
        write();
      });
      box.addEventListener("keydown", function (event) {
        if (event.key === "Backspace" && !box.value && boxes[index - 1]) boxes[index - 1].focus();
      });
      box.addEventListener("paste", function (event) {
        const text = (event.clipboardData.getData("text") || "").replace(/\D/g, "").slice(0, boxes.length);
        if (!text) return;
        event.preventDefault();
        boxes.forEach(function (item, itemIndex) { item.value = text[itemIndex] || ""; });
        boxes[Math.min(text.length, boxes.length) - 1].focus();
        write();
      });
    });
    form.addEventListener("submit", function (event) {
      write();
      if (/^\d{6}$/.test(hidden.value)) return;
      event.preventDefault();
      event.stopPropagation();
    }, true);
    const empty = boxes.filter(function (box) { return !box.value; })[0];
    if (empty) empty.focus();
  });

  function categoryValue(form) {
    const radio = form.querySelector('[name="category_id"]:checked');
    if (radio) return radio.value;
    const select = form.querySelector('select[name="category_id"]');
    return select ? select.value : "";
  }

  function filterFandoms(form) {
    const fandoms = form.querySelector("[data-fandoms]");
    if (!fandoms) return;
    const id = categoryValue(form);
    Array.prototype.forEach.call(fandoms.options, function (option) {
      if (!option.value) return;
      const show = !id || option.getAttribute("data-category") === id;
      option.hidden = !show;
      option.disabled = !show;
      if (!show && option.selected) fandoms.value = "";
    });
  }

  document.querySelectorAll("form").forEach(function (form) {
    syncMedia(form);
    filterFandoms(form);
    form.addEventListener("change", function (event) {
      if (!event.target) return;
      if (event.target.name === "content_type") syncMedia(form);
      if (event.target.name === "category_id") filterFandoms(form);
    });
  });

  function mountEditor(area) {
    if (!window.ClassicEditor || area.dataset.editorReady || area.closest("[data-compose]")) return;
    area.dataset.editorReady = "yes";
    ClassicEditor.create(area, {
      toolbar: ["heading", "|", "bold", "italic", "link", "bulletedList", "numberedList", "blockQuote", "|", "undo", "redo"],
      placeholder: area.getAttribute("placeholder") || "Write the text here."
    }).then(function (editor) {
      const form = area.closest("form");
      editor.model.document.on("change:data", function () { editor.updateSourceElement(); });
      if (form) form.addEventListener("submit", function () { editor.updateSourceElement(); }, true);
    }).catch(function () { area.dataset.editorReady = ""; });
  }

  document.querySelectorAll("textarea[data-rich]").forEach(function (area) {
    const drawer = area.closest("details");
    if (!drawer || drawer.open) mountEditor(area);
    if (drawer) drawer.addEventListener("toggle", function () {
      if (drawer.open) mountEditor(area);
    });
  });

  document.querySelectorAll("[data-compose]").forEach(function (form) {
    const title = form.querySelector("#title");
    const body = form.querySelector("#body");
    const counter = form.querySelector("[data-count]");
    const previewTitle = document.querySelector("[data-preview-title]");
    const previewBody = document.querySelector("[data-preview-body]");
    const previewCategory = document.querySelector("[data-preview-category]");
    function plain(value) {
      const node = document.createElement("div");
      node.innerHTML = value || "";
      return (node.textContent || "").replace(/\s+/g, " ").trim();
    }

    function paint() {
      if (title && counter) counter.textContent = title.value.length + "/" + (title.maxLength || 200);
      if (previewTitle) previewTitle.textContent = title && title.value.trim() ? title.value.trim() : "The title shows here";
      if (previewBody) {
        const summary = form.querySelector("#summary");
        const text = (summary && summary.value.trim()) || plain(body && body.value) || "A short excerpt shows here.";
        previewBody.textContent = text.length > 160 ? text.slice(0, 160) + "…" : text;
      }
      const category = form.querySelector('[name="category_id"]:checked');
      if (previewCategory) previewCategory.textContent = category ? category.getAttribute("data-label") : "Category";
    }

    form.addEventListener("input", paint);
    form.addEventListener("change", paint);
    paint();

    if (body && window.ClassicEditor) {
      ClassicEditor.create(body, {
        toolbar: ["heading", "|", "bold", "italic", "link", "bulletedList", "numberedList", "blockQuote", "|", "undo", "redo"],
        placeholder: "Write the piece. Headings, lists, and links are saved with it."
      }).then(function (editor) {
        const note = document.createElement("p");
        note.className = "fan-error";
        note.hidden = true;
        note.textContent = "Write the piece before sending it.";
        body.insertAdjacentElement("afterend", note);
        editor.model.document.on("change:data", function () {
          editor.updateSourceElement();
          note.hidden = true;
          paint();
        });
        form.addEventListener("submit", function (event) {
          editor.updateSourceElement();
          if (plain(editor.getData())) {
            note.hidden = true;
            return;
          }
          event.preventDefault();
          event.stopPropagation();
          note.hidden = false;
          editor.editing.view.focus();
        }, true);
      }).catch(function () {});
    }
  });

  const csrf = document.querySelector('meta[name="csrf"]');
  if (csrf) {
    document.querySelectorAll("form").forEach(function (form) {
      const method = (form.getAttribute("method") || "get").toLowerCase();
      if (method !== "post" || form.querySelector('input[name="csrf"]')) return;
      const field = document.createElement("input");
      field.type = "hidden";
      field.name = "csrf";
      field.value = csrf.getAttribute("content") || "";
      form.appendChild(field);
    });
  }

  document.querySelectorAll("form").forEach(function (form) {
    if (form.classList.contains("support-form")) return;
    form.noValidate = true;
    form.addEventListener("submit", function (event) {
      if (form.dataset.sending === "1") {
        event.preventDefault();
        event.stopImmediatePropagation();
        return;
      }
      form.dataset.sending = "1";
      clear(form);
      const fields = Array.prototype.filter.call(form.elements, function (field) {
        return field.willValidate && !field.disabled && !field.checkValidity();
      });
      if (!fields.length) {
        const submitter = event.submitter;
        if (submitter && submitter.name && !form.querySelector('input[type="hidden"][name="' + submitter.name + '"]')) {
          const carried = document.createElement("input");
          carried.type = "hidden";
          carried.name = submitter.name;
          carried.value = submitter.value;
          form.appendChild(carried);
        }
        form.querySelectorAll("button[type='submit']").forEach(function (button) {
          button.disabled = true;
        });
        return;
      }
      form.dataset.sending = "";
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

  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  document.querySelectorAll("[data-range]").forEach(function (root) {
    const toggle = root.querySelector(".range-toggle");
    const pop = root.querySelector(".range-pop");
    const form = root.querySelector(".range-custom");
    const custom = root.querySelector("[data-custom]");
    const cals = root.querySelector("[data-cals]");
    const fromInput = form.querySelector('input[name="from"]');
    const toInput = form.querySelector('input[name="to"]');
    let cursor = new Date(fromInput.value + "T00:00:00");
    if (Number.isNaN(cursor.getTime())) cursor = new Date();

    function iso(day) {
      const month = String(day.getMonth() + 1).padStart(2, "0");
      const date = String(day.getDate()).padStart(2, "0");
      return day.getFullYear() + "-" + month + "-" + date;
    }

    function parse(value) {
      const day = new Date(value + "T00:00:00");
      return Number.isNaN(day.getTime()) ? null : day;
    }

    function draw() {
      const left = new Date(cursor.getFullYear(), cursor.getMonth(), 1);
      const right = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1);
      cals.innerHTML = "";
      cals.appendChild(monthGrid(left, true));
      cals.appendChild(monthGrid(right, false));
    }

    function monthGrid(first, isLeft) {
      const wrap = document.createElement("div");
      wrap.className = "range-month";
      const head = document.createElement("div");
      head.className = "range-month-head";
      if (isLeft) {
        const prev = document.createElement("button");
        prev.type = "button";
        prev.textContent = "‹";
        prev.addEventListener("click", function () {
          cursor = new Date(cursor.getFullYear(), cursor.getMonth() - 1, 1);
          draw();
        });
        head.appendChild(prev);
      }
      const title = document.createElement("strong");
      title.textContent = months[first.getMonth()] + " " + first.getFullYear();
      head.appendChild(title);
      if (!isLeft) {
        const next = document.createElement("button");
        next.type = "button";
        next.textContent = "›";
        next.addEventListener("click", function () {
          cursor = new Date(cursor.getFullYear(), cursor.getMonth() + 1, 1);
          draw();
        });
        head.appendChild(next);
      }
      wrap.appendChild(head);
      const grid = document.createElement("div");
      grid.className = "range-grid";
      ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"].forEach(function (name) {
        const cell = document.createElement("span");
        cell.textContent = name;
        grid.appendChild(cell);
      });
      const start = new Date(first);
      start.setDate(1 - first.getDay());
      const from = parse(fromInput.value);
      const to = parse(toInput.value);
      for (let i = 0; i < 42; i += 1) {
        const day = new Date(start);
        day.setDate(start.getDate() + i);
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = String(day.getDate());
        if (day.getMonth() !== first.getMonth()) button.classList.add("is-out");
        const stamp = iso(day);
        if (from && stamp === iso(from)) button.classList.add("is-start");
        if (to && stamp === iso(to)) button.classList.add("is-end");
        if (from && to && day >= from && day <= to) button.classList.add("is-in");
        button.addEventListener("click", function () {
          const picked = parse(stamp);
          const currentFrom = parse(fromInput.value);
          const currentTo = parse(toInput.value);
          if (!currentFrom || (currentFrom && currentTo)) {
            fromInput.value = stamp;
            toInput.value = "";
          } else if (picked < currentFrom) {
            toInput.value = fromInput.value;
            fromInput.value = stamp;
          } else {
            toInput.value = stamp;
          }
          draw();
        });
        grid.appendChild(button);
      }
      wrap.appendChild(grid);
      return wrap;
    }

    function setOpen(open) {
      pop.hidden = !open;
      toggle.setAttribute("aria-expanded", open ? "true" : "false");
      if (open && !form.hidden) draw();
    }

    toggle.addEventListener("click", function () {
      setOpen(pop.hidden);
    });
    custom.addEventListener("click", function () {
      form.hidden = false;
      draw();
    });
    document.addEventListener("click", function (event) {
      if (!root.contains(event.target)) setOpen(false);
    });
    if (!form.hidden) draw();
  });

  const titles = document.querySelectorAll(".watch-list strong");
  if (!titles.length) return;
  const tip = document.createElement("div");
  tip.className = "playlist-tip";
  tip.hidden = true;
  document.body.appendChild(tip);

  function placeTip(event) {
    const gap = 14;
    const edge = 8;
    tip.hidden = false;
    const box = tip.getBoundingClientRect();
    let x = event.clientX + gap;
    let y = event.clientY + gap;
    if (x + box.width > window.innerWidth - edge) x = event.clientX - box.width - gap;
    if (y + box.height > window.innerHeight - edge) y = event.clientY - box.height - gap;
    if (x < edge) x = edge;
    if (y < edge) y = edge;
    tip.style.left = x + "px";
    tip.style.top = y + "px";
  }

  titles.forEach(function (title) {
    title.addEventListener("mouseenter", function (event) {
      tip.textContent = title.textContent.trim();
      placeTip(event);
    });
    title.addEventListener("mousemove", placeTip);
    title.addEventListener("mouseleave", function () {
      tip.hidden = true;
    });
  });
})();
