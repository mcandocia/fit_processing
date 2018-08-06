from bs4 import BeautifulSoup
import numpy as np 
PI = np.pi
import csv
import os
from collections import OrderedDict
import re

OUTPUT_FILE = 'gpx_processed_info.csv' 

MAX_SPEED = 50#mph

#radius of earth in miles
C_R = 6371/1.60934
def distcalc(c1, c2):
    lat1 = float(c1['lat'])*PI/180.
    lon1 = float(c1['lon'])*PI/180.

    lat2 = float(c2['lat'])*PI/180.
    lon2 = float(c2['lon'])*PI/180.

    dlat = lat2-lat1
    dlon = lon2-lon1

    a = np.sin(dlat/2.)**2 + np.cos(lat1)*np.cos(lat2)*np.sin(dlon/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    d = C_R * c 
    return d 

def calculate_distances(points):
    dists = np.asarray([distcalc(c2.attrs,c1.attrs) for c1, c2 in zip(points[1:],points[:-1])])
    return dists 

def calculate_velocities(distances):
    #convert mi/s to mph
    velocities = distances * 3600
    return velocities 

def calculate_accelerations(velocities):
    return np.diff(velocities)

MIPS_TO_MPH = 3600.

FPS_TO_MPH = 3600./5280

G_FPS = 32.

G_MPHPS = 32 * FPS_TO_MPH

def process_file(filename, target_dir):
    new_filename = re.sub(r'([^.]+)\.gpx', r'raw_csv/\1.csv', filename)
    if os.path.exists(new_filename):
        #print '%s already exists. skipping.' % new_filename
        return None
    print('processing %s' % filename )
    with open(os.path.join(target_dir, filename),'r') as f:
        soup = BeautifulSoup(f.read(), 'lxml')
        track = soup.find('trk')
        segments = track.find('trkseg')
        points = segments.find_all('trkpt')
        times = [p.find('time').text for p in points]
        elevations = np.asarray([float(p.find('ele').text) for p in points])
    #lon-lat based
    distances = calculate_distances(points)
    velocities = calculate_velocities(distances)
    #if velocity > MAX_SPEED, then it indicates discontinuity
    velocities = velocities * (velocities < MAX_SPEED)
    accelerations = calculate_accelerations(velocities)
    #elevation
    elevation_changes = np.diff(elevations)
    sum_v = np.sum(velocities)
    sum_v2 = np.sum(velocities**2)
    sum_v3 = np.sum(velocities**3)
    abs_elevation = np.sum(np.abs(elevation_changes))/2
    sum_a = np.sum(accelerations * (accelerations > 0))
    #alternative type of accelerations measurement
    velocities_mph = 3600 * velocities 
    energy_increases = velocities_mph[1:]**2 - velocities_mph[:-1]**2
    energy_increases = energy_increases - FPS_TO_MPH**2 * G_FPS * elevation_changes[1:] * (elevation_changes[1:] < 0)
    energy_increases = np.sum(energy_increases * (energy_increases > 0))
    with open(new_filename, 'w') as f:
        f.write('time,distance,elevation_change')
        for t, d, e in zip(times[1:], distances, elevation_changes):
            f.write('\n')
            f.write(','.join([str(t), str(d), str(e)]))
            return {
                'sum_v':sum_v,
                'sum_v2':sum_v2,
                'abs_elevation':abs_elevation,
                'sum_a':sum_a,
                'sum_v3':sum_v3,
                'sum_e':energy_increases
            }

def main(gpx_source_dir, gpx_target_dir, gpx_summary_filename):
    original_dir = os.getcwd()
    os.makedirs(gpx_target_dir, exist_ok=True)
    
    os.chdir(gpx_source_dir)
    file_list = [x for x in os.listdir('.') if x[-4:].lower()=='.gpx']
    file_list.sort()
    fileinfo = OrderedDict()
    for file in file_list:
        td = process_file(file, gpx_target_dir)
        if td is not None: 
            fileinfo[file] = td
    #no longer interested in actually summing up variables here...
    if True:
        return 0
    with open(os.path.join(gpx_target_dir, gpx_summary_filename), 'w') as f:
        f.write(','.join(['filename','sum_v','sum_v2','sum_v3','abs_elevation','sum_a', 'sum_e']))
        for fn, data in fileinfo.iteritems():
            f.write('\n')
            f.write(','.join([str(x) for x in [
                fn,
                data['sum_v'],
                data['sum_v2'],
                data['sum_v3'],
                data['abs_elevation'],
                data['sum_a'],
                data['sum_e']
            ]
            ]
            ))
    print('processed gpx files')
    
    os.setwd(original_dir)


if __name__=='__main__':
    raise NotImplementedError('this program is now to be called from other files') #main()

    """
    **Context:**

I am trying to reverse-engineer Strava's algorithm for measuring Calories burned on a bike ride. I have 76 .gpx files downloaded, along with Strava's estimation for Calories burned. The equations for measuring this involve being able to estimate the speed at various time points, the elevation at various time points, and calculating power as a polynomial function of these two values. Integrating unscaled polynomials over time and plugging them into a linear regression with respect to the Calorie estimate should determine coefficients for my particular case.

**Note that I do not believe Strava's measurement is accurate. I simply want to determine the algorithms and formula they use for my particular case**

_________________
**Problems:**

1. My current speed variable is simply calculated by scaling the distance (each over 1-second intervals), which was initially calculated using the [haversine formula](https://en.wikipedia.org/wiki/Haversine_formula). I have a smoothed version that uses a normal kernel with varying bandwidths, and in each case the total distance matches the one Strava displays on its website.

2. The elevation calculations I make to determine overall change in elevation are very far off from the website's. I am simply looking at all positive increases in elevation (there is an 0.1-foot resolution), and adding those together. The estimates the website gives are usually 3/4-3 times the value I estimate.

3. The power formula the website gives is [this](https://support.strava.com/hc/en-us/articles/216917107-Power-Calculations), but it seems to calculate wind resistance as a function of v^2 (which is usually the force) as opposed to v^3 (which should be the power). Either way, I use the first, second, and third powers of velocity as variables. Additionally, I look at kinetic energy increases (a function of v^2/2) and add those together, decreasing them by decreases in gravitational potential energy that simultaneously occur. 

_____________

**Additional notes about data:**

1. The rides take place on mostly flat ground, with very few hills. Most elevation changes take place over longer distances.

2. 
    """
