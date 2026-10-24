(() => {
  const config = window.MANAKA_DOWNLOADS || {};
  const versionParts = value => String(value || "").replace(/^v/, "").split(".").map(part => Number.parseInt(part, 10) || 0);
  const versionAtLeast = (actual, required) => {
    const a = versionParts(actual), b = versionParts(required);
    for (let i = 0; i < 3; i++) {
      if ((a[i] || 0) !== (b[i] || 0)) return (a[i] || 0) > (b[i] || 0);
    }
    return true;
  };
  document.querySelectorAll("[data-release-pending]").forEach(node => {
    node.hidden = versionAtLeast(config.version, node.dataset.releasePending);
  });
  document.querySelectorAll("[data-channel-pending]").forEach(node => {
    node.hidden = Boolean(config[node.dataset.channelPending + "Url"]);
  });
  const links = document.querySelectorAll("[data-download]");
  for (const link of links) {
    const channel = link.dataset.download;
    const urls = {
      baidu: config.baiduUrl,
      cos: config.cosUrl,
      github: config.githubUrl,
    };
    const url = urls[channel];
    if (url) {
      link.href = url;
      link.removeAttribute("aria-disabled");
      link.classList.remove("is-disabled");
    } else {
      link.href = "#downloads";
      link.setAttribute("aria-disabled", "true");
      link.classList.add("is-disabled");
      link.addEventListener("click", (event) => event.preventDefault());
    }
  }
  for (const menu of document.querySelectorAll("[data-download-menu]")) {
    const trigger = menu.querySelector(".download-trigger");
    const panel = menu.querySelector(".download-source-menu");
    const items = [...menu.querySelectorAll('[role="menuitem"]')];
    const setOpen = (open) => {
      menu.classList.toggle("is-open", open);
      trigger.setAttribute("aria-expanded", String(open));
      panel.setAttribute("aria-hidden", String(!open));
    };
    trigger.addEventListener("click", (event) => {
      event.stopPropagation();
      setOpen(!menu.classList.contains("is-open"));
    });
    menu.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        setOpen(false);
        trigger.focus();
      }
      if (event.key === "ArrowDown" && !menu.classList.contains("is-open")) {
        event.preventDefault();
        setOpen(true);
        const firstAvailable = items.find((item) => item.getAttribute("aria-disabled") !== "true");
        if (firstAvailable) firstAvailable.focus();
      }
    });
    items.forEach((item) => item.addEventListener("click", () => setOpen(false)));
    menu.addEventListener("click", (event) => event.stopPropagation());
    document.addEventListener("click", () => setOpen(false));
  }
  document.querySelectorAll("[data-version]").forEach((node) => {
    node.textContent = config.version || window.ManakaI18n?.t("download.current") || "当前版本";
  });
  document.querySelectorAll("[data-sha256]").forEach((node) => {
    node.textContent = config.sha256 || window.ManakaI18n?.t("download.pending") || "发布时提供";
  });
  document.querySelectorAll("[data-baidu-code]").forEach((node) => {
    node.textContent = config.baiduCode || "—";
  });
})();
