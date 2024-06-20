from dotenv import load_dotenv  # loads API
import os
import google.generativeai as genai

load_dotenv() #  loading environment variables from a .env file

# configuration for the API
api_key = os.getenv('API_KEY')
genai.configure(api_key=api_key)

model = genai.GenerativeModel('gemini-pro') # initialising the generative model


def generate_content(prompt): # generating content using the model

    try:
        response = model.generate_content(prompt)
        summary_generated = response.text
        print(f"Generated Content:\n{summary_generated}\n")
        print("--------------------------------------------------\n")
    except Exception as e:
        print(f"An error occurred: {e}")

# Example usage
generate_content('hello')
