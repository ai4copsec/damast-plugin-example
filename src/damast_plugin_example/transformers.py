"""
Example damast plugin transformer.

This module is what the ``damast.transformers`` entry-point in pyproject.toml points at -
see :class:`MMSIPatternClassifier` and the package README.
"""
from pathlib import Path

import polars
import yaml

from damast.core.dataframe import AnnotatedDataFrame
from damast.core.decorators import describe, input, output
from damast.core.transformations import PipelineElement


def load_pattern_rules(mapping_file: str | Path) -> dict[str, str]:
    """
    Load MMSI-pattern -> category rules from a YAML mapping file.

    Example:
        ```yaml
        # mmsi_categories.yaml - see examples/mmsi_categories.yaml for the full set of
        # patterns defined in Recommendation ITU-R M.585-10
        "111": sar-aircraft                      # Annex 1, Section 3: 111-MID-XXX
        "98": craft-associated-with-parent-ship  # Annex 1, Section 5: 98-MID-XXXX
        "99": aid-to-navigation                  # Annex 1, Section 4: 99-MID-XXXX
        "009990000": all-coast-stations          # Annex 1, Section 2 §8: fixed identity
        ```

    Args:
        mapping_file: Path to a YAML file mapping MMSI patterns to category labels. A
            pattern is matched as a leading-digits prefix, so it can be as short as a single
            digit (e.g. ``"9"``) or as long as a full 9-digit MMSI, in which case it only
            matches that one exact number. Patterns are matched longest-first, so a more
            specific one (e.g. ``"111"``, or a full 9-digit pattern) takes precedence over a
            shorter, more general one (e.g. ``"1"``).

    Returns:
        Mapping of pattern (as string) to category label

    Raises:
        FileNotFoundError: If `mapping_file` does not exist
    """
    with open(mapping_file) as f:
        rules = yaml.safe_load(f) or {}

    return {str(pattern): str(category) for pattern, category in rules.items()}


class MMSIPatternClassifier(PipelineElement):
    """
    Classify a MMSI column by matching it against patterns from a mapping file.

    MMSI numbers are not only assigned to ships - fixed digit patterns are reserved for other
    kinds of AIS transmitters, e.g. ``111MIDxxx`` for SAR aircraft or ``99MIDxxxx`` for aids to
    navigation, per Recommendation ITU-R M.585-10 (04/2026) - see
    examples/mmsi_categories.yaml for the full set of patterns it defines. This transformer
    looks up each MMSI's category from a user-supplied pattern -> label mapping (see
    `load_pattern_rules`) and adds it as a new column; it never drops rows - a MMSI matching no
    rule gets `default_category`.

    Example:
        ```python
        from damast.core.dataprocessing import DataProcessingPipeline
        from damast.plugins import MMSIPatternClassifier

        pipeline = DataProcessingPipeline(name="example", base_dir=".")
        pipeline.add("classify mmsi",
                     MMSIPatternClassifier(mapping_file="mmsi_categories.yaml"),
                     name_mappings={"x": "mmsi"})
        ```

    Args:
        mapping_file: YAML file mapping MMSI patterns to category labels - see
            `load_pattern_rules`. Re-read every time the transformer is constructed, including
            when a saved pipeline using it is loaded elsewhere, so keep it alongside the
            pipeline (or use an absolute path)
        default_category: Category assigned to a MMSI that matches no rule in `mapping_file`
    """

    def __init__(self, mapping_file: str | Path, default_category: str = "unknown"):
        self.mapping_file = str(mapping_file)
        self.default_category = default_category
        self._rules = load_pattern_rules(mapping_file)
        # match the most specific (longest) pattern first - a full 9-digit pattern therefore
        # takes precedence over any shorter pattern it happens to also start with
        self._patterns_by_specificity = sorted(self._rules, key=len, reverse=True)

    def _categorize(self, mmsi: int | None) -> str:
        if mmsi is None:
            return self.default_category

        # A MMSI is always 9 digits, but two categories (group ship call, coast station)
        # start with a "0" that a plain integer column silently drops - zfill it back before
        # matching patterns, or those two categories (and the all-coast-stations identity)
        # could never match.
        mmsi_str = str(mmsi).zfill(9)
        for pattern in self._patterns_by_specificity:
            if mmsi_str.startswith(pattern):
                return self._rules[pattern]

        return self.default_category

    @describe("Classify a MMSI column by matching it against patterns from a mapping file")
    @input({"x": {}})
    @output({"{{x}}_category": {}})
    def transform(self, df: AnnotatedDataFrame) -> AnnotatedDataFrame:
        feature = self.get_name("x")
        result = self.get_name("{{x}}_category")
        df.lazyframe = df.lazyframe.with_columns(
            polars.col(feature)
            .map_elements(self._categorize, return_dtype=polars.String)
            .alias(result)
        )
        return df
