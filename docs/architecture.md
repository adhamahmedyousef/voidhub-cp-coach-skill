# Architecture and evidence boundaries

The distributable skill lives under `skills/voidhub-cp-coach`. SKILL.md routes
only relevant references. UI metadata advertises the same capability.

The read client supports the two existing VoidHub v1 operations only. The
progress store owns learner JSON. Secret provisioning is a separate operator
tool. All three use Python's standard library; API keys never enter progress,
CLI arguments or output. Learner data and private credentials survive updates
because they are stored outside the installed skill.

The API controls authentication, publication visibility and distributed rate
limits. The client controls HTTPS origin, no redirects, bounded responses,
checksum/schema validation and local pacing. No client identity claim can
prevent a key holder from making requests outside the skill.

Progress integrity is deterministic. Correct topic selection, useful hints,
proof quality and genuine transfer are model judgments and need actual session
review. A schema validator cannot certify those judgments. No 100% accuracy claim.

The v1 progress format is documented in the bundled JSON Schema. The runtime
validator additionally enforces identity, monotonic assistance, repeat rules,
date requirements and derived mastery. Unknown versions fail without rewriting
data. Future changes require an explicit tested migration; no v2 migration is
invented for v1.

Local pacing locks and state locks use exclusive file creation; crashes leave a
lock for deliberate recovery. State replacement is atomic per file, with fsync
before replacement. Network filesystems that do not support these guarantees
are outside v1; use a local learner directory.

Repository tests never use production keys or claims of real contest acceptance.
No license has been selected yet; choose it before public distribution. The
project is not licensed for reuse merely because a repository is public.
