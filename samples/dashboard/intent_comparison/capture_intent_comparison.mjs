#!/usr/bin/env node

import {
  access,
  mkdir,
  readFile,
  readdir,
  stat,
  writeFile,
} from "node:fs/promises";
import { existsSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const VIEWPORT = Object.freeze({ width: 1440, height: 1200 });
const DEVICE_SCALE_FACTOR = 1;
const PRIMARY_LANGUAGE = "ja";
const DIRECTIONS = Object.freeze([
  {
    id: "A",
    slug: "priority-review-console",
    screenshot: "priority-review-console.png",
  },
  {
    id: "B",
    slug: "narrative-status-brief",
    screenshot: "narrative-status-brief.png",
  },
  {
    id: "C",
    slug: "lane-project-matrix",
    screenshot: "lane-project-matrix.png",
  },
]);

const scriptPath = fileURLToPath(import.meta.url);
const artifactDirectory = dirname(scriptPath);

function parseArguments(argv) {
  const options = {};
  const names = new Map([
    ["--playwright-core", "playwrightCore"],
    ["--browser", "browser"],
    ["--html", "html"],
    ["--manifest", "manifest"],
    ["--readback", "readback"],
  ]);

  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    if (argument === "--help" || argument === "-h") {
      options.help = true;
      continue;
    }
    const key = names.get(argument);
    if (!key) {
      throw new Error(`Unknown argument: ${argument}`);
    }
    const value = argv[index + 1];
    if (!value || value.startsWith("--")) {
      throw new Error(`Missing value for ${argument}`);
    }
    options[key] = value;
    index += 1;
  }
  return options;
}

function printHelp() {
  console.log(`Usage:
  node samples/dashboard/intent_comparison/capture_intent_comparison.mjs [options]

Options:
  --playwright-core PATH  Playwright Core package directory or index.mjs
  --browser PATH          Edge or Chrome executable
  --html PATH             Comparison HTML artifact
  --manifest PATH         Manifest JSON to update
  --readback PATH         Readback JSON to update

Environment overrides:
  PLAYWRIGHT_CORE_ENTRY, CHROMIUM_EXECUTABLE

The capture contract is fixed at 1440x1200 CSS pixels, DPR 1, and Japanese.`);
}

async function isFile(path) {
  try {
    return (await stat(path)).isFile();
  } catch {
    return false;
  }
}

async function normalizePlaywrightEntry(candidate) {
  if (!candidate) {
    return null;
  }
  const absolute = resolve(candidate);
  try {
    const details = await stat(absolute);
    if (details.isDirectory()) {
      const entry = join(absolute, "index.mjs");
      return (await isFile(entry)) ? entry : null;
    }
    return details.isFile() ? absolute : null;
  } catch {
    return null;
  }
}

function versionParts(value) {
  return value.split(/[^0-9]+/u).filter(Boolean).map(Number);
}

function compareVersionsDescending(left, right) {
  const leftParts = versionParts(left);
  const rightParts = versionParts(right);
  const length = Math.max(leftParts.length, rightParts.length);
  for (let index = 0; index < length; index += 1) {
    const difference = (rightParts[index] || 0) - (leftParts[index] || 0);
    if (difference !== 0) {
      return difference;
    }
  }
  return right.localeCompare(left);
}

async function discoverPlaywrightEntry(explicit) {
  const requested = explicit || process.env.PLAYWRIGHT_CORE_ENTRY;
  if (requested) {
    const entry = await normalizePlaywrightEntry(requested);
    if (!entry) {
      throw new Error(`Playwright Core entry does not exist: ${requested}`);
    }
    return entry;
  }

  const base = process.env.LOCALAPPDATA
    ? join(process.env.LOCALAPPDATA, "ms-playwright-go")
    : null;
  if (base) {
    let versions = [];
    try {
      versions = (await readdir(base, { withFileTypes: true }))
        .filter((entry) => entry.isDirectory())
        .map((entry) => entry.name)
        .sort(compareVersionsDescending);
    } catch {
      versions = [];
    }
    for (const version of versions) {
      const entry = join(base, version, "package", "index.mjs");
      if (await isFile(entry)) {
        return entry;
      }
    }
  }

  throw new Error(
    "No installed Playwright Core entry was found. Set PLAYWRIGHT_CORE_ENTRY or use --playwright-core; do not install a new dependency for this slice.",
  );
}

