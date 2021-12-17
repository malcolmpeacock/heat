# Script to generate heat demand time series with various methods.
# Input: temperature and wind speed from ERA-Iterim / ERA5
#        population data
# Output:hourly time series of heat demand, heat pump COP and electric heat
#        for the specified country and year.

# Python modules
import os
import shutil
import pandas as pd
from time import time
from datetime import date
import matplotlib.pyplot as plt
import argparse
import json

# Custom scripts
import scripts.download as download 
import scripts.read as read
import scripts.preprocess as preprocess
import scripts.demand as demand
import scripts.cop as cop
import scripts.write as write
import scripts.plot as plots
import scripts.electric as electric
from scripts.misc import localize

methods = { "B" : "BDEW", "W" : "Watson", "S" : "HDD 15.5", "H" : "HDD 12.8" }
method_string = json.dumps(methods)

all_countries = ['AT', 'BE', 'BG', 'CZ', 'DE', 'FR', 'GB', 'UK', 'NI', 'HR',
                 'HU', 'IE', 'LU', 'NL', 'PL', 'RO', 'SI', 'SK'] 

# process command line

parser = argparse.ArgumentParser(description='Generate heat and COP time series.')
parser.add_argument('ref', type=int, help='Reference year')
parser.add_argument('weather', type=int, help='Weather year')
parser.add_argument('--version', action="store", dest="version", help='Version - subdirectory to store output in, defaults to year', default=None )
parser.add_argument('--method', action="store", dest="method", help='Heat demand calculation method: ' + method_string, default='S' )
parser.add_argument('--grid', action="store", dest="grid", help='Grid I=0.75,0.75; 5=0.25,0.25 ', default='I' )
parser.add_argument('--profile', action="store", dest="profile", help='Hourly profile', default='bdew' )
parser.add_argument('--adverse', action="store", dest="adverse", help='UK Met office adverse weather scenario file', default=None)
parser.add_argument('--country', action="store", dest="country", help='Country one of:'+','.join(all_countries), default='GB' )
parser.add_argument('--nopop', action="store_true", dest="no_population", help='No weighting by population', default=False)
parser.add_argument('--plot', action="store_true", dest="plot", help='Show diagnostic plots', default=False)
parser.add_argument('--climate', action="store_true", dest="climate", help='Account for climate change', default=False)
parser.add_argument('--electric', action="store_true", dest="electric", help='Generate an eletricity time series', default=False)
parser.add_argument('--interim', action="store_true", dest="interim", help='Use ERA-Interim', default=False)
parser.add_argument("--tdays", type=int, action="store", dest="temp_days", help="Number of previous days temperature to use (1 to just use current day).", default=1)
# This is 1.0 because I am supplying annual heat demand for the country as
# opposed to fuel energy.
parser.add_argument("--eta", type=float, action="store", dest="efficiency", help="Factor to multiple by annual demand by to take account of efficiency.", default=1.0)
parser.add_argument('--debug', action="store_true", dest="debug", help='Debug mode 2 days only', default=False)

args = parser.parse_args()
ref = args.ref
year = args.weather
if args.version:
    version = args.version
else:
    version = str(year)
method = args.method
profile = args.profile
country = args.country
interim = args.interim
grid = args.grid

print('Options- weather year: {} reference year: {} method: {} profile: {} country: {} grid: {} '.format( year, ref, methods[method], profile, country, grid))

home_path = os.path.realpath('.')

input_path = os.path.join(home_path, 'input')
interim_path = os.path.join(home_path, 'interim')
output_path = os.path.join(home_path, 'output', version)

for path in [input_path, interim_path, output_path]:
    os.makedirs(path, exist_ok=True)
output_name = '{}Ref{}Weather{}{}-{}{}'.format(country,str(ref),str(year),grid,method,profile)
if args.climate:
    output_name += 'C'
#print('output_name {}'.format(output_name))
output_file = os.path.join(output_path, output_name + '.csv')
if args.adverse:
    output_file = os.path.join(output_path, args.adverse + '.csv')

# weather

if args.adverse:
    print('Using Adverse weather scenario file')
else:

    if interim:
        print('Using weather data from ERA-Interim')
        if "ECMWF_API_URL" not in os.environ or "ECMWF_API_KEY" not in os.environ or "ECMWF_API_EMAIL" not in os.environ:
            print("Environment variables ECMWF_API_URL, ECMWF_API_KEY and ECMWF_API_EMAIL must be set to use ERA-Interim")
            quit()
        download.wind(input_path)
        download.temperatures(input_path, year, year)
    else:
        print('Using weather data from ERA5')
        download.weather_era5(input_path, year, 6, args.grid)
        download.wind_era5(input_path,year, args.grid)

# population
# the population grid determines which weather grid squares belong to 
# a country

download.population(input_path)

print('Mapping population ... ')

mapped_population = preprocess.map_population(input_path, interim_path, country, args.adverse, interim, year, args.grid, args.plot)

# if no population weighting,
# set the population values all to the same thing so we get no weighting.

if args.no_population:
    mapped_population = mapped_population * 0.0 + 1.0
    print('No weighting by population')
else:
    print('Weighting by population')

print('Processing wind ... ')

