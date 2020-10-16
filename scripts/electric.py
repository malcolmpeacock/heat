
import os
import pandas as pd

from scripts.misc import localize
from scripts.misc import group_df_by_multiple_column_levels

# generate an electrity demand time series for the heat.

def finishing(cop, demand_space, demand_water, electric_parameters, country, correction=.85):


    # Localize Timestamps (including daylight saving time correction) and convert to UTC
    sinks = cop.columns.get_level_values('sink').unique()
    cop = pd.concat(
            [localize(cop[sink], country).tz_convert('utc') for sink in sinks],
            keys=sinks, axis=1, names=['sink', 'source', 'latitude', 'longitude']
    )

    # Prepare demand values
    demand_space = group_df_by_multiple_column_levels(demand_space, ['latitude', 'longitude'])

    demand_water = group_df_by_multiple_column_levels(demand_water, ['latitude', 'longitude'])

    # electricity assumptions
    # proportion of national heating and DHW types.
    heating_types = electric_parameters['heating_types']
    hot_water_types = electric_parameters['hot_water_types']
 
    # Spatial aggregation
    sources = cop.columns.get_level_values('source').unique()
    sinks = cop.columns.get_level_values('sink').unique()

    power = pd.concat(
        [pd.concat(
            [(demand_water * hot_water_types[source] / (1 if sink == 'resistive' else cop[sink][source]) ).sum(axis=1)
             if sink == 'water' else
             (demand_space * heating_types[source][sink] / (1 if sink == 'resistive' else cop[sink][source]) ).sum(axis=1)
             for sink in sinks],
            keys=sinks, axis=1
        ) for source in sources],
        keys=sources, axis=1
    )

    power_total = power.sum(axis=1)
    power_total.rename('electricity', inplace=True)
    return power_total
