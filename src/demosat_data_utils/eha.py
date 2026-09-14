"""Demosat Engineering Health and Alarms (EHA) as a TtsDataFrame.

This module provides the mission-specific Demosat EHA frame that extends the
shared AMPCS EHA seam with Demosat-specific alarm styling semantics.

See Also
--------
tts_data_utils.multimission.ampcs.eha : shared AMPCS EHA frame
"""

from typing import Dict, Optional

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
    LABEL_COL = "channelId"
    VALUE_COL = "eu"
    DEFAULT_TIME_LABEL = "scet"

    def lad(self, value: Optional[object] = None, *, label_col: Optional[str] = None, time_col: Optional[str] = None) -> "DemosatChannelFrame":
        """Return latest-available-data per channel with deterministic missing-time handling.

        Selects the latest row per ``label_col`` using ``time_col``.  Rows with
        missing/unusable ``time_col`` are ignored for max selection; if a group
        has no usable times, the last row in that group is returned to keep the
        result deterministic.  The method always returns a
        :class:`DemosatChannelFrame`.

        Parameters
        ----------
        value : Optional[object]
            If provided, return the latest row for the specified label value.
            If None, return latest row per label for the entire frame.
        label_col : Optional[str]
            Column to group by. Defaults to ``LABEL_COL``.
        time_col : Optional[str]
            Column to use for time comparison. Defaults to ``DEFAULT_TIME_LABEL``.

        Returns
        -------
        DemosatChannelFrame
            Frame containing latest rows.
        """
        label_col = label_col or self.LABEL_COL
        time_col = time_col or self.DEFAULT_TIME_LABEL

        if label_col is None:
            raise ValueError("LABEL_COL/label_col must be configured to use lad().")

        # Helper to parse times with TIME_FORMATS for robustness
        def parse_times(series: pd.Series) -> pd.Series:
            fmt = getattr(self, "TIME_FORMATS", {}).get(time_col)
            if fmt:
                if isinstance(fmt, (list, tuple)):
                    fmt = fmt[0]
                try:
                    return pd.to_datetime(series, format=fmt, errors="coerce")
                except Exception:
                    return pd.to_datetime(series, errors="coerce")
            return pd.to_datetime(series, errors="coerce")

        if value is None:
            if label_col not in self.columns or time_col not in self.columns:
                return self.__class__(self.copy(), coerce=False, validate=False)

            def pick_latest(group: pd.DataFrame) -> pd.Series:
                parsed = parse_times(group[time_col])
                valid_mask = parsed.notna()
                if valid_mask.any():
                    max_time = parsed[valid_mask].max()
                    candidates_mask = valid_mask & (parsed == max_time)
                    candidates = group[candidates_mask]
                    # Deterministic tie-break: pick last candidate by original index
                    idx = candidates.index[-1]
                    return group.loc[idx]
                # No usable time values: fall back to the last row in the group
                return group.iloc[-1]

            result_df = (
                self.groupby(label_col, group_keys=False)
                .apply(pick_latest)
                .reset_index()
            )
            if isinstance(result_df, pd.Series):
                result_df = result_df.to_frame().T
            return self.__class__(result_df, coerce=False, validate=False)

        # value-specific path: latest row for a single label
        if label_col not in self.columns:
            raise ValueError(f"Label column {label_col!r} not present in frame.")
        df = self[self[label_col] == value]
        if df.empty:
            raise KeyError(f"Label {value!r} not found in {label_col!r}.")
        if time_col is not None and time_col in df.columns:
            parsed = parse_times(df[time_col])
            valid_mask = parsed.notna()
            if valid_mask.any():
                max_time = parsed[valid_mask].max()
                candidates_mask = valid_mask & (parsed == max_time)
                candidates = df[candidates_mask]
                idx = candidates.index[-1]
                row = df.loc[idx]
            else:
                row = df.iloc[-1]
        else:
            row = df.iloc[-1]
        return self.__class__(row.to_frame().T, coerce=False, validate=False)

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
        for col, fmt in cls.TIME_FORMATS.items():
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], format=fmt, errors="coerce")
        return df


__all__ = [
    "DemosatChannelFrame",
    "DemosatChannelRowSeries",
]
