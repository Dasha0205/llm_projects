import os
import io
import sys
import json
import requests
from dotenv import load_dotenv
from gradio import close_all
from openai import OpenAI
import google.generativeai
import anthropic
from IPython.display import Markdown, display, update_display
import gradio as gr
import subprocess


load_dotenv(override=True)

openai_api = os.getenv("OPENAI_API_KEY")
google_api = os.getenv('GOOGLE_API_KEY')
anthropic_api = os.getenv("ANTHROPIC_API_KEY")

openai = OpenAI()
claude = anthropic.Anthropic()
google.generativeai.configure()
OPENAI_MODEL = "gpt-4o"
CLAUDE_MODEL = "claude-3-5-sonnet-20240620"
GOOGLE_MODEL = "gemini-2.0-flash"


system_message = "You are an assistant that reimplements Python code in high performance C++ for Windows. "
system_message += "Respond only with C++ code; use comments sparingly and do not provide any explanation other than occasional comments. "
system_message += ("The C++ response needs to produce an identical output in the fastest possible time. Keep track of a programm logic, you have to understand"
                   "and implement the logic to get the same result as python code")

def user_prompt_for(python):
    user_prompt = "Rewrite this Python code in C++ with the fastest possible implementation that produces identical output in the least time. "
    user_prompt += "Respond only with C++ code; do not explain your work other than a few comments. "
    user_prompt += "Pay attention to number types to ensure no int overflows. Remember to #include all necessary C++ packages such as iomanip.\n\n"
    user_prompt += python
    return user_prompt

def messages_for(python):
    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_prompt_for(python)}
    ]

def write_output(cpp):
    code = cpp.replace("```cpp","").replace("```","")
    with open("optimized.cpp", "w") as f:
        f.write(code)

def stream_gpt(python):
    stream = openai.chat.completions.create(model=OPENAI_MODEL, messages=messages_for(python), stream=True)
    reply=""
    for chunk in stream:
        fragment = chunk.choices[0].delta.content or ""
        reply += fragment
        yield reply.replace('```cpp\n','').replace('```','')

def stream_claude(python):
    stream = claude.messages.create(model=CLAUDE_MODEL,
                                    system=system_message,
                                    messages=[{"role": "user", "content": user_prompt_for(python)}],
                                    stream=True,
                                    max_tokens=4096)
    reply = ""
    for chunk in stream:
        fragment = chunk.choices[0].delta.content or ""
        reply += fragment
        yield reply.replace('```cpp\n','').replace('```','')

def stream_google(python):

    gemini = google.generativeai.GenerativeModel(
        model_name='gemini-2.0-flash',
        system_instruction=system_message
    )

    stream = gemini.generate_content(user_prompt_for(python), stream=True)

    reply = ""
    for chunk in stream:
        fragment = chunk.choices[0].delta.content or ""
        reply += fragment
        yield reply.replace('```cpp\n', '').replace('```', '')

pi = """
import time

def calculate(iterations, param1, param2):
    result = 1.0
    for i in range(1, iterations+1):
        j = i * param1 - param2
        result -= (1/j)
        j = i * param1 + param2
        result += (1/j)
    return result

start_time = time.time()
result = calculate(100_000_000, 4, 1) * 4
end_time = time.time()

print(f"Result: {result:.12f}")
print(f"Execution Time: {(end_time - start_time):.6f} seconds")
"""

def optimize(python, model):
    if model=="GPT":
        result = stream_gpt(python)
    elif model=="Claude":
        result = stream_claude(python)
    elif model=="Gemini":
        result = stream_google(python)
    else:
        raise ValueError("Unknown model")
    for stream_so_far in result:
        yield stream_so_far

def execute_python(code):
    try:
        output = io.StringIO()
        sys.stdout = output
        exec(code)
    finally:
        sys.stdout = sys.__stdout__
    return output.getvalue()

def execute_cpp(code):
    write_output(code)

    # Use g++ or the compiler available in your environment
    compiler_cmd = ["g++", "-O3", "-std=c++17", "-o", "optimized.exe", "optimized.cpp"]

    try:
        compile_result = subprocess.run(compiler_cmd, check=True, text=True, capture_output=True)

        # Run the compiled executable on Windows
        run_cmd = ["optimized.exe"]
        run_result = subprocess.run(run_cmd, check=True, text=True, capture_output=True)

        return run_result.stdout
    except subprocess.CalledProcessError as e:
        return f"An error occurred:\n{e.stderr}"

css = """
.python {background-color: #306998;}
.cpp {background-color: #050;}
"""

with gr.Blocks(css=css) as ui:
    gr.Markdown("## Convert code from Python to C++")
    with gr.Row():
        python = gr.Textbox(label="Python code:", value=pi, lines=10)
        cpp = gr.Textbox(label="C++ code:", lines=10)
    with gr.Row():
        model = gr.Dropdown(["GPT", "Claude"], label="Select model", value="GPT")
    with gr.Row():
        convert = gr.Button("Convert code")
    with gr.Row():
        python_run = gr.Button("Run Python")
        cpp_run = gr.Button("Run C++")
    with gr.Row():
        python_out = gr.TextArea(label="Python result:", elem_classes=["python"])
        cpp_out = gr.TextArea(label="C++ result:", elem_classes=["cpp"])

    convert.click(optimize, inputs=[python, model], outputs=[cpp])
    python_run.click(execute_python, inputs=[python], outputs=[python_out])
    cpp_run.click(execute_cpp, inputs=[cpp], outputs=[cpp_out])

ui.launch(inbrowser=True)
