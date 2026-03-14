# GameChanger Step-by-Step Product Scenario

This file is the execution script for turning GameChanger into a free GitHub-ready product.

## Step 1 - Product foundation (current)
- [x] Add license
- [x] Add contribution guide
- [x] Add security policy
- [x] Add roadmap
- [ ] Add CI workflow
- [ ] Normalize README for product messaging

Exit criteria:
- Repo can be shared publicly with clear legal and contribution rules.

## Step 2 - Tweak engine refactor
- [x] Move tweak actions from UI layer into a dedicated engine module
- [x] Standardize tweak schema: id, label, safety_level, requires_admin, rollback
- [x] Add dry-run mode and result object
- [x] Keep JSON state for rollback

Exit criteria:
- UI only orchestrates; engine owns behavior and rollback logic.

## Step 3 - Safe profiles
- [x] Add profile presets: LOL_SAFE, CS2_HDD, DESKTOP_LIGHT
- [x] Add one-click apply and one-click rollback per profile
- [x] Add profile validation and warnings

Exit criteria:
- Users can apply known-good bundles safely.

## Step 4 - Observability
- [x] Add structured log file in logs/ with timestamps
- [x] Add before/after snapshots for CPU, RAM, process count
- [x] Add export diagnostics button

Exit criteria:
- Users can share evidence when opening issues.

## Step 5 - Packaging quality
- [x] Embed app version in UI and EXE metadata
- [x] Add optional icon and signed artifact support
- [x] Add checksums for release artifacts

Exit criteria:
- Reproducible build with release integrity checks.

## Step 6 - Code architecture optimization
- [x] Centralize app path handling
- [x] Reduce duplicated game directory logic in engine
- [x] Remove nested action threading in optimize flow

Exit criteria:
- Core flows remain stable with cleaner architecture and less duplication.

## Step 7 - Community release loop
- [x] Add issue templates and bug report format
- [x] Add release checklist
- [ ] Publish v0.1.0 on GitHub Releases

Exit criteria:
- Public users can install, test, and report issues easily.

---

## Working mode
- Complete one step fully before moving on.
- Ship small, stable increments.
- Never add unsafe tweaks without rollback support.
