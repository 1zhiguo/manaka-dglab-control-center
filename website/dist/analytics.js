(() => {
  const measurementId = "G-MKGQEE5V97";

  window.dataLayer = window.dataLayer || [];
  window.gtag = window.gtag || function gtag() {
    window.dataLayer.push(arguments);
  };

  window.gtag("js", new Date());
  window.gtag("config", measurementId, {
    send_page_view: false,
    allow_google_signals: false,
    allow_ad_personalization_signals: false,
  });

  const track = (name, parameters = {}) => {
    try {
      window.gtag("event", name, {
        transport_type: "beacon",
        ...parameters,
      });
    } catch (_error) {
      // Analytics must never interrupt navigation or a download.
    }
  };

  const pageName = document.body.classList.contains("docs-body") ? "guide" : "home";
  track("page_view", {
    page_title: document.title,
    page_location: window.location.href,
    page_path: `${window.location.pathname}${window.location.search}`,
    page_name: pageName,
  });

  document.addEventListener("click", (event) => {
    const link = event.target.closest("a[href]");
    if (!link) return;

    const channel = link.dataset.download;
    if (channel === "baidu" || channel === "cos" || channel === "github") {
      const release = window.MANAKA_DOWNLOADS || {};
      const eventNames = {
        baidu: "download_baidu",
        cos: "download_cos",
        github: "download_github",
      };
      track(eventNames[channel], {
        download_channel: channel,
        file_name: release.fileName || "unknown",
        file_version: release.version || "unknown",
        link_url: link.href,
        source_page: pageName,
      });
      return;
    }

    let destination;
    try {
      destination = new URL(link.href, window.location.href);
    } catch (_error) {
      return;
    }

    if (destination.origin === window.location.origin && /\/guide(?:\.html)?$/.test(destination.pathname)) {
      track("open_guide", {
        link_url: destination.href,
        source_page: pageName,
      });
      return;
    }

    if (destination.hostname === "x.com" && destination.pathname.replace(/\/$/, "") === "/1zhiguo") {
      track("open_x_profile", {
        link_url: destination.href,
        source_page: pageName,
      });
    }
  });

  window.ManakaAnalytics = Object.freeze({ track });
})();
