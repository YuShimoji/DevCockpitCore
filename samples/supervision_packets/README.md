# Supervision Packet Samples

This directory contains deterministic, non-live fixture evidence for
`cross_project_supervision_packet.v1`.

| Path | Role |
| --- | --- |
| `task_report_manifest_v1.json` | Explicit report allowlist and SHA-256 bindings. |
| `reports/*.txt` | Four fictional AGENT_REPORT fixtures across two projects and multiple threads/lanes. |
| `cross_project_supervision_packet_v1.json` | Machine-readable global queue and project worksets. |
| `cross_project_supervision_packet_v1.md` | Human-readable review projection. |

Regenerate deterministically from the repository root:

```powershell
$env:PYTHONPATH = "src"
python -m dev_cockpit.supervision_packet `
  --manifest samples/supervision_packets/task_report_manifest_v1.json `
  --output-json samples/supervision_packets/cross_project_supervision_packet_v1.json `
  --output-markdown samples/supervision_packets/cross_project_supervision_packet_v1.md `
  --pretty
```

Render the accepted Priority Review Console with packet tasks:

```powershell
python -m dev_cockpit.dashboard `
  --supervision-packet samples/supervision_packets/cross_project_supervision_packet_v1.json
```

The manifest and every report are strict, content-bound inputs. Hashes bind
canonical UTF-8 LF bytes; a Windows CRLF checkout is normalized to LF before
hashing, while invalid UTF-8, bare carriage returns, and substantive edits fail
closed. The generator does not scan directories for a newest report, infer
reports from conversation history, write to sibling repositories, schedule
work, or make actions executable. Global rank is attention/review priority
only.

Canonical v6.5 ROUTE identity round-trips through `thread`, `lane`, `slice`,
and `artifact`; existing legacy fixtures continue through their historical
aliases. Conflicting explicit aliases fail closed. Loading a generated packet
also recomputes bindings, task IDs, collection membership, ranks, worksets,
coverage, attention policy, and observer-only scope. This remains deterministic
non-live fixture evidence.
