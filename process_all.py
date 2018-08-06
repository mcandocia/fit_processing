import os

import argparse

import import_and_process_garmin_fit
#import gpx_to_csv
import calculate_workout_variables
import censor_and_package

def main():
    options = parse_options()
    censor_search_directories = []
    
    if options['gpx_source_dir'] != '':
        if not options['skip_gpx_conversion']:
            print('doing GPX conversions')
            calculate_workout_variables.main(
                options['gpx_source_dir'],
                options['gpx_target_dir'],
                options['gpx_summary_filename'],

            )
        censor_search_directories.append(options['gpx_target_dir'])

    if options['fit_source_dir'] != '':
        if not options['skip_fit_conversion']:
            print('doing FIT conversions')
            import_and_process_garmin_fit.main(
                options['fit_source_dir'],
                options['fit_target_dir'],
                options['fit_processed_csv_dir'],
                options['fit_overwrite'],
                options['fit_ignore_splits_and_laps'],
            )
        censor_search_directories.append(options['fit_processed_csv_dir'])

    # even if no censoring is done, archiving can still be done here
    if True: #options['censorfile'] != '' and len(censor_search_directories) > 0:
        censor_target_dir = os.path.join(options['subject_dir'], options['name'], 'censored')
        censor_and_package.main(
            censor_search_directories,
            censor_target_dir,
            options['censorfile'],
            options['censor_string'],
            # will be used to control archiving
            options
        )



def parse_options():
    parser = argparse.ArgumentParser(description='Run FIT/GPX Pipeline')
    parser.add_argument('--subject-name', dest='subject_name', type=str, required=True,
                        help='name of subject'
    )

    parser.add_argument('--fit-source-dir', dest='fit_source_dir', type=str,
                        default='/media/max/GARMIN/Garmin/ACTIVITY/',
                        help='source data for garmin fit'
    )

    parser.add_argument('--fit-target-dir', dest='fit_target_dir', required=False,
                        default='',
                        help='target directory for FIT data; default uses subject name'
    )

    parser.add_argument('--fit-processed-csv-dir', dest='fit_processed_csv_dir', required=False,
                        default='',
                        help='target directory for CSVs of processed fit data; default uses subject name'
    )

    #TODO
    parser.add_argument('--erase-copied-fit-files', dest='erase_copied_fit_files', required=False,
                        action='store_true',
                        help='If True, will delete any copied FIT files (not the originals, though)'
    )

    parser.add_argument('--gpx-source-dir', dest='gpx_source_dir',required=False, default='',
                        help='directory for gpx files (if desired)',
    )

    parser.add_argument('--gpx-target-dir', dest='gpx_target_dir', required=False,
                        default='',
                        help='directory to store processed gpx csv in'
    )

    parser.add_argument('--subject-dir', dest='subject_dir',
                        default=os.path.join(os.getcwd(), 'subject_data'),
                        help='default directory to store subject data in',
    )

    parser.add_argument('--gpx-summary-filename', dest='gpx_summary_filename',
                        default='gpx_summary.csv',
                        help='the summary filename for gpx data'
    )

    parser.add_argument('--fit-overwrite', dest='fit_overwrite',
                        action='store_true', default=False, required=False,
                        help='Will overwrite any previously created CSVs from fit data'
    )

    parser.add_argument('--fit-ignore-splits-and-laps', dest='fit_ignore_splits_and_laps',
                        action='store_true', default=False, required=False,
                        help='Will not write split/lap data if specified'
    )

    # censorship arguments

    parser.add_argument('--censorfile', dest='censorfile', required=False,
                        default='',
                        help='If provided, will use censorfile CSV to create a copy of data '
                        'with censored locations around different latitude/longitude/radii'
    )

    parser.add_argument('--censor-string', dest='censor_string', required=False,
                        default='[CENSORED]',
                        help='This is what censored fields are replaced with in censored data'
    )

    parser.add_argument('--archive-results', dest='archive_results', action='store_true',
                        default=False,
                        help='If True, will package data into an archive'
    )

    parser.add_argument('--archive-censored-only', dest='archive_censored_only',
                        action='store_true',
                        default=False,
                        help='If True, will only package data that is censored'
    )

    parser.add_argument('--archive-extra-files', nargs='+', dest="archive_extra_files",
                        required=False,
                        help="Will copy these extra files into an archive if it is being "
                        "created"
    )

    parser.add_argument('--archive-output-dir', dest='archive_output_dir',
                        required=False, default='archives',
                        help="location for archived output"
    )

    parser.add_argument('--archive-filename', dest='archive_filename',
                        required=False, default='',
                        help='archive filename; will use name for default if none specified'
    )



    # skip steps to allow archiving/censoring without other processing

    parser.add_argument('--skip-gpx-conversion', dest='skip_gpx_conversion',
                        action='store_true', required=False,
                        help='Skips GPX conversion if used',
    )

    parser.add_argument('--skip-fit-conversion', dest='skip_fit_conversion',
                        action='store_true', required=False,
                        help='Skips FIT conversion if used'
    )

    args = parser.parse_args()
    
    options = vars(args)
    name = options['subject_name'].lower().replace(' ','_')
    options['root_subject_dir'] = os.path.join(options['subject_dir'], name)
    options['name'] = name
    if options['archive_extra_files'] is None:
        options['archive_extra_files'] = []
    # clean up some empty data
    if options['gpx_target_dir']=='':
        options['gpx_target_dir']=os.path.join(options['subject_dir'], name, 'gpx_csv')

    if options['fit_target_dir']=='':
        options['fit_target_dir']=os.path.join(options['subject_dir'], name, 'fit_files')

    if options['fit_processed_csv_dir']=='':
        options['fit_processed_csv_dir']=os.path.join(options['subject_dir'], name, 'fit_csv')

    if options['archive_filename'] == '':
        options['archive_filename']=name
        
    if options['archive_output_dir'][0] != '/':
        options['archive_output_dir'] = os.path.join(options['subject_dir'], options['archive_output_dir'])


    return options

    

if __name__=='__main__':
    main()


if False:
    print('cleaning GPS data and importing from garmin...')
    os.system('python calculate_workout_variables.py')
    os.system('python gpx_to_csv.py')
    os.system('python3 import_and_process_garmin_fit.py')
    print('cleaned GPS data and imported from garmin...')
