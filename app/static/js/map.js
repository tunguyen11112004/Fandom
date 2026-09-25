(function () {
  let map = null;

  function mount() {
  const node = document.querySelector("#event-map");
  const dataNode = document.querySelector("#event-map-data");
  if (!node || !dataNode || typeof L === "undefined") return;
  if (map) {
    map.remove();
    map = null;
  }

  let payload = { pins: [], you: null };
  try {
    payload = JSON.parse(dataNode.textContent || "{}");
  } catch (err) {
    payload = { pins: [], you: null };
  }

  map = L.map(node, {
    scrollWheelZoom: false,
    zoomControl: true,
    worldCopyJump: true,
  }).setView([20, 10], 2);

  L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
    {
      attribution: 'Tiles &copy; <a href="https://www.esri.com/">Esri</a>',
      maxZoom: 16,
    }
  ).addTo(map);
  L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}",
    { maxZoom: 16, pane: "overlayPane" }
  ).addTo(map);

  if (!node.dataset.wheelBound) {
    node.dataset.wheelBound = "1";
    node.addEventListener("click", () => {
      if (map) map.scrollWheelZoom.enable();
    });
    node.addEventListener("mouseleave", () => {
      if (map) map.scrollWheelZoom.disable();
    });
  }

  const pins = Array.isArray(payload.pins) ? payload.pins : [];
  const markers = [];

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[ch]));
  }

  pins.forEach((pin) => {
    const marker = L.circleMarker([pin.lat, pin.lng], {
      radius: 8,
      color: "#1a1204",
      weight: 2,
      fillColor: "#f2c14e",
      fillOpacity: 1,
      className: "gps-dot",
    });
    const lines = (pin.events || [])
      .map(
        (event) =>
          `<p><a href="#${escapeHtml(event.id)}">${escapeHtml(event.title)}</a><br />${escapeHtml(event.kind)} · ${escapeHtml(event.when)}</p>`
      )
      .join("");
    marker.bindPopup(`<strong>${escapeHtml(pin.city)}</strong>${lines}`, { className: "gps-popup" });
    marker.bindTooltip(pin.city, {
      permanent: true,
      direction: "top",
      offset: [0, -10],
      className: "gps-label",
      opacity: 1,
    });
    marker.addTo(map);
    markers.push(marker);
  });

  if (payload.you && Number.isFinite(payload.you.lat) && Number.isFinite(payload.you.lng)) {
    const you = L.circleMarker([payload.you.lat, payload.you.lng], {
      radius: 7,
      color: "#d7e6ff",
      weight: 2,
      fillColor: "#6aa7ff",
      fillOpacity: 1,
    });
    you.bindTooltip("You", {
      permanent: true,
      direction: "bottom",
      offset: [0, 8],
      className: "gps-label you-label",
      opacity: 1,
    });
    you.addTo(map);
    markers.push(you);
  }

  if (markers.length) {
    const bounds = L.featureGroup(markers).getBounds();
    if (bounds.isValid()) {
      map.fitBounds(bounds.pad(0.35), { padding: [36, 36], maxZoom: 6 });
    }
  }

  const slots = [
    { direction: "top", offset: [0, -12] },
    { direction: "bottom", offset: [0, 12] },
    { direction: "right", offset: [14, 0] },
    { direction: "left", offset: [-14, 0] },
    { direction: "top", offset: [42, -20] },
    { direction: "top", offset: [-42, -20] },
    { direction: "bottom", offset: [42, 16] },
    { direction: "bottom", offset: [-42, 16] },
  ];

  function boxesOverlap(a, b) {
    return !(a.right < b.left || a.left > b.right || a.bottom < b.top || a.top > b.bottom);
  }

  function labelBox(point, slot, text) {
    const width = Math.max(72, String(text).length * 7.6 + 24);
    const height = 30;
    let left = point.x;
    let top = point.y;
    if (slot.direction === "top") {
      left = point.x - width / 2 + slot.offset[0];
      top = point.y - height + slot.offset[1];
    } else if (slot.direction === "bottom") {
      left = point.x - width / 2 + slot.offset[0];
      top = point.y + slot.offset[1];
    } else if (slot.direction === "left") {
      left = point.x - width + slot.offset[0];
      top = point.y - height / 2 + slot.offset[1];
    } else {
      left = point.x + slot.offset[0];
      top = point.y - height / 2 + slot.offset[1];
    }
    return { left: left - 8, right: left + width + 8, top: top - 4, bottom: top + height + 4 };
  }

  function placeLabels() {
    const placed = [];
    const ordered = markers.slice().sort((a, b) => a.getLatLng().lng - b.getLatLng().lng);
    ordered.forEach((marker, index) => {
      const tip = marker.getTooltip();
      if (!tip) return;
      const text = tip.getContent();
      const point = map.latLngToContainerPoint(marker.getLatLng());
      const order = index % 2 === 0 ? slots : [slots[1], slots[0]].concat(slots.slice(2));
      let chosen = order[0];
      let chosenBox = labelBox(point, chosen, text);
      for (const slot of order) {
        const box = labelBox(point, slot, text);
        if (!placed.some((other) => boxesOverlap(box, other))) {
          chosen = slot;
          chosenBox = box;
          break;
        }
      }
      placed.push(chosenBox);
      marker.unbindTooltip();
      marker.bindTooltip(text, {
        permanent: true,
        direction: chosen.direction,
        offset: chosen.offset,
        className: text === "You" ? "gps-label you-label" : "gps-label",
        opacity: 1,
      });
    });
  }

  map.once("moveend", () => {
    window.requestAnimationFrame(placeLabels);
  });
  window.setTimeout(placeLabels, 400);
  }

  window.fanhubMountMap = mount;
  mount();
  window.addEventListener("resize", () => {
    if (!map) return;
    map.invalidateSize();
  });
})();
