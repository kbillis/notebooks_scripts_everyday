#!/usr/bin/env python3
import argparse
import os
import re
import subprocess
import tempfile
import json
from bs4 import BeautifulSoup
import requests
import shutil
import sys

class OllamaHTMLParser:
    def __init__(self, model_name="codellama:7b-instruct", ollama_url="http://localhost:11434"):
        """
        Initialize the parser with a specific Ollama model.
        
        Args:
            model_name: The name of the Ollama model to use
            ollama_url: The URL of the Ollama server
        """
        self.model_name = model_name
        self.ollama_url = ollama_url
        self.api_endpoint = f"{ollama_url}/api/generate"
        
    def _check_ollama_availability(self):
        """Check if Ollama server is accessible and the model is available."""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags")
            if response.status_code != 200:
                return False, "Ollama server is not responding correctly"
                
            models = response.json().get("models", [])
            available_models = [model["name"] for model in models]
            
            if self.model_name not in available_models:
                return False, f"Model '{self.model_name}' is not available. Available models: {', '.join(available_models)}"
                
            return True, "Ollama is available with the requested model"
        except requests.exceptions.ConnectionError:
            return False, "Ollama server is not running or not accessible"
            
    def extract_code_from_html(self, html_file):
        """
        Extract code blocks and instructions from an HTML file.
        
        Args:
            html_file: Path to the HTML file to parse
            
        Returns:
            dict: Contains extracted code files and instructions
        """
        try:
            with open(html_file, 'r', encoding='utf-8') as file:
                html_content = file.read()
                
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract all code blocks
            code_blocks = {}
            for code_element in soup.find_all(['code', 'pre']):
                # Try to determine the language from class attributes or parent elements
                language = "text"  # Default
                class_attr = code_element.get('class', [])
                
                for cls in class_attr:
                    if cls.startswith('language-') or cls.startswith('lang-'):
                        language = cls.split('-')[1]
                        break
                
                # Try to find a filename comment or hint
                code_text = code_element.get_text()
                filename_match = re.search(r'filename[:\s]+([^\s]+)', code_text, re.IGNORECASE)
                
                if filename_match:
                    filename = filename_match.group(1)
                else:
                    # Generate a filename based on content and language
                    if language in ["python", "py"]:
                        extension = "py"
                    elif language in ["javascript", "js"]:
                        extension = "js"
                    elif language in ["html"]:
                        extension = "html"
                    elif language in ["css"]:
                        extension = "css"
                    elif language in ["shell", "bash", "sh"]:
                        extension = "sh"
                    else:
                        extension = "txt"
                        
                    filename = f"extracted_{len(code_blocks) + 1}.{extension}"
                
                code_blocks[filename] = code_text
            
            # Extract instructions (assuming they're in paragraphs or divs)
            instructions = []
            for para in soup.find_all(['p', 'div']):
                if para.find(['code', 'pre']) is None:  # Skip if it contains code
                    text = para.get_text().strip()
                    if text and len(text) > 20:  # Assuming instructions are reasonably long
                        instructions.append(text)
            
            return {
                "code_files": code_blocks,
                "instructions": instructions,
                "title": soup.title.string if soup.title else "Extracted Code"
            }
            
        except Exception as e:
            print(f"Error parsing HTML: {e}")
            return {"error": str(e)}
    
    def analyze_with_ollama(self, extracted_data):
        """
        Use Ollama to analyze the extracted code and instructions.
        
        Args:
            extracted_data: Dictionary containing code files and instructions
            
        Returns:
            dict: Analysis results from the model
        """
        ollama_available, message = self._check_ollama_availability()
        if not ollama_available:
            return {"error": message}
        
        # Prepare the prompt for Ollama
        prompt = f"""Analyze the following code files and instructions:

INSTRUCTIONS:
{" ".join(extracted_data.get("instructions", ["No instructions provided."]))[:5000]}

CODE FILES:
"""
        # Add up to 3 code files to the prompt (to avoid token limits)
        for i, (filename, code) in enumerate(extracted_data.get("code_files", {}).items()):
            if i >= 3:
                prompt += "\n[Additional code files omitted for brevity]"
                break
            prompt += f"\n--- {filename} ---\n{code[:2000]}"
            if len(code) > 2000:
                prompt += "\n[Code truncated...]"
        
        prompt += """

Please provide the following information in JSON format:
1. The main purpose of the code
2. The proper order to run the files
3. Required dependencies
4. Command to run the code with an input file
5. Expected input file format
6. Expected output

The JSON format should be:
{
    "purpose": "Brief description of what the code does",
    "execution_order": ["file1.py", "file2.py", ...],
    "dependencies": ["package1", "package2", ...],
    "run_command": "python main.py input_file",
    "input_format": "Description of the expected input format",
    "output_description": "Description of the expected output"
}
"""
        
        try:
            response = requests.post(
                self.api_endpoint,
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False
                }
            )
            
            if response.status_code != 200:
                return {"error": f"Ollama API error: {response.text}"}
                
            generated_text = response.json().get("response", "")
            
            # Extract JSON from the response
            json_pattern = r'\{[\s\S]*\}'
            json_match = re.search(json_pattern, generated_text)
            
            if json_match:
                try:
                    analysis = json.loads(json_match.group(0))
                    return analysis
                except json.JSONDecodeError:
                    return {"error": "Could not parse the model's JSON output", "raw_output": generated_text}
            else:
                return {"error": "Could not find JSON in the model's output", "raw_output": generated_text}
                
        except Exception as e:
            return {"error": f"Error communicating with Ollama: {e}"}
    
    def create_runner_script(self, analysis, code_directory):
        """
        Create a runner script based on the analysis to easily execute the code.
        
        Args:
            analysis: The analysis results from Ollama
            code_directory: Directory where the code files are stored
            
        Returns:
            str: Path to the runner script
        """
        runner_script = os.path.join(code_directory, "run.py")
        
        template = f"""#!/usr/bin/env python3
# Auto-generated runner script for {analysis.get("purpose", "extracted code")}
import os
import sys
import subprocess
import shutil

def check_dependencies():
    required = {analysis.get("dependencies", [])}
    missing = []
    
    for pkg in required:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    
    if missing:
        print(f"Missing dependencies: {{', '.join(missing)}}")
        install = input("Would you like to install them now? (y/n): ")
        if install.lower() == 'y':
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
            print("Dependencies installed.")
        else:
            print("Please install the dependencies manually and try again.")
            sys.exit(1)

def run_code(input_file):
    if not os.path.exists(input_file):
        print(f"Error: Input file '{{input_file}}' not found.")
        sys.exit(1)
        
    print("Running the code with the provided input file...")
    
    # Expected execution order based on analysis
    execution_order = {analysis.get("execution_order", [])}
    
    # Handle the input file
    # Copy it to the working directory if needed
    if not os.path.dirname(input_file) == os.getcwd():
        shutil.copy(input_file, os.getcwd())
        input_file = os.path.basename(input_file)
    
    # Execute the main command
    try:
        cmd = "{analysis.get("run_command", "")}".replace("input_file", input_file)
        print(f"Executing: {{cmd}}")
        subprocess.run(cmd, shell=True, check=True)
        print("Execution completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Error executing the code: {{e}}")
        sys.exit(1)

def main():
    if len(sys.argv) != 2:
        print("Usage: python run.py <input_file>")
        print("Input file format: {analysis.get("input_format", "Not specified")}")
        sys.exit(1)
        
    input_file = sys.argv[1]
    check_dependencies()
    run_code(input_file)
    
if __name__ == "__main__":
    main()
"""
        
        with open(runner_script, 'w') as f:
            f.write(template)
        
        os.chmod(runner_script, 0o755)  # Make it executable
        return runner_script

