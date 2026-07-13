# Project Brief

## Project name

DevCockpitCore

## Purpose

DevCockpitCore is a cross-project development supervision substrate. It
produces local, read-only evidence that helps a supervisor or later agent resume
work without guessing repository state.

## Primary users

- The project owner reviewing development state across multiple local repos.
- Codex agents that need a compact restart surface before taking a reversible
  next action.

## User language

Japanese is the primary user language. Repository docs currently use English for
technical continuity.

## Core value

Turn scattered repo state, validation outputs, warnings, handoffs, and review
artifacts into bounded supervision evidence without expanding execution
authority.

## Product surface

- Standard-library Python package `dev_cockpit`.
- CLI/status producers, report normalizer, gate classifier, validation pack,
  cross-project smoke, bounded C3/C4 probes.
- Static local dashboard and review-only layout prototype under `samples/`.

## Non-goals

- General execution loop, scheduler, daemon, or arbitrary command runner.
- Web server, database, credentials, telemetry, external notifications, or
  target-repository writeback.
- Project-specific readiness work outside adapters, snapshots, or review
  evidence.

## Current product hypothesis

A queue-led Priority Review Console can make DevCockpitCore more useful than a
card-grid dashboard by putting current state, ordered warning review, active
decision context, and adjacent evidence into one static local review surface.

## Re-kickstart rule

BUILD turns must leave material evidence: implementation diff, validation log,
generated artifact, screenshot, or reproducible probe. Documentation records
completed work, but does not replace material evidence.
