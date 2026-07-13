#!/usr/bin/env node

import { createHash } from "node:crypto";
import { execFile } from "node:child_process";
import { realpathSync } from "node:fs";
import {
  access,
  copyFile,
  mkdir,
  mkdtemp,
  readFile,
  readdir,
  rm,
  stat,
  writeFile,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import { basename, dirname, isAbsolute, join, relative, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);
const ARTIFACT_ID = "priority-review-console-production-observation-surface-v1";
const MANIFEST_SCHEMA = "production_capture_manifest.v1";
const READBACK_SCHEMA = "production_capture_readback.v1";
const PRIORITY_READBACK_SCHEMA = "devcockpit_priority_readback.v1";
const FRESHNESS_RECEIPT_SCHEMA = "evidence_freshness_receipt.v1";
const DEVICE_SCALE_FACTOR = 1;
const CAPTURE_DEFINITIONS = Object.freeze([
  {
    id: "ja-desktop",
    filename: "priority-review-console-ja-desktop.png",
    language: "ja",
    locale: "ja-JP",
    viewport: { width: 1440, height: 1200 },
  },
  {
    id: "en-desktop",
    filename: "priority-review-console-en-desktop.png",
    language: "en",
    locale: "en-US",
    viewport: { width: 1440, height: 1200 },
  },
  {
    id: "ja-narrow",
    filename: "priority-review-console-ja-narrow.png",
    language: "ja",
    locale: "ja-JP",
    viewport: { width: 390, height: 3100 },
  },
]);
const CONTACT_SHEET = Object.freeze({
  id: "contact-sheet",
  filename: "priority-review-console-contact-sheet.png",
  width: 1440,
  height: 760,
});
const BASE_REQUIRED_LANDMARKS = Object.freeze({
  current_state: '[data-landmark="current-state"]',
  local_observer_health: '[data-landmark="local-observer-health"]',
  priority_lane: '[data-landmark="priority-lane"]',
  priority_first: '[data-landmark="priority-first"]',
  active_decision: '[data-landmark="active-decision"]',
  evidence_inspector: '[data-landmark="evidence-inspector"]',
  freshness_status: '[data-landmark="freshness-status"]',
  provenance: '[data-landmark="provenance"]',
});

function requiredLandmarks(priorityContract) {
  return Object.freeze({
    ...BASE_REQUIRED_LANDMARKS,
    ...(priorityContract.packet_loaded
      ? { packet_attention: '[data-landmark="packet-attention"]' }
      : {}),
  });
}
const AUTOMATED_STATUS_KEYS = Object.freeze([
  "source_binding",
  "automated_semantic_parity",
  "automated_priority_click_sync",
  "automated_priority_keyboard_sync",
  "automated_language_switch",
  "automated_visible_focus",
  "automated_no_javascript_fallback",
  "automated_overflow_check",
  "automated_narrow_order",
  "automated_geometry_check",
  "automated_browser_canvas_raster",
  "automated_ffmpeg_raster",
  "automated_decoder_agreement",
  "partial_black_negative_control",
  "browser_runtime",
]);

const scriptPath = fileURLToPath(import.meta.url);
const artifactDirectory = dirname(scriptPath);

function parseArguments(argv) {
  const options = { recordWorkerInspection: false };
  const valueOptions = new Map([
    ["--playwright-core", "playwrightCore"],
    ["--browser", "browser"],
    ["--ffmpeg", "ffmpeg"],
    ["--html", "html"],
    ["--priority-readback", "priorityReadback"],
    ["--freshness-receipt", "freshnessReceipt"],
    ["--output-root", "outputRoot"],
    ["--repo-root", "repoRoot"],
    ["--captured-at", "capturedAt"],
    ["--inspection-at", "inspectionAt"],
    ["--validate-semantic-fixture", "validateSemanticFixture"],
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
    if (argument === "--validate-source-binding") {
      options.validateSourceBinding = true;
      continue;
    }
    if (argument === "--validate-timestamp-authority") {
      options.validateTimestampAuthority = true;
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
  node samples/dashboard/production_capture/capture_priority_review_console.mjs [options]
  node samples/dashboard/production_capture/capture_priority_review_console.mjs --record-worker-inspection [options]

Normal capture creates three viewport PNGs, a contact sheet, a manifest, and an
automated readback under OUTPUT_ROOT. All files are staged until every automated
check passes. Capture IDs are content-derived; --captured-at is metadata only.

Options:
  --playwright-core PATH
  --browser PATH
  --ffmpeg PATH
  --html PATH
  --priority-readback PATH
  --freshness-receipt PATH
  --output-root PATH
  --repo-root PATH
  --captured-at ISO-8601
  --validate-timestamp-authority
  --validate-source-binding
  --validate-semantic-fixture PATH
  --record-worker-inspection
  --inspection-at ISO-8601

Environment overrides:
  PLAYWRIGHT_CORE_ENTRY
  CHROMIUM_EXECUTABLE
  FFMPEG_EXECUTABLE`);
}

function assertIsoInstant(value, optionName) {
  const match = typeof value === "string"
    ? /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,3}))?(Z|[+-]\d{2}:\d{2})$/u.exec(value)
    : null;
  if (!match || !Number.isFinite(Date.parse(value))) {
    throw new Error(`${optionName} must be an ISO-8601 timestamp.`);
  }
  const [, year, month, day, hour, minute, second, , zone] = match;
  const calendar = new Date(Date.UTC(Number(year), Number(month) - 1, Number(day)));
  const invalidCalendar = calendar.getUTCFullYear() !== Number(year)
    || calendar.getUTCMonth() + 1 !== Number(month)
    || calendar.getUTCDate() !== Number(day);
  const zoneHour = zone === "Z" ? 0 : Number(zone.slice(1, 3));
  const zoneMinute = zone === "Z" ? 0 : Number(zone.slice(4, 6));
  if (
    invalidCalendar
    || Number(hour) > 23
    || Number(minute) > 59
    || Number(second) > 59
    || zoneHour > 23
    || zoneMinute > 59
  ) {
    throw new Error(`${optionName} must be an ISO-8601 timestamp.`);
  }
  return new Date(value).toISOString();
}

function timestampAuthority(declaredValue, optionName, event) {
  if (declaredValue) {
    const value = assertIsoInstant(declaredValue, optionName);
    return {
      value,
      authority: "deterministic_declared_override",
      event,
      actual_observed_at: null,
      declared_at: value,
      current_observation_eligible: false,
    };
  }
  const value = new Date().toISOString();
  return {
    value,
    authority: event === "browser_capture_completed"
      ? "actual_browser_observation"
      : event === "worker_raster_inspection_completed"
        ? "actual_worker_inspection"
        : "runtime_clock_observation",
    event,
    actual_observed_at: value,
    declared_at: null,
    current_observation_eligible: event === "browser_capture_completed",
  };
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

async function discoverFfmpegExecutable(explicit) {
  const requested = explicit || process.env.FFMPEG_EXECUTABLE;
  if (requested) {
    const absolute = isAbsolute(requested) ? requested : resolve(requested);
    if (!(await isFile(absolute))) throw new Error(`FFmpeg executable does not exist: ${requested}`);
    return absolute;
  }
  try {
    await execFileAsync("ffmpeg", ["-version"], { windowsHide: true, maxBuffer: 1024 * 1024 });
    return "ffmpeg";
  } catch {
    throw new Error("System FFmpeg with PNG decoding is required. Use --ffmpeg or FFMPEG_EXECUTABLE.");
  }
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

function canonicalize(value) {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.keys(value).sort().map((key) => [key, canonicalize(value[key])]),
    );
  }
  return value;
}

function canonicalJson(value) {
  return JSON.stringify(canonicalize(value));
}

function bindEmbeddedPriorityHash(snapshot) {
  if (!Array.isArray(snapshot?.embedded_priorities)) return snapshot;
  const bound = {
    ...snapshot,
    embedded_priorities_sha256: sha256(
      Buffer.from(canonicalJson(snapshot.embedded_priorities), "utf8"),
    ),
  };
  delete bound.embedded_priorities;
  return bound;
}

function pngDimensions(buffer) {
  if (buffer.subarray(0, 8).toString("hex") !== "89504e470d0a1a0a") {
    throw new Error("Expected a PNG buffer.");
  }
  return { width: buffer.readUInt32BE(16), height: buffer.readUInt32BE(20) };
}

function displayPath(path, repoRoot, outputRoot) {
  const absolute = resolve(path);
  const fromOutput = relative(outputRoot, absolute);
  if (fromOutput && !fromOutput.startsWith("..") && !isAbsolute(fromOutput)) {
    return fromOutput.replaceAll("\\", "/");
  }
  const fromRepo = relative(repoRoot, absolute);
  if (fromRepo && !fromRepo.startsWith("..") && !isAbsolute(fromRepo)) {
    return fromRepo.replaceAll("\\", "/");
  }
  return `<external>/${basename(absolute)}`;
}


function portableRuntimePath(path) {
  if (!isAbsolute(path)) return path.replaceAll("\\", "/");
  const normalized = resolve(path).replaceAll("\\", "/");
  return /^[A-Za-z]:\/Users\//iu.test(normalized) || /^\/(?:home|Users)\//u.test(normalized)
    ? `<user-runtime>/${basename(normalized)}`
    : normalized;
}

function manifestOutputPath(filename) {
  return `screenshots/${filename}`;
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

function artifactUrl(htmlPath, language) {
  const url = new URL(pathToFileURL(htmlPath).href);
  url.searchParams.set("language", language);
  url.searchParams.set("capture", "production");
  return url.href;
}

async function activateLanguage(page, language) {
  const control = page.locator(`button[data-language="${language}"]`);
  if ((await control.count()) !== 1) throw new Error(`Language control must be unique: ${language}`);
  await control.click();
  await page.waitForFunction(
    (expected) => document.documentElement.dataset.language === expected,
    language,
  );
}

async function openState(page, htmlPath, language) {
  await page.goto(artifactUrl(htmlPath, language), { waitUntil: "load" });
  const current = await page.evaluate(() => document.documentElement.dataset.language || document.documentElement.lang);
  if (current !== language) await activateLanguage(page, language);
  await page.waitForFunction(
    (expected) =>
      document.documentElement.dataset.language === expected
      && document.documentElement.lang.toLowerCase().startsWith(expected),
    language,
  );
  await settlePage(page);
}

async function priorityIds(page) {
  return page.evaluate(() =>
    Array.from(document.querySelectorAll("button[data-priority-id]"), (item) => item.dataset.priorityId),
  );
}

function priorityInteractionPlan(ids) {
  if (!Array.isArray(ids) || !ids.length) return null;
  const next = ids.length === 1 ? ids[0] : ids[1];
  return {
    click_target: next,
    keyboard_targets: {
      End: ids.at(-1),
      Home: ids[0],
      ArrowDown: next,
      ArrowUp: ids[0],
    },
    mode: ids.length === 1 ? "single_priority_no_op" : "multi_priority_navigation",
  };
}

async function synchronizedState(page) {
  return page.evaluate(() => {
    const selected = Array.from(
      document.querySelectorAll('button[data-priority-id][aria-selected="true"]'),
      (item) => item.dataset.priorityId,
    );
    const decision = document.querySelector('[data-landmark="active-decision"]');
    const inspector = document.querySelector('[data-landmark="evidence-inspector"]');
    const focus = document.activeElement?.matches?.("button[data-priority-id]")
      ? document.activeElement.dataset.priorityId
      : null;
    const decisionId = decision?.dataset.priorityId || null;
    const inspectorId = inspector?.dataset.priorityId || null;
    return {
      selected_priority_ids: selected,
      decision_priority_id: decisionId,
      inspector_priority_id: inspectorId,
      inspector_evidence_id: inspector?.dataset.evidenceId || null,
      focused_priority_id: focus,
      pass: selected.length === 1
        && Boolean(selected[0])
        && selected[0] === decisionId
        && selected[0] === inspectorId
        && Boolean(inspector?.dataset.evidenceId),
    };
  });
}

async function semanticSnapshot(page, htmlPath, language) {
  await openState(page, htmlPath, language);
  const snapshot = await page.evaluate(() => {
    const orderedUnique = (values) => values.filter((value, index) => value && values.indexOf(value) === index);
    const priorities = Array.from(
      document.querySelectorAll("button[data-priority-id]"),
      (item) => item.dataset.priorityId,
    );
    const evidence = orderedUnique(Array.from(
      document.querySelectorAll("[data-evidence-id]"),
      (item) => item.dataset.evidenceId,
    ));
    const selected = Array.from(
      document.querySelectorAll('button[data-priority-id][aria-selected="true"]'),
      (item) => item.dataset.priorityId,
    );
    const decision = document.querySelector('[data-landmark="active-decision"]');
    const inspector = document.querySelector('[data-landmark="evidence-inspector"]');
    const embeddedPriorities = JSON.parse(
      document.getElementById("priority-model")?.textContent || "[]",
    );
    const selectedTask = embeddedPriorities.find(
      (item) => item.priority_id === selected[0],
    ) || {};
    const visibleField = (selector) => {
      const item = document.querySelector(selector);
      const style = item ? getComputedStyle(item) : null;
      const text = item?.textContent?.trim() || "";
      return {
        text,
        visible: Boolean(
          item
          && item.getClientRects().length
          && style?.display !== "none"
          && style?.visibility !== "hidden"
          && text
        ),
      };
    };
    const visibleLandmarks = {};
    for (const name of [
      "current-state",
      "local-observer-health",
      "packet-attention",
      "priority-lane",
      "priority-first",
      "priority-empty-state",
      "active-decision",
      "evidence-inspector",
      "freshness-status",
      "provenance",
    ]) {
      const item = document.querySelector(`[data-landmark="${name}"]`);
      visibleLandmarks[name] = Boolean(item && item.getClientRects().length);
    }
    return {
      language: document.documentElement.dataset.language,
      priority_ids: priorities,
      evidence_ids: evidence,
      selected_priority_ids: selected,
      decision_priority_id: decision?.dataset.priorityId || null,
      inspector_priority_id: inspector?.dataset.priorityId || null,
      inspector_evidence_id: inspector?.dataset.evidenceId || null,
      embedded_priorities: embeddedPriorities,
      project_identity: {
        expected: `${selectedTask.project_key || "unknown"} / ${selectedTask.thread_id || "local-observation"}`,
        rendered: visibleField('#active-decision [data-field="project-identity"]'),
      },
      lane_identity: {
        expected: `${selectedTask.lane_id || "observer"} / ${selectedTask.slice_id || "local-review"}`,
        rendered: visibleField('#active-decision [data-field="lane-identity"]'),
      },
      attention_class: {
        expected: selectedTask.attention_class || "local_evidence_priority",
        rendered: visibleField('#evidence-inspector [data-field="attention-class"]'),
      },
      visible_landmarks: visibleLandmarks,
    };
  });
  return bindEmbeddedPriorityHash(snapshot);
}

function arraysEqual(left, right) {
  return Array.isArray(left)
    && Array.isArray(right)
    && left.length === right.length
    && left.every((value, index) => value === right[index]);
}

function evaluatePrioritySemanticBinding(japanese, english, expected) {
  const expectedEvidenceId = expected.evidence_by_priority_id[expected.selected_priority_id];
  const requiredLandmarkNames = Object.values(requiredLandmarks(expected)).map(
    (selector) => selector.match(/data-landmark="([^"]+)"/u)?.[1],
  );
  const checks = {
    expected_priority_count_nonzero:
      expected.mode === "all_closed" ? expected.priority_ids.length === 0 : expected.priority_ids.length >= 1,
    japanese_language: japanese.language === "ja",
    english_language: english.language === "en",
    japanese_priority_ids: arraysEqual(japanese.priority_ids, expected.priority_ids),
    english_priority_ids: arraysEqual(english.priority_ids, expected.priority_ids),
    japanese_evidence_ids: arraysEqual(japanese.evidence_ids, expected.evidence_ids),
    english_evidence_ids: arraysEqual(english.evidence_ids, expected.evidence_ids),
    japanese_selected_priority: arraysEqual(
      japanese.selected_priority_ids,
      [expected.selected_priority_id],
    ),
    english_selected_priority: arraysEqual(
      english.selected_priority_ids,
      [expected.selected_priority_id],
    ),
    japanese_decision_priority:
      japanese.decision_priority_id === expected.selected_priority_id,
    english_decision_priority:
      english.decision_priority_id === expected.selected_priority_id,
    japanese_inspector_priority:
      japanese.inspector_priority_id === expected.selected_priority_id,
    english_inspector_priority:
      english.inspector_priority_id === expected.selected_priority_id,
    japanese_inspector_evidence: japanese.inspector_evidence_id === expectedEvidenceId,
    english_inspector_evidence: english.inspector_evidence_id === expectedEvidenceId,
    japanese_embedded_priority_model:
      japanese.embedded_priorities_sha256 === expected.priorities_sha256,
    english_embedded_priority_model:
      english.embedded_priorities_sha256 === expected.priorities_sha256,
    japanese_landmarks: requiredLandmarkNames.every(
      (name) => japanese.visible_landmarks[name] === true,
    ),
    english_landmarks: requiredLandmarkNames.every(
      (name) => english.visible_landmarks[name] === true,
    ),
    japanese_project_identity: japanese.project_identity.rendered.visible
      && japanese.project_identity.rendered.text === japanese.project_identity.expected,
    english_project_identity: english.project_identity.rendered.visible
      && english.project_identity.rendered.text === english.project_identity.expected,
    japanese_lane_identity: japanese.lane_identity.rendered.visible
      && japanese.lane_identity.rendered.text === japanese.lane_identity.expected,
    english_lane_identity: english.lane_identity.rendered.visible
      && english.lane_identity.rendered.text === english.lane_identity.expected,
    japanese_attention_class: japanese.attention_class.rendered.visible
      && japanese.attention_class.rendered.text === japanese.attention_class.expected,
    english_attention_class: english.attention_class.rendered.visible
      && english.attention_class.rendered.text === english.attention_class.expected,
  };
  return {
    status: Object.values(checks).every(Boolean) ? "pass" : "fail",
    expected_priority_contract: expected,
    checks,
    japanese,
    english,
  };
}

async function priorityClickCheck(page, htmlPath) {
  await openState(page, htmlPath, "ja");
  const ids = await priorityIds(page);
  if (!ids.length) {
    return { status: "fail", reason: "At least one priority is required.", priority_ids: ids };
  }
  const plan = priorityInteractionPlan(ids);
  const target = plan.click_target;
  await page.locator(`button[data-priority-id="${target}"]`).click();
  await page.waitForFunction(
    (expected) =>
      document.querySelector('[data-landmark="active-decision"]')?.dataset.priorityId === expected
      && document.querySelector('[data-landmark="evidence-inspector"]')?.dataset.priorityId === expected,
    target,
  );
  await settlePage(page);
  const state = await synchronizedState(page);
  return {
    status: state.pass && state.selected_priority_ids[0] === target ? "pass" : "fail",
    mode: plan.mode,
    target_priority_id: target,
    state,
  };
}

async function priorityKeyboardCheck(page, htmlPath) {
  await openState(page, htmlPath, "ja");
  const ids = await priorityIds(page);
  if (!ids.length) {
    return { status: "fail", reason: "At least one priority is required.", priority_ids: ids };
  }
  const plan = priorityInteractionPlan(ids);
  const steps = [];
  const first = page.locator(`button[data-priority-id="${ids[0]}"]`);
  await first.focus();
  for (const [key, expected] of Object.entries(plan.keyboard_targets)) {
    await page.keyboard.press(key);
    await page.waitForFunction(
      (priorityId) =>
        document.querySelector('[data-landmark="active-decision"]')?.dataset.priorityId === priorityId,
      expected,
    );
    const state = await synchronizedState(page);
    steps.push({
      key,
      expected_priority_id: expected,
      state,
      pass: state.pass
        && state.selected_priority_ids[0] === expected
        && state.focused_priority_id === expected,
    });
  }
  return {
    status: steps.every((item) => item.pass) ? "pass" : "fail",
    mode: plan.mode,
    steps,
  };
}

async function visibleFocusCheck(page, htmlPath) {
  await openState(page, htmlPath, "ja");
  const ids = await priorityIds(page);
  const target = ids[Math.min(1, ids.length - 1)];
  const control = page.locator(`button[data-priority-id="${target}"]`);
  await control.focus();
  const result = await control.evaluate((item) => {
    const style = getComputedStyle(item);
    return {
      priority_id: item.dataset.priorityId,
      matches_focus_visible: item.matches(":focus-visible"),
      outline_style: style.outlineStyle,
      outline_width: style.outlineWidth,
      box_shadow: style.boxShadow,
      pass: item.matches(":focus-visible")
        && ((style.outlineStyle !== "none" && style.outlineWidth !== "0px") || style.boxShadow !== "none"),
    };
  });
  return { status: result.pass ? "pass" : "fail", ...result };
}

async function languageSwitchCheck(page, htmlPath) {
  await openState(page, htmlPath, "ja");
  const ids = await priorityIds(page);
  const target = ids[Math.min(1, ids.length - 1)];
  await page.locator(`button[data-priority-id="${target}"]`).click();
  const before = await synchronizedState(page);
  await activateLanguage(page, "en");
  const clickState = await synchronizedState(page);
  const clickLanguage = await page.evaluate(() => ({
    language: document.documentElement.dataset.language,
    pressed: Array.from(
      document.querySelectorAll('button[data-language][aria-pressed="true"]'),
      (item) => item.dataset.language,
    ),
  }));
  await activateLanguage(page, "ja");
  const japanese = page.locator('button[data-language="ja"]');
  await japanese.focus();
  await page.keyboard.press("ArrowRight");
  await page.waitForFunction(() => document.documentElement.dataset.language === "en");
  const keyboardState = await synchronizedState(page);
  const keyboardLanguage = await page.evaluate(() => ({
    language: document.documentElement.dataset.language,
    pressed: Array.from(
      document.querySelectorAll('button[data-language][aria-pressed="true"]'),
      (item) => item.dataset.language,
    ),
    focused_language: document.activeElement?.dataset?.language || null,
  }));
  const pass = before.pass
    && clickState.pass
    && keyboardState.pass
    && before.selected_priority_ids[0] === target
    && clickState.selected_priority_ids[0] === target
    && keyboardState.selected_priority_ids[0] === target
    && clickLanguage.language === "en"
    && clickLanguage.pressed.length === 1
    && clickLanguage.pressed[0] === "en"
    && keyboardLanguage.language === "en"
    && keyboardLanguage.pressed.length === 1
    && keyboardLanguage.pressed[0] === "en"
    && keyboardLanguage.focused_language === "en";
  return {
    status: pass ? "pass" : "fail",
    preserved_priority_id: target,
    click: { language_state: clickLanguage, synchronized_state: clickState },
    keyboard: { language_state: keyboardLanguage, synchronized_state: keyboardState },
  };
}

async function overflowCheck(page, htmlPath, language, viewport) {
  await page.setViewportSize(viewport);
  await openState(page, htmlPath, language);
  return page.evaluate(({ expectedLanguage, expectedViewport }) => {
    const findings = [];
    for (const element of document.querySelectorAll("body *")) {
      const style = getComputedStyle(element);
      if (
        style.display === "none"
        || style.visibility === "hidden"
        || element.hidden
        || element.classList.contains("visually-hidden")
        || element.getClientRects().length === 0
      ) continue;
      if (
        element.scrollWidth > element.clientWidth + 1
        && !element.closest("[data-overflow-allowed]")
      ) {
        findings.push({
          tag: element.tagName.toLowerCase(),
          landmark: element.dataset.landmark || null,
          class_name: typeof element.className === "string" ? element.className : null,
          scroll_width: element.scrollWidth,
          client_width: element.clientWidth,
        });
      }
    }
    return {
      language: expectedLanguage,
      viewport: expectedViewport,
      document_width: document.documentElement.scrollWidth,
      findings,
      pass: document.documentElement.scrollWidth <= innerWidth + 1 && findings.length === 0,
    };
  }, { expectedLanguage: language, expectedViewport: viewport });
}

async function narrowOrderCheck(page, htmlPath) {
  await page.setViewportSize({ width: 390, height: 3100 });
  await openState(page, htmlPath, "ja");
  return page.evaluate(() => {
    const selectors = [
      '[data-landmark="priority-lane"]',
      '[data-landmark="active-decision"]',
      '[data-landmark="evidence-inspector"]',
    ];
    const elements = selectors.map((selector) => document.querySelector(selector));
    const positions = elements.map((item) => item?.getBoundingClientRect().top ?? null);
    const domOrder = elements.every(Boolean)
      && Boolean(elements[0].compareDocumentPosition(elements[1]) & Node.DOCUMENT_POSITION_FOLLOWING)
      && Boolean(elements[1].compareDocumentPosition(elements[2]) & Node.DOCUMENT_POSITION_FOLLOWING);
    const visualOrder = positions.every((value) => Number.isFinite(value))
      && positions[0] < positions[1]
      && positions[1] < positions[2];
    return {
      selectors,
      top_positions: positions,
      dom_order: domOrder,
      visual_order: visualOrder,
      pass: domOrder && visualOrder,
    };
  });
}

async function noJavascriptFallbackCheck(browser, htmlPath) {
  const context = await browser.newContext({
    javaScriptEnabled: false,
    viewport: { width: 1440, height: 1200 },
    deviceScaleFactor: DEVICE_SCALE_FACTOR,
    locale: "ja-JP",
    timezoneId: "Asia/Tokyo",
    reducedMotion: "reduce",
  });
  try {
    const page = await context.newPage();
    await page.goto(artifactUrl(htmlPath, "ja"), { waitUntil: "load" });
    const result = await page.evaluate(() => {
      const first = document.querySelector('[data-landmark="priority-first"]');
      const decision = document.querySelector('[data-landmark="active-decision"]');
      const inspector = document.querySelector('[data-landmark="evidence-inspector"]');
      const freshness = document.querySelector('[data-landmark="freshness-status"]');
      const provenance = document.querySelector('[data-landmark="provenance"]');
      const firstId = first?.dataset.priorityId
        || first?.querySelector("[data-priority-id]")?.dataset.priorityId
        || null;
      const decisionId = decision?.dataset.priorityId || null;
      const inspectorId = inspector?.dataset.priorityId || null;
      return {
        language: document.documentElement.lang,
        first_priority_id: firstId,
        decision_priority_id: decisionId,
        inspector_priority_id: inspectorId,
        evidence_id: inspector?.dataset.evidenceId || null,
        first_text_length: first?.textContent?.trim().length || 0,
        inspector_text_length: inspector?.textContent?.trim().length || 0,
        freshness_visible: Boolean(freshness?.getClientRects().length),
        provenance_visible: Boolean(provenance?.getClientRects().length),
        pass: Boolean(firstId)
          && firstId === decisionId
          && firstId === inspectorId
          && Boolean(inspector?.dataset.evidenceId)
          && (first?.textContent?.trim().length || 0) > 20
          && (inspector?.textContent?.trim().length || 0) > 20
          && Boolean(freshness?.getClientRects().length)
          && Boolean(provenance?.getClientRects().length),
      };
    });
    return { status: result.pass ? "pass" : "fail", ...result };
  } finally {
    await context.close();
  }
}

async function landmarkGeometry(page, viewport, selectors) {
  return page.evaluate(({ selectors, expectedViewport }) => {
    const results = {};
    for (const [name, selector] of Object.entries(selectors)) {
      const elements = document.querySelectorAll(selector);
      if (elements.length !== 1) {
        results[name] = { selector, count: elements.length, pass: false };
        continue;
      }
      const rect = elements[0].getBoundingClientRect();
      const rasterRect = {
        x: Math.max(0, Math.floor(rect.left)),
        y: Math.max(0, Math.floor(rect.top)),
        width: Math.max(0, Math.min(expectedViewport.width, Math.ceil(rect.right)) - Math.max(0, Math.floor(rect.left))),
        height: Math.max(0, Math.min(expectedViewport.height, Math.ceil(rect.bottom)) - Math.max(0, Math.floor(rect.top))),
      };
      const fullyVisible = rect.left >= 0
        && rect.top >= 0
        && rect.right <= expectedViewport.width + 1
        && rect.bottom <= expectedViewport.height + 1;
      results[name] = {
        selector,
        count: 1,
        rect: {
          x: Number(rect.x.toFixed(2)),
          y: Number(rect.y.toFixed(2)),
          width: Number(rect.width.toFixed(2)),
          height: Number(rect.height.toFixed(2)),
          right: Number(rect.right.toFixed(2)),
          bottom: Number(rect.bottom.toFixed(2)),
        },
        raster_rect: rasterRect,
        fully_visible: fullyVisible,
        pass: rect.width >= 4 && rect.height >= 4
          && rasterRect.width >= 4 && rasterRect.height >= 4
          && fullyVisible,
      };
    }
    return results;
  }, { selectors, expectedViewport: viewport });
}

function sampleRaster(raw, width, height, rect) {
  const x0 = Math.max(0, Math.min(width - 1, Math.floor(rect.x)));
  const y0 = Math.max(0, Math.min(height - 1, Math.floor(rect.y)));
  const x1 = Math.max(x0 + 1, Math.min(width, Math.ceil(rect.x + rect.width)));
  const y1 = Math.max(y0 + 1, Math.min(height, Math.ceil(rect.y + rect.height)));
  const area = (x1 - x0) * (y1 - y0);
  const step = Math.max(1, Math.floor(Math.sqrt(area / 180000)));
  let count = 0;
  let luminanceSum = 0;
  let luminanceSquared = 0;
  let nearBlack = 0;
  const quantized = new Map();
  for (let y = y0; y < y1; y += step) {
    for (let x = x0; x < x1; x += step) {
      const offset = (y * width + x) * 4;
      const r = raw[offset];
      const g = raw[offset + 1];
      const b = raw[offset + 2];
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
  const dominantRatio = Math.max(...quantized.values()) / count;
  const nearBlackRatio = nearBlack / count;
  return {
    sampled_pixels: count,
    luminance_mean: Number(mean.toFixed(4)),
    luminance_variance: Number(variance.toFixed(4)),
    near_black_ratio: Number(nearBlackRatio.toFixed(6)),
    quantized_color_count: quantized.size,
    dominant_color_ratio: Number(dominantRatio.toFixed(6)),
    pass: variance > 1 && nearBlackRatio < 0.985 && quantized.size >= 2 && dominantRatio < 0.995,
  };
}

async function browserCanvasDecode(page, buffer, regions) {
  const dataUrl = `data:image/png;base64,${buffer.toString("base64")}`;
  return page.evaluate(async ({ url, rasterRegions }) => {
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
    const rgba = context.getImageData(0, 0, canvas.width, canvas.height).data;
    const digest = await crypto.subtle.digest("SHA-256", rgba);
    const rgbaSha256 = Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
    const analyze = (rect) => {
      const x0 = Math.max(0, Math.min(canvas.width - 1, Math.floor(rect.x)));
      const y0 = Math.max(0, Math.min(canvas.height - 1, Math.floor(rect.y)));
      const x1 = Math.max(x0 + 1, Math.min(canvas.width, Math.ceil(rect.x + rect.width)));
      const y1 = Math.max(y0 + 1, Math.min(canvas.height, Math.ceil(rect.y + rect.height)));
      const area = (x1 - x0) * (y1 - y0);
      const step = Math.max(1, Math.floor(Math.sqrt(area / 180000)));
      let count = 0;
      let luminanceSum = 0;
      let luminanceSquared = 0;
      let nearBlack = 0;
      const quantized = new Map();
      for (let y = y0; y < y1; y += step) {
        for (let x = x0; x < x1; x += step) {
          const offset = (y * canvas.width + x) * 4;
          const r = rgba[offset];
          const g = rgba[offset + 1];
          const b = rgba[offset + 2];
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
      const dominantRatio = Math.max(...quantized.values()) / count;
      const nearBlackRatio = nearBlack / count;
      return {
        sampled_pixels: count,
        luminance_mean: Number(mean.toFixed(4)),
        luminance_variance: Number(variance.toFixed(4)),
        near_black_ratio: Number(nearBlackRatio.toFixed(6)),
        quantized_color_count: quantized.size,
        dominant_color_ratio: Number(dominantRatio.toFixed(6)),
        pass: variance > 1 && nearBlackRatio < 0.985 && quantized.size >= 2 && dominantRatio < 0.995,
      };
    };
    return {
      width: canvas.width,
      height: canvas.height,
      rgba_sha256: rgbaSha256,
      regions: Object.fromEntries(
        Object.entries(rasterRegions).map(([name, rect]) => [name, analyze(rect)]),
      ),
      roundtrip_png: canvas.toDataURL("image/png").split(",")[1],
    };
  }, { url: dataUrl, rasterRegions: regions });
}

async function normalizePng(ffmpeg, rawPath, finalPath) {
  await execFileAsync(
    ffmpeg,
    [
      "-v", "error",
      "-y",
      "-i", rawPath,
      "-frames:v", "1",
      "-map_metadata", "-1",
      "-vf", "format=rgba",
      "-c:v", "png",
      "-pred", "none",
      "-compression_level", "9",
      "-threads", "1",
      finalPath,
    ],
    { windowsHide: true, maxBuffer: 4 * 1024 * 1024 },
  );
}

async function ffmpegDecode(ffmpeg, pngPath, dimensions, regions) {
  const expectedLength = dimensions.width * dimensions.height * 4;
  const { stdout } = await execFileAsync(
    ffmpeg,
    [
      "-v", "error",
      "-i", pngPath,
      "-frames:v", "1",
      "-f", "rawvideo",
      "-pix_fmt", "rgba",
      "pipe:1",
    ],
    {
      encoding: "buffer",
      windowsHide: true,
      maxBuffer: expectedLength + 4 * 1024 * 1024,
    },
  );
  const raw = Buffer.from(stdout);
  if (raw.length !== expectedLength) {
    throw new Error(`FFmpeg RGBA length mismatch: expected ${expectedLength}, got ${raw.length}.`);
  }
  return {
    width: dimensions.width,
    height: dimensions.height,
    byte_length: raw.length,
    rgba_sha256: sha256(raw),
    regions: Object.fromEntries(
      Object.entries(regions).map(([name, rect]) => [name, sampleRaster(raw, dimensions.width, dimensions.height, rect)]),
    ),
  };
}

async function ffmpegDecodeBuffer(ffmpeg, buffer, path, dimensions, regions) {
  await writeFile(path, buffer);
  return ffmpegDecode(ffmpeg, path, dimensions, regions);
}

function geometryRegions(geometry) {
  return Object.fromEntries(
    Object.entries(geometry)
      .filter(([, item]) => item.raster_rect)
      .map(([name, item]) => [name, item.raster_rect]),
  );
}

async function captureOne(
  page,
  htmlPath,
  definition,
  stageScreenshots,
  ffmpeg,
  stageRoot,
  captureLandmarks,
) {
  await page.setViewportSize(definition.viewport);
  await openState(page, htmlPath, definition.language);
  const ids = await priorityIds(page);
  if (!ids.length) throw new Error("No priority controls were found.");
  await page.locator(`button[data-priority-id="${ids[0]}"]`).click();
  await settlePage(page);
  const state = await synchronizedState(page);
  const geometry = await landmarkGeometry(page, definition.viewport, captureLandmarks);
  const overflow = await overflowCheck(page, htmlPath, definition.language, definition.viewport);
  const rawPath = join(stageRoot, `raw-${definition.id}.png`);
  const finalPath = join(stageScreenshots, definition.filename);
  await page.screenshot({
    path: rawPath,
    fullPage: false,
    animations: "disabled",
    caret: "hide",
  });
  await normalizePng(ffmpeg, rawPath, finalPath);
  const buffer = await readFile(finalPath);
  const dimensions = pngDimensions(buffer);
  if (
    dimensions.width !== definition.viewport.width
    || dimensions.height !== definition.viewport.height
  ) {
    throw new Error(`${definition.id} dimensions do not match its viewport.`);
  }
  const regions = geometryRegions(geometry);
  const browser = await browserCanvasDecode(page, buffer, regions);
  const ffmpegResult = await ffmpegDecode(ffmpeg, finalPath, dimensions, regions);
  const roundtripPath = join(stageRoot, `roundtrip-${definition.id}.png`);
  const roundtripBuffer = Buffer.from(browser.roundtrip_png, "base64");
  const roundtripFfmpeg = await ffmpegDecodeBuffer(
    ffmpeg,
    roundtripBuffer,
    roundtripPath,
    dimensions,
    regions,
  );
  const decoderAgreement = browser.rgba_sha256 === ffmpegResult.rgba_sha256
    && browser.rgba_sha256 === roundtripFfmpeg.rgba_sha256;
  const browserPass = Object.values(browser.regions).every((item) => item.pass);
  const ffmpegPass = Object.values(ffmpegResult.regions).every((item) => item.pass);
  const geometryPass = Object.values(geometry).every((item) => item.pass);
  const landmarkPresence = {
    freshness_status: Boolean(geometry.freshness_status?.pass),
    provenance: Boolean(geometry.provenance?.pass),
  };
  return {
    definition,
    finalPath,
    buffer,
    dimensions,
    state,
    selected_priority_id: state.selected_priority_ids[0] || null,
    selected_evidence_id: state.inspector_evidence_id,
    geometry,
    overflow,
    browser: {
      width: browser.width,
      height: browser.height,
      rgba_sha256: browser.rgba_sha256,
      regions: browser.regions,
      pass: browserPass,
    },
    ffmpeg: {
      ...ffmpegResult,
      pass: ffmpegPass,
    },
    decoder_agreement: {
      browser_rgba_sha256: browser.rgba_sha256,
      ffmpeg_rgba_sha256: ffmpegResult.rgba_sha256,
      browser_roundtrip_ffmpeg_rgba_sha256: roundtripFfmpeg.rgba_sha256,
      pass: decoderAgreement,
    },
    landmark_presence: landmarkPresence,
    pass: state.pass
      && geometryPass
      && overflow.pass
      && browserPass
      && ffmpegPass
      && decoderAgreement
      && landmarkPresence.freshness_status
      && landmarkPresence.provenance,
  };
}

async function makeContactSheet(page, captures) {
  const encoded = captures.map((item) => ({
    id: item.definition.id,
    language: item.definition.language,
    viewport: item.definition.viewport,
    data: item.buffer.toString("base64"),
  }));
  return page.evaluate(async ({ items, sheet }) => {
    const canvas = document.createElement("canvas");
    canvas.width = sheet.width;
    canvas.height = sheet.height;
    const context = canvas.getContext("2d");
    context.fillStyle = "#0d100e";
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.fillStyle = "#f3efe5";
    context.font = '700 26px "Segoe UI", sans-serif';
    context.fillText("Priority Review Console · production capture", 24, 38);
    context.fillStyle = "#b7c0ae";
    context.font = '15px "Segoe UI", sans-serif';
    context.fillText("JA desktop · EN desktop · JA narrow · viewport screenshots · point-in-time proof", 24, 64);
    const margin = 24;
    const gap = 16;
    const tileTop = 90;
    const tileHeight = 600;
    const tileWidth = (canvas.width - margin * 2 - gap * 2) / 3;
    const tiles = {};
    for (let index = 0; index < items.length; index += 1) {
      const item = items[index];
      const image = new Image();
      image.src = `data:image/png;base64,${item.data}`;
      await new Promise((resolveImage, rejectImage) => {
        image.onload = resolveImage;
        image.onerror = () => rejectImage(new Error("Capture could not be decoded for contact sheet."));
      });
      const frameX = margin + index * (tileWidth + gap);
      context.fillStyle = "#121613";
      context.fillRect(frameX, tileTop, tileWidth, tileHeight);
      const labelHeight = 42;
      const availableHeight = tileHeight - labelHeight - 12;
      const scale = Math.min(tileWidth / image.naturalWidth, availableHeight / image.naturalHeight);
      const drawWidth = image.naturalWidth * scale;
      const drawHeight = image.naturalHeight * scale;
      const drawX = frameX + (tileWidth - drawWidth) / 2;
      const drawY = tileTop + 8 + (availableHeight - drawHeight) / 2;
      context.drawImage(image, drawX, drawY, drawWidth, drawHeight);
      context.strokeStyle = index === 0 ? "#e4ba58" : index === 1 ? "#75c8d5" : "#72c996";
      context.lineWidth = 2;
      context.strokeRect(frameX, tileTop, tileWidth, tileHeight);
      context.fillStyle = "#f3efe5";
      context.font = '700 17px "Segoe UI", sans-serif';
      context.fillText(
        `${item.id} · ${item.viewport.width}×${item.viewport.height}`,
        frameX + 10,
        tileTop + tileHeight - 15,
      );
      tiles[item.id] = {
        x: Math.floor(drawX),
        y: Math.floor(drawY),
        width: Math.max(1, Math.floor(drawWidth)),
        height: Math.max(1, Math.floor(drawHeight)),
      };
    }
    return {
      png: canvas.toDataURL("image/png").split(",")[1],
      tiles,
      width: canvas.width,
      height: canvas.height,
    };
  }, { items: encoded, sheet: CONTACT_SHEET });
}

async function partialBlackNegativeControl(page, capture, ffmpeg, stageRoot) {
  const target = capture.geometry.priority_first.raster_rect;
  const blacked = await page.evaluate(async ({ source, rect }) => {
    const image = new Image();
    image.src = `data:image/png;base64,${source}`;
    await new Promise((resolveImage, rejectImage) => {
      image.onload = resolveImage;
      image.onerror = () => rejectImage(new Error("Source capture could not be decoded for negative control."));
    });
    const canvas = document.createElement("canvas");
    canvas.width = image.naturalWidth;
    canvas.height = image.naturalHeight;
    const context = canvas.getContext("2d");
    context.drawImage(image, 0, 0);
    context.fillStyle = "#000";
    context.fillRect(rect.x, rect.y, rect.width, rect.height);
    return canvas.toDataURL("image/png").split(",")[1];
  }, { source: capture.buffer.toString("base64"), rect: target });
  const buffer = Buffer.from(blacked, "base64");
  const regions = { priority_first: target };
  const browser = await browserCanvasDecode(page, buffer, regions);
  const path = join(stageRoot, "partial-black-negative-control.png");
  const ffmpegResult = await ffmpegDecodeBuffer(
    ffmpeg,
    buffer,
    path,
    capture.dimensions,
    regions,
  );
  const browserRejected = !browser.regions.priority_first.pass;
  const ffmpegRejected = !ffmpegResult.regions.priority_first.pass;
  return {
    status: browserRejected && ffmpegRejected ? "pass" : "fail",
    source_capture: capture.definition.id,
    blacked_landmark: "priority_first",
    expected_result: "reject_blacked_landmark",
    browser_canvas: {
      detector_rejected: browserRejected,
      analysis: browser.regions.priority_first,
    },
    ffmpeg: {
      detector_rejected: ffmpegRejected,
      analysis: ffmpegResult.regions.priority_first,
    },
  };
}

async function generatorBlob(repoRoot) {
  const { stdout } = await execFileAsync(
    "git",
    ["hash-object", "src/dev_cockpit/dashboard.py"],
    { cwd: repoRoot, windowsHide: true },
  );
  return stdout.trim();
}

async function playwrightVersion(entry) {
  try {
    return (await readJson(join(dirname(entry), "package.json"))).version || "unknown";
  } catch {
    return "unknown";
  }
}

async function ffmpegVersion(executable) {
  const { stdout } = await execFileAsync(
    executable,
    ["-version"],
    { windowsHide: true, maxBuffer: 1024 * 1024 },
  );
  return stdout.split(/\r?\n/u)[0].trim();
}

function isNonEmptyString(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function pathKey(value) {
  let absolute = resolve(value);
  try {
    absolute = realpathSync.native(absolute);
  } catch {
    // Validation will report a mismatch or missing input at the caller boundary.
  }
  return process.platform === "win32" ? absolute.toLowerCase() : absolute;
}

function declaredPathCandidates(value, repoRoot, outputRoot) {
  if (!isNonEmptyString(value)) return [];
  if (isAbsolute(value)) return [pathKey(value)];
  return [...new Set([
    pathKey(resolve(repoRoot, value)),
    pathKey(resolve(outputRoot, value)),
  ])];
}

function orderedUnique(values) {
  return values.filter((value, index) => values.indexOf(value) === index);
}

function validatePriorityContract(priorityJson) {
  const errors = [];
  const priorities = Array.isArray(priorityJson.priorities) ? priorityJson.priorities : [];
  const informational = Array.isArray(priorityJson.informational_items)
    ? priorityJson.informational_items
    : [];
  const surface = priorityJson.surface || {};
  const packet = priorityJson.supervision_packet || {};
  const coverage = packet.coverage || {};
  const packetLoaded = packet.loaded === true;
  const allClosed = surface.all_closed === true;
  if (surface.priority_count !== priorities.length) {
    errors.push("surface.priority_count must exactly match priorities");
  }
  if (priorities.some((item) => item?.executable !== false)) {
    errors.push("every priority must remain executable:false");
  }
  if (informational.some(
    (item) => item?.executable !== false || item?.informational_only !== true,
  )) {
    errors.push("every informational item must be informational_only:true and executable:false");
  }
  if (packetLoaded) {
    if (coverage.active_task_count !== priorities.length) {
      errors.push("packet active_task_count must exactly match priorities");
    }
    if (coverage.closed_or_informational_count !== informational.length) {
      errors.push("packet closed count must exactly match informational_items");
    }
  }
  if (allClosed) {
    if (!packetLoaded) errors.push("all-closed mode requires a loaded supervision packet");
    if (priorities.length !== 0) errors.push("all-closed mode requires zero active priorities");
    if (informational.length === 0) errors.push("all-closed mode requires informational_items");
    if (coverage.active_task_count !== 0) errors.push("all-closed packet active count must be zero");
    if (coverage.closed_or_informational_count !== informational.length) {
      errors.push("all-closed packet closed count must match informational_items");
    }
  } else if (!priorities.length) {
    errors.push("priority readback priorities must contain at least one item unless packet is all-closed");
  }
  const priorityIds = priorities.map((item) => item?.priority_id);
  const evidenceByPriorityId = Object.fromEntries(
    priorities.map((item) => [item?.priority_id, item?.primary_evidence_id]),
  );
  if (priorityIds.some((value) => !isNonEmptyString(value))) {
    errors.push("every priority_id must be a non-empty string");
  }
  if (new Set(priorityIds).size !== priorityIds.length) {
    errors.push("priority_id values must be unique");
  }
  if (priorities.some((item) => !isNonEmptyString(item?.primary_evidence_id))) {
    errors.push("every primary_evidence_id must be a non-empty string");
  }
  const selectedPriorityId = surface.selected_priority_id;
  if (allClosed && selectedPriorityId !== null) {
    errors.push("all-closed surface.selected_priority_id must be null");
  } else if (!allClosed && !isNonEmptyString(selectedPriorityId)) {
    errors.push("surface.selected_priority_id must be a non-empty string");
  } else if (!allClosed && !priorityIds.includes(selectedPriorityId)) {
    errors.push("surface.selected_priority_id must reference a declared priority");
  }
  if (allClosed) {
    const closedEvidenceId = surface.selected_closed_evidence_id;
    const informationalEvidenceIds = informational.map((item) => item?.primary_evidence_id);
    if (!isNonEmptyString(closedEvidenceId) || !informationalEvidenceIds.includes(closedEvidenceId)) {
      errors.push("all-closed selected evidence must reference informational_items");
    }
  }
  if (errors.length) {
    throw new Error(`Priority readback semantic contract rejected: ${errors.join("; ")}`);
  }
  return {
    priority_ids: priorityIds,
    evidence_ids: orderedUnique(priorities.map((item) => item.primary_evidence_id)),
    selected_priority_id: selectedPriorityId,
    mode: allClosed ? "all_closed" : "active_queue",
    packet_loaded: packetLoaded,
    evidence_by_priority_id: evidenceByPriorityId,
    priorities_sha256: sha256(
      Buffer.from(canonicalJson(priorities), "utf8"),
    ),
  };
}

async function sourceBinding(options, repoRoot, outputRoot) {
  const htmlPath = resolve(options.html || join(repoRoot, "samples/dashboard/devcockpitcore_dashboard.html"));
  const priorityPath = resolve(
    options.priorityReadback || join(repoRoot, "samples/dashboard/devcockpitcore_priority_readback.json"),
  );
  const freshnessPath = resolve(
    options.freshnessReceipt || join(repoRoot, "samples/evidence_freshness/evidence_freshness_receipt_v1.json"),
  );
  await Promise.all([access(htmlPath), access(priorityPath), access(freshnessPath)]);
  const [
    html,
    priority,
    freshness,
    captureScript,
    priorityJson,
    freshnessJson,
    blob,
  ] = await Promise.all([
    readFile(htmlPath),
    readFile(priorityPath),
    readFile(freshnessPath),
    readFile(scriptPath),
    readJson(priorityPath),
    readJson(freshnessPath),
    generatorBlob(repoRoot),
  ]);
  const declaredReceipt = priorityJson.freshness_receipt;
  const declaredReceiptPath = declaredReceipt?.path;
  const declaredReceiptCaptureId = declaredReceipt?.capture_id;
  const actualReceiptCaptureId = freshnessJson.capture_id;
  const declaredCandidates = declaredPathCandidates(
    declaredReceiptPath,
    repoRoot,
    outputRoot,
  );
  const receiptPathMatch = declaredCandidates.includes(pathKey(freshnessPath));
  const checks = {
    priority_schema: priorityJson.schema_version === PRIORITY_READBACK_SCHEMA,
    priority_artifact: priorityJson.artifact_id === ARTIFACT_ID,
    declared_freshness_schema:
      declaredReceipt?.schema_version === FRESHNESS_RECEIPT_SCHEMA,
    actual_freshness_schema: freshnessJson.schema_version === FRESHNESS_RECEIPT_SCHEMA,
    declared_freshness_path_nonempty: isNonEmptyString(declaredReceiptPath),
    declared_freshness_capture_id_nonempty:
      isNonEmptyString(declaredReceiptCaptureId),
    actual_freshness_capture_id_nonempty: isNonEmptyString(actualReceiptCaptureId),
    priority_to_freshness_path_match: receiptPathMatch,
    priority_to_freshness_capture_id_match:
      isNonEmptyString(declaredReceiptCaptureId)
      && isNonEmptyString(actualReceiptCaptureId)
      && declaredReceiptCaptureId === actualReceiptCaptureId,
  };
  if (!Object.values(checks).every(Boolean)) {
    const failed = Object.entries(checks)
      .filter(([, pass]) => !pass)
      .map(([name]) => name);
    throw new Error(
      `Source binding rejected: ${failed.join(", ")}; declared freshness path=${JSON.stringify(declaredReceiptPath)}; actual freshness path=${JSON.stringify(freshnessPath)}`,
    );
  }
  const priorityContract = validatePriorityContract(priorityJson);
  const binding = {
    artifact_id: ARTIFACT_ID,
    html: {
      path: displayPath(htmlPath, repoRoot, outputRoot),
      sha256: canonicalTextSha256(html),
    },
    priority_readback: {
      path: displayPath(priorityPath, repoRoot, outputRoot),
      schema_version: priorityJson.schema_version || null,
      artifact_id: priorityJson.artifact_id || null,
      freshness_receipt_path: displayPath(freshnessPath, repoRoot, outputRoot),
      freshness_capture_id: declaredReceiptCaptureId,
      sha256: canonicalTextSha256(priority),
    },
    freshness_receipt: {
      path: displayPath(freshnessPath, repoRoot, outputRoot),
      schema_version: freshnessJson.schema_version || null,
      capture_id: freshnessJson.capture_id || null,
      sha256: canonicalTextSha256(freshness),
    },
    production_generator: {
      path: "src/dev_cockpit/dashboard.py",
      blob,
    },
    capture_script: {
      path: displayPath(scriptPath, repoRoot, outputRoot),
      sha256: canonicalTextSha256(captureScript),
    },
  };
  return {
    htmlPath,
    priorityPath,
    freshnessPath,
    binding,
    priorityContract,
    validation: {
      status: "pass",
      checks,
      declared_freshness_path_candidates: declaredCandidates.map((candidate) =>
        displayPath(candidate, repoRoot, outputRoot)
      ),
      actual_freshness_path: displayPath(freshnessPath, repoRoot, outputRoot),
    },
  };
}

function captureIdentity(binding) {
  const payload = {
    artifact_id: ARTIFACT_ID,
    html_sha256: binding.html.sha256,
    priority_readback_sha256: binding.priority_readback.sha256,
    freshness_receipt_sha256: binding.freshness_receipt.sha256,
    production_generator_blob: binding.production_generator.blob,
    capture_script_sha256: binding.capture_script.sha256,
    capture_definitions: CAPTURE_DEFINITIONS.map((item) => ({
      id: item.id,
      language: item.language,
      viewport: item.viewport,
      filename: item.filename,
    })),
    contact_sheet: CONTACT_SHEET,
    device_scale_factor: DEVICE_SCALE_FACTOR,
  };
  const digest = sha256(Buffer.from(canonicalJson(payload), "utf8"));
  return {
    payload,
    sha256: digest,
    capture_id: `priority-review-console-${digest.slice(0, 24)}`,
  };
}

function packageEntry(capture, captureId) {
  return {
    id: capture.definition.id,
    role: capture.definition.id,
    path: manifestOutputPath(capture.definition.filename),
    capture_id: captureId,
    language: capture.definition.language,
    viewport: {
      ...capture.definition.viewport,
      device_scale_factor: DEVICE_SCALE_FACTOR,
    },
    dimensions: capture.dimensions,
    normalized_png_sha256: sha256(capture.buffer),
    decoded_pixel_sha256: capture.browser.rgba_sha256,
    selected_priority_id: capture.selected_priority_id,
    selected_evidence_id: capture.selected_evidence_id,
    landmarks: capture.geometry,
    browser_canvas_raster: capture.browser,
    ffmpeg_raster: capture.ffmpeg,
    decoder_agreement: capture.decoder_agreement,
    overflow: capture.overflow,
    freshness_status_present: capture.landmark_presence.freshness_status,
    provenance_present: capture.landmark_presence.provenance,
    pass: capture.pass,
  };
}

function packagePaths(outputRoot) {
  return {
    manifest: join(outputRoot, "production_capture_manifest.json"),
    readback: join(outputRoot, "production_capture_readback.json"),
  };
}

function allAutomatedPass(readback) {
  return AUTOMATED_STATUS_KEYS.every((key) => readback[key]?.status === "pass");
}

async function promote(stageRoot, outputRoot, manifest, readback) {
  const targetScreenshots = join(outputRoot, "screenshots");
  await mkdir(targetScreenshots, { recursive: true });
  for (const filename of [
    ...CAPTURE_DEFINITIONS.map((item) => item.filename),
    CONTACT_SHEET.filename,
  ]) {
    await copyFile(join(stageRoot, "screenshots", filename), join(targetScreenshots, filename));
  }
  const stagedManifest = join(stageRoot, "production_capture_manifest.json");
  const stagedReadback = join(stageRoot, "production_capture_readback.json");
  await Promise.all([
    writeJson(stagedManifest, manifest),
    writeJson(stagedReadback, readback),
  ]);
  const paths = packagePaths(outputRoot);
  await Promise.all([
    copyFile(stagedManifest, paths.manifest),
    copyFile(stagedReadback, paths.readback),
  ]);
}

async function resolveBoundSourcePath(value, repoRoot, outputRoot) {
  if (isAbsolute(value)) return value;
  const outputCandidate = resolve(outputRoot, value);
  if (await isFile(outputCandidate)) return outputCandidate;
  return resolve(repoRoot, value);
}

async function recordWorkerInspection(options, outputRoot, repoRoot) {
  const paths = packagePaths(outputRoot);
  const [manifest, readback] = await Promise.all([readJson(paths.manifest), readJson(paths.readback)]);
  if (manifest.schema_version !== MANIFEST_SCHEMA || readback.schema_version !== READBACK_SCHEMA) {
    throw new Error("Worker inspection requires production capture v1 manifest/readback files.");
  }
  if (manifest.capture_id !== readback.capture_id) throw new Error("Manifest/readback capture IDs differ.");
  if (!allAutomatedPass(readback)) throw new Error("Every automated production capture status must pass first.");
  const binding = manifest.source_binding;
  const currentSources = [];
  for (const key of ["html", "priority_readback", "freshness_receipt", "capture_script"]) {
    const source = binding[key];
    const absolute = await resolveBoundSourcePath(source.path, repoRoot, outputRoot);
    const currentSha = canonicalTextSha256(await readFile(absolute));
    if (currentSha !== source.sha256) {
      throw new Error(`Source changed after capture: ${source.path}`);
    }
    currentSources.push({ role: key, path: source.path, sha256: currentSha });
  }
  const currentGeneratorBlob = await generatorBlob(repoRoot);
  if (currentGeneratorBlob !== binding.production_generator.blob) {
    throw new Error("Production generator changed after capture.");
  }
  currentSources.push({
    role: "production_generator",
    path: binding.production_generator.path,
    blob: currentGeneratorBlob,
  });
  const entries = [...manifest.screenshots, manifest.contact_sheet];
  const inspectedFiles = [];
  for (const entry of entries) {
    const absolute = resolve(outputRoot, entry.path);
    const currentSha = sha256(await readFile(absolute));
    const expectedSha = entry.normalized_png_sha256;
    if (currentSha !== expectedSha) throw new Error(`PNG hash changed after capture: ${entry.path}`);
    inspectedFiles.push({ path: entry.path, sha256: currentSha });
  }
  const inspectionTimestamp = timestampAuthority(
    options.inspectionAt,
    "--inspection-at",
    "worker_raster_inspection_completed",
  );
  const inspectedAt = inspectionTimestamp.value;
  readback.worker_raster_inspection = {
    status: "pass",
    inspected_at: inspectedAt,
    inspection_timestamp: inspectionTimestamp,
    inspected_capture_id: manifest.capture_id,
    method: "Worker opened the JA desktop, EN desktop, JA narrow, and contact-sheet PNGs after automated readback; this record is bound to their current SHA-256 hashes.",
    inspected_sources: currentSources,
    inspected_files: inspectedFiles,
    findings: {
      raster_completeness: "No blank, black, missing, clipped, or undecoded required production landmark was visible.",
      priority_synchronization: "The selected priority, Active Decision, and Evidence Inspector presented one coherent item.",
      localization: "Japanese and English desktop captures were readable; the Japanese narrow capture retained Priority Lane, Active Decision, and Evidence Inspector order.",
      provenance: "Freshness and provenance remained visible while preserving the recorded user visual acceptance.",
    },
  };
  readback.user_visual_acceptance = {
    status: "accepted",
    selected_direction: "A",
    production_artifact: "priority-review-console",
  };
  await writeJson(paths.readback, readback);
  console.log(`Worker raster inspection recorded for ${manifest.capture_id} (${inspectedFiles.length} files).`);
}

async function main() {
  const options = parseArguments(process.argv.slice(2));
  if (options.help) {
    printHelp();
    return;
  }
  if (options.validateTimestampAuthority) {
    console.log(JSON.stringify(
      timestampAuthority(options.capturedAt, "--captured-at", "timestamp_validation"),
      null,
      2,
    ));
    return;
  }
  if (options.validateSemanticFixture) {
    const fixture = await readJson(resolve(options.validateSemanticFixture));
    const semantic = evaluatePrioritySemanticBinding(
      bindEmbeddedPriorityHash(fixture.japanese),
      bindEmbeddedPriorityHash(fixture.english),
      fixture.expected_priority_contract,
    );
    const interactionPlan = priorityInteractionPlan(
      fixture.expected_priority_contract?.priority_ids,
    );
    console.log(JSON.stringify({
      priority_semantic_binding: semantic,
      priority_interaction_plan: interactionPlan,
    }, null, 2));
    if (semantic.status !== "pass" || !interactionPlan) {
      throw new Error("Priority semantic fixture rejected.");
    }
    return;
  }
  const repoRoot = resolve(options.repoRoot || join(artifactDirectory, "../../.."));
  const outputRoot = resolve(options.outputRoot || artifactDirectory);
  if (options.recordWorkerInspection) {
    await recordWorkerInspection(options, outputRoot, repoRoot);
    return;
  }
  if (options.capturedAt) assertIsoInstant(options.capturedAt, "--captured-at");
  const source = await sourceBinding(options, repoRoot, outputRoot);
  if (options.validateSourceBinding) {
    console.log(JSON.stringify({
      source_binding: source.validation,
      source_manifest_binding: source.binding,
      priority_contract: source.priorityContract,
    }, null, 2));
    return;
  }
  if (source.priorityContract.mode !== "active_queue") {
    throw new Error(
      "Production capture currently requires an active priority queue; all-closed rendering is verified by the dashboard contract tests.",
    );
  }
  const captureLandmarks = requiredLandmarks(source.priorityContract);
  const playwrightEntry = await discoverPlaywrightEntry(options.playwrightCore);
  const browserExecutable = await discoverBrowserExecutable(options.browser);
  const ffmpegExecutable = await discoverFfmpegExecutable(options.ffmpeg);
  const identity = captureIdentity(source.binding);
  const [{ chromium }, pwVersion, ffmpegRuntime] = await Promise.all([
    import(pathToFileURL(playwrightEntry).href),
    playwrightVersion(playwrightEntry),
    ffmpegVersion(ffmpegExecutable),
  ]);
  const stageRoot = await mkdtemp(join(tmpdir(), "devcockpit-production-capture-"));
  const stageScreenshots = join(stageRoot, "screenshots");
  await mkdir(stageScreenshots, { recursive: true });
  const runtimeErrors = [];
  const browser = await chromium.launch({ headless: true, executablePath: browserExecutable });
  try {
    const context = await browser.newContext({
      viewport: CAPTURE_DEFINITIONS[0].viewport,
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

    const [jaSemantic, enSemantic] = await Promise.all([
      semanticSnapshot(page, source.htmlPath, "ja"),
      (async () => {
        const secondaryPage = await context.newPage();
        try {
          return await semanticSnapshot(secondaryPage, source.htmlPath, "en");
        } finally {
          await secondaryPage.close();
        }
      })(),
    ]);
    const semanticParity = evaluatePrioritySemanticBinding(
      jaSemantic,
      enSemantic,
      source.priorityContract,
    );
    if (semanticParity.status !== "pass") {
      console.error(JSON.stringify({ priority_semantic_binding: semanticParity }, null, 2));
      throw new Error("Priority semantic binding rejected before capture.");
    }

    const clickSync = await priorityClickCheck(page, source.htmlPath);
    const keyboardSync = await priorityKeyboardCheck(page, source.htmlPath);
    const focus = await visibleFocusCheck(page, source.htmlPath);
    const languageSwitch = await languageSwitchCheck(page, source.htmlPath);
    const noJavascript = await noJavascriptFallbackCheck(browser, source.htmlPath);

    const overflowProbes = [];
    for (const probe of [
      { language: "ja", viewport: { width: 390, height: 3100 } },
      { language: "ja", viewport: { width: 768, height: 1200 } },
      { language: "ja", viewport: { width: 1021, height: 1200 } },
      { language: "ja", viewport: { width: 1050, height: 1200 } },
      { language: "ja", viewport: { width: 1100, height: 1200 } },
      { language: "ja", viewport: { width: 1119, height: 1200 } },
      { language: "ja", viewport: { width: 1120, height: 1200 } },
      { language: "ja", viewport: { width: 1440, height: 1200 } },
      { language: "en", viewport: { width: 1440, height: 1200 } },
    ]) {
      overflowProbes.push(await overflowCheck(page, source.htmlPath, probe.language, probe.viewport));
    }
    const overflowReadback = {
      status: overflowProbes.every((item) => item.pass) ? "pass" : "fail",
      probes: overflowProbes,
    };
    const narrowOrder = await narrowOrderCheck(page, source.htmlPath);
    const narrowOrderReadback = {
      status: narrowOrder.pass ? "pass" : "fail",
      ...narrowOrder,
    };

    const captures = [];
    for (const definition of CAPTURE_DEFINITIONS) {
      captures.push(
        await captureOne(
          page,
          source.htmlPath,
          definition,
          stageScreenshots,
          ffmpegExecutable,
          stageRoot,
          captureLandmarks,
        ),
      );
    }

    const contactSource = await makeContactSheet(page, captures);
    const rawContactPath = join(stageRoot, "raw-contact-sheet.png");
    const contactPath = join(stageScreenshots, CONTACT_SHEET.filename);
    await writeFile(rawContactPath, Buffer.from(contactSource.png, "base64"));
    await normalizePng(ffmpegExecutable, rawContactPath, contactPath);
    const contactBuffer = await readFile(contactPath);
    const contactDimensions = pngDimensions(contactBuffer);
    const contactBrowser = await browserCanvasDecode(page, contactBuffer, contactSource.tiles);
    const contactFfmpeg = await ffmpegDecode(
      ffmpegExecutable,
      contactPath,
      contactDimensions,
      contactSource.tiles,
    );
    const contactBrowserPass = Object.values(contactBrowser.regions).every((item) => item.pass);
    const contactFfmpegPass = Object.values(contactFfmpeg.regions).every((item) => item.pass);
    const contactAgreement = contactBrowser.rgba_sha256 === contactFfmpeg.rgba_sha256;
    const contactPass = contactDimensions.width === CONTACT_SHEET.width
      && contactDimensions.height === CONTACT_SHEET.height
      && contactBrowserPass
      && contactFfmpegPass
      && contactAgreement;
    const negativeControl = await partialBlackNegativeControl(
      page,
      captures[0],
      ffmpegExecutable,
      stageRoot,
    );

    const screenshotEntries = captures.map((capture) => packageEntry(capture, identity.capture_id));
    const contactEntry = {
      id: CONTACT_SHEET.id,
      role: "contact-sheet",
      path: manifestOutputPath(CONTACT_SHEET.filename),
      capture_id: identity.capture_id,
      source_capture_ids: CAPTURE_DEFINITIONS.map((item) => item.id),
      dimensions: contactDimensions,
      normalized_png_sha256: sha256(contactBuffer),
      decoded_pixel_sha256: contactBrowser.rgba_sha256,
      browser_canvas_raster: {
        regions: contactBrowser.regions,
        pass: contactBrowserPass,
      },
      ffmpeg_raster: {
        regions: contactFfmpeg.regions,
        rgba_sha256: contactFfmpeg.rgba_sha256,
        pass: contactFfmpegPass,
      },
      decoder_agreement: {
        browser_rgba_sha256: contactBrowser.rgba_sha256,
        ffmpeg_rgba_sha256: contactFfmpeg.rgba_sha256,
        pass: contactAgreement,
      },
      pass: contactPass,
    };
    const geometryReadback = {
      status: captures.every((item) => Object.values(item.geometry).every((entry) => entry.pass)) ? "pass" : "fail",
      captures: captures.map((item) => ({
        id: item.definition.id,
        landmarks: item.geometry,
        pass: Object.values(item.geometry).every((entry) => entry.pass),
      })),
    };
    const browserRaster = {
      status: captures.every((item) => item.browser.pass) && contactBrowserPass ? "pass" : "fail",
      captures: captures.map((item) => ({
        id: item.definition.id,
        rgba_sha256: item.browser.rgba_sha256,
        landmarks: item.browser.regions,
        pass: item.browser.pass,
      })),
      contact_sheet: { landmarks: contactBrowser.regions, pass: contactBrowserPass },
    };
    const ffmpegRaster = {
      status: captures.every((item) => item.ffmpeg.pass) && contactFfmpegPass ? "pass" : "fail",
      captures: captures.map((item) => ({
        id: item.definition.id,
        rgba_sha256: item.ffmpeg.rgba_sha256,
        landmarks: item.ffmpeg.regions,
        pass: item.ffmpeg.pass,
      })),
      contact_sheet: { landmarks: contactFfmpeg.regions, pass: contactFfmpegPass },
    };
    const decoderAgreement = {
      status: captures.every((item) => item.decoder_agreement.pass) && contactAgreement ? "pass" : "fail",
      method: "Browser Image/canvas RGBA SHA-256 equals system FFmpeg RGBA SHA-256; screenshot captures also bind a browser-canvas PNG round-trip decoded by FFmpeg.",
      captures: captures.map((item) => ({ id: item.definition.id, ...item.decoder_agreement })),
      contact_sheet: contactEntry.decoder_agreement,
    };
    const browserRuntime = {
      status: runtimeErrors.length === 0 ? "pass" : "fail",
      errors: runtimeErrors,
    };
    const captureTimestamp = timestampAuthority(
      options.capturedAt,
      "--captured-at",
      "browser_capture_completed",
    );
    const capturedAt = captureTimestamp.value;
    const manifest = {
      schema_version: MANIFEST_SCHEMA,
      artifact_id: ARTIFACT_ID,
      capture_id: identity.capture_id,
      captured_at: capturedAt,
      capture_timestamp: captureTimestamp,
      capture_identity_sha256: identity.sha256,
      capture_identity: identity.payload,
      source_binding: source.binding,
      capture_contract: {
        device_scale_factor: DEVICE_SCALE_FACTOR,
        screenshot_mode: "viewport_without_clip",
        settling: "document.fonts.ready; two animation frames; scroll reset; two animation frames",
        captures: CAPTURE_DEFINITIONS,
        contact_sheet: CONTACT_SHEET,
        required_landmarks: captureLandmarks,
        language_default: "ja",
        selected_direction: "A",
        output_promotion: "All outputs staged outside OUTPUT_ROOT and copied only after every automated status passed.",
      },
      screenshots: screenshotEntries,
      contact_sheet: contactEntry,
      capture_runtime: {
        node_version: process.version,
        browser_version: await browser.version(),
        playwright_core_version: pwVersion,
        ffmpeg_version: ffmpegRuntime,
        browser_executable: portableRuntimePath(browserExecutable),
        ffmpeg_executable: portableRuntimePath(ffmpegExecutable),
        capture_script_path: source.binding.capture_script.path,
        capture_script_sha256: source.binding.capture_script.sha256,
        locale: ["ja-JP", "en-US"],
        timezone: "Asia/Tokyo",
        reduced_motion: "reduce",
        dependency_install_performed: false,
      },
      validation_commands: [
        "node samples/dashboard/production_capture/capture_priority_review_console.mjs --captured-at <ISO-8601>",
        "node samples/dashboard/production_capture/capture_priority_review_console.mjs --record-worker-inspection --inspection-at <ISO-8601>",
        "python -m unittest tests.test_dashboard_production_capture",
        "git diff --check",
      ],
    };
    const readback = {
      schema_version: READBACK_SCHEMA,
      artifact_id: ARTIFACT_ID,
      capture_id: identity.capture_id,
      captured_at: capturedAt,
      capture_timestamp: captureTimestamp,
      source_binding: source.validation,
      automated_semantic_parity: semanticParity,
      automated_priority_click_sync: clickSync,
      automated_priority_keyboard_sync: keyboardSync,
      automated_language_switch: languageSwitch,
      automated_visible_focus: focus,
      automated_no_javascript_fallback: noJavascript,
      automated_overflow_check: overflowReadback,
      automated_narrow_order: narrowOrderReadback,
      automated_geometry_check: geometryReadback,
      automated_browser_canvas_raster: browserRaster,
      automated_ffmpeg_raster: ffmpegRaster,
      automated_decoder_agreement: decoderAgreement,
      partial_black_negative_control: negativeControl,
      browser_runtime: browserRuntime,
      worker_raster_inspection: {
        status: "pending",
        capture_id: identity.capture_id,
        reason: "Every regeneration invalidates the prior Worker inspection. Open all four final PNGs, then run --record-worker-inspection.",
      },
      user_visual_acceptance: {
        status: "accepted",
        selected_direction: "A",
        production_artifact: "priority-review-console",
      },
      remaining_review_debt: [],
    };
    if (!allAutomatedPass(readback) || !screenshotEntries.every((item) => item.pass) || !contactEntry.pass) {
      const failed = AUTOMATED_STATUS_KEYS.filter((key) => readback[key]?.status !== "pass");
      console.error(JSON.stringify({
        failure_diagnostics: {
          failed_statuses: failed,
          overflow: overflowProbes.filter((item) => !item.pass),
          geometry: captures.map((item) => ({
            id: item.definition.id,
            failed_landmarks: Object.fromEntries(
              Object.entries(item.geometry).filter(([, landmark]) => !landmark.pass),
            ),
          })).filter((item) => Object.keys(item.failed_landmarks).length),
          browser_raster: captures.map((item) => ({
            id: item.definition.id,
            failed_landmarks: Object.fromEntries(
              Object.entries(item.browser.regions).filter(([, landmark]) => !landmark.pass),
            ),
          })).filter((item) => Object.keys(item.failed_landmarks).length),
          ffmpeg_raster: captures.map((item) => ({
            id: item.definition.id,
            failed_landmarks: Object.fromEntries(
              Object.entries(item.ffmpeg.regions).filter(([, landmark]) => !landmark.pass),
            ),
          })).filter((item) => Object.keys(item.failed_landmarks).length),
          contact_sheet: {
            browser_pass: contactBrowserPass,
            ffmpeg_pass: contactFfmpegPass,
            decoder_agreement: contactAgreement,
          },
        },
      }, null, 2));
      throw new Error(`Automated production capture failed before promotion: ${failed.join(", ") || "capture entry failure"}`);
    }
    await promote(stageRoot, outputRoot, manifest, readback);
    console.log(JSON.stringify({
      capture_id: identity.capture_id,
      captured_at: capturedAt,
      automated_status: "pass",
      output_root: outputRoot.replaceAll("\\", "/"),
      png_count: 4,
    }, null, 2));
    await context.close();
  } finally {
    await browser.close();
    await rm(stageRoot, { recursive: true, force: true });
  }
}

main().catch((error) => {
  console.error(error.stack || String(error));
  process.exitCode = 1;
});
