import ollama

# Initialize the Ollama model
model = ollama.Model("YOUR_MODEL_NAME")  # Replace with your desired AI model

# Read the HTML file
html_file_path = "instructions.html"  # Replace with the path to your HTML file
with open(html_file_path, "r", encoding="utf-8") as file:
    html_content = file.read()

# Define a prompt to guide the model
prompt = f"""
You are an expert Python programmer. I have an HTML file with embedded instructions:
{html_content}

Please read the instructions and generate Python code based on them. Be clear and precise.
"""

# Send the prompt to the model and get the response
response = model.ask(prompt)

# Extract the generated code from the response
generated_code = response.get("content")  # Adjust this based on how the model returns the response

# Display the generated code
print("Generated Code:")
print(generated_code)

# Optionally save the generated code to a file
output_code_path = "generated_code.py"
with open(output_code_path, "w", encoding="utf-8") as code_file:
    code_file.write(generated_code)

print(f"\nGenerated code has been saved to: {output_code_path}")

