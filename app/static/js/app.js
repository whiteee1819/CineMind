/* ════════════════════════════════════════════════════════════════════
   CineMind front-end
   Vanilla ES2020, no build step. Structure:
     1. helpers      – DOM builder, API client, toasts
     2. state        – single source of truth
     3. components   – poster art, movie card, modal
     4. features     – discover, library, insights, dataset
     5. bootstrap
   Every piece of dataset text is inserted with textContent (never innerHTML)
   so uploaded files cannot inject markup.
   ════════════════════════════════════════════════════════════════════ */
(() => {
  "use strict";

  /* ───────────────────────── 1. helpers ───────────────────────── */

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

  /** Tiny hyperscript: h("div", {class: "x", onclick: fn}, child, "text"). */
  function h(tag, props = {}, ...children) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(props || {})) {
      if (value === null || value === undefined || value === false) continue;
      if (key === "class") node.className = value;
      else if (key === "text") node.textContent = value;
      else if (key === "style") Object.assign(node.style, value);
      else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
      else node.setAttribute(key, value === true ? "" : value);
    }
    for (const child of children.flat()) {
      if (child === null || child === undefined || child === false) continue;
      node.append(child.nodeType ? child : document.createTextNode(String(child)));
    }
    return node;
  }

  const clear = (node) => node.replaceChildren();
  const debounce = (fn, wait) => {
    let timer;
    return (...args) => { clearTimeout(timer); timer = setTimeout(() => fn(...args), wait); };
  };
  const fmt = (n) => Number(n).toLocaleString();

  /** Fetch wrapper: resolves JSON, rejects with a human-readable Error. */
  async function api(path, options = {}) {
    let response;
    try {
      response = await fetch(path, options);
    } catch {
      throw new Error("Cannot reach the server. Is it still running?");
    }
    let data = null;
    try { data = await response.json(); } catch { /* non-JSON body */ }
    if (!response.ok) throw new Error((data && data.error) || `Request failed (${response.status}).`);
    return data;
  }

  function toast(message, kind = "info") {
    const node = h("div", { class: `toast toast--${kind}`, text: message });
    $("#toasts").append(node);
    setTimeout(() => node.remove(), 4800);
  }

  /* ───────────────────────── 2. state ───────────────────────── */

  const state = {
    dataset: null,            // {meta, stats}
    datasetKey: null,         // identifies the active file (to reset profile on change)
    liked: new Map(),         // id -> movie
    genres: new Set(),
    library: { page: 1, q: "", genre: "", sort: "title", loaded: false },
    lastRequest: 0,
  };

  /* ───────────────────────── 3. components ───────────────────────── */

  // Rare-colour palette used to paint deterministic "poster" art per title.
  const POSTER_COLORS = ["#ff2e7e", "#ff7a3d", "#d4ff3a", "#2ee6c5", "#5b45ff", "#c84bff", "#ffc83d", "#1fa2ff"];

  function hash(text) {
    let value = 2166136261;
    for (let i = 0; i < text.length; i++) value = Math.imul(value ^ text.charCodeAt(i), 16777619);
    return value >>> 0;
  }

  function posterBackground(title) {
    const seed = hash(title);
    const first = POSTER_COLORS[seed % POSTER_COLORS.length];
    const second = POSTER_COLORS[(seed >> 5) % POSTER_COLORS.length];
    const other = second === first ? POSTER_COLORS[(seed % POSTER_COLORS.length + 3) % POSTER_COLORS.length] : second;
    return `linear-gradient(${(seed >> 9) % 360}deg, ${first}, ${other})`;
  }

  function initial(title) {
    const match = title.match(/[\p{L}\p{N}]/u);
    return match ? match[0].toUpperCase() : "★";
  }

  function poster(movie, withMatch) {
    const node = h("div", { class: "poster" },
      h("span", { class: "poster__letter", text: initial(movie.title) }),
      movie.year ? h("span", { class: "poster__year", text: movie.year }) : null,
    );
    node.style.setProperty("--poster", posterBackground(movie.title));
    if (withMatch && movie.match !== undefined) {
      const ring = h("div", { class: "match", title: "Match score" }, h("b", {}, movie.match, h("small", { text: "%" })));
      ring.style.setProperty("--p", movie.match);
      node.append(ring);
    }
    return node;
  }

  function genreTags(movie) {
    const shared = new Set(movie.shared_genres || []);
    const tags = movie.genres.slice(0, 4).map((genre) =>
      h("span", { class: `tag${shared.has(genre) ? " tag--hit" : ""}`, text: genre }));
    if (movie.genre_inferred) tags.push(h("span", { class: "tag tag--ai", title: "Genre inferred from the description", text: "✦ auto" }));
    return h("div", { class: "tags" }, tags);
  }

  function whyLine(movie) {
    const parts = [];
    if (movie.because) parts.push(h("span", {}, "Because you liked ", h("strong", { text: movie.because })));
    if (movie.shared_genres && movie.shared_genres.length) parts.push(h("span", {}, "shares ", h("strong", { text: movie.shared_genres.join(", ") })));
    if (movie.keywords && movie.keywords.length) {
      const words = movie.keywords.flatMap((word, i) => [i ? ", " : "", h("span", { class: "kw", text: word })]);
      parts.push(h("span", {}, "themes: ", words));
    }
    if (!parts.length) return h("div", { class: "card__why", text: "Matches your mood and filters." });
    return h("div", { class: "card__why" }, parts.flatMap((part, i) => [i ? " · " : "", part]));
  }

  function movieCard(movie, index, { compact = false, showWhy = false } = {}) {
    const card = h("button", {
      class: `card${compact ? " card--compact" : ""}`,
      type: "button",
      "aria-label": `${movie.title}${movie.year ? ` (${movie.year})` : ""} – view details`,
      onclick: () => openModal(movie),
    },
      poster(movie, showWhy),
      h("div", { class: "card__body" },
        h("div", { class: "card__title", text: movie.title }),
        genreTags(movie),
        showWhy ? whyLine(movie) : null,
      ),
    );
    card.style.setProperty("--i", Math.min(index, 14));
    return card;
  }

  /* Modal */
  const modal = $("#movieModal");

  function openModal(movie) {
    const body = $("#modalBody");
    clear(body);
    const liked = state.liked.has(movie.id);
    body.append(
      poster(movie, false),
      h("div", { class: "modal__content" },
        h("h3", { id: "modalTitle", text: movie.title }),
        h("div", { class: "modal__meta", text: [movie.year, movie.decade && `${movie.decade} cinema`].filter(Boolean).join(" · ") || "Year unknown" }),
        genreTags(movie),
        h("p", { text: movie.description || "No description available for this title." }),
        h("div", { class: "modal__actions" },
          h("button", { class: "cta", type: "button", onclick: () => { modal.close(); moreLikeThis(movie); } }, h("span", { text: "More like this" })),
          h("button", { class: "ghost-btn", type: "button", onclick: () => { modal.close(); addLiked(movie); showView("discover"); } },
            liked ? "✓ In your taste profile" : "＋ Add to my taste"),
        ),
      ),
    );
    modal.showModal();
  }

  $("#modalClose").addEventListener("click", () => modal.close());
  // Clicking the dimmed backdrop (the <dialog> itself) closes the dialog.
  modal.addEventListener("click", (event) => { if (event.target === modal) modal.close(); });

  /* ───────────────────────── 4a. navigation ───────────────────────── */

  const VIEWS = ["discover", "library", "insights", "dataset"];

  function showView(name) {
    if (!VIEWS.includes(name)) name = "discover";
    for (const view of VIEWS) {
      const active = view === name;
      const section = $(`#view-${view}`);
      section.hidden = !active;
      section.classList.toggle("is-active", active);
    }
    for (const tab of $$(".tab")) {
      const active = tab.dataset.view === name;
      tab.classList.toggle("is-active", active);
      tab.setAttribute("aria-selected", String(active));
    }
    if (location.hash !== `#${name}`) history.replaceState(null, "", `#${name}`);
    if (name === "library" && !state.library.loaded) loadLibrary();
    if (name === "insights") animateInsights();
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  for (const trigger of $$("[data-view]")) trigger.addEventListener("click", () => showView(trigger.dataset.view));
  window.addEventListener("hashchange", () => showView(location.hash.slice(1)));

  /* ───────────────────────── 4b. discover ───────────────────────── */

  const searchInput = $("#movieSearch");
  const suggestionList = $("#suggestions");
  let suggestionItems = [];
  let activeSuggestion = -1;
  let searchToken = 0;

  function closeSuggestions() {
    suggestionList.hidden = true;
    searchInput.setAttribute("aria-expanded", "false");
    activeSuggestion = -1;
  }

  function highlightSuggestion(index) {
    activeSuggestion = index;
    $$("li", suggestionList).forEach((li, i) => li.setAttribute("aria-selected", String(i === index)));
  }

  function renderSuggestions(movies) {
    clear(suggestionList);
    suggestionItems = movies.filter((movie) => !state.liked.has(movie.id));
    if (!suggestionItems.length) {
      suggestionList.append(h("li", { class: "is-empty", text: "No matching titles" }));
    }
    suggestionItems.forEach((movie, index) => {
      suggestionList.append(h("li", {
        role: "option",
        "aria-selected": "false",
        // mousedown fires before the input's blur, so the click is never lost.
        onmousedown: (event) => { event.preventDefault(); chooseSuggestion(index); },
      }, h("span", { text: movie.title }), h("small", { text: movie.year || "" })));
    });
    suggestionList.hidden = false;
    searchInput.setAttribute("aria-expanded", "true");
    highlightSuggestion(suggestionItems.length ? 0 : -1);
  }

  function chooseSuggestion(index) {
    const movie = suggestionItems[index];
    if (!movie) return;
    addLiked(movie);
    searchInput.value = "";
    closeSuggestions();
  }

  const runSearch = debounce(async () => {
    const query = searchInput.value.trim();
    if (!query) return closeSuggestions();
    const token = ++searchToken;
    try {
      const data = await api(`/api/movies/search?q=${encodeURIComponent(query)}&limit=8`);
      if (token === searchToken) renderSuggestions(data.results);   // ignore stale responses
    } catch (error) {
      toast(error.message, "error");
    }
  }, 180);

  searchInput.addEventListener("input", runSearch);
  searchInput.addEventListener("blur", closeSuggestions);
  searchInput.addEventListener("keydown", (event) => {
    if (suggestionList.hidden) return;
    const count = suggestionItems.length;
    if (event.key === "ArrowDown" && count) { event.preventDefault(); highlightSuggestion((activeSuggestion + 1) % count); }
    else if (event.key === "ArrowUp" && count) { event.preventDefault(); highlightSuggestion((activeSuggestion - 1 + count) % count); }
    else if (event.key === "Enter") { event.preventDefault(); chooseSuggestion(Math.max(activeSuggestion, 0)); }
    else if (event.key === "Escape") closeSuggestions();
  });

  function addLiked(movie) {
    if (state.liked.size >= 25) return toast("You can pick up to 25 favourites.", "error");
    state.liked.set(movie.id, movie);
    renderLiked();
  }

  function renderLiked() {
    const list = $("#likedChips");
    clear(list);
    for (const movie of state.liked.values()) {
      list.append(h("li", { class: "chip" },
        h("span", { text: movie.title }),
        h("button", { type: "button", "aria-label": `Remove ${movie.title}`, onclick: () => { state.liked.delete(movie.id); renderLiked(); }, text: "✕" }),
      ));
    }
  }

  function renderGenrePills() {
    const container = $("#genrePills");
    clear(container);
    const genres = state.dataset.stats.genres;
    for (const { name } of genres) {
      const pill = h("button", { class: "pill", type: "button", "aria-pressed": String(state.genres.has(name)), text: name });
      pill.addEventListener("click", () => {
        state.genres.has(name) ? state.genres.delete(name) : state.genres.add(name);
        pill.setAttribute("aria-pressed", String(state.genres.has(name)));
      });
      container.append(pill);
    }
  }

  function resetProfile() {
    state.liked.clear();
    state.genres.clear();
    $("#yearMin").value = $("#yearMax").value = $("#moodInput").value = "";
    renderLiked();
    renderGenrePills();
    clear($("#resultsGrid"));
    $("#resultsMeta").textContent = "";
    $("#resultsEmpty").hidden = false;
  }

  function showSkeletons() {
    const grid = $("#resultsGrid");
    clear(grid);
    for (let i = 0; i < 6; i++) grid.append(h("div", { class: "skeleton" }));
    $("#resultsEmpty").hidden = true;
  }

  async function recommend(overrides = null) {
    const yearMin = $("#yearMin").value.trim();
    const yearMax = $("#yearMax").value.trim();
    const payload = overrides || {
      liked: [...state.liked.keys()],
      genres: [...state.genres],
      mood: $("#moodInput").value.trim(),
      year_min: yearMin === "" ? null : Number(yearMin),
      year_max: yearMax === "" ? null : Number(yearMax),
      limit: 12,
    };
    if (!payload.liked.length && !payload.genres.length && !payload.mood) {
      return toast("Add a movie, pick a genre or describe a mood first.", "error");
    }

    const button = $("#recommendBtn");
    const requestId = ++state.lastRequest;
    button.disabled = true;
    showSkeletons();
    try {
      const data = await api("/api/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (requestId !== state.lastRequest) return;   // a newer request superseded this one
      renderResults(data);
    } catch (error) {
      if (requestId !== state.lastRequest) return;
      clear($("#resultsGrid"));
      $("#resultsEmpty").hidden = false;
      toast(error.message, "error");
    } finally {
      if (requestId === state.lastRequest) button.disabled = false;
    }
  }

  function renderResults({ results, meta }) {
    const grid = $("#resultsGrid");
    clear(grid);
    const empty = $("#resultsEmpty");
    if (!results.length) {
      empty.hidden = false;
      empty.querySelector("h3").textContent = "No titles match those filters";
      empty.querySelector("p").textContent = "Try widening the era, removing a genre or using different mood words.";
      $("#resultsMeta").textContent = "0 matches";
      return;
    }
    empty.hidden = true;
    const signals = { text: "plot similarity", genre: "genre affinity", year: "era" };
    $("#resultsMeta").textContent =
      `Top ${results.length} of ${fmt(meta.candidates)} candidates · ranked by ${meta.signals.map((s) => signals[s]).join(" + ")}`;
    results.forEach((movie, index) => grid.append(movieCard(movie, index, { showWhy: true })));
    if (window.matchMedia("(max-width: 1020px)").matches) grid.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function moreLikeThis(movie) {
    resetProfile();
    state.liked.set(movie.id, movie);
    renderLiked();
    showView("discover");
    recommend();
  }

  async function surprise() {
    const total = state.dataset.stats.total;
    try {
      const page = Math.floor(Math.random() * total) + 1;
      const data = await api(`/api/movies?per_page=1&page=${page}`);
      if (data.items[0]) addLiked(data.items[0]);
    } catch (error) {
      toast(error.message, "error");
    }
  }

  $("#recommendBtn").addEventListener("click", () => recommend());
  $("#clearBtn").addEventListener("click", resetProfile);
  $("#surpriseBtn").addEventListener("click", surprise);
  $("#moodInput").addEventListener("keydown", (event) => { if (event.key === "Enter") recommend(); });

  /* ───────────────────────── 4c. library ───────────────────────── */

  async function loadLibrary() {
    const lib = state.library;
    lib.loaded = true;
    const grid = $("#libGrid");
    const params = new URLSearchParams({ page: lib.page, per_page: 24, sort: lib.sort });
    if (lib.q) params.set("q", lib.q);
    if (lib.genre) params.set("genre", lib.genre);
    try {
      const data = await api(`/api/movies?${params}`);
      lib.page = data.page;
      clear(grid);
      data.items.forEach((movie, index) => grid.append(movieCard(movie, index, { compact: true })));
      $("#libMeta").textContent = data.total ? `${fmt(data.total)} title${data.total === 1 ? "" : "s"}` : "No titles found";
      renderPager(data);
    } catch (error) {
      toast(error.message, "error");
    }
  }

  function renderPager({ page, pages }) {
    const pager = $("#libPager");
    clear(pager);
    if (pages <= 1) return;
    const go = (target) => () => { state.library.page = target; loadLibrary(); window.scrollTo({ top: 0, behavior: "smooth" }); };
    pager.append(
      h("button", { type: "button", disabled: page <= 1, onclick: go(page - 1), text: "← Prev" }),
      h("span", { text: `Page ${page} / ${pages}` }),
      h("button", { type: "button", disabled: page >= pages, onclick: go(page + 1), text: "Next →" }),
    );
  }

  function renderLibraryFilters() {
    const select = $("#libGenre");
    const current = state.library.genre;
    clear(select);
    select.append(h("option", { value: "", text: "All genres" }));
    for (const { name, count } of state.dataset.stats.genres) {
      select.append(h("option", { value: name, text: `${name} (${count})`, selected: name === current }));
    }
  }

  $("#libQuery").addEventListener("input", debounce((event) => {
    Object.assign(state.library, { q: event.target.value.trim(), page: 1 });
    loadLibrary();
  }, 250));
  $("#libGenre").addEventListener("change", (event) => { Object.assign(state.library, { genre: event.target.value, page: 1 }); loadLibrary(); });
  $("#libSort").addEventListener("change", (event) => { Object.assign(state.library, { sort: event.target.value, page: 1 }); loadLibrary(); });

  /* ───────────────────────── 4d. insights ───────────────────────── */

  function renderInsights() {
    const stats = state.dataset.stats;
    const tiles = [
      [fmt(stats.total), "Movies"],
      [fmt(stats.genre_count), "Genres"],
      [stats.year_min ? `${stats.year_min}–${stats.year_max}` : "—", "Year span"],
      [stats.avg_genres_per_movie, "Genres per movie"],
      [`${Math.round((stats.with_description / stats.total) * 100)}%`, "With description"],
      [fmt(stats.genres_inferred), "Auto-categorised"],
    ];
    const tileBox = $("#insightTiles");
    clear(tileBox);
    for (const [value, label] of tiles) tileBox.append(h("div", { class: "tile" }, h("b", { text: value }), h("span", { text: label })));

    const maxGenre = Math.max(1, ...stats.genres.map((g) => g.count));
    const bars = $("#genreBars");
    clear(bars);
    for (const { name, count } of stats.genres) {
      const fill = h("span", { class: "bar__fill" });
      fill.dataset.width = String((count / maxGenre) * 100);
      bars.append(h("button", {
        class: "bar", type: "button", title: `Browse ${name} in the library`,
        onclick: () => { Object.assign(state.library, { genre: name, page: 1, loaded: false }); renderLibraryFilters(); showView("library"); },
      }, h("span", { text: name }), h("span", { class: "bar__track" }, fill), h("b", { text: count })));
    }

    const maxDecade = Math.max(1, ...stats.decades.map((d) => d.count));
    const columns = $("#decadeCols");
    clear(columns);
    for (const { name, count } of stats.decades) {
      const bar = h("div", { class: "col__bar" });
      bar.dataset.height = String((count / maxDecade) * 100);
      columns.append(h("div", { class: "col" }, h("b", { text: count }), bar, h("span", { text: name })));
    }

    const cloud = $("#themeCloud");
    clear(cloud);
    const maxTheme = Math.max(...stats.themes.map((t) => t.weight), 1);
    for (const { name, weight } of stats.themes) {
      cloud.append(h("span", { style: { fontSize: `${(1.2 + (weight / maxTheme) * 2.2).toFixed(2)}rem` }, text: name }));
    }
    if (!stats.themes.length) cloud.append(h("p", { class: "results__meta", text: "Add descriptions to your dataset to see themes." }));
  }

  /** Grow bars/columns from zero each time the tab opens. */
  function animateInsights() {
    requestAnimationFrame(() => requestAnimationFrame(() => {
      $$(".bar__fill").forEach((el) => { el.style.width = `${el.dataset.width}%`; });
      $$(".col__bar").forEach((el) => { el.style.height = `${el.dataset.height}%`; });
    }));
  }

  /* ───────────────────────── 4e. dataset ───────────────────────── */

  function renderHero() {
    const stats = state.dataset.stats;
    const items = [
      [fmt(stats.total), "titles"],
      [fmt(stats.genre_count), "genres"],
      [stats.year_min ? `${stats.year_min}–${stats.year_max}` : "—", "years"],
    ];
    const list = $("#heroStats");
    clear(list);
    for (const [value, label] of items) list.append(h("li", {}, h("b", { text: value }), label));

    const { meta } = state.dataset;
    $("#datasetPillText").textContent = `${meta.filename} · ${fmt(stats.total)} movies`;
  }

  function renderDatasetReport() {
    const { meta, stats } = state.dataset;
    const report = meta.report;
    const box = $("#datasetReport");
    clear(box);
    box.className = "panel report";

    const rows = [
      ["Rows read", report.rows_read], ["Movies loaded", report.rows_loaded],
      ["Duplicates merged", report.duplicates_removed], ["Skipped (no name)", report.dropped_missing_title],
      ["Missing year", report.missing_year], ["Missing genre", report.missing_genre],
      ["Missing description", report.missing_description], ["Genres inferred", report.genres_inferred],
    ];
    const mapping = Object.entries(report.mapped_columns).map(([field, column]) =>
      h("li", {}, h("code", { text: column }), ` → ${field}`));

    box.append(
      h("span", { class: `badge${meta.source === "sample" ? " badge--sample" : ""}`, text: meta.source === "sample" ? "Sample dataset" : "Your upload" }),
      h("h3", { text: "Active dataset" }),
      h("p", { class: "report__file", text: `${meta.filename} · loaded ${new Date(meta.loaded_at).toLocaleString()}` }),
      h("dl", { class: "kv" }, rows.flatMap(([label, value]) => [h("dt", { text: label }), h("dd", { text: fmt(value) })])),
      h("h4", { text: "Detected columns" }),
      h("ul", { class: "notes" }, mapping),
      report.ignored_columns.length ? h("p", { class: "report__file", text: `Ignored: ${report.ignored_columns.join(", ")}` }) : null,
      report.warnings.length ? h("h4", { text: "Notes" }) : null,
      report.warnings.length ? h("ul", { class: "notes" }, report.warnings.map((w) => h("li", { text: w }))) : null,
    );
    $("#resetBtn").hidden = meta.source === "sample";
  }

  /** Re-render everything that depends on the dataset. */
  function applyDataset(data) {
    const key = `${data.meta.filename}|${data.meta.loaded_at}`;
    const changed = state.datasetKey !== null && key !== state.datasetKey;
    state.dataset = data;
    state.datasetKey = key;

    if (changed) {
      // Movie ids belong to the previous dataset, so the profile must not survive.
      resetProfile();
      Object.assign(state.library, { page: 1, q: "", genre: "", loaded: false });
      $("#libQuery").value = "";
    } else {
      renderGenrePills();
    }
    renderHero();
    renderLibraryFilters();
    renderInsights();
    renderDatasetReport();
    if (changed && !$("#view-library").hidden) loadLibrary();
  }

  async function loadDataset() {
    applyDataset(await api("/api/dataset"));
  }

  const dropzone = $("#dropzone");
  const fileInput = $("#fileInput");
  const uploadState = $("#uploadState");

  function setUploadState(message, kind = "") {
    uploadState.textContent = message;
    uploadState.className = `dropzone__state${kind ? ` is-${kind}` : ""}`;
  }

  async function upload(file) {
    if (!file) return;
    setUploadState(`Analysing ${file.name}…`);
    const form = new FormData();
    form.append("file", file);
    try {
      const data = await api("/api/upload", { method: "POST", body: form });
      applyDataset(data);
      setUploadState(`✓ ${fmt(data.stats.total)} movies loaded`, "ok");
      toast(`Dataset ready: ${fmt(data.stats.total)} movies from ${file.name}`, "ok");
    } catch (error) {
      setUploadState(error.message, "error");
      toast(error.message, "error");
    } finally {
      fileInput.value = "";   // allow re-selecting the same file
    }
  }

  fileInput.addEventListener("change", () => upload(fileInput.files[0]));
  dropzone.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); fileInput.click(); } });
  for (const type of ["dragenter", "dragover"]) {
    dropzone.addEventListener(type, (event) => { event.preventDefault(); dropzone.classList.add("is-over"); });
  }
  for (const type of ["dragleave", "drop"]) {
    dropzone.addEventListener(type, (event) => { event.preventDefault(); dropzone.classList.remove("is-over"); });
  }
  dropzone.addEventListener("drop", (event) => upload(event.dataTransfer.files[0]));

  $("#resetBtn").addEventListener("click", async () => {
    try {
      applyDataset(await api("/api/dataset/reset", { method: "POST" }));
      setUploadState("");
      toast("Sample dataset restored.", "ok");
    } catch (error) {
      toast(error.message, "error");
    }
  });

  /* ───────────────────────── 5. bootstrap ───────────────────────── */

  (async function init() {
    try {
      await loadDataset();
    } catch (error) {
      toast(error.message, "error");
      $("#datasetPillText").textContent = "Offline";
    }
    showView(location.hash.slice(1) || "discover");
  })();
})();
