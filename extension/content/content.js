/**
 * SOL AI Extension — Content Script (Dark Mode Overhaul)
 */

const ICONS = {
  settings: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>`,
  close: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
  book: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20"/></svg>`,
  document: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>`,
  leaf: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 4.18 2 8 0 5.5-4.78 10-10 10Z"/><path d="M2 21c0-3 1.85-5.36 5.08-6C9.5 14.52 12 13 13 12"/></svg>`,
  bulb: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.9 1.3 1.5 1.5 2.5"/><path d="M9 18h6"/><path d="M10 22h4"/></svg>`,
  heart: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/></svg>`,
  git: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><circle cx="13" cy="6" r="3"/><line x1="6" y1="9" x2="6" y2="21"/><path d="M13 9a9 9 0 0 1 5 8"/></svg>`,
  list: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>`,
  arrowRight: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>`,
  lotus: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2c0 0-4 4-4 10a4 4 0 0 0 8 0c0-6-4-10-4-10Z"/><path d="M12 2c0 0 7 2 9 8 1 3 1 7-3 10-3 2-6 2-6 2s-3 0-6-2c-4-3-4-7-3-10 2-6 9-8 9-8Z"/></svg>`,
  select: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 3v2M5 9v2M5 15v2M3 21h2M9 21h2M15 21h2M21 21v-2M21 15v-2M21 9v-2M21 3h-2M15 3h-2M9 3H7"/><path d="M14 14l-8-8"/><path d="M14 14l-3-1"/><path d="M14 14l-1-3"/></svg>`,
  alertCircle: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`,
  search: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>`,
  wifiOff: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="2" y1="2" x2="22" y2="22"/><path d="M8.5 16.5a5 5 0 0 1 7 0"/><path d="M5 13a10 10 0 0 1 5.5-2.5"/><path d="M1 9a15 15 0 0 1 8.5-3.5"/><path d="M19 13a10 10 0 0 1 3 5.5"/><path d="M23 9a15 15 0 0 1-5 2"/></svg>`,
  pin: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="17" x2="12" y2="22"/><path d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V6h1a2 2 0 0 0 0-4H8a2 2 0 0 0 0 4h1v4.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24Z"/></svg>`,
  refreshCw: `<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>`
};

let solHostContainer = null;
let solShadowRoot = null;
let solLastQuery = "";
let loadingWatchdog = null;
let activeWatchdogQuery = "";

function clearWatchdog() {
  if (loadingWatchdog) {
    clearTimeout(loadingWatchdog);
    loadingWatchdog = null;
  }
  activeWatchdogQuery = "";
}

