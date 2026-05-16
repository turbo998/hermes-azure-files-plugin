# Contributing

Thanks for your interest in `hermes-azure-files-plugin`! Pull requests are very
welcome.

## Ground rules

1. Open an issue first for non-trivial changes (new tools, mount backends,
   breaking config) so we can align on the approach.
2. Keep PRs focused — one logical change per PR.
3. Use [Conventional Commits](https://www.conventionalcommits.org/) for commit
   messages (`feat:`, `fix:`, `docs:`, `test:`, `chore:` ...).
4. **All tests must pass** before a PR can be merged:

   ```bash
   pip install -e .[dev]
   pytest -q
   ```

5. Add tests for any new behavior. Prefer mocking the Azure SDK / subprocess
   layer so the suite stays runnable without a real Azure account.
6. Do not commit secrets, account keys, SAS tokens, or `connection_string`
   values.

## Code style

- Python 3.11+.
- Type hints on all public functions.
- Validate any user-controlled string that ends up in a shell command.

## Releasing

Maintainer-only. Bump version in `pyproject.toml`, update `CHANGELOG.md`, tag
`vX.Y.Z`, and publish a GitHub release.
