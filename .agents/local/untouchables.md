# Untouchables

## Registry source of truth

What it is and where: root-level `base/`, `docs/`, `examples/`, and `bin/` are the registry content for budai itself.

Why it is there: consumer repos eventually receive this content through `librarian sync`; this repo is the upstream source.

What you should NOT do: do not create a second manually maintained copy of root `base/` inside `.agents/base/` as part of ordinary edits.

What you should do instead: use `registry-source: self` in `.agents/manifest.yaml` until task `011` defines sync behavior.
