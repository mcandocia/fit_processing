import os
import csv
import re 
from bs4 import BeautifulSoup
import bs4
import shutil
from io import StringIO
import zipfile
import numpy as np 
PI = np.pi
import codecs

#should have 3 columns: longitude, latitude, radius (meters)
#CENSORFILE = 'censor.csv'

CENSOR_PARAMS = {
    'location':True,#this should always be true
    'heart_rate':False,
    'speed':True,
    'temperature':True,
    'speed_smooth':True,
    'elevation':True,
    'altitude':True,
    'timestamp':False,#if this is true, it will censor all of the CSVs
    'start_position_lat':True,
    'start_position_long':True,
    'end_position_lat':True,
    'end_position_long':True,
    'latitude':True,
    'longitude':True,
    'position_lat':True,
    'position_long':True,
    'enhanced_altitude':True,
    'enhanced_speed':True,
    #GPX-specific namestrk
    'ele':True,
    'lat':True,
    'lon':True,
    'time':False,#if this is true, will censor all of GPX
}

# other names that can be synonymous with lat, lon
ADDITIONAL_LATLONG = [('start_position_lat','start_position_long'),
    ('end_position_lat','end_position_long')]


#removes any NA values for coordinates
#REMOVE_MISSING_COORDINATES = True

CENSOR_STRING = '[CENSORED]'

#ROOT_DIRECTORY = '/ntfsl/data/workouts'

#SEARCH_DIRECTORIES = [
#    'workout_gpx/strava_gpx',
#    'workout_gpx/garmin_fit',
#    'workout_gpx/cateye_gpx',
#    'workout_gpx/strava_gpx/gpx_csv'
#]

#TARGET_DIRECTORY = 'CLEAN_WORKOUTS'

#ZIP_FILENAME = 'CLEAN_WORKOUTS.ZIP'

CENSOR_COORDINATES = []

#ADDITIONAL_FILES_TO_COPY = ['workout_gpx/strava_gpx/bike_and_run_gpx_info.ods']

#will overwrite file if it already exists
OVERWRITE = False 
OVERWRITE_CSV = True 
OVERWRITE_GPX = False 

BLACKLIST = set(['test_file.csv'])

#radius of earth in meters
C_R = 6371. * 1000#/1.60934
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

def is_censorable(longitude, latitude):
    censor = False 
    for cc in CENSOR_COORDINATES:
        dist = distcalc({'lat':cc['latitude'],
            'lon':cc['longitude']},
            {'lat':latitude,'lon':longitude})
        if dist <= cc['radius']:
            censor = True 
            break
    return censor 

CSV_REGEX = re.compile(r'.*\.csv$')
GPX_REGEX = re.compile(r'.*\.gpx$')

def find_csv(directory):
    files = os.listdir(directory)
    return [file for file in files if CSV_REGEX.match(file) and file not in BLACKLIST]

def find_gpx(directory):
    files = os.listdir(directory)
    return [file for file in files if GPX_REGEX.match(file) and file not in BLACKLIST]

def censor_line(x, template):
    return [e if not template[i] else CENSOR_STRING for i, e in enumerate(x)]

def transfer_csv(filename, directory, censor_target_dir):
    target_file = os.path.join(censor_target_dir, directory, filename)
    if os.path.isfile(target_file) and not (OVERWRITE or OVERWRITE_CSV):
        return 1
    with open(os.path.join(directory, filename), 'r') as f: 
        reader = csv.reader(f)
        use_alternate_censoring = False 
        with codecs.open(os.path.join(censor_target_dir, os.path.split(directory)[1], filename),
                         'w', encoding='utf8') as of:
            writer = csv.writer(of)
            header = next(reader)
            writer.writerow(header)
            if 'latitude' in header:
                lat_index = header.index('latitude')
                lon_index = header.index('longitude')
            elif 'position_lat' in header:
                lat_index = header.index('position_lat')
                lon_index = header.index('position_long')
            else:
                use_alternate_censoring=True
                other_latlong_indexes = []
                for names in ADDITIONAL_LATLONG:
                    try:
                        other_latlong_indexes.append( ( header.index(names[0]), header.index(names[1])) )
                    except ValueError:
                        continue 
            #currently not in use
            censorable_columns = [i for i, column in enumerate(header) if CENSOR_PARAMS.get(column, False)]
            #currently in use 
            should_censor = [CENSOR_PARAMS.get(column, False) for i, column in enumerate(header)]
            #print should_censor
            for line in reader:
                if not use_alternate_censoring:
                    try:
                        longitude, latitude = ( float(line[lon_index]), float(line[lat_index]) )
                        if is_censorable(longitude, latitude):
                            if not CENSOR_PARAMS['timestamp']:
                                writer.writerow(censor_line(line, should_censor))
                        else:
                            writer.writerow(line)
                    except ValueError:
                        #likely has one or both of the longitude/latitude values missing
                        #I do not personally have files like this (I think), but it is possible
                        #will fail to censor latitude/longitude if the other is not present, but that's
                        #not realistic
                        print('....')
                        writer.writerow(line)
                else:
                    will_censor = False 
                    for latitude_idx, longitude_idx in other_latlong_indexes:
                        try:
                            latitude = float(line[latitude_idx])
                            longitude = float(line[longitude_idx])
                        except ValueError:
                            #value of 'None' likely, will just ignore this...
                            continue 
                        will_censor = will_censor or is_censorable(latitude, longitude)
                        if will_censor:
                            break
                    if will_censor:
                        if not CENSOR_PARAMS['timestamp']:
                            writer.writerow(censor_line(line, should_censor))
                    else:
                        writer.writerow(line)
        print('transfered %s' % (os.path.join(directory, filename)))


