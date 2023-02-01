# Plot the baseline electricity demand

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib

# read historic eletricity demand
def read_espeni(filename, year=None, cols=['ELEXM_utc', 'POWER_ESPENI_MW']):
    espini = pd.read_csv(filename, header=0, parse_dates=[0], index_col=0, usecols=cols, squeeze=True)
    # convert from half hourly to hourly
    hourly = espini.resample('H').sum() * 0.5
    hourly.index = pd.DatetimeIndex(pd.to_datetime(hourly.index.strftime("%Y-%m-%d %H") )).tz_localize('UTC')
    if year==None:
        return hourly
    else:
        return hourly.loc[year+'-01-01 00:00:00' : year + '-12-31 23:00:00']

def get_demand(year):
    demand_filename = 'input/electric/espeni.csv'
    demand = read_espeni(demand_filename, year)
    electric = demand / 1000000.0
    return electric

def read_copheat(filename, parms=['electricity']):
    demand = pd.read_csv(filename, header=0, parse_dates=[0], index_col=0, usecols=['time']+parms, squeeze=True )
    return demand

year = '2018'
electric_2018 = get_demand(year)

# input assumptions for reference year 2018 heating
# this includes:
#   domestic space 18
#   services space  9
#   domestic water  5
#   services water  2
#   industry space  7
#   total          40.94923
# ( industry is in the electricity time series, unlike the gas time series)
heat_in_the_electricity_time_series = 40.94923
heat_that_is_electric = heat_in_the_electricity_time_series / electric_2018.sum()
print('heat_that_is_electric {}'.format(heat_that_is_electric) )

daily_electric_2018 = electric_2018.resample('D').sum()

print('Historic demand 2018: max {} min {} total {} '.format(electric_2018.max(), electric_2018.min(), electric_2018.sum() ) )

# read resistive heat for 2018

demand_filename = 'output/2018/GBRef2018Weather2018I-Bbdew.csv'
heat_demand2018 = read_copheat(demand_filename, ['electricity', 'temperature'])
# electricity demand if all heating were electric
resistive_heat_2018 = heat_demand2018['electricity'] * 1e-6

# get the portion of heat the is currently electric
heat_that_is_electric_2018 = electric_2018.sum() * heat_that_is_electric / resistive_heat_2018.sum()
electric2018_heat = resistive_heat_2018 * heat_that_is_electric_2018
print('resistive_heat_2018 min {} max {} sum {}'.format(resistive_heat_2018.min(), resistive_heat_2018.max(), resistive_heat_2018.sum() ) )

# create baseline
electric2018_no_heat = electric_2018 - electric2018_heat

# plot 2018 electric, heat and difference. daily
daily_electric2018_heat = electric2018_heat.resample('D').sum()
daily_electric2018_no_heat = electric2018_no_heat.resample('D').sum()

daily_electric_2018.plot(color='blue', label='Historic electricity demand time series 2018')
daily_electric2018_heat.plot(color='red', label='Electricty used for heating 2018')
daily_electric2018_no_heat.plot(color='purple', label='Electricity 2018 with heating electricity removed')
plt.title('Removing existing heating electricity from the daily electricty demand series')
plt.xlabel('day of the year', fontsize=15)
plt.ylabel('Daily Electricity Demand (Twh)', fontsize=15)
plt.legend(loc='upper center')
plt.show()

# stats
dayspm  = np.array([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])
monthly = daily_electric2018_no_heat.resample('M').sum() 
mppd = np.divide(monthly.values,dayspm)
print(mppd)
# exclude Xmas
no_xmas = daily_electric2018_no_heat['2018-01-01' : '2018-12-16']
print(no_xmas)
weekly_no_xmas = no_xmas.resample('W').sum() / 7.0
print('Daily variation: min {} max {} diff {}'.format(no_xmas.min(), no_xmas.max(), no_xmas.max() - no_xmas.min() ) )
print('Weekly variation: min {} max {} diff {}'.format(weekly_no_xmas.min(), weekly_no_xmas.max(), weekly_no_xmas.max() - weekly_no_xmas.min() ) )

# plot baseline 2018 daily and weekly
no_xmas.plot(color='blue', label='Daily baseline without Christmas holiday period 2018')
no_xmas.rolling(7, min_periods=1).mean().plot(color='green', label='7 day rolling average Daily baseline without Christmas holiday period 2018')
plt.title('Baseline seasonaily 2018')
plt.xlabel('day of the year', fontsize=15)
plt.ylabel('Daily Electricity Demand (Twh)', fontsize=15)
plt.legend(loc='upper center')
plt.ylim(0,1.0)
plt.show()
