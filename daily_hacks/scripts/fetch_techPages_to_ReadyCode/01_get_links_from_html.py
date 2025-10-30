from bs4 import BeautifulSoup

# Path to your HTML file
html_file = "B_O Trading Blog _ Substack.htm"

# Read the file
with open(html_file, "r", encoding="utf-8") as file:
    soup = BeautifulSoup(file, "lxml")

# Extract all links
links = []
for a in soup.find_all("a", href=True):
    url = a["href"]
    if "substack.com/p/" in url:  # Filter only blog post URLs
        links.append(url)

# Save extracted URLs to a text file
output_file = "blog_urls.txt"
with open(output_file, "w") as f:
    f.write("\n".join(links))

print(f"Extracted {len(links)} blog post URLs. Saved to {output_file}")

