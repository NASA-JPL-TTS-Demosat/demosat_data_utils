import unittest
import os
import pandas as pd
import pytest

from demosat_data_utils.evr import DemosatEvrFrame, DemosatEvrRowSeries, EVR_LEVEL_COLORS, EvrItem, EvrContainer
from tts_data_utils.core.data_frame import TtsDataFrame

_SIM_EVR_PATH = "/home/agent/context/github_com_NASA-JPL-TTS-Demosat_demosat_seq/examples/sim_outputs/simulated_evrs.csv"


def _load_fixture():
    if os.path.exists(_SIM_EVR_PATH):
        return _SIM_EVR_PATH
    return None


@pytest.mark.unreviewed_ai
class TestDemosatEvrFrame(unittest.TestCase):
    def test_construction_from_records(self):
        records = [
            {
                "recordType": "evr",
                "sessionId": 0,
                "sessionHost": "SIM",
                "name": "TEST_EVR",
                "module": "mod",
                "level": "FATAL",
                "eventId": 1,
                "vcid": 0,
                "dssId": 0,
                "fromSse": False,
                "realtime": False,
                "sclk": 0.0,
                "scet": "2024-001T00:00:00.000000",
                "ert": "2024-001T00:00:00.000000",
                "rct": None,
                "lst": None,
                "message": "msg",
                "metadataKeywordList": "[]",
                "metadataValuesList": "[]",
                "metadata": "{}",
            }
        ]
        df = DemosatEvrFrame(records)
        self.assertIsInstance(df, DemosatEvrFrame)
        self.assertIsInstance(df, TtsDataFrame)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.LABEL_COL, "name")
        self.assertEqual(df.VALUE_COL, "message")
        self.assertEqual(df.DEFAULT_TIME_LABEL, "scet")

    def test_construction_from_dataframe(self):
        data = {
            "name": ["A", "B"],
            "message": ["m1", "m2"],
            "level": ["DIAGNOSTIC", "FATAL"],
            "scet": ["2024-001T00:00:01.000000", "2024-001T00:00:02.000000"],
        }
        pdf = pd.DataFrame(data)
        df = DemosatEvrFrame(pdf)
        self.assertIsInstance(df, DemosatEvrFrame)
        self.assertEqual(len(df), 2)

    def test_csv_fixture_load(self):
        path = _load_fixture()
        if not path:
            self.skipTest("Fixture not available")
        df = DemosatEvrFrame(csv_path=path, coerce=True)
        self.assertIsInstance(df, DemosatEvrFrame)
        expected_cols = [
            "recordType", "sessionId", "sessionHost", "name", "module", "level",
            "eventId", "vcid", "dssId", "fromSse", "realtime", "sclk", "scet",
            "ert", "rct", "lst", "message", "metadataKeywordList", "metadataValuesList", "metadata"
        ]
        for col in expected_cols:
            self.assertIn(col, df.columns)
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(df["scet"]))

    def test_levels_and_styling(self):
        records = [
            {"name": f"E{i}", "message": "m", "level": lvl, "scet": "2024-001T00:00:00.000000"}
            for i, lvl in enumerate([
                "DIAGNOSTIC", "COMMAND", "ACTIVITY_LO", "ACTIVITY_HI",
                "WARNING_LO", "WARNING_HI", "FATAL", "SIM_ERROR"
            ])
        ]
        df = DemosatEvrFrame(records)
        for _, row in df.iterrows():
            style = row.default_html_row_style
            # Should have style for known levels
            self.assertTrue(style, f"No style for level {row['level']}")
            # Unknown level fallback
        # Test unknown level
        df_unknown = DemosatEvrFrame([{"name": "X", "message": "m", "level": "UNKNOWN", "scet": "2024-001T00:00:00.000000"}])
        style_unknown = df_unknown.iloc[0].default_html_row_style
        self.assertEqual(style_unknown, {})

    def test_filter_level(self):
        records = [
            {"name": "A", "message": "m", "level": "FATAL", "scet": "2024-001T00:00:00.000000"},
            {"name": "B", "message": "m", "level": "DIAGNOSTIC", "scet": "2024-001T00:00:00.000000"},
            {"name": "C", "message": "m", "level": "WARNING_LO", "scet": "2024-001T00:00:00.000000"},
        ]
        df = DemosatEvrFrame(records)
        filtered = df.filter_level("FATAL")
        self.assertIsInstance(filtered, DemosatEvrFrame)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered.iloc[0]["name"], "A")
        # Multiple levels
        filtered2 = df.filter_level(["FATAL", "WARNING_LO"])
        self.assertEqual(len(filtered2), 2)
        # Order preserved
        self.assertEqual(list(filtered2["name"]), ["A", "C"])

    def test_legacy_classes_preserved(self):
        # Legacy EvrItem and EvrContainer should still exist and be usable
        self.assertTrue(callable(EvrItem))
        self.assertTrue(callable(EvrContainer))
        # Instantiation requires full fields; just verify class attributes
        self.assertEqual(EvrItem.NAME, 'EVR')
        self.assertEqual(EvrContainer.DATA_ITEM_CLS, EvrItem)

    def test_public_import(self):
        # Ensure DemosatEvrFrame can be imported
        from demosat_data_utils.evr import DemosatEvrFrame as Imported
        self.assertTrue(Imported is DemosatEvrFrame)


if __name__ == "__main__":
    unittest.main()
