/**
 * Automated Extension Reliability Test Suite (Part H).
 *
 * Verifies:
 * Test A: Normal result: loading -> result, watchdog cleared.
 * Test B: Backend error: loading -> error, no infinite spinner, watchdog cleared.
 * Test C: Timeout: loading -> watchdog triggers at 25s -> timeout error -> retry button available.
 * Test D: New query while old query is loading: old watchdog must not overwrite the new query's UI.
 */

const path = require("path");
const assert = require("assert");

// Setup minimal mock DOM
function createMockElement(tag) {
  const el = {
    tagName: tag.toUpperCase(),
    children: [],
    style: {},
    className: "",
    _textContent: "",
    _innerHTML: "",
    parent: null,
    get textContent() {
      if (this.children.length > 0) {
        return this.children.map((c) => c.textContent || "").join("");
      }
      return this._textContent || "";
    },
    set textContent(v) {
      this._textContent = v;
      this.children = [];
    },
    get innerHTML() {
      return this._innerHTML || "";
    },
    set innerHTML(v) {
      this._innerHTML = v;
      if (v === "") {
        this.children = [];
      }
    },
    classList: {
      add: (c) => { el.className = (el.className ? el.className + " " : "") + c; },
      remove: (c) => { el.className = (el.className || "").replace(c, "").trim(); },
      contains: (c) => (el.className || "").split(/\s+/).includes(c),
    },
    setAttribute: (k, v) => { el[k] = v; },
    appendChild: (c) => {
      c.parent = el;
      el.children.push(c);
      return c;
    },
    remove: () => {
      if (el.parent) {
        el.parent.children = el.parent.children.filter((c) => c !== el);
      }
    },
    querySelector: (sel) => {
      for (const child of el.children) {
        if (sel.startsWith("#") && child.id === sel.slice(1)) return child;
        if (sel.startsWith(".") && child.classList && child.classList.contains(sel.slice(1))) return child;
        if (child.querySelector) {
          const found = child.querySelector(sel);
          if (found) return found;
        }
      }
      return null;
    },
    querySelectorAll: (sel) => [],
    attachShadow: () => {
      const shadow = createMockElement("shadow-root");
      shadow.parent = el;
      el.shadowRoot = shadow;
      return shadow;
    },
  };
  return el;
}

function createMockTextNode(text) {
  return {
    nodeType: 3,
    textContent: String(text),
    children: [],
  };
}

global.document = {
  createElement: createMockElement,
  createTextNode: createMockTextNode,
  body: createMockElement("body"),
};

let messageListeners = [];
global.chrome = {
  runtime: {
    getURL: (p) => p,
    sendMessage: (msg, cb) => {},
    onMessage: {
      addListener: (fn) => { messageListeners.push(fn); },
    },
  },
};

// Require content script
const content = require("../extension/content/content.js");

function dispatchMessage(msg) {
  for (const listener of messageListeners) {
    listener(msg, {}, () => {});
  }
}

// -----------------------------------------------------------------------------
// Test A: Normal result -> loading -> result -> watchdog cleared
// -----------------------------------------------------------------------------
function testA_normalResult() {
  console.log("Running Test A: Normal result...");
  dispatchMessage({ action: "SHOW_LOADING", query: "கால்" });
  assert.strictEqual(content.getActiveWatchdogQuery(), "கால்", "Watchdog query must be set to 'கால்'");
  assert.ok(content.getWatchdog() !== null, "Watchdog timer must be active");

  const mockResult = {
    lemma: "கால்",
    meaning: "விலங்குகளின் உறுப்பு",
    morphology: { pos: "noun", analysis_type: "core" },
    literary_context: [{ work: "குறுந்தொகை", passage: "கால் பொழி..." }],
  };

  dispatchMessage({ action: "SHOW_RESULT", query: "கால்", result: mockResult });
  assert.strictEqual(content.getWatchdog(), null, "Watchdog must be cleared on SHOW_RESULT");
  assert.strictEqual(content.getActiveWatchdogQuery(), "", "Active watchdog query must be reset");

  const shadow = content.getShadowRoot();
  const wordTitle = shadow.querySelector(".sol-word-title");
  assert.ok(wordTitle, "Result panel must render word title");
  assert.strictEqual(wordTitle.textContent, "கால்");
  console.log("  [PASS] Test A: Loading -> Result transition cleared watchdog cleanly.");
}

