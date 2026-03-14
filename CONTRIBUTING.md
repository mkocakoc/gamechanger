# Contributing to GameChanger

Thanks for contributing.

## Development setup
1. Install Python 3.10+.
2. Install dependencies:
   - `py -m pip install -r requirements.txt`
3. Run app:
   - `py src\\main.py`

## Pull request checklist
- Keep changes focused and small.
- Keep defaults safe and reversible.
- Add or update docs when behavior changes.
- Ensure syntax check passes:
  - `py -m py_compile src\\main.py`

## Coding guidelines
- Prefer clear function names and simple control flow.
- Avoid hidden side effects.
- Log meaningful action results for users.

## Commit format
- `feat: ...` for new functionality
- `fix: ...` for bug fixes
- `docs: ...` for documentation updates
- `chore: ...` for maintenance changes