function getShadowRoot() {
  if (!solHostContainer) {
    solHostContainer = document.createElement("div");
    solHostContainer.id = "sol-ai-extension-root";
    solHostContainer.style.position = "absolute";
    solHostContainer.style.top = "0";
    solHostContainer.style.left = "0";
    solHostContainer.style.width = "0";
    solHostContainer.style.height = "0";
    solHostContainer.style.zIndex = "2147483647";
    document.body.appendChild(solHostContainer);

    solShadowRoot = solHostContainer.attachShadow({ mode: "open" });

    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = chrome.runtime.getURL("content/content.css");
    solShadowRoot.appendChild(link);
  }
  return solShadowRoot;
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "GET_CONTEXT") {
    let contextText = "";
    try {
      const selection = window.getSelection();
      if (selection && selection.rangeCount > 0) {
        let container = selection.getRangeAt(0).commonAncestorContainer;
        if (container.nodeType === 3) container = container.parentNode;
        
        // Traverse up to find a block level element or something with enough text
        let current = container;
        while (current && current !== document.body && current.nodeName !== 'P' && current.nodeName !== 'DIV' && current.nodeName !== 'SECTION' && current.nodeName !== 'ARTICLE') {
          current = current.parentNode;
        }
        
        let fullPassage = "";
        if (current && current.textContent) {
          fullPassage = current.textContent.trim();
        } else if (container && container.textContent) {
          fullPassage = container.textContent.trim(); // fallback
        }

        const selectedWord = selection.toString().trim();

        if (fullPassage && selectedWord) {
          // Split using robust sentence boundary matching that handles all spacing variations
          const sentences = fullPassage.match(/[^.?!]+[.?!]*/g) || [];
          
          // Find the sentence that contains the selected word
          const targetSentence = sentences.find(sentence => sentence.includes(selectedWord));
          
          if (targetSentence) {
            contextText = targetSentence.trim();
          } else {
            // If strict match fails, try case-insensitive or partial match
            const looseSentence = sentences.find(sentence => sentence.toLowerCase().includes(selectedWord.toLowerCase()));
            if (looseSentence) {
              contextText = looseSentence.trim();
            } else {
              contextText = fullPassage.substring(0, 200); 
            }
          }
        }
      } // Closes if (selection && selection.rangeCount > 0)
      
      if (!contextText) {
        contextText = "[FALLBACK] Extracted text was empty.";
      }
    } catch (e) {
      console.error("Context extraction failed", e);
      contextText = "[FALLBACK] Extraction threw an error: " + e.message;
    }
    
    sendResponse({ context: contextText });
  } else if (message.action === "SHOW_LOADING") {
    solLastQuery = message.query || "";
    renderLoadingPanel(solLastQuery);
  } else if (message.action === "SHOW_RESULT") {
    renderResultPanel(message.query, message.result);
  } else if (message.action === "SHOW_ERROR") {
    renderErrorPanel(message.query || solLastQuery, message.error, message.canRetry);
  } else if (message.action === "SHOW_DEFAULT") {
    renderDefaultPanel();
  }
});

function closePanel() {
  clearWatchdog();
  if (solShadowRoot) {
    const panel = solShadowRoot.querySelector("#sol-ai-panel");
    if (panel) panel.remove();
  }
}

function createHeader() {
  const header = document.createElement("div");
  header.className = "sol-header";

  const group = document.createElement("div");
  group.className = "sol-logo-group";
  
  const logo = document.createElement("img");
  logo.src = chrome.runtime.getURL("icons/logo.png");
  logo.className = "sol-logo-img";

  const titleGroup = document.createElement("div");
  titleGroup.className = "sol-header-title";
  
  const title = document.createElement("span");
  title.className = "sol-header-title-text";
  title.textContent = "சொல் AI";
  
  const subtitle = document.createElement("span");
  subtitle.className = "sol-header-subtitle";
  subtitle.textContent = "WORDS. WISDOM. INTELLIGENCE.";

  titleGroup.appendChild(title);
  titleGroup.appendChild(subtitle);

  group.appendChild(logo);
  group.appendChild(titleGroup);

  const actions = document.createElement("div");
  actions.className = "sol-header-actions";

  const pinBtn = document.createElement("button");
  pinBtn.className = "sol-icon-btn";
  pinBtn.innerHTML = ICONS.pin;
  pinBtn.title = "Pin Panel";

  const setBtn = document.createElement("button");
  setBtn.className = "sol-icon-btn";
  setBtn.innerHTML = ICONS.settings;
  setBtn.title = "Settings";

  const closeBtn = document.createElement("button");
  closeBtn.className = "sol-icon-btn";
  closeBtn.innerHTML = ICONS.close;
  closeBtn.title = "Close Panel";
  closeBtn.onclick = closePanel;

  actions.appendChild(pinBtn);
  actions.appendChild(setBtn);
  actions.appendChild(closeBtn);

  header.appendChild(group);
  header.appendChild(actions);
  return header;
}

function createBasePanel() {
  const shadow = getShadowRoot();
  closePanel();

  const panel = document.createElement("div");
  panel.id = "sol-ai-panel";
  
  const bg = document.createElement("div");
  bg.className = "sol-panel-bg";
  panel.appendChild(bg);

  panel.appendChild(createHeader());

  const body = document.createElement("div");
  body.className = "sol-body";
  panel.appendChild(body);

  shadow.appendChild(panel);
  return { panel, body };
}

