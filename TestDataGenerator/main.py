import os
from dotenv import load_dotenv
from openai import OpenAI
import anthropic
import google.generativeai
import gradio as gr
from io import StringIO
import pandas as pd
import tempfile

load_dotenv(override=True)

openai_api = os.getenv("OPENAI_API_KEY")
google_api = os.getenv('GOOGLE_API_KEY')
anthropic_api = os.getenv("ANTHROPIC_API_KEY")
hf_token = os.getenv("HF_TOKEN")

system_prompt = f"""You create synthetic datasets for testing purposes.  
Based on the use case description, generate a CSV dataset with appropriate columns and a as much rows as the user tell
of realistic logic data.

IMPORTANT RULES:
1. Return ONLY the CSV data with headers and ensure there are no duplicate headers
2. No explanatory text before or after
3. No markdown formatting or code fences
4. No quotation marks around the entire response
5. Start directly with the column headers
6. The data itself has to be logically realistic.

Format: column1 (e.g. customer_id),column2 (e.g. country),column3 (e.g. age)
row1data,row1data,row1data
row2data,row2data,row2data"""

def data_user_prompt(usecase, num_rows):
  user_prompt = "Create a synthetic dataset for the use case provided below: "
  user_prompt += usecase
  user_prompt += f" Respond in csv with appropriate headers.  Do not include any other explanatory text, markdown formatting or code fences, or quotation marks around the entire response.  \
  Generate exactly {num_rows} rows of data for each column."
  return user_prompt


def openai_call(usecase, num_rows):
    openai = OpenAI()
    messages = [{"role":"system", "content":system_prompt},
                {"role":"user", "content":data_user_prompt(usecase, num_rows)}]
    response = openai.chat.completions.create(model="gpt-4o-mini", messages=messages, temperature=0.7)
    return response.choices[0].message.content

def anthropic_call(usecase, num_rows):
    claude = anthropic.Anthropic()
    response = claude.messages.create(model = "claude-3-7-sonnet-latest",
                                      system = system_prompt,
                                      messages=[
                                          {"role": "user", "content": data_user_prompt(usecase, num_rows)}
                                      ],
                                      temperature=0.7,
                                      max_tokens = 3500)

    return response.content[0].text

def google_call(usecase, num_rows):
    google.generativeai.configure()
    gemini = google.generativeai.GenerativeModel(
        model_name='gemini-2.0-flash',
        system_instruction=system_prompt
    )
    response = gemini.generate_content(data_user_prompt(usecase, num_rows))
    return response.text


def phi3_call(usecase, num_rows):
    return 0

def llama_call(usecase, num_rows):
    return 0

def generate_test_data(usecase, num_rows, model):

    if model == "OpenAI GPT-4o-mini":
        response = openai_call(usecase, num_rows)
    elif model == "Anthropic Claude 3.7 Sonnet":
        response = anthropic_call(usecase, num_rows)
    elif model == "Meta Llama":
        response = llama_call(usecase, num_rows)
    elif model == "Microsoft Phi-3":
        response = phi3_call(usecase, num_rows)
    elif model == "Google Gemini 2.0-flash":
        response = google_call(usecase, num_rows)

    df = pd.read_csv(StringIO(response))

    # Create a temporary file in a safe OS-dependent location
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
    df.to_csv(temp_file.name, index=False)
    temp_file.close()

    return df, temp_file.name


demo = gr.Interface(
    fn = generate_test_data ,
    inputs = [gr.Textbox(lines=5,label="Describe your usecase:",placeholder="Describe the dataset you would like to create and how you will use it"),
              gr.Slider(minimum=1, maximum=200, step=1, value=20, label="Number of rows"),
              gr.Dropdown(choices=["OpenAI GPT-4o-mini", "Anthropic Claude 3.7 Sonnet", "Google Gemini 2.0-flash", "Meta Llama", "Microsoft Phi-3"], value="OpenAI GPT-4o", label="Select Model")],
    outputs = [gr.DataFrame(label="Here is your dataset!",interactive=True),
               gr.File(label="Download CSV")],
    title = "Synthetic Data Generator",
    description = "Let me know your use case for synthetic data and I will create it for you.",
    examples = [
    ["Generate a dataset of students with columns: student_id, full_name, age, major, GPA, and graduation_year", 18],
    ["Create synthetic online orders data with order_id, customer_name, product_category, order_date, quantity, and total_price", 50],
    ["Generate patient records for a hospital with patient_id, name, age, gender, diagnosis, treatment_plan, and admission_date", 60],
    ["Generate car dealership data with model_name, manufacturer, year, price_usd, mileage, and fuel_type", 30]
    ],
    flagging_mode="never"
)

demo.launch()