// -----------------------------------------------------------------------------
// Test B: Backend error -> loading -> error -> no infinite spinner
// -----------------------------------------------------------------------------
function testB_backendError() {
  console.log("Running Test B: Backend error...");
  dispatchMessage({ action: "SHOW_LOADING", query: "மரங்களில்" });
  assert.ok(content.getWatchdog() !== null, "Watchdog timer must be active");

  dispatchMessage({ action: "SHOW_ERROR", query: "மரங்களில்", error: "Backend server offline", canRetry: true });
  assert.strictEqual(content.getWatchdog(), null, "Watchdog must be cleared on SHOW_ERROR");

  const shadow = content.getShadowRoot();
  const title = shadow.querySelector(".sol-status-title");
  assert.ok(title, "Error panel must render status title");
  const retryBtn = shadow.querySelector(".sol-status-btn");
  assert.ok(retryBtn, "Error panel must provide retry button");
  console.log("  [PASS] Test B: Error received, watchdog cleared, retry button available.");
}

// -----------------------------------------------------------------------------
// Test C: Timeout -> loading -> watchdog triggers at 25s -> retry available
// -----------------------------------------------------------------------------
async function testC_watchdogTimeout() {
  console.log("Running Test C: Watchdog timeout fallback...");

  const realSetTimeout = global.setTimeout;
  let timerFn = null;
  global.setTimeout = (fn, delay) => {
    timerFn = fn;
    return 999;
  };

  try {
    dispatchMessage({ action: "SHOW_LOADING", query: "நீண்டதேடல்" });
    assert.ok(timerFn !== null, "Watchdog timer function was registered");

    // Simulate 25-second timeout firing
    timerFn();

    // Verify error panel rendered
    const shadow = content.getShadowRoot();
    const desc = shadow.querySelector(".sol-status-desc");
    assert.ok(desc, "Status desc must exist on timeout");
    assert.ok(
      desc.textContent.includes("SOL AI took too long to respond"),
      `Unexpected desc textContent: '${desc.textContent}'`
    );
    assert.strictEqual(content.getWatchdog(), null, "Watchdog must be null after firing");
    const retryBtn = shadow.querySelector(".sol-status-btn");
    assert.ok(retryBtn, "Retry button must be available after timeout");
    console.log("  [PASS] Test C: Watchdog timed out and recovered gracefully with retry button.");
  } finally {
    global.setTimeout = realSetTimeout;
  }
}

// -----------------------------------------------------------------------------
// Test D: New query while old query is loading: old timer cannot overwrite new UI
// -----------------------------------------------------------------------------
function testD_newQueryCancelsOldWatchdog() {
  console.log("Running Test D: New query cancels old watchdog...");

  const realSetTimeout = global.setTimeout;
  const realClearTimeout = global.clearTimeout;
  let registeredTimers = [];
  let clearedTimers = [];

  global.setTimeout = (fn, delay) => {
    const id = registeredTimers.length + 1;
    registeredTimers.push({ id, fn, delay });
    return id;
  };
  global.clearTimeout = (id) => {
    clearedTimers.push(id);
  };

  try {
    // 1. First query started
    dispatchMessage({ action: "SHOW_LOADING", query: "சொல்1" });
    const timer1 = registeredTimers[0];
    assert.strictEqual(content.getActiveWatchdogQuery(), "சொல்1");

    // 2. Second query arrives before timer1 fires
    dispatchMessage({ action: "SHOW_LOADING", query: "சொல்2" });
    assert.strictEqual(content.getActiveWatchdogQuery(), "சொல்2");
    assert.ok(clearedTimers.includes(timer1.id), "Timer 1 must be explicitly cleared by clearTimeout");

    // 3. If timer1 somehow fired late, verify it does NOT overwrite சொல்2
    timer1.fn();
    assert.strictEqual(content.getActiveWatchdogQuery(), "சொல்2", "Stale timer must NOT clear or overwrite active query 2");

    console.log("  [PASS] Test D: Old query watchdog cleanly superseded by new query.");
  } finally {
    global.setTimeout = realSetTimeout;
    global.clearTimeout = realClearTimeout;
  }
}

