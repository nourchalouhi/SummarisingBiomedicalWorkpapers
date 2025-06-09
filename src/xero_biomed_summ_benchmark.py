"""
LLM Biomedical Summarisation Multi-Metric Benchmark

Runs Google Gemini and OpenAI GPT on biomedical abstract summarisation, evaluating outputs
with ROUGE, BERTScore, readability (FKGL, DCRS, CLI), AlignScore, and SummaC.
Aggregates and logs results per prompt and model, storing all results in CSV for easy analysis.

Safe for public repositories (no sensitive data paths, no API key logging).
"""

import os
import csv
import logging
import openai
import google.generativeai as genai
import time
import json
from dotenv import load_dotenv
from rouge_score import rouge_scorer
from bert_score import score as bert_score
import textstat
import numpy as np
from alignscore import AlignScore
from summac.model_summac import SummaCConv

# === 1. Setup ===

# Paths (relative for public code sharing)
DATA_PATH = 'data/plos_val.json'
OUTPUT_DIR = 'outputs'
CSV_FILE_PATH = os.path.join(OUTPUT_DIR, 'xero_biomed_summ_benchmark.csv')
LOG_FILE_PATH = os.path.join(OUTPUT_DIR, 'xero_biomed_summ_benchmark.log')

os.makedirs(OUTPUT_DIR, exist_ok=True)
if not os.path.isfile(DATA_PATH):
    raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")

# Logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(LOG_FILE_PATH)
console_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# API keys
load_dotenv()
google_api_key = os.getenv('API_KEY')
openai_api_key = os.getenv('OPENAI_API_KEY')
if not google_api_key or not openai_api_key:
    raise RuntimeError("API keys must be set in your .env file.")

genai.configure(api_key=google_api_key)
google_model = genai.GenerativeModel('gemini-pro')
openai.api_key = openai_api_key

# Metrics models
rouge = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)
summac_model = SummaCConv(
    models=["vitc"],
    bins='percentile',
    granularity="sentence",
    nli_labels="e",
    device="cpu",
    start_file="src/summac/summac_conv_vitc_sent_perc_e.bin",  # Relative path for repo
    agg="mean"
)
alignscore_model = AlignScore(
    model='roberta-base', batch_size=16, device='cpu', ckpt_path=None, evaluation_mode='nli_sp'
)

# === 2. Utilities ===

def concatenate_items(value, default=''):
    if isinstance(value, list):
        return ' '.join(value) if value else default
    elif isinstance(value, str):
        return value
    return default

def create_prompts(document):
    abstract = concatenate_items(document.get("abstract", ""))
    title = document.get('title', 'No title available')
    year = document.get('year', 'No year available')

    prompt_intro_1 = (
        "Compose a detailed Plain-Language Summary (PLS) of the following biomedical research paper to promote Knowledge Translation (KT) and make the findings accessible to a non-expert audience.\n\n"
    )
    prompt_intro_2 = (
        "Create an informative and accessible Plain-Language Summary (PLS) for the following biomedical research paper, aimed at enhancing Knowledge Translation (KT) and making the content understandable to individuals without a scientific background.\n\n"
    )
    full_prompts = [
        prompt_intro_1 + f"**Title**: \"{title}\"\n**Year**: {year}\n\n**Abstract**:\n{abstract}\n\n",
        prompt_intro_2 + f"**Title**: \"{title}\"\n**Year**: {year}\n\n**Abstract**:\n{abstract}\n\n"
    ]
    sanitized_abstract = "[Abstract text not shown]"
    sanitized_prompts = [
        prompt_intro_1 + f"**Title**: \"{title}\"\n**Year**: {year}\n\n**Abstract**:\n{sanitized_abstract}\n\n",
        prompt_intro_2 + f"**Title**: \"{title}\"\n**Year**: {year}\n\n**Abstract**:\n{sanitized_abstract}\n\n"
    ]
    generalized_prompts = [prompt_intro_1, prompt_intro_2]
    return list(zip(full_prompts, sanitized_prompts, generalized_prompts))

def calculate_readability(summary):
    return (
        textstat.flesch_kincaid_grade(summary),
        textstat.dale_chall_readability_score(summary),
        textstat.coleman_liau_index(summary)
    )

