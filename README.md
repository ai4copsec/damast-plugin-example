# damast-plugin-example

A minimal, standalone template for an **installable** [damast](https://github.com/simula/damast)
plugin package: a `PipelineElement` transformer that lives in its own Python package and is
discovered by damast via the `damast.transformers` entry-point group - rather than being copied
into every project that wants to use it.

This complements the *local, ad-hoc* plugin approach (a loose `*.py` file picked up via the
`DAMAST_PLUGIN_PATH` environment variable), which is documented directly in damast itself
(`damast plugins`, `docs/cli.rst`) and doesn't need a package like this one.

## What's here

- [`src/damast_plugin_example/transformers.py`](src/damast_plugin_example/transformers.py) -
  `MMSIPatternClassifier`, an example `PipelineElement` that classifies a MMSI column by
  matching it against patterns from a user-supplied mapping file. It adds a
  `<column>_category` column, e.g. `mmsi_category`, looking up each MMSI's longest matching
  pattern and falling back to a configurable `default_category` (`"unknown"` by default) when
  none match. It never drops rows.
- [`examples/mmsi_categories.yaml`](examples/mmsi_categories.yaml) - an example mapping file
  covering every fixed-pattern category defined in
  [Recommendation ITU-R M.585-10](https://www.itu.int/dms_pubrec/itu-r/rec/m/R-REC-M.585-10-202604-I!!PDF-E.pdf)
  (04/2026), "Assignment and use of identities in the maritime mobile service" - e.g. `111` for
  Search And Rescue aircraft, `98` for craft associated with a parent ship, `970` for an
  AIS-SART, and the single reserved, full 9-digit `009990000` all-coast-stations identity. A
  plain ship station has no such fixed pattern (Annex 1, Section 1) and so is left unmapped,
  falling back to `default_category`.
- [`pyproject.toml`](pyproject.toml) - registers `MMSIPatternClassifier` under the
  `damast.transformers` entry-point group:

  ```toml
  [project.entry-points."damast.transformers"]
  MMSIPatternClassifier = "damast_plugin_example.transformers:MMSIPatternClassifier"
  ```

- [`tests/test_transformers.py`](tests/test_transformers.py) - unit tests for the transformer
  itself, plus a test that it is actually discoverable as a damast plugin once installed
- [`examples/run_pipeline.py`](examples/run_pipeline.py) - builds and saves a
  `DataProcessingPipeline` that uses `MMSIPatternClassifier` with that mapping file

## Using this as a template

To adapt this for your own transformer(s):

1. Rename the package (`damast-plugin-example` / `damast_plugin_example`) to something specific
   to your project
2. Replace `MMSIPatternClassifier` in `transformers.py` with your own `PipelineElement`
   subclass(es)
3. Update the `[project.entry-points."damast.transformers"]` table in `pyproject.toml` to list
   every class you want discoverable - one `name = "module:ClassName"` entry per transformer
4. Update `dependencies` in `pyproject.toml` to match what your transformer(s) actually need

## Try it out

```bash
# from this directory
pip install -e ".[test]"

# MMSIPatternClassifier is now discoverable, without any further configuration
damast plugins
# MMSIPatternClassifier: damast_plugin_example.transformers:MMSIPatternClassifier

python -c "from damast.plugins import MMSIPatternClassifier; print(MMSIPatternClassifier)"

pytest
```

Build and apply a pipeline that uses it:

```bash
python examples/run_pipeline.py
# Saved pipeline to pipelines/classify-mmsi.damast.ppl

damast process --input-data <your-data>.parquet --pipeline pipelines/classify-mmsi.damast.ppl
```

Because `MMSIPatternClassifier` comes from an installed distribution, the saved pipeline records
the distribution name and version (not a file path) under `requires` - so loading it elsewhere
with a missing or mismatched version fails with an actionable message instead of a bare import
error.

Note that the mapping file's *path* - not its content - is what gets saved as a pipeline
parameter, and it is re-read every time the pipeline is loaded. Keep it alongside the pipeline
(or point `mapping_file` at an absolute, shared location) so it is still there when the pipeline
is used elsewhere.

## License

BSD 3-Clause, see [LICENSE](LICENSE).

## Copyright

Copyright (c) 2026 [Simula Research Laboratory, Oslo, Norway](https://www.simula.no/research/research-departments)


## Acknowledgments

The development of these examples are part of the EU-project [AI4COPSEC](https://ai4copsec.eu) which receives funding from the Horizon Europe framework programme under Grant Agreement N. 101190021.
