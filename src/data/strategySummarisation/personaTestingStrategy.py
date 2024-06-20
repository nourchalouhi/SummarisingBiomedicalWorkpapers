from dotenv import load_dotenv
import os
import jsonlines
import google.generativeai as genai
from rouge_score import rouge_scorer

load_dotenv()

api_key = os.getenv('API_KEY')
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-pro')

scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)

# Path to the JSONL file containing abstracts and plain language summaries
jsonl_file_path = '/Users/nourchalouhi/Documents/COMP4092 Summarising Biomedical Workpapers to the Layperson/Summarisation Testing/src/data/summaries/dev_plos.jsonl'

# Dictionary to store ROUGE scores for each summary
totalScores = {'rouge1': [], 'rouge2': [], 'rougeL': []}

# Limit to first 10 papers
max_documents = 10
summaryCount = 0  

# Process each document in the JSONL file
with jsonlines.open(jsonl_file_path) as reader:
    for document in reader:
        if summaryCount >= max_documents: 
            break
        
        abstract = document.get('abstract', '')
        refSummary = document.get('plain language summary', '')

        if abstract and refSummary:
            try:
                # Generate summary using the persona-based prompt
                response = model.generate_content(f'Imagine you are a science educator. Simplify this abstract for a non-expert audience: {abstract}')
                summary = ' '.join(response.text.split()[:200])  #limit summary to 200 words

                # Calculate ROUGE scores and store them
                scores = scorer.score(refSummary, summary)
                for key in totalScores:
                    totalScores[key].append(scores[key].fmeasure)

                summaryCount += 1  # Increment the document counter
                print(f"Processed document {summaryCount}")
            except Exception as e:
                print(f"Failed to generate summary for document {summaryCount} due to an error: {str(e)}\n")

# Calculate average scores
averageScores = {key: sum(values) / len(values) if values else 0 for key, values in totalScores.items()}

# Display the final average ROUGE scores
print("\nFinal Average ROUGE Scores:")
for key, value in averageScores.items():
    print(f"  {key}: {value:.4f}")
