# Enhancing Layperson Accessibility to Biomedical Abstracts Through Prompt Engineering

This repository is part of the research project titled **"Enhancing Layperson Accessibility to Biomedical Abstracts Through Prompt Engineering"**. The goal of the project is to explore and develop techniques using Large Language Models (LLMs), such as GPT-4 and Gemini, to improve the accessibility of complex biomedical texts for lay audiences by generating clear and concise plain language summaries (PLS). 

---

## Project Overview

Effective communication is critical to bridge the gap between scientific experts and the general public. This project utilises **prompt engineering techniques** to guide LLMs in generating understandable and accurate lay summaries from biomedical research abstracts. 

### Key Features:
- **Prompt Engineering**: Utilises various prompt strategies such as persona, few-shot learning, and chain-of-thought to guide LLMs in summarising complex biomedical texts.
- **Model Integration**: Compares the performance of different LLMs like GPT-4 and Gemini to generate high-quality plain language summaries.
- **Evaluation**: Applies multiple evaluation metrics (ROUGE, BERTScore, readability scores) to assess the clarity and accuracy of generated summaries.

### Datasets:
- **PLOS and eLife**: The project uses publicly available biomedical research articles from the **PLOS** and **eLife** journals, which include both complex abstracts and professionally written plain language summaries.

---

## Repository Structure

The repository is structured as follows:

- **`README.md`**: This file, providing an overview of the project and its purpose.
- **`SummarisingBiomedicalWorkpapers.git/`**: Version-controlled project files.
- **`dataSets/`**: Contains the datasets used for training, validating, and testing the models.
- **`records/`**: Contains all minutes and progress through the projet
- **`src/`**: Source code for the project.


---

## Objectives

The primary objectives of this research project are:

1. **Assess LLM Effectiveness**: Evaluate the capability of LLMs (particularly GPT-4 and Gemini) to generate layperson-accessible summaries from complex biomedical abstracts.
2. **Compare Prompt Engineering Techniques**: Perform comparative analyses on various prompt strategies to identify which methods best simplify medical jargon while retaining factual accuracy.
3. **Develop Domain-Specific Prompts**: Fine-tune prompts with domain-specific inputs based on PLS guidelines to enhance the quality of the outputs.
4. **Evaluate Summaries**: Use readability scores (e.g., Flesch-Kincaid), ROUGE, and BERTScore to assess the readability, relevance, and factuality of the generated summaries.