// -----------------------------------------------------------------------------
// Test E: Multiple meanings displayed as bullet points instead of semicolon
// -----------------------------------------------------------------------------
function testE_multipleMeaningsBullets() {
  console.log("Running Test E: Multiple meanings bullet points rendering...");
  const mockResult = {
    lemma: "கால்",
    meaning: "மாந்தர்கள் உட்பட விலங்குகளின் ஓர் உடல் உறுப்பு; இது தரையில் ஊன்றி நடக்கவோ, நகரவோ பயன்படுவது.",
    morphology: { pos: "noun", analysis_type: "core" },
    literary_context: [],
  };

  dispatchMessage({ action: "SHOW_RESULT", query: "கால்", result: mockResult });
  const shadow = content.getShadowRoot();
  const bulletsList = shadow.querySelector(".sol-meaning-bullets");
  assert.ok(bulletsList, "Must render .sol-meaning-bullets list when multiple senses exist");
  assert.strictEqual(bulletsList.children.length, 2, "Must contain exactly 2 bullet items");
  assert.strictEqual(bulletsList.children[0].tagName, "LI", "First item must be an LI");
  assert.strictEqual(bulletsList.children[0].textContent, "மாந்தர்கள் உட்பட விலங்குகளின் ஓர் உடல் உறுப்பு");
  assert.strictEqual(bulletsList.children[1].tagName, "LI", "Second item must be an LI");
  assert.strictEqual(bulletsList.children[1].textContent, "இது தரையில் ஊன்றி நடக்கவோ, நகரவோ பயன்படுவது.");

  // Also test single meaning fallback
  const singleResult = {
    lemma: "மரம்",
    meaning: "தாவர வகை",
    morphology: { pos: "noun", analysis_type: "core" },
    literary_context: [],
  };
  dispatchMessage({ action: "SHOW_RESULT", query: "மரம்", result: singleResult });
  const singleShadow = content.getShadowRoot();
  const singleBullets = singleShadow.querySelector(".sol-meaning-bullets");
  assert.strictEqual(singleBullets, null, "Must not render bullet list for single meaning");
  const summary = singleShadow.querySelector(".sol-meaning-summary");
  assert.ok(summary, "Must render .sol-meaning-summary for single meaning");
  assert.strictEqual(summary.textContent, "தாவர வகை");

  console.log("  [PASS] Test E: Multiple meanings rendered cleanly as bullet items.");
}

// -----------------------------------------------------------------------------
// Test F: Audio button removal verified
// -----------------------------------------------------------------------------
function testF_audioRemovalVerified() {
  console.log("Running Test F: Audio removal...");
  const mockResult = {
    lemma: "கால்",
    meaning: "உறுப்பு",
    morphology: { pos: "noun" },
    literary_context: [],
  };
  dispatchMessage({ action: "SHOW_RESULT", query: "கால்", result: mockResult });
  const shadow = content.getShadowRoot();
  const heroTop = shadow.querySelector(".sol-hero-top");
  assert.ok(heroTop, "Must render heroTop");
  const audioButtons = heroTop.children.filter((c) => c.innerHTML && c.innerHTML.includes("<polygon"));
  assert.strictEqual(audioButtons.length, 0, "Hero top must contain zero audio buttons/icons");
  console.log("  [PASS] Test F: Audio button cleanly removed from Extension.");
}

// -----------------------------------------------------------------------------
// Test G: Structured senses direct consumption
// -----------------------------------------------------------------------------
function testG_structuredSensesConsumption() {
  console.log("Running Test G: Structured senses...");
  const mockResult = {
    lemma: "கால்",
    senses: [
      { sense_number: 1, title: "உடல் உறுப்பு", raw_text: "உடல் உறுப்பு" },
      { sense_number: 2, title: "நான்கில் ஒரு பங்கு", raw_text: "நான்கில் ஒரு பங்கு" },
      { sense_number: 3, title: "காற்று", raw_text: "காற்று" },
    ],
    morphology: { pos: "noun" },
    literary_context: [],
  };
  dispatchMessage({ action: "SHOW_RESULT", query: "கால்", result: mockResult });
  const shadow = content.getShadowRoot();
  const bulletsList = shadow.querySelector(".sol-meaning-bullets");
  assert.ok(bulletsList, "Must render .sol-meaning-bullets list for structured senses");
  assert.strictEqual(bulletsList.children.length, 2, "Must preserve exactly 2 senses");
  assert.strictEqual(bulletsList.children[0].textContent, "உடல் உறுப்பு");
  assert.strictEqual(bulletsList.children[1].textContent, "நான்கில் ஒரு பங்கு");
  console.log("  [PASS] Test G: Structured senses consumed directly with 2 senses preserved.");
}

