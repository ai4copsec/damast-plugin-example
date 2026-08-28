"""
Build and save a damast pipeline that uses the MMSIPatternClassifier plugin from this package.

Unlike a local, ad-hoc plugin file on DAMAST_PLUGIN_PATH, nothing needs to be configured at
runtime here - once damast-plugin-example is installed (`pip install -e .`),
MMSIPatternClassifier is discoverable via `damast.plugins` like any transformer built into
damast itself.

Usage:
    python examples/run_pipeline.py
    damast process --input-data <data.parquet> --pipeline pipelines/classify-mmsi.damast.ppl
"""
from pathlib import Path

from damast.core.dataprocessing import DataProcessingPipeline
from damast.plugins import MMSIPatternClassifier

mapping_file = Path(__file__).parent / "mmsi_categories.yaml"

pipeline = DataProcessingPipeline(name="classify-mmsi", base_dir=".")
pipeline.add("Classify mmsi",
             # a MMSI matching none of the special-purpose patterns in mapping_file is,
             # per Rec. ITU-R M.585-10 Annex 1 Section 1, an ordinary ship station
             MMSIPatternClassifier(mapping_file=mapping_file, default_category="ship"),
             name_mappings={"x": "mmsi"})

pipeline_path = pipeline.save("pipelines")
print(f"Saved pipeline to {pipeline_path}")
