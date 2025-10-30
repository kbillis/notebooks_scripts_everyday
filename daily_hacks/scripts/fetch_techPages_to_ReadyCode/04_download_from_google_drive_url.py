import os
import re
import subprocess
from tqdm import tqdm

def install_gdown_if_needed():
    """Check if gdown is installed and install if needed."""
    try:
        import gdown
        print("gdown is already installed")
    except ImportError:
        print("Installing gdown...")
        subprocess.check_call(["pip", "install", "gdown"])
        print("gdown installed successfully")

def extract_file_id(drive_link):
    """Extract file ID from a Google Drive link."""
    # Pattern to extract the file ID from Google Drive links
    pattern = r'https://drive\.google\.com/file/d/([a-zA-Z0-9_-]+)/view'
    match = re.search(pattern, drive_link)
    if match:
        return match.group(1)
    return None

def download_drive_files(links_file, output_folder="downloaded_files", failed_links_file="failed_links.txt"):
    """
    Download all Google Drive files from the links in the specified file.
    Skips files that have already been downloaded.
    Records failed links in a separate file.
    Handles specific issues with Google Drive downloads.
    """
    # Import required libraries
    import gdown
    import subprocess
    import shutil
    
    # Create output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"Created output folder: {output_folder}")
    
    # Read links from file
    with open(links_file, "r", encoding="utf-8") as file:
        links = file.read().splitlines()
    
    print(f"Found {len(links)} links to process")
    
    # Track statistics
    successful_downloads = 0
    failed_downloads = 0
    skipped_downloads = 0
    failed_links = []  # List to store failed links
    
    for link in tqdm(links, desc="Processing files"):
        if not link.strip():  # Skip empty lines
            continue
            
        file_id = extract_file_id(link)
        if not file_id:
            print(f"Could not extract file ID from: {link}")
            failed_downloads += 1
            failed_links.append(f"INVALID_ID: {link}")
            continue
        
        # Create paths for potential existing files
        base_output_path = os.path.join(output_folder, file_id)
        possible_paths = [
            base_output_path,
            f"{base_output_path}.zip",
            f"{base_output_path}.pdf",
            f"{base_output_path}.jpg",
            f"{base_output_path}.png",
            f"{base_output_path}.docx",
            f"{base_output_path}.xlsx"
        ]
        
        # Check if file already exists with any common extension
        file_exists = False
        existing_path = None
        
        for path in possible_paths:
            if os.path.exists(path) and os.path.getsize(path) > 0:
                file_exists = True
                existing_path = path
                break
        
        if file_exists:
            print(f"Skipping {file_id} - already downloaded as {os.path.basename(existing_path)}")
            skipped_downloads += 1
            continue
            
        try:
            # Create a clean output path using just the file ID
            output_path = base_output_path
            
            # First try with gdown
            success = False
            url = f"https://drive.google.com/uc?id={file_id}"
            
            try:
                downloaded_path = gdown.download(url, output_path, quiet=False)
                if downloaded_path and os.path.exists(downloaded_path) and os.path.getsize(downloaded_path) > 0:
                    success = True
                else:
                    print(f"gdown download failed or produced empty file for {file_id}")
            except Exception as e:
                print(f"gdown failed for {file_id}: {str(e)}")
            
            # If gdown fails, try wget as a fallback
            if not success:
                try:
                    print(f"Trying wget for {file_id}")
                    # Use wget to download the file
                    wget_command = f"wget -q -O {output_path} 'https://drive.google.com/uc?id={file_id}'"
                    result = subprocess.run(wget_command, shell=True, check=True)
                    
                    # Check if file was downloaded and is not empty
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                        success = True
                        print(f"Successfully downloaded with wget: {output_path}")
                    else:
                        print(f"wget download failed or produced empty file for {file_id}")
                except subprocess.CalledProcessError as e:
                    print(f"wget failed for {file_id}: {str(e)}")
            
            # Check file type and rename if needed
            if success:
                try:
                    import magic  # python-magic library for file type detection
                    file_type = magic.from_file(output_path, mime=True)
                    
                    # Add appropriate extension based on MIME type
                    extension_map = {
                        'application/zip': '.zip',
                        'application/x-zip-compressed': '.zip',
                        'application/pdf': '.pdf',
                        'image/jpeg': '.jpg',
                        'image/png': '.png',
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
                        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx'
                    }
                    
                    if file_type in extension_map:
                        new_path = f"{output_path}{extension_map[file_type]}"
                        shutil.move(output_path, new_path)
                        print(f"Renamed file with extension: {os.path.basename(new_path)}")
                        output_path = new_path
                except ImportError:
                    # If magic is not available, check file headers manually for common formats
                    with open(output_path, 'rb') as f:
                        header = f.read(8)
                        if header.startswith(b'PK\x03\x04'):  # ZIP file signature
                            new_path = f"{output_path}.zip"
                            shutil.move(output_path, new_path)
                            print(f"Renamed zip file: {os.path.basename(new_path)}")
                            output_path = new_path
                        elif header.startswith(b'%PDF'):  # PDF file signature
                            new_path = f"{output_path}.pdf"
                            shutil.move(output_path, new_path)
                            print(f"Renamed PDF file: {os.path.basename(new_path)}")
                            output_path = new_path
                        # Add more file header checks here if needed
            
            if success:
                successful_downloads += 1
            else:
                failed_downloads += 1
                failed_links.append(f"DOWNLOAD_FAILED: {link}")
                print(f"Failed to download: {link}")
                
        except Exception as e:
            failed_downloads += 1
            failed_links.append(f"ERROR: {link} - {str(e)}")
            print(f"Error downloading {link}: {str(e)}")
    
    # Save failed links to file
    if failed_links:
        with open(failed_links_file, "w", encoding="utf-8") as f:
            f.write("# Failed downloads\n")
            f.write("# Format: [ERROR_TYPE]: [LINK] - [ERROR_MESSAGE]\n\n")
            f.write("\n".join(failed_links))
        print(f"Saved {len(failed_links)} failed links to {failed_links_file}")
    
    # Print summary
    print(f"\nDownload summary:")
    print(f"  - Total links: {len(links)}")
    print(f"  - Successfully downloaded: {successful_downloads}")
    print(f"  - Skipped (already downloaded): {skipped_downloads}")  
    print(f"  - Failed: {failed_downloads}")
    
    return output_folder


