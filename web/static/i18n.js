/* The console language: detection, the translation helper and the toggle.
 *
 * The catalogue arrives from /api/i18n.js, which the server builds from
 * web/messages.py. A key that the catalogue does not know falls back to
 * English and then to the key itself, and a missing catalogue leaves the
 * Chinese text of the page untouched.
 */
(function () {
  const STORAGE_KEY = "npt-lang";
  const catalogue = window.NPT_MESSAGES || {};
  const ATTRIBUTES = ["title", "placeholder", "aria-label"];

  function normalize(value) {
    return String(value || "").toLowerCase().startsWith("zh") ? "zh-CN" : "en";
  }

  function detectLanguage() {
    try {
      const saved = window.localStorage.getItem(STORAGE_KEY);
      if (saved) return normalize(saved);
    } catch (error) {
      /* A blocked storage must not stop the page. */
    }
    const languages = navigator.languages || [navigator.language || ""];
    for (const entry of languages) {
      if (String(entry).toLowerCase().startsWith("zh")) return "zh-CN";
    }
    return "en";
  }

  let language = detectLanguage();

  function translate(key) {
    const entry = catalogue[key];
    if (!entry) return key;
    return entry[language] || entry["en"] || key;
  }

  function fill(template, values) {
    if (!values) return template;
    return template.replace(/\{([A-Za-z0-9_]+)\}/g, (match, name) =>
      Object.prototype.hasOwnProperty.call(values, name) ? String(values[name]) : match);
  }

  function t(key, values) {
    return fill(translate(key), values);
  }

  function applyTranslations(root) {
    const scope = root || document;
    scope.querySelectorAll("[data-i18n]").forEach(element => {
      if (element.children.length) return;
      element.textContent = translate(element.getAttribute("data-i18n"));
    });
    ATTRIBUTES.forEach(attribute => {
      scope.querySelectorAll("[data-i18n-" + attribute + "]").forEach(element => {
        element.setAttribute(attribute, translate(element.getAttribute("data-i18n-" + attribute)));
      });
    });
  }

  function setLanguage(value, remember) {
    language = normalize(value);
    if (remember !== false) {
      try {
        window.localStorage.setItem(STORAGE_KEY, language);
      } catch (error) {
        /* A blocked storage must not stop the page. */
      }
    }
    document.documentElement.setAttribute("lang", language === "zh-CN" ? "zh-CN" : "en");
    applyTranslations(document);
    const toggle = document.getElementById("lang-toggle");
    if (toggle) toggle.textContent = language === "zh-CN" ? "EN" : "中文";
    document.dispatchEvent(new CustomEvent("npt-language", { detail: { language: language } }));
    return language;
  }

  function languageHeader(url) {
    if (!url || String(url).indexOf("//") === 0) return false;
    return String(url).indexOf("/api/") === 0;
  }

  const nativeFetch = window.fetch ? window.fetch.bind(window) : null;
  if (nativeFetch) {
    window.fetch = function (input, options) {
      const settings = options || {};
      const url = typeof input === "string" ? input : (input && input.url) || "";
      if (languageHeader(url)) {
        const headers = new Headers(settings.headers || (input && input.headers) || {});
        headers.set("X-NPT-Language", language);
        settings.headers = headers;
      }
      return nativeFetch(input, settings);
    };
  }

  window.t = t;
  window.nptI18n = {
    language: () => language,
    setLanguage: setLanguage,
    applyTranslations: applyTranslations,
    translate: translate
  };

  document.addEventListener("DOMContentLoaded", () => {
    setLanguage(language, false);
    const toggle = document.getElementById("lang-toggle");
    if (toggle) {
      toggle.addEventListener("click", () => {
        setLanguage(language === "zh-CN" ? "en" : "zh-CN");
      });
    }
  });
})();
