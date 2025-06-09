"""
Biomedical Paper Summarisation — Extractive+Abstractive LLM Evaluation Pipeline

This script is part of a thesis project evaluating summarisation quality on biomedical research papers using large language models (LLMs).
- **Extracts key sentences** from biomedical abstracts using an LLM-powered extractive prompt.
- **Generates abstractive summaries** from extracted sentences and keyword guidance, using an LLM (OpenAI GPT-4o-mini by default).
- **Evaluates generated summaries** against human reference summaries using ROUGE metrics, BERTScore, and readability formulas (Flesch-Kincaid, Dale-Chall, Coleman-Liau).
- **Handles long abstracts** by splitting into manageable token-length chunks.
- **Logs outputs and metrics** for traceability and reproducibility.

This pipeline was developed for experimentation, benchmarking, and prompt engineering during the research process.
Please ensure your API keys, input/output file paths, and dependencies are correctly configured before use.


"""
from dotenv import load_dotenv
import os
import logging
import openai
import csv
import json
import numpy as np
from rouge_score import rouge_scorer
from bert_score import score as bert_score
import textstat
import tiktoken

load_dotenv()
openai_api_key = os.getenv('OPENAI_API_KEY')
openai.api_key = openai_api_key

rouge_scorer_instance = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
log_directory = '/File Path'
if not os.path.exists(log_directory):
    os.makedirs(log_directory)
log_file_path = os.path.join(log_directory, 'FileName.log')
csv_file_path = os.path.join(log_directory, 'FileName.csv')
json_file_path = '/FileName.json'
file_handler = logging.FileHandler(log_file_path)
console_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

num_repeats = 3  

def calculate_readability(text):
    fkgl = textstat.flesch_kincaid_grade(text)
    dcrs = textstat.dale_chall_readability_score(text)
    cli = textstat.coleman_liau_index(text)
    return fkgl, dcrs, cli

def split_text_into_chunks(text, max_tokens_per_chunk, model="gpt-4o-mini"):
    encoding = tiktoken.encoding_for_model(model)
    tokens = encoding.encode(text)
    chunks = []
    for i in range(0, len(tokens), max_tokens_per_chunk):
        chunk_tokens = tokens[i:i + max_tokens_per_chunk]
        chunk_text = encoding.decode(chunk_tokens)
        chunks.append(chunk_text)
    return chunks

def extract_key_sentences(abstract_text):
    model_name = "gpt-4o-mini"
    max_context_tokens = 4096
    max_response_tokens = 500
    max_prompt_tokens = max_context_tokens - max_response_tokens - 1000
    abstract_chunks = split_text_into_chunks(abstract_text, max_prompt_tokens, model=model_name)
    extracted_sentences_list = []
    for idx, chunk in enumerate(abstract_chunks):
        extractive_prompt = (
            f"Part {idx+1} of {len(abstract_chunks)}:\n\n"
            "Extract the key sentences from the following part of a research abstract that highlight "
            "the main objectives, methods, and findings. Ensure that all critical technical details are included.\n\n"
            f"{chunk}\n\n"
            "Return only the most important sentences as an extract."
        )
        response = openai.ChatCompletion.create(
            model=model_name,
            messages=[{"role": "user", "content": extractive_prompt}]
        )
        extracted_text = response['choices'][0]['message']['content']
        logger.info(f"Extractive Prompt: {extractive_prompt}")
        logger.info(f"Extracted key sentences: {extracted_text}")
        extracted_sentences_list.append(extracted_text)
    combined_extracted_text = ' '.join(extracted_sentences_list)
    return combined_extracted_text

def abstractive_summarization(extracted_text, keywords):
    model_name = "gpt-4o-mini"
    max_context_tokens = 8192
    max_response_tokens = 500
    max_prompt_tokens = max_context_tokens - max_response_tokens - 1000
    encoding = tiktoken.encoding_for_model(model_name)
    tokens = encoding.encode(extracted_text)
    few_shot_example = (
        "Example Abstract:\n"
        "Example Summary:\n"
    )
    keyword_string = ", ".join(keywords)
    if len(tokens) > max_prompt_tokens:
        chunks = split_text_into_chunks(extracted_text, max_prompt_tokens - len(encoding.encode(few_shot_example)), model=model_name)
        summaries = []
        for idx, chunk in enumerate(chunks):
            abstractive_prompt = (
                f"{few_shot_example}"
                f"Part {idx+1} of {len(chunks)}:\n\n"
                "Compose an accessible summary of the following key points, avoiding technical jargon and explaining any necessary terms in simple language. "
                f"Ensure that the summary includes the following keywords: {keyword_string}.\n\n"
                f"{chunk}\n\n"
                "The summary should be concise, engaging, and no more than 300 words."
            )
            response = openai.ChatCompletion.create(
                model=model_name,
                messages=[{"role": "user", "content": abstractive_prompt}]
            )
            summary_text = response['choices'][0]['message']['content']
            summaries.append(summary_text)
        combined_summary = ' '.join(summaries)
        final_prompt = (
            f"{few_shot_example}"
            "Provide a concise and accessible summary of the following text, avoiding technical jargon and explaining any necessary terms in simple language. "
            f"Ensure that the summary includes the following keywords: {keyword_string}.\n\n"
            f"{combined_summary}\n\n"
            "The final summary should be engaging and no more than 300 words."
        )
        response = openai.ChatCompletion.create(
            model=model_name,
            messages=[{"role": "user", "content": final_prompt}]
        )
        final_summary = response['choices'][0]['message']['content']
        return final_summary
    else:
        abstractive_prompt = (
            f"{few_shot_example}"
            "Compose an accessible summary of the following key points, avoiding technical jargon and explaining any necessary terms in simple language. "
            f"Ensure that the summary includes the following keywords: {keyword_string}.\n\n"
            f"{extracted_text}\n\n"
            "The summary should be concise, engaging, and no more than 300 words."
        )
        response = openai.ChatCompletion.create(
            model=model_name,
            messages=[{"role": "user", "content": abstractive_prompt}]
        )
        summary_text = response['choices'][0]['message']['content']
        return summary_text

