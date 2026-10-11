(() => {
  const content = document.querySelector("#docContent");
  const toc = document.querySelector("#docToc");
  const sourceLabel = document.querySelector("#docSource");
  const rawLink = document.querySelector("#rawDocLink");
  const errorBox = document.querySelector("#docError");
  const search = document.querySelector("#docSearch");
  const searchStatus = document.querySelector("#searchStatus");
  const tabs = [...document.querySelectorAll(".doc-tab")];

  const escapeHtml = (value) => value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
  const inline = (value) => {
    const code = [];
    let safe = escapeHtml(value).replace(/`([^`]+)`/g, (_, text) => {
      code.push(`<code>${text}</code>`);
      return `\u0000${code.length - 1}\u0000`;
    });
    safe = safe.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    safe = safe.replace(/\[([^\]]+)]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
    return safe.replace(/\u0000(\d+)\u0000/g, (_, index) => code[Number(index)]);
  };
  const usedSlugs = new Map();
  const slug = (text) => {
    const base = text.toLowerCase().replace(/[^\p{Letter}\p{Number}]+/gu, "-").replace(/^-|-$/g, "") || "section";
    const count = usedSlugs.get(base) || 0;
    usedSlugs.set(base, count + 1);
    return count ? `${base}-${count + 1}` : base;
  };

  function renderMarkdown(markdown) {
    usedSlugs.clear();
    const lines = markdown.replace(/\r\n?/g, "\n").split("\n");
    const html = [];
    let paragraph = [], listType = "", inCode = false, codeLines = [];
    const flushParagraph = () => { if (paragraph.length) html.push(`<p>${inline(paragraph.join(" "))}</p>`); paragraph = []; };
    const closeList = () => { if (listType) html.push(`</${listType}>`); listType = ""; };
    for (const rawLine of lines) {
      if (rawLine.startsWith("```")) {
        flushParagraph(); closeList();
        if (inCode) { html.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`); codeLines = []; }
        inCode = !inCode; continue;
      }
      if (inCode) { codeLines.push(rawLine); continue; }
      const heading = rawLine.match(/^(#{1,3})\s+(.+)$/);
      if (heading) {
        flushParagraph(); closeList();
        const level = heading[1].length, title = heading[2].replace(/\*\*/g, "");
        html.push(`<h${level} id="${slug(title)}">${inline(heading[2])}</h${level}>`); continue;
      }
      const unordered = rawLine.match(/^\s*[-*]\s+(.+)$/), ordered = rawLine.match(/^\s*\d+\.\s+(.+)$/);
      if (unordered || ordered) {
        flushParagraph();
        const wanted = unordered ? "ul" : "ol";
        if (listType !== wanted) { closeList(); listType = wanted; html.push(`<${wanted}>`); }
        html.push(`<li>${inline((unordered || ordered)[1])}</li>`); continue;
      }
      if (!rawLine.trim()) { flushParagraph(); closeList(); continue; }
      paragraph.push(rawLine.trim());
    }
    flushParagraph(); closeList();
    if (inCode) html.push(`<pre><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
    return html.join("\n");
  }

  function buildToc() {
    toc.replaceChildren();
    content.querySelectorAll("h2, h3").forEach((heading) => {
      const link = document.createElement("a");
      link.href = `#${heading.id}`; link.textContent = heading.textContent;
      if (heading.tagName === "H3") link.className = "toc-sub";
      toc.append(link);
    });
  }
  function runSearch() {
    content.querySelectorAll(".search-hit").forEach((node) => node.classList.remove("search-hit"));
    const query = search.value.trim().toLocaleLowerCase("zh-CN");
    if (!query) { searchStatus.textContent = ""; return; }
    const matches = [...content.querySelectorAll("h1,h2,h3,p,li,pre")].filter((node) => node.textContent.toLocaleLowerCase("zh-CN").includes(query));
    matches.forEach((node) => node.classList.add("search-hit"));
    searchStatus.textContent = matches.length ? `找到 ${matches.length} 处，已定位第一处` : "没有找到匹配内容";
    matches[0]?.scrollIntoView({ behavior: "smooth", block: "center" });
  }
  async function loadDocument(fileName) {
    content.innerHTML = '<p class="doc-loading">正在读取 Markdown 文档…</p>';
    errorBox.hidden = true; search.value = ""; searchStatus.textContent = "";
    sourceLabel.textContent = `读取 ${fileName}`; rawLink.href = fileName;
    try {
      const response = await fetch(fileName, { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      content.innerHTML = renderMarkdown(await response.text()); buildToc();
    } catch (error) {
      content.replaceChildren(); toc.replaceChildren(); errorBox.hidden = false; console.error(error);
    }
  }
  tabs.forEach((tab) => tab.addEventListener("click", () => {
    tabs.forEach((item) => item.classList.toggle("is-active", item === tab)); loadDocument(tab.dataset.doc);
  }));
  search.addEventListener("search", runSearch);
  search.addEventListener("keydown", (event) => { if (event.key === "Enter") runSearch(); });
  loadDocument("QUICKSTART_CN.md");
})();
