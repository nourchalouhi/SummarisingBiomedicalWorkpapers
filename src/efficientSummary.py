from dotenv import load_dotenv
import os
import jsonlines
import google.generativeai as genai
from rouge_score import rouge_scorer

load_dotenv()

api_key = os.getenv('API_KEY')
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-pro')

scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)

jsonl_file_path = '/Users/nourchalouhi/Documents/COMP4092 Summarising Biomedical Workpapers to the Layperson/Summarisation Testing/src/data/dev_plos.jsonl'

# Define multiple prompts
prompts = [
    "Please explain the main findings of this biomedical abstract in simple language that a non-expert would understand:",
#
]

# Initialize dictionaries to hold scores for each prompt
total_scores = {i: {'rouge1': [], 'rouge2': [], 'rougeL': []} for i in range(len(prompts))}

with jsonlines.open(jsonl_file_path) as reader:
    for summary_count, document in enumerate(reader, start=1):
        if summary_count > 10:  # Only process the first 10 documents
            break

        abstract = document.get('abstract', '')
        ref_summary = document.get('plain language summary', '')

        if abstract and ref_summary:
            for i, prompt in enumerate(prompts):
                try:
                    response = model.generate_content(f'{prompt} {abstract}')
                    summary = ' '.join(response.text.split()[:200])
                    scores = scorer.score(ref_summary, summary)  # Corrected variable name
                    for key in scores:
                        total_scores[i][key].append(scores[key].fmeasure)
                except Exception as e:
                    print(f"Failed to generate summary for document {summary_count}, prompt {i+1} due to an error: {str(e)}")

# Calculate average scores and rank them
average_scores = {i: {key: sum(values) / len(values) for key, values in score_dict.items()} for i, score_dict in total_scores.items()}

# Determine which prompt performed best for each ROUGE metric
best_prompts = {}
for metric in ['rouge1', 'rouge2', 'rougeL']:
    best_prompt_index = sorted(average_scores.items(), key=lambda item: item[1][metric], reverse=True)[0][0]
    best_prompts[metric] = (best_prompt_index, average_scores[best_prompt_index][metric])

# Print the results
print("\nFinal ROUGE Score Comparison:")
for i, scores in average_scores.items():
    print(f"Average ROUGE Scores for Prompt {i+1}:")
    for key, value in scores.items():
        print(f"  {key}: {value:.4f}")

print("\nBest Prompt Rankings:")
for key, (index, score) in best_prompts.items():
    print(f"For {key}, the best prompt is {index+1} with a score of {score:.4f}")
