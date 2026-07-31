# Release documentation gates

Before release:

1. Regenerate and check the CLI reference.
2. Build Sphinx HTML with warnings as errors.
3. Validate the package version and declared Ledgercore range.
4. Validate changelog freshness through releaseledger.
5. Build a wheel and, when possible, verify that documented public modules
   import from the installed artifact.

Documentation changes do not introduce a hosted deployment or a new toolchain;
the repository's existing test, Ruff, mypy, and Sphinx commands remain the
release evidence.
