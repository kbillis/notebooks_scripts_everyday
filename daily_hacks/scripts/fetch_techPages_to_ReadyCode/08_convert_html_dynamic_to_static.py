from bs4 import BeautifulSoup
import os
# Directory containing the HTML files
html_directory = "/Users/kbillis/tmp_BO_trading/2nd_attempt"  # Replace with your directory
output_directory = "/Users/kbillis/tmp_BO_trading/2nd_attempt_stat"  # Replace with your desired directory


# Ensure the output directory exists
os.makedirs(output_directory, exist_ok=True)

# Process each HTML file
for file_name in os.listdir(html_directory):
    if file_name.endswith(".html"):  # Only process .html files
        file_path = os.path.join(html_directory, file_name)
        output_path = os.path.join(output_directory, file_name)

        # Parse the HTML file and remove <script> tags
        with open(file_path, "r", encoding="utf-8") as html_file:
            soup = BeautifulSoup(html_file, "html.parser")
            for script in soup.find_all("script"):
                script.decompose()  # Remove <script> tags

        # Save the modified HTML to the output directory
        with open(output_path, "w", encoding="utf-8") as output_file:
            output_file.write(str(soup))

        print(f"Saved static HTML: {output_path}")
