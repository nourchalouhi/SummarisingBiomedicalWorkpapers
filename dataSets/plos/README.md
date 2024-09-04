# PLOS JSON Dataset

This repository contains the PLOS dataset in JSON format. The dataset consists of biomedical research papers from the Public Library of Science (PLOS), including abstracts, sections, and plain language summaries. The dataset is split into training, validation, and test sets for use in tasks like summarisation, text analysis, and natural language processing (NLP).

## Dataset Structure

The dataset is split into three files:

- **train.json**: Training set
- **val.json**: Validation set
- **test.json**: Test set

Each file contains a list of JSON objects, where each object represents a research paper. Below is the structure of a typical document.

## File Information

- **File Format**: JSON
- **Data Source**: Public Library of Science (PLOS) journal publications
- **Purpose**: The dataset is intended for summarization and natural language processing tasks, particularly focusing on generating plain language summaries from biomedical research abstracts.

## JSON Structure

Each research paper in the dataset follows a similar structure:

```json
{
  "id": "plos-12345",
  "year": "2018",
  "title": "Impact of Climate Change on Public Health",
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
    "public health",
    "climate change"
  ]
}