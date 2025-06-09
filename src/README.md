Biomedical Paper Summarisation Project - Source Code Overview


This folder contains all Python scripts developed and used throughout my thesis experiments on biomedical paper summarisation using large language models (LLMs). 

Each script represents a different benchmarking pipeline, evaluation routine, or experimental prompt strategy trialed during the research. The variety of scripts here reflects the iterative, comparative, and exploratory approach taken to determine optimal prompting and summarisation performance for biomedical abstracts.

⸻

File Descriptions

	•	biomed_prompt_comparison.py

Benchmarking different prompt formulations for biomedical summarisation.

	•	extractive_abstractive_benchmark.py

Experiments combining extractive and abstractive summarisation, including various scoring metrics.

	•	extractive_abstractive_pipeline.py

End-to-end pipeline that automates extractive + abstractive summary generation and evaluation.

	•	llm_fewshot_summarisation_benchmark.py

Few-shot benchmarking: tests the effect of different few-shot prompt examples on summary quality.

	•	promptwise_summarisation_benchmark.py

Script for testing and comparing individual prompt variants on biomedical abstracts.

	•	summarisation_llm_benchmark.py

General LLM benchmarking for biomedical summarisation tasks.
	•	summarisation_prompt_comparison.py

Direct comparison of summarisation prompts, models, and output metrics.

	•	xero_biomed_summ_benchmark.py

(Custom variant; e.g. new metric integrations, model-specific evaluation, or for Xero-specific experiments—adapt description as needed.)

⸻

Notes

	•	All scripts were used at different stages of experimentation and iteration for my thesis.

	•	Each file targets a particular experimental question, evaluation scenario, or model setup.

	•	Scripts are not always standalone or production-ready—many are for rapid prototyping, comparison, and batch runs on datasets.

	•	For more details on how each experiment informed the thesis, please refer to the main thesis document or experimental appendix.

⸻

Usage

	•	Please review each script’s top-level comments and adjust file paths, API keys, or dependencies as needed before running.

	•	Most scripts require a valid .env with your API keys, and the correct data file paths set up as per your local structure.