function renderDefaultPanel() {
  const { body } = createBasePanel();
  clearWatchdog();
  
  const state = document.createElement("div");
  state.className = "sol-default-state";
  
  const iconBox = document.createElement("div");
  iconBox.className = "sol-status-icon";
  iconBox.innerHTML = ICONS.select;
  
  const title = document.createElement("div");
  title.className = "sol-default-title";
  title.textContent = "Select a Tamil word";
  
  const desc = document.createElement("div");
  desc.className = "sol-default-desc";
  desc.innerHTML = 'Highlight any Tamil word on this page,<br>then right-click and choose<br><strong>"Explain with சொல் AI"</strong>.';
  
  const quote = document.createElement("div");
  quote.className = "sol-footer-quote";
  quote.innerHTML = '“ஒரு சொல் — ஓர் உலகம்.”';

  state.appendChild(iconBox);
  state.appendChild(title);
  state.appendChild(desc);
  
  body.appendChild(state);
  body.appendChild(quote);
}

function renderLoadingPanel(queryText) {
  const { body } = createBasePanel();
  clearWatchdog();
  activeWatchdogQuery = queryText;

  const state = document.createElement("div");
  state.className = "sol-status-state";
  
  const iconBox = document.createElement("div");
  iconBox.className = "sol-status-icon loading";
  iconBox.innerHTML = ICONS.search; // We can use search or hourglass for loading
  
  const title = document.createElement("div");
  title.className = "sol-status-title";
  title.textContent = "Exploring...";
  
  const desc = document.createElement("div");
  desc.className = "sol-status-desc";
  desc.innerHTML = `Finding meanings, literary context<br>and more for "<strong>${queryText}</strong>"...`;

  state.appendChild(iconBox);
  state.appendChild(title);
  state.appendChild(desc);
  
  body.appendChild(state);

  // Watchdog: recover gracefully if background worker is killed or stalled (>25s)
  loadingWatchdog = setTimeout(() => {
    if (activeWatchdogQuery === queryText) {
      loadingWatchdog = null;
      activeWatchdogQuery = "";
      renderErrorPanel(
        queryText,
        "SOL AI took too long to respond. The server may still be warming up.",
        true
      );
    }
  }, 25000);
}

function renderErrorPanel(queryText, errorMessage, canRetry) {
  const { body } = createBasePanel();
  clearWatchdog();
  
  const state = document.createElement("div");
  state.className = "sol-status-state";
  
  const isNet = errorMessage.toLowerCase().includes("internet") || errorMessage.toLowerCase().includes("fetch");
  const isNotTamil = errorMessage.toLowerCase().includes("tamil");
  
  const iconBox = document.createElement("div");
  iconBox.className = "sol-status-icon error";
  iconBox.innerHTML = isNet ? ICONS.wifiOff : (isNotTamil ? ICONS.alertCircle : ICONS.alertCircle);
  
  const title = document.createElement("div");
  title.className = "sol-status-title";
  title.textContent = isNet ? "No internet connection" : (isNotTamil ? "This doesn't appear to be Tamil" : "Something went wrong");
  
  const desc = document.createElement("div");
  desc.className = "sol-status-desc";
  desc.textContent = errorMessage || "An unexpected error occurred. Please try again.";

  state.appendChild(iconBox);
  state.appendChild(title);
  state.appendChild(desc);

  if (canRetry) {
    const btn = document.createElement("button");
    btn.className = "sol-status-btn";
    btn.innerHTML = `${ICONS.refreshCw} Try again`;
    btn.onclick = () => {
      renderLoadingPanel(queryText);
      chrome.runtime.sendMessage({ action: "QUERY_API", query: queryText }, (response) => {
        if (chrome.runtime.lastError || !response || response.status === "error") {
          renderErrorPanel(queryText, response?.error || "Error", true);
        } else {
          renderResultPanel(queryText, response.data);
        }
      });
    };
    state.appendChild(btn);
  }
  
  body.appendChild(state);
}

