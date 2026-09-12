# LudoX — Codex instructions

These instructions apply to the whole repository unless a more specific
`AGENTS.md` exists in a subdirectory.

## 1. Approved specifications are read-only

Any Markdown file containing:

> **STATUS: APPROVED SPECIFICATION — READ ONLY**

is an authoritative LudoX specification.

During an implementation task:

- DO NOT modify an approved specification.
- DO NOT change the specification to match the current code.
- DO NOT silently implement behavior that contradicts the specification.
- DO NOT resolve `TBD` or `QUESTION` markers on your own.
- DO NOT treat a `TBD` or `QUESTION` as permission to choose an implementation.

If the requested implementation conflicts with an approved specification:

1. stop before making the conflicting change;
2. identify the exact specification file and section involved;
3. explain the conflict briefly;
4. propose the smallest specification change needed;
5. wait for explicit user approval before changing the specification or
   implementing behavior that contradicts it.

A user request that explicitly asks to update a named specification/document
counts as approval to edit only the requested documentation.

## 2. Specification status and implementation status are separate

Specification files may contain both:

- `STATUS: APPROVED SPECIFICATION — READ ONLY`
- `IMPLEMENTATION: NOT IMPLEMENTED`
- `IMPLEMENTATION: PARTIALLY IMPLEMENTED`
- `IMPLEMENTATION: IMPLEMENTED`

`IMPLEMENTATION` describes the current software state. It does not make the
specification editable.

## 3. Current protected specifications

The following files are specifications and should normally be treated as
read-only during implementation:

- `docs/ARCHITECTURE.md`
- `docs/ORGANIZATIONS.md`
- `docs/EVENTS.md`
- `docs/MODULES.md`
- `docs/CONFIGURATION.md`
- `docs/LENDING.md`
- `docs/DATABASE.md`
- `docs/OPERATION.md`

The header inside each file is the authoritative protection signal. Future
specification files should use the same header.

## 4. Prefer simple and readable solutions

LudoX is intended to be installable and configurable by people who are not
system administrators or software developers.

When multiple solutions satisfy the same approved requirements, prefer the
one that is:

- easier to understand;
- easier to configure from the UI;
- easier to inspect in plain-text configuration files;
- easier to diagnose and recover manually;
- based on familiar identifiers and concepts.

Do not introduce UUIDs, hashes, opaque generated identifiers, hidden mapping
layers, additional configuration files, registries, or speculative
abstractions only to prepare for hypothetical future requirements.

Such mechanisms are acceptable only when an approved requirement or a
concrete technical constraint makes the simpler solution insufficient.

Human-readable configuration is a project feature, not an implementation
detail.

## 5. Keep implementation scope narrow

Implement only the requested feature.

In particular:

- do not perform unrelated refactors;
- do not migrate the database schema unless explicitly requested;
- do not implement future architecture merely because it is described in
  the specifications;
- do not add speculative abstractions for features that are not part of the
  current task;
- preserve existing behavior unless the task explicitly changes it.

Example: implementing database export/backup must not trigger implementation
of the future database schema described in `docs/DATABASE.md`.

## 6. Database changes require explicit scope

Before changing database tables, relationships, migrations, or schema
versioning, verify that the current task explicitly requires a schema change.

If it does not, leave the schema unchanged.

When a task only needs to read, back up, export, or inspect the current
database, prefer an implementation that works with the existing schema.

## 7. Documentation during implementation

Implementation tasks may update ordinary implementation documentation when
needed, but protected specifications must not be changed unless explicitly
requested.

If implementation reveals a possible specification improvement, report it
separately instead of editing the specification.

## 8. Completion report

At the end of an implementation task, report:

- files changed;
- tests/checks performed;
- whether any approved specification was affected;
- any specification conflict or unresolved decision discovered.

If no approved specification was modified, state that explicitly.

## 9. Preferred implementation workflow

Before coding:

1. read this `AGENTS.md`;
2. identify the relevant approved specification(s);
3. read only the sections needed for the task;
4. confirm that the requested change does not conflict with them;
5. implement the smallest coherent change;
6. run the relevant tests/checks;
7. report the result without editing approved specifications.

When unsure whether a decision belongs to implementation or specification,
ask the user instead of deciding silently.