// -----------------------------------------------------------------------------
// Test H: Related words rendering max 3
// -----------------------------------------------------------------------------
function testH_relatedWordsMax3() {
  console.log("Running Test H: Related words max 3...");
  const mockResult = {
    lemma: "மரம்",
    senses: [{ sense_number: 1, title: "தாவர வகை", raw_text: "தாவர வகை" }],
    related_words: ["செடி", "கொடி", "தரு", "மரம்2", "மரங்கள்"],
    morphology: { pos: "noun" },
    literary_context: [],
  };
  dispatchMessage({ action: "SHOW_RESULT", query: "மரம்", result: mockResult });
  const shadow = content.getShadowRoot();
  const panel = shadow.querySelector("#sol-ai-panel");
  assert.ok(panel, "Must render panel");
  const body = panel.children.find((c) => c.className === "sol-body");
  assert.ok(body, "Must render body");
  const meanContent = body.children.find((c) => c.className && c.className.includes("sol-tab-content"));
  assert.ok(meanContent, "Must render meanContent");
  const relCard = meanContent.children.find((c) => {
    return c.children && c.children[0] && c.children[0].innerHTML && c.children[0].innerHTML.includes("Related Words");
  });
  assert.ok(relCard, "Must render Related Words card when related_words exist");
  const chipsGroup = relCard.children[1];
  assert.strictEqual(chipsGroup.children.length, 3, "Must display at most 3 related words");
  assert.strictEqual(chipsGroup.children[0].textContent, "செடி");
  assert.strictEqual(chipsGroup.children[1].textContent, "கொடி");
  assert.strictEqual(chipsGroup.children[2].textContent, "தரு");
  console.log("  [PASS] Test H: Related words displayed cleanly with maximum 3 items.");
}

function testI_structuredMorphologyPills() {
  console.log("Running Test I: Structured morphology pills rendering...");
  const mockResult = {
    lemma: "மரம்",
    senses: [{ sense_number: 1, title: "தாவர வகை", raw_text: "தாவர வகை" }],
    morphology: {
      pos: "noun",
      case: "Locative",
      number: "Plural",
      analysis_type: "core",
      raw_morphology: "noun+pl+loc",
    },
    literary_context: [],
  };
  dispatchMessage({ action: "SHOW_RESULT", query: "மரங்களில்", result: mockResult });
  const shadow = content.getShadowRoot();
  const panel = shadow.querySelector("#sol-ai-panel");
  const body = panel.children.find((c) => c.className === "sol-body");
  const tabContents = body.children.filter((c) => c.className && c.className.includes("sol-tab-content"));
  const morphContent = tabContents[2]; // 3rd tab: Morphology
  assert.ok(morphContent, "Must render morphology tab content");
  const mCard = morphContent.children[0];
  assert.ok(mCard, "Must render morphology card");
  const morphGroup = mCard.children[1];
  assert.ok(morphGroup, "Must render morphGroup");
  const pillsText = morphGroup.children.map((c) => c.textContent);
  assert.ok(pillsText.includes("POS: noun"), "Must render POS pill");
  assert.ok(pillsText.includes("CORE"), "Must render analysis type pill");
  assert.ok(pillsText.includes("Case: Locative"), "Must render Case pill");
  assert.ok(pillsText.includes("Number: Plural"), "Must render Number pill");
  assert.ok(pillsText.includes("noun+pl+loc"), "Must render raw morphology string");
  console.log("  [PASS] Test I: Structured morphology pills rendered cleanly.");
}

