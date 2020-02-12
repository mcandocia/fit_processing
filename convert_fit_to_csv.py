"""
toggle ALT_FILENAME to change naming scheme
currently recommended to keep at =True, since event type is placed in filename 
of created objects
"""

import csv
import os
#to install fitparse, run 
#sudo pip3 install -e git+https://github.com/dtcooper/python-fitparse#egg=python-fitparse
import fitparse
import pytz
from copy import copy
from tzwhere import tzwhere

print('Initializing tzwhere')
tzwhere = tzwhere.tzwhere()

tz_fields = ['timestamp_utc', 'timezone']

#for general tracks
allowed_fields = ['timestamp','position_lat','position_long', 'distance',
'enhanced_altitude', 'altitude','enhanced_speed',
                 'speed', 'heart_rate','cadence','fractional_cadence',
                 'temperature'] + tz_fields

# if gps data is spotty, but you want to keep HR/temp data while the clock is running, you can remove
# 'position_lat' and 'position_long' from here
required_fields = ['timestamp', 'position_lat', 'position_long', 'altitude']



#for laps
lap_fields = ['timestamp','start_time','start_position_lat','start_position_long',
               'end_position_lat','end_position_long','total_elapsed_time','total_timer_time',
               'total_distance','total_strides','total_calories','enhanced_avg_speed','avg_speed',
               'enhanced_max_speed','max_speed','total_ascent','total_descent',
               'event','event_type','avg_heart_rate','max_heart_rate',
               'avg_running_cadence','max_running_cadence',
               'lap_trigger','sub_sport','avg_fractional_cadence','max_fractional_cadence',
               'total_fractional_cycles','avg_vertical_oscillation','avg_temperature','max_temperature'] + tz_fields
#last field above manually generated
lap_required_fields = ['timestamp', 'start_time','lap_trigger']

#start/stop events
start_fields = ['timestamp','timer_trigger','event','event_type','event_group'] 
start_required_fields = copy(start_fields)
start_fields += tz_fields

#
all_allowed_fields = set(allowed_fields + lap_fields + start_fields)

UTC = pytz.UTC
CST = pytz.timezone('US/Central')


#files beyond the main file are assumed to be created, as the log will be updated only after they are created
ALT_FILENAME = True
ALT_LOG_ = 'file_log.log'

def read_log(log_path):
    with open(os.path.join(log_path, ALT_LOG_), 'r') as f:
        lines = f.read().split()
    return lines

def append_log(filename, log_path):
    with open(os.path.join(log_path, ALT_LOG_), 'a') as f:
        f.write(filename)
        f.write('\n')
    return None 

def main(
        fit_target_dir,
        fit_processed_csv_dir,
        fit_overwrite,
        fit_ignore_splits_and_laps,
):

    ALT_LOG = os.path.join(fit_processed_csv_dir, ALT_LOG_)
    files = os.listdir(fit_target_dir)
    fit_files = [file for file in files if file[-4:].lower()=='.fit']
    overwritten_files = []
    
    if not os.path.exists(ALT_LOG):
        os.system('touch %s' % ALT_LOG)
        file_list = []
    else:
        file_list = read_log(fit_processed_csv_dir)
        
    for file in fit_files:
        is_overwritten=False
        if file in file_list and not fit_overwrite:
            continue
        elif file in file_list:
            is_overwritten=True
            
        new_filename = file[:-4] + '.csv'
        
        fitfile = fitparse.FitFile(
            os.path.join(fit_target_dir, file),  
            data_processor=fitparse.StandardUnitsDataProcessor()
        )
        
        print('converting %s' % os.path.join(fit_target_dir, file))
        write_fitfile_to_csv(
            fitfile,
            new_filename,
            file,
            fit_target_dir,
            fit_processed_csv_dir,
            is_overwritten,
            fit_ignore_splits_and_laps,
        )
    print('finished conversions')

def lap_filename(output_filename):
    return output_filename[:-4] + '_laps.csv'

def start_filename(output_filename):
    return output_filename[:-4] + '_starts.csv'

def get_timestamp(messages):
    for m in messages:
        fields = m.fields
        for f in fields:
            if f.name == 'timestamp':
                return f.value
    return None

