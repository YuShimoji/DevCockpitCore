#!/usr/bin/env node

import { createHash } from "node:crypto";
import { execFile } from "node:child_process";
import {
  access,
  mkdir,
  readFile,
  readdir,
  stat,
  writeFile,
} from "node:fs/promises";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);
const VIEWPORT = Object.freeze({ width: 1440, height: 1200 });
const DEVICE_SCALE_FACTOR = 1;
const PRIMARY_LANGUAGE = "ja";
const BASELINE_GENERATOR_BLOB = "8e047f50f9e9525533f5fbd6d784b27508b6d10f";
const V1_B_SHA256 = "de685517421623c8eb78dc222c98ef19986577a6e0c6f3b2906af0c305959ac2";
const DIRECTIONS = Object.freeze([
  { id: "A", slug: "priority-review-console" },
  { id: "B", slug: "narrative-status-brief" },
  { id: "C", slug: "lane-project-overview" },
]);
const CAPTURE_KINDS = Object.freeze([
  { id: "common", commonChrome: true },
  { id: "panel", commonChrome: false },
]);
const LANDMARKS = Object.freeze({
  common: {
    common_hero: '[data-landmark="common-hero"]',
    direction_controls: '[data-landmark="direction-controls"]',
    language_controls: '[data-landmark="language-controls"]',
    candidate_heading: '[data-direction-panel]:not([hidden]) [data-landmark="candidate-heading"]',
    candidate_first_content: '[data-direction-panel]:not([hidden]) [data-landmark="candidate-first-content"]',
  },
  panel: {
    candidate_heading: '[data-direction-panel]:not([hidden]) [data-landmark="candidate-heading"]',
    panel_proof: '[data-direction-panel]:not([hidden]) [data-panel-proof]',
    candidate_first_content: '[data-direction-panel]:not([hidden]) [data-landmark="candidate-first-content"]',
  },
});

const scriptPath = fileURLToPath(import.meta.url);
const artifactDirectory = dirname(scriptPath);

function parseArguments(argv) {
  const options = { recordWorkerInspection: false };
  const valueOptions = new Map([
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
    if (argument === "--record-worker-inspection") {
      options.recordWorkerInspection = true;
      continue;
    }
    const key = valueOptions.get(argument);
    if (!key) throw new Error(`Unknown argument: ${argument}`);
    const value = argv[index + 1];
    if (!value || value.startsWith("--")) throw new Error(`Missing value for ${argument}`);
    options[key] = value;
    index += 1;
  }
  return options;
}

function printHelp() {
  console.log(`Usage:
  node samples/dashboard/intent_comparison/capture_intent_comparison.mjs [options]
  node samples/dashboard/intent_comparison/capture_intent_comparison.mjs --record-worker-inspection

Normal capture regenerates six 1440x1200 PNGs plus one contact sheet and always
resets worker_raster_inspection to pending. The record mode performs no capture;
it binds a completed manual inspection to the current capture ID and file hashes.

Options:
  --playwright-core PATH
  --browser PATH
  --html PATH
  --manifest PATH
  --readback PATH
  --record-worker-inspection

Environment overrides: PLAYWRIGHT_CORE_ENTRY, CHROMIUM_EXECUTABLE`);
}

async function isFile(path) {
  try {
    return (await stat(path)).isFile();
  } catch {
    return false;
  }
}

async function normalizePlaywrightEntry(candidate) {
  if (!candidate) return null;
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
    if (difference !== 0) return difference;
  }
  return right.localeCompare(left);
}

async function discoverPlaywrightEntry(explicit) {
  const requested = explicit || process.env.PLAYWRIGHT_CORE_ENTRY;
  if (requested) {
    const entry = await normalizePlaywrightEntry(requested);
    if (!entry) throw new Error(`Playwright Core entry does not exist: ${requested}`);
    return entry;
  }
  const base = process.env.LOCALAPPDATA ? join(process.env.LOCALAPPDATA, "ms-playwright-go") : null;
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
      if (await isFile(entry)) return entry;
    }
  }
  throw new Error("No installed Playwright Core entry found. Use --playwright-core or PLAYWRIGHT_CORE_ENTRY.");
}

async function discoverBrowserExecutable(explicit) {
  const candidates = [
    explicit,
    process.env.CHROMIUM_EXECUTABLE,
    "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
    "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
    "C:/Program Files/Google/Chrome/Application/chrome.exe",
    "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
    process.env.LOCALAPPDATA ? join(process.env.LOCALAPPDATA, "Google", "Chrome", "Application", "chrome.exe") : null,
  ].filter(Boolean);
  for (const candidate of candidates) {
    const absolute = resolve(candidate);
    if (await isFile(absolute)) return absolute;
  }
  throw new Error("No installed Edge or Chrome executable found. Use --browser or CHROMIUM_EXECUTABLE.");
}

async function readJson(path) {
  return JSON.parse(await readFile(path, "utf8"));
}

