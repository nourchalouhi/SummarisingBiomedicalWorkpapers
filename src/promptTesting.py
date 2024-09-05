from dotenv import load_dotenv
import os
import json
import google.generativeai as genai
from rouge_score import rouge_scorer
from bert_score import score
import textstat
import numpy as np
import time

# Load environment variables
load_dotenv()

# Fetch the API key and configure the Google Generative AI model
api_key = os.getenv('API_KEY')
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-pro')

# Initialize the RougeScorer and BERT scorer
scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)

# Define the JSON file path
json_file_path = '/Users/nourchalouhi/Documents/COMP4092 Summarising Biomedical Workpapers to the Layperson/Summarisation Testing/dataSets/elife/train.json'

# Store the results
totalScores1 = {'rouge': {'rouge1': [], 'rouge2': [], 'rougeL': []}, 'bertscore': [], 'readability': []}
totalScores2 = {'rouge': {'rouge1': [], 'rouge2': [], 'rougeL': []}, 'bertscore': [], 'readability': []}

# Open and load the JSON file
with open(json_file_path, 'r') as reader:
    data = json.load(reader)  # This will load the entire JSON file into memory as a list of dictionaries

# Start processing the documents
summaryCount = 0
for document in data:
    if summaryCount >= 40:
        break

    # Check if 'abstract' and 'summary' are available
    abstract_list = document.get('abstract', [])
    refSummary_list = document.get('summary', [])

    abstract = " ".join(abstract_list) if isinstance(abstract_list, list) else abstract_list
    refSummary = " ".join(refSummary_list) if isinstance(refSummary_list, list) else refSummary_list

    if not abstract or not refSummary:
        print(f"Skipping document {summaryCount} due to missing abstract or reference summary.")
        continue

    try:
        print(f"Processing document {summaryCount}...")

        # Generate content for Prompt 1
        response1 = model.generate_content(f'Explain the following biomedical abstract by breaking down the research process step-by-step. First, summarise the methodology—how was the study conducted? What were the key methods used? Then, explain the main outcomes of the study and why they matter in the context of biomedical science or public health. Abstract: {abstract}')
        summary1 = response1.text

        # Generate content for Prompt 2
        response2 = model.generate_content(
            f"Summarise the following biomedical research paper in simple language for a general audience.\n\n"
            f"**Title**: \"{document.get('title', 'No title available')}\"\n"
            f"**Year**: {document.get('year', 'No year available')}\n\n"
            f"**Abstract**:\n{abstract}\n\n"
            f"**Keywords**: {', '.join(document.get('keywords', ['No keywords available']))}\n\n"
            "Instructions:\n"
            "- Start by explaining the central topic of the paper based on the title.\n"
            "- Provide a simple explanation of the abstract without using biomedical jargon.\n"
            "- Highlight the significance of the findings and their potential impact.\n"
            "- Clarify any difficult terms using the provided keywords."
        )
        summary2 = response2.text

        # Handle potential API quota exhaustion
        if not summary1 or not summary2:
            print(f"Failed to generate summaries for document {summaryCount}.")
            continue

        # Calculate ROUGE scores
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

        # Add a delay to avoid hitting rate limits
        time.sleep(1)
        
        print(f"Processed document {summaryCount}")
    except Exception as e:
        print(f"Failed to generate summary for document {summaryCount} due to an error: {str(e)}")

    summaryCount += 1

# Check if any scores were calculated
if not totalScores1['rouge']['rouge1'] or not totalScores2['rouge']['rouge1']:
    print("No scores were calculated, check your input data and model responses.")
else:
    # Calculate and display average scores
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