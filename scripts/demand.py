
import numpy as np
import pandas as pd

# from scripts.misc import localize, upsample_df, group_df_by_multiple_column_levels
from .misc import localize, upsample_df, group_df_by_multiple_column_levels


def reference_temperature(temperature, nterms):

    # Daily average
    daily_average = temperature.groupby(pd.Grouper(freq='D')).mean().copy()

    # Weighted mean
    return sum([.5 ** i * daily_average.shift(i).fillna(method='bfill') for i in range(nterms)]) / \
           sum([.5 ** i for i in range(nterms)])

def hdd(temperature, population, base_temp=15.5):
    celsius = temperature - 273.15    # The temperature input is in Kelvin
    heat = base_temp - celsius        # degree days with base temp
    heat.clip(0, inplace=True)        # make sure its greater than zero.
    hdd = heat.sum()                  # sum up the days
    hdd = (hdd * population)/ population.sum()  # weight by population
    hdd = hdd.sum()          # sum up all the locations
    return hdd

def hdd_daily_heat(temperature, wind, all_parameters, base_temp=15.5):

    # Heating degree days .

    def heat_function(t, parameters):

        celsius = t - 273.15        # The temperature input is in Kelvin
        heat = base_temp - celsius  # degree days with base temp
        heat.clip(0, inplace=True)  # make sure its greater than zero.
        return heat

    return daily(temperature, wind, all_parameters, heat_function)

def hdd_daily_water(temperature, wind, all_parameters):

    # A function for the daily water heating demand - assumed divided equally between days
    # This is implemented in the following and passed to the general daily function

    def water_function(t, parameters):

        celsius = t - 273.15  # The temperature input is in Kelvin

        # sets to constant value - this screws everything up!!
        heat = (celsius * 0.0) + 10.0

        return heat

    return daily(temperature, wind, all_parameters, water_function)

def watson_daily_heat(temperature, wind, all_parameters):

    # Watson et al. 2015 describes the function for the daily gas demand
    #
    # Function           T(eff)
    # Total heat demand  <12.2
    #                    >14.2
    # Space heat demand
    # Domestic hot water
    # Gas Demand
    # This is implemented in the following and passed to the general daily function

    def heat_function(t, parameters):

        def watson_heat(et):
            if et < 14.1:
                heat = -6.71 * et + 111
                return heat
            else:
                heat = -1.21 * et + 33
                return heat

        celsius = t - 273.15  # The temperature input is in Kelvin
        ND = 27               # millions of dwellings - 27 in 2015
        return celsius.apply(watson_heat) * ND

    return daily(temperature, wind, all_parameters, heat_function)

def watson_daily_water(temperature, wind, all_parameters):

    # A function for the daily water heating demand is from Watson et al. 2019
    # This is implemented in the following and passed to the general daily function

    def water_function(t, parameters):

        celsius = t - 273.15  # The temperature input is in Kelvin
        ND = 27               # millions of dwellings - 27 in 2015

        # equation defined in Wastson et. al.
        heat = - 0.0458 * celsius + 1.8248
        # ensure its positive.
        heat.clip(0, inplace=True)

        return heat * ND

    return daily(temperature, wind, all_parameters, water_function)


def daily_heat(temperature, wind, all_parameters):

    # BDEW et al. 2015 describes the function for the daily heat demand
    # This is implemented in the following and passed to the general daily function

    def heat_function(t, parameters):

        celsius = t - 273.15  # The temperature input is in Kelvin

        sigmoid = parameters['A'] / (
                1 + (parameters['B'] / (celsius - 40)) ** parameters['C']
        ) + parameters['D']

        linear = pd.DataFrame(
            [parameters['m_{}'.format(i)] * celsius + parameters['b_{}'.format(i)] for i in ['s', 'w']]
        ).max()

        return sigmoid + linear

    return daily(temperature, wind, all_parameters, heat_function)


def daily_water(temperature, wind, all_parameters):

    # A function for the daily water heating demand is derived from BDEW et al. 2015
    # This is implemented in the following and passed to the general daily function

    def water_function(t, parameters):

        celsius = t - 273.15  # The temperature input is in Kelvin

        # Below 15 °C, the water heating demand is not defined and assumed to stay constant
        # this sets anything below 15 to 15.
        celsius.clip(15, inplace=True)

        return parameters['m_w'] * celsius + parameters['b_w'] + parameters['D']

    return daily(temperature, wind, all_parameters, water_function)


