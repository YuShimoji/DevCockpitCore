# Validation

Use a real Python 3.11+ interpreter with `PYTHONPATH=src`. On this host, the
verified interpreter path is:

```powershell
C:\Users\thank\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe
```

Avoid the WindowsApps `python.exe` stub.

## Install

```powershell
python -m pip install -e .
```

Editable install is optional for local verification because the repo supports
`PYTHONPATH=src`.

## Development server

```text
NOT_AVAILABLE_IN_THIS_REPO
```

DevCockpitCore has no web server or dev-server loop. Dashboard and prototype
outputs are static local HTML files.

## Build

```powershell
python -m compileall src tests
```

## Test

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover
```

## Lint

```text
NOT_AVAILABLE_IN_THIS_REPO
```

No dedicated linter is configured in `pyproject.toml`.

## Preview

```powershell
Start-Process .\samples\dashboard\layout_research\devcockpitcore_layout_prototype.html
Start-Process .\samples\dashboard\devcockpitcore_dashboard.html
```

The layout prototype is the active review surface. The generated production
dashboard is evidence, not the next design target.

## Screenshot capture

```text
NOT_AVAILABLE_IN_THIS_REPO
```

Prior handoffs used Playwright set-content smoke checks, but no repo-local
screenshot command is configured.

## Artifact generation

```powershell
$env:PYTHONPATH = "src"
python -m dev_cockpit.validation_pack --default --output artifacts/review/2026-07-10-rekickstart-validation-pack.json --pretty
python -m dev_cockpit.dashboard --output samples/dashboard/devcockpitcore_dashboard.html
```

The validation-pack command is the material evidence command selected for the
2026-07-10 re-kickstart BUILD turn.

## Validation rule

A validation entry is valid only when it includes:

- command
- date
- result
- output path or log summary

## Re-kickstart readback

All template placeholders were replaced with DevCockpitCore-specific commands or
`NOT_AVAILABLE_IN_THIS_REPO` after reading `README.md`, `pyproject.toml`,
`docs/runtime-state.md`, the active layout handoff, and validation-pack
references.
