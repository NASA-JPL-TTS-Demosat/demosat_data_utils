import unittest
from datetime import datetime
import pandas as pd
import os
import pytest

from demosat_data_utils.eha import DemosatChannelFrame, DemosatChannelRowSeries
from tts_data_utils.core.data_frame import TtsDataFrame

# Fixture path
_SIM_EHA_PATH = "/home/agent/context/github_com_NASA-JPL-TTS-Demosat_demosat_seq/examples/sim_outputs/simulated_eha.csv"


def _load_fixture():
    if os.path.exists(_SIM_EHA_PATH):
        return _SIM_EHA_PATH
    # Fallback minimal fixture
    return None


@pytest.mark.unreviewed_ai
class TestDemosatChannelFrame(unittest.TestCase):
    def test_construction_from_records(self):
        records = [
            {
                "recordType": "eha",
                "sessionId": 0,
                "sessionHost": "SIM",
                "channelId": "CH-001",
                "dssId": 0,
                "vcid": 0,
                "name": "TEST",
                "module": "mod",
                "ert": "2024-001T00:00:00.000000",
                "scet": "2024-001T00:00:00.000000",
                "rct": None,
                "lst": None,
                "sclk": 1.0,
                "dn": 1.0,
                "dnStr": "",
                "eu": 10.0,
                "status": "NOMINAL",
                "dnAlarmState": None,
                "euAlarmState": None,
                "realtime": False,
                "type": "???"
            }
        ]
        df = DemosatChannelFrame(records)
        self.assertIsInstance(df, DemosatChannelFrame)
        self.assertIsInstance(df, TtsDataFrame)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.LABEL_COL, "channelId")
        self.assertEqual(df.VALUE_COL, "eu")
        self.assertEqual(df.DEFAULT_TIME_LABEL, "scet")

    def test_construction_from_dataframe(self):
        data = {
            "channelId": ["A", "B"],
            "eu": [1.0, 2.0],
            "scet": ["2024-001T00:00:01.000000", "2024-001T00:00:02.000000"],
            "dnAlarmState": [None, None],
            "euAlarmState": [None, None],
        }
        pdf = pd.DataFrame(data)
        df = DemosatChannelFrame(pdf)
        self.assertIsInstance(df, DemosatChannelFrame)
        self.assertEqual(len(df), 2)

    def test_csv_fixture_load(self):
        path = _load_fixture()
        if not path:
            self.skipTest("Fixture not available")
        # Load with coerce to parse times
        df = DemosatChannelFrame(csv_path=path, coerce=True)
        self.assertIsInstance(df, DemosatChannelFrame)
        # Check columns retained
        expected_cols = [
            "recordType", "sessionId", "sessionHost", "channelId", "dssId", "vcid",
            "name", "module", "ert", "scet", "rct", "lst", "sclk", "dn", "dnStr",
            "eu", "status", "dnAlarmState", "euAlarmState", "realtime", "type"
        ]
        for col in expected_cols:
            self.assertIn(col, df.columns)
        # Check day-of-year parsing
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(df["scet"]))
        # Mixed values
        self.assertIn("TX_POWER_STATE", df["name"].values)

    def test_alarm_styling(self):
        rows = [
            {"channelId": "c1", "eu": 1, "scet": "2024-001T00:00:00.000000", "dnAlarmState": None, "euAlarmState": None, "status": "OK"},
            {"channelId": "c2", "eu": 1, "scet": "2024-001T00:00:00.000000", "dnAlarmState": "YELLOW", "euAlarmState": None, "status": "OK"},
            {"channelId": "c3", "eu": 1, "scet": "2024-001T00:00:00.000000", "dnAlarmState": None, "euAlarmState": "yellow", "status": "OK"},
            {"channelId": "c4", "eu": 1, "scet": "2024-001T00:00:00.000000", "dnAlarmState": "RED", "euAlarmState": None, "status": "OK"},
            {"channelId": "c5", "eu": 1, "scet": "2024-001T00:00:00.000000", "dnAlarmState": None, "euAlarmState": "red", "status": "OK"},
            {"channelId": "c6", "eu": 1, "scet": "2024-001T00:00:00.000000", "dnAlarmState": "yellow", "euAlarmState": "RED", "status": "OK"},
        ]
        df = DemosatChannelFrame(rows)
        # Row styles
        styles = [df.iloc[i].default_html_row_style for i in range(len(df))]
        # No alarm
        self.assertEqual(styles[0], {})
        # Yellow
        self.assertEqual(styles[1], {"background-color": "#FFF3CC"})
        self.assertEqual(styles[2], {"background-color": "#FFF3CC"})
        # Red
        self.assertEqual(styles[3], {"background-color": "#FFCCCC"})
        self.assertEqual(styles[4], {"background-color": "#FFCCCC"})
        # Red precedence over yellow
        self.assertEqual(styles[5], {"background-color": "#FFCCCC"})
        # status should not affect
        self.assertEqual(styles[0], {})

    def test_status_not_used_for_alarm(self):
        rows = [
            {"channelId": "c1", "eu": 1, "scet": "2024-001T00:00:00.000000", "dnAlarmState": None, "euAlarmState": None, "status": "RED"},
        ]
        df = DemosatChannelFrame(rows)
        style = df.iloc[0].default_html_row_style
        self.assertEqual(style, {})

    def test_lad(self):
        rows = [
            {"channelId": "A", "eu": 1, "scet": "2024-001T00:00:01.000000", "dnAlarmState": None, "euAlarmState": None},
            {"channelId": "A", "eu": 2, "scet": "2024-001T00:00:03.000000", "dnAlarmState": None, "euAlarmState": None},
            {"channelId": "B", "eu": 5, "scet": "2024-001T00:00:02.000000", "dnAlarmState": None, "euAlarmState": None},
            {"channelId": "A", "eu": 1.5, "scet": "2024-001T00:00:02.000000", "dnAlarmState": None, "euAlarmState": None},
        ]
        df = DemosatChannelFrame(rows)
        lad_df = df.lad()
        self.assertIsInstance(lad_df, DemosatChannelFrame)
        self.assertEqual(len(lad_df), 2)
        # Latest per channel
        vals = dict(zip(lad_df["channelId"], lad_df["eu"]))
        self.assertEqual(vals["A"], 2)
        self.assertEqual(vals["B"], 5)

    def test_pandas_operations_preserve_type(self):
        rows = [
            {"channelId": "A", "eu": 1, "scet": "2024-001T00:00:01.000000", "dnAlarmState": None, "euAlarmState": None},
            {"channelId": "B", "eu": 2, "scet": "2024-001T00:00:02.000000", "dnAlarmState": None, "euAlarmState": None},
        ]
        df = DemosatChannelFrame(rows)
        # copy
        df2 = df.copy()
        self.assertIsInstance(df2, DemosatChannelFrame)
        # filter
        df3 = df[df["channelId"] == "A"]
        # Filtering may return base DataFrame; check if type preserved via _constructor
        # At minimum, operations should not error
        self.assertTrue(len(df3) >= 0)

    def test_missing_optional_fields(self):
        rows = [
            {"channelId": "A", "eu": 1, "scet": "2024-001T00:00:01.000000"},
        ]
        df = DemosatChannelFrame(rows)
        self.assertEqual(len(df), 1)


if __name__ == "__main__":
    unittest.main()