wind = preprocess.wind(input_path, mapped_population, interim, year, args.grid, args.plot, args.adverse)
if args.plot:
    plt.show()

print('Processing temp ... ')

temperature = preprocess.temperature(input_path, year, mapped_population, interim_path, args.adverse, country, args.grid, 6)

# reduce size of data for debugging. 
# Number of days must be enough for number of days of reference temperature!

if args.debug:
    temperature = temperature['2018-01-01 00:00:00' : '2018-01-05 23:00:00']
    print(temperature)

# Account for climate change
if args.climate:
    print('Accounting for Climate Change')
    temperature = preprocess.climate(temperature, year)

# Reference temperature

num_previous = args.temp_days
print('Reference temp for ' + str(num_previous) + ' days ... ')

reference_temperature = demand.reference_temperature(temperature['air'],num_previous)

print('Daily parms ... ')
daily_parameters = read.daily_parameters(input_path)

print('Daily heat and water ... ')
if method == 'B':
    daily_heat = demand.daily_heat(reference_temperature, wind, daily_parameters)
    daily_water = demand.daily_water(reference_temperature, wind, daily_parameters)

if method == 'W':
    daily_heat = demand.watson_daily_heat(reference_temperature, wind, daily_parameters)
    daily_water = demand.watson_daily_water(reference_temperature, wind, daily_parameters)

if method == 'H':
    daily_heat = demand.hdd_daily_heat(reference_temperature, wind, daily_parameters, 12.8)
    daily_water = demand.hdd_daily_water(reference_temperature, wind, daily_parameters)

if method == 'S':
    daily_heat = demand.hdd_daily_heat(reference_temperature, wind, daily_parameters, 15.5)
    daily_water = demand.hdd_daily_water(reference_temperature, wind, daily_parameters)

if args.debug:
    print('daily_heat')
    print(daily_heat)

hourly_parameters = read.hourly_parameters(input_path, profile)

# plot hourly profiles to check
if args.plot:
    plots.hourly_profile(hourly_parameters)

print('Hourly heat ... ')
hourly_heat = demand.hourly_heat(daily_heat,
                                 reference_temperature, 
                                 hourly_parameters)
if args.debug:
    print('hourly_heat')
    print(hourly_heat)

print('Hourly water ... ')
hourly_water = demand.hourly_water(daily_water,
                                   reference_temperature, 
                                   hourly_parameters)

# For the other methods, we are calculating the hourly space heating.
if method == 'B':
    hourly_space = (hourly_heat - hourly_water).clip(lower=0)
else:
    hourly_space = hourly_heat.clip(lower=0)

annual_demands = read.annual_demand(input_path, country)
annual_demand_ref = annual_demands.loc[ref]
annual_space = { 'residential' : annual_demand_ref['domestic_space'], 'commercial' : annual_demand_ref['services_space'] }
annual_water = { 'residential' : annual_demand_ref['domestic_water'], 'commercial' : annual_demand_ref['services_water'] }
if year != ref:
    # hdd for reference year.
    hdd_ref = annual_demand_ref['hdd']
    if hdd_ref == 0.0:
        print('Reference year not equal to weather year, but hdd in {}.csv is 0.0'.format(country) )
        quit()
#   get hdd for weather year
    hdd = demand.hdd(reference_temperature, mapped_population, base_temp=15.5)
    print ('Reference year not equal to weather year, scale by hdd {} hdd_ref {} '.format(hdd,hdd_ref))
    annual_space['residential'] = annual_space['residential'] * hdd / hdd_ref
    annual_space['commercial'] = annual_space['commercial'] * hdd / hdd_ref

print ('spatial_space')
spatial_space = demand.finishing(hourly_space, mapped_population, annual_space, args.efficiency)

print ('spatial_water')
spatial_water = demand.finishing(hourly_water, mapped_population, annual_water, args.efficiency)

final_heat = demand.combine(spatial_space, spatial_water)

# Air, ground, water temp for each grid point
source_temperature = cop.source_temperature(temperature)
sink_temperature = cop.sink_temperature(temperature)

# coefficient of performance 

cop_parameters = read.cop_parameters(input_path)
spatial_cop = cop.spatial_cop(source_temperature, sink_temperature, cop_parameters)

final_cop = cop.finishing(spatial_cop, spatial_space, spatial_water, country)


# Calculate an electricity demand
if args.electric:
    # Read in combination of ASHP GSHP etc.
    parm_heat, parm_water = read.electric_parameters(input_path, country)
    electric_parameters = { 'heating_types': parm_heat, 'hot_water_types':parm_water}
    electric = electric.finishing(spatial_cop, spatial_space, spatial_water, electric_parameters, country)
    electric_sum = electric.sum() / 1000000.0
    print('Total Electric = {:.2f} TWh'.format(electric_sum))
else:
    electric = pd.Series()

# hourly air temperature
t = temperature['air'].mean(axis=1) - 273.15
t.rename('temperature', inplace=True)
t = localize(t, country).tz_convert('utc')
# hourly soil temperature
g = temperature['soil'].mean(axis=1) - 273.15
g.rename('soiltemp', inplace=True)
g = localize(g, country).tz_convert('utc')

# output the csv file
write.combined_csv( output_file, final_heat, final_cop, t, g, electric, args.adverse)
print('Output written to {}'.format(output_file))

