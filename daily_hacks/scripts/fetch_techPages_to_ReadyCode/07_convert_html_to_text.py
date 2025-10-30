#!/usr/bin/env python3
import os
import re
import argparse
from bs4 import BeautifulSoup
import justext
import trafilatura
from readability import Document
import csv

def extract_content_with_readability(html_content):
    """Extract main content using readability-lxml library."""
    try:
        doc = Document(html_content)
        content = doc.summary()
        # Clean up the extracted content
        soup = BeautifulSoup(content, 'html.parser')
        return soup.get_text(separator='\n\n').strip()
    except Exception as e:
        print(f"Readability extraction failed: {e}")
        return None

def extract_content_with_trafilatura(html_content):
    """Extract main content using trafilatura library."""
    try:
        extracted = trafilatura.extract(html_content, include_comments=False, 
                                       include_tables=True, include_images=False,
                                       output_format='text')
        return extracted
    except Exception as e:
        print(f"Trafilatura extraction failed: {e}")
        return None

def extract_content_with_justext(html_content):
    """Extract main content using justext library."""
    try:
        paragraphs = justext.justext(html_content, justext.get_stoplist("English"))
        content_parts = []
        for paragraph in paragraphs:
            if not paragraph.is_boilerplate:
                content_parts.append(paragraph.text)
        return '\n\n'.join(content_parts)
    except Exception as e:
        print(f"Justext extraction failed: {e}")
        return None

def extract_blog_content(html_file, output_dir, method='all'):
    """Extract blog content from HTML file using specified method(s)."""
    try:
        with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
            html_content = f.read()
        
        basename = os.path.basename(html_file)
        filename_no_ext = os.path.splitext(basename)[0]
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Track extraction success
        extraction_results = {}
        
        # Different extraction methods
        if method in ['readability', 'all']:
            readability_text = extract_content_with_readability(html_content)
            if readability_text:
                readability_output = os.path.join(output_dir, f"{filename_no_ext}_readability.txt")
                with open(readability_output, 'w', encoding='utf-8') as f:
                    f.write(readability_text)
                extraction_results['readability'] = len(readability_text)
        
        if method in ['trafilatura', 'all']:
            trafilatura_text = extract_content_with_trafilatura(html_content)
            if trafilatura_text:
                trafilatura_output = os.path.join(output_dir, f"{filename_no_ext}_trafilatura.txt")
                with open(trafilatura_output, 'w', encoding='utf-8') as f:
                    f.write(trafilatura_text)
                extraction_results['trafilatura'] = len(trafilatura_text)
        
        if method in ['justext', 'all']:
            justext_text = extract_content_with_justext(html_content)
            if justext_text:
                justext_output = os.path.join(output_dir, f"{filename_no_ext}_justext.txt")
                with open(justext_output, 'w', encoding='utf-8') as f:
                    f.write(justext_text)
                extraction_results['justext'] = len(justext_text)
        
        # Determine the best extraction (most content) if we used multiple methods
        if method == 'all' and extraction_results:
            best_method = max(extraction_results, key=extraction_results.get)
            best_source = None
            
            if best_method == 'readability':
                best_source = os.path.join(output_dir, f"{filename_no_ext}_readability.txt")
            elif best_method == 'trafilatura':
                best_source = os.path.join(output_dir, f"{filename_no_ext}_trafilatura.txt")
            elif best_method == 'justext':
                best_source = os.path.join(output_dir, f"{filename_no_ext}_justext.txt")
            
            if best_source:
                best_output = os.path.join(output_dir, f"{filename_no_ext}.txt")
                with open(best_source, 'r', encoding='utf-8') as src:
                    content = src.read()
                    with open(best_output, 'w', encoding='utf-8') as dst:
                        dst.write(content)
            
            return best_method, extraction_results.get(best_method, 0)
        
        return method, extraction_results.get(method, 0)
    
    except Exception as e:
        print(f"Error processing {html_file}: {e}")
        return None, 0

def process_directory(html_dir, output_dir, method='trafilatura'):
    """Process all HTML files in a directory."""
    html_files = [os.path.join(html_dir, f) for f in os.listdir(html_dir) if f.endswith('.html')]
    results = []
    
    print(f"Processing {len(html_files)} HTML files...")
    
    for i, html_file in enumerate(html_files):
        print(f"Processing {i+1}/{len(html_files)}: {os.path.basename(html_file)}")
        best_method, content_size = extract_blog_content(html_file, output_dir, method)
        results.append({
            'file': os.path.basename(html_file),
            'method': best_method,
            'content_size': content_size
        })
    
    # Write extraction report
    report_path = os.path.join(output_dir, "extraction_report.csv")
    with open(report_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['file', 'method', 'content_size'])
        writer.writeheader()
        writer.writerows(results)
    
    print(f"Extraction completed. Results saved to {output_dir}")
    print(f"Extraction report saved to {report_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Extract blog content from HTML files')
    parser.add_argument('html_dir', help='Directory containing HTML files')
    parser.add_argument('--output', default='blog_content', help='Output directory for extracted content')
    parser.add_argument('--method', default='all', 
                        choices=['all', 'readability', 'trafilatura', 'justext'],
                        help='Content extraction method to use')
    
    args = parser.parse_args()
    process_directory(args.html_dir, args.output, args.method)