"""
Biomedical Summarisation Pipeline — Extractive+Abstractive, LLM Evaluation

This script automates a two-step biomedical summarisation pipeline:
1. **Extractive:** Uses an LLM to extract key sentences from biomedical abstracts.
2. **Abstractive:** Uses an LLM to generate a plain-language summary from the extracted content, optionally incorporating keywords.

The script evaluates the generated summaries against reference summaries using ROUGE, readability, factuality (AlignScore, SummaC), and logs all results for reproducibility.

Features:
- Loads biomedical papers from a JSON file (see `json_file_path`).
- Handles nested lists in input (abstract, summary, keywords).
- Calls OpenAI GPT for extractive and abstractive steps (with error/retry logic).
- Evaluates output with ROUGE, FKGL, DCRS, CLI, AlignScore, SummaC.
- Aggregates results and writes mean/std metrics to CSV.
- Full logging to file and stderr for experiment traceability.

Requirements:
- Environment variables (`OPENAI_API_KEY`, etc.) in a `.env` file.
- Models: OpenAI GPT-4o-mini, SummaCConv, AlignScore (provide correct model bin paths).
- Datasets: JSON input file with 'abstract', 'summary', 'keywords' per record.
"""
import sys
import os
import logging
import openai
import csv
import json
import numpy as np
from rouge_score import rouge_scorer
from bert_score import score as bert_score
import textstat
import time
from requests.exceptions import ReadTimeout
from summac.model_summac import SummaCConv
from alignscore import AlignScore
from dotenv import load_dotenv
import traceback


# Load environment variables and API keys
load_dotenv()
openai_api_key = os.getenv('OPENAI_API_KEY')
openai.api_key = openai_api_key