function renderResultPanel(queryText, data) {
  const { body } = createBasePanel();
  clearWatchdog();
  
  // 1. Hero Section
  const hero = document.createElement("div");
  hero.className = "sol-hero";
  
  const heroTop = document.createElement("div");
  heroTop.className = "sol-hero-top";
  
  const wordGroup = document.createElement("div");
  const wordTitle = document.createElement("div");
  wordTitle.className = "sol-word-title";
  wordTitle.textContent = data.lemma || queryText;
  
  wordGroup.appendChild(wordTitle);
  heroTop.appendChild(wordGroup);
  
  const trans = document.createElement("div");
  trans.className = "sol-transliteration";
  trans.textContent = data.transliteration || "";
  
  const badges = document.createElement("div");
  badges.className = "sol-badges";
  
  if (data.morphology) {
    if (data.morphology.pos) {
      const b1 = document.createElement("span");
      b1.className = "sol-badge";
      b1.textContent = data.morphology.pos;
      badges.appendChild(b1);
    }
  }

  hero.appendChild(heroTop);
  hero.appendChild(trans);
  hero.appendChild(badges);
  body.appendChild(hero);

  // 2. Tabs Navigation
  const tabNav = document.createElement("div");
  tabNav.className = "sol-tabs";
  
  const tabNames = ["Meaning", "Literary Context", "Morphology"];
  const tabBtns = [];
  const tabContents = [];

  tabNames.forEach((name, i) => {
    const btn = document.createElement("button");
    btn.className = `sol-tab ${i === 0 ? "active" : ""}`;
    btn.textContent = name;
    
    const content = document.createElement("div");
    content.className = `sol-tab-content ${i === 0 ? "active" : ""}`;
    
    btn.onclick = () => {
      tabBtns.forEach(b => b.classList.remove("active"));
      tabContents.forEach(c => c.classList.remove("active"));
      btn.classList.add("active");
      content.classList.add("active");
    };
    
    tabBtns.push(btn);
    tabContents.push(content);
    tabNav.appendChild(btn);
  });
  
  body.appendChild(tabNav);
  
  const [meanContent, litContent, morphContent] = tabContents;

  // Build Meaning Content
  // 1. Separate Contextual WSD Card (Situational / In this context)
  if (data.contextual_meaning) {
    const contextCard = document.createElement("div");
    contextCard.className = "sol-meaning-card";
    contextCard.style.borderLeft = "3px solid #C9A227";

    const contextHeader = document.createElement("div");
    contextHeader.className = "sol-card-header";
    contextHeader.style.color = "#C9A227"; // Highlight context color
    contextHeader.innerHTML = `${ICONS.bulb} In this context (இச்சூழலில்)`;
    contextCard.appendChild(contextHeader);
    
    const contextText = document.createElement("div");
    contextText.className = "sol-meaning-summary";
    contextText.style.fontWeight = "bold";
    contextText.style.marginBottom = "0";
    contextText.textContent = data.contextual_meaning;
    contextCard.appendChild(contextText);

    meanContent.appendChild(contextCard);
  }

  // 2. General Meaning Card (Preserved Senses)
  const meanCard = document.createElement("div");
  meanCard.className = "sol-meaning-card";

  let senses = [];
  if (data.senses && Array.isArray(data.senses) && data.senses.length > 0) {
    senses = data.senses.slice(0, 2).map(s => s.raw_text || s.title);
  } else if (data.meaning) {
    senses = data.meaning.split(';').map(s => s.replace(/\s+/g, ' ').trim()).filter(Boolean).slice(0, 2);
  }

  const meanHeader = document.createElement("div");
  meanHeader.className = "sol-card-header";
  meanHeader.style.display = "flex";
  meanHeader.style.justifyContent = "space-between";
  meanHeader.style.alignItems = "center";
  meanHeader.innerHTML = `
    <span style="display:flex;align-items:center;gap:8px;">${ICONS.book} General Meaning</span>
    <span style="font-size:11px;color:#94a3b8;font-weight:500;">${senses.length} Senses Preserved</span>
  `;
  meanCard.appendChild(meanHeader);
  
  if (senses.length > 1) {
    const meanList = document.createElement("ul");
    meanList.className = "sol-meaning-bullets";
    senses.forEach(sense => {
      const li = document.createElement("li");
      li.textContent = sense;
      meanList.appendChild(li);
    });
    meanCard.appendChild(meanList);
  } else {
    const meanText = document.createElement("div");
    meanText.className = "sol-meaning-summary";
    meanText.textContent = senses.length === 1 ? senses[0] : "Meaning not established.";
    meanCard.appendChild(meanText);
  }
  
  meanContent.appendChild(meanCard);

  // 3. Related Words Card (max 3)
  const relWords = (data.related_words || []).slice(0, 3);
  if (relWords.length > 0) {
    const relCard = document.createElement("div");
    relCard.className = "sol-meaning-card";

    const relHeader = document.createElement("div");
    relHeader.className = "sol-card-header";
    relHeader.innerHTML = `${ICONS.git} Related Words`;
    relCard.appendChild(relHeader);

    const relGroup = document.createElement("div");
    relGroup.style.display = "flex";
    relGroup.style.flexWrap = "wrap";
    relGroup.style.gap = "8px";
    relGroup.style.marginTop = "10px";

    relWords.forEach(word => {
      const chip = document.createElement("button");
      chip.textContent = word;
      chip.className = "sol-badge";
      chip.style.cursor = "pointer";
      chip.style.borderColor = "rgba(201, 162, 39, 0.4)";
      chip.style.color = "var(--sol-gold)";
      chip.onclick = () => {
        renderLoadingPanel(word);
        chrome.runtime.sendMessage({ action: "QUERY_API", query: word }, (response) => {
          if (chrome.runtime.lastError || !response || response.status === "error") {
            renderErrorPanel(word, response?.error || "Error", true);
          } else {
            renderResultPanel(word, response.data);
          }
        });
      };
      relGroup.appendChild(chip);
    });

    relCard.appendChild(relGroup);
    meanContent.appendChild(relCard);
  }
  
  // Build Morph Content
  const mCard = document.createElement("div");
  mCard.className = "sol-meaning-card";
  const mHeader = document.createElement("div");
  mHeader.className = "sol-card-header";
  mHeader.innerHTML = `${ICONS.leaf} Morphological Analysis`;
  mCard.appendChild(mHeader);
  
  if (data.morphology) {
    const morphGroup = document.createElement("div");
    morphGroup.style.display = "flex";
    morphGroup.style.flexWrap = "wrap";
    morphGroup.style.gap = "8px";
    morphGroup.style.marginTop = "12px";

    if (data.morphology.pos) {
      const posPill = document.createElement("span");
      posPill.textContent = `POS: ${data.morphology.pos}`;
      posPill.style.padding = "4px 10px";
      posPill.style.background = "rgba(37, 99, 235, 0.1)";
      posPill.style.border = "1px solid rgba(37, 99, 235, 0.3)";
      posPill.style.borderRadius = "12px";
      posPill.style.fontSize = "12px";
      posPill.style.color = "#60a5fa";
      morphGroup.appendChild(posPill);
    }
    
    if (data.morphology.analysis_type) {
      const typePill = document.createElement("span");
      typePill.textContent = data.morphology.analysis_type.toUpperCase();
      typePill.style.padding = "4px 10px";
      typePill.style.background = "rgba(16, 185, 129, 0.1)";
      typePill.style.border = "1px solid rgba(16, 185, 129, 0.3)";
      typePill.style.borderRadius = "12px";
      typePill.style.fontSize = "12px";
      typePill.style.color = "#34d399";
      morphGroup.appendChild(typePill);
    }

    if (data.morphology.case) {
      const casePill = document.createElement("span");
      casePill.textContent = `Case: ${data.morphology.case}`;
      casePill.style.padding = "4px 10px";
      casePill.style.background = "rgba(168, 85, 247, 0.1)";
      casePill.style.border = "1px solid rgba(168, 85, 247, 0.3)";
      casePill.style.borderRadius = "12px";
      casePill.style.fontSize = "12px";
      casePill.style.color = "#c084fc";
      morphGroup.appendChild(casePill);
    }

    if (data.morphology.number) {
      const numPill = document.createElement("span");
      numPill.textContent = `Number: ${data.morphology.number}`;
      numPill.style.padding = "4px 10px";
      numPill.style.background = "rgba(234, 179, 8, 0.1)";
      numPill.style.border = "1px solid rgba(234, 179, 8, 0.3)";
      numPill.style.borderRadius = "12px";
      numPill.style.fontSize = "12px";
      numPill.style.color = "#facc15";
      morphGroup.appendChild(numPill);
    }

    if (data.morphology.raw_morphology) {
      const rawTxt = document.createElement("div");
      rawTxt.textContent = data.morphology.raw_morphology;
      rawTxt.style.color = "var(--sol-text-muted)";
      rawTxt.style.marginTop = "12px";
      rawTxt.style.width = "100%";
      morphGroup.appendChild(rawTxt);
    }
    mCard.appendChild(morphGroup);
  } else {
    const noM = document.createElement("div");
    noM.textContent = "Analysis unavailable.";
    mCard.appendChild(noM);
  }
  morphContent.appendChild(mCard);

  // Build Literary Content
  const litArr = data.literary_context || [];
  if (litArr.length > 0) {
    litArr.forEach((item, idx) => {
      const lCard = document.createElement("div");
      lCard.className = "sol-meaning-card";
      
      const lHead = document.createElement("div");
      lHead.className = "sol-card-header";
      lHead.innerHTML = `${ICONS.document} Literary Evidence (${idx + 1} of ${litArr.length})`;
      lCard.appendChild(lHead);
      
      const v = document.createElement("div");
      v.className = "sol-lit-verse";
      v.textContent = item.passage;
      lCard.appendChild(v);
      
      const meta = document.createElement("div");
      meta.className = "sol-lit-source";
      meta.innerHTML = `<span>— ${item.work}${item.verse_number ? ", " + item.verse_number : ""}</span>`;
      
      const link = document.createElement("button");
      link.className = "sol-view-context-btn";
      link.innerHTML = `View in context ${ICONS.arrowRight}`;
      meta.appendChild(link);
      
      lCard.appendChild(meta);
      litContent.appendChild(lCard);
    });
  } else {
    litContent.textContent = "No classical literature references found.";
    litContent.style.color = "var(--sol-text-muted)";
  }

  body.appendChild(meanContent);
  body.appendChild(litContent);
  body.appendChild(morphContent);

  // Actions Bar
  const actions = document.createElement("div");
  actions.className = "sol-bottom-actions";
  
  const a1 = document.createElement("button");
  a1.className = "sol-action-btn";
  a1.innerHTML = `${ICONS.list} Explore`;
  a1.onclick = () => {
    chrome.runtime.sendMessage({ action: "OPEN_WEB_APP", query: queryText });
  };
  
  const a3 = document.createElement("button");
  a3.className = "sol-action-btn";
  a3.innerHTML = `${ICONS.heart} Save word`;
  
  actions.appendChild(a1);
  actions.appendChild(a3);
  
  const quote = document.createElement("div");
  quote.className = "sol-footer-quote";
  quote.innerHTML = `<div class="sol-lotus">${ICONS.lotus}</div>“ஒரு சொல் — ஓர் உலகம்.”<br><span style="font-size:10px;color:var(--sol-text-muted)">சொல் AI</span>`;
  
  body.appendChild(actions);
  body.appendChild(quote);
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    renderDefaultPanel,
    renderLoadingPanel,
    renderErrorPanel,
    renderResultPanel,
    closePanel,
    clearWatchdog,
    getWatchdog: () => loadingWatchdog,
    getActiveWatchdogQuery: () => activeWatchdogQuery,
    getShadowRoot,
  };
}
