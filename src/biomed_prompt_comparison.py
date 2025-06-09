"""
Evaluates two Gemini prompt strategies for biomedical abstract summarisation using ROUGE, BERTScore, and Flesch-Kincaid readability.

- Loads PLOS dataset.
- Compares two prompt styles per document.
- Aggregates metrics across examples.
- Prints final results.

"""

import os
import json
import google.generativeai as genai
from rouge_score import rouge_scorer
from bert_score import score
import textstat
import numpy as np
import time
from dotenv import load_dotenv

# ==== SETUP ====

# Load environment variables (API KEY should be set in .env)
load_dotenv()
api_key = os.getenv('API_KEY')
if not api_key:
    raise RuntimeError("Missing API_KEY. Set it in your .env file.")

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-pro')

# Metrics
scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)

# Data path (relative for portability)
json_file_path = 'data/plos/train.json'

# ==== MAIN ====

totalScores1 = {'rouge': {'rouge1': [], 'rouge2': [], 'rougeL': []}, 'bertscore': [], 'readability': []}
totalScores2 = {'rouge': {'rouge1': [], 'rouge2': [], 'rougeL': []}, 'bertscore': [], 'readability': []}

with open(json_file_path, 'r') as reader:
    data = json.load(reader)

summaryCount = 0
for document in data:
    if summaryCount >= 2:  # Change this number to test more
        break

    abstract = " ".join(document.get('abstract', []))
    refSummary = " ".join(document.get('summary', []))
    if not abstract or not refSummary:
        print(f"Skipping document {summaryCount} due to missing abstract or summary.")
        continue

    try:
        print(f"Processing document {summaryCount}...")

        # Prompt 1: Step-by-step methodology + outcomes
        response1 = model.generate_content(
            f'Explain the following biomedical abstract by breaking down the research process step-by-step. '
            f'First, summarise the methodology—how was the study conducted? What were the key methods used? '
            f'Then, explain the main outcomes of the study and why they matter in the context of biomedical science or public health. '
            f'Abstract: {abstract}'
        )
        summary1 = response1.text

        # Prompt 2: Lay summary for a general audience
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

        if not summary1 or not summary2:
            print(f"Failed to generate summaries for document {summaryCount}.")
            continue

        # --- METRICS ---
        scores1 = scorer.score(refSummary, summary1)
        scores2 = scorer.score(refSummary, summary2)
        for key in ['rouge1', 'rouge2', 'rougeL']:
            totalScores1['rouge'][key].append(scores1[key].fmeasure)
            totalScores2['rouge'][key].append(scores2[key].fmeasure)

        # BERTScore
        P1, R1, F1 = score([summary1], [refSummary], lang="en", verbose=False)
        P2, R2, F2 = score([summary2], [refSummary], lang="en", verbose=False)
        totalScores1['bertscore'].append(F1.mean().item())
        totalScores2['bertscore'].append(F2.mean().item())

        # Flesch-Kincaid Readability
        totalScores1['readability'].append(textstat.flesch_kincaid_grade(summary1))
        totalScores2['readability'].append(textstat.flesch_kincaid_grade(summary2))

        time.sleep(1)  # Avoid API rate limits
        print(f"Processed document {summaryCount}")

    except Exception as e:
        print(f"Error processing document {summaryCount}: {e}")

    summaryCount += 1

# ==== AGGREGATE AND PRINT ====

def calculate_average(scores):
    averages = {}
    for key, values in scores.items():
        if isinstance(values, dict):
            averages[key] = {subkey: np.mean(subvalues) for subkey, subvalues in values.items()}
        else:
            averages[key] = np.mean(values)
    return averages

if not totalScores1['rouge']['rouge1'] or not totalScores2['rouge']['rouge1']:
    print("No scores calculated.")
else:
    averageScores1 = calculate_average(totalScores1)
    averageScores2 = calculate_average(totalScores2)

    print("\n=== Final Evaluation Metrics Comparison ===")
    print("Prompt 1 Metrics:")
    for metric, values in averageScores1.items():
        if isinstance(values, dict):
            for sub_metric, value in values.items():
                print(f"  {sub_metric}: {value:.4f}")
        else:
            print(f"  {metric}: {values:.4f}")

    print("Prompt 2 Metrics:")
    for metric, values in averageScores2.items():
        if isinstance(values, dict):
            for sub_metric, value in values.items():
                print(f"  {sub_metric}: {value:.4f}")
        else:
            print(f"  {metric}: {values:.4f}")