def download_drive_files_02(links_file, output_folder="downloaded_files", failed_links_file="failed_links.txt"):
    """
    Download all Google Drive files from the links in the specified file.
    Records failed links in a separate file.
    Handles specific issues with Google Drive downloads.
    """
    # Import required libraries
    import gdown
    import subprocess
    import shutil
    
    # Create output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"Created output folder: {output_folder}")
    
    # Read links from file
    with open(links_file, "r", encoding="utf-8") as file:
        links = file.read().splitlines()
    
    print(f"Found {len(links)} links to process")
    
    # Track successful and failed downloads
    successful_downloads = 0
    failed_downloads = 0
    failed_links = []  # List to store failed links
    
    for link in tqdm(links, desc="Downloading files"):
        if not link.strip():  # Skip empty lines
            continue
            
        file_id = extract_file_id(link)
        if not file_id:
            print(f"Could not extract file ID from: {link}")
            failed_downloads += 1
            failed_links.append(f"INVALID_ID: {link}")
            continue
            
        try:
            # Create a clean output path using just the file ID
            output_path = os.path.join(output_folder, file_id)
            
            # First try with gdown
            success = False
            url = f"https://drive.google.com/uc?id={file_id}"
            
            try:
                downloaded_path = gdown.download(url, output_path, quiet=False)
                if downloaded_path:
                    success = True
            except Exception as e:
                print(f"gdown failed for {file_id}: {str(e)}")
            
            # If gdown fails, try wget as a fallback
            if not success:
                try:
                    print(f"Trying wget for {file_id}")
                    # Use wget to download the file
                    wget_command = f"wget -q -O {output_path} 'https://drive.google.com/uc?id={file_id}'"
                    result = subprocess.run(wget_command, shell=True, check=True)
                    
                    # Check if file was downloaded and is not empty
                    if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                        success = True
                        print(f"Successfully downloaded with wget: {output_path}")
                    else:
                        print(f"wget download failed or produced empty file for {file_id}")
                except subprocess.CalledProcessError as e:
                    print(f"wget failed for {file_id}: {str(e)}")
            
            # Check if file is a zip and needs to be renamed
            if success:
                try:
                    import magic  # python-magic library for file type detection
                    file_type = magic.from_file(output_path, mime=True)
                    
                    if file_type in ['application/zip', 'application/x-zip-compressed']:
                        # Rename with .zip extension
                        new_path = f"{output_path}.zip"
                        shutil.move(output_path, new_path)
                        print(f"Renamed zip file: {new_path}")
                        output_path = new_path
                except ImportError:
                    # If magic is not available, check file headers manually
                    with open(output_path, 'rb') as f:
                        header = f.read(4)
                        if header.startswith(b'PK\x03\x04'):  # ZIP file signature
                            new_path = f"{output_path}.zip"
                            shutil.move(output_path, new_path)
                            print(f"Renamed zip file: {new_path}")
                            output_path = new_path
            
            if success:
                successful_downloads += 1
            else:
                failed_downloads += 1
                failed_links.append(f"DOWNLOAD_FAILED: {link}")
                print(f"Failed to download: {link}")
                
        except Exception as e:
            failed_downloads += 1
            failed_links.append(f"ERROR: {link} - {str(e)}")
            print(f"Error downloading {link}: {str(e)}")
    
    # Save failed links to file
    if failed_links:
        with open(failed_links_file, "w", encoding="utf-8") as f:
            f.write("# Failed downloads\n")
            f.write("# Format: [ERROR_TYPE]: [LINK] - [ERROR_MESSAGE]\n\n")
            f.write("\n".join(failed_links))
        print(f"Saved {len(failed_links)} failed links to {failed_links_file}")
    
    # Print summary
    print(f"\nDownload summary:")
    print(f"  - Total links: {len(links)}")
    print(f"  - Successfully downloaded: {successful_downloads}")
    print(f"  - Failed: {failed_downloads}")
    
    return output_folder

