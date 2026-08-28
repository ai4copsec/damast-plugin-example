import importlib.metadata

import polars
import pytest
from damast.core.dataframe import AnnotatedDataFrame
from damast.core.dataprocessing import DataProcessingPipeline
from damast.core.metadata import DataSpecification, MetaData
from damast.core.transformations import PluginManager

from damast_plugin_example.transformers import MMSIPatternClassifier, load_pattern_rules

MAPPING = {
    "111": "SAR",
    "98": "craft-associated-with-parent-ship",
    "99": "aid-to-navigation",
    "00": "coast-station",
    "009990000": "all-coast-stations",
    "0": "group-ship-call",
}


@pytest.fixture
def mapping_file(tmp_path):
    path = tmp_path / "mmsi_categories.yaml"
    path.write_text("\n".join(f'"{pattern}": {category}' for pattern, category in MAPPING.items()))
    return path


@pytest.fixture
def adf() -> AnnotatedDataFrame:
    # 111234567 -> SAR, 982345678 -> craft-associated-..., 993456789 -> aid-to-navigation,
    # 2345678   -> coast station 002345678 (2 leading 0s stripped by int storage) - must match
    #              "00" (coast-station), not "0" (group-ship-call), despite both being
    #              patterns of it,
    # 9990000   -> the reserved all-coast-stations identity 009990000 (2 leading 0s
    #              stripped) - must match the full 9-digit pattern, not the shorter "00",
    # 23523456  -> group ship call 023523456 (1 leading 0 stripped) - must not be swallowed by
    #              the "0" -> "00" disambiguation above,
    # 235678901 -> no rule matches -> default_category
    df = polars.DataFrame({
        "mmsi": [111234567, 982345678, 993456789, 2345678, 9990000, 23523456, 235678901],
    })
    metadata = MetaData(columns=[DataSpecification("mmsi", representation_type=int)])
    return AnnotatedDataFrame(df, metadata)


def test_load_pattern_rules(mapping_file):
    assert load_pattern_rules(mapping_file) == MAPPING


def test_classifies_by_longest_matching_pattern(adf, mapping_file, tmp_path):
    pipeline = DataProcessingPipeline(name="example", base_dir=str(tmp_path))
    pipeline.add("classify mmsi",
                 MMSIPatternClassifier(mapping_file=mapping_file),
                 name_mappings={"x": "mmsi"})

    result = pipeline.transform(df=adf)
    assert result.lazyframe.collect()["mmsi_category"].to_list() == [
        "SAR", "craft-associated-with-parent-ship", "aid-to-navigation", "coast-station",
        "all-coast-stations", "group-ship-call", "unknown",
    ]


def test_custom_default_category(adf, mapping_file, tmp_path):
    pipeline = DataProcessingPipeline(name="example", base_dir=str(tmp_path))
    pipeline.add("classify mmsi",
                 MMSIPatternClassifier(mapping_file=mapping_file, default_category="ship"),
                 name_mappings={"x": "mmsi"})

    result = pipeline.transform(df=adf)
    assert result.lazyframe.collect()["mmsi_category"].to_list()[-1] == "ship"


def test_discoverable_as_a_damast_plugin():
    """
    Requires this package to be installed (`pip install -e .`), so that the
    'damast.transformers' entry-point in pyproject.toml is registered.
    """
    entry_points = importlib.metadata.entry_points(group=PluginManager.ENTRY_POINT_GROUP)
    matches = [ep for ep in entry_points if ep.name == "MMSIPatternClassifier"]

    assert len(matches) == 1
    assert matches[0].load() is MMSIPatternClassifier
