"""Generate a static local review dashboard from DevCockpitCore evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import html
import json
from pathlib import Path
import sys
from typing import Any


PRODUCER = "dev_cockpit.dashboard"
DEFAULT_VALIDATION_RESULT_PATH = "samples/validation_packs/devcockpitcore_validation_pack_result.json"
DEFAULT_CROSS_PROJECT_SMOKE_RESULT_PATH = (
    "samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json"
)
DEFAULT_STATUS_SNAPSHOT_PATH = "samples/status_snapshots/devcockpitcore_status.json"
DEFAULT_ADAPTER_PATH = "adapters/devcockpitcore.json"
DEFAULT_RUNTIME_STATE_PATH = "docs/runtime-state.md"
DEFAULT_PROJECT_CONTEXT_PATH = "docs/project-context.md"
DEFAULT_OUTPUT_PATH = "samples/dashboard/devcockpitcore_dashboard.html"
DEFAULT_REVIEW_ACTIONS_JSON_PATH = "samples/dashboard/devcockpitcore_review_actions.json"
DEFAULT_REVIEW_ACTIONS_MD_PATH = "samples/dashboard/devcockpitcore_review_actions.md"

LOCKED_LANES = (
    "Arbitrary command runner",
    "General execution loop",
    "Scheduler or background daemon",
    "Web server or remote dashboard",
    "Database or credential handling",
    "External service notifications",
    "Target repository writeback",
    "C5/C6 capability expansion",
    "Public publication or production-ready claims",
)

DESIGNER_NOTES = (
    "Judge whether the first screen makes warning ownership and access state obvious.",
    "Keep warning text tied to source JSON paths so reviewers can audit it.",
    "Use proposal panels for future actions; do not turn them into executable controls.",
    "Preserve a single-file offline artifact for low-friction operator review.",
)


class DashboardError(ValueError):
    """Raised when dashboard evidence cannot be read or rendered."""


def build_dashboard_model(
    *,
    repo_root: str | Path = ".",
    validation_result_path: str | Path = DEFAULT_VALIDATION_RESULT_PATH,
    cross_project_smoke_result_path: str | Path = DEFAULT_CROSS_PROJECT_SMOKE_RESULT_PATH,
    status_snapshot_path: str | Path = DEFAULT_STATUS_SNAPSHOT_PATH,
    adapter_path: str | Path = DEFAULT_ADAPTER_PATH,
    runtime_state_path: str | Path = DEFAULT_RUNTIME_STATE_PATH,
    project_context_path: str | Path = DEFAULT_PROJECT_CONTEXT_PATH,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    review_actions_json_path: str | Path = DEFAULT_REVIEW_ACTIONS_JSON_PATH,
    review_actions_md_path: str | Path = DEFAULT_REVIEW_ACTIONS_MD_PATH,
    generated_at: str | None = None,
) -> dict[str, Any]:
    root = Path(repo_root)
    generated = generated_at or _utc_now_iso()

    validation, validation_source = _read_json_source(root, validation_result_path, "validation_pack_result")
    smoke, smoke_source = _read_json_source(root, cross_project_smoke_result_path, "cross_project_smoke_result")
    status, status_source = _read_json_source(root, status_snapshot_path, "status_snapshot")
    adapter, adapter_source = _read_json_source(root, adapter_path, "adapter_manifest")
    runtime_text, runtime_source = _read_text_source(root, runtime_state_path, "runtime_state")
    project_context_text, project_context_source = _read_text_source(
        root, project_context_path, "project_context"
    )

    runtime_labels = _parse_label_block(runtime_text)
    project_identity = _project_identity(adapter, status, runtime_labels)
    source_warnings = _source_warnings(
        validation_source,
        smoke_source,
        status_source,
        adapter_source,
        runtime_source,
        project_context_source,
    )
    health = _aggregate_health(validation, smoke, status, source_warnings)
    output_rel = _display_path(root, output_path)
    actions_json_rel = _display_path(root, review_actions_json_path)
    actions_md_rel = _display_path(root, review_actions_md_path)
    sources = [
        validation_source,
        smoke_source,
        status_source,
        adapter_source,
        runtime_source,
        project_context_source,
    ]
    warning_triage = _warning_triage(health, validation, smoke, status, sources)
    review_checkpoints = _review_checkpoints(health, validation, smoke)
    review_actions = _review_actions(
        health,
        validation,
        smoke,
        status,
        sources,
        warning_triage,
        review_checkpoints,
        output_rel,
    )
    action_summary = _review_action_summary(review_actions)
    freshness = _freshness_summary(sources, generated)
    decision_meters = _decision_meters(
        health,
        validation,
        smoke,
        status,
        sources,
        freshness,
        action_summary,
        warning_triage,
        review_actions,
        output_rel,
    )
    review_stack = _review_stack(health, warning_triage, freshness, action_summary)
    latest_brief = _latest_brief(health, warning_triage, freshness, output_rel, review_stack)

    return {
        "schema_version": "devcockpit_local_dashboard.v1",
        "generated_at": generated,
        "producer": PRODUCER,
        "project": project_identity,
        "output": {
            "repo_relative_path": output_rel,
            "open_command": _powershell_open_command(output_rel),
            "access_mode": "local_static_file",
            "access_state": "worker_generated_not_user_opened",
            "access_evidence_level": "file_generated_by_dashboard_command",
        },
        "action_package": {
            "json_path": actions_json_rel,
            "markdown_path": actions_md_rel,
            "schema_version": "devcockpit_review_actions.v1",
            "access_state": "worker_generated_not_user_opened",
            "access_evidence_level": "file_generated_by_dashboard_command",
        },
        "sources": sources,
        "freshness": freshness,
        "validation_pack": {
            "summary": _dict(validation.get("summary")),
            "health": _dict(validation.get("health")),
            "gate_input": _dict(validation.get("gate_input")),
            "checks": _list(validation.get("checks")),
        },
        "cross_project_smoke": {
            "summary": _dict(smoke.get("summary")),
            "health": _dict(smoke.get("health")),
            "readiness": _dict(smoke.get("readiness")),
            "gate_input": _dict(smoke.get("gate_input")),
            "projects": _list(smoke.get("projects")),
        },
        "status_snapshot": {
            "repo": _dict(status.get("repo")),
            "project_state": _dict(status.get("project_state")),
            "health": _dict(status.get("health")),
        },
        "runtime_state": runtime_labels,
        "project_context_available": bool(project_context_text),
        "health": health,
        "safe_to_run": _safe_to_run_items(output_rel),
        "safe_local_actions": _safe_local_actions(output_rel),
        "locked_lanes": list(LOCKED_LANES),
        "review_next": _review_next_items(health, validation, smoke),
        "review_checkpoints": review_checkpoints,
        "decision_meters": decision_meters,
        "review_stack": review_stack,
        "latest_brief": latest_brief,
        "warning_triage": warning_triage,
        "review_actions": review_actions,
        "review_action_summary": action_summary,
        "designer_notes": list(DESIGNER_NOTES),
    }


def render_dashboard(model: dict[str, Any]) -> str:
    project = _dict(model.get("project"))
    validation = _dict(model.get("validation_pack"))
    smoke = _dict(model.get("cross_project_smoke"))
    status_snapshot = _dict(model.get("status_snapshot"))
    health = _dict(model.get("health"))
    output = _dict(model.get("output"))
    freshness = _dict(model.get("freshness"))
    action_package = _dict(model.get("action_package"))
    action_summary = _dict(model.get("review_action_summary"))

    validation_summary = _dict(validation.get("summary"))
    smoke_summary = _dict(smoke.get("summary"))
    status_repo = _dict(status_snapshot.get("repo"))
    projects = _list(smoke.get("projects"))

    lines = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '  <meta charset="utf-8">',
        '  <meta name="viewport" content="width=device-width, initial-scale=1">',
        f"  <title>{_e(project.get('name', 'DevCockpitCore'))} Local Test Dashboard</title>",
        '  <meta name="color-scheme" content="dark">',
        "  <style>",
        _stylesheet(),
        "  </style>",
        "</head>",
        '<body data-dashboard-variant="home-linked-meters">',
        '  <a class="skip-link" href="#main-content">Skip to dashboard content</a>',
        _top_strip(model, project, health, output, freshness),
        _dashboard_nav(),
        '  <main id="main-content" class="page" tabindex="-1">',
        _noscript_notice(),
        _section(
            "Review Stack",
            [_review_stack_cards(_list(model.get("review_stack")))],
        ),
        _section(
            "Linked Detail Map",
            [
                _linked_detail_map(
                    model,
                    validation,
                    smoke,
                    status_snapshot,
                    output,
                    action_package,
                    freshness,
                    action_summary,
                    projects,
                )
            ],
            summary="Meter-linked detail panels with back-to-overview paths.",
        ),
        _section(
            "Evidence Snapshot",
            [_summary_band(project, validation_summary, smoke_summary, status_repo, health, output, freshness)],
            collapsed=True,
            summary="Raw source rollup and repo/access state.",
        ),
        _section(
            "Warnings Triage",
            [_warning_triage_panel(_list(model.get("warning_triage")))],
            collapsed=True,
            summary="Warning ownership groups and source notes.",
        ),
        _section(
            "Review Actions",
            [
                _review_action_summary_panel(action_summary, action_package),
                _review_action_filter_controls(),
                _details_panel(
                    "Detailed Review Actions",
                    [_review_action_cards(_list(model.get("review_actions")))],
                    "All generated review-only actions remain available here.",
                ),
            ],
        ),
        _section(
            "Project Cards",
            [
                _project_filter_controls(),
                _project_cards(projects),
            ],
            collapsed=True,
            summary="Per-project smoke evidence and warning notes.",
        ),
        _section(
            "Validation Pack",
            [
                _summary_line(validation_summary),
                _checks_table(_list(validation.get("checks"))),
            ],
            collapsed=True,
            summary="Validation check table and meter details.",
        ),
        _section(
            "Cross-Project Smoke",
            [
                _summary_line(smoke_summary),
                _projects_table(projects),
            ],
            collapsed=True,
            summary="Cross-project observer rows and warnings.",
        ),
        _section(
            "Health, Gate, Readiness",
            [
                _health_panel(health),
                _gate_panel("Validation Gate", _dict(validation.get("gate_input"))),
                _gate_panel("Smoke Gate", _dict(smoke.get("gate_input"))),
                _readiness_panel(_dict(smoke.get("readiness"))),
            ],
            css_class="grid-three",
            collapsed=True,
            summary="Raw gate, stop class, and readiness values.",
        ),
        _section(
            "Safe Local Actions",
            [
                _safe_action_cards(_list(model.get("safe_local_actions"))),
                _list_panel(_list(model.get("safe_to_run")), "safe compact-list"),
            ],
            collapsed=True,
            summary="Local checks and file-open commands only.",
        ),
        _section(
            "Locked Lanes",
            [_locked_lane_grid(_list(model.get("locked_lanes")))],
            collapsed=True,
            summary="Execution expansion lanes kept locked.",
        ),
        _section(
            "Designer / Operator Notes",
            [_list_panel(_list(model.get("designer_notes")), "notes")],
            collapsed=True,
            summary="Review guidance retained below the overview.",
        ),
        _section(
            "Sources and Access",
            [
                _sources_table(_list(model.get("sources"))),
                _access_panel(output),
                _action_package_access_panel(action_package),
            ],
            collapsed=True,
            summary="Source paths, generated_at values, and local access evidence.",
        ),
        "  </main>",
        _dashboard_footer(model),
        "  <script>",
        _dashboard_script(),
        "  </script>",
        "</body>",
        "</html>",
        "",
    ]
    return "\n".join(lines)


def write_dashboard(model: dict[str, Any], output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_dashboard(model), encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate a static DevCockpitCore local test dashboard."
    )
    parser.add_argument("--repo-root", default=".", help="Repository root used to resolve relative evidence paths.")
    parser.add_argument(
        "--validation-result",
        default=DEFAULT_VALIDATION_RESULT_PATH,
        help="validation_pack_result.v1 JSON path.",
    )
    parser.add_argument(
        "--cross-project-smoke-result",
        default=DEFAULT_CROSS_PROJECT_SMOKE_RESULT_PATH,
        help="cross_project_smoke_result.v1 JSON path.",
    )
    parser.add_argument(
        "--status-snapshot",
        default=DEFAULT_STATUS_SNAPSHOT_PATH,
        help="status_snapshot.v1 JSON path.",
    )
    parser.add_argument("--adapter", default=DEFAULT_ADAPTER_PATH, help="adapter_manifest.v1 JSON path.")
    parser.add_argument("--runtime-state", default=DEFAULT_RUNTIME_STATE_PATH, help="runtime state markdown path.")
    parser.add_argument(
        "--project-context",
        default=DEFAULT_PROJECT_CONTEXT_PATH,
        help="project context markdown path.",
    )
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, help="Output HTML path.")
    parser.add_argument(
        "--review-actions-json",
        default=DEFAULT_REVIEW_ACTIONS_JSON_PATH,
        help="Output non-executable review actions JSON path.",
    )
    parser.add_argument(
        "--review-actions-md",
        default=DEFAULT_REVIEW_ACTIONS_MD_PATH,
        help="Output non-executable review actions Markdown path.",
    )
    args = parser.parse_args(argv)

    try:
        model = build_dashboard_model(
            repo_root=args.repo_root,
            validation_result_path=args.validation_result,
            cross_project_smoke_result_path=args.cross_project_smoke_result,
            status_snapshot_path=args.status_snapshot,
            adapter_path=args.adapter,
            runtime_state_path=args.runtime_state,
            project_context_path=args.project_context,
            output_path=args.output,
            review_actions_json_path=args.review_actions_json,
            review_actions_md_path=args.review_actions_md,
        )
        package = review_action_package(model)
        write_dashboard(model, Path(args.repo_root) / args.output)
        write_review_actions_json(package, Path(args.repo_root) / args.review_actions_json, pretty=True)
        write_review_actions_markdown(package, Path(args.repo_root) / args.review_actions_md)
    except DashboardError as exc:
        print(f"dashboard error: {exc}", file=sys.stderr)
        return 2

    print(_display_path(Path(args.repo_root), args.output))
    print(_display_path(Path(args.repo_root), args.review_actions_json))
    print(_display_path(Path(args.repo_root), args.review_actions_md))
    return 0


def _top_strip(
    model: dict[str, Any],
    project: dict[str, Any],
    health: dict[str, Any],
    output: dict[str, Any],
    freshness: dict[str, Any],
) -> str:
    warning_count = len(_list(health.get("warnings")))
    blocker_count = len(_list(health.get("blockers")))
    generated_at = model.get("generated_at", "unknown")
    review_next = _list(model.get("review_next"))
    next_item = _short_text(str(review_next[0]), 88) if review_next else "Review warnings, blockers, and evidence freshness."
    decision = _decision_label(health)
    meters = _list(model.get("decision_meters"))
    return (
        '<header class="top-strip compact-dark-overview" data-dashboard-theme="dark">'
        '<div class="hero-copy">'
        '<p class="eyebrow">Local supervision HUD</p>'
        f"<h1>{_e(project.get('name', 'DevCockpitCore'))}</h1>"
        '<p class="hero-summary">Home-linked decision meter HUD for the next human review decision.</p>'
        f"<p class=\"subtle\">Generated {_e(generated_at)} from local evidence. Access: {_e(_access_label(output))}.</p>"
        f"<p class=\"subtle\">Current read: {_e(decision)} with {_e(str(blocker_count))} blockers and {_e(str(warning_count))} warning signals.</p>"
        f"{_latest_brief_panel(model.get('latest_brief'))}"
        "</div>"
        '<div id="meter-board" class="decision-meter-board" aria-label="Home-linked decision meters">'
        f"{_decision_meter_cards(meters)}"
        f"<div class=\"review-strip\"><span>Next</span><p>{_e(next_item)}</p><a href=\"#review-stack\">Review Stack</a></div>"
        "</div>"
        "</header>"
    )


def _dashboard_nav() -> str:
    links = (
        ("Brief", "latest-brief"),
        ("Meters", "meter-board"),
        ("Stack", "review-stack"),
        ("Details", "linked-detail-map"),
        ("Warnings", "warnings-triage"),
        ("Actions", "review-actions"),
        ("Projects", "project-cards"),
        ("Sources", "sources-and-access"),
    )
    link_html = "".join(f'<a href="#{target}">{_e(label)}</a>' for label, target in links)
    return f'<nav class="dashboard-nav" aria-label="Dashboard sections">{link_html}</nav>'


def _noscript_notice() -> str:
    return (
        '<noscript><div class="panel noscript-notice">'
        "<h2>JavaScript disabled</h2>"
        "<p>All dashboard evidence and review actions remain visible. Search and filter controls are optional local-only conveniences.</p>"
        "</div></noscript>"
    )


def _dashboard_footer(model: dict[str, Any]) -> str:
    return (
        '<footer class="dashboard-footer">'
        f"<p>Worker-generated local review artifact. Generated at {_e(model.get('generated_at', 'unknown'))}. "
        "No server, telemetry, task runner, or repository writeback is included.</p>"
        "</footer>"
    )


def _summary_band(
    project: dict[str, Any],
    validation_summary: dict[str, Any],
    smoke_summary: dict[str, Any],
    status_repo: dict[str, Any],
    health: dict[str, Any],
    output: dict[str, Any],
    freshness: dict[str, Any],
) -> str:
    cards = [
        _metric_card("Project", project.get("key", "unknown"), project.get("branch", "branch unknown")),
        _metric_card(
            "Validation",
            validation_summary.get("result", "unknown"),
            _count_text(validation_summary),
            validation_summary,
        ),
        _metric_card("Smoke", smoke_summary.get("result", "unknown"), _count_text(smoke_summary), smoke_summary),
        _metric_card(
            "Repo",
            status_repo.get("worktree", {}).get("state", "unknown"),
            f"HEAD {status_repo.get('head', 'unknown')}",
        ),
        _metric_card("Gate", health.get("stop_class", "unknown"), health.get("summary", "review evidence")),
        _metric_card("Sources", freshness.get("loaded_count", "unknown"), freshness.get("source_summary", "sources")),
        _metric_card("Access State", output.get("access_mode", "unknown"), output.get("access_evidence_level", "evidence")),
    ]
    return f'<div class="summary-grid">{"".join(cards)}</div>'


def _latest_brief_panel(brief_value: Any) -> str:
    brief = _dict(brief_value)
    if not brief:
        return ""
    steps = []
    for step_value in _list(brief.get("runway"))[:3]:
        step = _dict(step_value)
        steps.append(
            f'<li class="{_tone_class(step.get("tone"))}">'
            f"<span>{_e(step.get('label', 'Read'))}</span>"
            f"<strong>{_e(step.get('value', 'Review'))}</strong>"
            "</li>"
        )
    runway = f'<ol class="brief-runway">{"".join(steps)}</ol>' if steps else ""
    action = _dict(brief.get("primary_action"))
    primary_href = str(action.get("href") or "#review-stack")
    primary_label = str(action.get("label") or "Review")
    secondary = _dict(brief.get("secondary_link"))
    secondary_html = ""
    if secondary.get("label"):
        secondary_html = (
            f'<a class="brief-secondary" href="{_e(secondary.get("href", "#review-stack"))}">'
            f'{_e(secondary.get("label"))}</a>'
        )
    aside = _dict(brief.get("aside"))
    aside_html = ""
    if aside:
        aside_html = (
            '<p class="brief-aside">'
            f"<span>{_e(aside.get('label', 'Not urgent'))}</span>"
            f"{_e(aside.get('text', 'Keep locked lanes out of this review.'))}"
            "</p>"
        )
    return (
        '<section id="latest-brief" class="latest-brief" data-brief-kind="editorial" aria-label="Latest Brief">'
        "<h2>Latest Brief</h2>"
        f'<p class="brief-headline">{_e(brief.get("headline", "Review the current local state."))}</p>'
        f'<p class="brief-annotation">{_e(brief.get("annotation", ""))}</p>'
        f"{runway}"
        '<div class="brief-footer">'
        f"{aside_html}"
        '<div class="brief-actions">'
        f'<a class="brief-primary-action" href="{_e(primary_href)}">{_e(primary_label)}</a>'
        f"{secondary_html}"
        "</div>"
        "</div>"
        "</section>"
    )


def _decision_meter_cards(meters: list[Any]) -> str:
    cards = []
    for meter in meters:
        item = _dict(meter)
        progress = _dict(item.get("progress"))
        progress_html = _decision_progress(progress)
        evidence = item.get("evidence_path") or item.get("detail_href", "dashboard")
        action_href = str(item.get("action_href") or item.get("detail_href", "#linked-detail-map"))
        action_label = str(item.get("action_label") or "Review action")
        cards.append(
            f'<article class="decision-meter {_tone_class(item.get("tone"))}" data-meter-target="{_e(item.get("detail_href", ""))}">'
            f"<div class=\"meter-head\"><span>{_e(item.get('title', 'Meter'))}</span>"
            f"<strong>{_e(item.get('primary_value', 'n/a'))}</strong></div>"
            f"<p>{_e(item.get('summary', 'Review this signal.'))}</p>"
            f"{progress_html}"
            f"<p class=\"why-line\">{_e(item.get('why', 'Shows why this signal matters.'))}</p>"
            f"<div class=\"meter-links\"><a href=\"{_e(item.get('detail_href', '#linked-detail-map'))}\">Open detail</a>"
            f"<a href=\"{_e(action_href)}\">{_e(action_label)}</a></div>"
            f"<code>{_e(evidence)}</code>"
            "</article>"
        )
    return "".join(cards)


def _decision_progress(progress: dict[str, Any]) -> str:
    total = _int(progress.get("total"))
    done = _int(progress.get("done"))
    if total <= 0:
        label = progress.get("label", "count only")
        return f'<p class="meter-note">{_e(label)}</p>'
    width = max(0, min(100, round(done / total * 100)))
    label = progress.get("label") or f"{done}/{total}"
    tone = progress.get("tone", "neutral")
    return (
        f'<div class="decision-progress" role="progressbar" aria-valuemin="0" aria-valuemax="{_e(total)}" '
        f'aria-valuenow="{_e(done)}" aria-label="{_e(label)}">'
        f'<span class="{_result_class(tone)}" style="width:{width}%"></span>'
        f"</div><p class=\"meter-note\">{_e(label)}</p>"
    )


def _review_stack_cards(items: list[Any]) -> str:
    if not items:
        return '<div class="review-stack-grid"><article class="stack-card"><p>No review stack items were generated.</p></article></div>'
    cards = []
    for index, item in enumerate(items[:3], 1):
        row = _dict(item)
        cards.append(
            '<article class="stack-card" data-review-stack-item>'
            f"<span>Step {index}</span>"
            f"<strong>{_e(row.get('title', 'Review target'))}</strong>"
            f"<p>{_e(row.get('reason', 'Review this target before drilling into dense evidence.'))}</p>"
            f"<a href=\"{_e(row.get('href', '#linked-detail-map'))}\">{_e(row.get('link_label', 'Open detail'))}</a>"
            f"<code>{_e(row.get('evidence', 'dashboard'))}</code>"
            "</article>"
        )
    return f'<div class="review-stack-grid">{"".join(cards)}</div>'


def _linked_detail_map(
    model: dict[str, Any],
    validation: dict[str, Any],
    smoke: dict[str, Any],
    status_snapshot: dict[str, Any],
    output: dict[str, Any],
    action_package: dict[str, Any],
    freshness: dict[str, Any],
    action_summary: dict[str, Any],
    projects: list[Any],
) -> str:
    health = _dict(model.get("health"))
    warning_triage = _list(model.get("warning_triage"))
    actions = _list(model.get("review_actions"))
    validation_summary = _dict(validation.get("summary"))
    smoke_summary = _dict(smoke.get("summary"))
    status_repo = _dict(status_snapshot.get("repo"))
    stop_summary = _decision_detail(health)
    panels = [
        _linked_detail_panel(
            "detail-stop-gate",
            "Detail: Stop Gate",
            f"{len(_list(health.get('blockers')))} blockers; decision is {_decision_label(health)}.",
            "This exists to decide whether review can continue before anyone opens deeper evidence.",
            [
                _health_panel(health),
                _gate_panel("Validation Gate", _dict(validation.get("gate_input"))),
                _gate_panel("Smoke Gate", _dict(smoke.get("gate_input"))),
            ],
            actions,
            ("dashboard_health",),
            fallback=f"Stop gate has no blocker action. Current stop read is {stop_summary}.",
        ),
        _linked_detail_panel(
            "detail-warning-debt",
            "Detail: Warning Debt",
            f"{action_summary.get('warning', 0)} warning review actions across {len(warning_triage)} groups.",
            "This exists to show which warning bucket deserves attention before source browsing.",
            [_warning_triage_panel(warning_triage)],
            actions,
            ("validation_pack", "cross_project_smoke", "status_snapshot"),
        ),
        _linked_detail_panel(
            "detail-evidence-freshness",
            "Detail: Evidence Freshness",
            f"{freshness.get('loaded_count', '0/0')} sources loaded; latest generated at {freshness.get('latest_generated_at', 'unknown')}.",
            "This exists to decide whether the current evidence is fresh enough for a review decision.",
            [_sources_table(_list(model.get("sources")))],
            actions,
            ("dashboard_review",),
        ),
        _linked_detail_panel(
            "detail-review-actions",
            "Detail: Review Actions",
            f"{action_summary.get('total', 0)} actions; {action_summary.get('locked_by_gate', 0)} locked-by-gate reminder.",
            "This exists to keep review work visible while preserving executable:false on every action.",
            [_review_action_summary_panel(action_summary, action_package)],
            actions,
            ("dashboard_review", "locked_gate"),
        ),
        _linked_detail_panel(
            "detail-project-smoke",
            "Detail: Project Smoke",
            f"{smoke_summary.get('result', 'unknown')} across {_count_text(smoke_summary)}.",
            "This exists to separate cross-project observer warnings from DevCockpitCore implementation work.",
            [_project_cards(projects)],
            actions,
            ("cross_project_smoke",),
        ),
        _linked_detail_panel(
            "detail-source-files",
            "Detail: Source Files",
            f"Dashboard artifact is {output.get('repo_relative_path', 'unknown')}; repo state is {status_repo.get('worktree', {}).get('state', 'unknown')}.",
            "This exists to show local access and source paths without turning the dashboard into a server or runner.",
            [_access_panel(output), _action_package_access_panel(action_package), _summary_line(validation_summary)],
            actions,
            ("status_snapshot",),
        ),
    ]
    return f'<div class="linked-detail-grid">{"".join(panels)}</div>'


def _linked_detail_panel(
    panel_id: str,
    title: str,
    summary: str,
    why: str,
    body: list[str],
    actions: list[Any],
    related_source_types: tuple[str, ...],
    *,
    fallback: str = "No related review action is required for this signal.",
) -> str:
    return (
        f'<section id="{_e(panel_id)}" class="detail-anchor-panel" aria-labelledby="{_e(panel_id)}-heading">'
        '<div class="detail-anchor-head">'
        '<span>Linked detail</span>'
        f'<h3 id="{_e(panel_id)}-heading">{_e(title)}</h3>'
        f"<p>{_e(summary)}</p>"
        '<a class="back-link" href="#meter-board">Back to overview</a>'
        "</div>"
        f"<p class=\"why-line\">{_e(why)}</p>"
        f'<div class="detail-body">{"".join(body)}</div>'
        f"{_related_action_links(actions, related_source_types, fallback=fallback)}"
        "</section>"
    )


def _related_action_links(
    actions: list[Any],
    source_types: tuple[str, ...],
    *,
    fallback: str,
    limit: int = 4,
) -> str:
    matched = [
        _dict(action)
        for action in actions
        if str(_dict(action).get("source_type")) in source_types
    ]
    if not matched:
        return f'<div class="related-actions"><h4>Related Review Actions</h4><p>{_e(fallback)}</p></div>'
    rows = []
    for action in matched[:limit]:
        action_id = str(action.get("action_id", "review-action"))
        rows.append(
            "<li>"
            f'<a href="#{_e(action_id)}">{_e(action_id)}</a> '
            f"<span class=\"pill {_result_class(action.get('severity'))}\">{_e(action.get('severity', 'info'))}</span> "
            f"{_e(_short_text(str(action.get('reason', action.get('title', 'Review action'))), 88))}"
            "</li>"
        )
    overflow = len(matched) - limit
    overflow_html = f'<p class="subtle">+{overflow} more in Review Actions.</p>' if overflow > 0 else ""
    return (
        '<div class="related-actions">'
        "<h4>Related Review Actions</h4>"
        f'<ul class="list compact-list">{"".join(rows)}</ul>'
        f"{overflow_html}"
        "</div>"
    )


def _section(
    title: str,
    body: list[str],
    *,
    css_class: str = "",
    collapsed: bool = False,
    summary: str | None = None,
) -> str:
    klass = f' class="section-grid {css_class}"' if css_class else ' class="section-grid"'
    section_id = _slug(title)
    heading_id = f"{section_id}-heading"
    if collapsed:
        summary_text = summary or f"{title} details"
        return (
            f'<section id="{_e(section_id)}" class="section section-collapsed" aria-labelledby="{_e(heading_id)}">'
            '<details class="disclosure">'
            f'<summary><h2 id="{_e(heading_id)}">{_e(title)}</h2><span>{_e(summary_text)}</span></summary>'
            f"<div{klass}>{''.join(body)}</div></details></section>"
        )
    return (
        f'<section id="{_e(section_id)}" class="section" aria-labelledby="{_e(heading_id)}">'
        f'<h2 id="{_e(heading_id)}">{_e(title)}</h2>'
        f"<div{klass}>{''.join(body)}</div></section>"
    )


def _details_panel(title: str, body: list[str], summary: str) -> str:
    return (
        '<details class="disclosure detail-panel">'
        f"<summary><h3>{_e(title)}</h3><span>{_e(summary)}</span></summary>"
        f'<div class="section-grid">{"".join(body)}</div>'
        "</details>"
    )


def _review_checkpoint_cards(checkpoints: list[Any]) -> str:
    cards = []
    for checkpoint in checkpoints:
        item = _dict(checkpoint)
        cards.append(
            '<article class="checkpoint-card">'
            f"<span>{_e(item.get('label', 'Review'))}</span>"
            f"<strong>{_e(item.get('state', 'check'))}</strong>"
            f"<p>{_e(item.get('prompt', 'Review this section.'))}</p>"
            f"<code>{_e(item.get('evidence', 'dashboard'))}</code>"
            "</article>"
        )
    return f'<div class="checkpoint-grid">{"".join(cards)}</div>'


def _warning_triage_panel(groups: list[Any]) -> str:
    if not groups:
        return '<div class="panel"><p>No warning triage groups were available.</p></div>'
    cards = []
    for group in groups:
        item = _dict(group)
        entries = _list(item.get("items"))
        visible_entries = entries[:5]
        overflow = len(entries) - len(visible_entries)
        overflow_html = f'<p class="subtle">+{overflow} more in source evidence</p>' if overflow > 0 else ""
        cards.append(
            '<article class="triage-card">'
            f"<div class=\"triage-heading\"><span>{_e(item.get('source', 'Source'))}</span>"
            f"<strong class=\"{_result_class(item.get('severity'))}\">{_e(item.get('severity', 'unknown'))}</strong></div>"
            f"<p>{_e(item.get('count', 0))} item(s)</p>"
            f"{_list_panel(visible_entries or ['No items reported.'], 'warning-list compact-list')}"
            f"{overflow_html}"
            "</article>"
        )
    return f'<div class="triage-grid">{"".join(cards)}</div>'


def _review_action_summary_panel(summary: dict[str, Any], package: dict[str, Any]) -> str:
    return (
        '<div class="panel action-summary">'
        "<h3>Review-only Action Package</h3>"
        '<p><strong>Non-executable:</strong> every generated action is marked <code>executable: false</code>.</p>'
        f"<p><strong>Total:</strong> {_e(summary.get('total', 0))} "
        f"<strong>Blockers:</strong> {_e(summary.get('blocker', 0))} "
        f"<strong>Warnings:</strong> {_e(summary.get('warning', 0))} "
        f"<strong>Info:</strong> {_e(summary.get('info', 0))}</p>"
        f"<p><strong>JSON:</strong> <code>{_e(package.get('json_path', 'unknown'))}</code></p>"
        f"<p><strong>Markdown:</strong> <code>{_e(package.get('markdown_path', 'unknown'))}</code></p>"
        "</div>"
    )


def _review_action_filter_controls() -> str:
    return (
        '<div class="panel filter-panel">'
        "<h3>Action Review Filters</h3>"
        '<label for="action-search">Search review actions</label>'
        '<input id="action-search" data-action-search type="search" '
        'placeholder="Source, project, title, reason" autocomplete="off">'
        '<div class="filter-buttons" aria-label="Action severity filters">'
        '<button type="button" data-filter-action-severity="all">All</button>'
        '<button type="button" data-filter-action-severity="blocker">Blockers</button>'
        '<button type="button" data-filter-action-severity="warning">Warnings</button>'
        '<button type="button" data-filter-action-severity="info">Info</button>'
        "</div>"
        '<p class="subtle">Filters are local only; action cards remain visible without JavaScript.</p>'
        "</div>"
    )


def _review_action_cards(actions: list[Any]) -> str:
    if not actions:
        return '<div class="action-review-grid"><article class="review-action-card"><p>No review actions generated.</p></article></div>'
    cards = []
    for action in actions:
        item = _dict(action)
        severity = str(item.get("severity", "info"))
        action_id = _slug(item.get("action_id", "review-action"))
        search_text = " ".join(
            str(part)
            for part in (
                item.get("action_id", ""),
                item.get("source_type", ""),
                item.get("project_key", ""),
                item.get("title", ""),
                item.get("reason", ""),
                item.get("evidence_path", ""),
            )
        ).lower()
        gate_note = "Locked by gate" if item.get("blocked_by_gate") else "Review-only"
        cards.append(
            f'<article id="{_e(action_id)}" class="review-action-card" data-review-action data-severity="{_e(severity)}" data-search="{_e(search_text)}">'
            f"<div class=\"project-card-head\"><h3>{_e(item.get('title', 'Review action'))}</h3>"
            f"<span class=\"pill {_result_class(severity)}\">{_e(severity)}</span></div>"
            f"<p><strong>ID:</strong> <code>{_e(item.get('action_id', 'unknown'))}</code></p>"
            f"<p><strong>Source:</strong> {_e(item.get('source_type', 'unknown'))}"
            f"{' / ' + _e(item.get('project_key')) if item.get('project_key') else ''}</p>"
            f"<p><strong>Reason:</strong> {_e(item.get('reason', 'No reason provided.'))}</p>"
            f"<p><strong>Suggested review:</strong> {_e(item.get('suggested_review', 'Manual review.'))}</p>"
            f"<p><strong>Evidence:</strong> <code>{_e(item.get('evidence_path', 'unknown'))}</code></p>"
            f"<p><strong>Owner hint:</strong> {_e(item.get('owner_hint', 'operator'))}</p>"
            f"<p><strong>{_e(gate_note)}:</strong> executable is {_e(str(item.get('executable', False)).lower())}; surface {_e(item.get('safe_next_surface', 'local_review'))}</p>"
            "</article>"
        )
    return f'<div class="action-review-grid">{"".join(cards)}</div>'


def _project_filter_controls() -> str:
    return (
        '<div class="panel filter-panel">'
        '<h3>Project Review Filters</h3>'
        '<label for="project-search">Search project evidence</label>'
        '<input id="project-search" data-dashboard-search type="search" '
        'placeholder="Project, branch, adapter, warning" autocomplete="off">'
        '<div class="filter-buttons" aria-label="Project result filters">'
        '<button type="button" data-filter-result="all">All</button>'
        '<button type="button" data-filter-result="warn">Warnings</button>'
        '<button type="button" data-filter-result="pass">Pass</button>'
        '<button type="button" data-filter-result="fail">Fail</button>'
        '<button type="button" data-filter-result="skipped">Skipped</button>'
        "</div>"
        '<p class="subtle">All cards remain visible without JavaScript; filters only hide local DOM cards.</p>'
        "</div>"
    )


def _project_cards(projects: list[Any]) -> str:
    if not projects:
        return '<div class="project-card-grid"><article class="project-card"><p>No project evidence rows.</p></article></div>'
    cards = []
    for project in projects:
        item = _dict(project)
        snapshot = _dict(item.get("status_snapshot"))
        resolution = _dict(item.get("repo_resolution"))
        project_name = str(item.get("project", item.get("project_key", "unknown")))
        result = str(item.get("result", "unknown"))
        warnings = _list(snapshot.get("warnings"))
        search_text = " ".join(
            [
                project_name,
                str(item.get("project_key", "")),
                str(item.get("adapter_path", "")),
                str(snapshot.get("branch", "")),
                str(snapshot.get("head", "")),
                " ".join(str(warning) for warning in warnings),
            ]
        ).lower()
        cards.append(
            f'<article class="project-card" data-dashboard-project data-result="{_e(result.lower())}" data-search="{_e(search_text)}">'
            f"<div class=\"project-card-head\"><h3>{_e(project_name)}</h3>"
            f"<span class=\"pill {_result_class(result)}\">{_e(result)}</span></div>"
            f"<p><strong>Repo:</strong> {_e(resolution.get('selected') or 'not selected')}</p>"
            f"<p><strong>Branch:</strong> {_e(snapshot.get('branch', 'unknown'))} <span class=\"subtle\">{_e(snapshot.get('head', 'unknown'))}</span></p>"
            f"<p><strong>Adapter:</strong> <code>{_e(item.get('adapter_path', 'adapter unknown'))}</code></p>"
            f"{_meter(item)}"
            f"{_list_panel(warnings or ['No project warnings reported.'], 'warning-list compact-list')}"
            "</article>"
        )
    return f'<div class="project-card-grid">{"".join(cards)}</div>'


def _safe_action_cards(actions: list[Any]) -> str:
    cards = []
    for action in actions:
        item = _dict(action)
        cards.append(
            '<article class="action-card">'
            f"<span>{_e(item.get('kind', 'LOCAL'))}</span>"
            f"<strong>{_e(item.get('label', 'Action'))}</strong>"
            f"<p>{_e(item.get('effect', 'No effect described.'))}</p>"
            f"<code>{_e(item.get('command', 'open locally'))}</code>"
            "</article>"
        )
    return f'<div class="action-grid">{"".join(cards)}</div>'


def _locked_lane_grid(lanes: list[Any]) -> str:
    cards = []
    for lane in lanes:
        cards.append(
            '<article class="locked-card">'
            '<span>LOCKED</span>'
            f"<strong>{_e(lane)}</strong>"
            "<p>Not part of this static dashboard slice.</p>"
            "</article>"
        )
    return f'<div class="locked-grid">{"".join(cards)}</div>'


def _summary_line(summary: dict[str, Any]) -> str:
    return (
        '<div class="panel">'
        f'<h3>Summary</h3><p><span class="pill {_result_class(summary.get("result"))}">'
        f'{_e(summary.get("result", "unknown"))}</span> {_e(_count_text(summary))}</p>'
        f"{_meter(summary)}"
        "</div>"
    )


def _checks_table(checks: list[Any]) -> str:
    rows = []
    for check in checks:
        item = _dict(check)
        findings = _list(item.get("findings"))
        notes = _list(item.get("notes"))
        detail = f"{len(findings)} findings"
        if not findings and notes:
            detail = _short_text(str(notes[0]), 140)
        rows.append(
            "<tr>"
            f"<td><code>{_e(item.get('check_key', 'unknown'))}</code></td>"
            f"<td><span class=\"pill {_result_class(item.get('result'))}\">{_e(item.get('result', 'unknown'))}</span></td>"
            f"<td>{_e(item.get('severity', 'unknown'))}</td>"
            f"<td>{_meter(item)}</td>"
            f"<td>{_e(detail)}</td>"
            "</tr>"
        )
    return _table(
        ("Check", "Result", "Severity", "Bar", "Detail"),
        rows,
        empty_text="No validation checks were available.",
        caption="Validation pack checks, result severity, evidence bar, and detail.",
    )


def _projects_table(projects: list[Any]) -> str:
    rows = []
    for project in projects:
        item = _dict(project)
        snapshot = _dict(item.get("status_snapshot"))
        resolution = _dict(item.get("repo_resolution"))
        selected = resolution.get("selected") or "not selected"
        warnings = "; ".join(str(part) for part in _list(snapshot.get("warnings")))
        rows.append(
            "<tr>"
            f"<td><strong>{_e(item.get('project', item.get('project_key', 'unknown')))}</strong><br>"
            f"<code>{_e(item.get('adapter_path', 'adapter unknown'))}</code></td>"
            f"<td><span class=\"pill {_result_class(item.get('result'))}\">{_e(item.get('result', 'unknown'))}</span></td>"
            f"<td>{_e(selected)}</td>"
            f"<td>{_e(snapshot.get('branch', 'unknown'))}<br><span class=\"subtle\">{_e(snapshot.get('head', 'unknown'))}</span></td>"
            f"<td>{_meter(item)}</td>"
            f"<td>{_e(warnings or 'none')}</td>"
            "</tr>"
        )
    return _table(
        ("Project", "Result", "Repo", "Branch / HEAD", "Bar", "Warnings"),
        rows,
        empty_text="No cross-project rows were available.",
        caption="Cross-project smoke rows with result, repository hint, branch, and warning summary.",
    )


def _health_panel(health: dict[str, Any]) -> str:
    warnings = _list(health.get("warnings"))
    blockers = _list(health.get("blockers"))
    return (
        '<div class="panel">'
        "<h3>Warning / Blocker Split</h3>"
        f"<p><strong>Warnings:</strong> {_e(str(len(warnings)))}</p>"
        f"<p><strong>Blockers:</strong> {_e(str(len(blockers)))}</p>"
        f"{_list_panel(warnings or ['No warnings reported.'], 'warning-list')}"
        f"{_list_panel(blockers or ['No blockers reported.'], 'blocker-list')}"
        "</div>"
    )


def _gate_panel(title: str, gate: dict[str, Any]) -> str:
    return (
        '<div class="panel">'
        f"<h3>{_e(title)}</h3>"
        f"<p><strong>Decision:</strong> {_e(gate.get('recommended_gate_decision', 'unknown'))}</p>"
        f"<p><strong>Stop class:</strong> {_e(gate.get('stop_class', 'unknown'))}</p>"
        f"<p><strong>User work:</strong> {_e(gate.get('user_work', 'unknown'))}</p>"
        "</div>"
    )


def _readiness_panel(readiness: dict[str, Any]) -> str:
    notes = _list(readiness.get("notes"))
    return (
        '<div class="panel">'
        "<h3>Readiness</h3>"
        f"<p><strong>Foundation:</strong> {_e(readiness.get('foundation_automation_readiness', 'unknown'))}</p>"
        f"<p><strong>Execution:</strong> {_e(readiness.get('execution_automation_readiness', 'unknown'))}</p>"
        f"{_list_panel(notes or ['No readiness notes reported.'], 'readiness')}"
        "</div>"
    )


def _sources_table(sources: list[Any]) -> str:
    rows = []
    for source in sources:
        item = _dict(source)
        rows.append(
            "<tr>"
            f"<td>{_e(item.get('label', 'source'))}</td>"
            f"<td><code>{_e(item.get('repo_relative_path', 'unknown'))}</code></td>"
            f"<td><span class=\"pill {_result_class(item.get('state'))}\">{_e(item.get('state', 'unknown'))}</span></td>"
            f"<td>{_e(item.get('schema_version', 'n/a'))}</td>"
            f"<td>{_e(item.get('generated_at', 'n/a') or 'n/a')}</td>"
            "</tr>"
        )
    return _table(
        ("Source", "Repo-relative path", "State", "Schema", "Generated at"),
        rows,
        empty_text="No sources.",
        caption="Source evidence files used by the local dashboard.",
    )


def _access_panel(output: dict[str, Any]) -> str:
    return (
        '<div class="panel access-panel">'
        "<h3>Open / Access</h3>"
        f"<p><strong>Repo-relative artifact:</strong> <code>{_e(output.get('repo_relative_path', 'unknown'))}</code></p>"
        f"<p><strong>Access mode:</strong> {_e(output.get('access_mode', 'unknown'))}</p>"
        f"<p><strong>Access state:</strong> {_e(output.get('access_state', 'unknown'))}</p>"
        f"<p><strong>Evidence level:</strong> {_e(output.get('access_evidence_level', 'unknown'))}</p>"
        f"<p><strong>PowerShell:</strong> <code>{_e(output.get('open_command', 'unknown'))}</code></p>"
        "</div>"
    )


def _action_package_access_panel(package: dict[str, Any]) -> str:
    return (
        '<div class="panel access-panel">'
        "<h3>Review Action Package</h3>"
        f"<p><strong>Schema:</strong> {_e(package.get('schema_version', 'unknown'))}</p>"
        f"<p><strong>JSON:</strong> <code>{_e(package.get('json_path', 'unknown'))}</code></p>"
        f"<p><strong>Markdown:</strong> <code>{_e(package.get('markdown_path', 'unknown'))}</code></p>"
        f"<p><strong>Access state:</strong> {_e(package.get('access_state', 'unknown'))}</p>"
        f"<p><strong>Evidence level:</strong> {_e(package.get('access_evidence_level', 'unknown'))}</p>"
        "</div>"
    )


def _metric_card(label: str, value: Any, detail: Any, summary: dict[str, Any] | None = None) -> str:
    meter = _meter(summary) if summary else ""
    return (
        '<article class="metric-card">'
        f"<span>{_e(label)}</span>"
        f"<strong>{_e(value)}</strong>"
        f"<p>{_e(detail)}</p>"
        f"{meter}"
        "</article>"
    )


def _table(
    headers: tuple[str, ...],
    rows: list[str],
    *,
    empty_text: str,
    caption: str | None = None,
) -> str:
    if not rows:
        return f'<div class="panel"><p>{_e(empty_text)}</p></div>'
    header_html = "".join(f"<th>{_e(header)}</th>" for header in headers)
    caption_html = f"<caption>{_e(caption)}</caption>" if caption else ""
    return (
        '<div class="table-wrap"><table>'
        f"{caption_html}"
        "<thead><tr>"
        f"{header_html}"
        "</tr></thead><tbody>"
        f"{''.join(rows)}"
        "</tbody></table></div>"
    )


def _list_panel(items: list[Any], kind: str) -> str:
    lis = "".join(f"<li>{_e(item)}</li>" for item in items)
    return f'<ul class="list {kind}">{lis}</ul>'


def _meter(item: dict[str, Any] | None) -> str:
    if not item:
        return '<div class="meter" aria-label="No meter available"><span style="width:0%"></span></div>'
    done = _int(item.get("done"))
    total = _int(item.get("total"))
    width = 0 if total <= 0 else max(0, min(100, round(done / total * 100)))
    label = f"{done}/{total} done, meter {item.get('meter', 'n/a')}"
    return (
        f'<div class="meter" role="progressbar" aria-valuemin="0" aria-valuemax="{_e(total)}" '
        f'aria-valuenow="{_e(done)}" aria-label="{_e(label)}">'
        f'<span class="{_result_class(item.get("result"))}" style="width:{width}%"></span>'
        f'</div><code class="meter-code">{_e(item.get("meter", ""))}</code>'
    )


def _read_json_source(root: Path, path: str | Path, label: str) -> tuple[dict[str, Any], dict[str, Any]]:
    full_path = _resolve(root, path)
    source = {
        "label": label,
        "repo_relative_path": _display_path(root, path),
        "state": "missing",
        "schema_version": "n/a",
    }
    if not full_path.exists():
        source["warning"] = "missing source file"
        return {}, source
    try:
        data = json.loads(full_path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise DashboardError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise DashboardError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise DashboardError(f"{path} must contain a JSON object")
    source["state"] = "loaded"
    source["schema_version"] = str(data.get("schema_version", "unknown"))
    source["generated_at"] = str(data.get("generated_at", ""))
    return data, source


def _read_text_source(root: Path, path: str | Path, label: str) -> tuple[str, dict[str, Any]]:
    full_path = _resolve(root, path)
    source = {
        "label": label,
        "repo_relative_path": _display_path(root, path),
        "state": "missing",
        "schema_version": "text",
    }
    if not full_path.exists():
        source["warning"] = "missing source file"
        return "", source
    try:
        text = full_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DashboardError(f"cannot read {path}: {exc}") from exc
    source["state"] = "loaded"
    return text, source


def _resolve(root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return root / candidate


def _display_path(root: Path, path: str | Path) -> str:
    candidate = Path(path)
    if candidate.is_absolute():
        try:
            return candidate.resolve().relative_to(root.resolve()).as_posix()
        except ValueError:
            return candidate.name
    return candidate.as_posix()


def _parse_label_block(text: str) -> dict[str, str]:
    labels: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        if key and " " not in key:
            labels[key] = value.strip()
    return labels


def _project_identity(
    adapter: dict[str, Any],
    status: dict[str, Any],
    runtime_labels: dict[str, str],
) -> dict[str, Any]:
    repo = _dict(status.get("repo"))
    return {
        "name": adapter.get("project") or "DevCockpitCore",
        "key": adapter.get("project_key") or "devcockpitcore",
        "branch": repo.get("branch", "unknown"),
        "head": repo.get("head", "unknown"),
        "active_artifact": runtime_labels.get("active_artifact", "unknown"),
        "artifact_next": runtime_labels.get("artifact_next", "unknown"),
    }


def _source_warnings(*sources: dict[str, Any]) -> list[str]:
    warnings = []
    for source in sources:
        if source.get("state") != "loaded":
            warnings.append(f"{source.get('label', 'source')}: {source.get('warning', 'not loaded')}")
    return warnings


def _freshness_summary(sources: list[dict[str, Any]], generated_at: str) -> dict[str, Any]:
    loaded_count = sum(1 for source in sources if source.get("state") == "loaded")
    generated_values = [
        str(source.get("generated_at"))
        for source in sources
        if source.get("generated_at")
    ]
    latest = max(generated_values) if generated_values else generated_at
    return {
        "loaded_count": f"{loaded_count}/{len(sources)}",
        "latest_generated_at": latest,
        "source_summary": f"{loaded_count} loaded, {len(sources) - loaded_count} missing",
    }


def _aggregate_health(
    validation: dict[str, Any],
    smoke: dict[str, Any],
    status: dict[str, Any],
    source_warnings: list[str],
) -> dict[str, Any]:
    warnings: list[str] = list(source_warnings)
    blockers: list[str] = []

    for label, payload in (("validation", validation), ("smoke", smoke)):
        summary = _dict(payload.get("summary"))
        result = summary.get("result")
        payload_health = _dict(payload.get("health"))
        warnings.extend(f"{label}: {item}" for item in _list(payload_health.get("warnings")))
        blockers.extend(f"{label}: {item}" for item in _list(payload_health.get("blockers")))
        if result == "fail":
            blockers.append(f"{label}: summary result is fail")
        elif result == "warn":
            warnings.append(f"{label}: summary result is warn")

    status_health = _dict(status.get("health"))
    if status_health.get("status") in {"yellow", "warn"}:
        warnings.extend(f"status: {item}" for item in _list(status_health.get("notes")))
    if status_health.get("status") in {"red", "fail"}:
        blockers.append("status snapshot health is red")

    stop_class = (
        _dict(validation.get("gate_input")).get("stop_class")
        or _dict(smoke.get("gate_input")).get("stop_class")
        or status_health.get("stop_class")
        or "unknown"
    )
    tone = "red" if blockers else "yellow" if warnings else "green"
    return {
        "tone": tone,
        "label": {"green": "Green", "yellow": "Yellow", "red": "Red"}[tone],
        "warnings": sorted(set(str(item) for item in warnings if item)),
        "blockers": sorted(set(str(item) for item in blockers if item)),
        "stop_class": stop_class,
        "summary": "blockers present" if blockers else "warnings only" if warnings else "no warnings",
    }


def _warning_triage(
    health: dict[str, Any],
    validation: dict[str, Any],
    smoke: dict[str, Any],
    status: dict[str, Any],
    sources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    blockers = _list(health.get("blockers"))
    groups.append(
        {
            "source": "Blockers",
            "severity": "red" if blockers else "green",
            "count": len(blockers),
            "items": blockers or ["No blockers reported in current evidence."],
        }
    )

    validation_warnings = _list(_dict(validation.get("health")).get("warnings"))
    if _dict(validation.get("summary")).get("result") == "warn":
        validation_warnings.append("validation summary result is warn")
    groups.append(
        {
            "source": "Validation Pack",
            "severity": "warn" if validation_warnings else "green",
            "count": len(validation_warnings),
            "items": validation_warnings or ["No validation warnings reported."],
        }
    )

    smoke_warnings = _list(_dict(smoke.get("health")).get("warnings"))
    if _dict(smoke.get("summary")).get("result") == "warn":
        smoke_warnings.append("cross-project smoke summary result is warn")
    groups.append(
        {
            "source": "Cross-Project Smoke",
            "severity": "warn" if smoke_warnings else "green",
            "count": len(smoke_warnings),
            "items": smoke_warnings or ["No smoke warnings reported."],
        }
    )

    project_items = []
    for project in _list(smoke.get("projects")):
        item = _dict(project)
        snapshot = _dict(item.get("status_snapshot"))
        for warning in _list(snapshot.get("warnings")):
            project_items.append(f"{item.get('project_key', 'project')}: {warning}")
    groups.append(
        {
            "source": "Project Rows",
            "severity": "warn" if project_items else "green",
            "count": len(project_items),
            "items": project_items or ["No project-row warnings reported."],
        }
    )

    status_items = _list(_dict(status.get("health")).get("notes"))
    groups.append(
        {
            "source": "Status Snapshot",
            "severity": "warn" if status_items else "green",
            "count": len(status_items),
            "items": status_items or ["No status snapshot notes reported."],
        }
    )

    source_items = [
        f"{source.get('label', 'source')}: {source.get('warning', 'not loaded')}"
        for source in sources
        if source.get("state") != "loaded"
    ]
    groups.append(
        {
            "source": "Source Files",
            "severity": "warn" if source_items else "green",
            "count": len(source_items),
            "items": source_items or ["All configured source files loaded."],
        }
    )
    return groups


def _review_actions(
    health: dict[str, Any],
    validation: dict[str, Any],
    smoke: dict[str, Any],
    status: dict[str, Any],
    sources: list[dict[str, Any]],
    warning_triage: list[dict[str, Any]],
    review_checkpoints: list[dict[str, str]],
    dashboard_path: str,
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    validation_path = _source_path(sources, "validation_pack_result")
    smoke_path = _source_path(sources, "cross_project_smoke_result")
    status_path = _source_path(sources, "status_snapshot")

    for blocker in _list(health.get("blockers")):
        _append_review_action(
            actions,
            prefix="blocker",
            source_type="dashboard_health",
            severity="blocker",
            project_key=None,
            source_path=dashboard_path,
            title="Review blocker before integration",
            reason=str(blocker),
            evidence_path=dashboard_path,
            suggested_review="Confirm the blocker and decide the smallest safe fix before using the dashboard as an integration signal.",
            owner_hint="supervisor",
            blocked_by_gate=False,
            safe_next_surface="local_review",
        )

    validation_warnings = _list(_dict(validation.get("health")).get("warnings"))
    if _dict(validation.get("summary")).get("result") == "warn":
        validation_warnings.append("validation summary result is warn")
    for warning in validation_warnings:
        _append_review_action(
            actions,
            prefix="validation",
            source_type="validation_pack",
            severity="warning",
            project_key="devcockpitcore",
            source_path=validation_path,
            title="Review validation warning",
            reason=str(warning),
            evidence_path=validation_path,
            suggested_review="Classify whether this is expected fixture or hygiene residue, then record whether cleanup is needed.",
            owner_hint="operator",
            blocked_by_gate=False,
            safe_next_surface="local_review",
        )

    smoke_warnings = _list(_dict(smoke.get("health")).get("warnings"))
    if _dict(smoke.get("summary")).get("result") == "warn":
        smoke_warnings.append("cross-project smoke summary result is warn")
    for warning in smoke_warnings:
        _append_review_action(
            actions,
            prefix="smoke",
            source_type="cross_project_smoke",
            severity="warning",
            project_key=None,
            source_path=smoke_path,
            title="Review cross-project smoke warning",
            reason=str(warning),
            evidence_path=smoke_path,
            suggested_review="Review the smoke row and decide whether the observer warning is expected; do not edit sibling repositories from this package.",
            owner_hint="operator",
            blocked_by_gate=False,
            safe_next_surface="dashboard_only",
        )

    for project in _list(smoke.get("projects")):
        item = _dict(project)
        project_key = str(item.get("project_key", "project"))
        snapshot = _dict(item.get("status_snapshot"))
        for warning in _list(snapshot.get("warnings")):
            _append_review_action(
                actions,
                prefix=f"project-{_slug(project_key)}",
                source_type="cross_project_smoke",
                severity="warning",
                project_key=project_key,
                source_path=smoke_path,
                title=f"Review {project_key} smoke row",
                reason=str(warning),
                evidence_path=smoke_path,
                suggested_review="Inspect this project row as observer evidence only; route any real project work through that project's own lane.",
                owner_hint="operator",
                blocked_by_gate=False,
                safe_next_surface="dashboard_only",
            )

    for note in _list(_dict(status.get("health")).get("notes")):
        _append_review_action(
            actions,
            prefix="status",
            source_type="status_snapshot",
            severity="warning",
            project_key="devcockpitcore",
            source_path=status_path,
            title="Review current repository status note",
            reason=str(note),
            evidence_path=status_path,
            suggested_review="Confirm the current worktree state is expected before treating the dashboard as ready for integration.",
            owner_hint="operator",
            blocked_by_gate=False,
            safe_next_surface="local_review",
        )

    for checkpoint in review_checkpoints:
        _append_review_action(
            actions,
            prefix="checkpoint",
            source_type="dashboard_review",
            severity="info",
            project_key="devcockpitcore",
            source_path=dashboard_path,
            title=str(checkpoint.get("label", "Review checkpoint")),
            reason=str(checkpoint.get("state", "review state")),
            evidence_path=str(checkpoint.get("evidence", dashboard_path)),
            suggested_review=str(checkpoint.get("prompt", "Review this checkpoint.")),
            owner_hint="supervisor",
            blocked_by_gate=False,
            safe_next_surface="manual_freeform",
        )

    if warning_triage:
        _append_review_action(
            actions,
            prefix="locked-gate",
            source_type="locked_gate",
            severity="info",
            project_key="devcockpitcore",
            source_path=dashboard_path,
            title="Keep locked lanes gated",
            reason="Locked lanes are reminders, not generated work items.",
            evidence_path=dashboard_path,
            suggested_review="Use locked lane cards only to confirm the dashboard did not expand execution authority.",
            owner_hint="supervisor",
            blocked_by_gate=True,
            safe_next_surface="dashboard_only",
        )
    return actions


def _append_review_action(
    actions: list[dict[str, Any]],
    *,
    prefix: str,
    source_type: str,
    severity: str,
    project_key: str | None,
    source_path: str,
    title: str,
    reason: str,
    evidence_path: str,
    suggested_review: str,
    owner_hint: str,
    blocked_by_gate: bool,
    safe_next_surface: str,
) -> None:
    action_id = f"{_slug(prefix)}-{len(actions) + 1:03d}"
    actions.append(
        {
            "action_id": action_id,
            "source_type": source_type,
            "severity": severity,
            "project_key": project_key,
            "source_path": source_path,
            "title": title,
            "reason": reason,
            "evidence_path": evidence_path,
            "suggested_review": suggested_review,
            "owner_hint": owner_hint,
            "executable": False,
            "blocked_by_gate": blocked_by_gate,
            "safe_next_surface": safe_next_surface,
        }
    )


def _review_action_summary(actions: list[dict[str, Any]]) -> dict[str, int]:
    summary = {
        "total": len(actions),
        "blocker": 0,
        "warning": 0,
        "info": 0,
        "locked_by_gate": 0,
    }
    for action in actions:
        severity = str(action.get("severity", "info"))
        if severity in summary:
            summary[severity] += 1
        if action.get("blocked_by_gate"):
            summary["locked_by_gate"] += 1
    return summary


def review_action_package(model: dict[str, Any]) -> dict[str, Any]:
    package = _dict(model.get("action_package"))
    output = _dict(model.get("output"))
    actions = _list(model.get("review_actions"))
    return {
        "schema_version": package.get("schema_version", "devcockpit_review_actions.v1"),
        "generated_at": model.get("generated_at"),
        "producer": PRODUCER,
        "source_dashboard": output.get("repo_relative_path"),
        "package": {
            "json_path": package.get("json_path"),
            "markdown_path": package.get("markdown_path"),
            "access_state": package.get("access_state"),
            "access_evidence_level": package.get("access_evidence_level"),
        },
        "summary": _dict(model.get("review_action_summary")),
        "actions": actions,
    }


def dumps_review_actions(package: dict[str, Any], *, pretty: bool = False) -> str:
    return json.dumps(
        package,
        ensure_ascii=False,
        indent=2 if pretty else None,
        sort_keys=False,
    ) + "\n"


def render_review_actions_markdown(package: dict[str, Any]) -> str:
    summary = _dict(package.get("summary"))
    lines = [
        "# DevCockpitCore Review Actions",
        "",
        "Non-executable review package generated from local dashboard evidence.",
        "",
        f"- generated_at: `{_md(package.get('generated_at', 'unknown'))}`",
        f"- source_dashboard: `{_md(package.get('source_dashboard', 'unknown'))}`",
        f"- total_actions: `{_md(summary.get('total', 0))}`",
        f"- blockers: `{_md(summary.get('blocker', 0))}`",
        f"- warnings: `{_md(summary.get('warning', 0))}`",
        f"- info: `{_md(summary.get('info', 0))}`",
        "",
        "## How to review this package",
        "",
        "1. Confirm blocker count is zero before using the dashboard as an integration signal.",
        "2. Review warning actions against their evidence paths and classify them as expected residue or future cleanup.",
        "3. Treat locked-by-gate entries as boundary reminders, not work items.",
        "",
        "| action_id | severity | source_type | project_key | title | evidence_path | executable |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for action in _list(package.get("actions")):
        item = _dict(action)
        lines.append(
            "| "
            + " | ".join(
                _md(item.get(field, ""))
                for field in (
                    "action_id",
                    "severity",
                    "source_type",
                    "project_key",
                    "title",
                    "evidence_path",
                    "executable",
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "Review notes:",
            "- These actions are review-only and not a runner.",
            "- Do not treat locked-by-gate entries as work items.",
            "- Use source evidence paths to inspect the underlying JSON before deciding next work.",
            "",
        ]
    )
    return "\n".join(lines)


def write_review_actions_json(package: dict[str, Any], output_path: str | Path, *, pretty: bool = False) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(dumps_review_actions(package, pretty=pretty), encoding="utf-8", newline="\n")


def write_review_actions_markdown(package: dict[str, Any], output_path: str | Path) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_review_actions_markdown(package), encoding="utf-8", newline="\n")


def _source_path(sources: list[dict[str, Any]], label: str) -> str:
    for source in sources:
        if source.get("label") == label:
            return str(source.get("repo_relative_path", label))
    return label


def _safe_to_run_items(output_rel: str) -> list[str]:
    return [
        f"Open the generated static file: {_powershell_open_command(output_rel)}",
        "Regenerate dashboard: PYTHONPATH=src python -m dev_cockpit.dashboard",
        "Regenerate validation evidence with the fixed default validation pack.",
        "Regenerate smoke evidence with the fixed default cross-project smoke.",
        "Run compileall and unittest locally before treating a slice as reviewed.",
    ]


def _safe_local_actions(output_rel: str) -> list[dict[str, str]]:
    return [
        {
            "kind": "OPEN_ONLY",
            "label": "Open generated dashboard",
            "command": _powershell_open_command(output_rel),
            "effect": "Local browser opens the generated HTML file; no server or repository writes.",
        },
        {
            "kind": "LOCAL_GENERATE",
            "label": "Regenerate dashboard",
            "command": "PYTHONPATH=src python -m dev_cockpit.dashboard --output samples/dashboard/devcockpitcore_dashboard.html",
            "effect": "Rebuilds the static HTML from existing local evidence files.",
        },
        {
            "kind": "LOCAL_CHECK",
            "label": "Run local tests",
            "command": "PYTHONPATH=src python -m unittest discover",
            "effect": "Runs DevCockpitCore unit tests in the current checkout only.",
        },
    ]


def _latest_brief(
    health: dict[str, Any],
    warning_triage: list[dict[str, Any]],
    freshness: dict[str, Any],
    output_rel: str,
    review_stack: list[dict[str, str]],
) -> dict[str, Any]:
    blockers = _list(health.get("blockers"))
    warnings = _list(health.get("warnings"))
    largest_warning = _largest_warning_group(warning_triage)
    first_next = review_stack[0] if review_stack else {}
    warning_source = str(largest_warning.get("source", "Warnings"))
    warning_source_label = _brief_warning_source_label(warning_source)
    warning_count = _int(largest_warning.get("count"))
    loaded, total = _parse_count_pair(str(freshness.get("loaded_count", "0/0")))
    access_label = "local file" if output_rel else "local artifact"
    if blockers:
        headline = "Pause locally; blocker evidence needs judgment before this can be a handoff signal."
        annotation = (
            "Treat the stop gate as the first read. Warning review can wait until the blocking row is explained."
        )
        first_step = {
            "label": "Pause",
            "value": f"{len(blockers)} blocker item(s)",
            "href": "#detail-stop-gate",
            "tone": "red",
        }
        primary_action = {"label": "Open stop gate", "href": "#detail-stop-gate"}
    elif warnings:
        headline = "Continue locally; the useful attention is warning judgment, not blocker hunting."
        annotation = (
            f"The largest review bucket is {warning_source_label}; read it as review debt and confirm whether it is expected observer residue."
        )
        first_step = {
            "label": "Continue",
            "value": "No blocker stop",
            "href": "#detail-stop-gate",
            "tone": "green",
        }
        primary_action = {
            "label": "Review warning detail",
            "href": _warning_group_href(warning_source),
        }
    else:
        headline = "Continue locally; current evidence is quiet enough for a quick handoff review."
        annotation = (
            f"All configured sources are loaded into the {access_label}; use the meters only to spot-check freshness and access."
        )
        first_step = {
            "label": "Continue",
            "value": "No blocker stop",
            "href": "#detail-stop-gate",
            "tone": "green",
        }
        primary_action = {
            "label": str(first_next.get("link_label") or "Open review stack"),
            "href": str(first_next.get("href") or "#review-stack"),
        }

    if loaded < total:
        proof_value = f"{loaded}/{total} sources loaded"
        proof_tone = "yellow"
    else:
        proof_value = f"{loaded}/{total} sources ready"
        proof_tone = "green"

    if warning_count:
        middle_value = f"{warning_count} item(s) need judgment"
    else:
        middle_value = "No warning bucket leads"

    return {
        "kind": "editorial",
        "headline": headline,
        "annotation": annotation,
        "runway": [
            first_step,
            {
                "label": "Warnings",
                "value": middle_value,
                "href": _warning_group_href(warning_source),
                "tone": "yellow" if warning_count else "green",
            },
            {
                "label": "Proof",
                "value": proof_value,
                "href": "#detail-evidence-freshness",
                "tone": proof_tone,
            },
        ],
        "primary_action": primary_action,
        "secondary_link": {
            "label": "Why blocked?" if blockers else "Why no blocker?",
            "href": "#detail-stop-gate",
        },
        "aside": {
            "label": "Not urgent",
            "text": "execution expansion stays locked; expected fixture residue belongs in review debt unless source evidence changes.",
        },
    }


def _decision_meters(
    health: dict[str, Any],
    validation: dict[str, Any],
    smoke: dict[str, Any],
    status: dict[str, Any],
    sources: list[dict[str, Any]],
    freshness: dict[str, Any],
    action_summary: dict[str, Any],
    warning_triage: list[dict[str, Any]],
    review_actions: list[dict[str, Any]],
    dashboard_path: str,
) -> list[dict[str, Any]]:
    blockers = _list(health.get("blockers"))
    warnings = _list(health.get("warnings"))
    action_total = _int(action_summary.get("total"))
    warning_actions = _int(action_summary.get("warning"))
    blocker_actions = _int(action_summary.get("blocker"))
    loaded_sources = sum(1 for source in sources if source.get("state") == "loaded")
    total_sources = len(sources)
    smoke_summary = _dict(smoke.get("summary"))
    status_repo = _dict(status.get("repo"))
    top_warning_group = _largest_warning_group(warning_triage)
    warning_action_types = _warning_group_source_types(str(top_warning_group.get("source", "")))
    access_primary = "Local" if dashboard_path else "Review"

    return [
        {
            "title": "Stop Gate",
            "primary_value": f"{len(blockers)} blockers",
            "summary": f"{_decision_label(health)}: {_decision_detail(health)}.",
            "why": "Start here because blockers decide whether the review can continue.",
            "detail_href": "#detail-stop-gate",
            "action_href": _action_href(review_actions, ("dashboard_health",), fallback="#detail-stop-gate"),
            "action_label": "Review action" if blocker_actions else "No blocker action",
            "evidence_path": "Health, Gate, Readiness",
            "tone": "red" if blockers else "green",
            "progress": {
                "done": blocker_actions,
                "total": action_total,
                "label": f"{blocker_actions}/{action_total} actions are blockers",
                "tone": "red" if blocker_actions else "green",
            },
        },
        {
            "title": "Warning Debt",
            "primary_value": f"{warning_actions} warnings",
            "summary": f"Largest group: {top_warning_group.get('source', 'none')}.",
            "why": "This points to the warning bucket most likely to need the next judgment.",
            "detail_href": "#detail-warning-debt",
            "action_href": _action_href(
                review_actions,
                warning_action_types,
                fallback="#review-actions",
            ),
            "action_label": "Review action",
            "evidence_path": top_warning_group.get("source", "Warnings Triage"),
            "tone": "yellow" if warning_actions or warnings else "green",
            "progress": {
                "done": warning_actions,
                "total": action_total,
                "label": f"{warning_actions}/{action_total} actions carry warnings",
                "tone": "yellow" if warning_actions else "green",
            },
        },
        {
            "title": "Evidence Freshness",
            "primary_value": str(freshness.get("loaded_count", "0/0")),
            "summary": f"Latest source: {_short_text(str(freshness.get('latest_generated_at', 'unknown')), 30)}.",
            "why": "Use this before trusting the dashboard as a current handoff surface.",
            "detail_href": "#detail-evidence-freshness",
            "action_href": _action_href(review_actions, ("dashboard_review",), fallback="#review-actions"),
            "evidence_path": "Sources and Access",
            "tone": "green" if loaded_sources == total_sources else "yellow",
            "progress": {
                "done": loaded_sources,
                "total": total_sources,
                "label": f"{loaded_sources}/{total_sources} configured sources loaded",
                "tone": "green" if loaded_sources == total_sources else "yellow",
            },
        },
        {
            "title": "Review Queue",
            "primary_value": f"{action_total} actions",
            "summary": f"{warning_actions} warnings, {action_summary.get('info', 0)} info.",
            "why": "This keeps the next decisions visible while preserving non-executable actions.",
            "detail_href": "#detail-review-actions",
            "action_href": _action_href(review_actions, ("locked_gate",), fallback="#review-actions"),
            "evidence_path": "samples/dashboard/devcockpitcore_review_actions.json",
            "tone": "yellow" if warning_actions else "green",
            "progress": {
                "done": warning_actions + blocker_actions,
                "total": action_total,
                "label": f"{warning_actions + blocker_actions}/{action_total} actions need triage",
                "tone": "yellow" if warning_actions or blocker_actions else "green",
            },
        },
        {
            "title": "Project Smoke",
            "primary_value": str(smoke_summary.get("result", "unknown")),
            "summary": _count_text(smoke_summary),
            "why": "This separates cross-project observer warnings from local implementation work.",
            "detail_href": "#detail-project-smoke",
            "action_href": _action_href(review_actions, ("cross_project_smoke",), fallback="#review-actions"),
            "evidence_path": "samples/cross_project_smokes/devcockpitcore_cross_project_smoke_result.json",
            "tone": smoke_summary.get("result", "neutral"),
            "progress": {
                "done": _int(smoke_summary.get("done")),
                "total": _int(smoke_summary.get("total")),
                "label": _count_text(smoke_summary),
                "tone": smoke_summary.get("result", "neutral"),
            },
        },
        {
            "title": "Access Readiness",
            "primary_value": access_primary,
            "summary": f"Repo is {status_repo.get('worktree', {}).get('state', 'unknown')}; open as static file.",
            "why": "Use this to confirm review access without adding a server, scheduler, or writeback path.",
            "detail_href": "#detail-source-files",
            "action_href": _action_href(review_actions, ("status_snapshot",), fallback="#review-actions"),
            "evidence_path": dashboard_path,
            "tone": "green" if loaded_sources == total_sources else "yellow",
            "progress": {
                "done": loaded_sources,
                "total": total_sources,
                "label": f"{loaded_sources}/{total_sources} access sources present",
                "tone": "green" if loaded_sources == total_sources else "yellow",
            },
        },
    ]


def _review_stack(
    health: dict[str, Any],
    warning_triage: list[dict[str, Any]],
    freshness: dict[str, Any],
    action_summary: dict[str, Any],
) -> list[dict[str, str]]:
    blockers = _list(health.get("blockers"))
    largest_warning = _largest_warning_group(warning_triage)
    stack = [
        {
            "title": "Check Stop Gate",
            "reason": (
                "Blockers exist and must be resolved before integration."
                if blockers
                else "No blockers are reported; confirm this before reviewing warning debt."
            ),
            "href": "#detail-stop-gate",
            "link_label": "Open stop gate",
            "evidence": "Health, Gate, Readiness",
        },
        {
            "title": f"Review {largest_warning.get('source', 'Warning Debt')}",
            "reason": f"{largest_warning.get('count', 0)} warning item(s) make this the largest current review bucket.",
            "href": _warning_group_href(str(largest_warning.get("source", ""))),
            "link_label": "Open warning detail",
            "evidence": str(largest_warning.get("source", "Warnings Triage")),
        },
    ]
    loaded, total = _parse_count_pair(str(freshness.get("loaded_count", "0/0")))
    if loaded < total:
        stack.append(
            {
                "title": "Refresh Evidence",
                "reason": f"{loaded}/{total} sources loaded; inspect missing or stale source evidence.",
                "href": "#detail-evidence-freshness",
                "link_label": "Open freshness detail",
                "evidence": "Sources and Access",
            }
        )
    elif _int(action_summary.get("warning")):
        stack.append(
            {
                "title": "Use Review Queue",
                "reason": f"{action_summary.get('warning', 0)} warning actions are ready for freeform review.",
                "href": "#detail-review-actions",
                "link_label": "Open action queue",
                "evidence": "Review Actions",
            }
        )
    else:
        stack.append(
            {
                "title": "Confirm Access",
                "reason": "All sources loaded; verify the local static handoff path and print view.",
                "href": "#detail-source-files",
                "link_label": "Open source detail",
                "evidence": "Sources and Access",
            }
        )
    return stack[:3]


def _largest_warning_group(groups: list[dict[str, Any]]) -> dict[str, Any]:
    candidates = [
        _dict(group)
        for group in groups
        if str(_dict(group).get("source", "")) != "Blockers"
    ]
    if not candidates:
        return {"source": "Warning Debt", "count": 0}
    return max(candidates, key=lambda item: _int(item.get("count")))


def _warning_group_href(source: str) -> str:
    mapping = {
        "Validation Pack": "#detail-warning-debt",
        "Cross-Project Smoke": "#detail-project-smoke",
        "Project Rows": "#detail-project-smoke",
        "Status Snapshot": "#detail-source-files",
        "Source Files": "#detail-evidence-freshness",
    }
    return mapping.get(source, "#detail-warning-debt")


def _brief_warning_source_label(source: str) -> str:
    mapping = {
        "Validation Pack": "validation findings",
        "Cross-Project Smoke": "cross-project smoke rows",
        "Project Rows": "project observer rows",
        "Status Snapshot": "repository status notes",
        "Source Files": "source freshness notes",
    }
    return mapping.get(source, "warning notes")


def _warning_group_source_types(source: str) -> tuple[str, ...]:
    mapping = {
        "Validation Pack": ("validation_pack",),
        "Cross-Project Smoke": ("cross_project_smoke",),
        "Project Rows": ("cross_project_smoke",),
        "Status Snapshot": ("status_snapshot",),
        "Source Files": ("dashboard_review",),
    }
    return mapping.get(source, ("validation_pack", "cross_project_smoke", "status_snapshot"))


def _action_href(
    actions: list[dict[str, Any]],
    source_types: tuple[str, ...],
    *,
    fallback: str,
) -> str:
    for action in actions:
        item = _dict(action)
        if str(item.get("source_type")) in source_types:
            return f"#{_slug(item.get('action_id', 'review-action'))}"
    return fallback


def _parse_count_pair(value: str) -> tuple[int, int]:
    if "/" not in value:
        return 0, 0
    left, right = value.split("/", 1)
    return _int(left), _int(right)


def _review_next_items(
    health: dict[str, Any],
    validation: dict[str, Any],
    smoke: dict[str, Any],
) -> list[str]:
    items = []
    if health.get("blockers"):
        items.append("Resolve blocker rows before using this as an integration signal.")
    elif health.get("warnings"):
        items.append("Review warning rows and confirm they are expected observer-only residue.")
    else:
        items.append("Use this dashboard as the first local review surface for current evidence.")
    items.append(
        f"Validation checks: {_count_text(_dict(validation.get('summary')))}."
    )
    items.append(
        f"Cross-project rows: {_count_text(_dict(smoke.get('summary')))}."
    )
    items.append("Open details only when a warning needs source evidence.")
    return items


def _review_checkpoints(
    health: dict[str, Any],
    validation: dict[str, Any],
    smoke: dict[str, Any],
) -> list[dict[str, str]]:
    validation_summary = _dict(validation.get("summary"))
    smoke_summary = _dict(smoke.get("summary"))
    blocker_count = len(_list(health.get("blockers")))
    warning_count = len(_list(health.get("warnings")))
    return [
        {
            "label": "1. Meter Clarity",
            "state": f"{blocker_count} blocker(s), {warning_count} warning signal(s)",
            "prompt": "Confirm the home meters tell which subsystem to inspect first.",
            "evidence": "Home Decision Meters",
        },
        {
            "label": "2. Detail Linkage",
            "state": "6 meter-linked detail panels",
            "prompt": "Confirm each meter link lands on the matching detail panel and back link.",
            "evidence": "Linked Detail Map",
        },
        {
            "label": "3. Evidence Freshness",
            "state": f"validation {validation_summary.get('result', 'unknown')} / smoke {smoke_summary.get('result', 'unknown')}",
            "prompt": "Verify source generated_at values are current enough for the review decision.",
            "evidence": "Sources and Access",
        },
    ]


def _decision_label(health: dict[str, Any]) -> str:
    if _list(health.get("blockers")):
        return "Stop"
    if str(health.get("tone", "")).lower() in {"yellow", "warn", "warning"}:
        return "Continue"
    if str(health.get("tone", "")).lower() in {"green", "pass"}:
        return "Ready"
    return "Review"


def _decision_detail(health: dict[str, Any]) -> str:
    if _list(health.get("blockers")):
        return "blockers first"
    if _list(health.get("warnings")):
        return "warnings only"
    return _short_text(str(health.get("summary", "source-backed")), 42)


def _access_label(output: dict[str, Any]) -> str:
    mode = str(output.get("access_mode", "unknown"))
    state = str(output.get("access_state", "unknown"))
    if mode == "local_static_file" and state == "worker_generated_not_user_opened":
        return "Local file / user-opened prior"
    if mode == "local_static_file":
        return "Local file"
    return _short_text(mode.replace("_", " "), 32)


def _count_text(summary: dict[str, Any]) -> str:
    done = summary.get("done", "?")
    total = summary.get("total", "?")
    passed = summary.get("passed")
    warnings = summary.get("warnings")
    failed = summary.get("failed")
    parts = [f"{done}/{total} complete"]
    if passed is not None:
        parts.append(f"{passed} pass")
    if warnings is not None:
        parts.append(f"{warnings} warn")
    if failed is not None:
        parts.append(f"{failed} fail")
    return ", ".join(parts)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _short_text(value: str, limit: int) -> str:
    value = " ".join(value.split())
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


def _slug(value: Any) -> str:
    text = str(value).lower()
    chars = []
    previous_dash = False
    for char in text:
        if char.isalnum():
            chars.append(char)
            previous_dash = False
        elif not previous_dash:
            chars.append("-")
            previous_dash = True
    return "".join(chars).strip("-") or "action"


def _md(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _powershell_open_command(output_rel: str) -> str:
    return "Start-Process .\\" + output_rel.replace("/", "\\")


def _result_class(value: Any) -> str:
    text = str(value).lower()
    if text in {"pass", "green", "loaded"}:
        return "is-green"
    if text in {"warn", "warning", "yellow", "missing", "skipped"}:
        return "is-yellow"
    if text in {"fail", "red", "error", "blocker"}:
        return "is-red"
    return "is-neutral"


def _tone_class(value: Any) -> str:
    return _result_class(value)


def _e(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _dashboard_script() -> str:
    return """
