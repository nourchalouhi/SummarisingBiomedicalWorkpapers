"""
Biomedical Paper Summarisation — Prompt Comparison Pipeline

Compares Google Gemini and OpenAI GPT model summaries using a variety of prompt templates on biomedical abstracts.
Calculates ROUGE, BERTScore, readability, and (optionally) factuality metrics. All results are written to CSV.
Set your API keys in a .env file and configure file paths before running.
"""
from dotenv import load_dotenv
import os
import csv
import openai
import google.generativeai as genai
from statistics import mean, stdev
import time
import json
from rouge_score import rouge_scorer
from bert_score import score as bert_score
import textstat
import numpy as np

# Optional: Import these only if available
try:
    from alignscore import AlignScore
    from summac.model_summac import SummaCConv
    HAS_FACTUALITY_MODELS = True
except ImportError:
    HAS_FACTUALITY_MODELS = False

# Load environment variables from .env
load_dotenv()

# Get API keys from environment variables
google_api_key = os.getenv('API_KEY')          # Set your Gemini API Key in .env
openai_api_key = os.getenv('OPENAI_API_KEY')   # Set your OpenAI API Key in .env

if not google_api_key or not openai_api_key:
    raise ValueError("API_KEY and OPENAI_API_KEY must be set in your .env file.")

# Configure Gemini and OpenAI
genai.configure(api_key=google_api_key)
google_model = genai.GenerativeModel('gemini-pro')
openai.api_key = openai_api_key

# ROUGE scorer
rouge_scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)

# Optional: Initialise factuality models if available
if HAS_FACTUALITY_MODELS:
    summac_model = SummaCConv(
        models=["vitc"],
        bins='percentile',
        granularity="sentence",
        nli_labels="e",
        device="cpu",
        start_file="PATH/TO/summac_conv_vitc_sent_perc_e.bin",  
        agg="mean"
    )
    alignscore_model = AlignScore(
        model='roberta-base', batch_size=16, device='cpu', ckpt_path=None, evaluation_mode='nli_sp'
    )

DATA_PATH = os.path.join('data', 'val.json')
PROMPT_LOG_PATH = os.path.join('logs', 'prompt_log.csv')
CSV_FILE_PATH = os.path.join('outputs', 'chain_of_thought_results.csv')