def downloaid_drive_files_02(links_file, output_folder="downloaded_files", failed_links_file="failed_links.txt"):
    """
    Download all Google Drive files from the links in the specified file.
    Records failed links in a separate file.
    """
    # Import gdown (after ensuring it's installed)
    import gdown
    
    # Create output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"Created output folder: {output_folder}")
    
    # Read links from file
    with open(links_file, "r", encoding="utf-8") as file:
        links = file.read().splitlines()
    
    print(f"Found {len(links)} links to process")
    
    # Track successful and failed downloads
    successful_downloads = 0
    failed_downloads = 0
    failed_links = []  # List to store failed links
    
    for link in tqdm(links, desc="Downloading files"):
        if not link.strip():  # Skip empty lines
            continue
            
        file_id = extract_file_id(link)
        if not file_id:
            print(f"Could not extract file ID from: {link}")
            failed_downloads += 1
            failed_links.append(f"INVALID_ID: {link}")
            continue
            
        try:
            # The output parameter determines the filename
            # Using the file ID as filename initially
            output_path = os.path.join(output_folder, f"{file_id}")
            
            # Download the file
            url = f"https://drive.google.com/uc?id={file_id}"
            downloaded_path = gdown.download(url, output_path, quiet=False)
            
            if downloaded_path:
                successful_downloads += 1
                print(f"Successfully downloaded: {downloaded_path}")
            else:
                failed_downloads += 1
                failed_links.append(f"DOWNLOAD_FAILED: {link}")
                print(f"Failed to download: {link}")
                
        except Exception as e:
            failed_downloads += 1
            failed_links.append(f"ERROR: {link} - {str(e)}")
            print(f"Error downloading {link}: {str(e)}")
    
    # Save failed links to file
    if failed_links:
        with open(failed_links_file, "w", encoding="utf-8") as f:
            f.write("# Failed downloads\n")
            f.write("# Format: [ERROR_TYPE]: [LINK] - [ERROR_MESSAGE]\n\n")
            f.write("\n".join(failed_links))
        print(f"Saved {len(failed_links)} failed links to {failed_links_file}")
    
    # Print summary
    print(f"\nDownload summary:")
    print(f"  - Total links: {len(links)}")
    print(f"  - Successfully downloaded: {successful_downloads}")
    print(f"  - Failed: {failed_downloads}")
    
    return output_folder


def download_drive_files_no_list_failed(links_file, output_folder="downloaded_files"):
    """Download all Google Drive files from the links in the specified file."""
    # Import gdown (after ensuring it's installed)
    import gdown
    
     
    # Create output folder if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"Created output folder: {output_folder}")
    
    # Read links from file
    with open(links_file, "r", encoding="utf-8") as file:
        links = file.read().splitlines()
    
    print(f"Found {len(links)} links to process")
    
    # Download each file
    successful_downloads = 0
    failed_downloads = 0
    
    for link in tqdm(links, desc="Downloading files"):
        if not link.strip():  # Skip empty lines
            continue
            
        file_id = extract_file_id(link)
        if not file_id:
            print(f"Could not extract file ID from: {link}")
            failed_downloads += 1
            continue
        
        try:
            # The output parameter determines the filename
            # Using the file ID as filename initially
            output_path = os.path.join(output_folder, f"{file_id}")
            
            # Download the file
            url = f"https://drive.google.com/uc?id={file_id}"
            downloaded_path = gdown.download(url, output_path, quiet=False)
            
            if downloaded_path:
                successful_downloads += 1
                print(f"Successfully downloaded: {downloaded_path}")
            else:
                failed_downloads += 1
                print(f"Failed to download: {link}")
        
        except Exception as e:
            failed_downloads += 1
            print(f"Error downloading {link}: {str(e)}")
    
    print(f"\nDownload summary:")
    print(f"  - Total links: {len(links)}")
    print(f"  - Successfully downloaded: {successful_downloads}")
    print(f"  - Failed: {failed_downloads}")
    
    return output_folder

def main():
    # Install gdown if not already installed
    install_gdown_if_needed()
    
    # File containing Google Drive links
    links_file = "google_drive_links.txt"
    if not os.path.exists(links_file):
        links_file = input("Enter the path to your file containing Google Drive links: ")
    
    # Folder to save downloaded files
    output_folder = "downloaded_drive_files"
    
    # Download files
    downloaded_folder = download_drive_files(links_file, output_folder)
    print(f"All files have been downloaded to '{downloaded_folder}'")

if __name__ == "__main__":
    main()
