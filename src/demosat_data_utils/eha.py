"""Demosat Engineering Health and Alarms (EHA) as a TtsDataFrame.

This module provides the mission-specific Demosat EHA frame that extends the
shared AMPCS EHA seam with Demosat-specific alarm styling semantics.

See Also
--------
tts_data_utils.multimission.ampcs.eha : shared AMPCS EHA frame
"""

from typing import Dict

import pandas as pd

from tts_data_utils.core.data_frame import TtsRowSeries
from tts_data_utils.multimission.ampcs.eha import AmpcsEhaFrame


class DemosatChannelRowSeries(TtsRowSeries):
    """Row ergonomics for a single Demosat EHA telemetry point.

    Colours the table row by worst-case alarm state, case-insensitively:
    RED (dnAlarmState or euAlarmState) → red background,
    YELLOW (dnAlarmState or euAlarmState) → yellow background,
    otherwise neutral.  Red takes precedence over yellow.  The ``status``
    column is never used for alarm styling.
    """

    @property
    def default_html_row_style(self) -> Dict:
        """Row background based on dnAlarmState/euAlarmState with case-insensitive handling."""
        def normalize(state):
            if isinstance(state, str):
                return state.strip().lower()
            return ""

        dn_state = normalize(self.get("dnAlarmState", ""))
        eu_state = normalize(self.get("euAlarmState", ""))

        # Red takes precedence
        if dn_state == "red" or eu_state == "red":
            return {"background-color": "#FFCCCC"}
        if dn_state == "yellow" or eu_state == "yellow":
            return {"background-color": "#FFF3CC"}
        return {}


class DemosatChannelFrame(AmpcsEhaFrame):
    """Demosat Engineering Health and Alarms telemetry as a TtsDataFrame.

    Retains the complete Demosat EHA row shape with permissive schema handling.
    Uses ``channelId`` as the semantic label, ``eu`` as the primary value, and
    ``scet`` as the default time axis.  Day-of-year timestamps are supported
    via ``TIME_FORMATS``.

    Alarm styling is provided by :class:`DemosatChannelRowSeries` which reads
    ``dnAlarmState`` and ``euAlarmState`` case-insensitively, gives red
    precedence over yellow, and ignores ``status``.
    """

    ROW_SERIES_CLASS = DemosatChannelRowSeries

    # Demosat uses year-day-of-year timestamps like 2024-033T00:00:00.000000
    TIME_FORMATS = {
        "scet": "%Y-%jT%H:%M:%S.%f",
        "ert": "%Y-%jT%H:%M:%S.%f",
        "rct": "%Y-%jT%H:%M:%S.%f",
        "lst": "%Y-%jT%H:%M:%S.%f",
    }

    @classmethod
    def _read_csv_to_df(cls, filepath: str, *args, **kwargs) -> pd.DataFrame:
        """Read CSV and coerce Demosat day-of-year timestamps.

        Parameters
        ----------
        filepath: str
            Path to the CSV file.
        *args, **kwargs
            Passed through to :func:`pandas.read_csv`.

        Returns
        -------
        pd.DataFrame
            DataFrame with ``scet``, ``ert``, ``rct`` and ``lst`` parsed as datetimes.
        """
        # Parse CSV and coerce Demosat day-of-year timestamps
        df = pd.read_csv(filepath, *args, **kwargs)
        for col in ("scet", "ert", "rct", "lst"):
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], format="%Y-%jT%H:%M:%S.%f", errors="coerce")
        return df
