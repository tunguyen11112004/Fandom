import * as THREE from "https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.js";

const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const canvas = document.getElementById("fx-field");
const spark = getComputedStyle(document.body).getPropertyValue("--spark").trim() || "#ff8a3d";

const wind = document.getElementById("wind");
if (!reduce && wind) {
  let lastY = window.scrollY;
  let target = 0;
  let shown = 0;
  const tick = () => {
    if (wind.duration && !wind.seeking) {
      target += 0.006;
      shown += (target - shown) * 0.08;
      const span = wind.duration;
      wind.currentTime = ((shown % span) + span) % span;
    }
    requestAnimationFrame(tick);
  };
  const arm = () => {
    wind.pause();
    if (!wind.duration) return;
    shown = wind.currentTime;
    target = shown;
    tick();
  };
  if (wind.readyState >= 1) arm();
  else wind.addEventListener("loadedmetadata", arm, { once: true });
  window.addEventListener("scroll", () => {
    const y = window.scrollY;
    const delta = y - lastY;
    lastY = y;
    target += Math.max(-0.35, Math.min(0.35, delta * 0.012));
  }, { passive: true });
}

if (!reduce && window.gsap) {
  document.documentElement.classList.add("gsap-on");
  const { gsap } = window;
  if (window.ScrollTrigger) gsap.registerPlugin(window.ScrollTrigger);

  gsap.from(".site-nav a, .mark", {
    y: -18,
    opacity: 0,
    duration: 0.55,
    stagger: 0.05,
    ease: "power2.out",
  });

  const heroBits = document.querySelectorAll(".hero-copy > *");
  if (heroBits.length) {
    gsap.from(heroBits, {
      y: 28,
      opacity: 0,
      duration: 0.75,
      stagger: 0.08,
      delay: 0.12,
      ease: "power3.out",
    });
  }

  const reveal = ".content-card, .hot-card, .category-card, .news-item, .path-card, .flagship-card, .color-tile";
  gsap.set(reveal, { opacity: 0, y: 36 });
  if (window.ScrollTrigger) {
    window.ScrollTrigger.batch(reveal, {
      start: "top 92%",
      once: true,
      onEnter: (batch) => {
        gsap.to(batch, {
          opacity: 1,
          y: 0,
          duration: 0.7,
          stagger: 0.07,
          ease: "power3.out",
          overwrite: true,
        });
      },
    });
    gsap.utils.toArray(".section-head, .page-head, .filters").forEach((el) => {
      gsap.from(el, {
        scrollTrigger: { trigger: el, start: "top 90%", once: true },
        y: 22,
        opacity: 0,
        duration: 0.6,
        ease: "power2.out",
      });
    });
  } else {
    gsap.to(reveal, { opacity: 1, y: 0, duration: 0.7, stagger: 0.05, ease: "power3.out" });
  }

  document.querySelectorAll(".content-card, .hot-card, .category-card, .flagship-card, .path-card").forEach((card) => {
    const img = card.querySelector("img");
    card.addEventListener("pointermove", (event) => {
      const box = card.getBoundingClientRect();
      const x = (event.clientX - box.left) / box.width - 0.5;
      const y = (event.clientY - box.top) / box.height - 0.5;
      gsap.to(card, {
        rotateY: x * 7,
        rotateX: y * -6,
        y: -8,
        duration: 0.35,
        ease: "power2.out",
        transformPerspective: 800,
        overwrite: "auto",
      });
      if (img) gsap.to(img, { scale: 1.08, x: x * -14, y: y * -8, duration: 0.45, overwrite: "auto" });
    });
    card.addEventListener("pointerleave", () => {
      gsap.to(card, { rotateX: 0, rotateY: 0, y: 0, duration: 0.5, ease: "power3.out", overwrite: "auto" });
      if (img) gsap.to(img, { scale: 1, x: 0, y: 0, duration: 0.5, overwrite: "auto" });
    });
  });

  gsap.set(".map-pin", { xPercent: -50, yPercent: -50 });

  if (window.ScrollTrigger) {
    gsap.from(".footer-col", {
      scrollTrigger: { trigger: ".site-footer", start: "top 88%", once: true },
      y: 40,
      opacity: 0,
      stagger: 0.08,
      duration: 0.75,
      ease: "power3.out",
    });
    gsap.from(".map-pin", {
      scrollTrigger: { trigger: ".hub-map", start: "top 90%", once: true },
      scale: 0,
      opacity: 0,
      stagger: 0.07,
      duration: 0.55,
      ease: "back.out(1.8)",
    });
    gsap.from(".footer-calendar li, .event-list li", {
      scrollTrigger: { trigger: ".footer-calendar, .event-list", start: "top 92%", once: true },
      x: -16,
      opacity: 0,
      stagger: 0.06,
      duration: 0.5,
      ease: "power2.out",
    });
    const tiltMap = gsap.quickTo(".hub-map", "rotation", { duration: 0.7, ease: "power3" });
    window.ScrollTrigger.create({
      onUpdate(self) {
        tiltMap(gsap.utils.clamp(-1.6, 1.6, self.getVelocity() / 900));
      },
    });
  }

  gsap.to(".map-pin-dot", {
    scale: 1.4,
    duration: 1.1,
    repeat: -1,
    yoyo: true,
    ease: "sine.inOut",
    stagger: 0.14,
  });

  document.querySelectorAll(".footer-col a, .site-nav a").forEach((link) => {
    link.addEventListener("pointerenter", () => {
      gsap.to(link, { y: -3, duration: 0.25, ease: "power2.out" });
    });
    link.addEventListener("pointerleave", () => {
      gsap.to(link, { y: 0, duration: 0.35, ease: "power3.out" });
    });
  });

  const sparkDot = document.querySelector(".cursor-spark");
  if (sparkDot && window.matchMedia("(pointer: fine)").matches) {
    const xTo = gsap.quickTo(sparkDot, "x", { duration: 0.4, ease: "power3" });
    const yTo = gsap.quickTo(sparkDot, "y", { duration: 0.4, ease: "power3" });
    window.addEventListener("pointermove", (event) => {
      xTo(event.clientX);
      yTo(event.clientY);
      gsap.to(sparkDot, { opacity: 0.85, duration: 0.2 });
    });
  }

  window.addEventListener("load", () => {
    if (window.ScrollTrigger) window.ScrollTrigger.refresh();
  });
}

if (!reduce && canvas && window.gsap) {

  const renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: false });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
  renderer.setSize(window.innerWidth, window.innerHeight);
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 40);
  camera.position.z = 8;

  const count = 280;
  const positions = new Float32Array(count * 3);
  for (let i = 0; i < count; i += 1) {
    positions[i * 3] = (Math.random() - 0.5) * 18;
    positions[i * 3 + 1] = (Math.random() - 0.5) * 12;
    positions[i * 3 + 2] = (Math.random() - 0.5) * 8;
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  const material = new THREE.PointsMaterial({
    color: new THREE.Color(spark),
    size: 0.06,
    transparent: true,
    opacity: 0.85,
  });
  const points = new THREE.Points(geometry, material);
  scene.add(points);

  window.addEventListener("resize", () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  });

  function frame() {
    points.rotation.y += 0.0008;
    points.position.y += 0.002;
    if (points.position.y > 1.2) points.position.y = -1.2;
    renderer.render(scene, camera);
    requestAnimationFrame(frame);
  }
  frame();
}
