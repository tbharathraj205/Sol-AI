/**
 * Global Configuration & Storage Helper for SOL AI Browser Extension.
 * Default API Base URL: http://127.0.0.1:8000
 * The browser extension NEVER handles Gemini API keys directly; keys remain server-side.
 */

var DEFAULT_CONFIG = typeof DEFAULT_CONFIG !== "undefined" ? DEFAULT_CONFIG : {
  SOL_API_BASE_URL: "http://127.0.0.1:8000",
  DEFAULT_PROVIDER: "mock",
  TIMEOUT_MS: 24000,
};

/**
 * Retrieves configured SOL AI API Base URL from chrome.storage.local
 */
async function getApiBaseUrl() {
  if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
    return new Promise((resolve) => {
      chrome.storage.local.get(["SOL_API_BASE_URL"], (result) => {
        let url = result.SOL_API_BASE_URL || DEFAULT_CONFIG.SOL_API_BASE_URL;
        url = url.trim().replace(/\/+$/, "");
        resolve(url);
      });
    });
  }
  return DEFAULT_CONFIG.SOL_API_BASE_URL;
}

/**
 * Saves SOL AI API Base URL to chrome.storage.local
 */
async function setApiBaseUrl(url) {
  if (typeof chrome !== "undefined" && chrome.storage && chrome.storage.local) {
    let cleanUrl = (url || DEFAULT_CONFIG.SOL_API_BASE_URL).trim().replace(/\/+$/, "");
    return new Promise((resolve) => {
      chrome.storage.local.set({ SOL_API_BASE_URL: cleanUrl }, resolve);
    });
  }
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { DEFAULT_CONFIG, getApiBaseUrl, setApiBaseUrl };
}
