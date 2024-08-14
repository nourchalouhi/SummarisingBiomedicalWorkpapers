from dotenv import load_dotenv
import os
import jsonlines
import google.generativeai as genai
from rouge_score import rouge_scorer
from bert_score import score
import textstat
import numpy as np
import torch

# Load environment variables
load_dotenv()

# Fetch the API key and configure the Google Generative AI model
api_key = os.getenv('API_KEY')
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-pro')

# Initialize the RougeScorer and BERT scorer
scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)

jsonl_file_path = '/Users/nourchalouhi/Documents/COMP4092 Summarising Biomedical Workpapers to the Layperson/Summarisation Testing/src/data/summaries/dev_plos.jsonl'

totalScores1 = {'rouge': {'rouge1': [], 'rouge2': [], 'rougeL': []}, 'bertscore': [], 'readability': []}
totalScores2 = {'rouge': {'rouge1': [], 'rouge2': [], 'rougeL': []}, 'bertscore': [], 'readability': []}

with jsonlines.open(jsonl_file_path) as reader:
    summaryCount = 0
    for document in reader:
        if summaryCount >= 1000:
            break
        abstract = document.get('abstract', '')
        refSummary = document.get('plain language summary', '')

        if abstract and refSummary:
            try:
                # Generate summaries using two different prompts
                response1 = model.generate_content(f'Create a plain language summary understandable without biomedical jargon: {abstract}')
                summary1 = ' '.join(response1.text.split()[:200])

                response2 = model.generate_content(f'Explain the essence of the research for a general audience, including thought processes and information selection: {abstract}')
                summary2 = ' '.join(response2.text.split()[:200])

                # Calculate and store ROUGE scores
                scores1 = scorer.score(refSummary, summary1)
                scores2 = scorer.score(refSummary, summary2)
                for key in ['rouge1', 'rouge2', 'rougeL']:
                    totalScores1['rouge'][key].append(scores1[key].fmeasure)
                    totalScores2['rouge'][key].append(scores2[key].fmeasure)

                # Calculate BERTScore
                P1, R1, F1 = score([summary1], [refSummary], lang="en", verbose=True)
                P2, R2, F2 = score([summary2], [refSummary], lang="en", verbose=True)
                totalScores1['bertscore'].append(F1.mean().item())
                totalScores2['bertscore'].append(F2.mean().item())

                # Calculate readability scores
                fkgl1 = textstat.flesch_kincaid_grade(summary1)
                fkgl2 = textstat.flesch_kincaid_grade(summary2)
                totalScores1['readability'].append(fkgl1)
                totalScores2['readability'].append(fkgl2)

                print(f"Processed document {summaryCount}")
            except Exception as e:
                print(f"Failed to generate summary for document {summaryCount} due to an error: {str(e)}")

        summaryCount += 1

# Calculate average scores for each metric
def calculate_average(scores):
    averages = {}
    for key, values in scores.items():
        if isinstance(values, dict):  # Nested dictionaries for ROUGE
            averages[key] = {subkey: np.mean(subvalues) for subkey, subvalues in values.items()}
        else:
            averages[key] = np.mean(values)
    return averages

averageScores1 = calculate_average(totalScores1)
averageScores2 = calculate_average(totalScores2)

# Display the final comparison
print("\nFinal Evaluation Metrics Comparison:")
print("Metrics for Prompt 1:")
for metric, values in averageScores1.items():
    if isinstance(values, dict):
        for sub_metric, value in values.items():
            print(f"  {sub_metric}: {value:.4f}")
    else:
        print(f"  {metric}: {values:.4f}")

print("Metrics for Prompt 2:")
for metric, values in averageScores2.items():
    if isinstance(values, dict):
        for sub_metric, value in values.items():
            print(f"  {sub_metric}: {value:.4f}")
    else:
        print(f"  {metric}: {values:.4f}")