def load_data_from_json(json_file_path):
    with open(json_file_path, 'r') as file:
        data = json.load(file)
    return data

def evaluate_and_log(data):
    per_prompt_metrics = {
        'prompt_text': "Extract and summarize abstracts",
        'papers_tested': 0,
        'repeats': num_repeats,
        'models': {
            'GPT': {
                'abstractive_metrics': {
                    'rouge1': [],
                    'rouge2': [],
                    'rougeL': [],
                    'bertscore': [],
                    'fkgl': [],
                    'dcrs': [],
                    'cli': []
                }
            }
        }
    }
    results_list = []
    max_documents = 50
    processed_docs = 0
    for i, document in enumerate(data):
        if processed_docs >= max_documents:
            break
        logger.info(f"Processing document {i+1}")
        abstract_list = document.get('abstract', [])
        refSummary_list = document.get('summary', [])
        keywords = document.get('keywords', [])
        abstract = " ".join(abstract_list) if isinstance(abstract_list, list) else abstract_list
        reference_summary = " ".join(refSummary_list) if isinstance(refSummary_list, list) else refSummary_list
        if not abstract or not reference_summary:
            logger.warning(f"Skipping document {i+1} due to missing abstract or summary.")
            continue
        per_prompt_metrics['papers_tested'] += 1
        processed_docs += 1
        rouge1_scores = []
        rouge2_scores = []
        rougeL_scores = []
        for repeat in range(num_repeats):
            logger.info(f"Repeat {repeat+1}/{num_repeats} for document {i+1}")
            extracted_sentences = extract_key_sentences(abstract)
            summary = abstractive_summarization(extracted_sentences, keywords)
            rouge_scores_abstractive = rouge_scorer_instance.score(reference_summary, summary)
            rouge1_scores.append(rouge_scores_abstractive['rouge1'].fmeasure)
            rouge2_scores.append(rouge_scores_abstractive['rouge2'].fmeasure)
            rougeL_scores.append(rouge_scores_abstractive['rougeL'].fmeasure)
        logger.info(f"Document {i+1} ROUGE-1 Scores: {rouge1_scores}")
        logger.info(f"Document {i+1} ROUGE-2 Scores: {rouge2_scores}")
        logger.info(f"Document {i+1} ROUGE-L Scores: {rougeL_scores}")
        rouge1_mean = np.mean(rouge1_scores)
        rouge1_std = np.std(rouge1_scores)
        rouge2_mean = np.mean(rouge2_scores)
        rouge2_std = np.std(rouge2_scores)
        rougeL_mean = np.mean(rougeL_scores)
        rougeL_std = np.std(rougeL_scores)
        logger.info(f"Document {i+1} ROUGE-1 Mean: {rouge1_mean}, Std: {rouge1_std}")
        logger.info(f"Document {i+1} ROUGE-2 Mean: {rouge2_mean}, Std: {rouge2_std}")
        logger.info(f"Document {i+1} ROUGE-L Mean: {rougeL_mean}, Std: {rougeL_std}")
        per_prompt_metrics['models']['GPT']['abstractive_metrics']['rouge1'].append({'mean': rouge1_mean, 'std': rouge1_std})
        per_prompt_metrics['models']['GPT']['abstractive_metrics']['rouge2'].append({'mean': rouge2_mean, 'std': rouge2_std})
        per_prompt_metrics['models']['GPT']['abstractive_metrics']['rougeL'].append({'mean': rougeL_mean, 'std': rougeL_std})
        result = {
            'document_id': i+1,
            'rouge1_mean': rouge1_mean,
            'rouge1_std': rouge1_std,
            'rouge2_mean': rouge2_mean,
            'rouge2_std': rouge2_std,
            'rougeL_mean': rougeL_mean,
            'rougeL_std': rougeL_std
        }
        results_list.append(result)
    with open(csv_file_path, 'w', newline='') as csvfile:
        fieldnames = ['document_id', 'rouge1_mean', 'rouge1_std', 'rouge2_mean', 'rouge2_std', 'rougeL_mean', 'rougeL_std']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for data in results_list:
            writer.writerow(data)
    print(f"Results written to {csv_file_path}")
    logging.shutdown()

if __name__ == "__main__":
    data = load_data_from_json(json_file_path)
    evaluate_and_log(data)