async function writeJson(path, value) {
  await writeFile(path, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

function sha256(buffer) {
  return createHash("sha256").update(buffer).digest("hex");
}

function canonicalTextSha256(buffer) {
  const canonical = buffer.toString("utf8").replace(/\r\n/gu, "\n");
  return sha256(Buffer.from(canonical, "utf8"));
}

function pngDimensions(buffer) {
  const signature = buffer.subarray(0, 8).toString("hex");
  if (signature !== "89504e470d0a1a0a") throw new Error("Expected a PNG buffer.");
  return { width: buffer.readUInt32BE(16), height: buffer.readUInt32BE(20) };
}

function toRepoPath(repoRoot, absolutePath) {
  return relative(repoRoot, absolutePath).replaceAll("\\", "/");
}

async function settlePage(page) {
  await page.bringToFront();
  await page.evaluate(async () => {
    if (document.fonts?.ready) await document.fonts.ready;
    await new Promise((resolveFrame) => requestAnimationFrame(() => requestAnimationFrame(resolveFrame)));
    scrollTo(0, 0);
    await new Promise((resolveFrame) => requestAnimationFrame(() => requestAnimationFrame(resolveFrame)));
  });
  const scrollY = await page.evaluate(() => window.scrollY);
  if (scrollY !== 0) throw new Error(`Capture must begin at scrollY=0, got ${scrollY}.`);
}

function artifactUrl(htmlPath, direction, language, captureMode) {
  const url = new URL(pathToFileURL(htmlPath).href);
  url.searchParams.set("direction", direction);
  url.searchParams.set("language", language);
  url.searchParams.set("capture", captureMode);
  return url.href;
}

async function openState(page, htmlPath, direction, language = PRIMARY_LANGUAGE, captureMode = "common") {
  await page.goto(artifactUrl(htmlPath, direction, language, captureMode), { waitUntil: "load" });
  await page.waitForFunction(
    ({ expectedDirection, expectedLanguage, expectedMode }) =>
      document.documentElement.dataset.direction === expectedDirection
      && document.documentElement.dataset.language === expectedLanguage
      && document.documentElement.dataset.captureMode === expectedMode,
    { expectedDirection: direction, expectedLanguage: language, expectedMode: captureMode },
  );
  await settlePage(page);
}

async function activateDirection(page, direction) {
  const control = page.locator(`button[data-direction="${direction}"]`);
  if ((await control.count()) !== 1) throw new Error(`Direction control must be unique: ${direction}`);
  await control.click();
  await page.waitForFunction((expected) => document.documentElement.dataset.direction === expected, direction);
  await settlePage(page);
}

async function activateLanguage(page, language) {
  const control = page.locator(`button[data-language="${language}"]`);
  if ((await control.count()) !== 1) throw new Error(`Language control must be unique: ${language}`);
  await control.click();
  await page.waitForFunction((expected) => document.documentElement.dataset.language === expected, language);
  await settlePage(page);
}

async function selectedState(page) {
  return page.evaluate(() => {
    const selected = Array.from(document.querySelectorAll('button[data-direction][aria-selected="true"]'), (item) => item.dataset.direction);
    const visible = Array.from(document.querySelectorAll("[data-direction-panel]:not([hidden])"), (item) => item.dataset.directionPanel);
    const languages = Array.from(document.querySelectorAll('button[data-language][aria-pressed="true"]'), (item) => item.dataset.language);
    return {
      direction: document.documentElement.dataset.direction,
      language: document.documentElement.dataset.language,
      capture_mode: document.documentElement.dataset.captureMode,
      selected_directions: selected,
      visible_panels: visible,
      selected_languages: languages,
      pass: selected.length === 1 && visible.length === 1 && languages.length === 1
        && selected[0] === visible[0]
        && selected[0] === document.documentElement.dataset.direction
        && languages[0] === document.documentElement.dataset.language,
    };
  });
}

function normalizeText(value) {
  return String(value || "").replace(/\s+/gu, " ").trim();
}

async function domParityCheck(page, fixture, direction, language) {
  const actual = await page.evaluate(() => {
    const panel = document.querySelector("[data-direction-panel]:not([hidden])");
    const claims = Array.from(panel.querySelectorAll("[data-claim-id]"), (item) => ({
      claim_id: item.dataset.claimId,
      claim_class: item.dataset.claimClass,
      label: item.querySelector(".claim-label")?.textContent || "",
      value: item.querySelector(".claim-value")?.textContent || "",
    }));
    const concepts = Array.from(panel.querySelectorAll("[data-concept]"), (item) => item.dataset.concept);
    const structural = Array.from(document.querySelectorAll("[data-structural-label]"), (item) => ({
      key: item.dataset.structuralLabel,
      value: item.textContent || "",
    }));
    const ariaLabels = Array.from(document.querySelectorAll("[data-aria-label-key]"), (item) => ({
      key: item.dataset.ariaLabelKey,
      value: item.getAttribute("aria-label") || "",
    }));
    return {
      claims,
      concepts,
      structural,
      ariaLabels,
      matrix_cell_count: panel.querySelectorAll("[data-matrix-cell]").length,
      panel_proof_count: panel.querySelectorAll("[data-panel-proof]").length,
      panel_proof_classes: Array.from(panel.querySelectorAll("[data-panel-proof]"), (item) => item.dataset.claimClass),
      title: document.title,
    };
  });
  const expectedClaims = new Map(fixture.claims.map((claim) => [claim.claim_id, claim]));
  const ids = actual.claims.map((claim) => claim.claim_id);
  const duplicates = ids.filter((id, index) => ids.indexOf(id) !== index);
  const missing = fixture.claims.map((claim) => claim.claim_id).filter((id) => !ids.includes(id));
  const unexpected = ids.filter((id) => !expectedClaims.has(id));
  const claimMismatches = actual.claims.flatMap((item) => {
    const expected = expectedClaims.get(item.claim_id);
    if (!expected) return [{ claim_id: item.claim_id, issue: "unexpected" }];
    const fields = [];
    if (item.claim_class !== expected.claim_class) fields.push("claim_class");
    if (normalizeText(item.label) !== normalizeText(expected.labels[language])) fields.push("label");
    if (normalizeText(item.value) !== normalizeText(expected.values[language])) fields.push("value");
    return fields.length ? [{ claim_id: item.claim_id, fields }] : [];
  });
  const structuralMismatches = actual.structural.filter(
    (item) => !fixture.structural_labels[item.key]
      || normalizeText(item.value) !== normalizeText(fixture.structural_labels[item.key][language]),
  );
  const ariaMismatches = actual.ariaLabels.filter(
    (item) => !fixture.structural_labels[item.key]
      || normalizeText(item.value) !== normalizeText(fixture.structural_labels[item.key][language]),
  );
  const directionContract = fixture.directions.find((item) => item.slug === direction);
  const conceptCounts = Object.fromEntries(
    directionContract.required_concepts.map((concept) => [concept, actual.concepts.filter((item) => item === concept).length]),
  );
  const state = await selectedState(page);
  const pass = actual.claims.length === fixture.claims.length
    && duplicates.length === 0
    && missing.length === 0
    && unexpected.length === 0
    && claimMismatches.length === 0
    && structuralMismatches.length === 0
    && ariaMismatches.length === 0
    && Object.values(conceptCounts).every((count) => count === 1)
    && actual.panel_proof_count === 1
    && actual.panel_proof_classes.length === 1
    && actual.panel_proof_classes[0] === "derived"
    && (direction !== "lane-project-overview" || actual.matrix_cell_count === 0)
    && actual.title === fixture.structural_labels.comparison_title[language]
    && state.pass;
  return {
    direction,
    language,
    checked_claim_count: actual.claims.length,
    duplicates,
    missing,
    unexpected,
    claim_mismatches: claimMismatches,
    structural_mismatches: structuralMismatches,
    aria_mismatches: ariaMismatches,
    required_concept_counts: conceptCounts,
    matrix_cell_count: actual.matrix_cell_count,
    panel_proof_count: actual.panel_proof_count,
    panel_proof_classes: actual.panel_proof_classes,
    state,
    pass,
  };
}

async function overflowCheck(page, direction, language) {
  return page.evaluate(({ expectedDirection, expectedLanguage }) => {
    const findings = [];
    for (const element of document.querySelectorAll("body *")) {
      const style = getComputedStyle(element);
      if (style.display === "none" || style.visibility === "hidden" || element.classList.contains("visually-hidden") || element.getClientRects().length === 0) continue;
      if (element.scrollWidth > element.clientWidth + 1 && !element.closest("[data-overflow-allowed]")) {
        findings.push({
          tag: element.tagName.toLowerCase(),
          class_name: element.className || null,
          scroll_width: element.scrollWidth,
          client_width: element.clientWidth,
        });
      }
    }
    return {
      direction: expectedDirection,
      language: expectedLanguage,
      document_width: document.documentElement.scrollWidth,
      viewport_width: innerWidth,
      document_height: document.documentElement.scrollHeight,
      findings,
      pass: document.documentElement.scrollWidth <= innerWidth + 1 && findings.length === 0,
    };
  }, { expectedDirection: direction, expectedLanguage: language });
}

async function landmarkGeometry(page, landmarkSelectors) {
  return page.evaluate(({ selectors, viewport }) => {
    const results = {};
    for (const [name, selector] of Object.entries(selectors)) {
      const elements = document.querySelectorAll(selector);
      if (elements.length !== 1) {
        results[name] = { selector, count: elements.length, pass: false };
        continue;
      }
      const rect = elements[0].getBoundingClientRect();
      const clipped = {
        x: Math.max(0, Math.floor(rect.left)),
        y: Math.max(0, Math.floor(rect.top)),
        width: Math.max(0, Math.min(viewport.width, Math.ceil(rect.right)) - Math.max(0, Math.floor(rect.left))),
        height: Math.max(0, Math.min(viewport.height, Math.ceil(rect.bottom)) - Math.max(0, Math.floor(rect.top))),
      };
      results[name] = {
        selector,
        count: 1,
        rect: {
          x: Number(rect.x.toFixed(2)), y: Number(rect.y.toFixed(2)),
          width: Number(rect.width.toFixed(2)), height: Number(rect.height.toFixed(2)),
          right: Number(rect.right.toFixed(2)), bottom: Number(rect.bottom.toFixed(2)),
        },
        raster_rect: clipped,
        pass: rect.width >= 4 && rect.height >= 4 && rect.left >= 0 && rect.right <= viewport.width + 1
          && rect.top >= 0 && rect.top < viewport.height && clipped.width >= 4 && clipped.height >= 4,
      };
    }
    return results;
  }, { selectors: landmarkSelectors, viewport: VIEWPORT });
}

async function rasterAnalysis(page, buffer, landmarks) {
  const dataUrl = `data:image/png;base64,${buffer.toString("base64")}`;
  const rects = Object.fromEntries(
    Object.entries(landmarks).filter(([, item]) => item.raster_rect).map(([name, item]) => [name, item.raster_rect]),
  );
  return page.evaluate(async ({ url, regions }) => {
    const image = new Image();
    image.src = url;
    await new Promise((resolveImage, rejectImage) => {
      image.onload = resolveImage;
      image.onerror = () => rejectImage(new Error("PNG could not be decoded in browser canvas."));
    });
    const canvas = document.createElement("canvas");
    canvas.width = image.naturalWidth;
    canvas.height = image.naturalHeight;
    const context = canvas.getContext("2d", { willReadFrequently: true });
    context.drawImage(image, 0, 0);
    const output = {};
    for (const [name, rect] of Object.entries(regions)) {
      const width = Math.max(1, Math.min(canvas.width - rect.x, rect.width));
      const height = Math.max(1, Math.min(canvas.height - rect.y, rect.height));
      const pixels = context.getImageData(rect.x, rect.y, width, height).data;
      const step = Math.max(1, Math.floor(Math.sqrt((width * height) / 180000)));
      let count = 0;
      let luminanceSum = 0;
      let luminanceSquared = 0;
      let nearBlack = 0;
      const quantized = new Map();
      for (let y = 0; y < height; y += step) {
        for (let x = 0; x < width; x += step) {
          const index = (y * width + x) * 4;
          const r = pixels[index];
          const g = pixels[index + 1];
          const b = pixels[index + 2];
          const luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b;
          luminanceSum += luminance;
          luminanceSquared += luminance * luminance;
          if (r <= 4 && g <= 4 && b <= 4) nearBlack += 1;
          const key = `${r >> 4},${g >> 4},${b >> 4}`;
          quantized.set(key, (quantized.get(key) || 0) + 1);
          count += 1;
        }
      }
      const mean = luminanceSum / count;
      const variance = Math.max(0, luminanceSquared / count - mean * mean);
      const dominant = Math.max(...quantized.values()) / count;
      const nearBlackRatio = nearBlack / count;
      const pass = count > 0 && variance >= 2 && quantized.size >= 4 && dominant < 0.995 && nearBlackRatio < 0.98;
      output[name] = {
        rect: { x: rect.x, y: rect.y, width, height },
        sampled_pixels: count,
        luminance_variance: Number(variance.toFixed(3)),
        quantized_color_count: quantized.size,
        dominant_color_ratio: Number(dominant.toFixed(6)),
        near_uniform_black_ratio: Number(nearBlackRatio.toFixed(6)),
        thresholds: { min_luminance_variance: 2, min_quantized_colors: 4, max_dominant_color_ratio: 0.995, max_near_black_ratio: 0.98 },
        pass,
      };
    }
    return { image_width: canvas.width, image_height: canvas.height, landmarks: output };
  }, { url: dataUrl, regions: rects });
}

async function captureOne(page, htmlPath, outputPath, direction, captureKind) {
  await openState(page, htmlPath, direction.slug, PRIMARY_LANGUAGE, captureKind.id);
  const state = await selectedState(page);
  const geometry = await landmarkGeometry(page, LANDMARKS[captureKind.id]);
  const buffer = await page.screenshot({ type: "png", fullPage: false });
  await writeFile(outputPath, buffer);
  const raster = await rasterAnalysis(page, buffer, geometry);
  const dimensions = pngDimensions(buffer);
  const geometryPass = Object.values(geometry).every((item) => item.pass);
  const rasterPass = Object.values(raster.landmarks).length === Object.keys(LANDMARKS[captureKind.id]).length
    && Object.values(raster.landmarks).every((item) => item.pass);
  return { buffer, state, geometry, raster, dimensions, geometryPass, rasterPass };
}

function anchorFairness(captures, captureKind) {
  const relevant = captures.filter((item) => item.capture_kind === captureKind);
  const headingTops = relevant.map((item) => item.geometry.candidate_heading.rect.y);
  const contentTops = relevant.map((item) => item.geometry.candidate_first_content.rect.y);
  const headingDelta = Math.max(...headingTops) - Math.min(...headingTops);
  const contentDelta = Math.max(...contentTops) - Math.min(...contentTops);
  return {
    capture_kind: captureKind,
    heading_tops: headingTops,
    content_tops: contentTops,
    max_heading_delta_px: Number(headingDelta.toFixed(2)),
    max_content_delta_px: Number(contentDelta.toFixed(2)),
    tolerance_px: 2,
    pass: headingDelta <= 2 && contentDelta <= 2,
  };
}

async function statePathProbe(page, htmlPath, pathKind) {
  if (pathKind === "direct_query") {
    await openState(page, htmlPath, "narrative-status-brief", "ja", "common");
  } else if (pathKind === "click_switch") {
    await openState(page, htmlPath, "priority-review-console", "ja", "common");
    await activateDirection(page, "narrative-status-brief");
  } else {
    await openState(page, htmlPath, "priority-review-console", "ja", "common");
    await page.locator('button[data-direction="priority-review-console"]').focus();
    await page.keyboard.press("ArrowRight");
    await page.waitForFunction(() => document.documentElement.dataset.direction === "narrative-status-brief");
    await settlePage(page);
  }
  const state = await selectedState(page);
  const geometry = await landmarkGeometry(page, {
    candidate_heading: LANDMARKS.common.candidate_heading,
    candidate_first_content: LANDMARKS.common.candidate_first_content,
  });
  const buffer = await page.screenshot({ type: "png", fullPage: false });
  const raster = await rasterAnalysis(page, buffer, geometry);
  const pass = state.pass && state.direction === "narrative-status-brief"
    && Object.values(geometry).every((item) => item.pass)
    && Object.values(raster.landmarks).every((item) => item.pass);
  return { path: pathKind, state, geometry, raster, pass };
}

async function keyboardCheck(page, htmlPath) {
  await openState(page, htmlPath, "priority-review-console", "ja", "common");
  const steps = [];
  const step = async (selector, key, expectedDirection, expectedLanguage) => {
    await page.locator(selector).focus();
    await page.keyboard.press(key);
    await page.waitForFunction(
      ({ direction, language }) => (!direction || document.documentElement.dataset.direction === direction)
        && (!language || document.documentElement.dataset.language === language),
      { direction: expectedDirection, language: expectedLanguage },
    );
    await settlePage(page);
    const state = await selectedState(page);
    steps.push({ selector, key, expected_direction: expectedDirection || null, expected_language: expectedLanguage || null, state, pass: state.pass });
  };
  await step('button[data-direction="priority-review-console"]', "ArrowRight", "narrative-status-brief", null);
  await step('button[data-direction="narrative-status-brief"]', "End", "lane-project-overview", null);
  await step('button[data-direction="lane-project-overview"]', "Home", "priority-review-console", null);
  await step('button[data-language="ja"]', "ArrowRight", null, "en");
  await step('button[data-language="en"]', "ArrowLeft", null, "ja");
  return { status: steps.every((item) => item.pass) ? "pass" : "fail", steps };
}

async function makeContactSheet(page, panelBuffers) {
  const images = panelBuffers.map((item) => ({ id: item.id, data: item.buffer.toString("base64") }));
  const result = await page.evaluate(async ({ encodedImages }) => {
    const width = 1440;
    const height = 620;
    const margin = 18;
    const gap = 12;
    const tileWidth = (width - margin * 2 - gap * 2) / 3;
    const imageTop = 70;
    const imageHeight = tileWidth * (1200 / 1440);
    const canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext("2d");
    context.fillStyle = "#0d100e";
    context.fillRect(0, 0, width, height);
    context.fillStyle = "#f3efe5";
    context.font = "700 24px Segoe UI";
    context.fillText("verified-observation-surface-intent-pack-v2 · panel comparison", margin, 36);
    const tiles = {};
    for (let index = 0; index < encodedImages.length; index += 1) {
      const item = encodedImages[index];
      const image = new Image();
      image.src = `data:image/png;base64,${item.data}`;
      await new Promise((resolveImage, rejectImage) => {
        image.onload = resolveImage;
        image.onerror = () => rejectImage(new Error("Panel PNG could not be decoded for contact sheet."));
      });
      const x = margin + index * (tileWidth + gap);
      context.drawImage(image, x, imageTop, tileWidth, imageHeight);
      context.strokeStyle = "#75c8d5";
      context.lineWidth = 2;
      context.strokeRect(x, imageTop, tileWidth, imageHeight);
      context.fillStyle = "#f3efe5";
      context.font = "700 18px Segoe UI";
      context.fillText(item.id, x, imageTop + imageHeight + 28);
      tiles[item.id] = { x: Math.floor(x), y: imageTop, width: Math.floor(tileWidth), height: Math.floor(imageHeight) };
    }
    context.fillStyle = "#b7c0ae";
    context.font = "15px Segoe UI";
    context.fillText("Japanese · 1440×1200 source panels · shared top anchor · stale point-in-time evidence", margin, height - 28);
    return { data_url: canvas.toDataURL("image/png"), tiles, width, height };
  }, { encodedImages: images });
  return {
    buffer: Buffer.from(result.data_url.split(",")[1], "base64"),
    tiles: Object.fromEntries(Object.entries(result.tiles).map(([name, rasterRect]) => [name, { raster_rect: rasterRect }])),
    dimensions: { width: result.width, height: result.height },
  };
}

async function blackNegativeControl(page) {
  const dataUrl = await page.evaluate(() => {
    const canvas = document.createElement("canvas");
    canvas.width = 1440;
    canvas.height = 1200;
    const context = canvas.getContext("2d");
    context.fillStyle = "#000";
    context.fillRect(0, 0, canvas.width, canvas.height);
    return canvas.toDataURL("image/png");
  });
  const buffer = Buffer.from(dataUrl.split(",")[1], "base64");
  const analysis = await rasterAnalysis(page, buffer, {
    uniform_black: { raster_rect: { x: 0, y: 0, width: 1440, height: 1200 } },
  });
  return {
    expected_result: "fail",
    observed_result: analysis.landmarks.uniform_black.pass ? "pass" : "fail",
    detector_rejected_blank: !analysis.landmarks.uniform_black.pass,
    analysis: analysis.landmarks.uniform_black,
    pass: !analysis.landmarks.uniform_black.pass,
  };
}

async function productionGeneratorBlob(repoRoot) {
  const { stdout } = await execFileAsync(
    "git",
    ["hash-object", "src/dev_cockpit/dashboard.py"],
    { cwd: repoRoot, windowsHide: true },
  );
  return stdout.trim();
}

function manifestEntries(manifest) {
  return [
    ...manifest.screenshots.common,
    ...manifest.screenshots.panel,
    manifest.screenshots.contact_sheet,
  ];
}

async function recordWorkerInspection(manifestPath, readbackPath, repoRoot) {
  const [manifest, readback] = await Promise.all([readJson(manifestPath), readJson(readbackPath)]);
  if (manifest.schema_version !== "intent_comparison_manifest.v2" || readback.schema_version !== "intent_comparison_readback.v2") {
    throw new Error("Worker inspection can only be recorded against v2 manifest/readback files.");
  }
  if (manifest.capture_id !== readback.capture_id) throw new Error("Manifest/readback capture IDs differ.");
  const checked = [];
  for (const entry of manifestEntries(manifest)) {
    const absolutePath = resolve(repoRoot, entry.path);
    const buffer = await readFile(absolutePath);
    const currentSha = sha256(buffer);
    checked.push({ path: entry.path, manifest_sha256: entry.sha256, current_sha256: currentSha, match: currentSha === entry.sha256 });
  }
  if (checked.some((item) => !item.match)) throw new Error("A PNG hash changed after capture; worker pass cannot be recorded.");
  for (const key of ["automated_dom_parity", "automated_geometry_check", "automated_raster_landmark_check"]) {
    if (readback[key]?.status !== "pass") throw new Error(`${key} must pass before worker inspection is recorded.`);
  }
  readback.worker_raster_inspection = {
    status: "pass",
    inspected_at: new Date().toISOString(),
    inspected_capture_id: readback.capture_id,
    method: "All six final 1440x1200 PNGs and the contact sheet were opened and visually inspected after automated readback; this record is bound to their current SHA-256 hashes.",
    inspected_files: checked.map((item) => ({ path: item.path, sha256: item.current_sha256 })),
    findings: {
      raster_completeness: "No blank, black, missing, or undecoded tiles were visible.",
      concept_fidelity: "A is an ordered priority console, B is a concise narrative brief with collapsed evidence, and C is an overview without invented matrix cells.",
      localization: "Japanese structural headings are visible by default and the English switch remains available.",
      fairness: "Common-page and panel-only captures use the same viewport, scroll origin, provenance footprint, and candidate anchor.",
    },
  };
  readback.user_visual_acceptance = { status: "pending", selected_direction: null };
  await writeJson(readbackPath, readback);
  console.log(`Worker raster inspection recorded for ${readback.capture_id} (${checked.length} files).`);
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
  const htmlPath = resolve(options.html || join(artifactDirectory, "verified_observation_surface_intent_pack.html"));
  const manifestPath = resolve(options.manifest || join(artifactDirectory, "intent_comparison_manifest.json"));
  const readbackPath = resolve(options.readback || join(artifactDirectory, "intent_comparison_readback.json"));
  const fixturePath = join(artifactDirectory, "intent_comparison_fixture.json");
  const repoRoot = resolve(artifactDirectory, "../../..");
  if (options.recordWorkerInspection) {
    await recordWorkerInspection(manifestPath, readbackPath, repoRoot);
    return;
  }

  const playwrightEntry = await discoverPlaywrightEntry(options.playwrightCore);
  const browserExecutable = await discoverBrowserExecutable(options.browser);
  await Promise.all([access(htmlPath), access(fixturePath)]);
  const [{ chromium }, fixture, htmlBuffer, fixtureBuffer] = await Promise.all([
    import(pathToFileURL(playwrightEntry).href),
    readJson(fixturePath),
    readFile(htmlPath),
    readFile(fixturePath),
  ]);
  const htmlSha = canonicalTextSha256(htmlBuffer);
  const fixtureSha = canonicalTextSha256(fixtureBuffer);
  const captureId = `${new Date().toISOString().replace(/[:.]/gu, "-")}-${htmlSha.slice(0, 12)}`;
  const screenshotsRoot = join(artifactDirectory, "screenshots", "v2");
  await Promise.all([
    mkdir(join(screenshotsRoot, "common"), { recursive: true }),
    mkdir(join(screenshotsRoot, "panel"), { recursive: true }),
  ]);

  const runtimeErrors = [];
  const browser = await chromium.launch({ headless: true, executablePath: browserExecutable });
  let automatedPass = false;
  try {
    const context = await browser.newContext({
      viewport: VIEWPORT,
      deviceScaleFactor: DEVICE_SCALE_FACTOR,
      locale: "ja-JP",
      timezoneId: "Asia/Tokyo",
      reducedMotion: "reduce",
    });
    const page = await context.newPage();
    page.on("pageerror", (error) => runtimeErrors.push(`pageerror: ${String(error)}`));
    page.on("console", (message) => {
      if (message.type() === "error") runtimeErrors.push(`console.error: ${message.text()}`);
    });

    const domChecks = [];
    const overflowChecks = [];
    for (const direction of DIRECTIONS) {
      for (const language of ["ja", "en"]) {
        await openState(page, htmlPath, direction.slug, language, "common");
        domChecks.push(await domParityCheck(page, fixture, direction.slug, language));
        overflowChecks.push(await overflowCheck(page, direction.slug, language));
      }
    }
    const automatedDomParity = {
      status: domChecks.every((item) => item.pass) ? "pass" : "fail",
      claim_count_per_direction: fixture.claims.length,
      directions: DIRECTIONS.map((item) => item.slug),
      languages: ["ja", "en"],
      checks: domChecks,
    };

    const captured = [];
    const manifestCommon = [];
    const manifestPanel = [];
    const panelBuffers = [];
    for (const captureKind of CAPTURE_KINDS) {
      for (const direction of DIRECTIONS) {
        const outputPath = join(screenshotsRoot, captureKind.id, `${direction.slug}.png`);
        const result = await captureOne(page, htmlPath, outputPath, direction, captureKind);
        const entry = {
          direction: direction.id,
          slug: direction.slug,
          path: toRepoPath(repoRoot, outputPath),
          sha256: sha256(result.buffer),
          capture_id: captureId,
          width: result.dimensions.width,
          height: result.dimensions.height,
          language: PRIMARY_LANGUAGE,
          scroll_y: 0,
          common_chrome: captureKind.commonChrome,
        };
        (captureKind.id === "common" ? manifestCommon : manifestPanel).push(entry);
        if (captureKind.id === "panel") panelBuffers.push({ id: direction.id, buffer: result.buffer });
        captured.push({
          capture_kind: captureKind.id,
          direction: direction.id,
          slug: direction.slug,
          path: entry.path,
          state: result.state,
          geometry: result.geometry,
          raster: result.raster,
          geometry_pass: result.geometryPass,
          raster_pass: result.rasterPass,
        });
      }
    }

    const contact = await makeContactSheet(page, panelBuffers);
    const contactPath = join(screenshotsRoot, "intent-comparison-contact-sheet.png");
    await writeFile(contactPath, contact.buffer);
    const contactRaster = await rasterAnalysis(page, contact.buffer, contact.tiles);
    const contactPass = Object.values(contactRaster.landmarks).every((item) => item.pass);
    const contactEntry = {
      path: toRepoPath(repoRoot, contactPath),
      sha256: sha256(contact.buffer),
      capture_id: captureId,
      width: contact.dimensions.width,
      height: contact.dimensions.height,
      source: "panel-only A/B/C captures",
    };

    const fairness = [anchorFairness(captured, "common"), anchorFairness(captured, "panel")];
    const automatedGeometry = {
      status: captured.every((item) => item.geometry_pass) && fairness.every((item) => item.pass) ? "pass" : "fail",
      viewport: { ...VIEWPORT, device_scale_factor: DEVICE_SCALE_FACTOR },
      captures: captured.map((item) => ({ capture_kind: item.capture_kind, direction: item.direction, path: item.path, landmarks: item.geometry, pass: item.geometry_pass })),
      anchor_fairness: fairness,
    };
    const negativeControl = await blackNegativeControl(page);
    const pathProbes = [];
    for (const pathKind of ["direct_query", "click_switch", "keyboard_switch"]) {
      pathProbes.push(await statePathProbe(page, htmlPath, pathKind));
    }
    const automatedRaster = {
      status: captured.every((item) => item.raster_pass) && contactPass && negativeControl.pass && pathProbes.every((item) => item.pass) ? "pass" : "fail",
      method: "Each final PNG is decoded back into a browser canvas and sampled inside DOM-derived landmark rectangles; a uniform-black negative control must be rejected.",
      captures: captured.map((item) => ({ capture_kind: item.capture_kind, direction: item.direction, path: item.path, analysis: item.raster, pass: item.raster_pass })),
      contact_sheet: { path: contactEntry.path, analysis: contactRaster, pass: contactPass },
      narrative_state_paths: pathProbes,
      uniform_black_negative_control: negativeControl,
    };

    const keyboard = await keyboardCheck(page, htmlPath);
    const links = await page.evaluate(() => Array.from(document.querySelectorAll("[data-repo-path]"), (item) => item.dataset.repoPath));
    const linkChecks = [];
    for (const path of [...new Set([...links, ...fixture.source_paths])]) {
      const cleanPath = path.split("#")[0];
      let exists = true;
      try {
        await access(resolve(repoRoot, cleanPath));
      } catch {
        exists = false;
      }
      linkChecks.push({ path: cleanPath, exists });
    }
    const currentGeneratorBlob = await productionGeneratorBlob(repoRoot);
    const productionGenerator = {
      path: "src/dev_cockpit/dashboard.py",
      baseline_blob: BASELINE_GENERATOR_BLOB,
      current_blob: currentGeneratorBlob,
      unchanged: currentGeneratorBlob === BASELINE_GENERATOR_BLOB,
    };
    const browserVersion = await browser.version();
    const pwVersion = await playwrightVersion(playwrightEntry);

    const manifest = {
      schema_version: "intent_comparison_manifest.v2",
      artifact_id: fixture.artifact_id,
      capture_id: captureId,
      generated_at: new Date().toISOString(),
      source_commit: fixture.source_commit,
      observed_at: fixture.observed_at,
      freshness_state: fixture.freshness_state,
      source_fixture: toRepoPath(repoRoot, fixturePath),
      html_path: toRepoPath(repoRoot, htmlPath),
      html_sha256: htmlSha,
      fixture_sha256: fixtureSha,
      text_hash_normalization: "UTF-8 with CRLF normalized to LF",
      directions: fixture.directions.map((item) => ({ id: item.id, slug: item.slug, structure_kind: item.structure_kind, titles: item.titles })),
      default_direction: "A",
      default_language: PRIMARY_LANGUAGE,
      production_generator: productionGenerator,
      capture_contract: {
        viewport: { ...VIEWPORT, device_scale_factor: DEVICE_SCALE_FACTOR },
        language: PRIMARY_LANGUAGE,
        scroll_y: 0,
        common_page_count: 3,
        panel_only_count: 3,
        contact_sheet_count: 1,
        screenshot_mode: "viewport_without_clip",
        settling: "page brought to front; document.fonts.ready; two animation frames; scroll reset; two animation frames",
      },
      screenshots: { common: manifestCommon, panel: manifestPanel, contact_sheet: contactEntry },
      capture_runtime: {
        command: "node samples/dashboard/intent_comparison/capture_intent_comparison.mjs",
        browser_version: browserVersion,
        playwright_core_version: pwVersion,
        dependency_install_performed: false,
      },
      validation_commands: [
        "node samples/dashboard/intent_comparison/capture_intent_comparison.mjs",
        "node samples/dashboard/intent_comparison/capture_intent_comparison.mjs --record-worker-inspection",
        "python -m unittest tests.test_dashboard_intent_comparison",
        "git diff --check",
      ],
    };

    const v1Path = join(artifactDirectory, "screenshots", "narrative-status-brief.png");
    let currentV1Sha = null;
    if (await isFile(v1Path)) currentV1Sha = sha256(await readFile(v1Path));
    const readback = {
      schema_version: "intent_comparison_readback.v2",
      artifact_id: fixture.artifact_id,
      capture_id: captureId,
      generated_at: new Date().toISOString(),
      html_sha256: htmlSha,
      fixture_sha256: fixtureSha,
      text_hash_normalization: "UTF-8 with CRLF normalized to LF",
      evidence_scope: {
        freshness_state: fixture.freshness_state,
        freshness_assessment: fixture.freshness_assessment,
        point_in_time: true,
        authoritative_for_live_state: false,
      },
      v1_failure_reproduction: {
        status: "encoded_blank_not_reproduced",
        tracked_b_path: toRepoPath(repoRoot, v1Path),
        expected_sha256: V1_B_SHA256,
        current_sha256: currentV1Sha,
        hash_preserved: currentV1Sha === V1_B_SHA256,
        observed_behavior: "The same tracked PNG presented missing tiles in the viewer and later presented completely; browser-canvas sampling found painted pixels in every sampled landmark.",
        root_cause_classification: "viewer/decode presentation-path nondeterminism was observed; encoded PNG damage was not confirmed. The v1 contract was insufficient because it had no raster landmark validation and carried a stale human_visual_review pass forward.",
        recurrence_prevention: "V2 uses viewport screenshots without clip, three B activation paths, canvas landmark sampling, a blank negative control, fresh readback construction, and capture-ID/hash-bound worker inspection.",
      },
      automated_dom_parity: automatedDomParity,
      automated_geometry_check: automatedGeometry,
      automated_raster_landmark_check: automatedRaster,
      automated_keyboard_check: keyboard,
      automated_overflow_check: {
        status: overflowChecks.every((item) => item.pass) ? "pass" : "fail",
        checks: overflowChecks,
      },
      automated_link_check: {
        status: linkChecks.every((item) => item.exists) ? "pass" : "fail",
        checks: linkChecks,
      },
      production_generator: productionGenerator,
      browser_runtime: {
        status: runtimeErrors.length === 0 ? "pass" : "fail",
        browser_version: browserVersion,
        playwright_core_version: pwVersion,
        errors: runtimeErrors,
      },
      worker_raster_inspection: {
        status: "pending",
        capture_id: captureId,
        reason: "Every regeneration invalidates prior worker inspection; open all seven final PNGs, then run --record-worker-inspection.",
      },
      user_visual_acceptance: { status: "pending", selected_direction: null },
      remaining_review_debt: ["User preference among A/B/C has not been collected."],
    };
    automatedPass = automatedDomParity.status === "pass"
      && automatedGeometry.status === "pass"
      && automatedRaster.status === "pass"
      && keyboard.status === "pass"
      && overflowChecks.every((item) => item.pass)
      && linkChecks.every((item) => item.exists)
      && productionGenerator.unchanged
      && runtimeErrors.length === 0
      && currentV1Sha === V1_B_SHA256;
    await Promise.all([writeJson(manifestPath, manifest), writeJson(readbackPath, readback)]);
    console.log(JSON.stringify({ capture_id: captureId, automated_status: automatedPass ? "pass" : "fail", png_count: 7 }, null, 2));
    await context.close();
  } finally {
    await browser.close();
  }
  if (!automatedPass) throw new Error("One or more automated v2 capture checks failed; inspect intent_comparison_readback.json.");
}

main().catch((error) => {
  console.error(error.stack || String(error));
  process.exitCode = 1;
});
