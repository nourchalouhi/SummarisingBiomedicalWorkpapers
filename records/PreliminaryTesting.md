# Project Title: Summarisation of Biomedical Workpapers - Preliminary Testing

## Overview
This project aims to explore different AI-based summarisation strategies to convert complex biomedical research paper abstracts into plain language summaries understandable by laypersons.

## Objective
To assess and compare the effectiveness of various summarisation approaches including persona-based, few-shot learning, and chain of thought techniques.
 
## Methodology

Tested different prompt strategies using Gemini Model in attempts to summarise the biomedical workpaper to the layperson. The scores were average out of 1000 PLOS workpapers. 

## Results

The table below presents the average ROUGE scores for each summarisation method:

| Summarisation Method | ROUGE-1 Score | ROUGE-2 Score | ROUGE-L Score |
|----------------------|---------------|---------------|---------------|
| Persona-Based        | 0.4019        | 0.0840        | 0.1938        |           
| Few-Shot Learning    | 0.3930        | 0.1008        | 0.2077        |           
| Chain of Thought     | 0.4859        | 0.1349        | 0.2201        |           

### Interpretation
- **ROUGE-1** measures the overlap of unigrams between the generated summary and the reference summary, indicating basic content matching.
- **ROUGE-2** focuses on the overlap of bigrams, which evaluates the fluency and order of content.
- **ROUGE-L** assesses the longest common subsequence of words, providing insight into sentence-level structure and fluency.

# Introducing Bert Score and Readability Metrics Across

## Final Evaluation Metrics Comparison: Almost 650 json Files 
Metrics for Prompt 1:
  rouge1: 0.4299
  rouge2: 0.1086
  rougeL: 0.2196
  bertscore: 0.8655
  readability: 11.3706
Metrics for Prompt 2:
  rouge1: 0.4197
  rouge2: 0.0998
  rougeL: 0.2045
  bertscore: 0.8524
  readability: 11.8079

  