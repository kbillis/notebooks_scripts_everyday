#!/usr/bin/env python3
import os
import shutil
import sys



# how to run: find ./downloaded_drive_files/ -type f -not -path "*/\.*" | grep -v ".zip" | xargs -I{} python 06_check_file_format.py  "{}"

def check_file_type(file_path):
    """
    Check the file type based on its header bytes and rename it appropriately.
    """
    # Dictionary of common file signatures (magic numbers) and their corresponding extensions
    signatures = {
        b'PK\x03\x04': '.zip',                   # ZIP archive
        b'%PDF': '.pdf',                         # PDF document
        b'\xFF\xD8\xFF': '.jpg',                 # JPEG image
        b'\x89PNG\r\n\x1A\n': '.png',            # PNG image
        b'GIF8': '.gif',                         # GIF image
        b'\x25\x21PS': '.ps',                    # PostScript file
        b'\x7FELF': '.elf',                      # ELF file
        b'\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1': '.doc',  # MS Office file
        b'Rar!\x1A\x07\x00': '.rar',             # RAR archive
        b'Rar!\x1A\x07\x01\x00': '.rar',         # RAR archive 5.0
        b'\x50\x4B\x05\x06': '.zip',             # Empty ZIP archive
        b'\x50\x4B\x07\x08': '.zip',             # Spanned ZIP archive
        b'BZh': '.bz2',                          # BZip2 archive
        b'\x1F\x8B\x08': '.gz',                  # GZip archive
        b'SQLite format 3\x00': '.sqlite',       # SQLite database
        b'\x00\x00\x01\x00': '.ico',             # ICO image
        b'II*\x00': '.tif',                      # TIFF image
        b'MM\x00*': '.tif',                      # TIFF image
        b'\x00\x01\x00\x00\x00': '.ttf',         # TrueType font
        b'OTTO': '.otf',                         # OpenType font
        b'\x1A\x45\xDF\xA3': '.webm',            # WebM video
        b'\x52\x49\x46\x46': '.wav',             # WAV audio
    }
    
    # Try to determine file type by reading the header
    header_size = 16  # Read first 16 bytes to cover most signatures
    
    try:
        with open(file_path, 'rb') as f:
            header = f.read(header_size)
            
        # Check for various file signatures
        file_type = None
        for signature, extension in signatures.items():
            if header.startswith(signature):
                file_type = extension
                break
        
        # If we found a match, rename the file
        if file_type:
            new_path = file_path + file_type
            print(f"File signature identified as: {file_type[1:].upper()}")
            print(f"Renaming to: {new_path}")
            shutil.move(file_path, new_path)
            print("File renamed successfully.")
        else:
            print("Could not identify file type from signature.")
            
            # Additional check for text files
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    start = f.read(100)
                    if start and all(32 <= ord(c) <= 126 or c in '\n\r\t' for c in start):
                        print("File appears to be a text file.")
                        new_path = file_path + '.txt'
                        print(f"Renaming to: {new_path}")
                        shutil.move(file_path, new_path)
            except UnicodeDecodeError:
                print("File is likely a binary file of unknown format.")
        
        return True
    except Exception as e:
        print(f"Error checking file: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python check_file_type.py <file_path>")
        sys.exit(1)
        
    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        sys.exit(1)
        
    check_file_type(file_path)



