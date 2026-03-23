#Python Imports
import pdb
from abc import ABC, abstractmethod
from datetime import datetime

#JPL Imports
from jpl_time import Time

#This Library Imports
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
    def default_html_row_style(self):
        """
        Returns the CSS style dictionary corresponding to the EVR's severity level.
        
        :return: A dictionary containing background-color and text color.
        :rtype: dict
        """
        return EVR_LEVEL_COLORS[self.level]


class EvrContainer(CoreEvrContainer):
    DATA_ITEM_CLS = EvrItem
    LEVELS = ['DIAGNOSTIC', 'COMMAND', 'ACTIVITY_LO', 'ACTIVITY_HI', 'WARNING_LO', 'WARNING_HI', 'FATAL', 'SIM_ERROR']