def main():
    parser = argparse.ArgumentParser(description="Parse HTML files with code using Ollama")
    parser.add_argument("html_file", help="Path to the HTML file to parse")
    parser.add_argument("--model", default="llama3", help="Ollama model to use (default: llama3)")
    parser.add_argument("--output", help="Output directory for extracted code (default: auto-generated)")
    parser.add_argument("--ollama-url", default="http://localhost:11434", help="Ollama API URL")
    args = parser.parse_args()
    
    if not os.path.exists(args.html_file):
        print(f"Error: HTML file '{args.html_file}' not found.")
        return 1
        
    # Create output directory
    output_dir = args.output if args.output else f"extracted_code_{int(os.path.getmtime(args.html_file))}"
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Using Ollama model: {args.model}")
    parser = OllamaHTMLParser(model_name=args.model, ollama_url=args.ollama_url)
    
    print(f"Parsing HTML file: {args.html_file}")
    extracted_data = parser.extract_code_from_html(args.html_file)
    
    if "error" in extracted_data:
        print(f"Error: {extracted_data['error']}")
        return 1
        
    # Save extracted code files
    for filename, code in extracted_data.get("code_files", {}).items():
        file_path = os.path.join(output_dir, filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w') as f:
            f.write(code)
        
        print(f"Saved: {file_path}")
    
    # Save instructions
    if extracted_data.get("instructions"):
        with open(os.path.join(output_dir, "instructions.txt"), 'w') as f:
            f.write("\n\n".join(extracted_data["instructions"]))
        print(f"Saved: {os.path.join(output_dir, 'instructions.txt')}")
    
    print(f"\nAnalyzing code with Ollama ({args.model})...")
    analysis = parser.analyze_with_ollama(extracted_data)
    
    if "error" in analysis:
        print(f"Analysis error: {analysis['error']}")
        if "raw_output" in analysis:
            print("\nRaw output from model:")
            print(analysis["raw_output"][:500] + "..." if len(analysis["raw_output"]) > 500 else analysis["raw_output"])
    else:
        # Create a README with the analysis
        with open(os.path.join(output_dir, "README.md"), 'w') as f:
            f.write(f"# {extracted_data.get('title', 'Extracted Code')}\n\n")
            f.write(f"## Purpose\n{analysis.get('purpose', 'Not specified')}\n\n")
            f.write(f"## Dependencies\n")
            for dep in analysis.get("dependencies", []):
                f.write(f"- {dep}\n")
            f.write(f"\n## How to Run\n```\n{analysis.get('run_command', 'Command not specified')}\n```\n\n")
            f.write(f"## Input Format\n{analysis.get('input_format', 'Not specified')}\n\n")
            f.write(f"## Expected Output\n{analysis.get('output_description', 'Not specified')}\n\n")
        
        print(f"Saved: {os.path.join(output_dir, 'README.md')}")
        
        # Create the runner script
        runner_script = parser.create_runner_script(analysis, output_dir)
        print(f"Created runner script: {runner_script}")
        
        print("\nSummary of extraction:")
        print(f"- Extracted {len(extracted_data.get('code_files', {}))} code files")
        print(f"- Found {len(extracted_data.get('instructions', []))} instruction blocks")
        print(f"- Generated README.md and run.py")
        print(f"\nTo run the extracted code with an input file:")
        print(f"cd {output_dir}")
        print(f"python run.py path/to/your/input_file")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())