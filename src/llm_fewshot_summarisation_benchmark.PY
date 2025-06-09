"""
LLM Few-Shot Summarisation Benchmark

Benchmarks Google Gemini and OpenAI GPT models on biomedical abstract summarisation
using few-shot prompt templates. Evaluates outputs with ROUGE metrics and logs all
results for later inspection.
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
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

# Load environment variables
load_dotenv()

# Fetch API keys and configure models
google_api_key = os.getenv('API_KEY')      # Google API Key
openai_api_key = os.getenv('OPENAI_API_KEY')  # OpenAI API Key
if not google_api_key or not openai_api_key:
    raise RuntimeError("API keys must be set in your .env file.")

genai.configure(api_key=google_api_key)
google_model = genai.GenerativeModel('gemini-pro')  # Ensure this is a valid model name for your API
openai.api_key = openai_api_key

# Initialize ROUGE scorer
rouge_scorer_instance = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)

# Relative paths for input and output
DATA_PATH = 'data/plos_val.json'
OUTPUT_DIR = 'outputs'
os.makedirs(OUTPUT_DIR, exist_ok=True)
csv_file_path = os.path.join(OUTPUT_DIR, 'results_fewshot_ROUGE.csv')
prompt_log_path = os.path.join(OUTPUT_DIR, 'results_fewshot_ROUGE.txt')

# Check for data file
if not os.path.isfile(DATA_PATH):
    raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")

# Load the JSON dataset
with open(DATA_PATH, 'r') as f:
    data = json.load(f)

def get_first_item(value, default=''):
    if isinstance(value, list):
        return ' '.join(value) if value else default
    elif isinstance(value, str):
        return value
    else:
        return default

def create_prompts(document, example_abstracts_summaries):
    abstract = get_first_item(document.get("abstract", ""))
    title = document.get('title', 'No title available')
    year = document.get('year', 'No year available')

    if not isinstance(abstract, str) or not abstract.strip():
        abstract = "No abstract available."

    # Few-shot example
    few_shot_example = (
        "Example:\n"
        "Abstract:\n"
        "Summary:\n"
         )

    prompts = [
        f"{few_shot_example}Now, based on the following abstract, write a summary:\n\nAbstract:\n{abstract}\n\nSummary:",
        f"{few_shot_example}Please summarize the following abstract:\n\nAbstract:\n{abstract}\n\nSummary:",
        f"{few_shot_example}Given the abstract below, generate a concise summary:\n\nAbstract:\n{abstract}\n\nSummary:",
        f"{few_shot_example}Read the abstract and provide a brief summary highlighting the main findings:\n\nAbstract:\n{abstract}\n\nSummary:",
        f"{few_shot_example}Using the example as a guide, write a summary for this abstract:\n\nAbstract:\n{abstract}\n\nSummary:",
    ]
    return prompts

def write_to_csv(results, file_path):
    with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "Prompt", "Model", "Papers Tested",
            "ROUGE-1 (Mean)", "ROUGE-1 (STD)",
            "ROUGE-2 (Mean)", "ROUGE-2 (STD)",
            "ROUGE-L (Mean)", "ROUGE-L (STD)"
        ])
        for result in results:
            writer.writerow(result)

def log_prompts(prompt_log, prompt_id, model_name, prompt_text, summary):
    with open(prompt_log, 'a', encoding='utf-8') as f:
        f.write(f"\nPrompt ID: {prompt_id}\n")
        f.write(f"Model: {model_name}\n")
        f.write(f"Prompt:\n{prompt_text}\n")
        f.write(f"Generated Summary:\n{summary}\n")
        f.write("="*50 + "\n")

def process_and_evaluate(data, example_abstracts_summaries, num_repeats=3):
    results = []
    total_documents = len(data[:5])
    for test_num, document in enumerate(data[:5]):  # Limit to first 5 documents for testing
        print(f"Processing document {test_num + 1}/{total_documents}")
        prompts = create_prompts(document, example_abstracts_summaries)
        reference_summary = get_first_item(document.get("summary", ""))

        for prompt_num, prompt in enumerate(prompts):
            print(f"  Using prompt {prompt_num + 1}/{len(prompts)}")
            prompt_id = f"Prompt {prompt_num + 1}"
            google_results = []
            openai_results = []

            for repeat in range(num_repeats):
                print(f"    Repeat {repeat + 1}/{num_repeats}")
                try:
                    responseGoogle = google_model.generate_content(
                        prompt=prompt,
                        max_output_tokens=1024
                    )
                    summaryGoogle = responseGoogle.text
                    log_prompts(prompt_log_path, prompt_id, 'Google Gemini', prompt, summaryGoogle)

                    responseOpenAI = openai.ChatCompletion.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.7
                    )
                    summaryOpenAI = responseOpenAI['choices'][0]['message']['content']
                    log_prompts(prompt_log_path, prompt_id, 'OpenAI GPT', prompt, summaryOpenAI)

                    rouge_google = rouge_scorer_instance.score(reference_summary, summaryGoogle)
                    rouge_openai = rouge_scorer_instance.score(reference_summary, summaryOpenAI)

                    google_results.append([
                        rouge_google['rouge1'].fmeasure, rouge_google['rouge2'].fmeasure, rouge_google['rougeL'].fmeasure
                    ])
                    openai_results.append([
                        rouge_openai['rouge1'].fmeasure, rouge_openai['rouge2'].fmeasure, rouge_openai['rougeL'].fmeasure
                    ])

                except Exception as e:
                    print(f"Error processing prompt {prompt_id}, iteration {repeat + 1}: {e}")
                    logging.exception("Exception occurred")
                    google_results.append([0]*3)
                    openai_results.append([0]*3)

            google_means = [mean([x[i] for x in google_results]) for i in range(3)]
            google_stds = [stdev([x[i] for x in google_results]) if len(google_results) > 1 else 0 for i in range(3)]
            openai_means = [mean([x[i] for x in openai_results]) for i in range(3)]
            openai_stds = [stdev([x[i] for x in openai_results]) if len(openai_results) > 1 else 0 for i in range(3)]

            results.append([prompt_id, 'Google Gemini', total_documents] + google_means + google_stds)
            results.append([prompt_id, 'OpenAI GPT', total_documents] + openai_means + openai_stds)

    return results

# Example abstract and summary for few-shot learning (from the example you provided)
example_abstracts_summaries = {
    "abstract": [
      ],
    "summary": [
     ]
}

# Process the prompts and collect results
final_results = process_and_evaluate(data, example_abstracts_summaries, num_repeats=3)

# Write the results to a CSV file
write_to_csv(final_results, csv_file_path)

print(f"Results have been written to {csv_file_path}")
print(f"Prompt log has been saved to {prompt_log_path}")