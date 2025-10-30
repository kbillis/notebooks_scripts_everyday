import re
import os
import glob

def clean_drive_link(link):
    """Clean a Google Drive link by removing trailing backslashes and other unwanted characters."""
    # Remove trailing backslashes
    cleaned_link = re.sub(r'\\+$', '', link)
    return cleaned_link

def extract_drive_links(file_path):
    """Extract Google Drive links from a file."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
            content = file.read()
            
        # Pattern specifically for Google Drive file links
        drive_pattern = r'https://drive\.google\.com/file/d/[a-zA-Z0-9_-]+/view\?usp=sharing\\*'
        drive_links = re.findall(drive_pattern, content)
        
        # Clean the links
        cleaned_links = [clean_drive_link(link) for link in drive_links]
        
        return cleaned_links
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return []

def main():
    # Directory containing files
    # You can modify this path to point to your directory
    file_dir = "./2nd_attempt/"  
    
    # Get all files in the directory (or specify a pattern like "*.txt" or "*.html")
    files = glob.glob(os.path.join(file_dir, "*"))
    
    if not files:
        print("No files found in the specified directory.")
        return
    
    all_links = []
    
    # Process each file
    for file_path in files:
        if os.path.isfile(file_path):
            print(f"Processing {file_path}...")
            links = extract_drive_links(file_path)
            
            if links:
                print(f"Found {len(links)} Google Drive links in {file_path}")
                all_links.extend(links)
    
    # Remove duplicates while preserving order
    unique_links = []
    for link in all_links:
        if link not in unique_links:
            unique_links.append(link)
    
    # Print all unique links
    print("\n=== All Unique Google Drive Links ===")
    for link in unique_links:
        print(link)
    
    # Save links to a file
    with open("google_drive_links.txt", "w", encoding="utf-8") as output_file:
        output_file.write("\n".join(unique_links))
    
    print(f"\nExtracted {len(unique_links)} unique Google Drive links")
    print("Links have been saved to google_drive_links.txt")

if __name__ == "__main__":
    main()
