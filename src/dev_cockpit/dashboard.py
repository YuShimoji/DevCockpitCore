"""Generate a static local review dashboard from DevCockpitCore evidence."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import sys
from typing import Any

from .evidence_freshness import EvidenceFreshnessError, load_receipt
from .supervision_packet import (
    SupervisionPacketError,
    load_packet,
    load_packet_with_manifest,
)


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
DEFAULT_FRESHNESS_RECEIPT_PATH = (
    "samples/evidence_freshness/evidence_freshness_receipt_v1.json"
)
DEFAULT_PRIORITY_READBACK_PATH = "samples/dashboard/devcockpitcore_priority_readback.json"

PRIORITY_POLICY = (
    {
        "precedence": 1,
        "key": "required_blocker",
        "label_ja": "必須ブロッカー",
        "label_en": "Required blocker",
    },
    {
        "precedence": 2,
        "key": "required_validation_failure",
        "label_ja": "必須検証失敗",
        "label_en": "Required validation failure",
    },
    {
        "precedence": 3,
        "key": "current_state_evidence_ineligible",
        "label_ja": "現状根拠の不適格",
        "label_en": "Current-state evidence ineligible",
    },
    {
        "precedence": 4,
        "key": "owned_actionable_warning",
        "label_ja": "担当付き警告",
        "label_en": "Owned actionable warning",
    },
    {
        "precedence": 5,
        "key": "maintenance_or_decision",
        "label_ja": "保守・判断",
        "label_en": "Maintenance or decision",
    },
    {
        "precedence": 6,
        "key": "optional_information",
        "label_ja": "任意・参考情報",
        "label_en": "Optional information",
    },
)

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
    freshness_receipt_path: str | Path = DEFAULT_FRESHNESS_RECEIPT_PATH,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    review_actions_json_path: str | Path = DEFAULT_REVIEW_ACTIONS_JSON_PATH,
    review_actions_md_path: str | Path = DEFAULT_REVIEW_ACTIONS_MD_PATH,
    priority_readback_path: str | Path = DEFAULT_PRIORITY_READBACK_PATH,
    supervision_packet_path: str | Path | None = None,
    supervision_manifest_path: str | Path | None = None,
    verify_freshness_hashes: bool = False,
    generated_at: str | None = None,
) -> dict[str, Any]:
    if supervision_manifest_path is not None and supervision_packet_path is None:
        raise DashboardError("supervision manifest requires a supervision packet")
    root = Path(repo_root)

    freshness_full_path = _resolve(root, freshness_receipt_path)
    if not freshness_full_path.exists():
        raise DashboardError(f"missing evidence freshness receipt: {freshness_receipt_path}")
    try:
        freshness_receipt = load_receipt(
            freshness_full_path,
            repo_root=root,
            verify_hashes=verify_freshness_hashes,
        )
    except (EvidenceFreshnessError, OSError) as exc:
        raise DashboardError(f"invalid evidence freshness receipt {freshness_receipt_path}: {exc}") from exc
    generated = generated_at or str(freshness_receipt["assessed_at"])

    validation, validation_source = _read_json_source(root, validation_result_path, "validation_pack_result")
    smoke, smoke_source = _read_json_source(root, cross_project_smoke_result_path, "cross_project_smoke_result")
    status, status_source = _read_json_source(root, status_snapshot_path, "status_snapshot")
    adapter, adapter_source = _read_json_source(root, adapter_path, "adapter_manifest")
    runtime_text, runtime_source = _read_text_source(root, runtime_state_path, "runtime_state")
    project_context_text, project_context_source = _read_text_source(
        root, project_context_path, "project_context"
    )
    supervision_packet: dict[str, Any] = {}
    supervision_packet_source: dict[str, Any] | None = None
    if supervision_packet_path is not None:
        packet_full_path = _resolve(root, supervision_packet_path)
        try:
            if supervision_manifest_path is not None:
                supervision_packet = load_packet_with_manifest(
                    packet_full_path,
                    _resolve(root, supervision_manifest_path),
                    repo_root=root,
                )
            else:
                supervision_packet = load_packet(packet_full_path)
        except (SupervisionPacketError, OSError) as exc:
            raise DashboardError(
                f"invalid cross-project supervision packet {supervision_packet_path}: {exc}"
            ) from exc
        supervision_packet_source = {
            "label": "cross_project_supervision_packet",
            "repo_relative_path": _display_path(root, supervision_packet_path),
            "state": "loaded",
            "schema_version": str(supervision_packet.get("schema_version", "unknown")),
            "generated_at": str(supervision_packet.get("generated_at", "")),
            "artifact_id": str(supervision_packet.get("artifact_id", "")),
            "binding_mode": (
                "source_bound_manifest_reprojection"
                if supervision_manifest_path is not None
                else "standalone_packet_contract"
            ),
            "manifest_path": (
                _display_path(root, supervision_manifest_path)
                if supervision_manifest_path is not None
                else None
            ),
        }
    freshness_receipt_source = {
        "label": "evidence_freshness_receipt",
        "repo_relative_path": _display_path(root, freshness_receipt_path),
        "state": "loaded",
        "schema_version": str(freshness_receipt.get("schema_version", "unknown")),
        "generated_at": str(freshness_receipt.get("assessed_at", "")),
        "capture_id": str(freshness_receipt.get("capture_id", "")),
        "hashes_verified": verify_freshness_hashes,
    }

    runtime_labels = _parse_label_block(runtime_text)
    project_identity = _project_identity(adapter, status, runtime_labels)
    source_warnings = _source_warnings(
        validation_source,
        smoke_source,
        status_source,
        adapter_source,
        runtime_source,
        project_context_source,
        freshness_receipt_source,
        *([supervision_packet_source] if supervision_packet_source else []),
    )
    health = _aggregate_health(validation, smoke, status, source_warnings)
    output_rel = _display_path(root, output_path)
    actions_json_rel = _display_path(root, review_actions_json_path)
    actions_md_rel = _display_path(root, review_actions_md_path)
    priority_readback_rel = _display_path(root, priority_readback_path)
    sources = [
        validation_source,
        smoke_source,
        status_source,
        adapter_source,
        runtime_source,
        project_context_source,
        freshness_receipt_source,
    ]
    if supervision_packet_source:
        sources.append(supervision_packet_source)
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
    source_freshness = _freshness_summary(sources, generated)
    evidence_freshness = _receipt_freshness_projection(freshness_receipt)
    priority_items = (
        _packet_priority_items(supervision_packet)
        if supervision_packet
        else _priority_items(
            health=health,
            validation=validation,
            smoke=smoke,
            status=status,
            receipt=freshness_receipt,
            review_actions=review_actions,
            validation_path=_display_path(root, validation_result_path),
            smoke_path=_display_path(root, cross_project_smoke_result_path),
            status_path=_display_path(root, status_snapshot_path),
        )
    )
    informational_items = (
        _packet_informational_items(supervision_packet)
        if supervision_packet
        else []
    )
    packet_attention = _packet_attention_summary(supervision_packet)
    decision_meters = _decision_meters(
        health,
        validation,
        smoke,
        status,
        sources,
        source_freshness,
        action_summary,
        warning_triage,
        review_actions,
        output_rel,
    )
    review_stack = _review_stack(health, warning_triage, source_freshness, action_summary)
    frontpage_report = _frontpage_report(health, warning_triage, source_freshness, output_rel, review_stack)

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
        "priority_readback": {
            "repo_relative_path": priority_readback_rel,
            "schema_version": "devcockpit_priority_readback.v1",
            "access_state": "worker_generated_not_user_opened",
            "access_evidence_level": "file_generated_by_dashboard_command",
        },
        "sources": sources,
        "freshness": source_freshness,
        "source_freshness": source_freshness,
        "evidence_freshness": evidence_freshness,
        "evidence_freshness_receipt": freshness_receipt,
        "supervision_packet": supervision_packet,
        "priority_policy": (
            [dict(item) for item in _list(supervision_packet.get("attention_policy"))]
            if supervision_packet
            else [dict(item) for item in PRIORITY_POLICY]
        ),
        "priority_items": priority_items,
        "informational_items": informational_items,
        "selected_priority_id": priority_items[0]["priority_id"] if priority_items else None,
        "selected_closed_evidence_id": (
            informational_items[0]["primary_evidence_id"]
            if not priority_items and informational_items
            else None
        ),
        "packet_attention": packet_attention,
        "user_visual_acceptance": "accepted",
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
        "frontpage_report": frontpage_report,
        "latest_brief": frontpage_report,
        "warning_triage": warning_triage,
        "review_actions": review_actions,
        "review_action_summary": action_summary,
        "designer_notes": list(DESIGNER_NOTES),
    }


def render_dashboard(model: dict[str, Any]) -> str:
    """Render the selected Priority Review Console as the production surface."""

    project = _dict(model.get("project"))
    health = _dict(model.get("health"))
    validation = _dict(model.get("validation_pack"))
    smoke = _dict(model.get("cross_project_smoke"))
    action_package = _dict(model.get("action_package"))
    action_summary = _dict(model.get("review_action_summary"))
    output = _dict(model.get("output"))
    freshness = _dict(model.get("evidence_freshness"))
    receipt = _dict(model.get("evidence_freshness_receipt"))
    supervision_packet = _dict(model.get("supervision_packet"))
    priorities = [item for item in _list(model.get("priority_items")) if isinstance(item, dict)]
    informational_items = [
        item for item in _list(model.get("informational_items")) if isinstance(item, dict)
    ]
    if not priorities and not informational_items:
        raise DashboardError("priority console requires at least one priority item")
    all_closed = bool(supervision_packet and not priorities and informational_items)
    selected = priorities[0] if priorities else informational_items[0]
    interaction_items = priorities if priorities else informational_items
    packet_attention = _dict(model.get("packet_attention"))
    eligible = _dict(freshness.get("current_state_claim_eligible"))
    source_counts = _dict(freshness.get("source_counts"))
    authority_copy = _authority_copy(_dict(freshness.get("authority")))
    has_blockers = bool(_list(health.get("blockers")))
    local_health_ja = "停止" if has_blockers else "継続可能"
    local_health_en = "Blocked" if has_blockers else "Continue"
    packet_attention_ja = (
        f"停止 {packet_attention.get('stop', 0)} / "
        f"判断 {packet_attention.get('decision', 0)} / "
        f"対応中 {packet_attention.get('active', 0)} / "
        f"完了 {packet_attention.get('closed', 0)}"
    )
    packet_attention_en = (
        f"{packet_attention.get('stop', 0)} stop / "
        f"{packet_attention.get('decision', 0)} decision / "
        f"{packet_attention.get('active', 0)} active / "
        f"{packet_attention.get('closed', 0)} closed"
    )
    fallback_ja = (
        "完了済み情報とその根拠を以下に表示します。"
        if all_closed
        else "完全な代替表示として、順位1、その判断、根拠を以下に表示します。"
    )
    fallback_en = (
        "Completed information and its evidence are rendered below."
        if all_closed
        else "Rank 1, its active decision, and its evidence are rendered below as the complete fallback."
    )

    lines = [
        "<!doctype html>",
        '<html lang="ja" data-language="ja">',
        "<head>",
        '  <meta charset="utf-8">',
        '  <meta name="viewport" content="width=device-width, initial-scale=1">',
        f"  <title>Priority Review Console · {_e(project.get('name', 'DevCockpitCore'))}</title>",
        '  <meta name="color-scheme" content="dark">',
        "  <style>",
        _stylesheet(),
        "  </style>",
        "</head>",
        '<body data-dashboard-variant="priority-review-console-production" data-dashboard-theme="dark">',
        '  <a class="skip-link" href="#main-content"><span class="lang-ja">主要画面へ移動</span><span class="lang-en">Skip to main console</span></a>',
        '  <header class="production-header" data-landmark="current-state">',
        '    <div class="production-title-row">',
        '      <div class="production-title-copy">',
        '        <p class="eyebrow">DEVCOCKPITCORE / OBSERVER CONSOLE</p>',
        '        <h1><span class="lang-ja">優先レビュー・コンソール</span><span class="lang-en">Priority Review Console</span></h1>',
        '        <p class="production-deck"><span class="lang-ja">優先事項を選ぶと、判断と根拠が同じ対象へ同期します。読み取り専用・オフライン・非実行です。</span><span class="lang-en">Selecting a priority synchronizes its decision and evidence. Read-only, offline, and non-executable.</span></p>',
        "      </div>",
        '      <div class="header-controls">',
        '        <div class="language-switch" role="group" aria-label="表示言語" data-language-controls data-aria-ja="表示言語" data-aria-en="Display language">',
        '          <button type="button" data-language="ja" aria-pressed="true" data-aria-ja="日本語を表示" data-aria-en="Show Japanese">日本語</button>',
        '          <button type="button" data-language="en" aria-pressed="false" data-aria-ja="英語を表示" data-aria-en="Show English">English</button>',
        "        </div>",
        '        <div class="acceptance-state"><span class="lang-ja">視覚受入</span><span class="lang-en">Visual acceptance</span><strong><span class="lang-ja">受入済み</span><span class="lang-en">Accepted</span></strong></div>',
        "      </div>",
        "    </div>",
        '    <dl class="current-state-strip">',
        f'      <div data-landmark="local-observer-health"><dt><span class="lang-ja">ローカル観測基盤</span><span class="lang-en">Local observer health</span></dt><dd><span class="lang-ja">{_e(local_health_ja)}</span><span class="lang-en">{_e(local_health_en)}</span></dd></div>',
        (f'      <div data-landmark="packet-attention"><dt><span class="lang-ja">監修パケット</span><span class="lang-en">Packet attention</span></dt><dd><span class="lang-ja">{_e(packet_attention_ja)}</span><span class="lang-en">{_e(packet_attention_en)}</span></dd></div>' if supervision_packet else ""),
        f'      <div data-landmark="freshness-summary"><dt><span class="lang-ja">ローカルreceipt根拠</span><span class="lang-en">Local receipt evidence</span></dt><dd><span class="lang-ja">{_e(eligible.get("eligible", 0))}/{_e(source_counts.get("total", 0))} 使用可</span><span class="lang-en">{_e(eligible.get("eligible", 0))}/{_e(source_counts.get("total", 0))} eligible</span></dd></div>',
        f'      <div><dt><span class="lang-ja">優先事項</span><span class="lang-en">Priorities</span></dt><dd>{len(priorities)}</dd></div>',
        '      <div><dt><span class="lang-ja">実行権限</span><span class="lang-en">Execution</span></dt><dd><span class="lang-ja">ロック中</span><span class="lang-en">Locked</span></dd></div>',
        "    </dl>",
        f'    <p class="receipt-line"><span class="lang-ja">ローカルreceipt判定時点</span><span class="lang-en">Local receipt assessed at</span> <time datetime="{_e(freshness.get("assessed_at", ""))}">{_e(freshness.get("assessed_at", ""))}</time> · <span class="lang-ja">{_e(authority_copy.get("ja", ""))}</span><span class="lang-en">{_e(authority_copy.get("en", ""))}</span></p>',
        "  </header>",
        '  <nav class="dashboard-nav" aria-label="ダッシュボード区分" data-aria-ja="ダッシュボード区分" data-aria-en="Dashboard sections">',
        '    <a href="#priority-lane"><span class="lang-ja">優先一覧</span><span class="lang-en">Priorities</span></a>',
        '    <a href="#active-decision"><span class="lang-ja">判断</span><span class="lang-en">Decision</span></a>',
        '    <a href="#evidence-inspector"><span class="lang-ja">根拠</span><span class="lang-en">Evidence</span></a>',
        ('    <a href="#project-worksets"><span class="lang-ja">プロジェクト別</span><span class="lang-en">Project worksets</span></a>' if supervision_packet else ""),
        '    <a href="#evidence-appendix"><span class="lang-ja">証拠付録</span><span class="lang-en">Evidence appendix</span></a>',
        "  </nav>",
        '  <main id="main-content" class="production-page" tabindex="-1">',
        f'    <noscript><div class="noscript-notice"><strong><span class="lang-ja">JavaScriptは無効です。</span><span class="lang-en">JavaScript is disabled.</span></strong> <span class="lang-ja">{_e(fallback_ja)}</span><span class="lang-en">{_e(fallback_en)}</span></div></noscript>',
        '    <div class="priority-workspace" data-priority-workspace>',
        _priority_lane(priorities, all_closed=all_closed),
        _active_decision(selected, informational=all_closed),
        _evidence_inspector(selected, receipt, informational=all_closed),
        "    </div>",
        _packet_worksets_section(supervision_packet),
        _production_appendix(model, validation, smoke, action_package, action_summary, output, receipt),
        "  </main>",
        _dashboard_footer(model),
        f'  <script type="application/json" id="priority-model">{_json_for_script(interaction_items)}</script>',
        "  <script>",
        _dashboard_script(),
        "  </script>",
        "</body>",
        "</html>",
        "",
    ]
    return "\n".join(lines)


def _priority_lane(
    priorities: list[dict[str, Any]],
    *,
    all_closed: bool = False,
) -> str:
    buttons: list[str] = []
    for index, item in enumerate(priorities):
        action = _dict(item.get("action"))
        reason = _dict(item.get("reason"))
        state = _dict(item.get("state"))
        owner = _dict(item.get("owner"))
        priority_id = str(item.get("priority_id", ""))
        evidence_id = str(item.get("primary_evidence_id", ""))
        evidence_refs = [value for value in _list(item.get("evidence_refs")) if isinstance(value, dict)]
        evidence = evidence_refs[0] if evidence_refs else {}
        evidence_route = _compact_path(str(evidence.get("source_path", item.get("primary_evidence_path", ""))))
        evidence_classification = _localized_evidence_labels(evidence)["classification"]
        project_key = str(item.get("project_key", "unknown"))
        thread_id = str(item.get("thread_id", "local-observation"))
        lane_id = str(item.get("lane_id", "observer"))
        first_hook = ' data-landmark="priority-first"' if index == 0 else ""
        buttons.append(
            f'<button type="button" class="priority-row state-{_e(state.get("key", "informational"))}" '
            f'data-priority-id="{_e(priority_id)}" data-evidence-id="{_e(evidence_id)}" data-project-key="{_e(project_key)}" data-thread-id="{_e(thread_id)}" data-lane-id="{_e(lane_id)}" role="option" aria-selected="{"true" if index == 0 else "false"}" '
            f'aria-controls="active-decision evidence-inspector" tabindex="{"0" if index == 0 else "-1"}"{first_hook}>'
            f'<span class="priority-rank">#{_e(item.get("rank", index + 1))}</span>'
            '<span class="priority-copy">'
            f'<span class="priority-identity">{_e(project_key)} · {_e(thread_id)} · {_e(lane_id)}</span>'
            f'<strong><span class="lang-ja">{_e(action.get("ja", ""))}</span><span class="lang-en">{_e(action.get("en", ""))}</span></strong>'
            f'<small><span class="lang-ja">{_e(reason.get("ja", ""))}</span><span class="lang-en">{_e(reason.get("en", ""))}</span></small>'
            '<span class="priority-meta">'
            f'<span><span class="lang-ja">{_e(state.get("ja", ""))}</span><span class="lang-en">{_e(state.get("en", ""))}</span></span>'
            f'<span><span class="lang-ja">{_e(owner.get("ja", ""))}</span><span class="lang-en">{_e(owner.get("en", ""))}</span></span>'
            f'<span>{_e(evidence_route)}</span><span><span class="lang-ja">{_e(evidence_classification.get("ja", ""))}</span><span class="lang-en">{_e(evidence_classification.get("en", ""))}</span></span>'
            "</span></span></button>"
        )
    content = "".join(buttons)
    if not priorities and all_closed:
        content = (
            '<div class="priority-empty-state" data-landmark="priority-empty-state" role="status">'
            '<strong><span class="lang-ja">要対応の監修taskはありません</span>'
            '<span class="lang-en">No active supervision tasks</span></strong>'
            '<p><span class="lang-ja">packet内のtaskはすべて完了済みまたは情報提供です。完了根拠は右側で確認できます。</span>'
            '<span class="lang-en">Every packet task is closed or informational. Its evidence remains available alongside this empty state.</span></p>'
            '</div>'
        )
    return (
        '      <section id="priority-lane" class="console-panel priority-lane" data-landmark="priority-lane" aria-labelledby="priority-lane-title">'
        '<header class="console-panel-head"><p>01 / PRIORITY LANE</p>'
        '<h2 id="priority-lane-title"><span class="lang-ja">優先事項</span><span class="lang-en">Priorities</span></h2>'
        '<span class="panel-hint"><span class="lang-ja">確認優先度</span><span class="lang-en">Review attention</span></span></header>'
        f'<div class="priority-list" role="listbox" aria-label="優先レビュー一覧" data-aria-ja="優先レビュー一覧" data-aria-en="Priority review queue">{content}</div>'
        '<p class="queue-note"><span class="lang-ja">global rank は確認・判断の優先度であり、実行順ではありません。異なるprojectの安全な継続は並行できます。</span>'
        '<span class="lang-en">Global rank is attention and review priority, not execution order. Safe continuations in different projects may proceed in parallel.</span></p>'
        "</section>"
    )


def _active_decision(item: dict[str, Any], *, informational: bool = False) -> str:
    action = _dict(item.get("action"))
    reason = _dict(item.get("reason"))
    decision = _dict(item.get("decision"))
    outcome = _dict(item.get("desired_outcome"))
    state = _dict(item.get("state"))
    owner = _dict(item.get("owner"))
    project_key = str(item.get("project_key", "unknown"))
    thread_id = str(item.get("thread_id", "local-observation"))
    lane_id = str(item.get("lane_id", "observer"))
    slice_id = str(item.get("slice_id", "local-review"))
    priority_id = str(item.get("priority_id", ""))
    heading_ja = "完了情報" if informational else "現在の判断"
    heading_en = "Completed Information" if informational else "Active Decision"
    rank_label = "INFO" if informational else f"#{_e(item.get('rank', 1))}"
    panel_label = "02 / COMPLETED INFORMATION" if informational else "02 / ACTIVE DECISION"
    identity_attributes = (
        f'data-item-mode="informational" data-closed-item-id="{_e(priority_id)}"'
        if informational
        else (
            f'data-item-mode="active" data-priority-id="{_e(priority_id)}" '
            f'data-selected-priority-id="{_e(priority_id)}"'
        )
    )
    return (
        f'      <section id="active-decision" class="console-panel active-decision" data-landmark="active-decision" {identity_attributes} aria-labelledby="active-decision-title">'
        f'<header class="console-panel-head"><p>{panel_label}</p>'
        f'<h2 id="active-decision-title"><span class="lang-ja">{_e(heading_ja)}</span><span class="lang-en">{_e(heading_en)}</span></h2>'
        f'<span class="panel-hint" data-field="rank">{rank_label}</span></header>'
        '<div class="decision-body">'
        f'<p class="decision-kicker" data-field="state"><span class="lang-ja">{_e(state.get("ja", ""))}</span><span class="lang-en">{_e(state.get("en", ""))}</span></p>'
        f'<h3 data-field="action"><span class="lang-ja">{_e(action.get("ja", ""))}</span><span class="lang-en">{_e(action.get("en", ""))}</span></h3>'
        f'<p class="decision-reason" data-field="reason"><span class="lang-ja">{_e(reason.get("ja", ""))}</span><span class="lang-en">{_e(reason.get("en", ""))}</span></p>'
        '<dl class="decision-grid">'
        '<div><dt><span class="lang-ja">project / thread</span><span class="lang-en">Project / thread</span></dt>'
        f'<dd data-field="project-identity">{_e(project_key)} / {_e(thread_id)}</dd></div>'
        '<div><dt><span class="lang-ja">lane / slice</span><span class="lang-en">Lane / slice</span></dt>'
        f'<dd data-field="lane-identity">{_e(lane_id)} / {_e(slice_id)}</dd></div>'
        '<div><dt><span class="lang-ja">判断すること</span><span class="lang-en">Decision</span></dt>'
        f'<dd data-field="decision"><span class="lang-ja">{_e(decision.get("ja", ""))}</span><span class="lang-en">{_e(decision.get("en", ""))}</span></dd></div>'
        '<div><dt><span class="lang-ja">望ましい結果</span><span class="lang-en">Desired outcome</span></dt>'
        f'<dd data-field="outcome"><span class="lang-ja">{_e(outcome.get("ja", ""))}</span><span class="lang-en">{_e(outcome.get("en", ""))}</span></dd></div>'
        '<div><dt><span class="lang-ja">所有者</span><span class="lang-en">Owner</span></dt>'
        f'<dd data-field="owner"><span class="lang-ja">{_e(owner.get("ja", ""))}</span><span class="lang-en">{_e(owner.get("en", ""))}</span></dd></div>'
        '<div><dt><span class="lang-ja">次の操作</span><span class="lang-en">Next operation</span></dt><dd><span class="lang-ja">根拠を確認して判断を記録する（自動実行なし）</span><span class="lang-en">Review evidence and record a decision (no execution)</span></dd></div>'
        "</dl></div></section>"
    )


def _evidence_inspector(
    item: dict[str, Any],
    receipt: dict[str, Any],
    *,
    informational: bool = False,
) -> str:
    refs = [value for value in _list(item.get("evidence_refs")) if isinstance(value, dict)]
    evidence = refs[0] if refs else {}
    priority_id = str(item.get("priority_id", ""))
    path = str(evidence.get("source_path", item.get("primary_evidence_path", "")))
    evidence_id = str(evidence.get("source_id", ""))
    evidence_population = str(evidence.get("evidence_population", "local_observer_receipt"))
    population_ja = "manifest拘束report" if evidence_population == "packet_report" else "ローカル観測receipt"
    population_en = "Manifest-bound packet report" if evidence_population == "packet_report" else "Local observer receipt"
    identity_attributes = (
        f'data-item-mode="informational" data-closed-item-id="{_e(priority_id)}"'
        if informational
        else (
            f'data-item-mode="active" data-priority-id="{_e(priority_id)}" '
            f'data-selected-priority-id="{_e(priority_id)}"'
        )
    )
    reason_codes = ", ".join(str(value) for value in _list(evidence.get("reason_codes"))) or "none"
    source_label = _human_source_label(evidence)
    evidence_labels = _localized_evidence_labels(evidence)
    review_action_ids = ", ".join(
        str(value.get("action_id", ""))
        for value in _list(item.get("review_action_refs"))
        if isinstance(value, dict) and value.get("action_id")
    ) or "none"
    evidence_binding_line = (
        '<p class="receipt-id" data-field="evidence-binding">manifest-bound packet evidence</p>'
        if evidence_population == "packet_report"
        else f'<p class="receipt-id" data-field="evidence-binding">receipt <code>{_e(receipt.get("capture_id", ""))}</code></p>'
    )
    return (
        f'      <aside id="evidence-inspector" class="console-panel evidence-inspector" data-landmark="evidence-inspector" {identity_attributes} data-evidence-id="{_e(evidence_id)}" aria-labelledby="evidence-inspector-title">'
        '<header class="console-panel-head"><p>03 / EVIDENCE INSPECTOR</p>'
        '<h2 id="evidence-inspector-title"><span class="lang-ja">根拠</span><span class="lang-en">Evidence</span></h2>'
        f'<span class="panel-hint"><span class="lang-ja">{_e(population_ja)}</span><span class="lang-en">{_e(population_en)}</span></span></header>'
        '<div class="evidence-body">'
        f'<div class="evidence-status" data-field="freshness" data-landmark="freshness-status"><span class="lang-ja">{_e(evidence_labels["classification"].get("ja", ""))}</span><span class="lang-en">{_e(evidence_labels["classification"].get("en", ""))}</span></div>'
        '<dl class="evidence-grid">'
        '<div><dt><span class="lang-ja">根拠母集団</span><span class="lang-en">Evidence population</span></dt>'
        f'<dd data-field="evidence-population">{_e(evidence_population)}</dd></div>'
        '<div><dt><span class="lang-ja">ソース</span><span class="lang-en">Source</span></dt>'
        f'<dd data-field="source-label"><span class="lang-ja">{_e(source_label.get("ja", ""))}</span><span class="lang-en">{_e(source_label.get("en", ""))}</span><small data-field="source-route">{_e(_compact_path(path))}</small></dd></div>'
        '<div><dt><span class="lang-ja">現状根拠として使用可</span><span class="lang-en">Current-claim eligible</span></dt>'
        f'<dd data-field="eligible"><span class="lang-ja">{_e(evidence_labels["eligibility"].get("ja", ""))}</span><span class="lang-en">{_e(evidence_labels["eligibility"].get("en", ""))}</span></dd></div>'
        '<div><dt><span class="lang-ja">時間状態</span><span class="lang-en">Temporal state</span></dt>'
        f'<dd data-field="temporal"><span class="lang-ja">{_e(evidence_labels["temporal"].get("ja", ""))}</span><span class="lang-en">{_e(evidence_labels["temporal"].get("en", ""))}</span></dd></div>'
        '<div><dt><span class="lang-ja">改訂整合性</span><span class="lang-en">Revision binding</span></dt>'
        f'<dd data-field="revision"><span class="lang-ja">{_e(evidence_labels["revision"].get("ja", ""))}</span><span class="lang-en">{_e(evidence_labels["revision"].get("en", ""))}</span></dd></div>'
        '<div><dt><span class="lang-ja">判定時点</span><span class="lang-en">Assessed at</span></dt>'
        f'<dd data-field="assessed">{_e(evidence.get("assessed_at", receipt.get("assessed_at", "")))}</dd></div>'
        '<div><dt><span class="lang-ja">有効期限</span><span class="lang-en">Fresh through</span></dt>'
        f'<dd data-field="fresh-through">{_e(evidence.get("fresh_through") or "n/a")}</dd></div>'
        "</dl>"
        '<details class="provenance-details" data-landmark="provenance"><summary><span class="lang-ja">由来の詳細</span><span class="lang-en">Provenance details</span></summary>'
        '<dl class="provenance-grid">'
        f'<div><dt>source_id</dt><dd data-field="source-id">{_e(evidence.get("source_id", ""))}</dd></div>'
        f'<div><dt>attention_class</dt><dd data-field="attention-class">{_e(item.get("attention_class", "local_evidence_priority"))}</dd></div>'
        f'<div><dt>full_path</dt><dd class="full-path" data-field="source-path">{_e(path)}</dd></div>'
        f'<div><dt>authority</dt><dd data-field="authority">{_e(evidence.get("authority_classification", "unknown"))}</dd></div>'
        f'<div><dt>reason_codes</dt><dd data-field="reason-codes">{_e(reason_codes)}</dd></div>'
        f'<div><dt>review_actions</dt><dd data-field="review-actions">{_e(review_action_ids)}</dd></div>'
        f'<div><dt>content_sha256</dt><dd class="hash-value" data-field="content-sha">{_e(evidence.get("content_sha256") or "n/a")}</dd></div>'
        "</dl></details>"
        + evidence_binding_line
        + "</div></aside>"
    )


def _packet_worksets_section(packet: dict[str, Any]) -> str:
    if not packet:
        return ""
    cards: list[str] = []
    for raw_workset in _list(packet.get("project_worksets")):
        workset = _dict(raw_workset)
        project_key = str(workset.get("project_key", "unknown"))
        active_ids = ", ".join(str(value) for value in _list(workset.get("active_task_ids"))) or "none"
        closed_ids = ", ".join(
            str(value) for value in _list(workset.get("closed_or_informational_task_ids"))
        ) or "none"
        ranks = ", ".join(
            f"#{_e(_dict(value).get('global_rank'))} {_e(_dict(value).get('task_id'))}"
            for value in _list(workset.get("global_rank_references"))
        ) or "none"
        cards.append(
            '<article class="workset-card">'
            f'<h3>{_e(project_key)}</h3>'
            '<dl>'
            f'<div><dt><span class="lang-ja">project内の先頭task</span><span class="lang-en">Project-local first task</span></dt><dd><code>{_e(workset.get("project_local_first_task_id") or "none")}</code></dd></div>'
            f'<div><dt><span class="lang-ja">global rank参照</span><span class="lang-en">Global rank references</span></dt><dd>{ranks}</dd></div>'
            f'<div><dt><span class="lang-ja">active task</span><span class="lang-en">Active tasks</span></dt><dd>{_e(active_ids)}</dd></div>'
            f'<div><dt><span class="lang-ja">user / supervisor gate</span><span class="lang-en">User / supervisor gate</span></dt><dd>{_e(workset.get("user_or_supervisor_gate", "none"))}</dd></div>'
            f'<div><dt><span class="lang-ja">安全な継続</span><span class="lang-en">Safe continuation</span></dt><dd>{_e(workset.get("safe_continuation", "none"))}</dd></div>'
            f'<div><dt><span class="lang-ja">closed / informational</span><span class="lang-en">Closed / informational</span></dt><dd>{_e(closed_ids)}</dd></div>'
            '</dl></article>'
        )
    return (
        '    <details id="project-worksets" class="project-worksets">'
        '<summary><span><span class="lang-ja">project別 workset</span><span class="lang-en">Project worksets</span></span>'
        '<small><span class="lang-ja">同じtask IDをproject単位で再投影します。</span><span class="lang-en">The same task IDs are reprojected by project; ranks are not recalculated.</span></small></summary>'
        f'<div class="workset-grid">{"".join(cards)}</div></details>'
    )


def _production_appendix(
    model: dict[str, Any],
    validation: dict[str, Any],
    smoke: dict[str, Any],
    action_package: dict[str, Any],
    action_summary: dict[str, Any],
    output: dict[str, Any],
    receipt: dict[str, Any],
) -> str:
    return (
        '    <details id="evidence-appendix" class="evidence-appendix">'
        '<summary><span><span class="lang-ja">証拠付録を開く</span><span class="lang-en">Open evidence appendix</span></span>'
        '<small><span class="lang-ja">密な表・確認項目・ロック中の領域は主画面の下位です。</span><span class="lang-en">Dense tables, review actions, and locked lanes remain subordinate.</span></small></summary>'
        '<div class="appendix-content">'
        '<section aria-labelledby="receipt-ledger-title"><h2 id="receipt-ledger-title"><span class="lang-ja">鮮度receipt台帳</span><span class="lang-en">Freshness receipt ledger</span></h2>'
        f'{_receipt_sources_table(_list(receipt.get("sources")))}</section>'
        '<section aria-labelledby="review-actions-title"><h2 id="review-actions-title"><span class="lang-ja">非実行の確認項目</span><span class="lang-en">Non-executable review actions</span></h2>'
        f'{_review_action_summary_panel(action_summary, action_package)}{_review_action_cards(_list(model.get("review_actions")))}</section>'
        '<section aria-labelledby="validation-title"><h2 id="validation-title"><span class="lang-ja">検証pack</span><span class="lang-en">Validation Pack</span></h2>'
        f'{_summary_line(_dict(validation.get("summary")))}{_checks_table(_list(validation.get("checks")))}</section>'
        '<section aria-labelledby="smoke-title"><h2 id="smoke-title"><span class="lang-ja">横断project観測</span><span class="lang-en">Cross-Project Smoke</span></h2>'
        f'{_summary_line(_dict(smoke.get("summary")))}{_projects_table(_list(smoke.get("projects")))}</section>'
        '<section aria-labelledby="locked-title"><h2 id="locked-title"><span class="lang-ja">ロック中lane</span><span class="lang-en">Locked lanes</span></h2>'
        f'{_locked_lane_grid(_list(model.get("locked_lanes")))}</section>'
        '<section aria-labelledby="sources-title"><h2 id="sources-title"><span class="lang-ja">ソースとアクセス</span><span class="lang-en">Sources and access</span></h2>'
        f'{_sources_table(_list(model.get("sources")))}{_access_panel(output)}{_action_package_access_panel(action_package)}</section>'
        "</div></details>"
    )


def _receipt_sources_table(sources: list[Any]) -> str:
    rows: list[str] = []
    for item in sources:
        source = _dict(item)
        cells = [
            source.get("project_id", ""),
            source.get("source_id", ""),
            source.get("required", False),
            source.get("freshness_state", "unknown"),
            source.get("revision_binding_state", "unknown"),
            source.get("current_state_claim_eligible", False),
            _compact_path(str(source.get("source_path", ""))),
        ]
        rows.append("<tr>" + "".join(f"<td>{_e(value)}</td>" for value in cells) + "</tr>")
    return _table(
        (
            {"ja": "プロジェクト", "en": "Project"},
            {"ja": "ソース", "en": "Source"},
            {"ja": "必須", "en": "Required"},
            {"ja": "鮮度", "en": "Freshness"},
            {"ja": "改訂整合性", "en": "Revision"},
            {"ja": "使用可", "en": "Eligible"},
            {"ja": "経路", "en": "Path"},
        ),
        rows,
        empty_text={"ja": "鮮度証拠ソースはありません。", "en": "No evidence freshness sources."},
        caption={"ja": "鮮度receiptの証拠ソース", "en": "Evidence freshness receipt sources"},
    )


def _compact_path(value: str) -> str:
    normalized = value.replace("\\", "/").rstrip("/")
    if not normalized:
        return "n/a"
    if normalized.startswith("git-observation:"):
        return normalized
    return normalized.rsplit("/", 1)[-1]


def _localized_evidence_labels(source: dict[str, Any]) -> dict[str, dict[str, str]]:
    freshness_state = str(source.get("freshness_state", "unknown"))
    temporal_state = str(source.get("temporal_state", "unknown"))
    revision_state = str(source.get("revision_binding_state", "unknown"))
    eligible = source.get("current_state_claim_eligible") is True
    freshness = {
        "fresh": {"ja": "鮮度内", "en": "Fresh"},
        "stale": {"ja": "期限超過", "en": "Stale"},
        "unknown": {"ja": "鮮度不明", "en": "Freshness unknown"},
        "not_applicable": {"ja": "対象外", "en": "Not applicable"},
    }.get(freshness_state, {"ja": "鮮度不明", "en": freshness_state})
    temporal = {
        "fresh": {"ja": "鮮度内", "en": "Fresh"},
        "stale": {"ja": "期限超過", "en": "Stale"},
        "unknown": {"ja": "不明", "en": "Unknown"},
        "not_applicable": {"ja": "対象外", "en": "Not applicable"},
    }.get(temporal_state, {"ja": "不明", "en": temporal_state})
    revision = {
        "match": {"ja": "一致", "en": "Match"},
        "mismatch": {"ja": "不一致", "en": "Mismatch"},
        "unknown": {"ja": "不明", "en": "Unknown"},
        "not_applicable": {"ja": "対象外", "en": "Not applicable"},
    }.get(revision_state, {"ja": "不明", "en": revision_state})
    eligibility = (
        {"ja": "使用可", "en": "Eligible"}
        if eligible
        else {"ja": "使用不可", "en": "Ineligible"}
    )
    return {
        "classification": {
            "ja": f"{freshness['ja']}・現状根拠{eligibility['ja']}",
            "en": f"{freshness['en']} · claim-{eligibility['en'].lower()}",
        },
        "eligibility": eligibility,
        "temporal": temporal,
        "revision": revision,
    }


def _authority_copy(authority: dict[str, Any]) -> dict[str, str]:
    if authority.get("tracked_example") is True:
        return {
            "ja": "追跡済みの決定論的サンプル。継続的な現状根拠ではありません。",
            "en": "Tracked deterministic example; never authoritative for live state.",
        }
    return {
        "ja": "ローカル読み取り専用の取得結果。記録した判定時点と有効期間内でのみ使用できます。",
        "en": "Local read-only capture; valid only for the recorded assessment and policy window.",
    }


def _human_source_label(source: dict[str, Any]) -> dict[str, str]:
    source_id = str(source.get("source_id", ""))
    known = {
        "validation-pack-sample": {"ja": "検証pack結果", "en": "Validation pack result"},
        "cross-project-smoke-sample": {"ja": "横断観測結果", "en": "Cross-project observation"},
        "status-snapshot-sample": {"ja": "状態snapshot", "en": "Status snapshot"},
        "intent-comparison-manifest-v2": {"ja": "比較履歴", "en": "Comparison history"},
    }
    if source_id in known:
        return dict(known[source_id])
    if source_id.endswith(".live_status_observation"):
        project = source_id.split(".", 1)[0]
        return {
            "ja": f"{project} 読み取り専用観測",
            "en": f"{project} read-only observation",
        }
    return {"ja": "証拠ソース", "en": "Evidence source"}


def _json_for_script(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).replace("<", "\\u003c")


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
    parser.add_argument(
        "--freshness-receipt",
        default=DEFAULT_FRESHNESS_RECEIPT_PATH,
        help="Validated evidence_freshness_receipt.v1 JSON path.",
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
    parser.add_argument(
        "--priority-readback",
        default=DEFAULT_PRIORITY_READBACK_PATH,
        help="Output deterministic priority/readback JSON path.",
    )
    parser.add_argument(
        "--supervision-packet",
        help=(
            "Optional cross_project_supervision_packet.v1 JSON path. "
            "When omitted, preserve the existing evidence-derived priority path."
        ),
    )
    parser.add_argument(
        "--supervision-manifest",
        help=(
            "Optional task_report_manifest.v1 path. When paired with --supervision-packet, "
            "the packet is rebuilt from its bound report sources before projection."
        ),
    )
    parser.add_argument(
        "--generated-at",
        help="Optional deterministic dashboard generation timestamp; defaults to receipt assessed_at.",
    )
    parser.add_argument(
        "--skip-freshness-hash-verification",
        action="store_true",
        help="Validate the receipt schema but skip source hash recomputation (test fixtures only).",
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
            freshness_receipt_path=args.freshness_receipt,
            output_path=args.output,
            review_actions_json_path=args.review_actions_json,
            review_actions_md_path=args.review_actions_md,
            priority_readback_path=args.priority_readback,
            supervision_packet_path=args.supervision_packet,
            supervision_manifest_path=args.supervision_manifest,
            verify_freshness_hashes=not args.skip_freshness_hash_verification,
            generated_at=args.generated_at,
        )
        package = review_action_package(model)
        priority_package = priority_readback(model)
        write_dashboard(model, Path(args.repo_root) / args.output)
        write_review_actions_json(package, Path(args.repo_root) / args.review_actions_json, pretty=True)
        write_review_actions_markdown(package, Path(args.repo_root) / args.review_actions_md)
        write_priority_readback(
            priority_package,
            Path(args.repo_root) / args.priority_readback,
            pretty=True,
        )
    except DashboardError as exc:
        print(f"dashboard error: {exc}", file=sys.stderr)
        return 2

    print(_display_path(Path(args.repo_root), args.output))
    print(_display_path(Path(args.repo_root), args.review_actions_json))
    print(_display_path(Path(args.repo_root), args.review_actions_md))
    print(_display_path(Path(args.repo_root), args.priority_readback))
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
    report = _dict(model.get("frontpage_report") or model.get("latest_brief"))
    headline = str(report.get("headline") or "Review the current local state.")
    annotation = str(report.get("annotation") or "Use the linked evidence below when a review signal needs source detail.")
    primary = _dict(report.get("primary_action"))
    primary_href = str(primary.get("href") or "#review-map")
    primary_label = str(primary.get("label") or "Open review map")
    secondary = _dict(report.get("secondary_link"))
    secondary_href = str(secondary.get("href") or "#detail-evidence-freshness")
    secondary_label = str(secondary.get("label") or "Check evidence freshness")
    aside = _dict(report.get("aside"))
    aside_text = str(
        aside.get("text")
        or "Execution expansion stays locked; use this as a local review surface only."
    )
    return (
        '<header class="top-strip report-first-frontpage" data-dashboard-theme="dark">'
        '<section id="current-status-report" class="frontpage-report" aria-label="Current Status Report">'
        '<div class="report-front-grid">'
        '<div class="report-main">'
        '<p class="eyebrow">Current Status / Supervision Report</p>'
        f"<h1>{_e(project.get('name', 'DevCockpitCore'))}</h1>"
        f'<p class="report-headline">{_e(headline)}</p>'
        f'<p class="report-interpretation">{_e(annotation)}</p>'
        "</div>"
        '<div class="report-next">'
        "<span>Open first</span>"
        f'<a class="report-primary-action" href="{_e(primary_href)}">{_e(primary_label)}</a>'
        f'<a class="report-secondary-link" href="{_e(secondary_href)}">{_e(secondary_label)}</a>'
        "</div>"
        "</div>"
        f"{_report_status_strip(health, report, freshness, output)}"
        '<p class="report-meta">'
        f"Generated {_e(generated_at)} from local evidence. "
        f"Access: {_e(_access_label(output))}. "
        f"{_e(str(blocker_count))} blocker(s), {_e(str(warning_count))} warning signal(s). "
        f"Not urgent: {_e(aside_text)}"
        "</p>"
        "</section>"
        "</header>"
    )


def _dashboard_nav() -> str:
    links = (
        ("Report", "current-status-report"),
        ("Review Map", "review-map"),
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


def _report_status_strip(
    health: dict[str, Any],
    report: dict[str, Any],
    freshness: dict[str, Any],
    output: dict[str, Any],
) -> str:
    blockers = len(_list(health.get("blockers")))
    runway = [_dict(item) for item in _list(report.get("runway"))]
    warning = runway[1] if len(runway) > 1 else {}
    proof = runway[2] if len(runway) > 2 else {}
    indicators = [
        {
            "label": "Stop gate",
            "value": f"{blockers} blocker(s)",
            "tone": "red" if blockers else "green",
        },
        {
            "label": "Attention",
            "value": str(warning.get("value") or "No warning bucket leads"),
            "tone": str(warning.get("tone") or "neutral"),
        },
        {
            "label": "Evidence",
            "value": str(proof.get("value") or freshness.get("loaded_count", "0/0")),
            "tone": str(proof.get("tone") or "neutral"),
        },
        {
            "label": "Access",
            "value": _access_label(output),
            "tone": "neutral",
        },
    ]
    items = []
    for item in indicators:
        items.append(
            f'<div class="{_tone_class(item.get("tone"))}">'
            f"<dt>{_e(item.get('label', 'Signal'))}</dt>"
            f"<dd>{_e(item.get('value', 'Review'))}</dd>"
            "</div>"
        )
    return f'<dl class="report-status-strip" aria-label="Current report indicators">{"".join(items)}</dl>'


def _review_map(meters: list[Any]) -> str:
    if not meters:
        return '<nav class="review-map-list" aria-label="Compact review map"><p>No review map items were generated.</p></nav>'
    links = []
    for meter in meters:
        item = _dict(meter)
        href = str(item.get("detail_href") or "#linked-detail-map")
        tone = _review_map_tone(item.get("tone"))
        links.append(
            f'<a class="review-map-item {tone}" data-review-map-item href="{_e(href)}">'
            f"<span>{_e(item.get('title', 'Review'))}</span>"
            f"<strong>{_e(item.get('primary_value', 'n/a'))}</strong>"
            f"<small>{_e(_short_text(str(item.get('summary', 'Open detail.')), 82))}</small>"
            "</a>"
        )
    return f'<nav class="review-map-list" aria-label="Compact review map">{"".join(links)}</nav>'


def _review_map_tone(value: Any) -> str:
    normalized = str(value or "neutral").lower()
    mapping = {
        "pass": "tone-green",
        "green": "tone-green",
        "warn": "tone-yellow",
        "warning": "tone-yellow",
        "yellow": "tone-yellow",
        "fail": "tone-red",
        "red": "tone-red",
        "neutral": "tone-neutral",
    }
    return mapping.get(normalized, "tone-neutral")


def _dashboard_footer(model: dict[str, Any]) -> str:
    return (
        '<footer class="dashboard-footer">'
        '<p><span class="lang-ja">Workerが生成したローカル確認成果物です。生成時点</span>'
        '<span class="lang-en">Worker-generated local review artifact. Generated at</span> '
        f"{_e(model.get('generated_at', 'unknown'))}. "
        '<span class="lang-ja">server、telemetry、task runner、repository writebackは含みません。</span>'
        '<span class="lang-en">No server, telemetry, task runner, or repository writeback is included.</span></p>'
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
        '<a class="back-link" href="#review-map">Back to review map</a>'
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
        '<h3><span class="lang-ja">確認専用action package</span><span class="lang-en">Review-only Action Package</span></h3>'
        '<p><strong><span class="lang-ja">非実行:</span><span class="lang-en">Non-executable:</span></strong> '
        '<span class="lang-ja">全項目を</span><span class="lang-en">every generated action is marked</span> <code>executable: false</code>.</p>'
        f'<p><strong><span class="lang-ja">合計:</span><span class="lang-en">Total:</span></strong> {_e(summary.get("total", 0))} '
        f'<strong><span class="lang-ja">停止:</span><span class="lang-en">Blockers:</span></strong> {_e(summary.get("blocker", 0))} '
        f'<strong><span class="lang-ja">警告:</span><span class="lang-en">Warnings:</span></strong> {_e(summary.get("warning", 0))} '
        f'<strong><span class="lang-ja">参考:</span><span class="lang-en">Info:</span></strong> {_e(summary.get("info", 0))}</p>'
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
        return '<div class="action-review-grid"><article class="review-action-card"><p><span class="lang-ja">確認項目は生成されませんでした。</span><span class="lang-en">No review actions generated.</span></p></article></div>'
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
        gate_note_ja = "gateでロック" if item.get("blocked_by_gate") else "確認専用"
        gate_note_en = "Locked by gate" if item.get("blocked_by_gate") else "Review-only"
        cards.append(
            f'<article id="{_e(action_id)}" class="review-action-card" data-review-action data-severity="{_e(severity)}" data-search="{_e(search_text)}">'
            f"<div class=\"project-card-head\"><h3>{_e(item.get('title', 'Review action'))}</h3>"
            f"<span class=\"pill {_result_class(severity)}\">{_e(severity)}</span></div>"
            f"<p><strong>ID:</strong> <code>{_e(item.get('action_id', 'unknown'))}</code></p>"
            f'<p><strong><span class="lang-ja">ソース:</span><span class="lang-en">Source:</span></strong> {_e(item.get("source_type", "unknown"))}'
            f"{' / ' + _e(item.get('project_key')) if item.get('project_key') else ''}</p>"
            f'<p><strong><span class="lang-ja">理由:</span><span class="lang-en">Reason:</span></strong> {_e(item.get("reason", "No reason provided."))}</p>'
            f'<p><strong><span class="lang-ja">推奨確認:</span><span class="lang-en">Suggested review:</span></strong> {_e(item.get("suggested_review", "Manual review."))}</p>'
            f'<p><strong><span class="lang-ja">根拠:</span><span class="lang-en">Evidence:</span></strong> <code>{_e(item.get("evidence_path", "unknown"))}</code></p>'
            f'<p><strong><span class="lang-ja">所有者:</span><span class="lang-en">Owner hint:</span></strong> {_e(item.get("owner_hint", "operator"))}</p>'
            f'<p><strong><span class="lang-ja">{_e(gate_note_ja)}:</span><span class="lang-en">{_e(gate_note_en)}:</span></strong> executable = {_e(str(item.get("executable", False)).lower())}; surface = {_e(item.get("safe_next_surface", "local_review"))}</p>'
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
    translations = {
        "Arbitrary command runner": "任意command runner",
        "General execution loop": "汎用実行loop",
        "Scheduler or background daemon": "schedulerまたはbackground daemon",
        "Web server or remote dashboard": "web serverまたはremote dashboard",
        "Database or credential handling": "databaseまたはcredential処理",
        "External service notifications": "外部service通知",
        "Target repository writeback": "対象repositoryへのwriteback",
        "C5/C6 capability expansion": "C5/C6 capability拡張",
        "Public publication or production-ready claims": "公開publicationまたはproduction-ready claim",
    }
    cards = []
    for lane in lanes:
        lane_text = str(lane)
        cards.append(
            '<article class="locked-card">'
            '<span>LOCKED</span>'
            f'<strong><span class="lang-ja">{_e(translations.get(lane_text, lane_text))}</span><span class="lang-en">{_e(lane_text)}</span></strong>'
            '<p><span class="lang-ja">この静的dashboard sliceには含みません。</span><span class="lang-en">Not part of this static dashboard slice.</span></p>'
            "</article>"
        )
    return f'<div class="locked-grid">{"".join(cards)}</div>'


def _summary_line(summary: dict[str, Any]) -> str:
    return (
        '<div class="panel">'
        f'<h3><span class="lang-ja">概要</span><span class="lang-en">Summary</span></h3><p><span class="pill {_result_class(summary.get("result"))}">'
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
        (
            {"ja": "検証", "en": "Check"},
            {"ja": "結果", "en": "Result"},
            {"ja": "重要度", "en": "Severity"},
            {"ja": "進捗", "en": "Bar"},
            {"ja": "詳細", "en": "Detail"},
        ),
        rows,
        empty_text={"ja": "利用できる検証項目はありません。", "en": "No validation checks were available."},
        caption={
            "ja": "検証packの項目、結果、重要度、証拠進捗、詳細。",
            "en": "Validation pack checks, result severity, evidence bar, and detail.",
        },
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
        (
            {"ja": "プロジェクト", "en": "Project"},
            {"ja": "結果", "en": "Result"},
            {"ja": "repository", "en": "Repo"},
            {"ja": "branch / HEAD", "en": "Branch / HEAD"},
            {"ja": "進捗", "en": "Bar"},
            {"ja": "警告", "en": "Warnings"},
        ),
        rows,
        empty_text={"ja": "利用できる横断project行はありません。", "en": "No cross-project rows were available."},
        caption={
            "ja": "横断project観測の結果、repository、branch、警告概要。",
            "en": "Cross-project smoke rows with result, repository hint, branch, and warning summary.",
        },
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
        (
            {"ja": "ソース", "en": "Source"},
            {"ja": "repository相対経路", "en": "Repo-relative path"},
            {"ja": "状態", "en": "State"},
            {"ja": "schema", "en": "Schema"},
            {"ja": "生成時点", "en": "Generated at"},
        ),
        rows,
        empty_text={"ja": "ソースはありません。", "en": "No sources."},
        caption={
            "ja": "ローカルdashboardが使用した証拠ソース。",
            "en": "Source evidence files used by the local dashboard.",
        },
    )


def _access_panel(output: dict[str, Any]) -> str:
    return (
        '<div class="panel access-panel">'
        '<h3><span class="lang-ja">開く / access</span><span class="lang-en">Open / Access</span></h3>'
        f'<p><strong><span class="lang-ja">repository相対成果物:</span><span class="lang-en">Repo-relative artifact:</span></strong> <code>{_e(output.get("repo_relative_path", "unknown"))}</code></p>'
        f'<p><strong><span class="lang-ja">access mode:</span><span class="lang-en">Access mode:</span></strong> {_e(output.get("access_mode", "unknown"))}</p>'
        f'<p><strong><span class="lang-ja">access state:</span><span class="lang-en">Access state:</span></strong> {_e(output.get("access_state", "unknown"))}</p>'
        f'<p><strong><span class="lang-ja">証拠level:</span><span class="lang-en">Evidence level:</span></strong> {_e(output.get("access_evidence_level", "unknown"))}</p>'
        f"<p><strong>PowerShell:</strong> <code>{_e(output.get('open_command', 'unknown'))}</code></p>"
        "</div>"
    )


def _action_package_access_panel(package: dict[str, Any]) -> str:
    return (
        '<div class="panel access-panel">'
        '<h3><span class="lang-ja">確認action package</span><span class="lang-en">Review Action Package</span></h3>'
        f"<p><strong>Schema:</strong> {_e(package.get('schema_version', 'unknown'))}</p>"
        f"<p><strong>JSON:</strong> <code>{_e(package.get('json_path', 'unknown'))}</code></p>"
        f"<p><strong>Markdown:</strong> <code>{_e(package.get('markdown_path', 'unknown'))}</code></p>"
        f'<p><strong><span class="lang-ja">access state:</span><span class="lang-en">Access state:</span></strong> {_e(package.get("access_state", "unknown"))}</p>'
        f'<p><strong><span class="lang-ja">証拠level:</span><span class="lang-en">Evidence level:</span></strong> {_e(package.get("access_evidence_level", "unknown"))}</p>'
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
    headers: tuple[str | dict[str, str], ...],
    rows: list[str],
    *,
    empty_text: str | dict[str, str],
    caption: str | dict[str, str] | None = None,
) -> str:
    if not rows:
        if isinstance(empty_text, dict):
            return (
                '<div class="panel"><p>'
                f'<span class="lang-ja">{_e(empty_text.get("ja", ""))}</span>'
                f'<span class="lang-en">{_e(empty_text.get("en", ""))}</span>'
                "</p></div>"
            )
        return f'<div class="panel"><p>{_e(empty_text)}</p></div>'
    header_html = "".join(f"<th>{_localized_html(header)}</th>" for header in headers)
    caption_html = f"<caption>{_localized_html(caption)}</caption>" if caption else ""
    return (
        '<div class="table-wrap" data-overflow-allowed><table>'
        f"{caption_html}"
        "<thead><tr>"
        f"{header_html}"
        "</tr></thead><tbody>"
        f"{''.join(rows)}"
        "</tbody></table></div>"
    )


def _localized_html(value: str | dict[str, str]) -> str:
    if isinstance(value, dict):
        return (
            f'<span class="lang-ja">{_e(value.get("ja", ""))}</span>'
            f'<span class="lang-en">{_e(value.get("en", ""))}</span>'
        )
    return _e(value)


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


def _receipt_freshness_projection(receipt: dict[str, Any]) -> dict[str, Any]:
    """Project the landed receipt contract without re-evaluating freshness."""

    summary = _dict(receipt.get("summary"))
    authority = _dict(receipt.get("authority"))
    source_counts = _dict(summary.get("source_counts"))
    eligibility = _dict(summary.get("current_state_claim_eligible"))
    return {
        "schema_version": str(receipt.get("schema_version", "")),
        "capture_id": str(receipt.get("capture_id", "")),
        "assessed_at": str(receipt.get("assessed_at", "")),
        "observation_mode": str(receipt.get("observation_mode", "")),
        "authority": dict(authority),
        "source_counts": dict(source_counts),
        "current_state_claim_eligible": dict(eligibility),
        "required_missing": _int(summary.get("required_missing")),
        "required_invalid": _int(summary.get("required_invalid")),
        "statement": str(authority.get("statement", "")),
        "point_in_time": authority.get("point_in_time") is True,
        "live": authority.get("live") is True,
    }


def _packet_priority_items(packet: dict[str, Any]) -> list[dict[str, Any]]:
    """Project manifest-bound report tasks into the accepted Priority Console shape."""

    return _packet_task_items(packet, "global_attention_queue")


def _packet_informational_items(packet: dict[str, Any]) -> list[dict[str, Any]]:
    """Project closed packet tasks for evidence browsing without making priorities."""

    return _packet_task_items(packet, "closed_or_informational")


def _packet_task_items(packet: dict[str, Any], collection: str) -> list[dict[str, Any]]:

    first_by_project = {
        str(_dict(workset).get("project_key", "")): str(
            _dict(workset).get("project_local_first_task_id", "")
        )
        for workset in _list(packet.get("project_worksets"))
    }
    state_labels = {
        "true_stop_or_required_failure": {"key": "blocked", "ja": "停止", "en": "Blocked"},
        "user_authorization_or_material_decision": {"key": "decision", "ja": "判断待ち", "en": "Decision required"},
        "awaiting_supervisor_acceptance": {"key": "review", "ja": "監修確認", "en": "Supervisor review"},
        "active_safe_continuation": {"key": "continue", "ja": "安全に継続", "en": "Safe continuation"},
        "unknown_requiring_review": {"key": "review", "ja": "要確認", "en": "Review required"},
        "closed_or_informational": {"key": "informational", "ja": "完了情報", "en": "Closed / informational"},
    }
    items: list[dict[str, Any]] = []
    for raw_task in _list(packet.get(collection)):
        task = _dict(raw_task)
        project_key = str(task.get("project_key", "unknown"))
        task_id = str(task.get("task_id", ""))
        attention_class = str(task.get("attention_class", "unknown_requiring_review"))
        next_state = _dict(task.get("next_state"))
        next_text = str(
            next_state.get("recommended_slice")
            or (
                "user work: " + str(next_state.get("user_work"))
                if next_state.get("user_work") not in {None, "none"}
                else next_state.get("agent_work") or "review classification"
            )
        )
        source_path = str(task.get("source_report_path", ""))
        source_hash = str(task.get("source_report_sha256", ""))
        evidence_class = str(task.get("evidence_class", ""))
        evidence = {
            "source_id": f"{task_id}.source_report",
            "source_path": source_path,
            "freshness_state": "not_applicable",
            "temporal_state": "not_applicable",
            "revision_binding_state": "match",
            "current_state_claim_eligible": False,
            "assessed_at": str(packet.get("generated_at", "")),
            "fresh_through": None,
            "content_sha256": source_hash,
            "authority_classification": (
                "manifest_bound_authentic_point_in_time_report"
                if evidence_class == "authentic_owner_authorized_point_in_time_report"
                else "explicit_manifest_bound_report"
            ),
            "evidence_population": "packet_report",
            "reason_codes": [attention_class, str(task.get("gate_stop_class", "UNKNOWN"))],
        }
        items.append(
            {
                "condition_key": f"supervision_packet:{task_id}",
                "precedence": int(task.get("attention_precedence", 5)),
                "project_key": project_key,
                "thread_id": str(task.get("thread_id", "unknown-thread")),
                "lane_id": str(task.get("lane_id", "unknown-lane")),
                "slice_id": str(task.get("slice_id", "unknown-slice")),
                "artifact_id": str(task.get("artifact_id", "unknown-artifact")),
                "attention_class": attention_class,
                "global_rank_meaning": "attention_and_review_priority_only",
                "project_local_first": first_by_project.get(project_key) == task_id,
                "required": bool(task.get("required")),
                "state": state_labels.get(attention_class, state_labels["unknown_requiring_review"]),
                "action": {
                    "ja": f"{project_key}: {task.get('outcome_summary', 'reportを確認')}",
                    "en": str(task.get("outcome_summary", "Review report")),
                },
                "reason": {
                    "ja": f"現在: {task.get('current_state', 'unknown')}",
                    "en": f"Current state: {task.get('current_state', 'unknown')}",
                },
                "decision": {
                    "ja": f"確認分類: {attention_class}",
                    "en": f"Attention class: {attention_class}",
                },
                "desired_outcome": {"ja": next_text, "en": next_text},
                "owner": {
                    "id": _slug(next_state.get("owner") or "supervisor"),
                    "ja": str(next_state.get("owner") or "Supervisor"),
                    "en": str(next_state.get("owner") or "Supervisor"),
                },
                "raw_condition": str(task.get("gate_decision", "unknown")),
                "primary_evidence_id": evidence["source_id"],
                "primary_evidence_path": source_path,
                "evidence_refs": [evidence],
                "review_action_refs": [],
                "source_report_sha256": source_hash,
                "claim_class": "derived",
                "evidence_claim_class": "observed_report",
                "display_copy_claim_class": "editorial",
                "ranking_policy_claim_class": "policy",
                "executable": False,
                "blocked_by_gate": attention_class
                in {"true_stop_or_required_failure", "user_authorization_or_material_decision"},
                "safe_next_surface": "local_review",
                "priority_id": task_id,
                "rank": (
                    int(task["global_rank"])
                    if type(task.get("global_rank")) is int
                    else 0
                ),
                "informational_only": collection == "closed_or_informational",
            }
        )
    return items


def _packet_attention_summary(packet: dict[str, Any]) -> dict[str, Any]:
    if not packet:
        return {
            "loaded": False,
            "status": "not_loaded",
            "stop": 0,
            "decision": 0,
            "active": 0,
            "closed": 0,
            "all_closed": False,
            "executable": False,
        }
    tasks = [_dict(value) for value in _list(packet.get("global_attention_queue"))]
    classes = [str(task.get("attention_class", "")) for task in tasks]
    stop = classes.count("true_stop_or_required_failure")
    decision = sum(
        classes.count(value)
        for value in (
            "user_authorization_or_material_decision",
            "awaiting_supervisor_acceptance",
            "unknown_requiring_review",
        )
    )
    active = classes.count("active_safe_continuation")
    closed = len(_list(packet.get("closed_or_informational")))
    status = "stop" if stop else "decision" if decision else "active" if active else "all_closed"
    return {
        "loaded": True,
        "status": status,
        "stop": stop,
        "decision": decision,
        "active": active,
        "closed": closed,
        "all_closed": not tasks and closed > 0,
        "executable": False,
    }


def _priority_items(
    *,
    health: dict[str, Any],
    validation: dict[str, Any],
    smoke: dict[str, Any],
    status: dict[str, Any],
    receipt: dict[str, Any],
    review_actions: list[dict[str, Any]],
    validation_path: str,
    smoke_path: str,
    status_path: str,
) -> list[dict[str, Any]]:
    """Build one deterministic, deduplicated, review-only priority queue."""

    receipt_sources = _list(receipt.get("sources"))
    receipt_projects = {
        str(item.get("project_id", "")): item
        for item in _list(receipt.get("projects"))
        if isinstance(item, dict)
    }
    required_projects = {
        key for key, item in receipt_projects.items() if item.get("required") is True
    }
    candidates: dict[str, dict[str, Any]] = {}

    def evidence_for(path: str, project_key: str | None = None) -> dict[str, Any]:
        normalized = _normalized_evidence_path(path)
        exact = [
            item
            for item in receipt_sources
            if isinstance(item, dict)
            and _normalized_evidence_path(str(item.get("source_path", ""))) == normalized
        ]
        if exact:
            return dict(sorted(exact, key=lambda item: str(item.get("source_id", "")))[0])
        if project_key:
            live_id = f"{project_key}.live_status_observation"
            for item in receipt_sources:
                if isinstance(item, dict) and item.get("source_id") == live_id:
                    return dict(item)
        return {
            "source_id": "dashboard-production-surface",
            "source_path": path,
            "freshness_state": "not_applicable",
            "temporal_state": "not_applicable",
            "revision_binding_state": "not_applicable",
            "current_state_claim_eligible": False,
            "assessed_at": str(receipt.get("assessed_at", "")),
            "fresh_through": None,
            "content_sha256": None,
            "authority_classification": "review_metadata",
            "reason_codes": ["review_metadata_not_current_state_evidence"],
        }

    def add(
        *,
        condition_key: str,
        precedence: int,
        project_key: str,
        required: bool,
        evidence_path: str,
        raw_condition: str,
        action_ja: str,
        action_en: str,
        reason_ja: str,
        reason_en: str,
        decision_ja: str,
        decision_en: str,
        outcome_ja: str,
        outcome_en: str,
        owner_id: str,
        owner_ja: str,
        owner_en: str,
        evidence: dict[str, Any] | None = None,
    ) -> None:
        dedupe_key = f"{project_key}:{condition_key}"
        item = candidates.get(dedupe_key)
        if item is not None:
            ref = _priority_evidence_ref(evidence or evidence_for(evidence_path, project_key))
            if ref not in item["evidence_refs"]:
                item["evidence_refs"].append(ref)
                item["evidence_refs"].sort(key=lambda value: (value["source_path"], value["source_id"]))
            return
        evidence_row = evidence or evidence_for(evidence_path, project_key)
        candidates[dedupe_key] = {
            "condition_key": condition_key,
            "precedence": precedence,
            "project_key": project_key,
            "required": required,
            "state": _priority_state(precedence),
            "action": {"ja": action_ja, "en": action_en},
            "reason": {"ja": reason_ja, "en": reason_en},
            "decision": {"ja": decision_ja, "en": decision_en},
            "desired_outcome": {"ja": outcome_ja, "en": outcome_en},
            "owner": {"id": owner_id, "ja": owner_ja, "en": owner_en},
            "raw_condition": raw_condition,
            "primary_evidence_id": str(evidence_row.get("source_id", "")),
            "primary_evidence_path": str(evidence_row.get("source_path", evidence_path)),
            "evidence_refs": [_priority_evidence_ref(evidence_row)],
            "review_action_refs": [],
            "claim_class": "derived",
            "evidence_claim_class": "observed",
            "display_copy_claim_class": "editorial",
            "ranking_policy_claim_class": "policy",
            "executable": False,
            "blocked_by_gate": False,
            "safe_next_surface": "local_review",
        }

    failed_required_check_keys = {
        str(item.get("check_key", "unknown"))
        for item in _list(validation.get("checks"))
        if isinstance(item, dict)
        and str(item.get("result", "")).lower() in {"fail", "failed", "error"}
        and str(item.get("severity", "")).lower() == "required"
    }
    for source_name, payload, evidence_path in (
        ("validation", validation, validation_path),
        ("smoke", smoke, smoke_path),
    ):
        explicit_blockers = sorted(
            {
                str(value)
                for value in _list(_dict(payload.get("health")).get("blockers"))
                if str(value)
            }
        )
        for blocker in explicit_blockers:
            matching_check = next(
                (key for key in sorted(failed_required_check_keys) if key.lower() in blocker.lower()),
                None,
            )
            condition_key = (
                f"validation_check:{matching_check}"
                if source_name == "validation" and matching_check
                else f"blocker:{source_name}:{_condition_code(blocker)}"
            )
            add(
                condition_key=condition_key,
                precedence=1,
                project_key="devcockpitcore",
                required=True,
                evidence_path=evidence_path,
                raw_condition=blocker,
                action_ja="必須ブロッカーを解消する",
                action_en="Resolve the required blocker",
                reason_ja="必須の停止条件が証拠に記録されています。",
                reason_en=f"A required stop condition is reported: {blocker}",
                decision_ja="この停止条件を解消するために、どの最小修正が必要か。",
                decision_en="What is the smallest correction that clears this stop condition?",
                outcome_ja="必須ゲートが停止条件なしで再検証される。",
                outcome_en="The required gate is revalidated without a stop condition.",
                owner_id="operator",
                owner_ja="運用担当",
                owner_en="Operator",
            )
        summary_failed = str(_dict(payload.get("summary")).get("result", "")).lower() == "fail"
        concrete_failure_exists = bool(explicit_blockers) or (
            source_name == "validation" and bool(failed_required_check_keys)
        )
        if summary_failed and not concrete_failure_exists:
            add(
                condition_key=f"blocker:{source_name}:summary_failed",
                precedence=1,
                project_key="devcockpitcore",
                required=True,
                evidence_path=evidence_path,
                raw_condition=f"{source_name} summary result is fail",
                action_ja=f"{source_name}の停止結果を調査する",
                action_en=f"Investigate the {source_name} stop result",
                reason_ja="具体的な失敗行を伴わない停止結果が報告されています。",
                reason_en=f"The {source_name} summary reports failure without a concrete blocker row.",
                decision_ja="停止結果を説明する具体的な証拠行はどれか。",
                decision_en="Which concrete evidence row explains the stop result?",
                outcome_ja="停止結果が具体的な原因と修正へ結び付く。",
                outcome_en="The stop result is tied to a concrete cause and correction.",
                owner_id="operator",
                owner_ja="運用担当",
                owner_en="Operator",
            )

    status_health = _dict(status.get("health"))
    status_is_blocking = str(status_health.get("status", "")).lower() in {"red", "fail", "failed"}
    if status_is_blocking:
        raw_status = "; ".join(str(value) for value in _list(status_health.get("notes"))) or "status snapshot health is red"
        add(
            condition_key=_condition_code(raw_status),
            precedence=1,
            project_key="devcockpitcore",
            required=True,
            evidence_path=status_path,
            raw_condition=raw_status,
            action_ja="状態snapshotの停止条件を解消する",
            action_en="Resolve the status snapshot stop condition",
            reason_ja="状態snapshotが停止状態を報告しています。",
            reason_en=f"The status snapshot reports a stop condition: {raw_status}",
            decision_ja="停止状態を解消する最小の確認または修正は何か。",
            decision_en="What is the smallest review or correction that clears the stop state?",
            outcome_ja="状態snapshotが停止条件なしで再生成される。",
            outcome_en="The status snapshot is regenerated without a stop condition.",
            owner_id="operator",
            owner_ja="運用担当",
            owner_en="Operator",
        )

    for check in sorted(
        (item for item in _list(validation.get("checks")) if isinstance(item, dict)),
        key=lambda item: str(item.get("check_key", "")),
    ):
        if str(check.get("result", "")).lower() not in {"fail", "failed", "error"}:
            continue
        if str(check.get("severity", "")).lower() != "required":
            continue
        check_key = str(check.get("check_key", "unknown"))
        raw = _first_finding_text(check) or f"required validation check failed: {check_key}"
        human_check = check_key.replace("_", " ").strip() or "required validation"
        add(
            condition_key=f"validation_check:{check_key}",
            precedence=2,
            project_key="devcockpitcore",
            required=True,
            evidence_path=validation_path,
            raw_condition=raw,
            action_ja="必須検証の失敗を修復する",
            action_en=f"Repair required validation check '{human_check}'",
            reason_ja="必須検証が失敗しています。機械判定の詳細は隣接する根拠で確認できます。",
            reason_en=f"A required validation check failed: {raw}",
            decision_ja="失敗原因を除去する最小の変更は何か。",
            decision_en="What is the smallest change that removes the failure?",
            outcome_ja="対象検証がpassになり、他の必須検証を退行させない。",
            outcome_en="The check passes without regressing other required validation.",
            owner_id="developer",
            owner_ja="開発担当",
            owner_en="Developer",
        )

    input_paths = {validation_path, smoke_path, status_path}
    for project_key in sorted(required_projects):
        backing = [
            item
            for item in receipt_sources
            if isinstance(item, dict)
            and item.get("project_id") == project_key
            and (
                _normalized_evidence_path(str(item.get("source_path", "")))
                in {_normalized_evidence_path(path) for path in input_paths}
                or item.get("source_id") == f"{project_key}.live_status_observation"
            )
        ]
        if any(item.get("current_state_claim_eligible") is True for item in backing):
            continue
        reason_codes = sorted(
            {
                str(code)
                for item in backing
                for code in _list(item.get("reason_codes"))
                if str(code)
            }
        )
        primary = sorted(
            backing,
            key=lambda item: (
                0 if item.get("source_id") == f"{project_key}.live_status_observation" else 1,
                str(item.get("source_id", "")),
            ),
        )[0] if backing else evidence_for(status_path, project_key)
        raw = ", ".join(reason_codes) or "no eligible current-state evidence source"
        add(
            condition_key="current_claim_ineligible",
            precedence=3,
            project_key=project_key,
            required=True,
            evidence_path=str(primary.get("source_path", status_path)),
            raw_condition=raw,
            action_ja="現状根拠を更新して適格性を回復する",
            action_en="Refresh evidence and restore current-state eligibility",
            reason_ja="必須プロジェクトを現在状態として扱える根拠がありません。",
            reason_en="No evidence for the required project is eligible for a current-state claim.",
            decision_ja="どの読み取り専用観測を更新すれば、現在状態を安全に判断できるか。",
            decision_en="Which read-only observation must be refreshed before current state can be judged safely?",
            outcome_ja="新しい鮮度証跡で、少なくとも1つの必須観測が現状根拠として使用可能になる。",
            outcome_en="A new receipt makes at least one required observation current-state eligible.",
            owner_id="operator",
            owner_ja="運用担当",
            owner_en="Operator",
            evidence=primary,
        )

    for check in sorted(
        (item for item in _list(validation.get("checks")) if isinstance(item, dict)),
        key=lambda item: str(item.get("check_key", "")),
    ):
        if str(check.get("result", "")).lower() != "warn":
            continue
        check_key = str(check.get("check_key", "unknown"))
        raw = _first_finding_text(check) or f"validation warning: {check_key}"
        label_ja, label_en = _validation_check_label(check_key)
        add(
            condition_key=f"validation_check:{check_key}",
            precedence=4,
            project_key="devcockpitcore",
            required=True,
            evidence_path=validation_path,
            raw_condition=raw,
            action_ja=label_ja,
            action_en=label_en,
            reason_ja="追跡済み検証packが、確認の必要な衛生上の警告を1件記録しています。",
            reason_en="The tracked validation pack records one hygiene warning that needs classification.",
            decision_ja="既知fixtureとして維持するか、衛生上の残留として除去するか。",
            decision_en="Should this remain as a known fixture or be removed as hygiene residue?",
            outcome_ja="警告の意図と次の扱いが記録される。",
            outcome_en="The warning's intent and next treatment are recorded.",
            owner_id="operator",
            owner_ja="運用担当",
            owner_en="Operator",
        )

    project_rows = [item for item in _list(smoke.get("projects")) if isinstance(item, dict)]
    for project in sorted(project_rows, key=lambda item: str(item.get("project_key", ""))):
        project_key = str(project.get("project_key", "unknown"))
        project_name = str(project.get("project", project_key))
        receipt_project = _dict(receipt_projects.get(project_key))
        if receipt_project and receipt_project.get("available") is False:
            continue
        required = bool(project.get("required")) or project_key in required_projects
        status_snapshot = _dict(project.get("status_snapshot"))
        for warning in sorted({str(value) for value in _list(status_snapshot.get("warnings")) if str(value)}):
            condition = _condition_code(warning)
            warning_ja = _warning_reason_ja(warning)
            precedence = 4 if required else 5
            add(
                condition_key=condition,
                precedence=precedence,
                project_key=project_key,
                required=required,
                evidence_path=smoke_path,
                raw_condition=warning,
                action_ja=f"{project_name} の観測警告を確認する",
                action_en=f"Review the {project_name} observation warning",
                reason_ja=f"読み取り専用観測の報告: {warning_ja}",
                reason_en=f"The read-only observation reports: {warning}",
                decision_ja="想定内の観測状態か、当該プロジェクトの専用laneへ送るべきか。",
                decision_en="Is this expected observer state, or should it be routed to that project's own lane?",
                outcome_ja="DevCockpitCoreから書き戻さず、所有者と次の確認先が明確になる。",
                outcome_en="Owner and next review surface are clear without writeback from DevCockpitCore.",
                owner_id="project_owner" if not required else "operator",
                owner_ja="プロジェクト所有者" if not required else "運用担当",
                owner_en="Project owner" if not required else "Operator",
                evidence=evidence_for(smoke_path, project_key),
            )

    status_snapshot = _dict(status.get("health"))
    status_notes = [] if status_is_blocking else sorted(
        {str(value) for value in _list(status_snapshot.get("notes")) if str(value)}
    )
    for note in status_notes:
        condition = _condition_code(note)
        add(
            condition_key=condition,
            precedence=4,
            project_key="devcockpitcore",
            required=True,
            evidence_path=status_path,
            raw_condition=note,
            action_ja="DevCockpitCoreの状態注記を確認する",
            action_en="Review the DevCockpitCore status note",
            reason_ja=f"状態snapshotの注記: {_warning_reason_ja(note)}",
            reason_en=f"The status snapshot contains a note: {note}",
            decision_ja="この状態は現在の作業境界として想定内か。",
            decision_en="Is this state expected within the current work boundary?",
            outcome_ja="状態注記が想定内か要対応かに分類される。",
            outcome_en="The note is classified as expected or requiring follow-up.",
            owner_id="operator",
            owner_ja="運用担当",
            owner_en="Operator",
        )

    for project_key, project in sorted(receipt_projects.items()):
        if project.get("required") is True or project.get("available") is not False:
            continue
        raw = ", ".join(str(value) for value in _list(project.get("reason_codes"))) or "optional project missing"
        add(
            condition_key="optional_project_missing",
            precedence=6,
            project_key=project_key,
            required=False,
            evidence_path=f"git-observation:../{project_key}",
            raw_condition=raw,
            action_ja=f"任意プロジェクト {project_key} の欠落を記録する",
            action_en=f"Record missing optional project {project_key}",
            reason_ja="任意観測先が見つかりません。必須ゲートは停止しません。",
            reason_en="The optional observation target is missing and does not stop the required gate.",
            decision_ja="次回観測まで参考情報として残すか。",
            decision_en="Should this remain informational until the next observation?",
            outcome_ja="任意欠落が必須問題と混同されない。",
            outcome_en="Optional absence is not confused with a required problem.",
            owner_id="observer",
            owner_ja="観測担当",
            owner_en="Observer",
            evidence=evidence_for(f"git-observation:../{project_key}", project_key),
        )

    matched_review_action_ids = _attach_priority_review_actions(candidates, review_actions)
    owner_labels = {
        "operator": ("運用担当", "Operator"),
        "developer": ("開発担当", "Developer"),
        "supervisor": ("監修担当", "Supervisor"),
    }
    for raw_action in review_actions:
        action = _dict(raw_action)
        action_id = str(action.get("action_id", ""))
        if action_id in matched_review_action_ids or not _priority_eligible_review_action(action):
            continue
        source_type = str(action.get("source_type", ""))
        project_key = str(action.get("project_key") or "devcockpitcore")
        action_receipt_project = _dict(receipt_projects.get(project_key))
        if (
            source_type in {"cross_project_smoke", "status_snapshot"}
            and action_receipt_project
            and action_receipt_project.get("available") is False
        ):
            continue
        required = project_key in required_projects or project_key == "devcockpitcore"
        severity = str(action.get("severity", "warning")).lower()
        precedence = 1 if severity == "blocker" else 4 if required else 5
        reason = str(action.get("reason", "review action requires classification"))
        evidence_path = str(action.get("evidence_path") or action.get("source_path") or status_path)
        owner_id = str(action.get("owner_hint") or "operator")
        owner_ja, owner_en = owner_labels.get(owner_id, ("担当者", owner_id.replace("_", " ").title()))
        source_labels = {
            "validation_pack": ("検証警告", "validation warning"),
            "cross_project_smoke": ("横断観測警告", "cross-project observation warning"),
            "status_snapshot": ("状態注記", "status note"),
        }
        source_ja, source_en = source_labels.get(source_type, ("確認項目", "review item"))
        add(
            condition_key=f"review_action:{source_type}:{_condition_code(reason)}",
            precedence=precedence,
            project_key=project_key,
            required=required,
            evidence_path=evidence_path,
            raw_condition=reason,
            action_ja=f"担当付き{source_ja}を確認する",
            action_en=f"Review the owned {source_en}",
            reason_ja="既存の非実行review actionが、担当者付きの確認項目を報告しています。",
            reason_en=f"An existing non-executable review action reports: {reason}",
            decision_ja="この確認項目は想定内か、所有laneへ送るべきか。",
            decision_en="Is this expected, or should it be routed to the owning lane?",
            outcome_ja="確認結果と次の所有者が記録される。",
            outcome_en="The classification and next owner are recorded.",
            owner_id=owner_id,
            owner_ja=owner_ja,
            owner_en=owner_en,
        )
    _attach_priority_review_actions(candidates, review_actions)

    if not candidates:
        eligible_sources = [
            item
            for item in receipt_sources
            if isinstance(item, dict)
            and item.get("project_id") == "devcockpitcore"
            and item.get("current_state_claim_eligible") is True
        ]
        primary = (
            sorted(eligible_sources, key=lambda item: str(item.get("source_id", "")))[0]
            if eligible_sources
            else evidence_for(status_path, "devcockpitcore")
        )
        add(
            condition_key="routine_observation_review",
            precedence=5,
            project_key="devcockpitcore",
            required=True,
            evidence_path=str(primary.get("source_path", status_path)),
            raw_condition="no blocker or actionable warning; current evidence eligible",
            action_ja="現状根拠を確認して観測を継続する",
            action_en="Confirm current evidence and continue observation",
            reason_ja="停止条件と担当付き警告はなく、必須の現状根拠を使用できます。",
            reason_en="No stop condition or owned warning is present, and required current-state evidence is eligible.",
            decision_ja="この状態を次のhandoffに使えるか。",
            decision_en="Can this state support the next handoff?",
            outcome_ja="健全な状態が明示され、次の観測時点が分かる。",
            outcome_en="The healthy state is explicit and the next observation point is clear.",
            owner_id="observer",
            owner_ja="観測担当",
            owner_en="Observer",
            evidence=primary,
        )

    ordered = sorted(
        candidates.values(),
        key=lambda item: (
            _int(item.get("precedence")),
            0 if item.get("required") is True else 1,
            str(item.get("project_key", "")),
            str(item.get("condition_key", "")),
            str(item.get("primary_evidence_path", "")),
        ),
    )
    for rank, item in enumerate(ordered, start=1):
        identity = f"{item['project_key']}:{item['condition_key']}"
        item["priority_id"] = f"priority-{hashlib.sha256(identity.encode('utf-8')).hexdigest()[:12]}"
        item["rank"] = rank
    return ordered


def _priority_evidence_ref(source: dict[str, Any]) -> dict[str, Any]:
    return {
        key: source.get(key)
        for key in (
            "source_id",
            "source_path",
            "freshness_state",
            "temporal_state",
            "revision_binding_state",
            "current_state_claim_eligible",
            "assessed_at",
            "fresh_through",
            "content_sha256",
            "authority_classification",
            "reason_codes",
        )
    }


def _attach_priority_review_actions(
    candidates: dict[str, dict[str, Any]],
    review_actions: list[dict[str, Any]],
) -> set[str]:
    """Bind compatible review-action evidence without turning it into execution."""

    matched_ids: set[str] = set()
    for candidate in candidates.values():
        condition_key = str(candidate.get("condition_key", ""))
        project_key = str(candidate.get("project_key", ""))
        refs: list[dict[str, Any]] = []
        for raw_action in review_actions:
            action = _dict(raw_action)
            if not _priority_eligible_review_action(action):
                continue
            source_type = str(action.get("source_type", ""))
            reason = str(action.get("reason", ""))
            lowered = reason.lower()
            action_project = str(action.get("project_key") or "")
            if action_project and action_project != project_key:
                continue
            action_condition = _condition_code(reason)
            condition_matches = (
                action_condition == condition_key
                or condition_key.endswith(action_condition)
                or (
                    condition_key.startswith("validation_check:")
                    and condition_key.split(":", 1)[1] in lowered
                    and source_type == "validation_pack"
                )
            )
            if not condition_matches:
                continue
            refs.append(
                {
                    "action_id": str(action.get("action_id", "")),
                    "source_type": source_type,
                    "severity": str(action.get("severity", "")),
                    "owner_hint": str(action.get("owner_hint", "")),
                    "evidence_path": str(action.get("evidence_path", "")),
                    "executable": False,
                }
            )
            matched_ids.add(str(action.get("action_id", "")))
        candidate["review_action_refs"] = sorted(
            {item["action_id"]: item for item in refs if item["action_id"]}.values(),
            key=lambda item: item["action_id"],
        )
    return {value for value in matched_ids if value}


def _priority_eligible_review_action(action: dict[str, Any]) -> bool:
    if action.get("executable") is not False:
        return False
    if str(action.get("source_type", "")) not in {
        "validation_pack",
        "cross_project_smoke",
        "status_snapshot",
    }:
        return False
    if str(action.get("severity", "")).lower() not in {"blocker", "warning"}:
        return False
    if not str(action.get("owner_hint", "")).strip():
        return False
    reason = str(action.get("reason", ""))
    lowered = reason.lower()
    if (
        "summary result is" in lowered
        or lowered == "report hygiene warnings present"
        or (str(action.get("project_key") or "") == "" and lowered.endswith(": warn"))
    ):
        return False
    return True


def _priority_state(precedence: int) -> dict[str, str]:
    states = {
        1: {"key": "blocked", "ja": "停止", "en": "Blocked"},
        2: {"key": "failed", "ja": "失敗", "en": "Failed"},
        3: {"key": "evidence_ineligible", "ja": "根拠更新待ち", "en": "Evidence refresh needed"},
        4: {"key": "review", "ja": "要確認", "en": "Review"},
        5: {"key": "decision", "ja": "判断待ち", "en": "Decision pending"},
        6: {"key": "informational", "ja": "参考", "en": "Informational"},
    }
    return dict(states.get(precedence, states[6]))


def _condition_code(value: str) -> str:
    lowered = value.strip().lower()
    known = (
        ("worktree is dirty", "worktree_dirty"),
        ("runtime state document is absent", "runtime_state_missing"),
        ("project context document is absent", "project_context_missing"),
        ("differs from adapter default", "branch_differs_from_default"),
        ("pseudo_git_tag", "pseudo_git_tag_residue"),
    )
    for needle, code in known:
        if needle in lowered:
            return code
    digest = hashlib.sha256(lowered.encode("utf-8")).hexdigest()[:12]
    return f"observed_condition_{digest}"


def _warning_reason_ja(value: str) -> str:
    lowered = value.strip().lower()
    if "worktree is dirty" in lowered:
        return "作業ツリーに未確定変更があります。"
    if "runtime state document is absent" in lowered:
        return "runtime-state文書がありません。"
    if "project context document is absent" in lowered:
        return "project-context文書がありません。"
    if "differs from adapter default" in lowered:
        return "現在のbranchがadapterの既定branchと異なります。"
    return "詳細は隣接する根拠と由来情報で確認してください。"


def _first_finding_text(check: dict[str, Any]) -> str:
    findings = _list(check.get("findings"))
    if not findings:
        return ""
    first = findings[0]
    if isinstance(first, dict):
        return json.dumps(first, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return str(first)


def _validation_check_label(check_key: str) -> tuple[str, str]:
    if check_key == "pseudo_git_tag_scan":
        return (
            "サンプル報告内のGit UI表記を確認する",
            "Review Git UI markers in the sample report",
        )
    human = check_key.replace("_", " ").strip() or "validation warning"
    return (f"検証警告「{human}」を判定する", f"Classify validation warning '{human}'")


def _normalized_evidence_path(value: str) -> str:
    return value.strip().replace("\\", "/").lower()


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


def priority_readback(model: dict[str, Any]) -> dict[str, Any]:
    """Return the deterministic machine readback consumed by capture QA."""

    freshness = _dict(model.get("evidence_freshness"))
    priority_output = _dict(model.get("priority_readback"))
    priorities = [dict(item) for item in _list(model.get("priority_items")) if isinstance(item, dict)]
    informational_items = [
        dict(item)
        for item in _list(model.get("informational_items"))
        if isinstance(item, dict)
    ]
    supervision_packet = _dict(model.get("supervision_packet"))
    packet_attention = _dict(model.get("packet_attention"))
    receipt_path = _source_path(_list(model.get("sources")), "evidence_freshness_receipt")
    return {
        "schema_version": "devcockpit_priority_readback.v1",
        "artifact_id": "priority-review-console-production-observation-surface-v1",
        "generated_at": str(model.get("generated_at", "")),
        "producer": PRODUCER,
        "surface": {
            "selected_direction": "priority-review-console",
            "production": True,
            "b_and_c_production_tabs": False,
            "selected_priority_id": model.get("selected_priority_id"),
            "selected_closed_evidence_id": model.get("selected_closed_evidence_id"),
            "priority_count": len(priorities),
            "all_closed": bool(supervision_packet and not priorities and informational_items),
            "default_language": "ja",
            "languages": ["ja", "en"],
            "user_visual_acceptance": str(model.get("user_visual_acceptance", "accepted")),
            "executable": False,
        },
        "priority_policy": [dict(item) for item in _list(model.get("priority_policy")) if isinstance(item, dict)],
        "supervision_packet": {
            "loaded": bool(supervision_packet),
            "schema_version": supervision_packet.get("schema_version"),
            "artifact_id": supervision_packet.get("artifact_id"),
            "coverage": _dict(supervision_packet.get("coverage")),
            "project_worksets": [
                dict(item)
                for item in _list(supervision_packet.get("project_worksets"))
                if isinstance(item, dict)
            ],
            "scope_boundary": _dict(supervision_packet.get("scope_boundary")),
            "attention_summary": dict(packet_attention),
        },
        "freshness_receipt": {
            "path": receipt_path,
            "schema_version": freshness.get("schema_version"),
            "capture_id": freshness.get("capture_id"),
            "assessed_at": freshness.get("assessed_at"),
            "observation_mode": freshness.get("observation_mode"),
            "authority": _dict(freshness.get("authority")),
            "source_counts": _dict(freshness.get("source_counts")),
            "current_state_claim_eligible": _dict(
                freshness.get("current_state_claim_eligible")
            ),
        },
        "priority_output": dict(priority_output),
        "priorities": priorities,
        "informational_items": informational_items,
        "scope_boundary": {
            "observer_first": True,
            "offline_static": True,
            "target_repository_writeback": False,
            "execution_automation": False,
            "external_publication": False,
            "locked_lanes_excluded_from_priorities": True,
        },
    }


def write_priority_readback(
    package: dict[str, Any],
    output_path: str | Path,
    *,
    pretty: bool = False,
) -> None:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(
        package,
        ensure_ascii=False,
        indent=2 if pretty else None,
        sort_keys=True,
    )
    output.write_text(f"{text}\n", encoding="utf-8", newline="\n")


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


def _frontpage_report(
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
        "kind": "frontpage_report",
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
            "label": "1. Priority Comprehension",
            "state": f"{blocker_count} blocker(s), {warning_count} warning signal(s)",
            "prompt": "Confirm rank 1 exposes action, reason, state, owner, and next operation.",
            "evidence": "Priority Lane / Active Decision",
        },
        {
            "label": "2. Selection Synchronization",
            "state": "priority, decision, and evidence share one selected ID",
            "prompt": "Confirm click and keyboard selection keep the decision and evidence inspector synchronized.",
            "evidence": "Priority Review Console",
        },
        {
            "label": "3. Evidence Eligibility",
            "state": f"validation {validation_summary.get('result', 'unknown')} / smoke {smoke_summary.get('result', 'unknown')}",
            "prompt": "Verify the receipt's freshness, revision binding, authority, and current-claim eligibility.",
            "evidence": "Evidence Inspector / receipt ledger",
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
    return list(value) if isinstance(value, list) else []


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
  "use strict";
  var modelNode = document.getElementById("priority-model");
  var priorities = modelNode ? JSON.parse(modelNode.textContent || "[]") : [];
  var byId = new Map(priorities.map(function (item) { return [item.priority_id, item]; }));
  var priorityButtons = Array.prototype.slice.call(document.querySelectorAll("button[data-priority-id]"));
  var languageButtons = Array.prototype.slice.call(document.querySelectorAll("button[data-language]"));
  var decision = document.querySelector('[data-landmark="active-decision"]');
  var inspector = document.querySelector('[data-landmark="evidence-inspector"]');
  var selectedId = priorityButtons.length ? priorityButtons[0].dataset.priorityId : null;

  function compactPath(value) {
    var normalized = String(value || "").replaceAll("\\\\", "/").replace(/[/]$/u, "");
    if (normalized.startsWith("git-observation:")) return normalized;
    return normalized.split("/").pop() || "n/a";
  }

  function humanSourceLabel(sourceId) {
    var known = {
      "validation-pack-sample": { ja: "検証pack結果", en: "Validation pack result" },
      "cross-project-smoke-sample": { ja: "横断観測結果", en: "Cross-project observation" },
      "status-snapshot-sample": { ja: "状態snapshot", en: "Status snapshot" },
      "intent-comparison-manifest-v2": { ja: "比較履歴", en: "Comparison history" }
    };
    if (known[sourceId]) return known[sourceId];
    if (String(sourceId || "").endsWith(".live_status_observation")) {
      var project = sourceId.split(".", 1)[0];
      return { ja: project + " 読み取り専用観測", en: project + " read-only observation" };
    }
    return { ja: "証拠ソース", en: "Evidence source" };
  }

  function localizedEvidenceLabels(evidence) {
    var freshness = {
      fresh: { ja: "鮮度内", en: "Fresh" },
      stale: { ja: "期限超過", en: "Stale" },
      unknown: { ja: "鮮度不明", en: "Freshness unknown" },
      not_applicable: { ja: "対象外", en: "Not applicable" }
    }[evidence.freshness_state] || { ja: "鮮度不明", en: String(evidence.freshness_state || "Unknown") };
    var temporal = {
      fresh: { ja: "鮮度内", en: "Fresh" },
      stale: { ja: "期限超過", en: "Stale" },
      unknown: { ja: "不明", en: "Unknown" },
      not_applicable: { ja: "対象外", en: "Not applicable" }
    }[evidence.temporal_state] || { ja: "不明", en: String(evidence.temporal_state || "Unknown") };
    var revision = {
      match: { ja: "一致", en: "Match" },
      mismatch: { ja: "不一致", en: "Mismatch" },
      unknown: { ja: "不明", en: "Unknown" },
      not_applicable: { ja: "対象外", en: "Not applicable" }
    }[evidence.revision_binding_state] || { ja: "不明", en: String(evidence.revision_binding_state || "Unknown") };
    var eligibility = evidence.current_state_claim_eligible === true
      ? { ja: "使用可", en: "Eligible" }
      : { ja: "使用不可", en: "Ineligible" };
    return {
      classification: {
        ja: freshness.ja + "・現状根拠" + eligibility.ja,
        en: freshness.en + " · claim-" + eligibility.en.toLowerCase()
      },
      eligibility: eligibility,
      temporal: temporal,
      revision: revision
    };
  }

  function bilingual(container, value) {
    if (!container) return;
    var pair = value || {};
    var ja = container.querySelector(".lang-ja");
    var en = container.querySelector(".lang-en");
    if (ja) ja.textContent = pair.ja || "";
    if (en) en.textContent = pair.en || "";
  }

  function text(target, value) {
    var node = document.querySelector(target);
    if (node) node.textContent = value == null ? "n/a" : String(value);
  }

  function selectPriority(priorityId, focus) {
    var item = byId.get(priorityId);
    if (!item || !decision || !inspector) return;
    selectedId = priorityId;
    priorityButtons.forEach(function (button) {
      var isSelected = button.dataset.priorityId === priorityId;
      button.setAttribute("aria-selected", isSelected ? "true" : "false");
      button.tabIndex = isSelected ? 0 : -1;
      if (isSelected && focus) button.focus();
    });
    decision.dataset.priorityId = priorityId;
    decision.dataset.selectedPriorityId = priorityId;
    inspector.dataset.priorityId = priorityId;
    inspector.dataset.selectedPriorityId = priorityId;
    decision.querySelector('[data-field="rank"]').textContent = "#" + item.rank;
    bilingual(decision.querySelector('[data-field="state"]'), item.state);
    bilingual(decision.querySelector('[data-field="action"]'), item.action);
    bilingual(decision.querySelector('[data-field="reason"]'), item.reason);
    bilingual(decision.querySelector('[data-field="decision"]'), item.decision);
    bilingual(decision.querySelector('[data-field="outcome"]'), item.desired_outcome);
    bilingual(decision.querySelector('[data-field="owner"]'), item.owner);
    text('#active-decision [data-field="project-identity"]', (item.project_key || "unknown") + " / " + (item.thread_id || "local-observation"));
    text('#active-decision [data-field="lane-identity"]', (item.lane_id || "observer") + " / " + (item.slice_id || "local-review"));
    var evidence = (item.evidence_refs || [])[0] || {};
    var evidenceLabels = localizedEvidenceLabels(evidence);
    inspector.dataset.evidenceId = evidence.source_id || "";
    bilingual(inspector.querySelector('[data-field="freshness"]'), evidenceLabels.classification);
    bilingual(inspector.querySelector('[data-field="source-label"]'), humanSourceLabel(evidence.source_id));
    text('#evidence-inspector [data-field="source-route"]', compactPath(evidence.source_path));
    bilingual(inspector.querySelector('[data-field="eligible"]'), evidenceLabels.eligibility);
    bilingual(inspector.querySelector('[data-field="temporal"]'), evidenceLabels.temporal);
    bilingual(inspector.querySelector('[data-field="revision"]'), evidenceLabels.revision);
    text('#evidence-inspector [data-field="assessed"]', evidence.assessed_at || "n/a");
    text('#evidence-inspector [data-field="fresh-through"]', evidence.fresh_through || "n/a");
    text('#evidence-inspector [data-field="source-id"]', evidence.source_id || "n/a");
    text('#evidence-inspector [data-field="attention-class"]', item.attention_class || "local_evidence_priority");
    text('#evidence-inspector [data-field="evidence-population"]', evidence.evidence_population || "local_observer_receipt");
    text('#evidence-inspector [data-field="source-path"]', evidence.source_path || "n/a");
    text('#evidence-inspector [data-field="authority"]', evidence.authority_classification || "unknown");
    text('#evidence-inspector [data-field="reason-codes"]', (evidence.reason_codes || []).join(", ") || "none");
    text(
      '#evidence-inspector [data-field="review-actions"]',
      (item.review_action_refs || []).map(function (ref) { return ref.action_id; }).join(", ") || "none"
    );
    text('#evidence-inspector [data-field="content-sha"]', evidence.content_sha256 || "n/a");
  }

  function setLanguage(language, focus) {
    if (language !== "ja" && language !== "en") return;
    document.documentElement.lang = language;
    document.documentElement.dataset.language = language;
    Array.prototype.slice.call(document.querySelectorAll("[data-aria-ja][data-aria-en]")).forEach(function (node) {
      node.setAttribute("aria-label", node.dataset[language === "ja" ? "ariaJa" : "ariaEn"] || "");
    });
    languageButtons.forEach(function (button) {
      var isSelected = button.dataset.language === language;
      button.setAttribute("aria-pressed", isSelected ? "true" : "false");
      button.tabIndex = isSelected ? 0 : -1;
      button.setAttribute("aria-label", button.dataset[language === "ja" ? "ariaJa" : "ariaEn"] || button.textContent);
      if (isSelected && focus) button.focus();
    });
  }

  priorityButtons.forEach(function (button, index) {
    button.addEventListener("click", function () { selectPriority(button.dataset.priorityId, false); });
    button.addEventListener("keydown", function (event) {
      var target = index;
      if (event.key === "ArrowDown" || event.key === "ArrowRight") target = (index + 1) % priorityButtons.length;
      else if (event.key === "ArrowUp" || event.key === "ArrowLeft") target = (index - 1 + priorityButtons.length) % priorityButtons.length;
      else if (event.key === "Home") target = 0;
      else if (event.key === "End") target = priorityButtons.length - 1;
      else return;
      event.preventDefault();
      selectPriority(priorityButtons[target].dataset.priorityId, true);
    });
  });

  languageButtons.forEach(function (button, index) {
    button.addEventListener("click", function () { setLanguage(button.dataset.language, false); });
    button.addEventListener("keydown", function (event) {
      var target = index;
      if (event.key === "ArrowRight" || event.key === "ArrowDown") target = (index + 1) % languageButtons.length;
      else if (event.key === "ArrowLeft" || event.key === "ArrowUp") target = (index - 1 + languageButtons.length) % languageButtons.length;
      else if (event.key === "Home") target = 0;
      else if (event.key === "End") target = languageButtons.length - 1;
      else return;
      event.preventDefault();
      setLanguage(languageButtons[target].dataset.language, true);
    });
  });

  var requestedLanguage = new URLSearchParams(window.location.search).get("language");
  setLanguage(requestedLanguage === "en" ? "en" : "ja", false);
  if (selectedId) selectPriority(selectedId, false);
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
  --priority: #e4ba58;
  --decision: #75c8d5;
  --evidence: #72c996;
  --console-bg: #0d100e;
  --console-panel: #171c18;
  --console-deep: #121613;
  --console-line: #3a463d;
}
* { box-sizing: border-box; }
html[data-language="ja"] .lang-en,
html[data-language="en"] .lang-ja { display: none !important; }
body {
  margin: 0;
  background: var(--paper);
  color: var(--ink);
  font-family: "Segoe UI", Arial, sans-serif;
  line-height: 1.45;
}
.production-header {
  padding: 20px 24px 14px;
  background: var(--console-bg);
  border-bottom: 1px solid var(--console-line);
}
.production-title-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 24px;
  align-items: start;
  max-width: 1480px;
  margin: 0 auto;
}
.production-title-copy { min-width: 0; }
.production-title-copy h1 {
  margin: 0;
  font-size: clamp(28px, 3vw, 40px);
  line-height: 1.08;
  letter-spacing: -0.02em;
}
.production-deck {
  max-width: 58rem;
  margin: 8px 0 0;
  color: var(--muted);
  font-size: 14px;
}
.header-controls {
  display: grid;
  justify-items: end;
  gap: 10px;
}
.language-switch {
  display: inline-flex;
  border: 1px solid var(--console-line);
  background: var(--console-deep);
}
.language-switch button {
  min-height: 38px;
  padding: 7px 14px;
  border: 0;
  border-right: 1px solid var(--console-line);
  background: transparent;
  color: var(--muted);
  font: inherit;
  font-weight: 800;
}
.language-switch button:last-child { border-right: 0; }
.language-switch button[aria-pressed="true"] { background: var(--decision); color: #081012; }
.acceptance-state {
  display: flex;
  gap: 8px;
  align-items: baseline;
  color: var(--muted);
  font-size: 12px;
  text-transform: uppercase;
}
.acceptance-state strong { color: var(--priority); }
.current-state-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  max-width: 1480px;
  margin: 16px auto 0;
  border: 1px solid var(--console-line);
  background: var(--console-deep);
}
.current-state-strip > div {
  min-width: 0;
  padding: 8px 12px;
  border-right: 1px solid var(--console-line);
}
.current-state-strip > div:last-child { border-right: 0; }
.current-state-strip dt { color: var(--muted); font-size: 11px; font-weight: 800; text-transform: uppercase; }
.current-state-strip dd { margin: 2px 0 0; color: var(--ink); font-weight: 850; overflow-wrap: anywhere; }
.receipt-line {
  max-width: 1480px;
  margin: 8px auto 0;
  color: var(--muted);
  font-size: 12px;
  overflow-wrap: anywhere;
}
.production-page {
  min-width: 0;
  padding: 16px 24px 42px;
  background: var(--console-bg);
}
.priority-workspace {
  display: grid;
  grid-template-columns: minmax(280px, 29fr) minmax(400px, 42fr) minmax(280px, 29fr);
  gap: 12px;
  max-width: 1480px;
  margin: 0 auto;
  align-items: stretch;
}
@media (min-width: 1121px) {
  .priority-workspace { height: min(876px, calc(100vh - 324px)); min-height: 760px; }
}
.console-panel {
  min-width: 0;
  border: 1px solid var(--console-line);
  background: var(--console-panel);
  overflow: hidden;
}
.priority-lane { border-top: 3px solid var(--priority); }
.active-decision { border-top: 3px solid var(--decision); }
.evidence-inspector { border-top: 3px solid var(--evidence); }
.console-panel-head {
  position: relative;
  min-height: 84px;
  padding: 13px 16px 12px;
  border-bottom: 1px solid var(--console-line);
  background: var(--console-deep);
}
.console-panel-head p {
  margin: 0 0 5px;
  color: var(--muted);
  font: 700 10px/1.2 Consolas, "Courier New", monospace;
  letter-spacing: .08em;
}
.console-panel-head h2 { margin: 0; font-size: 20px; line-height: 1.2; }
.panel-hint {
  position: absolute;
  top: 15px;
  right: 15px;
  color: var(--muted);
  font: 700 11px/1.2 Consolas, "Courier New", monospace;
}
.priority-list {
  display: grid;
  max-height: 680px;
  overflow-y: auto;
  scrollbar-color: var(--priority) var(--console-deep);
}
.priority-row {
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr);
  gap: 10px;
  width: 100%;
  min-width: 0;
  min-height: 94px;
  padding: 13px 14px;
  border: 0;
  border-bottom: 1px solid var(--console-line);
  border-left: 3px solid transparent;
  background: transparent;
  color: var(--ink);
  text-align: left;
  font: inherit;
  cursor: pointer;
}
.priority-row:hover { background: #1c231e; }
.priority-row[aria-selected="true"] { border-left-color: var(--priority); background: #252116; }
.priority-empty-state { min-height: 180px; padding: 28px 20px; display: grid; align-content: center; gap: 10px; color: var(--muted); }
.priority-empty-state strong { color: var(--teal); font-size: 15px; }
.priority-empty-state p { margin: 0; line-height: 1.55; }
.priority-rank { color: var(--priority); font: 800 14px/1.4 Consolas, "Courier New", monospace; }
.priority-copy { display: grid; min-width: 0; gap: 5px; }
.priority-identity { color: var(--teal); font: 700 10px/1.3 Consolas, "Courier New", monospace; overflow-wrap: anywhere; }
.priority-copy strong { font-size: 14px; line-height: 1.35; overflow-wrap: anywhere; }
.priority-copy small { color: var(--muted); font-size: 11.5px; line-height: 1.4; overflow-wrap: anywhere; }
.priority-meta { display: flex; flex-wrap: wrap; gap: 5px 10px; color: var(--priority); font-size: 11px; font-weight: 800; }
.queue-note { margin: 0; padding: 11px 14px; color: var(--muted); font-size: 10.5px; line-height: 1.45; }
.decision-body, .evidence-body { padding: 18px; }
.decision-kicker {
  display: inline-block;
  margin: 0 0 12px;
  padding: 3px 8px;
  border: 1px solid var(--decision);
  color: var(--decision);
  font-size: 11px;
  font-weight: 800;
}
.decision-body h3 { margin: 0 0 10px; font-size: clamp(22px, 2.2vw, 32px); line-height: 1.2; overflow-wrap: anywhere; }
.decision-reason { margin: 0 0 18px; color: var(--muted); overflow-wrap: anywhere; }
.decision-grid, .evidence-grid, .provenance-grid { display: grid; gap: 0; margin: 0; }
.decision-grid > div, .evidence-grid > div, .provenance-grid > div {
  padding: 11px 0;
  border-top: 1px solid var(--console-line);
}
.decision-grid dt, .evidence-grid dt, .provenance-grid dt {
  color: var(--muted);
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
}
.decision-grid dd, .evidence-grid dd, .provenance-grid dd {
  margin: 4px 0 0;
  overflow-wrap: anywhere;
}
.evidence-grid dd small { display: block; margin-top: 3px; color: var(--muted); font: 11px/1.35 Consolas, "Courier New", monospace; overflow-wrap: anywhere; }
.evidence-status {
  display: inline-flex;
  margin-bottom: 12px;
  padding: 5px 9px;
  border: 1px solid var(--evidence);
  color: var(--evidence);
  font: 800 12px/1.2 Consolas, "Courier New", monospace;
  text-transform: uppercase;
}
.provenance-details { margin-top: 12px; border-top: 1px solid var(--console-line); }
.provenance-details summary { padding: 12px 0; color: var(--evidence); cursor: pointer; font-weight: 800; }
.provenance-grid { font-family: Consolas, "Courier New", monospace; font-size: 11px; }
.full-path, .hash-value { overflow-wrap: anywhere; word-break: normal; }
.receipt-id { margin: 14px 0 0; color: var(--muted); font-size: 11px; overflow-wrap: anywhere; }
.project-worksets {
  max-width: 1480px;
  margin: 16px auto 0;
  border: 1px solid var(--console-line);
  background: var(--console-panel);
}
.project-worksets > summary {
  display: grid;
  grid-template-columns: minmax(160px, auto) minmax(0, 1fr);
  gap: 12px;
  padding: 14px 16px;
  cursor: pointer;
  font-weight: 800;
}
.project-worksets > summary small { color: var(--muted); font-weight: 400; }
.workset-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; padding: 0 16px 16px; }
.workset-card { min-width: 0; padding: 14px; border: 1px solid var(--console-line); background: var(--console-deep); }
.workset-card h3 { margin: 0 0 10px; color: var(--teal); }
.workset-card dl { display: grid; gap: 8px; margin: 0; }
.workset-card dt { color: var(--muted); font-size: 10px; font-weight: 800; text-transform: uppercase; }
.workset-card dd { margin: 2px 0 0; font: 11px/1.4 Consolas, "Courier New", monospace; overflow-wrap: anywhere; }
.evidence-appendix {
  max-width: 1480px;
  margin: 16px auto 0;
  border: 1px solid var(--console-line);
  background: var(--console-deep);
}
.evidence-appendix > summary {
  display: grid;
  grid-template-columns: minmax(160px, auto) minmax(0, 1fr);
  gap: 12px;
  padding: 14px 16px;
  color: var(--ink);
  cursor: pointer;
  font-weight: 800;
}
.evidence-appendix > summary small { color: var(--muted); font-weight: 400; }
.appendix-content { display: grid; gap: 24px; padding: 0 16px 18px; }
.appendix-content section { min-width: 0; }
.noscript-notice {
  max-width: 1480px;
  margin: 0 auto 12px;
  padding: 10px 12px;
  border: 1px solid var(--priority);
  background: #252116;
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
  padding: 28px 32px 24px;
  background: #151914;
  border-bottom: 1px solid var(--line);
}
.frontpage-report {
  max-width: 1120px;
  margin: 0 auto;
}
.report-front-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(220px, 300px);
  gap: 24px;
  align-items: start;
}
.report-main { min-width: 0; }
.report-headline {
  max-width: 48rem;
  margin-bottom: 10px;
  color: var(--ink);
  font-size: 28px;
  font-weight: 800;
  line-height: 1.2;
}
.report-interpretation {
  max-width: 55rem;
  margin-bottom: 0;
  color: var(--muted);
  font-size: 15px;
}
.report-next {
  display: grid;
  gap: 8px;
  padding-top: 26px;
}
.report-next span {
  color: var(--yellow);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}
.report-primary-action,
.report-secondary-link {
  display: inline-flex;
  min-height: 36px;
  align-items: center;
  justify-content: center;
  padding: 7px 11px;
  border: 1px solid rgba(244, 241, 232, 0.24);
  border-radius: 6px;
  color: var(--ink);
  font-weight: 800;
  text-decoration: none;
}
.report-primary-action {
  background: rgba(217, 168, 78, 0.18);
  border-color: rgba(217, 168, 78, 0.55);
}
.report-secondary-link {
  background: rgba(102, 198, 166, 0.12);
}
.report-status-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0;
  margin: 18px 0 10px;
  padding: 9px 0;
  border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
}
.report-status-strip div {
  min-width: 0;
  padding: 0 14px;
  border-right: 1px solid rgba(244, 241, 232, 0.12);
  background: transparent;
}
.report-status-strip div:first-child { padding-left: 0; }
.report-status-strip div:last-child { border-right: 0; padding-right: 0; }
.report-status-strip dt {
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}
.report-status-strip dd {
  margin: 3px 0 0;
  color: var(--ink);
  font-size: 14px;
  font-weight: 800;
  overflow-wrap: anywhere;
}
.report-meta {
  max-width: 68rem;
  margin: 0;
  color: var(--muted);
  font-size: 12px;
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
.review-map-list {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 0;
  border-top: 1px solid var(--line);
  border-bottom: 1px solid var(--line);
  background: #151914;
}
.review-map-item {
  display: grid;
  grid-template-rows: auto auto 1fr;
  gap: 3px;
  min-height: 56px;
  padding: 8px 10px 8px 12px;
  border: 0;
  border-right: 1px solid rgba(244, 241, 232, 0.12);
  border-left: 3px solid transparent;
  color: var(--ink);
  text-decoration: none;
}
.review-map-item:last-child { border-right: 0; }
.review-map-item:hover {
  background: #1b211c;
}
.review-map-item.tone-green { border-left-color: var(--green); }
.review-map-item.tone-yellow { border-left-color: var(--yellow); }
.review-map-item.tone-red { border-left-color: var(--red); }
.review-map-item.tone-neutral { border-left-color: var(--teal); }
.review-map-item span {
  color: var(--muted);
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
}
.review-map-item strong {
  font-size: 14px;
  line-height: 1.1;
  overflow-wrap: anywhere;
}
.review-map-item small {
  margin: 0;
  color: var(--muted);
  font-size: 11px;
  line-height: 1.3;
}
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
  flex-wrap: wrap;
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
@media (max-width: 1120px) {
  .priority-workspace { grid-template-columns: 1fr; }
  .priority-lane, .active-decision, .evidence-inspector { min-height: auto; }
}
@media (max-width: 980px) {
  .report-front-grid { grid-template-columns: 1fr; }
  .report-next { padding-top: 0; }
  .overview-board, .top-kpis, .review-map-list, .review-stack-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .summary-grid, .grid-three { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .filter-panel { grid-template-columns: 1fr; }
}
@media (max-width: 640px) {
  .production-header { padding: 16px 14px 12px; }
  .production-title-row { grid-template-columns: 1fr; gap: 14px; }
  .header-controls { justify-items: start; }
  .current-state-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .current-state-strip > div:nth-child(2) { border-right: 0; }
  .current-state-strip > div:nth-child(-n+2) { border-bottom: 1px solid var(--console-line); }
  .production-page { padding: 12px 14px 30px; }
  .dashboard-nav { padding: 8px 14px; }
  .console-panel-head { min-height: 74px; padding: 11px 13px; }
  .priority-row { min-height: 82px; padding: 11px; }
  .decision-body, .evidence-body { padding: 14px; }
  .project-worksets > summary { grid-template-columns: 1fr; }
  .evidence-appendix > summary { grid-template-columns: 1fr; }
  .top-strip { padding: 22px 18px; }
  .page { padding: 18px; }
  .summary-grid, .grid-three, .overview-board, .top-kpis, .review-map-list, .review-stack-grid { grid-template-columns: 1fr; }
  .report-status-strip { grid-template-columns: 1fr; }
  .report-status-strip div {
    padding: 8px 0;
    border-right: 0;
    border-bottom: 1px solid rgba(244, 241, 232, 0.12);
  }
  .report-status-strip div:last-child { border-bottom: 0; }
  .disclosure > summary { grid-template-columns: auto 1fr; }
  .disclosure > summary span { grid-column: 2; }
  .detail-anchor-head { grid-template-columns: 1fr; }
  .detail-anchor-head .back-link { grid-column: 1; grid-row: auto; }
  h1 { font-size: 24px; }
  .report-headline { font-size: 22px; }
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
  .skip-link, .dashboard-nav, .filter-panel, .language-switch, script {
    display: none !important;
  }
  .top-strip, .dashboard-footer, .metric-card, .panel, .table-wrap, .checkpoint-card, .triage-card, .project-card, .action-card, .review-action-card, .locked-card, .review-map-item, .stack-card, .detail-anchor-panel {
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
  .overview-card {
    background: #ffffff;
    color: #000000;
    box-shadow: none;
  }
  .page {
    padding: 0;
  }
  .production-header, .production-page, .console-panel, .project-worksets, .evidence-appendix {
    background: #ffffff;
    color: #000000;
    border-color: #777777;
  }
  .production-page { padding: 0; }
  .priority-workspace { grid-template-columns: 1fr; }
  .priority-row, .console-panel-head { background: #ffffff; color: #000000; }
  .project-worksets:not([open]) > :not(summary) { display: block; }
  .evidence-appendix:not([open]) > :not(summary) { display: block; }
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
