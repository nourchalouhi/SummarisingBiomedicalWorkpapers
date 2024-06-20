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

jsonl_file_path = '/Users/nourchalouhi/Documents/COMP4092 Summarising Biomedical Workpapers to the Layperson/Summarisation Testing/src/data/summaries/dev_plos.jsonl'  #[4]

totalScores1 = {'rouge1': [], 'rouge2': [], 'rougeL': []}
totalScores2 = {'rouge1': [], 'rouge2': [], 'rougeL': []}

with jsonlines.open(jsonl_file_path) as reader:
    summaryCount = 0  # Initialize the counter to zero
    for document in reader:
        if summaryCount >= 10:  # Check if 10 summaries have already been processed
            break
        abstract = document.get('abstract', '')
        refSummary = document.get('plain language summary', '')


        if abstract and refSummary:
            try:
                # Generate summaries with both prompts
                response1 = model.generate_content(f'Create an abstractive Plain language summary a non expert would understand without the use of biomedical jargon{abstract}')
                summary1 = ' '.join(response1.text.split()[:200])

                response2 = model.generate_content(f'You are an expert summarizer reviewing a scientific paper. As you read through the abstract, carefully consider the key points that a non-expert might need to understand the essence of the research. Walk me through your thought process as you distill this information into a concise summary suitable for a general audience, explaining why you select certain pieces of information and omit others. {abstract}')
                summary2 = ' '.join(response2.text.split()[:200])

                # Calculate and store ROUGE scores
                scores1 = scorer.score(refSummary, summary1)
                scores2 = scorer.score(refSummary, summary2)
                for key in totalScores1.keys():
                    totalScores1[key].append(scores1[key].fmeasure)
                    totalScores2[key].append(scores2[key].fmeasure)

                print(f"Processed document {summaryCount}")
            except Exception as e:
                print(f"Failed to generate summary for document {summaryCount} due to an error: {str(e)}\n")
        
        summaryCount += 1

#calculates the average scores
averageScores1 = {key: sum(values)/ len(values) for key, values in totalScores1.items()}
averageScores2 = {key: sum(values)/ len(values) for key, values in totalScores2.items()}

#display the final comparison
print("\nFinal ROUGE Score Comparison:")
print("Average ROUGE Scores for Prompt 1:")

for key, value in averageScores1.items():
    print(f"  {key}: {value:.4f}")

print("Average ROUGE Scores for Prompt 2:")
for key, value in averageScores2.items():
    print(f"  {key}: {value:.4f}")

for key in averageScores1: #determine which prompt performed better overall

    betterPrompt = "Prompt 1" if averageScores1[key] > averageScores2[key] else "Prompt 2"
    print(f"For {key}, {betterPrompt} performed better.")
