from dotenv import load_dotenv
import os
import json  # Use json instead of jsonlines
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

json_file_path = '/Users/nourchalouhi/Documents/COMP4092 Summarising Biomedical Workpapers to the Layperson/Summarisation Testing/elife/val.json'

totalScores1 = {'rouge': {'rouge1': [], 'rouge2': [], 'rougeL': []}, 'bertscore': [], 'readability': []}
totalScores2 = {'rouge': {'rouge1': [], 'rouge2': [], 'rougeL': []}, 'bertscore': [], 'readability': []}

# Open and load the JSON file
with open(json_file_path, 'r') as reader:
    data = json.load(reader)  # This will load the entire JSON file into memory as a list of dictionaries

summaryCount = 0
for document in data:  # Iterate through the list of documents if JSON is an array
    if summaryCount >= 1000:
        break

    # Check if 'abstract' and 'summary' are lists and handle accordingly
    abstract_list = document.get('abstract', [])
    refSummary_list = document.get('summary', [])
    
    # Join list elements into a single string if they are lists
    abstract = " ".join(abstract_list) if isinstance(abstract_list, list) else abstract_list
    refSummary = " ".join(refSummary_list) if isinstance(refSummary_list, list) else refSummary_list

    if not abstract or not refSummary:
        print(f"Skipping document {summaryCount} due to missing abstract or reference summary.")
        continue

    try:
        # Generate summaries using two different prompts
        print(f"Processing document {summaryCount}...")

        response1 = model.generate_content(f'Given the following biomedical abstract, create a plain language summary that is understandable without using biomedical jargon. Follow these steps: - Start by identifying the core topic and the main findings in the abstract. What is the primary focus of the study? Summarize the key results and conclusions. - Translate any complex biomedical terms into simpler language that a layperson can understand. Where necessary, offer brief explanations or analogies that a general audience can relate to. Avoid oversimplifying to the point of losing critical information. Explain the importance of the findings in clear and concise terms. Why is this research relevant? Discuss the implications for the general public or specific groups if applicable. - Offer essential background information that situates the study within the broader field of biomedical science. Connect the study’s focus to well-known issues or public health concerns to make it more relatable. Mention the key methods used in the study, focusing on the approach rather than technical details. Explain the methodology in a way that is easy to understand, ensuring that the reader can grasp the study’s reliability without needing in-depth knowledge. - Summarize the potential impact of the study’s findings. What are the possible applications? How might this research influence future studies, healthcare practices, or public health policies? - Ensure that the summary is clear, concise, and avoids unnecessary detail. The goal is to inform, not to overwhelm. Now, generate the plain language summary: {abstract}')
        summary1 = response1.text

        response2 = model.generate_content(f'Imagine you are a science communicator who is passionate about making complex biomedical research accessible to the general public. Your goal is to create a plain language summary that anyone, regardless of their background, can understand and find engaging. Below are examples of how similar biomedical research has been summarised for a general audience. Use these examples to guide your summary of the given abstract. Abstract: {abstract}')
        summary2 = response2.text

        # Check if summaries are generated
        if not summary1 or not summary2:
            print(f"Failed to generate summaries for document {summaryCount}.")
            continue

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

# Check if any scores were calculated
if not totalScores1['rouge']['rouge1'] or not totalScores2['rouge']['rouge1']:
    print("No scores were calculated, check your input data and model responses.")
else:
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

    # Display final comparisons
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
            