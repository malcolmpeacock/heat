
import os
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

from . import read
from .misc import upsample_df

def split_northern_ireland(s,keep=False):
    mainland=[]
    ni=[]
    for items in s.iteritems():
        latitude=items[0][0]
        longitude=items[0][1]
        if longitude < -5.18 and latitude < 55.2 and latitude > 52.5:
            ni.append(items[0])
        else:
            mainland.append(items[0])
    if keep:
        new_s = s.loc[ni]
    else:
        new_s = s.loc[mainland]
    return new_s

def map_population(input_path, interim_path, country, adverse,  interim=True, year=None, grid='I', plot=True):

    weather_grid = None
    mapped_population = {}

    if adverse:
        file = os.path.join(interim_path, 'population_adverse')
    else:
        file = os.path.join(interim_path, 'population{}_{}'.format(grid,country))

    if not os.path.isfile(file):

        population = read.population(input_path)
        if adverse:
            weather_data = read.wind_adverse(input_path, adverse)
        else:
            if interim:
                weather_data = read.wind(input_path)  # For the weather grid
            else:
                weather_data = read.wind_era5(input_path, year, grid)

        # Make GeoDataFrame from the weather data coordinates
        weather_grid = gpd.GeoDataFrame(index=weather_data.columns)
        weather_grid['geometry'] = weather_grid.index.map(lambda i: Point(reversed(i)))

        # Set coordinate reference system to 'latitude/longitude'
        weather_grid.crs = {'init': 'epsg:4326'}

        # Make polygons around the weather points
        weather_grid['geometry'] = weather_grid.geometry.apply(lambda point: point.buffer(.75 / 2, cap_style=3))

        # Make list from MultiIndex (this is necessary for the spatial join)
        weather_grid.index = weather_grid.index.tolist()

        # Filter population data by country to cut processing time
        if country == 'GB' or country == 'NI':
            gdf = population[population['CNTR_CODE'] == 'UK'].copy()
        else:
            gdf = population[population['CNTR_CODE'] == country].copy()

        # Align coordinate reference systems
        print(' aligning coords .....')
        gdf = gdf.to_crs({'init': 'epsg:4326'})

        # Spatial join
        # This must map the population onto the weather grid since
        # the UK weather grid contains 128022 points!
        print(' spatial join .....')
        gdf = gpd.sjoin(gdf, weather_grid, how="left", op='within')

        # Sum up population
        s = gdf.groupby('index_right')['TOT_P'].sum()

        # Remove NI if GB
        if country == 'GB':
            s = split_northern_ireland(s)
        if country == 'NI':
            s = split_northern_ireland(s,True)
        # Write results to interim path
        s.to_pickle(file)

    else:

        s = pd.read_pickle(file)
        print('{} already exists and is read from disk.'.format(file))

    mapped_population = s

    if plot:
        print('Plot of the re-mapped population data of {}'
              ' for visual inspection:'.format(country))
        gdf = gpd.GeoDataFrame(mapped_population, columns=['TOT_P'])
        gdf['geometry'] = gdf.index.map(lambda i: Point(reversed(i)))
        gdf.plot(column='TOT_P', legend=True)

    return mapped_population


def wind(input_path, mapped_population, interim, year, grid='I', plot=True, adverse=None):

    if adverse:
        df = read.wind_adverse(input_path, adverse)
    else:
        if interim:
            df = read.wind(input_path)
        else:
            df = read.wind_era5(input_path, year, grid)

    # Temporal average
    s = df.mean(0)

    if plot:
        print('Plot of the wind averages for visual inspection:')
        gdf = gpd.GeoDataFrame(s, columns=['wind'])
        gdf['geometry'] = gdf.index.map(lambda i: Point(reversed(i)))
        gdf.plot(column='wind', legend=True)

    # Wind data is filtered by population grid points for GB
    pd_wind = s.loc[mapped_population.index.tolist()]
    return pd_wind

def temperature_daily2hourly(input_path, t):
    t.index = pd.DatetimeIndex(t.index.date, name='time')
    t = upsample_df(t, '60min')
#   print('After upsample')
#   print(t)
    # apply the hourly temperature profile
    profile = read.temperature_profile(input_path)
#   print(profile)
    times = t.index.map(lambda x: int(x.strftime('%H')))
#   print(times)
    # add on the mean difference of the temperature for that hour to the 
    # average temperature, so that for the middle of the day we have a higher
    # temperature and for the night we have a lower one.
    t = t + profile.loc[times].values
#   print(t)
    return t

def temperature(input_path, year, mapped_population, interim_path, adverse, country='GB', grid='I', hour=6):

    if adverse:
        parameters = {
            'air': 't2m',
            'soil': 'stl4'
        }
        t = pd.concat(
                [read.temp_adverse(input_path, adverse, parameter) for parameter in parameters.values()],
            keys=parameters.keys(), names=['parameter', 'latitude', 'longitude'], axis=1
        )

        t = temperature_daily2hourly(input_path, t)
#       t.to_pickle("/home/malcolm/uclan/tools/python/scripts/heat/output/adv/pickle")

        temp_data = pd.concat(
            [t[parameter][mapped_population.index.tolist()] for parameter in parameters.keys()], keys=parameters.keys(), names=['parameter', 'latitude', 'longitude'], axis=1)

    else:
        file = os.path.join(interim_path, 'temperature_' + grid + country + str(year))

        if os.path.isfile(file):
            temp_data = pd.read_pickle(file)
            print('temperature preprocessed {} already exists and is read from disk.'.format(file))
        else:

            parameters = {
                'air': 't2m',
                'soil': 'stl4'
            }
            t = pd.concat(
                [read.weather_era5(input_path, year, hour, grid, 'temperature', parameter) for parameter in parameters.values()],
            keys=parameters.keys(), names=['parameter', 'latitude', 'longitude'], axis=1
            )

            t = upsample_df(t, '60min')

            temp_data = pd.concat(
            [t[parameter][mapped_population.index.tolist()] for parameter in parameters.keys()], keys=parameters.keys(), names=['parameter', 'latitude', 'longitude'], axis=1)

            # Write results to interim path
            temp_data.to_pickle(file)

#   print(temp_data.index)
#   quit()
    return temp_data

def climate(temperature, year):
    temperature_change = (2020 - year) / 40.0
    temperature['air'] = temperature['air'] + temperature_change
    temperature['soil'] = temperature['soil'] + temperature_change
    return temperature
