import os
import shutil
import re

import convert_fit_to_csv

#ACTIVITY_DIRECTORY = '/media/max/GARMIN/Garmin/ACTIVITY/'

#TARGET_DIRECTORY = '/ntfsl/data/workouts/workout_gpx/garmin_fit/'

FNAME_REGEX = re.compile(r'\.[Ff][Ii][Tt]')



def main(
        fit_source_dir,
        fit_target_dir,
        fit_processed_csv_dir,
        fit_overwrite,
        fit_ignore_splits_and_laps,
):
    os.makedirs(fit_target_dir, exist_ok=True)
    os.makedirs(fit_processed_csv_dir, exist_ok=True)
    activity_files = os.listdir(fit_source_dir)
    print('activity files: ', activity_files)
    new_names = [FNAME_REGEX.sub('.fit', file) for file in activity_files]
    print('new names: ', new_names)
    current_files = set(os.listdir(fit_target_dir))
    print('current_files: ', current_files)
    for src_file, tgt_file in zip(activity_files, new_names):
        if FNAME_REGEX.sub('.fit', tgt_file) in current_files:
            print('%s already exists...' % tgt_file)
            continue
        else:
            pass
        shutil.copyfile(
            os.path.join(fit_source_dir, src_file),
            os.path.join(fit_target_dir, tgt_file)
        )
        print("copied %s to %s" % (
            os.path.join(fit_source_dir, src_file),
            os.path.join(fit_target_dir, tgt_file)
        )
        )

    convert_fit_to_csv.main(
        fit_target_dir,
        fit_processed_csv_dir,
        fit_overwrite,
        fit_ignore_splits_and_laps,
    )
    
    #os.chdir(fit_target_dir)
    #os.system('python3 convert_fit_to_csv.py')

if __name__=='__main__':
    main()