def load_censor_coordinates(censorfile):
    # not great practice, but easy enough to use here
    global CENSOR_COORDINATES 
    with open(censorfile,'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        lat_index = header.index('latitude')
        lon_index = header.index('longitude')
        radius_index = header.index('radius')
        for line in reader:
            CENSOR_COORDINATES.append({'latitude':float(line[lat_index]),
                'longitude':float(line[lon_index]),
                'radius':float(line[radius_index])}
                )
        print(CENSOR_COORDINATES )
    print('loaded CENSOR_COORDINATES')
    return 0

def transfer_gpx(filename, directory, censor_target_dir):
    target_file = os.path.join(censor_target_dir, os.path.split(directory)[1], filename)
    if os.path.isfile(target_file) and not (OVERWRITE or OVERWRITE_GPX):
        return 1
    with open(os.path.join(directory, filename),'r') as f:
        data = f.read()
        soup = BeautifulSoup(data, 'lxml',from_encoding="utf-8")
    trkpts = soup.find_all('trkpt')
    for pt in trkpts:
        lat, lon = (float(pt.attrs['lat']), float(pt.attrs['lon']) )
        will_censor = is_censorable(lon, lat)
        if will_censor:
            if CENSOR_PARAMS['time']:
                pt.decompose()
            else:
                for child in pt.children:
                    if isinstance(child, bs4.element.Tag):
                        if CENSOR_PARAMS.get(child.name, False):
                            child.decompose()
                if CENSOR_PARAMS.get('lat', False):
                    pt.attrs['lat'] = CENSOR_STRING
                if CENSOR_PARAMS.get('lon', False):
                    pt.attrs['lon'] = CENSOR_STRING 
                
    with codecs.open(os.path.join(censor_target_dir, os.path.split(directory)[1],
                                  filename), 'w', encoding='utf8') as f:
        try:
            f.write(soup.prettify())
        except:
            print(filename )
            print(directory )
            raise Exception('fix that damn unicode bug')
    print('processed %s' % '/'.join([directory,filename]))
    return 0 

def make_directories(censor_search_directories, censor_target_dir):
    counter = 0
    for directory in censor_search_directories:
        path = os.path.join(censor_target_dir, os.path.split(directory)[1])
        if not os.path.exists(path):
            os.makedirs(path)
            counter += 1
    print('made %d necessary directories' % counter )

def zip_target_directory( archive_target_dir, zip_filename, target_directory):
    shutil.make_archive(os.path.join(archive_target_dir, zip_filename), 'zip', target_directory)

def main(
        censor_search_directories,
        censor_target_dir,
        censorfile,
        censor_string,
        options, # pretty much everything else...
):
    #os.chdir(ROOT_DIRECTORY)
    if censorfile != '':
        load_censor_coordinates(censorfile)

    # quick h4ck
    global CENSOR_STRING
    CENSOR_STRING = censor_string

    if censorfile != '':
        make_directories(censor_search_directories, censor_target_dir)
        for directory in censor_search_directories:
            print('searching %s' % directory )
            csv_files = find_csv(directory)
            gpx_files = find_gpx(directory)
            #print gpx_files
            for filename in csv_files:
                try:
                    transfer_csv(filename, directory, censor_target_dir)
                except Exception as e:
                    print('!')
                    print(filename )
                    raise e 
            for filename in gpx_files:
                transfer_gpx(filename, directory, censor_target_dir)
    if options['archive_results']:
        os.makedirs(options['archive_output_dir'], exist_ok=True)
        for file in options['archive_extra_files']:
            if options['archive_censored_only']:
                shutil.copyfile(file, os.path.join(censor_target_dir, os.path.split(file)[1]))
            else:
                shutil.copyfile(file, os.path.join(options['root_subject_dir'], os.path.split(file)[1]))

        if options['archive_censored_only']:
            zip_target_directory(options['archive_output_dir'], options['archive_filename'],
                                 censor_target_dir
            )
        else:
            zip_target_directory(options['archive_output_dir'], options['archive_filename'],
                                 options['root_subject_dir'],
            )
        print('made censored files and zipped them!')


if __name__=='__main__':
    raise NotImplementedError('No longer supporting executable')