def get_event_type(messages):
    for m in messages:
        fields = m.fields
        for f in fields:
            if f.name == 'sport':
                return f.value
    return None

def write_fitfile_to_csv(
        fitfile,
        output_file='test_output.csv',
        original_filename=None,
        fit_target_dir=None, #raises errors if not defined
        fit_processed_csv_dir=None, #raises errors if not defined
        is_overwritten=False,
        fit_ignore_splits_and_laps=False
):
    tz_name = ''
    local_tz = CST
    changed_tz = False
    position_long = None
    position_lat = None
    messages = fitfile.messages
    data = []
    lap_data = []
    start_data = []
    #this should probably work, but it's possibly 
    #based on a certain version of the file/device
    timestamp = get_timestamp(messages)
    event_type = get_event_type(messages)
    if event_type is None:
        event_type = 'other'
    output_file = event_type + '_' + timestamp.strftime('%Y-%m-%d_%H-%M-%S.csv')
    
    for m in messages:
        skip=False
        skip_lap = False 
        skip_start = False 
        if not hasattr(m, 'fields'):
            continue
        fields = m.fields
        #check for important data types
        mdata = {}
        for field in fields:
            if not changed_tz and field.name in ['position_lat','position_long', 'start_position_lat','start_position_long']:
                if 'lat' in field.name:
                    try:
                        position_lat = float(field.value)
                    except TypeError:
                        pass
                else:
                    try:
                        position_long = float(field.value)
                    except TypeError:
                        pass
                if position_lat is not None and position_long is not None:
                    changed_tz = True
                    tz_name = tzwhere.tzNameAt(position_lat, position_long)
                    local_tz = pytz.timezone(tz_name)
                    if tz_name != 'US/Central':
                        print('Using timezone %s' % tz_name)
                    
                
            if field.name in all_allowed_fields:
                # currently saving timezone conversion to end, but keeping this here for now
                if field.name=='timestamp' and False:
                    mdata[field.name] = UTC.localize(field.value).astimezone(local_tz)
                else:
                    mdata[field.name] = field.value
        # this is sort of a janky way of determining field type, but it works for now
        for rf in required_fields:
            if rf not in mdata:
                skip=True
        for lrf in lap_required_fields:
            if lrf not in mdata:
                skip_lap = True 
        for srf in start_required_fields:
            if srf not in mdata:
                skip_start = True
        if not skip:
            data.append(mdata)
        elif not skip_lap:
            lap_data.append(mdata)
        elif not skip_start:
            start_data.append(mdata)

    # localize timezone
    for row in data + lap_data + start_data:
        if 'timestamp' in row:
            row['timestamp_utc'] = row['timestamp']
            row['timestamp'] = UTC.localize(row['timestamp']).astimezone(local_tz)
            row['timezone'] = tz_name
            
    #write to csv
    #general track info
    with open(os.path.join(fit_processed_csv_dir, output_file), 'w') as f:
        writer = csv.writer(f)
        writer.writerow(allowed_fields)
        for entry in data:
            writer.writerow([ str(entry.get(k, '')) for k in allowed_fields])

    if not fit_ignore_splits_and_laps:
        #lap info
        with open(os.path.join(fit_processed_csv_dir, lap_filename(output_file)), 'w') as f:
            writer = csv.writer(f)
            writer.writerow(lap_fields)
            for entry in lap_data:
                writer.writerow([ str(entry.get(k, '')) for k in lap_fields])
        #start/stop info
        with open(os.path.join(fit_processed_csv_dir, start_filename(output_file)), 'w') as f:
            writer = csv.writer(f)
            writer.writerow(start_fields)
            for entry in start_data:
                writer.writerow([ str(entry.get(k, '')) for k in start_fields])
    print('wrote %s' % output_file)
    if not fit_ignore_splits_and_laps:
        print('wrote %s' % lap_filename(output_file))
        print('wrote %s' % start_filename(output_file))

    if not is_overwritten:
        append_log(original_filename, fit_processed_csv_dir)

    if not changed_tz:
        print('TZ IS NOT CHANGED!')

if __name__=='__main__':
    raise NotImplementedError('There is no way to currently run this as a command-line script. It must be imported. Run process_all.py instead.')
    main()
