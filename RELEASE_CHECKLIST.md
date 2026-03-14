# Release Checklist

## Pre-release
- [ ] Version bumped in src/version.py
- [ ] Changelog/release notes drafted
- [ ] All scenario steps completed or intentionally deferred
- [ ] CI is green on main

## Quality
- [ ] Manual smoke test on Windows (app launch, optimize, rollback, diagnostics)
- [ ] Dry-run and rollback verified
- [ ] No new errors in src/main.py, src/tweaks_engine.py, src/observability.py

## Build
- [ ] Run build_exe.bat
- [ ] dist/GameChanger.exe created
- [ ] dist/SHA256SUMS.txt created
- [ ] Optional signing validated (if certificate available)

## Publish (GitHub Release)
- [ ] Create tag (example: v0.5.0)
- [ ] Create GitHub Release from tag
- [ ] Attach GameChanger.exe and SHA256SUMS.txt
- [ ] Paste release notes

## Post-release
- [ ] Verify download and checksum from release page
- [ ] Announce release and ask for diagnostics-backed feedback
