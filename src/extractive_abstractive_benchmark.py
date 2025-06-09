"""
Biomedical Paper Summarisation: Prompt Benchmark Script
-------------------------------------------------------
This script is part of a collection of benchmarking utilities used for my thesis research
on large language model (LLM) summarisation of biomedical literature. The script
evaluates various summarisation prompts for biomedical abstracts, using both Google Gemini
and OpenAI GPT models. It measures summary quality with multiple metrics (ROUGE, BERTScore,
readability, AlignScore, SummaC), supporting reproducible and comparative experiments.

Features:
- Extracts key sentences from abstracts with LexRank.
- Generates plain-language summaries with different prompt styles.
- Evaluates summaries against human references using ROUGE, BERTScore, readability, AlignScore, SummaC.
- Logs results and aggregates per-prompt metrics for direct comparison.
- Modular, reproducible, and suited to academic benchmarking.

Usage:
- Configure environment variables and paths at the top (or via .env).
- Adjust the number of documents and repeats as needed.
- Results will be saved as a CSV and all major steps logged.

Context:
This script is not meant for production use but is provided for reproducibility, transparency, and as a record of thesis experimental workflow.
"""
import os
import csv
import logging
import time
import json
import numpy as np
from dotenv import load_dotenv

import openai
import google.generativeai as genai
from rouge_score import rouge_scorer
from bert_score import score as bert_score
import textstat
from alignscore import AlignScore
from summac.model_summac import SummaCConv
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer

# Setup logger early!
def setup_logger(log_file_path):
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler(log_file_path)
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger

# Paths (use relative or .env)
load_dotenv()
SUMMAC_BIN_PATH = os.getenv("SUMMAC_BIN_PATH", "summac_conv_vitc_sent_perc_e.bin")
DATA_PATH = os.getenv("DATA_PATH", "data/val.json")
CSV_FILE_PATH = os.getenv("CSV_FILE_PATH", "outputs/results_PLOS_XEROSHOT.csv")
LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "outputs/prompt_output.log")

logger = setup_logger(LOG_FILE_PATH)

# API keys
google_api_key = os.getenv('API_KEY')
openai_api_key = os.getenv('OPENAI_API_KEY')

genai.configure(api_key=google_api_key)
google_model_name = os.getenv("GOOGLE_MODEL_NAME", "models/text-bison-001")
openai.api_key = openai_api_key

rouge_scorer_instance = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)

summac_model = SummaCConv(
    models=["vitc"],
    bins='percentile',
    granularity="sentence",
    nli_labels="e",
    device="cpu",
    start_file=SUMMAC_BIN_PATH,
    agg="mean"
)
alignscore_model = AlignScore(
    model='roberta-base', batch_size=16, device='cpu', ckpt_path=None, evaluation_mode='nli_sp'
)

def concatenate_items(value, default=''):
    if isinstance(value, list):
        return ' '.join(value) if value else default
    elif isinstance(value, str):
        return value
    else:
        return default

def extract_key_sentences(abstract_text, num_sentences=3):
    try:
        parser = PlaintextParser.from_string(abstract_text, Tokenizer('english'))
        summarizer = LexRankSummarizer()
        summary = summarizer(parser.document, num_sentences)
        extracted_sentences = ' '.join(str(sentence) for sentence in summary)
        return extracted_sentences
    except Exception as e:
        logger.error(f"Error in extract_key_sentences: {e}")
        print(f"Error in extract_key_sentences: {e}")
        return abstract_text

def create_prompts(document, extracted_sentences):
    title = document.get('title', 'No title available')
    year = document.get('year', 'No year available')
    prompt_intro_1 = (
        "Compose a detailed Plain-Language Summary (PLS) of the following key sentences extracted from a biomedical research paper to promote Knowledge Translation (KT) and make the findings accessible to a non-expert audience.\n\n"
    )
    prompt_intro_2 = (
        "Create an informative and accessible Plain-Language Summary (PLS) for the following key sentences extracted from a biomedical research paper, aimed at enhancing Knowledge Translation (KT) and making the content understandable to individuals without a scientific background.\n\n"
    )
    full_prompts = [
        prompt_intro_1 + f"**Title**: \"{title}\"\n" + f"**Year**: {year}\n\n" + f"**Key Sentences**:\n{extracted_sentences}\n\n",
        prompt_intro_2 + f"**Title**: \"{title}\"\n" + f"**Year**: {year}\n\n" + f"**Key Sentences**:\n{extracted_sentences}\n\n"
    ]
    return full_prompts

def calculate_readability(summary):
    fkgl = textstat.flesch_kincaid_grade(summary)
    dcrs = textstat.dale_chall_readability_score(summary)
    cli = textstat.coleman_liau_index(summary)
    return fkgl, dcrs, cli

