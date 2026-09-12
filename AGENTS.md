/
AGENTS.md


LudoX — Codex instructions
These instructions apply to the whole repository unless a more specific
AGENTS.md exists in a subdirectory.

1. Approved specifications are read-only
Any Markdown file containing:

STATUS: APPROVED SPECIFICATION — READ ONLY

is an authoritative LudoX specification.

During an implementation task:

DO NOT modify an approved specification.

DO NOT change the specification to match the current code.

DO NOT silently implement behavior that contradicts the specification.

DO NOT resolve TBD or QUESTION markers on your own.

DO NOT treat a TBD or QUESTION as permission to choose an implementation.

If the requested implementation conflicts with an approved specification:

stop before making the conflicting change;

identify the exact specification file and section involved;

explain the conflict briefly;

propose the smallest specification change needed;

wait for explicit user approval before changing the specification or
implementing behavior that contradicts it.

A user request that explicitly asks to update a named specification/document
counts as approval to edit only the requested documentation.

2. Specification status and implementation status are separate
Specification files may contain both:

STATUS: APPROVED SPECIFICATION — READ ONLY

IMPLEMENTATION: NOT IMPLEMENTED

IMPLEMENTATION: PARTIALLY IMPLEMENTED

IMPLEMENTATION: IMPLEMENTED

IMPLEMENTATION describes the current software state. It does not make the
specification editable.

3. Current protected specifications
The following files are specifications and should normally be treated as
read-only during implementation:

docs/ARCHITECTURE.md

docs/ORGANIZATIONS.md

docs/EVENTS.md

docs/MODULES.md

docs/CONFIGURATION.md

docs/LENDING.md

docs/DATABASE.md

docs/OPERATION.md

The header inside each file is the authoritative protection signal. Future
specification files should use the same header.

4. Prefer simple and readable solutions
LudoX is intended to be installable and configurable by people who are not
system administrators or software developers.

When multiple solutions satisfy the same approved requirements, prefer the
one that is:

easier to understand;

easier to configure from the UI;

easier to inspect in plain-text configuration files;

easier to diagnose and recover manually;

based on familiar identifiers and concepts.

Do not introduce UUIDs, hashes, opaque generated identifiers, hidden mapping
layers, additional configuration files, registries, or speculative
abstractions only to prepare for hypothetical future requirements.

Such mechanisms are acceptable only when an approved requirement or a
concrete technical constraint makes the simpler solution insufficient.

Human-readable configuration is a project feature, not an implementation
detail.

5. Keep implementation scope narrow
Implement only the requested feature.

In particular:

do not perform unrelated refactors;

do not migrate the database schema unless explicitly requested;

do not implement future architecture merely because it is described in
the specifications;

do not add speculative abstractions for features that are not part of the
current task;

preserve existing behavior unless the task explicitly changes it.

Example: implementing database export/backup must not trigger implementation
of the future database schema described in docs/DATABASE.md.

6. Database changes require explicit scope
Before changing database tables, relationships, migrations, or schema
versioning, verify that the current task explicitly requires a schema change.

If it does not, leave the schema unchanged.

When a task only needs to read, back up, export, or inspect the current
database, prefer an implementation that works with the existing schema.

7. Git and commits
Commits should be frequent, small, and logically coherent.

For implementation tasks:

divide the work into meaningful implementation steps when possible;

create a separate commit for each coherent sub-part of the task;

do not artificially combine unrelated changes into one large commit;

do not create trivial commits for individual lines or mechanical edits;

each commit should represent a meaningful, reviewable step;

keep every commit focused on the current issue or requested task;

never include unrelated pre-existing working-tree changes in a commit;

review the relevant diff before each commit;

run the relevant tests before committing a completed step;

whenever practical, leave the repository in a working state after each
commit;

use concise Conventional Commit style messages when appropriate.

Every commit message must include the GitHub issue number that the commit
belongs to. Use this format when practical:

feat: add organization context (#15)
docs: document migration workflow (#20)
test: cover organization selection (#15)

The issue reference is required in addition to the Conventional Commit type.
Do not use `fixes`, `closes`, or equivalent automatic-closing keywords unless
the user explicitly asks to close the issue.

When the task clearly identifies an issue, use that issue number. If the
appropriate issue is not otherwise clear, use the issue associated with the
current working branch. For example, work on
`feature/15-organizations-context` defaults to `#15`.

If neither the task nor the branch identifies an issue unambiguously, ask the
user before creating the commit rather than inventing an issue reference.

Typical natural commit boundaries include:

database migration;

persistence or service layer;

configuration or context handling;

UI implementation;

tests for a completed functional part;

documentation explicitly requested as part of the task.

The exact number of commits is not predetermined. Prefer natural
implementation boundaries over either one large commit or excessive
micro-commits.

Unless the user explicitly requests otherwise:

never push;

never close GitHub issues;

never create or switch branches.

If the user explicitly requests commits, create the appropriate local commits
following the rules above and report their hashes at the end.

8. Documentation during implementation
Implementation tasks may update ordinary implementation documentation when
needed, but protected specifications must not be changed unless explicitly
requested.

If implementation reveals a possible specification improvement, report it
separately instead of editing the specification.

9. Completion report
At the end of an implementation task, report:

files changed;

tests/checks performed;

commits created, with hash and message when commits were requested;

whether any approved specification was affected;

any specification conflict or unresolved decision discovered;

whether a push was performed.

If no approved specification was modified, state that explicitly.

10. Preferred implementation workflow
Before coding:

read this AGENTS.md;

identify the relevant approved specification(s);

read only the sections needed for the task;

confirm that the requested change does not conflict with them;

divide the work into natural, reviewable implementation steps;

implement the smallest coherent change for the current step;

run the relevant tests/checks;

create a local commit when commits were requested;

continue with the next coherent step;

run the complete relevant test suite before reporting completion.

When unsure whether a decision belongs to implementation or specification,
ask the user instead of deciding silently.