async function discoverBrowserExecutable(explicit) {
  const candidates = [
    explicit,
    process.env.CHROMIUM_EXECUTABLE,
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    process.env.LOCALAPPDATA
      ? join(process.env.LOCALAPPDATA, "Google", "Chrome", "Application", "chrome.exe")
      : null,
  ].filter(Boolean);

  for (const candidate of candidates) {
    const absolute = resolve(candidate);
    if (await isFile(absolute)) {
      return absolute;
    }
  }
  throw new Error(
    "No installed Edge or Chrome executable was found. Set CHROMIUM_EXECUTABLE or use --browser; do not install a new browser for this slice.",
  );
}

async function readJson(path) {
  return JSON.parse(await readFile(path, "utf8"));
}

async function writeJson(path, value) {
  await writeFile(path, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

async function settlePage(page) {
  await page.evaluate(async () => {
    if (document.fonts?.ready) {
      await document.fonts.ready;
    }
    await new Promise((resolveFrame) => {
      requestAnimationFrame(() => requestAnimationFrame(resolveFrame));
    });
  });
}

function directionSelector(slug) {
  return `button[data-direction="${slug}"]`;
}

function languageSelector(language) {
  return `button[data-language="${language}"]`;
}

async function requireUniqueVisibleControl(page, selector, label) {
  const controls = page.locator(selector);
  const count = await controls.count();
  if (count !== 1) {
    throw new Error(`${label} must match exactly one control; found ${count}: ${selector}`);
  }
  const control = controls.first();
  await control.waitFor({ state: "visible" });
  return control;
}

async function directionState(page, expected) {
  return page.evaluate((slug) => {
    const controls = Array.from(document.querySelectorAll("button[data-direction]"));
    const panels = Array.from(document.querySelectorAll("[data-direction-panel]"));
    const isSelected = (element) =>
      element.getAttribute("aria-selected") === "true"
      || element.getAttribute("aria-pressed") === "true";
    const isVisible = (element) => {
      if (element.hidden || element.getAttribute("aria-hidden") === "true") {
        return false;
      }
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      return style.display !== "none"
        && style.visibility !== "hidden"
        && rect.width > 0
        && rect.height > 0;
    };
    const selected = controls.filter(isSelected).map((element) => element.dataset.direction);
    const visible = panels.filter(isVisible).map((element) => element.dataset.directionPanel);
    return {
      expected: slug,
      selected,
      visible,
      document_direction: document.documentElement.dataset.direction || null,
      pass: selected.length === 1
        && selected[0] === slug
        && visible.length === 1
        && visible[0] === slug,
    };
  }, expected);
}

async function languageState(page, expected) {
  return page.evaluate((language) => {
    const controls = Array.from(document.querySelectorAll("button[data-language]"));
    const selected = controls
      .filter((element) =>
        element.getAttribute("aria-selected") === "true"
        || element.getAttribute("aria-pressed") === "true")
      .map((element) => element.dataset.language);
    const documentLanguage = (
      document.documentElement.dataset.language
      || document.documentElement.lang
      || ""
    ).toLowerCase().split("-")[0];
    return {
      expected: language,
      selected,
      document_language: documentLanguage || null,
      pass: selected.length === 1
        && selected[0] === language
        && documentLanguage === language,
    };
  }, expected);
}

async function waitForDirection(page, slug) {
  await page.waitForFunction((expected) => {
    const control = document.querySelector(`button[data-direction="${expected}"]`);
    const panel = document.querySelector(`[data-direction-panel="${expected}"]`);
    if (!control || !panel) {
      return false;
    }
    const selected = control.getAttribute("aria-selected") === "true"
      || control.getAttribute("aria-pressed") === "true";
    const style = getComputedStyle(panel);
    const rect = panel.getBoundingClientRect();
    const visible = !panel.hidden
      && panel.getAttribute("aria-hidden") !== "true"
      && style.display !== "none"
      && style.visibility !== "hidden"
      && rect.width > 0
      && rect.height > 0;
    return selected && visible;
  }, slug);
  await settlePage(page);
}

async function activateDirection(page, slug) {
  const control = await requireUniqueVisibleControl(
    page,
    directionSelector(slug),
    `Direction ${slug}`,
  );
  await control.click();
  await waitForDirection(page, slug);
  const state = await directionState(page, slug);
  if (!state.pass) {
    throw new Error(`Direction selected-state failed: ${JSON.stringify(state)}`);
  }
  return state;
}

async function waitForLanguage(page, language) {
  await page.waitForFunction((expected) => {
    const control = document.querySelector(`button[data-language="${expected}"]`);
    if (!control) {
      return false;
    }
    const selected = control.getAttribute("aria-selected") === "true"
      || control.getAttribute("aria-pressed") === "true";
    const current = (
      document.documentElement.dataset.language
      || document.documentElement.lang
      || ""
    ).toLowerCase().split("-")[0];
    return selected && current === expected;
  }, language);
  await settlePage(page);
}

async function activateLanguage(page, language) {
  const control = await requireUniqueVisibleControl(
    page,
    languageSelector(language),
    `Language ${language}`,
  );
  await control.click();
  await waitForLanguage(page, language);
  const state = await languageState(page, language);
  if (!state.pass) {
    throw new Error(`Language selected-state failed: ${JSON.stringify(state)}`);
  }
  return state;
}

async function measureOverflow(page, direction, language) {
  return page.evaluate(({ currentDirection, currentLanguage }) => {
    const tolerance = 1;
    const selectorFor = (element) => {
      if (element.id) {
        return `${element.tagName.toLowerCase()}#${element.id}`;
      }
      const dataHook = [
        "data-semantic-key",
        "data-direction-panel",
        "data-repo-path",
      ].find((name) => element.hasAttribute(name));
      if (dataHook) {
        return `${element.tagName.toLowerCase()}[${dataHook}="${element.getAttribute(dataHook)}"]`;
      }
      const classes = Array.from(element.classList).slice(0, 2);
      return `${element.tagName.toLowerCase()}${classes.map((name) => `.${name}`).join("")}`;
    };
    const isVisible = (element) => {
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      return !element.hidden
        && element.getAttribute("aria-hidden") !== "true"
        && style.display !== "none"
        && style.visibility !== "hidden"
        && rect.width > 0
        && rect.height > 0;
    };
    const hasHorizontalContainment = (element) => {
      for (let ancestor = element.parentElement; ancestor && ancestor !== document.body; ancestor = ancestor.parentElement) {
        const style = getComputedStyle(ancestor);
        if (/^(auto|scroll|hidden|clip)$/u.test(style.overflowX)
            && ancestor.scrollWidth > ancestor.clientWidth + tolerance) {
          return true;
        }
      }
      return false;
    };

    const findings = [];
    if (document.documentElement.scrollWidth > innerWidth + tolerance) {
      findings.push({
        kind: "document_horizontal_overflow",
        selector: "html",
        excess_px: document.documentElement.scrollWidth - innerWidth,
      });
    }

    for (const element of document.querySelectorAll("body *")) {
      if (!isVisible(element) || element.closest("[data-overflow-allowed]")) {
        continue;
      }
      const style = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      if ((rect.left < -tolerance || rect.right > innerWidth + tolerance)
          && !hasHorizontalContainment(element)) {
        findings.push({
          kind: "viewport_overshoot",
          selector: selectorFor(element),
          left: Math.round(rect.left),
          right: Math.round(rect.right),
        });
      }
      const hasText = (element.innerText || "").trim().length > 0;
      if (hasText
          && /^(hidden|clip)$/u.test(style.overflowX)
          && element.scrollWidth > element.clientWidth + tolerance) {
        findings.push({
          kind: "clipped_horizontal_text",
          selector: selectorFor(element),
          excess_px: element.scrollWidth - element.clientWidth,
        });
      }
      if (hasText
          && /^(hidden|clip)$/u.test(style.overflowY)
          && element.scrollHeight > element.clientHeight + tolerance) {
        findings.push({
          kind: "clipped_vertical_text",
          selector: selectorFor(element),
          excess_px: element.scrollHeight - element.clientHeight,
        });
      }
    }

    const uniqueFindings = Array.from(
      new Map(findings.map((finding) => [JSON.stringify(finding), finding])).values(),
    );
    const documentHeight = document.documentElement.scrollHeight;
    return {
      direction: currentDirection,
      language: currentLanguage,
      viewport_width: innerWidth,
      viewport_height: innerHeight,
      document_width: document.documentElement.scrollWidth,
      document_height: documentHeight,
      scroll_burden_px: Math.max(0, documentHeight - innerHeight),
      viewport_count: Number((documentHeight / innerHeight).toFixed(2)),
      findings: uniqueFindings,
      pass: uniqueFindings.length === 0,
    };
  }, { currentDirection: direction, currentLanguage: language });
}

async function semanticParityReadback(page, direction, language, semanticContract) {
  return page.evaluate(({ currentDirection, currentLanguage, expectedContract }) => {
    const panel = document.querySelector(
      `[data-direction-panel="${currentDirection}"]:not([hidden])`,
    );
    if (!(panel instanceof HTMLElement)) {
      return {
        direction: currentDirection,
        language: currentLanguage,
        checked_key_count: 0,
        duplicate_keys: [],
        missing_keys: Object.keys(expectedContract),
        unexpected_keys: [],
        mismatches: [{ key: null, expected: "visible direction panel", actual: null }],
        pass: false,
      };
    }

    const items = Array.from(panel.querySelectorAll("[data-semantic-key]")).map((item) => ({
      key: item.dataset.semanticKey,
      value: item.querySelector(".semantic-value")?.textContent?.trim() ?? null,
    }));
    const counts = new Map();
    for (const item of items) {
      counts.set(item.key, (counts.get(item.key) || 0) + 1);
    }
    const expectedKeys = Object.keys(expectedContract);
    const actualKeys = Array.from(counts.keys());
    const duplicateKeys = actualKeys.filter((key) => counts.get(key) !== 1);
    const missingKeys = expectedKeys.filter((key) => !counts.has(key));
    const unexpectedKeys = actualKeys.filter((key) => !(key in expectedContract));
    const mismatches = items.flatMap((item) => {
      if (!(item.key in expectedContract)) {
        return [];
      }
      const expected = expectedContract[item.key]?.[currentLanguage];
      return item.value === expected
        ? []
        : [{ key: item.key, expected, actual: item.value }];
    });
    return {
      direction: currentDirection,
      language: currentLanguage,
      checked_key_count: items.length,
      duplicate_keys: duplicateKeys,
      missing_keys: missingKeys,
      unexpected_keys: unexpectedKeys,
      mismatches,
      pass: duplicateKeys.length === 0
        && missingKeys.length === 0
        && unexpectedKeys.length === 0
        && mismatches.length === 0,
    };
  }, {
    currentDirection: direction,
    currentLanguage: language,
    expectedContract: semanticContract,
  });
}

async function focusReadback(page) {
  return page.evaluate(() => {
    const element = document.activeElement;
    if (!(element instanceof HTMLElement)) {
      return { direction: null, language: null, visible: false };
    }
    const style = getComputedStyle(element);
    const hasOutline = style.outlineStyle !== "none"
      && Number.parseFloat(style.outlineWidth || "0") > 0;
    const hasShadow = style.boxShadow !== "none";
    return {
      direction: element.dataset.direction || null,
      language: element.dataset.language || null,
      focus_visible_match: element.matches(":focus-visible"),
      visual_indicator: hasOutline || hasShadow,
      visible: element.matches(":focus-visible") && (hasOutline || hasShadow),
    };
  });
}

async function keyboardDirectionStep(page, from, key, expected) {
  const control = await requireUniqueVisibleControl(
    page,
    directionSelector(from),
    `Keyboard direction ${from}`,
  );
  await control.focus();
  await page.keyboard.press(key);
  try {
    await waitForDirection(page, expected);
  } catch {
    // Record a failed step below instead of losing the rest of the readback.
  }
  const state = await directionState(page, expected);
  const focus = await focusReadback(page);
  return {
    from,
    key,
    expected,
    state,
    focus,
    pass: state.pass && focus.direction === expected && focus.visible,
  };
}

async function keyboardLanguageStep(page, from, key, expected) {
  const control = await requireUniqueVisibleControl(
    page,
    languageSelector(from),
    `Keyboard language ${from}`,
  );
  await control.focus();
  await page.keyboard.press(key);
  try {
    await waitForLanguage(page, expected);
  } catch {
    // Record a failed step below instead of losing the rest of the readback.
  }
  const state = await languageState(page, expected);
  const focus = await focusReadback(page);
  return {
    from,
    key,
    expected,
    state,
    focus,
    pass: state.pass && focus.language === expected && focus.visible,
  };
}

async function runKeyboardChecks(page) {
  await activateDirection(page, DIRECTIONS[0].slug);
  const directionSteps = [];
  directionSteps.push(await keyboardDirectionStep(
    page,
    DIRECTIONS[0].slug,
    "ArrowRight",
    DIRECTIONS[1].slug,
  ));
  directionSteps.push(await keyboardDirectionStep(
    page,
    DIRECTIONS[1].slug,
    "ArrowRight",
    DIRECTIONS[2].slug,
  ));
  directionSteps.push(await keyboardDirectionStep(
    page,
    DIRECTIONS[2].slug,
    "ArrowLeft",
    DIRECTIONS[1].slug,
  ));
  directionSteps.push(await keyboardDirectionStep(
    page,
    DIRECTIONS[1].slug,
    "End",
    DIRECTIONS[2].slug,
  ));
  directionSteps.push(await keyboardDirectionStep(
    page,
    DIRECTIONS[2].slug,
    "Home",
    DIRECTIONS[0].slug,
  ));

  await activateLanguage(page, "ja");
  const languageSteps = [];
  languageSteps.push(await keyboardLanguageStep(page, "ja", "ArrowRight", "en"));
  languageSteps.push(await keyboardLanguageStep(page, "en", "ArrowLeft", "ja"));

  return {
    direction_steps: directionSteps,
    language_steps: languageSteps,
    focus_state_visible: [...directionSteps, ...languageSteps]
      .every((step) => step.focus.visible),
    pass: [...directionSteps, ...languageSteps].every((step) => step.pass),
  };
}

async function inspectLinks(page) {
  const links = await page.evaluate(() => Array.from(document.querySelectorAll("a[href]"))
    .map((anchor) => {
      const target = new URL(anchor.href);
      const current = new URL(location.href);
      const fragment = target.hash;
      target.hash = "";
      current.hash = "";
      return {
        href_attribute: anchor.getAttribute("href"),
        resolved_href: anchor.href,
        text: (anchor.textContent || "").trim(),
        same_document_fragment: Boolean(fragment) && target.href === current.href,
        fragment_exists: fragment
          ? Boolean(document.getElementById(decodeURIComponent(fragment.slice(1))))
          : null,
      };
    }));
  const findings = [];
  const checked = [];

  for (const link of links) {
    const url = new URL(link.resolved_href);
    checked.push(link.href_attribute);
    if (url.protocol === "file:") {
      const path = fileURLToPath(new URL(url.href.split("#", 1)[0]));
      if (!existsSync(path)) {
        findings.push({
          kind: "missing_local_target",
          href: link.href_attribute,
          resolved_path: path,
        });
      }
      if (link.same_document_fragment && link.fragment_exists === false) {
        findings.push({
          kind: "missing_fragment_target",
          href: link.href_attribute,
          fragment: decodeURIComponent(url.hash.slice(1)),
        });
      }
    } else if (url.protocol === "javascript:") {
      findings.push({ kind: "unsupported_javascript_link", href: link.href_attribute });
    }
  }

  return {
    status: findings.length === 0 ? "pass" : "fail",
    count: findings.length,
    browser_checked_links: checked,
    browser_findings: findings,
  };
}

function pngDimensions(buffer) {
  const signature = "89504e470d0a1a0a";
  if (buffer.subarray(0, 8).toString("hex") !== signature) {
    throw new Error("Screenshot output is not a PNG file.");
  }
  return {
    width: buffer.readUInt32BE(16),
    height: buffer.readUInt32BE(20),
  };
}

function updateRemainingReviewDebt(existing, automatedChecksPass, humanVisualReviewStatus) {
  const debt = Array.isArray(existing) ? existing : [];
  const retained = debt.filter((item) =>
    !item.startsWith("Capture A, B, and C at ")
    && !item.startsWith("Inspect Japanese and English at the capture viewport")
    && !item.startsWith("Human visual review remains for "));
  if (automatedChecksPass && humanVisualReviewStatus !== "pass") {
    retained.unshift(
      "Human visual review remains for first-scan hierarchy, evidence proximity, Japanese typography, scroll burden, selected-state clarity, and card-grid regression.",
    );
  } else if (!automatedChecksPass) {
    retained.unshift(
      "Resolve failed browser capture, overflow, keyboard, link, or selected-state checks and rerun capture_intent_comparison.mjs.",
    );
  }
  return Array.from(new Set(retained));
}

async function playwrightVersion(entry) {
  try {
    const packageJson = await readJson(join(dirname(entry), "package.json"));
    return packageJson.version || "unknown";
  } catch {
    return "unknown";
  }
}

async function main() {
  const options = parseArguments(process.argv.slice(2));
  if (options.help) {
    printHelp();
    return;
  }

  const htmlPath = resolve(
    options.html
      || process.env.INTENT_COMPARISON_HTML
      || join(artifactDirectory, "verified_observation_surface_intent_pack.html"),
  );
  const manifestPath = resolve(
    options.manifest || join(artifactDirectory, "intent_comparison_manifest.json"),
  );
  const readbackPath = resolve(
    options.readback || join(artifactDirectory, "intent_comparison_readback.json"),
  );
  const fixturePath = join(artifactDirectory, "intent_comparison_fixture.json");
  const screenshotsDirectory = join(artifactDirectory, "screenshots");
  const playwrightEntry = await discoverPlaywrightEntry(options.playwrightCore);
  const browserExecutable = await discoverBrowserExecutable(options.browser);

  await Promise.all([
    access(htmlPath),
    access(manifestPath),
    access(readbackPath),
    access(fixturePath),
    mkdir(screenshotsDirectory, { recursive: true }),
  ]);

  const [{ chromium }, manifest, previousReadback, fixture] = await Promise.all([
    import(pathToFileURL(playwrightEntry).href),
    readJson(manifestPath),
    readJson(readbackPath),
    readJson(fixturePath),
  ]);

  const browser = await chromium.launch({
    headless: true,
    executablePath: browserExecutable,
  });
  const runtimeErrors = [];
  let finalReadback;
  let allChecksPass = false;

  try {
    const context = await browser.newContext({
      viewport: VIEWPORT,
      deviceScaleFactor: DEVICE_SCALE_FACTOR,
      locale: "ja-JP",
      timezoneId: "Asia/Tokyo",
      reducedMotion: "reduce",
    });
    const page = await context.newPage();
    page.on("pageerror", (error) => runtimeErrors.push(String(error)));
    page.on("console", (message) => {
      if (message.type() === "error") {
        runtimeErrors.push(`console.error: ${message.text()}`);
      }
    });
    await page.goto(pathToFileURL(htmlPath).href, { waitUntil: "load" });
    await settlePage(page);

    if ((await page.locator("button[data-direction]").count()) !== DIRECTIONS.length) {
      throw new Error(`Expected ${DIRECTIONS.length} direction controls.`);
    }
    if ((await page.locator("[data-direction-panel]").count()) !== DIRECTIONS.length) {
      throw new Error(`Expected ${DIRECTIONS.length} direction panels.`);
    }
    if ((await page.locator("button[data-language]").count()) !== 2) {
      throw new Error("Expected exactly two language controls.");
    }

    const overflowByLanguage = { ja: [], en: [] };
    const scrollBurden = { ja: {}, en: {} };
    const selectedStateChecks = [];
    const semanticParityChecks = [];
    const screenshotFiles = {};
    const screenshotDimensions = {};

    for (const direction of DIRECTIONS) {
      await activateDirection(page, direction.slug);
      for (const language of ["ja", "en"]) {
        await activateLanguage(page, language);
        selectedStateChecks.push({
          direction: await directionState(page, direction.slug),
          language: await languageState(page, language),
        });
        semanticParityChecks.push(await semanticParityReadback(
          page,
          direction.slug,
          language,
          fixture.semantic_contract,
        ));
        const overflow = await measureOverflow(page, direction.slug, language);
        overflowByLanguage[language].push(...overflow.findings.map((finding) => ({
          direction: direction.id,
          slug: direction.slug,
          ...finding,
        })));
        scrollBurden[language][direction.id] = {
          document_height: overflow.document_height,
          scroll_burden_px: overflow.scroll_burden_px,
          viewport_count: overflow.viewport_count,
        };

        if (language === PRIMARY_LANGUAGE) {
          const screenshotPath = join(screenshotsDirectory, direction.screenshot);
          const capturePage = await context.newPage();
          capturePage.on("pageerror", (error) => runtimeErrors.push(`capture ${direction.id}: ${String(error)}`));
          capturePage.on("console", (message) => {
            if (message.type() === "error") {
              runtimeErrors.push(`capture ${direction.id} console.error: ${message.text()}`);
            }
          });
          try {
            const captureUrl = pathToFileURL(htmlPath);
            captureUrl.searchParams.set("direction", direction.slug);
            captureUrl.searchParams.set("language", PRIMARY_LANGUAGE);
            await capturePage.goto(captureUrl.href, { waitUntil: "load" });
            await settlePage(capturePage);
            const captureDirectionState = await directionState(capturePage, direction.slug);
            const captureLanguageState = await languageState(capturePage, PRIMARY_LANGUAGE);
            if (!captureDirectionState.pass || !captureLanguageState.pass) {
              throw new Error(`Screenshot capture state mismatch for ${direction.id}.`);
            }
            const captureScrollY = await capturePage.evaluate(() => {
              if (document.activeElement instanceof HTMLElement) {
                document.activeElement.blur();
              }
              document.documentElement.scrollTop = 0;
              document.body.scrollTop = 0;
              window.scrollTo({ top: 0, left: 0, behavior: "instant" });
              return window.scrollY;
            });
            await settlePage(capturePage);
            const settledScrollY = await capturePage.evaluate(() => window.scrollY);
            if (captureScrollY !== 0 || settledScrollY !== 0) {
              throw new Error(
                `Screenshot capture must start at scrollY=0; ${direction.id} observed ${captureScrollY}/${settledScrollY}.`,
              );
            }
            const png = await capturePage.screenshot({
              path: screenshotPath,
              type: "png",
              clip: {
                x: 0,
                y: 0,
                width: VIEWPORT.width,
                height: VIEWPORT.height,
              },
              scale: "css",
            });
            screenshotFiles[direction.id] = screenshotPath;
            screenshotDimensions[direction.id] = pngDimensions(png);
          } finally {
            await capturePage.close();
          }
        }
      }
    }

    const keyboard = await runKeyboardChecks(page);
    const links = await inspectLinks(page);
    const dimensionsPass = Object.values(screenshotDimensions).every((dimensions) =>
      dimensions.width === VIEWPORT.width && dimensions.height === VIEWPORT.height);
    const overflowPass = overflowByLanguage.ja.length === 0
      && overflowByLanguage.en.length === 0;
    const selectedStatePass = selectedStateChecks.every((check) =>
      check.direction.pass && check.language.pass);
    const semanticParityPass = semanticParityChecks.every((check) => check.pass);
    const runtimePass = runtimeErrors.length === 0;
    allChecksPass = dimensionsPass
      && overflowPass
      && keyboard.pass
      && links.status === "pass"
      && selectedStatePass
      && semanticParityPass
      && runtimePass;

    finalReadback = {
      ...previousReadback,
      content_parity_across_directions: {
        status: semanticParityPass ? "pass" : "fail",
        directions: DIRECTIONS.map((direction) => direction.id),
        languages: ["ja", "en"],
        semantic_key_count_per_direction: Object.keys(fixture.semantic_contract).length,
        method: "Browser DOM readback activates every direction and language, then compares each rendered data-semantic-key value with the fixture semantic_contract.",
        checks: semanticParityChecks,
      },
      screenshot_dimensions: {
        status: dimensionsPass ? "pass" : "fail",
        width: VIEWPORT.width,
        height: VIEWPORT.height,
        device_scale_factor: DEVICE_SCALE_FACTOR,
        files: Object.fromEntries(DIRECTIONS.map((direction) => [
          direction.id,
          {
            path: manifest.screenshot_paths?.[direction.id]
              || screenshotFiles[direction.id],
            ...screenshotDimensions[direction.id],
          },
        ])),
      },
      overflow_findings: {
        ...previousReadback.overflow_findings,
        status: overflowPass ? "pass" : "fail",
        viewport: { ...VIEWPORT, device_scale_factor: DEVICE_SCALE_FACTOR },
        japanese: overflowByLanguage.ja,
        english: overflowByLanguage.en,
        scroll_burden: scrollBurden,
        method: "Browser DOM geometry across every direction in Japanese and English; intentional horizontal containers may opt out with data-overflow-allowed.",
      },
      broken_links: {
        ...previousReadback.broken_links,
        ...links,
      },
      keyboard_switch_check: {
        ...previousReadback.keyboard_switch_check,
        status: keyboard.pass ? "pass" : "fail",
        direction_keys: ["ArrowLeft", "ArrowRight", "Home", "End"],
        language_keys: ["ArrowLeft", "ArrowRight"],
        focus_state_visible: keyboard.focus_state_visible,
        direction_steps: keyboard.direction_steps,
        language_steps: keyboard.language_steps,
      },
      selected_state_check: {
        status: selectedStatePass ? "pass" : "fail",
        exactly_one_direction_and_language_selected: selectedStatePass,
        checks: selectedStateChecks,
      },
      browser_runtime_check: {
        status: runtimePass ? "pass" : "fail",
        errors: runtimeErrors,
        browser_version: browser.version(),
        playwright_core_version: await playwrightVersion(playwrightEntry),
      },
      remaining_review_debt: updateRemainingReviewDebt(
        previousReadback.remaining_review_debt,
        allChecksPass,
        previousReadback.human_visual_review?.status,
      ),
    };

    const portableCommand = "node samples/dashboard/intent_comparison/capture_intent_comparison.mjs";
    const updatedManifest = {
      ...manifest,
      capture: {
        ...manifest.capture,
        viewport: {
          width: VIEWPORT.width,
          height: VIEWPORT.height,
          device_scale_factor: DEVICE_SCALE_FACTOR,
        },
        language: PRIMARY_LANGUAGE,
        command: portableCommand,
        browser_version: browser.version(),
        playwright_core_version: await playwrightVersion(playwrightEntry),
        dependency_install_performed: false,
      },
      validation_commands: Array.from(new Set([
        ...(manifest.validation_commands || []),
        portableCommand,
      ])),
    };

    await Promise.all([
      writeJson(readbackPath, finalReadback),
      writeJson(manifestPath, updatedManifest),
    ]);
    await context.close();
  } finally {
    await browser.close();
  }

  const summary = {
    status: allChecksPass ? "pass" : "fail",
    viewport: VIEWPORT,
    language: PRIMARY_LANGUAGE,
    playwright_core_entry: playwrightEntry,
    browser_executable: browserExecutable,
    readback: readbackPath,
  };
  console.log(JSON.stringify(summary, null, 2));
  if (!allChecksPass) {
    process.exitCode = 1;
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.stack : String(error));
  process.exitCode = 1;
});