function testJ_structuredLiteraryContextAndExpansion() {
  console.log("Running Test J: Structured literary context snippet and expansion toggle...");
  const mockResult = {
    lemma: "அறம்",
    query: "அறம்",
    senses: [{ sense_number: 1, title: "நற்செயல்", raw_text: "நற்செயல்" }],
    morphology: { pos: "noun" },
    literary_context: [
      {
        work: "திருக்குறள்",
        verse_number: "31",
        author: "திருவள்ளுவர்",
        passage: "சிறப்பீனும் செல்வமும் ஈனும் அறத்தினூங்கு\nஆக்கமும் எவனோ உயிர்க்கு.",
        matched_line: "சிறப்பீனும் செல்வமும் ஈனும் அறத்தினூங்கு",
        snippet: "சிறப்பீனும் செல்வமும் ஈனும் அறத்தினூங்கு",
        highlight_offsets: [{ start: 27, end: 31 }],
        passage_highlight_offsets: [{ start: 27, end: 31 }],
        is_featured: true,
        can_expand: true,
      },
      {
        work: "ஆத்திசூடி",
        verse_number: "1",
        author: "ஔவையார்",
        passage: "அறம் செய விரும்பு.",
        matched_line: "அறம் செய விரும்பு.",
        snippet: "அறம் செய விரும்பு.",
        highlight_offsets: [{ start: 0, end: 4 }],
        passage_highlight_offsets: [{ start: 0, end: 4 }],
        is_featured: false,
        can_expand: false,
      },
    ],
  };

  dispatchMessage({ action: "SHOW_RESULT", query: "அறம்", result: mockResult });
  const shadow = content.getShadowRoot();
  const panel = shadow.querySelector("#sol-ai-panel");
  const body = panel.children.find((c) => c.className === "sol-body");
  const tabContents = body.children.filter((c) => c.className && c.className.includes("sol-tab-content"));
  const litContent = tabContents[1]; // 2nd tab: Literary Context
  assert.ok(litContent, "Must render literary context tab");
  assert.strictEqual(litContent.children.length, 2, "Must render 2 literary cards");

  // First card: expandable
  const card1 = litContent.children[0];
  const verse1 = card1.querySelector(".sol-lit-verse");
  assert.ok(verse1, "Card 1 must contain .sol-lit-verse");
  assert.strictEqual(verse1.textContent, "சிறப்பீனும் செல்வமும் ஈனும் அறத்தினூங்கு", "Initial render must display snippet, not full passage");

  // Verify highlight span in Card 1
  const span1 = verse1.children.find((c) => c.tagName === "SPAN");
  assert.ok(span1, "Must render highlight span");
  assert.strictEqual(span1.style.color, "#e5c158", "Highlight span must have gold color");

  // Verify expand button exists and displays "View more"
  const expandBtn1 = card1.querySelector(".sol-lit-expand-btn");
  assert.ok(expandBtn1, "Card 1 must have .sol-lit-expand-btn when can_expand is true");
  assert.strictEqual(expandBtn1.textContent, "View more", "Initial button text must be 'View more'");

  // Click expand button to expand
  expandBtn1.onclick();
  assert.strictEqual(verse1.textContent, "சிறப்பீனும் செல்வமும் ஈனும் அறத்தினூங்கு\nஆக்கமும் எவனோ உயிர்க்கு.", "Verse must expand to full passage");
  assert.strictEqual(expandBtn1.textContent, "Show less", "Button text must toggle to 'Show less'");

  // Click again to collapse
  expandBtn1.onclick();
  assert.strictEqual(verse1.textContent, "சிறப்பீனும் செல்வமும் ஈனும் அறத்தினூங்கு", "Verse must collapse back to snippet");
  assert.strictEqual(expandBtn1.textContent, "View more", "Button text must toggle back to 'View more'");

  // Second card: non-expandable (can_expand is false)
  const card2 = litContent.children[1];
  const verse2 = card2.querySelector(".sol-lit-verse");
  assert.ok(verse2, "Card 2 must contain .sol-lit-verse");
  assert.strictEqual(verse2.textContent, "அறம் செய விரும்பு.");
  const expandBtn2 = card2.querySelector(".sol-lit-expand-btn");
  assert.strictEqual(expandBtn2, null, "Card 2 must NOT render expand button when can_expand is false");

  console.log("  [PASS] Test J: Structured literary context snippet and expansion toggle verified.");
}

async function runAll() {
  testA_normalResult();
  testB_backendError();
  await testC_watchdogTimeout();
  testD_newQueryCancelsOldWatchdog();
  testE_multipleMeaningsBullets();
  testF_audioRemovalVerified();
  testG_structuredSensesConsumption();
  testH_relatedWordsMax3();
  testI_structuredMorphologyPills();
  testJ_structuredLiteraryContextAndExpansion();
  console.log("\nALL EXTENSION RELIABILITY TESTS PASSED (10/10)!");
}

runAll().catch((err) => {
  console.error("Test failure:", err);
  process.exit(1);
});
