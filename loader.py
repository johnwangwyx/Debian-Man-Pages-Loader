import requests
import os
import gzip
import tarfile
import shutil
import arpy
import re
from concurrent.futures import ThreadPoolExecutor, as_completed

ARCH = "binary-amd64"
DEB_PACKAGE_URL = f"https://ftp.debian.org/debian/dists/Debian12.5/main/{ARCH}/Packages.gz"
UNPACKING_DIR = 'man_data'
MAN_PAGE_DIR = os.path.join(UNPACKING_DIR, 'man_pages')

def extract_deb(data_path, extract_to):
    print(f"Extracting DEB package: {data_path} to {extract_to}")
    if not os.path.exists(extract_to):
        os.makedirs(extract_to)

    # Open the DEB file as an AR archive
    with arpy.Archive(data_path) as archive:
        archive.read_all_headers()
        for name in archive.archived_files:
           if name.startswith(b'data.tar'):
                content = archive.archived_files[name]
                # Determine the compression based on the file extension
                if name.endswith(b'.gz'):
                    tar_mode = 'r:gz'
                elif name.endswith(b'.xz'):
                    tar_mode = 'r:xz'
                else:
                    tar_mode = 'r'
                
                # Write the data.tar content to a temporary file and extract
                tar_path = os.path.join(extract_to, name.decode())
                with open(tar_path, 'wb') as tar_file:
                    tar_file.write(content.read())

                # Extract the tar file using tarfile
                with tarfile.open(tar_path, mode=tar_mode) as tar:
                    tar.extractall(path=extract_to)

def download_file(url):
    print(f"Downloading file from {url}")
    local_filename = url.split('/')[-1]
    with requests.get(url, stream=True) as r:
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    return local_filename

def extract_gz(file_path):
    print(f"Extracting gzip file {file_path}")
    with gzip.open(file_path, 'rb') as f:
        with open(file_path.replace('.gz', ''), 'wb') as f_out:
            f_out.write(f.read())

def move_and_clean_man_pages(extract_to, man_dest_folder):
    print(f"Scanning and moving man pages from {extract_to} to {man_dest_folder}")
    man_page_regex = re.compile(r'(usr\\share\\man\\|usr\\man\\|usr\\X11R6\\man\\|usr\\local\\man/|opt\\man\\)')
    
    # Ensure destination folder exists
    if not os.path.exists(man_dest_folder):
        os.makedirs(man_dest_folder)
    
    # Walk through the directory structure
    for root, dirs, files in os.walk(extract_to):
        # Check if current directory matches the man page directory pattern
        if man_page_regex.search(root):
            for file in files:
                if file.endswith('.gz'):
                    src_file = os.path.join(root, file)
                    # Remove the .gz extension for the destination file
                    dst_file = os.path.join(man_dest_folder, file[:-3])  # Strip '.gz' from filename
     
                    if not os.path.exists(dst_file):
                        # Decompress and move
                        with gzip.open(src_file, 'rb') as f_in:
                            with open(dst_file, 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                        print(f"Decompressed and moved {src_file} to {dst_file}")
                        os.remove(src_file)
                    else:
                        print(f"File {dst_file} already exists. Skipping.")

    # Clean up the entire extracted directory structure
    shutil.rmtree(extract_to)
    print(f"Cleaned up extraction directory {extract_to}")

def download_and_process_package(link, dest_folder, man_dest_folder):
    print(f"Processing package: {link}")
    full_link = f"http://ftp.ca.debian.org/debian/{link}"
    deb_path = download_file(full_link)
    extract_to = os.path.join(dest_folder, os.path.basename(deb_path).replace('.deb', ''))
    extract_deb(deb_path, extract_to)
    move_and_clean_man_pages(extract_to, man_dest_folder)
    os.remove(deb_path)  # Remove the .deb file to free up space
    print(f"Completed processing of {deb_path}")

def main():
    # Ensure destination folders exist
    if not os.path.exists(UNPACKING_DIR):
        os.makedirs(UNPACKING_DIR)

    # Download and extract Packages file
    packages_path = download_file(DEB_PACKAGE_URL)
    extract_gz(packages_path)

    with open(packages_path.replace('.gz', ''), 'r', encoding='utf-8') as f:
        lines = f.readlines()

    deb_links = [line.split(' ')[1].strip() for line in lines if line.startswith('Filename: ')]

    total_links = len(deb_links)
    print(f"Found {total_links} packages to process.")

    # Using ThreadPoolExecutor to process each package in a separate thread
    with ThreadPoolExecutor(max_workers=32) as executor:
        futures = {executor.submit(download_and_process_package, link, UNPACKING_DIR, MAN_PAGE_DIR): link for link in deb_links}
        completed = 0
        for future in as_completed(futures):
            completed += 1
            package = futures[future]
            try:
                result = future.result()
                print(f"Successfully processed [{completed}/{total_links}]: {result}")
            except Exception as exc:
                print(f"{package} generated an exception: {exc}")

if __name__ == '__main__':
    main()