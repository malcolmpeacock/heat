# general plotting functions

import matplotlib.pyplot as plt

# plot the given hourly profile
def hourly_profile(profile):
    hourly_profile_building('SFH',profile)
    hourly_profile_building('MFH',profile)
    hourly_profile_building('COM',profile)

def hourly_profile_building(building,profile):
    for(name,data) in profile[building].iteritems():
        data.plot(label=name, use_index=False)
    plt.title('Hourly Profiles for ' + building)
    plt.xlabel('Hour of the day')
    plt.ylabel('Normalised Demand')
    plt.legend(loc='upper right')
    plt.show()
