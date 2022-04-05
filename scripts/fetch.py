""" Download packages and extract images based on dlinks.txt files. """

import argparse
import glob
import multiprocessing
import os
import subprocess
import shutil
import sys
import tarfile
import tempfile
import urllib.request
import xml.etree.ElementTree as ET
import zlib
import gzip

tempfile.gettempdir()

DLINKS_FOLDERS = [
    'data/test/radiology',
    'data/test/non-radiology',
    'data/train/radiology',
    'data/train/non-radiology',
    'data/validation/radiology',
    'data/validation/non-radiology',
]

PMCID_INFORMATION_API = 'https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?tool=roco-fetch&email=johannes.rueckert@fh-dortmund.de&id='


def init(argsp):
    global args
    args = argsp


def log_status(index, pmc_id, num_groups):
    print("{:.3%}".format(1. * index / num_groups) + ' | '
          + str(index) + '/' + str(num_groups) + ' | '
          + os.path.basename(pmc_id))


def extract_image_info(line, image_dir):
    line_parts_tab = line.split("\t")
    image_name = line_parts_tab[-1].strip()
    archive_url = line_parts_tab[1].split(' ')[2]
    pmc_id = archive_url.split("/")[-1][:-7]
    target_filename = line_parts_tab[0] + ".jpg"

    return archive_url, image_name, pmc_id, \
           os.path.join(image_dir, args.subdir, target_filename)


def provide_extraction_dir():
    if not os.path.exists(args.extraction_dir):
        os.makedirs(args.extraction_dir, 0o755)

    # Delete extraction directory contents if it's not empty
    elif len(os.listdir(args.extraction_dir)) > 0 and not args.keep_archives:
        if not args.delete_extraction_dir:
            raise Exception('The extraction directory {0} is not empty, ' +
                            'please pass -d if confirm deletion of its contents')

        files = glob.glob(os.path.join(args.extraction_dir, '*'))
        for f in files:
            if os.path.isdir(f):
                shutil.rmtree(f, True)
            else:
                os.remove(f)


def remove_extraction_dir():
    shutil.rmtree(args.extraction_dir, True)


def determine_number_of_images(dlinks_folder):
    with open(os.path.join(args.repository_dir, dlinks_folder, 'dlinks.txt')) as \
            dlinks_file:
        return sum(1 for _ in dlinks_file)


def collect_dlinks_lines():
    lines = []
    for folder in args.dlinks_folders:
        filename = os.path.join(args.repository_dir, folder, 'dlinks.txt')
        image_dir = os.path.join(os.path.dirname(filename), args.subdir)
        if not os.path.exists(image_dir):
            os.mkdir(image_dir, 0o755)

        with open(filename) as dlinks_file:
            lines.extend([[line.rstrip('\n'), folder] for line in dlinks_file])

    return lines


def group_lines_by_archive(lines):
    groups = {}
    for line, folder in lines:
        image_info = extract_image_info(line, folder)

        if groups.get(image_info[0]) is None:
            groups[image_info[0]] = []

        groups[image_info[0]].append(image_info)

    return groups


def process_group(group):
    archive_url = group[0][0]
    pmc_id = group[0][2]
    extraction_dir_name = args.extraction_dir

    archive_filename = os.path.join(extraction_dir_name,
                                    archive_url.split('/')[-1])

    # Skip if all images have already been extracted
    extraction_needed = False
    for _, _, _, target_filename in group:
        if not os.path.exists(os.path.join(args.repository_dir, target_filename)):
            extraction_needed = True
            break

    if not extraction_needed:
        return pmc_id + ' (not needed)'

    # delete archive if it exists to avoid problems with aborted downloads
    shutil.rmtree(archive_filename, True)

    num_download_retries = 1

    result = download_archive(extraction_dir_name, archive_url,
                              num_download_retries)

    # if wget returned an error, archive was moved; we try to find the new URL
    while result > 0 \
            or not os.path.exists(archive_filename):

        print('Error: download failed, retrying')

        if num_download_retries == 1:
            new_archive_url = determine_new_archive_url(archive_url)

            # abort if archive no longer on FTP
            if new_archive_url is None:
                return pmc_id + ' (FAILED)'

            if new_archive_url != archive_url:
                archive_url = new_archive_url

        num_download_retries += 1
        result = download_archive(extraction_dir_name, archive_url,
                                  num_download_retries)

    # collect and extract images from archive
    for _, image_name, pmc_id, target_filename in group:
        # do not extract if the image already exists
        if os.path.exists(os.path.join(args.repository_dir, target_filename)):
            continue

        image_name_in_archive = pmc_id + "/" + image_name

        extracted = False

        while not extracted:
            archive_tarfile = None
            download_again = False
            try:
                archive_tarfile = tarfile.open(archive_filename)
                member = archive_tarfile.getmember(image_name_in_archive)
                archive_tarfile.extractall(extraction_dir_name, [member])
            except KeyError as e:
                print('Error: failed to extract image {0} from archive {1}: {2}'
                      .format(image_name_in_archive, archive_url, e))
                break
            except (EOFError, tarfile.ReadError, zlib.error, gzip.BadGzipFile) as e:
                print('Error: failed to extract {0} ({1}), re-downloading...'
                      .format(archive_filename, e))
                num_download_retries += 1
                download_again = True
            else:
                extracted = True
            finally:
                if isinstance(archive_tarfile, tarfile.TarFile):
                    archive_tarfile.close()

                if download_again:
                    os.remove(archive_filename)
                    download_archive(extraction_dir_name, archive_url,
                                     num_download_retries)

        # download was successful, but image does not exist in archive, skip
        if not extracted:
            print('Image {0} not found in archive {1}, skipping'
                  .format(image_name_in_archive, archive_url))
            continue

        # copy extracted images to target folder
        image_filename = os.path.join(extraction_dir_name, pmc_id, image_name)
        shutil.copy(image_filename, os.path.join(args.repository_dir, target_filename))

    # remove group directory from extraction dir
    shutil.rmtree(os.path.join(extraction_dir_name, pmc_id), True)

    if not args.keep_archives:
        os.remove(archive_filename)

    return pmc_id


