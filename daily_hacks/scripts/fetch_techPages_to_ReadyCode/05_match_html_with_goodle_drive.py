#!/usr/bin/env python3
import os
import re
import hashlib
import zipfile
import tempfile
from datetime import datetime
import difflib
from bs4 import BeautifulSoup
import argparse

def get_file_fingerprint(filepath):
    """Create a content fingerprint of the file."""
    with open(filepath, 'rb') as f:
        content = f.read()
        return hashlib.md5(content).hexdigest()

def get_html_title(html_file):
    """Extract title from HTML file."""
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
            soup = BeautifulSoup(content, 'html.parser')
            return soup.title.string if soup.title else None
    except:
        return None

def get_html_content_text(html_file):
    """Extract text content from HTML file."""
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
            soup = BeautifulSoup(content, 'html.parser')
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            return soup.get_text()
    except Exception as e:
        print(f"Error extracting text from {html_file}: {e}")
        return ""

def get_google_drive_id_from_html(html_file):
    """Try to find Google Drive IDs in the HTML content."""
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # Look for patterns that might represent Google Drive IDs
            # Common pattern for Google Drive file IDs
            pattern = r'[\w-]{25,33}'
            matches = re.findall(pattern, content)
            return matches
    except:
        return []

def compare_text_similarity(text1, text2):
    """Compare similarity between two text strings."""
    return difflib.SequenceMatcher(None, text1, text2).ratio()

def is_zip_file(filepath):
    """Check if the file is a ZIP archive."""
    if filepath.endswith('.zip'):
        return True

    # Check file header for ZIP signature
    try:
        with open(filepath, 'rb') as f:
            header = f.read(4)
            return header.startswith(b'PK\x03\x04')
    except:
        return False

def extract_text_from_zip(zip_file):
    """Extract text content from ZIP file."""
    result_text = ""
    try:
        if zipfile.is_zipfile(zip_file):
            with zipfile.ZipFile(zip_file, 'r') as z:
                # Get list of text files inside the ZIP
                text_files = [f for f in z.namelist() if f.endswith(('.txt', '.html', '.md', '.csv', '.json', '.xml'))]

                # Limit to first 5 text files to avoid processing too much
                for file in text_files[:5]:
                    try:
                        with tempfile.NamedTemporaryFile(delete=False) as temp:
                            temp.write(z.read(file))
                            temp_filename = temp.name

                        # Read extracted file content
                        with open(temp_filename, 'r', encoding='utf-8', errors='ignore') as f:
                            result_text += f.read() + "\n\n"

                        # Clean up
                        os.unlink(temp_filename)
                    except:
                        continue
        return result_text
    except Exception as e:
        print(f"Error processing ZIP file {zip_file}: {e}")
        return ""

def get_file_content_for_comparison(file_path):
    """Get content from a file for comparison, handling different file types."""
    # For HTML files
    if file_path.endswith('.html'):
        return get_html_content_text(file_path)

    # For ZIP files
    if is_zip_file(file_path):
        return extract_text_from_zip(file_path)

    # For text files
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except:
        # For binary files, return an empty string
        return ""

