/**
 * SOL AI Extension — Background Service Worker (Manifest V3)
 * Manages context menus, API requests, and message passing between content scripts and popup.
 *
 * Security Note: All LLM API keys (e.g. Gemini) remain server-side.
 * The extension communicates ONLY with the SOL AI API server (default http://localhost:8000).
 */

importScripts("../config/config.js");

const CONTEXT_MENU_ID = "sol_ai_explain";

// Setup context menu on installation
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: CONTEXT_MENU_ID,
    title: "Explain with SOL AI",
    contexts: ["selection"],
  });
});

// Context menu click handler
chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== CONTEXT_MENU_ID || !tab || !tab.id) return;

  const rawText = info.selectionText || "";
  const queryText = rawText.trim();

  if (!queryText) {
    chrome.tabs.sendMessage(tab.id, {
      action: "SHOW_ERROR",
      error: "Select a Tamil word or phrase first.",
    });
    return;
  }

  try {
    // 1. Request surrounding context from the content script FIRST (before modifying DOM)
    let contextText = "";
    try {
      const contextResponse = await chrome.tabs.sendMessage(tab.id, { action: "GET_CONTEXT" });
      if (contextResponse && contextResponse.context) {
        contextText = contextResponse.context;
      }
    } catch (e) {
      console.warn("Could not retrieve context from content script:", e);
    }

    // 1.5 Notify content script to open panel in LOADING state
    chrome.tabs.sendMessage(tab.id, {
      action: "SHOW_LOADING",
      query: queryText,
    });

    // 2. Perform API request to SOL AI backend
    const apiBaseUrl = await getApiBaseUrl();
    let response;
    try {
      response = await fetchWithTimeout(
        `${apiBaseUrl}/api/query`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: queryText, context: contextText }),
        },
        DEFAULT_CONFIG.TIMEOUT_MS
      );
    } catch (fetchErr) {
      let errorMsg = `SOL AI server could not be reached at ${apiBaseUrl}. Ensure the backend server is running.`;
      if (fetchErr.name === "AbortError") {
        errorMsg = "SOL AI took too long to respond (request timed out).";
      }
      chrome.tabs.sendMessage(tab.id, {
        action: "SHOW_ERROR",
        error: errorMsg,
        query: queryText,
        canRetry: true,
      });
      return;
    }

    let data;
    try {
      data = await response.json();
    } catch (jsonErr) {
      chrome.tabs.sendMessage(tab.id, {
        action: "SHOW_ERROR",
        error: "Received invalid response format from SOL AI server.",
        query: queryText,
        canRetry: true,
      });
      return;
    }

    if (!response.ok) {
      const errDetail = (data && typeof data === "object" && data.error)
        ? data.error
        : `SOL AI API returned HTTP status ${response.status}.`;
      chrome.tabs.sendMessage(tab.id, {
        action: "SHOW_ERROR",
        error: errDetail,
        query: queryText,
        canRetry: true,
      });
      return;
    }

    // 3. Send structured response to content script
    chrome.tabs.sendMessage(tab.id, {
      action: "SHOW_RESULT",
      query: queryText,
      result: data,
    });
  } catch (err) {
    let errorMsg = "An unexpected error occurred while communicating with SOL AI.";
    if (err && err.name === "AbortError") {
      errorMsg = "SOL AI took too long to respond (request timed out).";
    }

    chrome.tabs.sendMessage(tab.id, {
      action: "SHOW_ERROR",
      error: errorMsg,
      query: queryText,
      canRetry: true,
    });
  }
});

// Handle messages from popup or content script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "QUERY_API") {
    const queryText = (message.query || "").trim();
    if (!queryText) {
      sendResponse({ status: "error", error: "Select a Tamil word or phrase first." });
      return true;
    }

    (async () => {
      try {
        const apiBaseUrl = await getApiBaseUrl();
        let response;
        try {
          response = await fetchWithTimeout(
            `${apiBaseUrl}/api/query`,
            {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ 
                query: queryText, 
                context: message.context || "", 
                provider: message.provider 
              }),
            },
            DEFAULT_CONFIG.TIMEOUT_MS
          );
        } catch (fetchErr) {
          let errorMsg = `SOL AI server could not be reached at ${apiBaseUrl}. Ensure the backend server is running.`;
          if (fetchErr.name === "AbortError") {
            errorMsg = "SOL AI took too long to respond (request timed out).";
          }
          sendResponse({ status: "error", error: errorMsg });
          return;
        }

        let data;
        try {
          data = await response.json();
        } catch (jsonErr) {
          sendResponse({ status: "error", error: "Received invalid response format from SOL AI server." });
          return;
        }

        if (!response.ok) {
          const errDetail = (data && typeof data === "object" && data.error)
            ? data.error
            : `API returned status ${response.status}`;
          sendResponse({ status: "error", error: errDetail });
        } else {
          sendResponse({ status: "success", data: data });
        }
      } catch (err) {
        sendResponse({ status: "error", error: "An unexpected error occurred while communicating with SOL AI." });
      }
    })();

    return true; // Keep response channel open for async sendResponse
  } else if (message.action === "OPEN_WEB_APP") {
    const query = message.query || "";
    // Hardcoded to localhost:3000 for development. Can be made configurable.
    const searchUrl = `http://localhost:3000/?q=${encodeURIComponent(query)}`;
    chrome.tabs.create({ url: searchUrl });
  }
});

/**
 * Fetch wrapper with timeout abort controller
 */
async function fetchWithTimeout(resource, options = {}, timeoutMs = 24000) {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(resource, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(id);
    return response;
  } catch (err) {
    clearTimeout(id);
    throw err;
  }
}
