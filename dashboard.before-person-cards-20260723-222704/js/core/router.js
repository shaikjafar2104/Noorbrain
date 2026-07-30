(() => {
  "use strict";

  const pages = new Map();
  let currentPage = null;

  function register(
    name,
    {
      title = name,
      subtitle = "",
      onOpen = null,
      onClose = null
    } = {}
  ) {
    pages.set(
      name,
      {
        title,
        subtitle,
        onOpen,
        onClose
      }
    );
  }

  function exists(name) {
    return pages.has(name);
  }

  function show(name) {
    const target = document.getElementById(
      `page-${name}`
    );

    const config = pages.get(name);

    /*
     * Dynamic extension scripts such as Activity or
     * Reminder Rules may manage their own page opening.
     * Unknown pages are therefore ignored safely.
     */
    if (!target || !config) {
      return false;
    }

    if (
      currentPage &&
      currentPage !== name
    ) {
      const previous = pages.get(currentPage);

      if (
        previous &&
        typeof previous.onClose === "function"
      ) {
        previous.onClose();
      }
    }

    document
      .querySelectorAll(".page")
      .forEach(page => {
        page.classList.remove("active");
      });

    document
      .querySelectorAll(".nav-item")
      .forEach(item => {
        item.classList.toggle(
          "active",
          item.dataset.page === name
        );
      });

    target.classList.add("active");

    const title =
      document.getElementById("pageTitle");

    const subtitle =
      document.getElementById("pageSubtitle");

    if (title) {
      title.textContent = config.title;
    }

    if (subtitle) {
      subtitle.textContent = config.subtitle;
    }

    currentPage = name;

    if (typeof config.onOpen === "function") {
      config.onOpen();
    }

    window.dispatchEvent(
      new CustomEvent(
        "noor:page-opened",
        {
          detail: {
            page: name
          }
        }
      )
    );

    return true;
  }

  function initialize(defaultPage = "dashboard") {
    document.addEventListener(
      "click",
      event => {
        const navigation =
          event.target.closest("[data-page]");

        if (
          navigation &&
          navigation.dataset.page
        ) {
          show(navigation.dataset.page);
          return;
        }

        const jump =
          event.target.closest(
            "[data-page-jump]"
          );

        if (
          jump &&
          jump.dataset.pageJump
        ) {
          show(jump.dataset.pageJump);
        }
      }
    );

    show(defaultPage);
  }

  function current() {
    return currentPage;
  }

  window.NoorRouter = {
    register,
    exists,
    show,
    initialize,
    current
  };
})();