(function () {
  var search = document.querySelector("[data-dashboard-search]");
  var buttons = Array.prototype.slice.call(document.querySelectorAll("[data-filter-result]"));
  var cards = Array.prototype.slice.call(document.querySelectorAll("[data-dashboard-project]"));
  var actionSearch = document.querySelector("[data-action-search]");
  var actionButtons = Array.prototype.slice.call(document.querySelectorAll("[data-filter-action-severity]"));
  var actionCards = Array.prototype.slice.call(document.querySelectorAll("[data-review-action]"));
  var active = "all";
  var activeActionSeverity = "all";

  function applyFilters() {
    var query = search ? search.value.trim().toLowerCase() : "";
    cards.forEach(function (card) {
      var result = card.getAttribute("data-result") || "unknown";
      var text = card.getAttribute("data-search") || "";
      var resultMatch = active === "all" || result === active;
      var textMatch = query === "" || text.indexOf(query) !== -1;
      card.hidden = !(resultMatch && textMatch);
    });
  }

  buttons.forEach(function (button) {
    button.addEventListener("click", function () {
      active = button.getAttribute("data-filter-result") || "all";
      buttons.forEach(function (item) { item.setAttribute("aria-pressed", "false"); });
      button.setAttribute("aria-pressed", "true");
      applyFilters();
    });
  });

  if (search) {
    search.addEventListener("input", applyFilters);
  }

  if (buttons.length) {
    buttons[0].setAttribute("aria-pressed", "true");
  }

  function applyActionFilters() {
    var query = actionSearch ? actionSearch.value.trim().toLowerCase() : "";
    actionCards.forEach(function (card) {
      var severity = card.getAttribute("data-severity") || "info";
      var text = card.getAttribute("data-search") || "";
      var severityMatch = activeActionSeverity === "all" || severity === activeActionSeverity;
      var textMatch = query === "" || text.indexOf(query) !== -1;
      card.hidden = !(severityMatch && textMatch);
    });
  }

  actionButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      activeActionSeverity = button.getAttribute("data-filter-action-severity") || "all";
      actionButtons.forEach(function (item) { item.setAttribute("aria-pressed", "false"); });
      button.setAttribute("aria-pressed", "true");
      applyActionFilters();
    });
  });

  if (actionSearch) {
    actionSearch.addEventListener("input", applyActionFilters);
  }

  if (actionButtons.length) {
    actionButtons[0].setAttribute("aria-pressed", "true");
  }
}());
""".strip()


def _stylesheet() -> str:
    return """