# Utility to log prompts and responses
def log_prompt(hypothesis_test, prompt, model, generated_summary):
    try:
        with open(PROMPT_LOG_PATH, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([hypothesis_test, prompt, model, generated_summary])
    except Exception as e:
        print(f"Error logging prompt: {e}")

def ensure_string(value):
    if isinstance(value, list):
        return " ".join(value)
    elif isinstance(value, str):
        return value
    return ""


def create_prompts(document):
    abstract = ensure_string(document.get("abstract", ""))
    title = document.get('title', 'No title available')
    year = document.get('year', 'No year available')
    keywords = document.get('keywords', ['No keywords available'])
    if not isinstance(keywords, list):
        keywords = [keywords]
    prompts = [
    ]
    return prompts

def write_to_csv(results, file_path):
    try:
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
    except Exception as e:
        print(f"Error writing to CSV: {e}")

def calculate_readability(summary):
    fkgl = textstat.flesch_kincaid_grade(summary)
    dcrs = textstat.dale_chall_readability_score(summary)
    cli = textstat.coleman_liau_index(summary)
    return fkgl, dcrs, cli

def process_and_evaluate(data, num_repeats=2):
    results = []
    for test_num, document in enumerate(data[:20]):
        prompts = create_prompts(document)
        reference_summary = ensure_string(document.get("summary", ""))
        for prompt_num, prompt in enumerate(prompts):
            hypothesis_test = f"Hypothesis Test {test_num + 1} - Prompt {prompt_num + 1}"
            google_results, openai_results = [], []
            for repeat in range(num_repeats):
                try:
                    # Google Gemini generation
                    responseGoogle = google_model.generate_content(f'{prompt}')
                    summaryGoogle = ensure_string(getattr(responseGoogle, 'text', 'Blocked Response'))
                    log_prompt(hypothesis_test, prompt, 'Google Gemini', summaryGoogle)
                    # OpenAI GPT generation
                    responseOpenAI = openai.ChatCompletion.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "system", "content": "You are a helpful assistant."},
                                  {"role": "user", "content": f'{prompt}'}]
                    )
                    summaryOpenAI = ensure_string(responseOpenAI['choices'][0]['message']['content'])
                    log_prompt(hypothesis_test, prompt, 'OpenAI GPT', summaryOpenAI)
                    # ROUGE
                    rouge_google = rouge_scorer.score(summaryGoogle, reference_summary)
                    rouge_openai = rouge_scorer.score(summaryOpenAI, reference_summary)
                    # BERTScore
                    _, _, F_google = bert_score([summaryGoogle], [reference_summary], lang="en", device='cpu')
                    _, _, F_openai = bert_score([summaryOpenAI], [reference_summary], lang="en", device='cpu')
                    # Readability
                    fkgl_google, dcrs_google, cli_google = calculate_readability(summaryGoogle)
                    fkgl_openai, dcrs_openai, cli_openai = calculate_readability(summaryOpenAI)
                    # Factuality (if available)
                    alignscore_google = alignscore_openai = 0
                    summaC_google = summaC_openai = 0
                    if HAS_FACTUALITY_MODELS:
                        abstract_text = ensure_string(document.get("abstract", ""))
                        alignscore_google = np.mean(alignscore_model.score(
                            contexts=[abstract_text], claims=[summaryGoogle]))
                        alignscore_openai = np.mean(alignscore_model.score(
                            contexts=[abstract_text], claims=[summaryOpenAI]))
                        summaC_google = np.mean(summac_model.score(
                            [abstract_text], [summaryGoogle])['scores'])
                        summaC_openai = np.mean(summac_model.score(
                            [abstract_text], [summaryOpenAI])['scores'])
                    # Collect results
                    google_results.append([
                        rouge_google['rouge1'].fmeasure, rouge_google['rouge2'].fmeasure, rouge_google['rougeL'].fmeasure,
                        F_google.mean().item(), fkgl_google, dcrs_google, cli_google, alignscore_google, summaC_google
                    ])
                    openai_results.append([
                        rouge_openai['rouge1'].fmeasure, rouge_openai['rouge2'].fmeasure, rouge_openai['rougeL'].fmeasure,
                        F_openai.mean().item(), fkgl_openai, dcrs_openai, cli_openai, alignscore_openai, summaC_openai
                    ])
                    time.sleep(3)  # API rate limit buffer
                except Exception as e:
                    print(f"Error: {e}")
                    google_results.append([0]*9)
                    openai_results.append([0]*9)
            google_means = [mean([x[i] for x in google_results]) for i in range(9)]
            google_stds = [stdev([x[i] for x in google_results]) if len(google_results) > 1 else 0 for i in range(9)]
            openai_means = [mean([x[i] for x in openai_results]) for i in range(9)]
            openai_stds = [stdev([x[i] for x in openai_results]) if len(openai_results) > 1 else 0 for i in range(9)]
            results.append([hypothesis_test, prompt, 'Google Gemini'] + google_means + google_stds)
            results.append([hypothesis_test, prompt, 'OpenAI GPT'] + openai_means + openai_stds)
    return results

# Entrypoint for running the script
if __name__ == "__main__":
    # Load the JSON dataset
    if not os.path.isfile(DATA_PATH):
        raise FileNotFoundError(f"Dataset not found at {DATA_PATH}. Please update DATA_PATH.")

    with open(DATA_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    final_results = process_and_evaluate(data)
    write_to_csv(final_results, CSV_FILE_PATH)
    print(f"Results have been written to {CSV_FILE_PATH}")