def download_archive(extraction_dir, archive_url, num_retries):
    if num_retries > args.num_retries:
        raise Exception("Giving up download of archive {0} after {1} tries"
                        .format(archive_url, num_retries))

    return subprocess.call(['wget', '-nc', '-nd', '-c', '-q', '-P',
                            extraction_dir, archive_url])


def determine_new_archive_url(current_archive_url):
    pmc_id = current_archive_url.split('/')[-1][:-7]
    request_url = PMCID_INFORMATION_API + pmc_id
    print('Trying to get new archive URL: ' + request_url)
    contents = urllib.request.urlopen(request_url).read()
    root = ET.fromstring(contents)

    for link in root.iter('link'):
        if link.get('format') == 'tgz':
            return link.get('href')

    # check if archive is available
    for error in root.iter('error'):
        code = error.get('code')
        if code == 'idIsNotOpenAccess':
            print('Archive {0} no longer open access'
                  .format(current_archive_url))
        elif code == 'idDoesNotExist':
            print('Archive {0} no longer exists'
                  .format(current_archive_url))
        else:
            print('API returned error code {0} for archive {1}'
                  .format(code, current_archive_url))

    return None


def parse_args():
    parser = argparse.ArgumentParser(
        description=__doc__.strip(),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        '-c', '--print-config',
        help='print configuration and exit',
        action='store_true'
    )

    parser.add_argument(
        '-s', '--subdir',
        help='name of image subdirectory, relative to dlinks.txt location',
        default='images'
    )

    parser.add_argument(
        '-e', '--extraction-dir',
        help='path to the directory where downloaded archives and '
             + 'images are extracted before being moved to the data subdirectory',
        default=os.path.join(tempfile.tempdir, 'roco-dataset'),
    )

    parser.add_argument(
        '-d', '--delete-extraction-dir',
        help='to avoid loss of data, this must be passed to confirm that all '
             + 'data in the extraction directory will be deleted',
        action='store_true',
    )

    parser.add_argument(
        '-k', '--keep-archives',
        help='keep downloaded archives after extraction. Ensure sufficient '
             + 'available disk space at the extraction directory location',
        action='store_true',
    )

    parser.add_argument(
        '-n', '--num-processes',
        help='number of parallel processes, reduce this if you are being '
             + 'locked out of the PMC FTP service',
        default=multiprocessing.cpu_count(),
        type=int,
    )

    parser.add_argument(
        '-r', '--num-retries',
        help='number of retries for failed downloads before giving up',
        default=10,
        type=int,
    )

    return parser.parse_args()


def print_config(args):
    print('Configuration:')
    print('Subdirectory: {0}'.format(args.subdir))
    print('Extraction directory: {0}'.format(args.extraction_dir))
    print('Keep archives: {0}'.format(args.keep_archives))
    print('Delete contents of extraction directory: {0}'
          .format(args.delete_extraction_dir))
    print('Number of processes: {0}'.format(args.num_processes))
    print('Number of download retries: {0}'.format(args.num_retries))


if __name__ == '__main__':
    # Make sure that wget is available
    if not shutil.which("wget"):
        print("wget not found, please install wget and put it on your PATH")
        exit(-1)
    args = parse_args()
    args.repository_dir = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
    args.dlinks_folders = DLINKS_FOLDERS

    print_config(args)

    if args.print_config:
        exit(0)

    print('Fetching ROCO dataset images...')

    lines = collect_dlinks_lines()
    groups = group_lines_by_archive(lines)
    num_groups = len(groups)
    provide_extraction_dir()

    pool = multiprocessing.Pool(processes=args.num_processes,
                                maxtasksperchild=100, initializer=init,
                                initargs=(args,))
    for i, pmc_id in enumerate(pool.imap_unordered(process_group,
                                                   groups.values())):
        log_status(i, pmc_id, num_groups)

    pool.close()
    pool.join()

    if not args.keep_archives:
        remove_extraction_dir()
