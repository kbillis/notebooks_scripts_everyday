
import time 
import os 
import sys

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By




# Load URLs from the file
if len(sys.argv) > 1:
    file_path = sys.argv[1]
else:
    file_path = "blog_urls.txt"  # Default file path if none provided

# Read URLs from the file
with open(file_path, "r") as f:
    urls = [line.strip() for line in f.readlines()]

# Now you can use the urls list
print(f"Loaded {len(urls)} URLs from {file_path}")



# Define the download directory (update as needed)
download_dir = "/Users/kbillis/tmp_BO_trading"

# Ensure the directory exists
os.makedirs(download_dir, exist_ok=True)

# Set Chrome options for headless printing to PDF
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--kiosk-printing")  # Auto-confirm print dialogs
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--headless")  # Run without UI
chrome_options.add_argument("--enable-print-browser")
chrome_options.add_argument("--start-maximized")

# Set Chrome to print as PDF
settings = {
    "recentDestinations": [{"id": "Save as PDF", "origin": "local", "account": ""}],
    "selectedDestinationId": "Save as PDF",
    "version": 2
}

prefs = {
    "printing.print_preview_sticky_settings.appState": str(settings),
    "savefile.default_directory": download_dir  # Change this path as needed
}
chrome_options.add_experimental_option("prefs", prefs)
chrome_options.add_argument("--disable-print-preview")

# this is an alterantive method if versions of software match! 
# Path to ChromeDriver
driver_path = "/Users/kbillis/miniconda3/envs/BO_channel_detection1/lib/python3.11/site-packages/chromedriver_binary/chromedriver"  # Update this with your actual path
# service = Service(driver_path)
# driver = webdriver.Chrome(service=service, options=chrome_options)

# Use WebDriver Manager to install the correct ChromeDriver version
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)


# Log in manually first
print("Open Chrome and log in to Substack. Then press Enter...")
driver.get("https://substack.com")
input("Press Enter after logging in...")

# Download each blog as PDF and save full HTML
for url in urls:
    print(f"Processing: {url}")
    driver.get(url)
    time.sleep(5)  # Wait for page to load

    # Extract full HTML and save
    html_content = driver.page_source
    filename_base = url.split("/")[-1] or "index"  # Use last part of URL for filename
    html_filename = os.path.join(download_dir, f"{filename_base}.html")

    with open(html_filename, "w", encoding="utf-8") as file:
        file.write(html_content)
    
    print(f"Saved HTML: {html_filename}")

    # Print page as PDF
    # driver.execute_script("window.print();")
    time.sleep(3)  # Allow time for saving

print("All blogs downloaded as PDFs and HTML files!")
driver.quit()

