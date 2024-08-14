from dotenv import load_dotenv # loads API
import os 
import jsonlines
import google.generativeai as genai #[3]
from rouge_score import rouge_scorer #[2]

# .env
load_dotenv()

# Configuration for the API
api_key = os.getenv('API_KEY')
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-pro')

# Initialize the RougeScorer
scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)

# ROUGE-1: This indicates the match between the generated text and the reference text using 1-grams or individual words.
# ROUGE-2: The same than ROUGE-1, but It considers sets of 2-grams.
# ROUGE-L: This metric evaluates the match of the longest common subsequence of words between the two texts. The words do not need to be in the exact same order.[1]

jsonl_file_path = '/Users/nourchalouhi/Documents/COMP4092 Summarising Biomedical Workpapers to the Layperson/Summarisation Testing/src/data/summaries/dev_plos.jsonl'

with jsonlines.open(jsonl_file_path) as reader: # JSONL file reader
    summaryCount = 1  # Counter
    for document in reader:
        abstract = document.get('abstract', '')
        refSummary = document.get('plain language summary', '')  # Fetch the reference summary
        
        # Check if there's content to summarize and a reference summary (PLS)
        if abstract and refSummary:
            try:
                # Call API 
                response = model.generate_content(f'Summarise this abstract to the layperson {abstract}')
                summaryGenerated = response.text
                
                # Calculate the ROUGE scores
                scores = scorer.score(refSummary, summaryGenerated)
                
                # Formatting output
                print(f"Biomedical Paper {summaryCount} Summary:\n{summaryGenerated}\n")
                print("ROUGE Scores:")
                for score_type, score in scores.items():
                    print(f"  {score_type}: Precision: {score.precision:.4f}, Recall: {score.recall:.4f},  F1: {score.fmeasure:.4f}")
                # F1 formula score: 2 * (precision * recall) / (precision + recall)

                print("--------------------------------------------------\n")  # Spacing
                
            except Exception as e:
                print(f"Failed to generate summary for document {summaryCount} due to an error: {str(e)}\n")
        else:
            print(f"Document {summaryCount} is missing necessary data.\n")
        
        summaryCount += 1


#[1] https://towardsai.net/p/machine-learning/rouge-metrics-evaluating-summaries-in-large-language-models
#[2] https://pypi.org/project/rouge-metric/
#[3] https://ai.google.dev/tutorials/quickstart
#[4] https://www.nactem.ac.uk/readability/
