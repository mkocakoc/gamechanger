# GameChanger Product Roadmap

## Vision
GameChanger helps older gaming PCs stay playable with safe, reversible Windows optimizations.

## Principles
- Safety first: no risky registry hacks by default.
- Reversible changes: every tweak has rollback.
- Transparent actions: logs show each command and result.
- User control: no always-on background service.

## Phase 1 - Open Source Foundation
- [x] Basic GUI app and one-click optimization
- [x] LoL/CS2 helper actions
- [x] HDD mode and cache warm-up
- [ ] Licensing, contribution, security policy
- [ ] CI checks (lint, syntax, package smoke test)
- [ ] Versioning and release notes process

## Phase 2 - Safe Tweak Engine
- [ ] Introduce tweak catalog with metadata
- [ ] Add "apply", "dry-run", and "rollback" per tweak
- [ ] Add profile system: "LoL", "CS2", "General Desktop"
- [ ] Persist last state to JSON for undo after reboot

## Phase 3 - Better UX and Reliability
- [ ] Action progress panel with statuses
- [ ] Better error messaging and privilege checks
- [ ] Background process snapshot before and after tweak
- [ ] Optional startup check for reverted settings

## Phase 4 - Distribution
- [ ] Signed releases (if certificate available)
- [ ] Portable zip and installer package
- [ ] GitHub Releases with checksums
- [ ] In-app "Check for update" (manual only)

## Phase 5 - Community and Growth
- [ ] Benchmark contribution guide
- [ ] Known hardware profiles (e.g., i7-7700K + GTX 1070)
- [ ] Localization (TR/EN)
- [ ] Issues triage automation
