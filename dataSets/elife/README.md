# eLife JSON Dataset

This repository contains the `eLife` dataset in JSON format. The dataset consists of biomedical research papers from the eLife journal, specifically focused on papers, their abstracts, sections, and plain language summaries. The dataset is intended for use in tasks such as summarisation, text analysis, and natural language processing (NLP).

## Dataset Structure

The dataset is divided into three files:

- **train.json**: Training set
- **val.json**: Validation set
- **test.json**: Test set

Each file contains a list of research papers, represented as JSON objects with various fields. These files are typically used for training, validating, and testing machine learning models, especially for tasks like generating plain language summaries from biomedical abstracts.

## File Information

- **File Format**: JSON
- **Data Source**: eLife journal publications
- **Purpose**: This dataset is used to evaluate plain language summarisation of biomedical abstracts using AI models and other NLP tasks.

## Structure of the JSON File

Each research paper in the dataset is represented as a JSON object with the following structure:

```json
{
  "id": "elife-56656-v2",
  "year": "2020",
  "title": "SKAP2 is required for defense against K. pneumoniae infection and neutrophil respiratory burst",
  "sections": [
    ["Section content as a list of paragraphs"]
  ],
  "headings": [
    "Introduction",
    "Results",
    "Discussion",
    "Materials and methods"
  ],
  "abstract": [
    "List of abstract paragraphs"
  ],
  "summary": [
    "Plain language summary paragraphs"
  ],
  "keywords": [
    "developmental biology"
  ]
}