# Initialize ROUGE scorer and logging
rouge_scorer_instance = rouge_scorer.RougeScorer(
    ['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Ensure the log directory exists
log_directory = 'logs'
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

# Update the file paths to valid locations
log_file_path = os.path.join(log_directory, 'summarisation_pipeline.log')
csv_file_path = os.path.join(log_directory, 'summarisation_results.csv')
json_file_path = 'data/elife_val.json'

# Logging handlers
file_handler = logging.FileHandler(log_file_path)
console_handler = logging.StreamHandler(sys.stderr)  # Output logs to stderr
formatter = logging.Formatter('%(asctime)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Number of repeats per prompt
num_repeats = 3  # You can adjust this number as needed

# Initialize SummaC and AlignScore models
summac_model = SummaCConv(
    models=["vitc"],
    bins='percentile',
    granularity="sentence",
    nli_labels="e",
    device="cpu",
    start_file="INSERT_FILE_PATH_HERE.bin",
    agg="mean"
)

alignscore_model = AlignScore(
    model='roberta-base', batch_size=16, device='cpu', ckpt_path=None, evaluation_mode='nli_sp'
)

# Function to calculate readability metrics
def calculate_readability(text):
    fkgl = textstat.flesch_kincaid_grade(text)
    dcrs = textstat.dale_chall_readability_score(text)
    cli = textstat.coleman_liau_index(text)
    return fkgl, dcrs, cli

# Function to calculate AlignScore
def calculate_align_score(summary, reference):
    # Ensure summary and reference are strings
    if not isinstance(summary, str):
        summary = " ".join(flatten_list(summary))
    if not isinstance(reference, str):
        reference = " ".join(flatten_list(reference))
    return np.mean(alignscore_model.score(contexts=[reference], claims=[summary]))

# Function to calculate SummaC score
def calculate_summac_score(summary, reference):
    # Ensure summary and reference are strings
    if not isinstance(summary, str):
        summary = " ".join(flatten_list(summary))
    if not isinstance(reference, str):
        reference = " ".join(flatten_list(reference))
    return np.mean(summac_model.score([reference], [summary])['scores'])

# Retry decorator for API calls
def retry_api_call(max_retries=3, delay=5):
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (ReadTimeout, openai.error.Timeout) as e:
                    if attempt < max_retries - 1:
                        logger.warning(f"API call failed (attempt {attempt + 1}/{max_retries}), retrying after {delay} seconds...")
                        time.sleep(delay)
                    else:
                        logger.error("API call failed after all retries.")
                        raise
        return wrapper
    return decorator

@retry_api_call()
def openai_chat_completion(model_name, prompt):
    response = openai.ChatCompletion.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        timeout=60
    )
    return response['choices'][0]['message']['content']

# Function to flatten nested lists
def flatten_list(lst):
    flat_list = []
    if isinstance(lst, list):
        for item in lst:
            if isinstance(item, list):
                flat_list.extend(flatten_list(item))
            else:
                flat_list.append(item)
    else:
        flat_list.append(lst)
    return flat_list

# Extract key sentences with AI model
def extract_key_sentences(abstract_text):
    model_name = "gpt-4o-mini"  # Update to the model you are using
    extractive_prompt = (
        "Extract the key sentences from the following research abstract that highlight "
        "the main objectives, methods, and findings. Ensure that all critical technical details are included.\n\n"
        f"{abstract_text}\n\n"
        "Return only the most important sentences as an extract."
    )
    extracted_text = openai_chat_completion(model_name, extractive_prompt)
    logger.info(f"Extractive Summary: {extracted_text}")
    return extracted_text

def abstractive_summarization(extracted_text, keywords):
    model_name = "gpt-4o-mini"  # Update to the model you are using

    few_shot_examples = (
        "Example Abstract 1:\n"

        "Example Summary 1:\n"

        "Example Abstract 2:\n"

        "Example Summary 2:\n"

    )

    # Flatten and join keywords
    if isinstance(keywords, list):
        keywords = flatten_list(keywords)
    else:
        keywords = [keywords]
    keyword_string = ", ".join(keywords)

    abstractive_prompt = (
        f"{few_shot_examples}"
        "Compose an accessible summary of the following key points, avoiding technical jargon and explaining any necessary terms in simple language. "
        f"Ensure that the summary includes the following keywords: {keyword_string}.\n\n"
        f"{extracted_text}\n\n"
        "The paragraph summary should be concise and engaging."
    )
    summary_text = openai_chat_completion(model_name, abstractive_prompt)
    
    # Log the abstractive summary
    logger.info(f"Abstractive Summary: {summary_text}")

    # Ensure that extracted_text and summary_text are strings
    if not isinstance(extracted_text, str):
        extracted_text = " ".join(flatten_list(extracted_text))
    if not isinstance(summary_text, str):
        summary_text = " ".join(flatten_list(summary_text))
        
    rouge_scores = rouge_scorer_instance.score(extracted_text, summary_text)
    logger.info(f"ROUGE between Extracted Text and Abstractive Summary:")
    logger.info(f"ROUGE-1: {rouge_scores['rouge1'].fmeasure}, ROUGE-2: {rouge_scores['rouge2'].fmeasure}, ROUGE-L: {rouge_scores['rougeL'].fmeasure}")
    return summary_text

# Function to load data from JSON file
def load_data_from_json(json_file_path):
    with open(json_file_path, 'r') as file:
        data = json.load(file)
    return data

def evaluate_and_log(data):
    per_prompt_metrics = {
        'prompt_text': "Extract and summarize abstracts",
        'papers_tested': 0,
        'repeats': num_repeats,
        'models': {}
    }
    
    # Initialize main metric lists
    rouge1_all_scores = []
    rouge2_all_scores = []
    rougeL_all_scores = []
    fkgl_all_scores = []
    dcrs_all_scores = []
    cli_all_scores = []
    align_all_scores = []
    summac_all_scores = []
    max_documents = 2
    processed_docs = 0

    for i, document in enumerate(data):
        if processed_docs >= max_documents:
            break

        try:
            logger.info(f"Processing document {i+1}")

            abstract_list = document.get('abstract', [])
            refSummary_list = document.get('summary', [])
            keywords = document.get('keywords', [])

            # Flatten the lists
            abstract_list = flatten_list(abstract_list)
            refSummary_list = flatten_list(refSummary_list)
            keywords = flatten_list(keywords)

            # Join the lists into strings
            abstract = " ".join(abstract_list)
            reference_summary = " ".join(refSummary_list)

            if not abstract.strip() or not reference_summary.strip():
                logger.warning(f"Skipping document {i+1} due to missing abstract or summary.")
                continue

            per_prompt_metrics['papers_tested'] += 1
            processed_docs += 1

            # Initialize per-document metric lists
            rouge1_scores = []
            rouge2_scores = []
            rougeL_scores = []
            fkgl_scores = []
            dcrs_scores = []
            cli_scores = []
            align_scores = []
            summac_scores = []

            for repeat in range(num_repeats):
                logger.info(f"Repeat {repeat+1}/{num_repeats} for document {i+1}")
                extracted_sentences = extract_key_sentences(abstract)
                summary = abstractive_summarization(extracted_sentences, keywords)

                # Log the abstractive summary
                logger.info(f"Abstractive Summary: {summary}")

                # Ensure that summary and reference_summary are strings
                if not isinstance(summary, str):
                    summary = " ".join(flatten_list(summary))
                if not isinstance(reference_summary, str):
                    reference_summary = " ".join(flatten_list(reference_summary))

                # Add logging to check types
                logger.debug(f"Type of summary: {type(summary)}")
                logger.debug(f"Type of reference_summary: {type(reference_summary)}")

                rouge_scores_abstractive = rouge_scorer_instance.score(reference_summary, summary)
                logger.info(f"ROUGE between Reference Summary and Abstractive Summary:")
                logger.info(f"ROUGE-1: {rouge_scores_abstractive['rouge1'].fmeasure}, ROUGE-2: {rouge_scores_abstractive['rouge2'].fmeasure}, ROUGE-L: {rouge_scores_abstractive['rougeL'].fmeasure}")
                rouge1_scores.append(rouge_scores_abstractive['rouge1'].fmeasure)
                rouge2_scores.append(rouge_scores_abstractive['rouge2'].fmeasure)
                rougeL_scores.append(rouge_scores_abstractive['rougeL'].fmeasure)

                fkgl, dcrs, cli = calculate_readability(summary)
                fkgl_scores.append(fkgl)
                dcrs_scores.append(dcrs)
                cli_scores.append(cli)

                align_score = calculate_align_score(summary, reference_summary)
                align_scores.append(align_score)

                summac_score = calculate_summac_score(summary, reference_summary)
                summac_scores.append(summac_score)

            # After processing all repeats for the document, extend the main lists
            rouge1_all_scores.extend(rouge1_scores)
            rouge2_all_scores.extend(rouge2_scores)
            rougeL_all_scores.extend(rougeL_scores)
            fkgl_all_scores.extend(fkgl_scores)
            dcrs_all_scores.extend(dcrs_scores)
            cli_all_scores.extend(cli_scores)
            align_all_scores.extend(align_scores)
            summac_all_scores.extend(summac_scores)

        except Exception as e:
            logger.error(f"Error processing document {i+1}: {e}")
            traceback.print_exc()
            continue

    # Function to filter out invalid values
    def filter_valid_values(values_list):
        return [x for x in values_list if x is not None and not np.isnan(x)]

    # Apply filtering before calculating mean and std
    rouge1_valid_scores = filter_valid_values(rouge1_all_scores)
    rouge2_valid_scores = filter_valid_values(rouge2_all_scores)
    rougeL_valid_scores = filter_valid_values(rougeL_all_scores)
    fkgl_valid_scores = filter_valid_values(fkgl_all_scores)
    dcrs_valid_scores = filter_valid_values(dcrs_all_scores)
    cli_valid_scores = filter_valid_values(cli_all_scores)
    align_valid_scores = filter_valid_values(align_all_scores)
    summac_valid_scores = filter_valid_values(summac_all_scores)

    # Calculate the mean and std for all documents processed
    rouge1_mean = np.mean(rouge1_valid_scores) if rouge1_valid_scores else 0
    rouge1_std = np.std(rouge1_valid_scores) if rouge1_valid_scores else 0
    rouge2_mean = np.mean(rouge2_valid_scores) if rouge2_valid_scores else 0
    rouge2_std = np.std(rouge2_valid_scores) if rouge2_valid_scores else 0
    rougeL_mean = np.mean(rougeL_valid_scores) if rougeL_valid_scores else 0
    rougeL_std = np.std(rougeL_valid_scores) if rougeL_valid_scores else 0

    fkgl_mean = np.mean(fkgl_valid_scores) if fkgl_valid_scores else 0
    fkgl_std = np.std(fkgl_valid_scores) if fkgl_valid_scores else 0
    dcrs_mean = np.mean(dcrs_valid_scores) if dcrs_valid_scores else 0
    dcrs_std = np.std(dcrs_valid_scores) if dcrs_valid_scores else 0
    cli_mean = np.mean(cli_valid_scores) if cli_valid_scores else 0
    cli_std = np.std(cli_valid_scores) if cli_valid_scores else 0

    align_mean = np.mean(align_valid_scores) if align_valid_scores else 0
    align_std = np.std(align_valid_scores) if align_valid_scores else 0
    summac_mean = np.mean(summac_valid_scores) if summac_valid_scores else 0
    summac_std = np.std(summac_valid_scores) if summac_valid_scores else 0

    # Store final results in a list for CSV output
    result = {
        'Prompt Number': "All",
        'Prompt Text': per_prompt_metrics['prompt_text'],
        'Papers Tested': processed_docs,
        'Repeats': num_repeats,
        'Model': 'GPT',
        'ROUGE-1 Mean': rouge1_mean,
        'ROUGE-1 Std': rouge1_std,
        'ROUGE-2 Mean': rouge2_mean,
        'ROUGE-2 Std': rouge2_std,
        'ROUGE-L Mean': rougeL_mean,
        'ROUGE-L Std': rougeL_std,
        'BERTScore Mean': None,  # Placeholder as BERTScore is not calculated here
        'BERTScore Std': None,   # Placeholder as BERTScore is not calculated here
        'FKGL Mean': fkgl_mean,
        'FKGL Std': fkgl_std,
        'DCRS Mean': dcrs_mean,
        'DCRS Std': dcrs_std,
        'CLI Mean': cli_mean,
        'CLI Std': cli_std,
        'AlignScore Mean': align_mean,
        'AlignScore Std': align_std,
        'SummaC Mean': summac_mean,
        'SummaC Std': summac_std
    }

    # Write the results to a CSV file
    with open(csv_file_path, 'w', newline='') as csvfile:
        fieldnames = [
            'Prompt Number', 'Prompt Text', 'Papers Tested', 'Repeats', 'Model',
            'ROUGE-1 Mean', 'ROUGE-1 Std', 'ROUGE-2 Mean', 'ROUGE-2 Std',
            'ROUGE-L Mean', 'ROUGE-L Std', 'BERTScore Mean', 'BERTScore Std',
            'FKGL Mean', 'FKGL Std', 'DCRS Mean', 'DCRS Std', 'CLI Mean', 'CLI Std',
            'AlignScore Mean', 'AlignScore Std', 'SummaC Mean', 'SummaC Std'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerow(result)

    print(f"Results written to {csv_file_path}")
    logging.shutdown()

if __name__ == "__main__":
    data = load_data_from_json(json_file_path)
    evaluate_and_log(data)
