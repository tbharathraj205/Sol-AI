/**
 * SOL AI Extension — Popup Logic
 * Handles manual word lookup, API Base URL settings, and structured response rendering.
 */

document.addEventListener("DOMContentLoaded", async () => {
  const queryInput = document.getElementById("sol-query-input");
  const analyzeBtn = document.getElementById("sol-analyze-btn");
  const popupView = document.getElementById("sol-popup-view");
  const settingsToggle = document.getElementById("sol-settings-toggle");
  const settingsDrawer = document.getElementById("sol-settings-drawer");
  const apiUrlInput = document.getElementById("sol-api-url-input");
  const saveUrlBtn = document.getElementById("sol-save-url-btn");
  const settingsStatus = document.getElementById("sol-settings-status");

  // Load API URL
  const currentUrl = await getApiBaseUrl();
  apiUrlInput.value = currentUrl;

  // Settings drawer toggle
  if (settingsToggle && settingsDrawer) {
    settingsToggle.addEventListener("click", () => {
      settingsDrawer.classList.toggle("open");
    });
  }

  // Save Settings
  if (saveUrlBtn && apiUrlInput && settingsStatus) {
    saveUrlBtn.addEventListener("click", async () => {
      const newUrl = apiUrlInput.value;
      await setApiBaseUrl(newUrl);
      settingsStatus.textContent = "Saved API URL!";
      setTimeout(() => {
        settingsStatus.textContent = "";
        settingsDrawer.classList.remove("open");
      }, 1200);
    });
  }

  // Trigger analysis on Enter key
  if (queryInput) {
    queryInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        performLookup();
      }
    });
  }

  if (analyzeBtn) {
    analyzeBtn.addEventListener("click", performLookup);
  }

  async function performLookup() {
    const queryText = (queryInput.value || "").trim();
    if (!queryText) {
      renderError("Select or type a Tamil word or phrase first.");
      return;
    }

    renderLoading(queryText);

    chrome.runtime.sendMessage(
      { action: "QUERY_API", query: queryText },
      (response) => {
        if (chrome.runtime.lastError || !response) {
          renderError("SOL AI could not be reached. Ensure API server is running.");
          return;
        }

        if (response.status === "error") {
          renderError(response.error);
        } else {
          renderResult(response.data);
        }
      }
    );
  }

  function renderLoading(text) {
    popupView.innerHTML = `
      <div style="text-align: center; padding: 32px 16px;">
        <div style="font-weight: 600; color: #2563eb; margin-bottom: 8px;">Analyzing "${text}"...</div>
        <div style="font-size: 12px; color: #64748b;">Retrieving evidence from Tamil resource adapters...</div>
      </div>
    `;
  }

  function renderError(msg) {
    popupView.innerHTML = `
      <div style="background: #fef2f2; border: 1px solid #fecaca; color: #991b1b; padding: 12px; border-radius: 6px;">
        <div style="font-weight: 600; margin-bottom: 4px;">Error</div>
        <div>${msg}</div>
      </div>
    `;
  }

  function renderResult(data) {
    popupView.innerHTML = "";

    // 1. Lemma & Meaning Card
    const lemmaCard = document.createElement("div");
    lemmaCard.className = "sol-card";

    const lemmaHeader = document.createElement("div");
    lemmaHeader.className = "sol-section-header";
    lemmaHeader.textContent = "Root Lemma & Meaning";

    const lemmaTitle = document.createElement("div");
    lemmaTitle.className = "sol-lemma-title";
    lemmaTitle.textContent = data.lemma || data.query;

    lemmaCard.appendChild(lemmaHeader);
    lemmaCard.appendChild(lemmaTitle);

    const rawSenses = data.meaning
      ? data.meaning.split(';').map(s => s.replace(/\s+/g, ' ').trim()).filter(Boolean)
      : [];
    const senses = rawSenses.slice(0, 2);

    if (senses.length > 1) {
      const meanList = document.createElement("ul");
      meanList.className = "sol-meaning-bullets";
      senses.forEach(sense => {
        const li = document.createElement("li");
        li.textContent = sense;
        meanList.appendChild(li);
      });
      lemmaCard.appendChild(meanList);
    } else if (senses.length === 1) {
      const meaningText = document.createElement("div");
      meaningText.className = "sol-meaning-text";
      meaningText.textContent = senses[0];
      lemmaCard.appendChild(meaningText);
    } else {
      const meaningText = document.createElement("div");
      meaningText.className = "sol-meaning-text sol-empty-meaning";
      meaningText.textContent = "Meaning not established from the available evidence.";
      lemmaCard.appendChild(meaningText);
    }

    popupView.appendChild(lemmaCard);

    // 2. Morphology Card
    const morph = data.morphology;
    const morphCard = document.createElement("div");
    morphCard.className = "sol-card";

    const morphHeader = document.createElement("div");
    morphHeader.className = "sol-section-header";
    morphHeader.textContent = "Morphology";

    const morphGroup = document.createElement("div");
    morphGroup.className = "sol-morph-group";

    if (morph) {
      if (morph.pos) {
        const posPill = document.createElement("span");
        posPill.className = "sol-pill sol-pill-pos";
        posPill.textContent = `POS: ${morph.pos}`;
        morphGroup.appendChild(posPill);
      }

      const atype = morph.analysis_type || "core";
      const typePill = document.createElement("span");
      typePill.className = `sol-pill ${atype === "guesser" ? "sol-pill-guesser" : "sol-pill-core"}`;
      typePill.textContent = `${atype.toUpperCase()}`;
      morphGroup.appendChild(typePill);

      if (morph.fst_model) {
        const modelPill = document.createElement("span");
        modelPill.className = "sol-pill sol-pill-model";
        modelPill.textContent = morph.fst_model;
        morphGroup.appendChild(modelPill);
      }
    } else {
      const noMorph = document.createElement("div");
      noMorph.className = "sol-empty-meaning";
      noMorph.textContent = "Morphological analysis unavailable.";
      morphGroup.appendChild(noMorph);
    }

    morphCard.appendChild(morphHeader);
    morphCard.appendChild(morphGroup);
    popupView.appendChild(morphCard);

    // 3. Contextual Interpretation
    if (data.contextual_interpretation) {
      const interpCard = document.createElement("div");
      interpCard.className = "sol-card";

      const interpHeader = document.createElement("div");
      interpHeader.className = "sol-section-header";
      interpHeader.textContent = "Contextual Interpretation";

      const interpText = document.createElement("div");
      interpText.style.fontSize = "12px";
      interpText.style.color = "#334155";
      interpText.textContent = data.contextual_interpretation;

      interpCard.appendChild(interpHeader);
      interpCard.appendChild(interpText);
      popupView.appendChild(interpCard);
    }

    // 4. Literary Context
    const litItems = data.literary_context || [];
    if (litItems.length > 0) {
      const litCard = document.createElement("div");
      litCard.className = "sol-card";

      const litHeader = document.createElement("div");
      litHeader.className = "sol-section-header";
      litHeader.textContent = `Literary Context (${litItems.length})`;

      litCard.appendChild(litHeader);

      litItems.slice(0, 3).forEach((item) => {
        const itemDiv = document.createElement("div");
        itemDiv.className = "sol-literary-card";

        const meta = document.createElement("div");
        meta.style.fontWeight = "600";
        meta.style.fontSize = "11px";
        meta.style.color = "#2563eb";
        meta.textContent = `${item.work || "Sangam Work"} ${item.verse_number ? "(" + item.verse_number + ")" : ""}`;

        const passage = document.createElement("div");
        passage.style.fontSize = "12px";
        passage.style.color = "#0f172a";
        passage.style.marginTop = "2px";
        passage.textContent = item.passage || "";

        itemDiv.appendChild(meta);
        itemDiv.appendChild(passage);
        litCard.appendChild(itemDiv);
      });

      popupView.appendChild(litCard);
    }



    // 5. Sources
    const sources = data.sources || [];
    const srcCard = document.createElement("div");
    srcCard.className = "sol-card";

    const srcHeader = document.createElement("div");
    srcHeader.className = "sol-section-header";
    srcHeader.textContent = "Sources Provenance";

    const srcTags = document.createElement("div");
    srcTags.className = "sol-source-tags";

    if (sources.length > 0) {
      sources.forEach((s) => {
        const chip = document.createElement("span");
        chip.className = "sol-source-chip";
        chip.textContent = s;
        srcTags.appendChild(chip);
      });
    } else {
      const noSrc = document.createElement("span");
      noSrc.className = "sol-empty-meaning";
      noSrc.textContent = "No primary resource evidence.";
      srcTags.appendChild(noSrc);
    }

    srcCard.appendChild(srcHeader);
    srcCard.appendChild(srcTags);
    popupView.appendChild(srcCard);
  }
});
