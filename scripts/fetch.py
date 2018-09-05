""" Download packages and extract images based on dlinks.txt files.

Check the configuration below, then run this script. Compatible with python 2
and 3.

"""

import multiprocessing
import os
import subprocess
import shutil
import sys
import tarfile
import tempfile

tempfile.gettempdir()

# Configuration

# Extracted images will be copied to this dir relative to the dlinks.txt
# file location
IMAGE_SUBDIR = 'images'

DLINKS_FOLDERS = [
    'data/test/radiology',
    'data/test/non-radiology',
    'data/train/radiology',
    'data/train/non-radiology',
    'data/validation/radiology',
    'data/validation/non-radiology',
]

# Change this if you want to store the extracted files somewhere persistently
EXTRACTION_DIR = os.path.join(tempfile.tempdir, 'roco-dataset')
# Change to True to keep archives after extraction (you should change
# EXTRACTION_DIR as well)
KEEP_ARCHIVES = False

# Number of images to fetch in parallel; setting this too high may get you
# temporarily banned from accessing the PMC FTP service
NUM_PROCESSES = 4

# Configuration end


def init(args):
    global counter
    counter = args


def log_status(index, target_filename, num_images):
    print("{:.3%}".format(1. * index / num_images) + ' | '
          + str(index) + '/' + str(num_images) + ' | '
          + os.path.basename(target_filename))


def extract_image_info(line, image_dir):
    line_parts_tab = line.split("\t")
    image_name = line_parts_tab[-1].strip()
    archive_url = line_parts_tab[1].split(' ')[2]
    pmc_id = archive_url.split(os.sep)[-1][:-7]
    target_filename = pmc_id + '_' + image_name

    return archive_url, image_name, pmc_id, \
           os.path.join(image_dir, target_filename)


def provide_extraction_dir():
    if not os.path.exists(EXTRACTION_DIR):
        os.makedirs(EXTRACTION_DIR, 0o755)


def remove_extraction_dir():
    shutil.rmtree(EXTRACTION_DIR, True)


def determine_number_of_images(dlinks_folder):
    with open(os.path.join(dataset_dir, dlinks_folder, 'dlinks.txt')) as \
            dlinks_file:
        return sum(1 for line in dlinks_file)


def collect_dlinks_lines():
    lines = []
    for folder in DLINKS_FOLDERS:
        filename = os.path.join(dataset_dir, folder, 'dlinks.txt')
        image_dir = os.path.join(os.path.dirname(filename), IMAGE_SUBDIR)
        if not os.path.exists(image_dir):
            os.mkdir(image_dir, 0o755)

        with open(filename) as \
                dlinks_file:
            lines.extend([[line.rstrip('\n'), folder] for line in dlinks_file])

    return lines


def download_and_extract_archive(archive_url, pmc_id, extraction_dir_name,
                                 image_name,
                                 target_filename):
    # download archive if it doesn't exist
    archive_filename = os.path.join(extraction_dir_name,
                                    archive_url.split(os.sep)[-1])

    if not os.path.exists(archive_filename):
        subprocess.call(
            ['wget', '-nd', '-q', '-P', extraction_dir_name, archive_url])

    archive_tarfile = tarfile.open(archive_filename)

    image_name_in_archive = pmc_id + os.sep + image_name
    image_tarinfo = archive_tarfile.getmember(image_name_in_archive)

    # extract image to extraction dir, then copy to target file name
    archive_tarfile.extractall(extraction_dir_name, [image_tarinfo])
    image_filename = os.path.join(extraction_dir_name, image_name_in_archive)
    shutil.copy(image_filename, target_filename)

    # remove image and archive from extraction dir
    shutil.rmtree(os.path.join(extraction_dir_name, pmc_id), True)
    if not KEEP_ARCHIVES:
        os.remove(archive_filename)


def process_line(line_and_folder):
    image_dir = os.path.join(dataset_dir, line_and_folder[1], IMAGE_SUBDIR)
    archive_url, image_name, pmc_id, target_filename \
        = extract_image_info(line_and_folder[0], image_dir)
    with counter.get_lock():
        counter.value += 1
        log_status(counter.value, target_filename, num_images)
    if not os.path.exists(target_filename):
        download_and_extract_archive(
            archive_url, pmc_id, EXTRACTION_DIR,
            image_name, os.path.join(image_dir, target_filename))


counter = None

if __name__ == '__main__':
    print('\rFetching ROCO dataset images...')
    dataset_dir = os.path.dirname(os.path.abspath(os.path.realpath(sys.argv[0])
                                                  + '/..'))
    lines = collect_dlinks_lines()
    num_images = len(lines)
    provide_extraction_dir()

    counter = multiprocessing.Value('i', 0)
    pool = multiprocessing.Pool(processes=NUM_PROCESSES, maxtasksperchild=10,
                                initializer=init, initargs=(counter, ))
    pool.map(process_line, lines, chunksize=1)
    pool.close()
    pool.join()

    if not KEEP_ARCHIVES:
        remove_extraction_dir()
