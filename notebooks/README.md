Date / Time: 4PM 12/03/2024

Discussions:

•	Key points discussed:
o	Attributes of machine learning pertinent to the project.
o	Techniques in Summarisation
o	Framework for system implementation 
o	Scoring System
o	Common Techniques for prompt Engineering
o	Fact Checking and AI Hallucination mitigation.
o	criteria for assessing summarisation quality.
o	Error analysis
o	Improving quality of summarisation
o	Central issues within the scope of this research field.

To Do:

•	Review literature and databases emailed by supervisor:
1.	Readability Controllable Biomedical Document Summarisation by Zheheng Luo, et al.: Introduces a corpus with 28,124 biomedical papers for readability-adjustable summarisation, showcasing transformer-based methods. Paper | Corpus
2.	Making Science Simple: Corpora for the Lay Summarisation of Scientific Literature by Tomas Goldsack, et al.: Offers a general corpus for scientific literature summarisation, not limited to biomedical texts. Paper | GitHub
3.	A Dataset for Plain Language Adaptation of Biomedical Abstracts by Kush Attal, et al.: Provides a dataset of 750 abstracts and 7,653 sentence pairs for biomedical abstracts' plain language adaptation. Paper | Dataset
Completed:
•	Reviewed academic papers.
•	Analysed databases for structural insights of biomedical papers.
 


Date / Time: 11:30AM 19/03/2024

Discussions:
•	Shared insights from literature on evaluation metrics, with a focus on ROUGE.
•	Highlighted the importance of choosing the most relevant evaluation frameworks for summarisation output assessment.
•	Discussed the use of various AI platforms for preliminary summarisation experimentation, including Chat GPT, Gemini, and PaLM 2, deciding on Gemini for its cost advantage.
•	Recommended to download the ROUGE evaluation toolkit via the Anaconda platform.
•	Emphasised finding the most relevant evaluation metric tailored to the objectives of the study.

To Do:
•	Advised to write some code to summarise biomedical papers and compare to the already summarised paragraphs.
•	Advised to try some prompts using the PLOS sample.
•	Emailed by Supervisor: 
" I just read the Google's PaLM is no longer supported, instead you can use Gemini. You can read the documentation here: https://ai.google.dev/docs
You have the choice to obtain a developer key and develop the code in your computer (the preferred choice), or develop using Google AI Studio (which may be good for the first time and for quick tests)"
•	Create a Git Repository to add meeting minutes and all related documentation.

Completed:
•	Set up development environment by downloading Python and the Anaconda distribution.
•	Switched back to using Visual Studio Code as my primary IDE.
•	Installed the conda package manager, Python extensions for IDE, and other relevant packages necessary for my project.
•	Wrote a Python script that uses the integrated API 'Gemini Pro' from Google's Generative AI to automatically summarise biomedical research papers. 
•	The script reads from a JSONL file containing document abstracts and sequentially generates summaries, restricting them to the first 200 words 
•	Each summary is numbered and formatted for clear differentiation, with error handling in place to manage any potential issues during the summarisation process.