def match_files(html_dir, drive_dir, output_file="matches.csv"):
    """Find potential matches between HTML files and Google Drive files."""
    html_files = [os.path.join(html_dir, f) for f in os.listdir(html_dir) if f.endswith('.html')]
    drive_files = [os.path.join(drive_dir, f) for f in os.listdir(drive_dir) if os.path.isfile(os.path.join(drive_dir, f))]

    matches = []
    html_match_count = {}  # Track how many matches each HTML file has
    drive_match_count = {}  # Track how many matches each Drive file has

    print(f"Processing {len(html_files)} HTML files and {len(drive_files)} Drive files...")

    # First pass: Look for direct ID references in HTML files
    print("Pass 1: Checking for direct ID references in HTML...")
    for html_file in html_files:
        potential_ids = get_google_drive_id_from_html(html_file)

        match_found = False
        for drive_id in potential_ids:
            for drive_file in drive_files:
                drive_basename = os.path.basename(drive_file)
                # Remove .zip extension if present for comparison
                drive_basename_no_ext = drive_basename.rsplit('.', 1)[0] if '.' in drive_basename else drive_basename

                if drive_basename == drive_id or drive_basename_no_ext == drive_id:
                    matches.append((html_file, drive_file, "id_match", 1.0))
                    
                    # Update match counters
                    html_match_count[html_file] = html_match_count.get(html_file, 0) + 1
                    drive_match_count[drive_file] = drive_match_count.get(drive_file, 0) + 1
                    
                    match_found = True
                    break
            if match_found:
                break

    # Second pass: Use file fingerprinting for binary files and content comparison for text
    print("Pass 2: Comparing content between HTML and drive files...")
    matched_html_files = [m[0] for m in matches]
    unmatched_html_files = [f for f in html_files if f not in matched_html_files]

    for html_file in unmatched_html_files:
        html_content = get_html_content_text(html_file)
        if not html_content:
            continue

        best_match = None
        best_score = 0

        for drive_file in drive_files:
            # Try to get content from drive file
            drive_content = get_file_content_for_comparison(drive_file)

            if drive_content:
                # For text content, use text similarity
                similarity = compare_text_similarity(html_content[:5000], drive_content[:5000])

                if similarity > best_score and similarity > 0.3:  # Threshold can be adjusted
                    best_score = similarity
                    best_match = drive_file

        if best_match:
            matches.append((html_file, best_match, "content_similarity", best_score))
            
            # Update match counters
            html_match_count[html_file] = html_match_count.get(html_file, 0) + 1
            drive_match_count[best_match] = drive_match_count.get(best_match, 0) + 1

    # Third pass: For remaining unmatched files, try date-based matching
    print("Pass 3: Using date-based matching for remaining files...")
    matched_html_files = [m[0] for m in matches]
    unmatched_html_files = [f for f in html_files if f not in matched_html_files]

    html_dates = [(f, datetime.fromtimestamp(os.path.getmtime(f))) for f in unmatched_html_files]
    drive_dates = [(f, datetime.fromtimestamp(os.path.getmtime(f))) for f in drive_files]

    for html_file, html_date in html_dates:
        best_match = None
        best_diff = float('inf')

        for drive_file, drive_date in drive_dates:
            # Calculate time difference in seconds
            time_diff = abs((html_date - drive_date).total_seconds())

            if time_diff < best_diff and time_diff < 86400:  # Within 24 hours
                best_diff = time_diff
                best_match = drive_file

        if best_match:
            matches.append((html_file, best_match, "date_similarity", 1.0 - (best_diff / 86400)))
            
            # Update match counters
            html_match_count[html_file] = html_match_count.get(html_file, 0) + 1
            drive_match_count[best_match] = drive_match_count.get(best_match, 0) + 1

    # Find unmatched HTML files
    unmatched_html_files = [f for f in html_files if f not in html_match_count]
    for html_file in unmatched_html_files:
        matches.append((html_file, "NO_MATCH", "no_match", 0.0))
        html_match_count[html_file] = 0

    # Find unmatched Drive files
    unmatched_drive_files = [f for f in drive_files if f not in drive_match_count]
    for drive_file in unmatched_drive_files:
        matches.append(("NO_MATCH", drive_file, "no_match", 0.0))
        drive_match_count[drive_file] = 0

    # Write results to file
    with open(output_file, 'w') as f:
        f.write("HTML File,Drive File,Match Method,Confidence,Is Unique Match\n")
        for html_file, drive_file, method, confidence in matches:
            html_basename = os.path.basename(html_file) if html_file != "NO_MATCH" else "NO_MATCH"
            drive_basename = os.path.basename(drive_file) if drive_file != "NO_MATCH" else "NO_MATCH"
            
            # Determine if this is a unique match (both file has only one match)
            is_unique = "yes" if (html_file == "NO_MATCH" or html_match_count[html_file] == 1) and (drive_file == "NO_MATCH" or drive_match_count[drive_file] == 1) else "no"
            
            f.write(f'"{html_basename}","{drive_basename}",{method},{confidence:.2f},{is_unique}\n')

    print(f"Found {len(matches)} potential matches. Results written to {output_file}")
    print(f"- {len(unmatched_html_files)} HTML files without matches")
    print(f"- {len(unmatched_drive_files)} Drive files without matches")
    return matches

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Match HTML files with Google Drive files')
    parser.add_argument('html_dir', help='Directory containing HTML files')
    parser.add_argument('drive_dir', help='Directory containing Google Drive files')
    parser.add_argument('--output', default='matches.csv', help='Output CSV file')

    args = parser.parse_args()
    match_files(args.html_dir, args.drive_dir, args.output)