:root {
  color-scheme: dark;
  --ink: #f4f1e8;
  --muted: #b8bdaa;
  --line: #3a4038;
  --panel: #1b1f1b;
  --paper: #111411;
  --soft: #232920;
  --green: #57b985;
  --yellow: #d9a84e;
  --red: #ee6878;
  --navy: #4d705f;
  --teal: #66c6a6;
  --amber-soft: #3a301c;
  --shadow: rgba(0, 0, 0, 0.35);
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font-family: "Segoe UI", Arial, sans-serif;
  line-height: 1.45;
}
a { color: var(--teal); }
a:focus-visible, button:focus-visible, input:focus-visible, [tabindex]:focus-visible {
  outline: 3px solid var(--yellow);
  outline-offset: 3px;
}
.skip-link {
  position: absolute;
  left: 16px;
  top: -48px;
  z-index: 10;
  padding: 8px 12px;
  background: #f4f1e8;
  color: #111411;
  border: 2px solid var(--yellow);
  border-radius: 6px;
  font-weight: 700;
}
.skip-link:focus {
  top: 12px;
}
.top-strip {
  display: grid;
  grid-template-columns: minmax(260px, 0.56fr) minmax(620px, 1fr);
  gap: 24px;
  align-items: stretch;
  padding: 26px 32px 22px;
  background: #151914;
  border-bottom: 1px solid var(--line);
}
.dashboard-nav {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 9px 32px;
  background: #171b17;
  border-bottom: 1px solid var(--line);
}
.dashboard-nav a {
  display: inline-flex;
  min-height: 34px;
  align-items: center;
  padding: 5px 10px;
  border: 1px solid var(--line);
  border-radius: 6px;
  color: var(--ink);
  font-weight: 700;
  text-decoration: none;
}
.dashboard-nav a:hover {
  background: var(--soft);
}
h1, h2, h3, p { margin-top: 0; }
h1 { margin-bottom: 8px; font-size: 30px; letter-spacing: 0; }
h2 { margin-bottom: 14px; font-size: 20px; letter-spacing: 0; }
h3 { margin-bottom: 10px; font-size: 16px; letter-spacing: 0; }
h4 { margin: 0 0 8px; font-size: 14px; letter-spacing: 0; }
.eyebrow {
  margin-bottom: 6px;
  color: var(--yellow);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}