def daily(temperature, wind, all_parameters, func):

    # All locations are separated by the average wind speed with the threshold 4.4 m/s
    windy_locations = {
        'normal': wind[wind <= 4.4].index,
        'windy': wind[wind > 4.4].index
    }

    buildings = ['SFH', 'MFH', 'COM']

    return pd.concat(
        [pd.concat(
            [temperature[locations].apply(func, parameters=all_parameters[(building, windiness)])
             for windiness, locations in windy_locations.items()],
            axis=1
        ) for building in buildings],
        keys=buildings, names=['building', 'latitude', 'longitude'], axis=1
    )


def hourly_heat(daily_df, temperature, parameters):

    # According to BGW 2006, temperature classes are derived from the temperature data
    # This is re-sampled to a 60-min-resolution and passed to the general hourly function
    # MP: For each latitude,lognitude in the grid classes contains the 
    #     temperature in one of the 5 degree bands 5,10,15 etc to look up
    #     the hourly factors to multiply by.

    classes = upsample_df(
        (np.ceil(((temperature - 273.15) / 5).astype('float64')) * 5).clip(lower=-15, upper=30),
        '60min'
    ).astype(int).astype(str)

    return hourly(daily_df, classes, parameters)


def hourly_water(daily_df, temperature, parameters):

    # For water heating, the highest temperature classes '30' is chosen
    # This is re-sampled to a 60-min-resolution and passed to the general hourly function

    classes = upsample_df(
        pd.DataFrame(30, index=temperature.index, columns=temperature.columns),
        '60min'
    ).astype(int).astype(str)

    return hourly(daily_df, classes, parameters)


def hourly(daily_df, classes, parameters):

    def hourly_factors(building):

        # This function selects hourly factors from BGW 2006 by time and temperature class
        slp = pd.DataFrame(index=classes.index, columns=classes.columns)

        # Time includes the hour of the day
        times = classes.index.map(lambda x: x.strftime('%H:%M'))
        # For commercial buildings, time additionally includes the weekday
        if building == 'COM':
            weekdays = classes.index.map(lambda x: int(x.strftime('%w')))
            times = list(zip(weekdays, times))

        for column in classes.columns:
            slp[column] = parameters[building].lookup(times, classes.loc[:, column])

        return slp

    buildings = daily_df.columns.get_level_values('building').unique()

    results = pd.concat(
        [upsample_df(daily_df, '60min')[building] * hourly_factors(building) for building in buildings],
        keys=buildings, names=['building', 'latitude', 'longitude'], axis=1
#       keys=buildings, names=['building', 'country', 'latitude', 'longitude'], axis=1
    )

    return results


def finishing(df, population, building_database, efficiency=0.9, country='GB'):

    # Single- and multi-family houses are aggregated assuming a ratio of 70:30
    # Transforming to heat demand assuming an average conversion efficiency of 0.9
    building_database = {
        'SFH': efficiency * .7 * building_database['residential'],
        'MFH': efficiency * .3 * building_database['residential'],
        'COM': efficiency * building_database['commercial']
    }

    results = []

    # Localize Timestamps (including daylight saving time correction)
    df_country = localize(df, country)

    absolute = []
    for building_type, building_data in building_database.items():

        # Weighting
        df_cb = df_country[building_type] * population

        # Scaling to 1 TWh/a
        years = df_cb.index.year.unique()
        factor = 1000000 / df_cb.sum().sum() * len(years)

        # Scaling to building database
        factors = 1000000 / df_cb.sum().sum() * building_data
        absolute.append(df_cb * factors)

    country_results = pd.concat(absolute, axis=1, keys=building_database.keys(), names=['building_type', 'latitude', 'longitude'])

    return country_results.tz_convert('utc')


def combine(space, water):
    
    # Spatial aggregation
    space = space.sum(axis=1)
    water = water.sum(axis=1)

    df = pd.concat([space, water, space+water], axis=1, keys=['space', 'water', 'heat'])

    return df
