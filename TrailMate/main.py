import os
from dotenv import load_dotenv
from openai import OpenAI
import gradio as gr
import json
import tools
from io import BytesIO
import tempfile
import subprocess
from pydub import AudioSegment
import time


# tools ideas: Route Finder / Hiking Trails Lookup(AllTrails API), Gear recommendation, Speech recognition
# Add typing messages

load_dotenv(override=True)

openai_api = os.getenv("OPENAI_API_KEY")
google_api = os.getenv('GOOGLE_API_KEY')
anthropic_api = os.getenv("ANTHROPIC_API_KEY")


# Set connections
openai = OpenAI()
# claude = anthropic.Anthropic()
# google.generativeai.configure()

MODEL = "gpt-4o-mini"


force_dark_mode = """
function refresh() {
    const url = new URL(window.location);
    if (url.searchParams.get('__theme') !== 'dark') {
        url.searchParams.set('__theme', 'dark');
        window.location.href = url.href;
    }
}
"""

system_message = """
You are TrailMate, a friendly and humorous hiking assistant.

Your mission is to help the user plan and enjoy hiking adventures: recommending gear, planning routes, checking weather, and visualizing ideas.

You can:
- Use tools to look up weather conditions for specific places and times.
- Use tools to generate visual images when asked (e.g., “show me”, “draw”, “generate”, “visualize”).
- Speak your responses out loud via text-to-speech after replying (handled by the system).

Style:
- Be adventurous, encouraging, and outdoorsy — like a well-traveled trail buddy.
- Use short, natural sentences, with a light dose of humor.
- If replying to a question that would benefit from visualizing or weather data, trigger the appropriate tool instead of guessing.

Do NOT:
- Mention that you are using tools — just act as if you naturally know the info.

You are here to make hiking more exciting, well-prepared, and fun.
"""



tools_list = [tools.weather_tool, tools.image_tool]


def play_audio(audio_segment):
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, "temp_audio.wav")
    try:
        audio_segment.export(temp_path, format="wav")
        time.sleep(
            3)  # Student Dominic found that this was needed. You could also try commenting out to see if not needed on your PC
        subprocess.call([
            "ffplay",
            "-nodisp",
            "-autoexit",
            "-hide_banner",
            temp_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    finally:
        try:
            os.remove(temp_path)
        except Exception:
            pass


def talker(message):
    response = openai.audio.speech.create(
        model="tts-1",
        voice="onyx",  # Also, try replacing onyx with alloy
        input=message
    )
    audio_stream = BytesIO(response.content)
    audio = AudioSegment.from_file(audio_stream, format="mp3")
    play_audio(audio)


def chat(message, history):
    # Step 1: Reconstruct messages manually from history (filtered)
    messages = [{"role": "system", "content": system_message}]

    # Append all valid history messages, skipping any base64 image replies
    for item in history:
        if item["role"] == "assistant" and item["content"].startswith("Here’s what I’ve visualized"):
            continue  # skip image response
        messages.append(item)

    # Step 2: Add current user message
    messages.append({"role": "user", "content": message})

    # Step 3: Send to OpenAI with tool support
    response = openai.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=tools_list
    )

    # Step 4: Handle tool call
    if response.choices[0].finish_reason == "tool_calls":
        tool_message = response.choices[0].message
        tool_response, _ = handle_tool_call(tool_message)

        if "image_url" in json.loads(tool_response["content"]):
            # Do not add tool call to history for images
            talker("Here’s what I’ve visualized for you")
            return f"Here’s what I’ve visualized for you:\n![Generated Image]({json.loads(tool_response['content'])['image_url']})"

        # Append tool messages
        messages.append(tool_message)
        messages.append(tool_response)

        # Step 5: Continue the conversation after the tool call
        response = openai.chat.completions.create(
            model=MODEL,
            messages=messages
        )

    talker(response.choices[0].message.content)
    return response.choices[0].message.content


def handle_tool_call(message):
    tool_call = message.tool_calls[0]
    func_name = tool_call.function.name
    arguments = json.loads(tool_call.function.arguments)

    if func_name == "get_weather":
        city = arguments.get("location")
        when = arguments.get("when", "now")
        weather = tools.get_weather(city, when)
        response = {
            "role": "tool",
            "content": json.dumps({"location": city, "weather": weather}),
            "tool_call_id": tool_call.id
        }
        return response, city

    elif func_name == "generate_image":
        prompt = arguments.get("prompt")
        image_url = tools.generate_image(prompt)
        response = {
            "role": "tool",
            "content": json.dumps({"image_url": image_url}),
            "tool_call_id": tool_call.id
        }
        return response, None

gr.ChatInterface(fn=chat, type="messages", js=force_dark_mode).launch()

