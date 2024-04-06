from dotenv import load_dotenv # loads API
import os #fetch environmental variables 
import jsonlines
import google.generativeai as genai
from rouge_score import rouge_scorer

# .env
load_dotenv()

#configuration for the API
api_key = os.getenv('API_KEY')
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-pro')

# Initialise the RougeScorer
scorer = rouge_scorer.RougeScorer(['rouge1', 'rouge2', 'rougeL'], use_stemmer=True)

# Set the path directly to your JSONL file
jsonl_file_path = '/Users/nourchalouhi/Documents/COMP4092 Summarising Biomedical Workpapers to the Layperson/Summarisation Testing/src/data/dev_plos.jsonl'

with jsonlines.open(jsonl_file_path) as reader:# JSONL file reader
    summaryCount = 1  # counter
    for document in reader:
        abstract = document.get('abstract', '')
        refSummary = document.get('plain language summary', '')  #fetch the ref ummary
        
        #check if there's content to summarise and a ref summary
        if abstract and refSummary:
            try:
                #call API 
                response = model.generate_content(f'Please summarise this biomedical abstract to the layperson. {abstract}')
                summaryGenerated = response.text
                
                #200 words limit
                summaryWords = summaryGenerated.split()[:200]
                summaryGenerated = ' '.join(summaryWords)
                
                #calculate the ROUGE scores
                scores = scorer.score(refSummary, summaryGenerated)
                
                # Formatting output
                print(f"Biomedical Paper {summaryCount} Summary:\n{summaryGenerated}\n")
                print("ROUGE Scores:")
                for score_type, score in scores.items():
                    print(f"  {score_type}: Precision: {score.precision:.4f}, Recall: {score.recall:.4f},  F1: {score.fmeasure:.4f}")
               #F1 formula score :2 * (precision * recall) / (precision + recall)

                print("--------------------------------------------------\n")  #spacing
                
            except Exception as e:
                print(f"Failed to generate summary for document {summaryCount} due to an error: {str(e)}\n")
        else:
            print(f"Document {summaryCount} is missing necessary data.\n")
        
        summaryCount += 1
