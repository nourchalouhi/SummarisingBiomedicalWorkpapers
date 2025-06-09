"""
Chain-of-Thought Prompting Evaluation for Biomedical Summarisation

This script benchmarks chain-of-thought (CoT) style prompting and baseline prompts on biomedical research abstracts
using both Google Gemini and OpenAI GPT models. For each abstract, multiple CoT prompt variants are tested.
The resulting summaries are compared to gold-standard references using ROUGE metrics.

Features:
- Loads biomedical abstract dataset from JSON.
- Runs 5 custom prompt variants per abstract (edit `create_prompts()` to define your prompts).
- Calls both Gemini and GPT for each prompt and logs all outputs.
- Evaluates each generated summary with ROUGE-1, ROUGE-2, and ROUGE-L.
- Writes all results to a CSV for downstream analysis.

"""
from dotenv import load_dotenv
import os
import csv
import openai
import google.generativeai as genai
import time
import json
from rouge_score import rouge_scorer
from statistics import mean, stdev

load_dotenv()

google_api_key = os.getenv('API_KEY')
openai_api_key = os.getenv('OPENAI_API_KEY')

genai.configure(api_key=google_api_key)
google_model = genai.GenerativeModel('gemini-pro')
openai.api_key = openai_api_key

rouge_scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)

DATA_PATH = os.path.join('data', 'val.json')
CSV_FILE_PATH = os.path.join('outputs', 'chain_of_thought.csv')

with open(DATA_PATH, 'r') as f:
    data = json.load(f)

def get_first_item(value, default=''):
    if isinstance(value, list):
        return value[0] if value else default
    elif isinstance(value, str):
        return value
    else:
        return default

def create_prompts(document):
    abstract = get_first_item(document.get("abstract", ""))
    title = document.get('title', 'No title available')
    year = document.get('year', 'No year available')
    keywords = document.get('keywords', ['No keywords available'])
    if not isinstance(keywords, list):
        keywords = [keywords]
    prompts = [
        (
            f"**Title**: \"{title}\"\n"
            f"**Year**: {year}\n\n"
            f"**Abstract**:\n{abstract}\n\n"
            f"**Keywords**: {', '.join(keywords)}\n\n"
            "PROMPT 1\n"
        ),
        (
            f"**Title**: \"{title}\"\n"
            f"**Year**: {year}\n\n"
            f"**Abstract**:\n{abstract}\n\n"
            f"**Keywords**: {', '.join(keywords)}\n\n"
            "PROMPT 2\n"
        ),
        (
            f"**Title**: \"{title}\"\n"
            f"**Year**: {year}\n\n"
            f"**Abstract**:\n{abstract}\n\n"
            f"**Keywords**: {', '.join(keywords)}\n\n"
            "PROMPT 3\n"
        ),
        (
            f"**Title**: \"{title}\"\n"
            f"**Year**: {year}\n\n"
            f"**Abstract**:\n{abstract}\n\n"
            f"**Keywords**: {', '.join(keywords)}\n\n"
            "PROMPT 4\n"

        ),
        (
            f"**Title**: \"{title}\"\n"
            f"**Year**: {year}\n\n"
            f"**Abstract**:\n{abstract}\n\n"
            f"**Keywords**: {', '.join(keywords)}\n\n"
            "PROMPT 5\n"
        )
    ]
    return prompts

def write_to_csv(results, file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            "Hypothesis Test", "Prompt", "Model",
            "ROUGE-1 (Mean)", "ROUGE-1 (STD)", "ROUGE-2 (Mean)", "ROUGE-2 (STD)",
            "ROUGE-L (Mean)", "ROUGE-L (STD)"
        ])
        for result in results:
            writer.writerow(result)

def process_and_evaluate(data, num_repeats=2):
    results = []
    for test_num, document in enumerate(data[:5]):
        prompts = create_prompts(document)
        reference_summary = get_first_item(document.get("summary", ""))
        for prompt_num, prompt in enumerate(prompts):
            hypothesis_test = f"Hypothesis Test {test_num + 1} - Prompt {prompt_num + 1}"
            google_results = []
            openai_results = []
            for repeat in range(num_repeats):
                try:
                    responseGoogle = google_model.generate_content(f'{prompt}')
                    summaryGoogle = responseGoogle.text
                    responseOpenAI = openai.ChatCompletion.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "You are a helpful assistant."},
                            {"role": "user", "content": f'{prompt}'}
                        ],
                    )
                    summaryOpenAI = responseOpenAI['choices'][0]['message']['content']
                    rouge_google = rouge_scorer.score(summaryGoogle, reference_summary)
                    rouge_openai = rouge_scorer.score(summaryOpenAI, reference_summary)
                    google_results.append([
                        rouge_google['rouge1'].fmeasure, rouge_google['rouge2'].fmeasure, rouge_google['rougeL'].fmeasure
                    ])
                    openai_results.append([
                        rouge_openai['rouge1'].fmeasure, rouge_openai['rouge2'].fmeasure, rouge_openai['rougeL'].fmeasure
                    ])
                    time.sleep(1)
                except Exception as e:
                    google_results.append([0]*3)
                    openai_results.append([0]*3)
            google_means = [mean([x[i] for x in google_results]) for i in range(3)]
            google_stds = [stdev([x[i] for x in google_results]) if len(google_results) > 1 else 0 for i in range(3)]
            openai_means = [mean([x[i] for x in openai_results]) for i in range(3)]
            openai_stds = [stdev([x[i] for x in openai_results]) if len(openai_results) > 1 else 0 for i in range(3)]
            results.append([hypothesis_test, prompt, 'Google Gemini'] + google_means + google_stds)
            results.append([hypothesis_test, prompt, 'OpenAI GPT'] + openai_means + openai_stds)
    return results

final_results = process_and_evaluate(data)
write_to_csv(final_results, CSV_FILE_PATH)
print(f"Results have been written to {CSV_FILE_PATH}")