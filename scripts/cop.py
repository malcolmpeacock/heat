
import os
import pandas as pd

# from scripts.misc import localize
# from scripts.misc import group_df_by_multiple_column_levels
from .misc import group_df_by_multiple_column_levels,localize


def source_temperature(temperature):

    celsius = temperature - 273.15

    return pd.concat(
        [celsius['air'], celsius['soil'] - 5, 0 * celsius['air'] + 10 - 5],
        keys=['air', 'ground', 'water'],
        names=['source', 'latitude', 'longitude'],
        axis=1
    )


def sink_temperature(temperature):

    celsius = temperature['air'] - 273.15

    return pd.concat(
        [-1 * celsius + 40, -.5 * celsius + 30, 0 * celsius + 50],
        keys=['radiator', 'floor', 'water'],
        names=['sink', 'latitude', 'longitude'],
        axis=1
    )


def spatial_cop(source, sink, cop_parameters):

    def cop_curve(delta_t, source_type):
        delta_t.clip(lower=15, inplace=True)
        return sum(cop_parameters.loc[i, source_type] * delta_t ** i for i in range(3))

    source_types = source.columns.get_level_values('source').unique()
    sink_types = sink.columns.get_level_values('sink').unique()

    return pd.concat(
        [pd.concat(
            [cop_curve(sink[sink_type] - source[source_type], source_type)
             for sink_type in sink_types],
            keys=sink_types,
            axis=1
        ) for source_type in source_types],
        keys=source_types,
        axis=1,
        names=['source', 'sink', 'latitude', 'longitude']
    ).round(4).swaplevel(0, 1, axis=1)


def finishing(cop, demand_space, demand_water, country, correction=.85):

    # Localize Timestamps (including daylight saving time correction) and convert to UTC
    sinks = cop.columns.get_level_values('sink').unique()
    cop = pd.concat(
            [localize(cop[sink], country).tz_convert('utc') for sink in sinks],
            keys=sinks, axis=1, names=['sink', 'source', 'latitude', 'longitude']
    )

    # Prepare demand values
    demand_space = group_df_by_multiple_column_levels(demand_space, ['latitude', 'longitude'])

    demand_water = group_df_by_multiple_column_levels(demand_water, ['latitude', 'longitude'])
 
    # Spatial aggregation
    sources = cop.columns.get_level_values('source').unique()
    sinks = cop.columns.get_level_values('sink').unique()
    power = pd.concat(
        [pd.concat(
            [(demand_water / cop[sink][source]).sum(axis=1)
             if sink == 'water' else
             (demand_space / cop[sink][source]).sum(axis=1)
             for sink in sinks],
            keys=sinks, axis=1
        ) for source in sources],
        keys=sources, axis=1
    )
    heat = pd.concat(
        [pd.concat(
            [demand_water.sum(axis=1)
             if sink == 'water' else
             demand_space.sum(axis=1)
             for sink in sinks],
            keys=sinks, axis=1
        ) for source in sources],
        keys=sources, axis=1, names=['sink', 'source']
    )
    cop = heat / power

    # Correction and round
    cop = (cop * correction).round(2)

    # Fill NA at the end and the beginning of the dataset arising from different local times
    cop = cop.fillna(method='bfill').fillna(method='ffill')

    # Rename columns
    cop.columns.set_levels(['ASHP', 'GSHP', 'WSHP'], level=0, inplace=True)
    cop.columns.set_levels(['radiator', 'floor', 'water'], level=1, inplace=True)
    cop.columns = ['_'.join([level for level in col_name]) for col_name in cop.columns.values]

    return cop

