# bootstrap_archive (Archived)

## Purpose
- This folder keeps historical bootstrap batch scripts for audit/reference.
- These scripts are **not** part of the current recommended setup flow.

## Safety Warning
- Do not rerun these scripts blindly on an existing repository.
- They may overwrite generated files (`README.md`, `.gitignore`, scaffolded project files).
- They may assume old paths, old dependencies, or one-time initialization states.

## Usage Rule
- Default: **read-only reference**.
- If execution is absolutely required:
  1. Run only in a disposable clone/sandbox.
  2. Review script contents line-by-line first.
  3. Capture diffs before applying to main branches.
