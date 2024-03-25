from dotenv import load_dotenv
import os
import jsonlines
import google.generativeai as genai

# Load the environment variables
load_dotenv()

# Configuration for the API
api_key = os.getenv('API_KEY')
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-pro')

# Set the path directly to your JSONL file
jsonl_file_path = '/Users/nourchalouhi/Documents/COMP4092 Summarising Biomedical Workpapers to the Layperson/Summarisation Testing/src/data/dev_plos.jsonl'

# Open and read the contents of the JSONL file
with jsonlines.open(jsonl_file_path) as reader:
    summary_number = 1  # Start counter for summaries
    for document in reader:
        content_to_summarise = document.get('abstract', '')#summarising abstract
        
        # Check if there is content to summarise
        if content_to_summarise:
            try:
                # Call the API to generate a summary
                response = model.generate_content(f'Please summarise this biomedical abstract for a general audience. {content_to_summarise}')
                summary = response.text  # Assuming response.text contains the summary text
                
                # Handle the length of the summary if needed
                summary_words = summary.split()[:200]  # Example: Limiting to first 200 words
                summary = ' '.join(summary_words)
                
                # Print a header with the summary number and then the summary
                print(f"Biomedical Paper {summary_number} Summary:\n{summary}\n")
                print("--------------------------------------------------\n")  # Line space for differentiation
                summary_number += 1  # Increment the counter
            except Exception as e:
                print(f"Failed to generate summary for document due to an error: {str(e)}\n")
        else:
            print(f"No content to summarise found in document {summary_number}.\n")
            summary_number += 1  # Increment the counter