.subtle { color: var(--muted); font-size: 13px; }
.hero-copy { min-width: 0; }
.hero-summary {
  max-width: 34rem;
  margin-bottom: 12px;
  color: var(--muted);
  font-size: 15px;
}
.latest-brief {
  margin-top: 14px;
  padding: 14px;
  border: 1px solid #524832;
  border-left: 4px solid var(--yellow);
  border-radius: 8px;
  background: #211f1a;
}
.latest-brief h2 {
  margin: 0 0 8px;
  color: var(--yellow);
  font-size: 13px;
  text-transform: uppercase;
}
.brief-headline {
  margin: 0 0 8px;
  color: var(--ink);
  font-size: 18px;
  font-weight: 800;
  line-height: 1.25;
}
.brief-annotation {
  margin: 0 0 12px;
  color: var(--muted);
  font-size: 13px;
}
.brief-runway {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px;
  margin: 0 0 12px;
  padding: 0;
  list-style: none;
}
.brief-runway li {
  min-height: 58px;
  padding: 8px;
  border: 1px solid rgba(244, 241, 232, 0.14);
  border-radius: 6px;
  background: #151914;
}
.brief-runway span,
.brief-aside span {
  display: block;
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}
.brief-runway strong {
  display: block;
  margin-top: 4px;
  font-size: 13px;
  line-height: 1.2;
  overflow-wrap: anywhere;
}
.brief-footer {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
  align-items: end;
}
.brief-aside {
  margin: 0;
  color: var(--muted);
  font-size: 12px;
}
.brief-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}
.brief-primary-action,
.brief-secondary {
  display: inline-flex;
  min-height: 32px;
  align-items: center;
  padding: 5px 10px;
  border: 1px solid rgba(244, 241, 232, 0.22);
  border-radius: 6px;
  color: var(--ink);
  font-size: 12px;
  font-weight: 700;
  text-decoration: none;
}
.brief-primary-action {
  background: rgba(217, 168, 78, 0.16);
}
.overview-board {
  display: grid;
  grid-template-columns: 1.2fr repeat(3, minmax(112px, 0.72fr));
  gap: 10px;
}
.overview-card {
  min-height: 112px;
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #1e241f;
  box-shadow: 0 12px 30px var(--shadow);
}
.overview-card span {
  display: block;
  margin-bottom: 8px;
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
}
.overview-card strong {
  display: block;
  font-size: 28px;
  line-height: 1.05;
  overflow-wrap: anywhere;
}
.overview-card p {
  margin: 8px 0 0;
  color: var(--muted);
  font-size: 13px;
}
.overview-primary {
  background: #243321;
  border-color: #53633b;
}
.decision-meter-board {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}
.decision-meter {
  display: grid;
  gap: 8px;
  min-height: 186px;
  padding: 13px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #1e241f;
  box-shadow: 0 12px 30px var(--shadow);
}
.decision-meter.is-green { color: var(--ink); background: #1e2a21; border-color: #405d45; }
.decision-meter.is-yellow { color: var(--ink); background: #2d281b; border-color: #6c562b; }
.decision-meter.is-red { color: var(--ink); background: #2d1b20; border-color: #7d3b45; }
.decision-meter.is-neutral { color: var(--ink); background: #1b2528; border-color: #38606a; }
.meter-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}
.meter-head span {
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}
.meter-head strong {
  font-size: 24px;
  line-height: 1.05;
  text-align: right;
  overflow-wrap: anywhere;
}
.decision-meter p {
  margin: 0;
  color: var(--muted);
  font-size: 13px;
}
.decision-progress {
  width: 100%;
  height: 10px;
  overflow: hidden;
  background: #101410;
  border-radius: 4px;
}
.decision-progress span { display: block; height: 100%; border-radius: 4px; }
.meter-note { font-size: 12px; }
.why-line { color: var(--ink); }
.meter-links {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.meter-links a,
.stack-card a,
.back-link {
  display: inline-flex;
  min-height: 32px;
  align-items: center;
  padding: 5px 10px;
  border: 1px solid rgba(244, 241, 232, 0.24);
  border-radius: 6px;
  color: var(--ink);
  font-weight: 700;
  text-decoration: none;
}
.meter-links a:first-child,
.stack-card a {
  background: rgba(102, 198, 166, 0.14);
}
.review-strip {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: auto minmax(180px, 1fr) auto;
  gap: 12px;
  align-items: center;
  min-height: 48px;
  padding: 10px 12px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--amber-soft);
}
.review-strip span {
  color: var(--yellow);
  font-size: 12px;
  font-weight: 700;
}
.review-strip p { margin: 0; color: var(--ink); }
.review-strip a {
  min-height: 32px;
  padding: 5px 10px;
  border: 1px solid rgba(244, 241, 232, 0.24);
  border-radius: 6px;
  text-decoration: none;
  font-weight: 700;
}
.top-kpis {
  display: grid;
  grid-template-columns: 1.2fr repeat(4, minmax(88px, 1fr));
  gap: 8px;
}
.kpi-large, .kpi-small {
  min-height: 78px;
  padding: 10px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: var(--soft);
  overflow-wrap: anywhere;
}
.kpi-large span, .kpi-small span {
  display: block;
  margin-bottom: 5px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
}
.kpi-large strong { display: block; font-size: 24px; }
.kpi-small strong { display: block; font-size: 14px; }
.page { padding: 18px 32px 40px; }
.review-stack-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.stack-card {
  min-height: 152px;
  padding: 14px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 6px;
}
.stack-card span {
  display: block;
  margin-bottom: 6px;
  color: var(--yellow);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}
.stack-card strong {
  display: block;
  margin-bottom: 8px;
  font-size: 18px;
}
.stack-card p { color: var(--muted); font-size: 13px; }
.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
  margin-bottom: 24px;
}
.metric-card, .panel, .table-wrap, .checkpoint-card, .triage-card, .project-card, .action-card, .review-action-card, .locked-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 6px;
}
.metric-card { padding: 14px; min-height: 126px; }
.metric-card span {
  display: block;
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}
.metric-card strong {
  display: block;
  margin: 8px 0 6px;
  font-size: 24px;
  overflow-wrap: anywhere;
}
.metric-card p { margin-bottom: 10px; color: var(--muted); font-size: 13px; }
.section { margin-top: 18px; }
.section-grid { display: grid; gap: 12px; }
.grid-three { grid-template-columns: repeat(3, minmax(220px, 1fr)); }
.panel { padding: 16px; }
.disclosure {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #171b17;
}
.disclosure > summary {
  display: grid;
  grid-template-columns: auto minmax(160px, auto) minmax(220px, 1fr);
  gap: 14px;
  align-items: center;
  min-height: 56px;
  padding: 12px 14px;
  cursor: pointer;
  list-style: none;
}
.disclosure > summary::-webkit-details-marker { display: none; }
.disclosure > summary::before {
  content: "+";
  display: inline-grid;
  place-items: center;
  width: 24px;
  height: 24px;
  margin-right: 8px;
  border: 1px solid var(--line);
  border-radius: 6px;
  color: var(--yellow);
}
.disclosure[open] > summary::before { content: "-"; }
.disclosure > summary h2,
.disclosure > summary h3 {
  display: inline;
  margin: 0;
}
.disclosure > summary span {
  color: var(--muted);
  font-size: 13px;
}
.disclosure > .section-grid {
  padding: 0 14px 14px;
}
.detail-panel { background: #1a1e1a; }
.linked-detail-grid {
  display: grid;
  gap: 14px;
}
.detail-anchor-panel {
  padding: 16px;
  border-top: 1px solid var(--line);
  background: #151914;
}
.detail-anchor-panel:target {
  outline: 3px solid rgba(217, 168, 78, 0.75);
  outline-offset: 3px;
}
.detail-anchor-head {
  display: grid;
  grid-template-columns: minmax(180px, 1fr) auto;
  gap: 8px 14px;
  align-items: start;
}
.detail-anchor-head span {
  color: var(--yellow);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}
.detail-anchor-head h3,
.detail-anchor-head p {
  grid-column: 1;
  margin: 0;
}
.detail-anchor-head p { color: var(--muted); }
.detail-anchor-head .back-link {
  grid-column: 2;
  grid-row: 1 / span 3;
  align-self: start;
}
.detail-body {
  display: grid;
  gap: 12px;
  margin-top: 12px;
}
.related-actions {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--line);
}
.checkpoint-grid, .triage-grid, .project-card-grid, .action-grid, .action-review-grid, .locked-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
  gap: 12px;
}
.checkpoint-card, .triage-card, .project-card, .action-card, .review-action-card, .locked-card {
  padding: 14px;
}
.checkpoint-card span, .action-card span, .locked-card span, .triage-heading span {
  display: block;
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}
.checkpoint-card strong, .action-card strong, .locked-card strong {
  display: block;
  margin: 6px 0;
  font-size: 17px;
}
.triage-heading, .project-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
}
.project-card h3 { margin-bottom: 8px; }
.filter-panel {
  display: grid;
  grid-template-columns: minmax(220px, 1fr) 2fr;
  gap: 10px 14px;
  align-items: end;
}
.filter-panel h3, .filter-panel .subtle { grid-column: 1 / -1; }
.filter-panel label {
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}
.filter-panel input {
  width: 100%;
  min-height: 36px;
  padding: 7px 9px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: #121612;
  color: var(--ink);
  font: inherit;
}
.filter-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.filter-buttons button {
  min-height: 34px;
  padding: 6px 10px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: #161a16;
  color: var(--ink);
  font: inherit;
  font-weight: 700;
}
.filter-buttons button[aria-pressed="true"] {
  background: var(--teal);
  color: #111411;
}
.locked-card {
  border-color: rgba(238, 104, 120, 0.65);
  background: #2d1b20;
}
.locked-card span { color: var(--red); }
.review-action-card {
  border-left: 4px solid var(--teal);
}
.action-summary {
  border-left: 4px solid var(--navy);
}
.status-badge, .pill {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 3px 9px;
  border-radius: 6px;
  font-weight: 700;
}
.status-badge { min-width: 96px; justify-content: center; }
.is-green { color: #0d140f; background: var(--green); }
.is-yellow { color: #171106; background: var(--yellow); }
.is-red { color: #1a070b; background: var(--red); }
.is-neutral { color: #0d140f; background: var(--teal); }
.meter {
  width: 100%;
  height: 10px;
  margin: 7px 0 4px;
  overflow: hidden;
  background: #101410;
  border-radius: 4px;
}
.meter span { display: block; height: 100%; border-radius: 4px; }
.meter-code { color: var(--muted); font-size: 12px; }
.table-wrap { overflow-x: auto; background: #171b17; }
table { width: 100%; border-collapse: collapse; min-width: 760px; }
caption {
  padding: 10px 12px;
  color: var(--muted);
  font-size: 13px;
  text-align: left;
}
th, td { padding: 10px 12px; border-bottom: 1px solid var(--line); text-align: left; vertical-align: top; }
th { color: var(--muted); font-size: 12px; text-transform: uppercase; }
td { font-size: 14px; }
code {
  padding: 1px 4px;
  background: #101410;
  color: #eadfbd;
  border-radius: 4px;
  font-family: Consolas, "Courier New", monospace;
  overflow-wrap: anywhere;
}
.list { margin: 0; padding-left: 19px; }
.list li { margin: 6px 0; }
.compact-list li { margin: 3px 0; }
.safe li::marker { color: var(--green); }
.locked li::marker, .blocker-list li::marker { color: var(--red); }
.review li::marker, .warning-list li::marker { color: var(--yellow); }
.notes li::marker, .readiness li::marker { color: var(--teal); }
.access-panel { margin-top: 12px; }
.noscript-notice { border-left: 4px solid var(--yellow); }
.dashboard-footer {
  padding: 18px 32px 28px;
  color: var(--muted);
  background: #151914;
  border-top: 1px solid var(--line);
}
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    scroll-behavior: auto !important;
    transition-duration: 0.01ms !important;
    animation-duration: 0.01ms !important;
  }
}
@media (max-width: 980px) {
  .top-strip { grid-template-columns: 1fr; align-items: start; }
  .overview-board, .top-kpis, .decision-meter-board, .review-stack-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .summary-grid, .grid-three { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .filter-panel { grid-template-columns: 1fr; }
}
@media (max-width: 640px) {
  .top-strip { padding: 22px 18px; }
  .page { padding: 18px; }
  .summary-grid, .grid-three, .overview-board, .top-kpis, .decision-meter-board, .review-stack-grid { grid-template-columns: 1fr; }
  .review-strip { grid-template-columns: 1fr; }
  .disclosure > summary { grid-template-columns: auto 1fr; }
  .disclosure > summary span { grid-column: 2; }
  .brief-runway, .brief-footer { grid-template-columns: 1fr; }
  .brief-actions { justify-content: flex-start; }
  .detail-anchor-head { grid-template-columns: 1fr; }
  .detail-anchor-head .back-link { grid-column: 1; grid-row: auto; }
  h1 { font-size: 24px; }
}
@media print {
  body {
    background: #ffffff;
    color: #000000;
    font-size: 11pt;
  }
  :root {
    color-scheme: light;
    --ink: #000000;
    --muted: #333333;
    --line: #999999;
    --panel: #ffffff;
    --paper: #ffffff;
    --soft: #eeeeee;
  }
  .skip-link, .dashboard-nav, .filter-panel, script {
    display: none !important;
  }
  .top-strip, .dashboard-footer, .metric-card, .panel, .table-wrap, .checkpoint-card, .triage-card, .project-card, .action-card, .review-action-card, .locked-card, .decision-meter, .stack-card, .detail-anchor-panel, .latest-brief {
    border-color: #999999;
    box-shadow: none;
    background: #ffffff;
    color: #000000;
  }
  .disclosure {
    background: #ffffff;
    border-color: #999999;
  }
  .disclosure:not([open]) > :not(summary) {
    display: block;
  }
  .review-strip, .overview-card {
    background: #ffffff;
    color: #000000;
    box-shadow: none;
  }
  .page {
    padding: 0;
  }
  .section {
    break-inside: avoid;
    page-break-inside: avoid;
  }
  a[href]::after {
    content: " (" attr(href) ")";
    font-size: 9pt;
  }
}
""".strip()


if __name__ == "__main__":
    raise SystemExit(main())
