document.addEventListener("DOMContentLoaded", function () {
  const toggle = document.getElementById("menuToggle");
  const nav = document.getElementById("mainNav");
  if (toggle && nav) {
    toggle.addEventListener("click", function () {
      nav.classList.toggle("open");
    });
  }

  // auto-dismiss flash messages after a few seconds
  document.querySelectorAll(".flash").forEach(function (el) {
    setTimeout(function () {
      el.style.transition = "opacity 0.4s";
      el.style.opacity = "0";
      setTimeout(function () { el.remove(); }, 400);
    }, 3500);
  });

  // product photo slideshow
  document.querySelectorAll(".slideshow").forEach(function (slideshow) {
    const count = parseInt(slideshow.dataset.count, 10) || 1;
    if (count <= 1) return;

    const track = slideshow.querySelector(".slideshow-track");
    const dots = slideshow.querySelectorAll(".slide-dot");
    const prevBtn = slideshow.querySelector(".slide-prev");
    const nextBtn = slideshow.querySelector(".slide-next");
    let index = 0;

    function goTo(i) {
      index = (i + count) % count;
      track.style.transform = "translateX(-" + (index * 100) + "%)";
      dots.forEach(function (dot, d) {
        dot.classList.toggle("active", d === index);
      });
    }

    if (prevBtn) prevBtn.addEventListener("click", function () { goTo(index - 1); });
    if (nextBtn) nextBtn.addEventListener("click", function () { goTo(index + 1); });
    dots.forEach(function (dot, d) {
      dot.addEventListener("click", function () { goTo(d); });
    });
  });
});
