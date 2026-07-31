# Memoryledger documentation

The site is authored in MyST Markdown and built with Sphinx. Install the
package and documentation dependencies from the repository root:

```bash
python -m pip install -e .
python -m pip install -r docs/requirements.txt
```

For an editable development environment, `python -m pip install -e ".[dev]"`
installs the same documentation dependencies through the project optional
dependency group.

Build HTML with warnings treated as errors:

```bash
python -m sphinx -W --keep-going -b html docs docs/_build/html
```

The standard wrapper is equivalent:

```bash
cd docs
make html
```

`docs/_build/` is generated output. The CLI reference is generated from the
command catalog and Typer tree; edit its generator and metadata instead of the
generated page.

The repository includes `.readthedocs.yaml` for the supported Read the Docs
build, using the same `docs/requirements.txt` and `docs/conf.py` configuration.
