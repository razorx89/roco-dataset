""" Download packages and extract images based on dlinks.txt files. """

import argparse
import multiprocessing
import os
import subprocess
import shutil
import sys
import tarfile
import tempfile

tempfile.gettempdir()

DLINKS_FOLDERS = [
    'data/test/radiology',
    'data/test/non-radiology',
    'data/train/radiology',
    'data/train/non-radiology',
    'data/validation/radiology',
    'data/validation/non-radiology',
]


def init(argsp):
    global args
    args = argsp


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
    if not os.path.exists(args.extraction_dir):
        os.makedirs(args.extraction_dir, 0o755)


def remove_extraction_dir():
    shutil.rmtree(args.extraction_dir, True)


def determine_number_of_images(dlinks_folder):
    with open(os.path.join(dataset_dir, dlinks_folder, 'dlinks.txt')) as \
            dlinks_file:
        return sum(1 for line in dlinks_file)


def collect_dlinks_lines():
    lines = []
    for folder in DLINKS_FOLDERS:
        filename = os.path.join(dataset_dir, folder, 'dlinks.txt')
        image_dir = os.path.join(os.path.dirname(filename), args.subdir)
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
    if not args.keep_archives:
        os.remove(archive_filename)


def process_line(line_and_folder):
    image_dir = os.path.join(dataset_dir, line_and_folder[1], args.subdir)
    archive_url, image_name, pmc_id, target_filename \
        = extract_image_info(line_and_folder[0], image_dir)

    if not os.path.exists(target_filename):
        download_and_extract_archive(
            archive_url, pmc_id, args.extraction_dir,
            image_name, os.path.join(image_dir, target_filename))

    return target_filename


def parse_args():
    parser = argparse.ArgumentParser(
        description=__doc__.strip(),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        '-s', '--subdir',
        help='name of image subdirectory, relative to dlinks.txt location',
        default='images'
    )

    parser.add_argument(
        '-e', '--extraction-dir',
        help='path to the extraction directory where downloaded archives and '
             + 'images are stored',
        default=os.path.join(tempfile.tempdir, 'roco-dataset'),
    )

    parser.add_argument(
        '-k', '--keep-archives',
        help='keep downloaded archives after extraction. Ensure sufficient '
             + 'available disk space at the extraction directory location',
        action='store_true',
    )

    parser.add_argument(
        '-n', '--num-processes',
        help='Number of parallel processes, reduce this if you are being '
             + 'locked out of the PMC FTP service',
        default=multiprocessing.cpu_count(),
        type=int,
    )

    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()

    print('\rFetching ROCO dataset images...')
    dataset_dir = os.path.dirname(os.path.abspath(os.path.realpath(sys.argv[0])
                                                  + '/..'))
    lines = collect_dlinks_lines()
    num_images = len(lines)
    provide_extraction_dir()

    pool = multiprocessing.Pool(processes=args.num_processes,
                                maxtasksperchild=10, initializer=init,
                                initargs=(args, ))
    for i, file in enumerate(pool.imap_unordered(process_line, lines)):
        log_status(i, file, num_images)

    pool.close()
    pool.join()

    if not args.keep_archives:
        remove_extraction_dir()
