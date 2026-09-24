(function () {
  const root = document.querySelector("[data-reel]");
  if (!root) return;

  const slides = Array.from(root.querySelectorAll(".reel-slide"));
  const title = root.querySelector(".reel-title");
  const meta = root.querySelector(".reel-meta");
  const bar = root.querySelector(".reel-bar span");
  if (slides.length < 2) return;

  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  let index = 0;
  let timer = 0;
  const hold = 3400;

  function show(next) {
    slides[index].classList.remove("is-on");
    index = next;
    slides[index].classList.add("is-on");
    title.textContent = slides[index].dataset.title || "";
    meta.textContent = slides[index].dataset.meta || "";
    if (bar) {
      bar.style.animation = "none";
      void bar.offsetWidth;
      bar.style.animation = "";
    }
  }

  function start() {
    if (reduce) return;
    window.clearInterval(timer);
    timer = window.setInterval(function () {
      show((index + 1) % slides.length);
    }, hold);
  }

  root.addEventListener("mouseenter", function () {
    window.clearInterval(timer);
  });
  root.addEventListener("mouseleave", start);
  start();
})();
