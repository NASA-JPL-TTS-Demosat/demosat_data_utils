#Python Imports
import pandas as pd

#This Library Imports
from tts_data_utils.core.log import TtsLogRowSeries
from tts_data_utils.multimission.ampcs.evr import AmpcsEvrFrame
from tts_data_utils.multimission.evr import EvrContainer as CoreEvrContainer
from tts_data_utils.multimission.evr import EvrItem as CoreEvrItem

EVR_LEVEL_COLORS = {
    'DIAGNOSTIC':  {'background-color': '#90ED91', 'color': '#333333'},
    'COMMAND':     {'background-color': '#0D00FF', 'color': '#F1F1F2'},
    'ACTIVITY_LO': {'background-color': '#D3D3D3', 'color': '#333333'},
    'ACTIVITY_HI': {'background-color': '#666666', 'color': '#F1F1F2'},
    'WARNING_LO':  {'background-color': '#F0F001', 'color': '#333333'},
    'WARNING_HI':  {'background-color': '#FEA500', 'color': '#333333'},
    'FATAL':       {'background-color': '#FF5E66', 'color': '#F1F1F2'},
    'SIM_ERROR':   {'background-color': '#FF5E66', 'color': '#F1F1F2'} 
}



class EvrItem(CoreEvrItem):
    NAME = 'EVR'
    @property
    def default_html_row_style(self) -> dict:
        """
        Returns the CSS style dictionary corresponding to the EVR's severity level.
        
        :return: A dictionary containing background-color and text color.
        :rtype: dict
        """
        return EVR_LEVEL_COLORS[self.level]


class EvrContainer(CoreEvrContainer):
    DATA_ITEM_CLS = EvrItem
    LEVELS = ['DIAGNOSTIC', 'COMMAND', 'ACTIVITY_LO', 'ACTIVITY_HI', 'WARNING_LO', 'WARNING_HI', 'FATAL', 'SIM_ERROR']


class DemosatEvrRowSeries(TtsLogRowSeries):
    """Row ergonomics for a single DemoSat EVR.

    Uses the mission-local EVR_LEVEL_COLORS palette, which extends the
    canonical AMPCS levels with the DemoSat-specific SIM_ERROR level.
    """

    LEVEL_COL = 'level'
    LEVEL_COLORS = EVR_LEVEL_COLORS


class DemosatEvrFrame(AmpcsEvrFrame):
    """DemoSat Event Records as a TtsDataFrame.

    Extends :class:`AmpcsEvrFrame` with the SIM_ERROR severity level that is
    unique to the DemoSat simulator environment.  Row coloring uses the
    mission-local :data:`EVR_LEVEL_COLORS` palette so SIM_ERROR rows are
    visually distinct.

    FILTER_COLS exposes ``level``, ``module``, and ``name`` to the query
    layer and any future LogExplorer widget.
    """

    ROW_SERIES_CLASS = DemosatEvrRowSeries

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
        df = pd.read_csv(filepath, *args, **kwargs)
        for col in ("scet", "ert", "rct", "lst"):
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], format="%Y-%jT%H:%M:%S.%f", errors="coerce")
        return df

    LEVELS = [
        'DIAGNOSTIC',
        'COMMAND',
        'ACTIVITY_LO',
        'ACTIVITY_HI',
        'WARNING_LO',
        'WARNING_HI',
        'FATAL',
        'SIM_ERROR',
    ]

    FILTER_COLS = {
        'level': LEVELS,
        'module': None,
        'name': None,
    }
