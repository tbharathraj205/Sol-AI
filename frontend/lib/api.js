/**
 * SOL AI Frontend API Client.
 * Connects to SOL AI REST API backend.
 *
 * In production (Vercel) and development, requests to /api/* are proxied
 * to the backend (configured via SOL_BACKEND_URL in next.config.mjs).
 * To bypass the proxy or specify a direct API host, configure NEXT_PUBLIC_SOL_API_BASE_URL.
 */

const API_BASE_URL = (process.env.NEXT_PUBLIC_SOL_API_BASE_URL || "").replace(/\/+$/, "");

/**
 * Checks API server health
 */
export async function checkApiHealth() {
  try {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), 4000);
    const res = await fetch(`${API_BASE_URL}/api/health`, {
      method: "GET",
      signal: controller.signal,
    });
    clearTimeout(id);
    if (res.ok) {
      const data = await res.json();
      return { status: "ok", data };
    }
    return { status: "error", message: `HTTP ${res.status}` };
  } catch (err) {
    return { status: "offline", message: "SOL AI API backend is offline." };
  }
}

/**
 * Queries SOL AI engine for etymological & morphological evidence
 * @param {string} word Tamil query word or phrase
 * @param {string} provider Optional provider ('mock', 'gemini', or 'groq')
 */
export async function querySolApi(word, provider = "mock") {
  const queryText = (word || "").trim();
  if (!queryText) {
    return { error: "Search query cannot be empty.", isUnknown: false };
  }

  try {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), 30000); // 30s timeout
    const res = await fetch(`${API_BASE_URL}/api/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: queryText, provider }),
      signal: controller.signal,
      cache: "no-store",
    });
    clearTimeout(id);

    const data = await res.json();

    if (!res.ok) {
      return {
        error: data.error || `SOL AI API returned HTTP status ${res.status}.`,
        isError: true,
      };
    }

    return { data, isError: false };
  } catch (err) {
    if (err.name === "AbortError") {
      return {
        error: "SOL AI API took too long to respond. Please try again.",
        isTimeout: true,
      };
    }
    const target = API_BASE_URL || "/api";
    return {
      error: `SOL AI backend server could not be reached. Ensure the API is reachable at ${target}.`,
      isOffline: true,
    };
  }
}