def write_per_prompt_csv(per_prompt_metrics, file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
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
                avg_metrics = model_data['average_metrics']
                std_metrics = model_data['std_metrics']
                row = {
                    'Prompt Number': prompt_num,
                    'Prompt Text': prompt_text,
                    'Papers Tested': papers_tested,
                    'Repeats': repeats,
                    'Model': model_name,
                    'ROUGE-1 Mean': avg_metrics['rouge1'],
                    'ROUGE-1 Std': std_metrics['rouge1'],
                    'ROUGE-2 Mean': avg_metrics['rouge2'],
                    'ROUGE-2 Std': std_metrics['rouge2'],
                    'ROUGE-L Mean': avg_metrics['rougeL'],
                    'ROUGE-L Std': std_metrics['rougeL'],
                    'BERTScore Mean': avg_metrics['bertscore'],
                    'BERTScore Std': std_metrics['bertscore'],
                    'FKGL Mean': avg_metrics['fkgl'],
                    'FKGL Std': std_metrics['fkgl'],
                    'DCRS Mean': avg_metrics['dcrs'],
                    'DCRS Std': std_metrics['dcrs'],
                    'CLI Mean': avg_metrics['cli'],
                    'CLI Std': std_metrics['cli'],
                    'AlignScore Mean': avg_metrics['alignscore'],
                    'AlignScore Std': std_metrics['alignscore'],
                    'SummaC Mean': avg_metrics['summaC'],
                    'SummaC Std': std_metrics['summaC'],
                }
                writer.writerow(row)

def process_and_evaluate(data, num_repeats=3, num_documents=None):
    per_prompt_metrics = {}
    if num_documents is not None:
        data = data[:num_documents]
    for test_num, document in enumerate(data):
        abstract_text = concatenate_items(document.get("abstract", ""))
        if not abstract_text:
            logger.warning(f"Skipping document {test_num + 1} due to empty abstract.")
            continue
        extracted_sentences = extract_key_sentences(abstract_text, num_sentences=3)
        prompts = create_prompts(document, extracted_sentences)
        reference_summary = concatenate_items(document.get("summary", ""))
        if not reference_summary:
            logger.warning(f"Skipping document {test_num + 1} due to empty reference summary.")
            continue
        logger.info(f"Processing document {test_num + 1}")
        logger.info(f"Reference Summary: {reference_summary}")
        for prompt_num, full_prompt in enumerate(prompts, start=1):
            logger.info(f"Prompt {prompt_num}: {full_prompt}")
            if prompt_num not in per_prompt_metrics:
                per_prompt_metrics[prompt_num] = {
                    'prompt_text': full_prompt,
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
                    responseGoogle = genai.GenerativeModel(google_model_name).generate_content(
                        full_prompt,
                        generation_config={"max_output_tokens": 1024, "temperature": 0.3}
                    )
                    summaryGoogle = responseGoogle.text
                    logger.info(f"Google Gemini summary {repeat + 1}: {summaryGoogle}")
                    responseOpenAI = openai.ChatCompletion.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant."},
                            {"role": "user", "content": f'{full_prompt}'}
                        ],
                        max_tokens=1000,
                        temperature=0.3
                    )
                    summaryOpenAI = responseOpenAI['choices'][0]['message']['content']
                    logger.info(f"OpenAI GPT summary {repeat + 1}: {summaryOpenAI}")
                    rouge_google = rouge_scorer_instance.score(reference_summary, summaryGoogle)
                    rouge_openai = rouge_scorer_instance.score(reference_summary, summaryOpenAI)
                    logger.info(f"ROUGE Google: {rouge_google}")
                    logger.info(f"ROUGE OpenAI: {rouge_openai}")
                    P_google, R_google, F_google = bert_score([summaryGoogle], [reference_summary], lang="en", device='cpu')
                    P_openai, R_openai, F_openai = bert_score([summaryOpenAI], [reference_summary], lang="en", device='cpu')
                    logger.info(f"BERTScore Google F1: {F_google.mean().item()}")
                    logger.info(f"BERTScore OpenAI F1: {F_openai.mean().item()}")
                    fkgl_google, dcrs_google, cli_google = calculate_readability(summaryGoogle)
                    fkgl_openai, dcrs_openai, cli_openai = calculate_readability(summaryOpenAI)
                    alignscore_google = np.mean(alignscore_model.score(
                        contexts=[abstract_text], claims=[summaryGoogle]))
                    alignscore_openai = np.mean(alignscore_model.score(
                        contexts=[abstract_text], claims=[summaryOpenAI]))
                    summaC_google = np.mean(summac_model.score(
                        [abstract_text], [summaryGoogle])['scores'])
                    summaC_openai = np.mean(summac_model.score(
                        [abstract_text], [summaryOpenAI])['scores'])
                    logger.info(f"AlignScore Google: {alignscore_google}, SummaC Google: {summaC_google}")
                    logger.info(f"AlignScore OpenAI: {alignscore_openai}, SummaC OpenAI: {summaC_openai}")
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
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"Error processing doc {test_num+1}, prompt {prompt_num}, repeat {repeat+1}: {e}")
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

if __name__ == "__main__":
    with open(DATA_PATH, 'r') as f:
        data = json.load(f)
    num_documents_to_process = 2
    per_prompt_metrics = process_and_evaluate(data, num_repeats=3, num_documents=num_documents_to_process)
    write_per_prompt_csv(per_prompt_metrics, CSV_FILE_PATH)
    logging.shutdown()
    print(f"Per-prompt aggregated results have been written to {CSV_FILE_PATH}")