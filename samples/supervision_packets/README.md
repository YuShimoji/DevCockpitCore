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

The manifest and every report are strict, content-bound inputs. Editing a
report without updating the explicit manifest hash fails closed. The generator
does not scan directories for a newest report, infer reports from conversation
history, write to sibling repositories, schedule work, or make actions
executable. Global rank is attention/review priority only.