def write_per_prompt_csv(per_prompt_metrics, file_path):
    with open(file_path, 'w', newline='') as csvfile:
        fieldnames = [
            'Prompt Number', 'Prompt Text', 'Papers Tested', 'Repeats', 'Model',
            'ROUGE-1 Mean', 'ROUGE-1 Std',
            'ROUGE-2 Mean', 'ROUGE-2 Std',
            'ROUGE-L Mean', 'ROUGE-L Std',
            'BERTScore Mean', 'BERTScore Std',
            'FKGL Mean', 'FKGL Std',
            'DCRS Mean', 'DCRS Std',
            'CLI Mean', 'CLI Std',
            'AlignScore Mean', 'AlignScore Std',
            'SummaC Mean', 'SummaC Std'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for prompt_num, prompt_data in per_prompt_metrics.items():
            prompt_text = prompt_data['prompt_text']
            papers_tested = prompt_data['papers_tested']
            repeats = prompt_data['repeats']
            for model_name, model_data in prompt_data['models'].items():
                avg = model_data['average_metrics']
                std = model_data['std_metrics']
                row = {
                    'Prompt Number': prompt_num,
                    'Prompt Text': prompt_text,
                    'Papers Tested': papers_tested,
                    'Repeats': repeats,
                    'Model': model_name,
                    'ROUGE-1 Mean': avg['rouge1'],
                    'ROUGE-1 Std': std['rouge1'],
                    'ROUGE-2 Mean': avg['rouge2'],
                    'ROUGE-2 Std': std['rouge2'],
                    'ROUGE-L Mean': avg['rougeL'],
                    'ROUGE-L Std': std['rougeL'],
                    'BERTScore Mean': avg['bertscore'],
                    'BERTScore Std': std['bertscore'],
                    'FKGL Mean': avg['fkgl'],
                    'FKGL Std': std['fkgl'],
                    'DCRS Mean': avg['dcrs'],
                    'DCRS Std': std['dcrs'],
                    'CLI Mean': avg['cli'],
                    'CLI Std': std['cli'],
                    'AlignScore Mean': avg['alignscore'],
                    'AlignScore Std': std['alignscore'],
                    'SummaC Mean': avg['summaC'],
                    'SummaC Std': std['summaC'],
                }
                writer.writerow(row)

# === 3. Main Processing ===

def process_and_evaluate(data, num_repeats=3, num_documents=None):
    per_prompt_metrics = {}
    if num_documents is not None:
        data = data[:num_documents]
    for test_num, document in enumerate(data):
        prompts = create_prompts(document)
        reference_summary = concatenate_items(document.get("summary", ""))
        logger.info(f"Processing document {test_num + 1}")
        logger.info(f"Reference Summary: {reference_summary[:180]}...")  # Safe log

        for prompt_num, (full_prompt, sanitized_prompt, generalized_prompt) in enumerate(prompts, start=1):
            logger.info(f"Prompt {prompt_num}: {sanitized_prompt}")
            if prompt_num not in per_prompt_metrics:
                per_prompt_metrics[prompt_num] = {
                    'prompt_text': generalized_prompt,
                    'papers_tested': 0,
                    'repeats': num_repeats,
                    'models': {
                        'Google Gemini': { 'metrics': {k: [] for k in [
                            'rouge1','rouge2','rougeL','bertscore','fkgl','dcrs','cli','alignscore','summaC']}},
                        'OpenAI GPT': { 'metrics': {k: [] for k in [
                            'rouge1','rouge2','rougeL','bertscore','fkgl','dcrs','cli','alignscore','summaC']}},
                    }
                }
            per_prompt_metrics[prompt_num]['papers_tested'] += 1
            for repeat in range(num_repeats):
                try:
                    # --- Model Calls ---
                    responseGoogle = google_model.generate_content(full_prompt)
                    summaryGoogle = responseGoogle.text
                    logger.info(f"Google summary {repeat + 1}: {summaryGoogle[:180]}...")

                    responseOpenAI = openai.ChatCompletion.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant."},
                            {"role": "user", "content": full_prompt}
                        ],
                        max_tokens=1000,
                        temperature=0.3
                    )
                    summaryOpenAI = responseOpenAI['choices'][0]['message']['content']
                    logger.info(f"OpenAI summary {repeat + 1}: {summaryOpenAI[:180]}...")

                    # --- Metrics ---
                    rouge_google = rouge.score(reference_summary, summaryGoogle)
                    rouge_openai = rouge.score(reference_summary, summaryOpenAI)
                    P_google, R_google, F_google = bert_score(
                        [summaryGoogle], [reference_summary], lang="en", device='cpu')
                    P_openai, R_openai, F_openai = bert_score(
                        [summaryOpenAI], [reference_summary], lang="en", device='cpu')
                    fkgl_google, dcrs_google, cli_google = calculate_readability(summaryGoogle)
                    fkgl_openai, dcrs_openai, cli_openai = calculate_readability(summaryOpenAI)
                    abstract_text = concatenate_items(document.get("abstract", ""))
                    alignscore_google = float(np.mean(alignscore_model.score(
                        contexts=[abstract_text], claims=[summaryGoogle])))
                    alignscore_openai = float(np.mean(alignscore_model.score(
                        contexts=[abstract_text], claims=[summaryOpenAI])))
                    summaC_google = float(np.mean(summac_model.score(
                        [abstract_text], [summaryGoogle])['scores']))
                    summaC_openai = float(np.mean(summac_model.score(
                        [abstract_text], [summaryOpenAI])['scores']))

                    metrics_google = {
                        'rouge1': rouge_google['rouge1'].fmeasure,
                        'rouge2': rouge_google['rouge2'].fmeasure,
                        'rougeL': rouge_google['rougeL'].fmeasure,
                        'bertscore': F_google.mean().item(),
                        'fkgl': fkgl_google,
                        'dcrs': dcrs_google,
                        'cli': cli_google,
                        'alignscore': alignscore_google,
                        'summaC': summaC_google
                    }
                    metrics_openai = {
                        'rouge1': rouge_openai['rouge1'].fmeasure,
                        'rouge2': rouge_openai['rouge2'].fmeasure,
                        'rougeL': rouge_openai['rougeL'].fmeasure,
                        'bertscore': F_openai.mean().item(),
                        'fkgl': fkgl_openai,
                        'dcrs': dcrs_openai,
                        'cli': cli_openai,
                        'alignscore': alignscore_openai,
                        'summaC': summaC_openai
                    }
                    for metric_name, value in metrics_google.items():
                        per_prompt_metrics[prompt_num]['models']['Google Gemini']['metrics'][metric_name].append(value)
                    for metric_name, value in metrics_openai.items():
                        per_prompt_metrics[prompt_num]['models']['OpenAI GPT']['metrics'][metric_name].append(value)
                    time.sleep(1)  # Be API friendly

                except Exception as e:
                    logger.error(f"Error on document {test_num + 1}, prompt {prompt_num}, repeat {repeat + 1}: {e}")
                    for metric_name in per_prompt_metrics[prompt_num]['models']['Google Gemini']['metrics']:
                        per_prompt_metrics[prompt_num]['models']['Google Gemini']['metrics'][metric_name].append(0)
                        per_prompt_metrics[prompt_num]['models']['OpenAI GPT']['metrics'][metric_name].append(0)

    for prompt_num, prompt_data in per_prompt_metrics.items():
        for model_name in ['Google Gemini', 'OpenAI GPT']:
            metrics = prompt_data['models'][model_name]['metrics']
            average_metrics = {metric_name: np.mean(values) for metric_name, values in metrics.items()}
            std_metrics = {metric_name: np.std(values) for metric_name, values in metrics.items()}
            prompt_data['models'][model_name]['average_metrics'] = average_metrics
            prompt_data['models'][model_name]['std_metrics'] = std_metrics

    return per_prompt_metrics

# === 4. Run Experiment ===

if __name__ == "__main__":
    with open(DATA_PATH, 'r') as f:
        data = json.load(f)
    num_documents_to_process = 50
    per_prompt_metrics = process_and_evaluate(data, num_repeats=3, num_documents=num_documents_to_process)
    write_per_prompt_csv(per_prompt_metrics, CSV_FILE_PATH)
    logging.shutdown()
    print(f"\nPer-prompt aggregated results have been written to {CSV_FILE_PATH}\nLogs are in {LOG_FILE_PATH}")