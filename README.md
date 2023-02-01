# heat
Python program to generate heat demand time series from weather for an EU country. Optionally also generates an electricity demand time series.

## Author
 Malcolm Peacock 2020 
 ( derived from code https://oruhnau/when2heat )

## Inputs

### Specified by the user

* Country: one of AT, BE, BG, CZ, DE, FR, GB, UK, NI, HR, HU, IE, LU, NL, PL, RO, SI, SK
* Year (of weather)
* Reference year - if different from the weather year then heating degrees days for the reference year are also required.
* Annual demand figures for space and water heating for the reference year
* ERA-Interim or ERA5 API key
* Method of splitting up the annual demand
* Which hourly profile to use

### Downloaded by the program

* Temperatures and windspeed from ERA-Interim or ERA5 Reanalysis
* Population from GeoSTAT

### Provided with the program

* Hourly profile from BDEW/BGW
* Flat Hourly profile
* RHPP Heat Pump Trial Hourly Profile
* Default annual demand values for some years / countries
* Example input file for the proportions of heat pump types: GB.csv
* Historic electricity demand from I. A. G. Wilson, A. J. R. Rennie, Y. Ding, P. C. Eames, P. J. Hall, and N. J. Kelly, "Historical daily gas and electrical energy flows through Great Britain's transmission networks and the decarbonisation of domestic heat," Energy policy, vol. 61, pp. 301-305, 2013, doi: 10.1016/j.enpol.2013.05.110.

## Function

* Generates hourly time series of heat and heat pump COP. Optionally includes temperature and eletricity time series.
* Uses a variety of different methods specified as user inputs.

## Output

csv file containing one row per hour of the year, and columns for:
* heat pump COP for GSHP, ASHP, WSHP and sinks: radiator, floor, water.
* space and water heating demand
* mean temperature
* optional heating electricty demand time series.

## Example of use

python heat_series.py 2018 2018 --electric

to use other years, for example for GB, you need to supply an annual demand in input/GB.csv

to create a baseline electricity demand without heat:

python baseline_plot.py

## Heat demand methods

There are 4 different heat demand methods:
* S - Heating Degree Days with a base temperature of 15.5
* H - Heading Degree Days with a base temperature of 12.8
* B - BDEW German Gas Demand Methodology 
* W - Regression equation from Watson et. al
