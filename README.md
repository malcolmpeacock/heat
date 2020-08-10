# heat
Python program to generate heat demand time series from weather for an EU country. 

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

### Downloaded by the program

* Temperatures and windspeed from ERA-Interim or ERA5 Reanalysis
* Population from GeoSTAT

### Provided with the program

* Hourly profile from BDEW/BGW
* Flat Hourly profile
* Default annual demand values for some years / countries

## Function

* Generates hourly time series of heat and heat pump COP. Optionally includes temperature and eletricity time series.
* Uses a variety of different methods specified as user inputs.

## Output

csv file containing one row per hour of the year, and columns for:
* heat pump COP for GSHP, ASHP, WSHP and sinks: radiator, floor, water.
* space and water heating demand
* mean temperature
* optional eletric heat time series.
