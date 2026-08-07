# Contributing

Use a short-lived branch, keep changes scoped, update relevant documentation, and include tests where behavior changes. Before review, run `make lint`, `make test`, and `make validate` as those targets become implemented.

Commits must not contain secrets, generated dependencies, Terraform state, or unrelated changes. Architecture-impacting decisions should be recorded in `docs/adr/`.
