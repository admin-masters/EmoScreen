document.addEventListener("DOMContentLoaded", function () {
  const header = document.querySelector("[data-site-header]");
  const toggle = document.querySelector("[data-nav-toggle]");

  function syncHeaderState() {
    if (!header) return;
    header.classList.toggle("is-scrolled", window.scrollY > 6);
  }

  if (toggle && header) {
    toggle.addEventListener("click", function () {
      const isOpen = header.classList.toggle("is-open");
      toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
    });
  }

  window.addEventListener("scroll", syncHeaderState, { passive: true });
  syncHeaderState();

  document.querySelectorAll("[data-copy-text]").forEach(function (button) {
    button.addEventListener("click", async function () {
      const text = button.getAttribute("data-copy-text") || "";
      if (!text) return;
      try {
        await navigator.clipboard.writeText(text);
        const original = button.textContent;
        button.textContent = "Copied";
        window.setTimeout(function () {
          button.textContent = original;
        }, 1400);
      } catch (err) {
        console.warn("Clipboard write failed", err);
      }
    });
  });
});
