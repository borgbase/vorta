# Contributing to Vorta

Thanks for your interest in contributing to Vorta.

## How to contribute

1. **Open an issue first.** Before writing any code, please [open an issue](https://github.com/borgbase/vorta/issues) describing the bug or feature. This lets us discuss the approach before you invest time on a PR.

2. **PRs require an approved issue.** Pull requests are only accepted for issues that have been triaged and approved. If you open a PR without a corresponding issue, you'll be asked to create one first.

3. **Prefer detailed feature requests over PRs.** A well-written feature request — with motivation, use cases, and expected behavior — is often more valuable than a code contribution. It helps us design the feature to fit the project's architecture and long-term direction.

4. **Join the discussion.** For general questions and ideas, use [GitHub Discussions](https://github.com/borgbase/vorta/discussions). For bug reports, [open an issue](https://github.com/borgbase/vorta/issues/new/choose).

## AI-generated content

All issues, PRs, and comments must be submitted by humans who are fully responsible for their content.

AI-assisted code contributions are welcome, but they must meet the same quality bar as any other contribution: complete, tested, and ready to merge. Partial or rough drafts that need significant rework will be closed.

The following are explicitly not welcome:

- **AI-generated comment replies.** They add noise, not value. Maintainers can tell and will disregard them.
- **AI-generated issues.** Issues must demonstrate that the reporter actually experienced the bug or has a genuine use case. Speculative "I noticed this might be a problem" issues will be closed.
- **Bulk cosmetic PRs.** Submitting many small PRs (typo fixes, docstring additions, comment rewording) that appear AI-generated will be closed. One thoughtful contribution is worth more than ten cosmetic ones.

If you are asked a follow-up question on your PR, respond with specifics about your code. Inability to explain your own changes signals the PR wasn't genuinely authored and it will be closed.

## Development

```bash
uv sync              # Install dependencies
make test            # Run all tests (via nox, multiple Borg versions)
make test-unit       # Run unit tests only
make lint            # Run linters (ruff)
```

See [CLAUDE.md](../CLAUDE.md) for the full project structure and architecture overview, and our [contributor guide](https://vorta.borgbase.com/contributing/) for additional details on coding, translation, and packaging.

*By submitting a contribution, you provide it under the terms of the [project license](../LICENSE.txt) and affirm the [Developer Certificate of Origin](https://developercertificate.org/).*
