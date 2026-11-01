# Public repository content

Keep product documentation, build instructions, architecture, security boundaries,
generic configuration examples, and reproducible tests in this repository.

Keep machine inventories, personal absolute paths, production origin addresses,
administration access instructions for a real installation, session transcripts,
raw logs, screenshots containing accounts, and deployment receipts outside Git.
Use `example.com`, `example.test`, `example.invalid`, documentation IP ranges,
temporary directories and generated test identities for examples and fixtures.

Public product endpoints and verification public keys may be required for the
application to work. Review their purpose before changing them; do not weaken
TLS, signature verification or allowlists to make examples easier to run.
Read private configuration through explicit local settings or environment
variables. Do not add real credentials or deployment-specific defaults.

Before a commit or PR, inspect the complete diff, newly tracked files, metadata,
test fixtures and documentation. Summarize validation commands, results and
limitations without copying private paths or raw operational records.
Gitignore does not remove tracked files or earlier commits. History, tags,
release artifacts and PR references require a separate review.
