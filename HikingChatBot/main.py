import os
import requests
from dotenv import load_dotenv
from openai import OpenAI
import google.generativeai
import anthropic
import gradio as gr
import json

"""
 Hiking ChatBot assistant, helping people with choosing the route, gear, planning the trip and finding out the details. 
    - Chat Interface
    - Adding Tools (Access to maps, etc)
    - Sound recognition
    - Image generation (for what?)
"""

load_dotenv(override=True)

openai_api = os.getenv("OPENAI_API_KEY")
google_api = os.getenv('GOOGLE_API_KEY')
anthropic_api = os.getenv("ANTHROPIC_API_KEY")


# Set connections
openai = OpenAI()
claude = anthropic.Anthropic()
google.generativeai.configure()

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
system_message = """You are hiking assistant. You are helping the user in all questions about hikes,
                    choose gear and routes. You are very humorous and adventurous. You should encourage people
                    to take challenges."""


def get_weather(location: str, when: str = "now") -> str:
    api_key = os.getenv("WEATHER_API_KEY")
    when = when.lower().strip()

    current_aliases = ["now", "today", "сейчас", "сегодня"]
    forecast_map = {
        "tomorrow": 1,
        "завтра": 1,
        "in 2 days": 2,
        "через 2 дня": 2,
        "in 3 days": 3,
        "через 3 дня": 3
    }

    if when in current_aliases:
        url = f"http://api.weatherapi.com/v1/current.json?key={api_key}&q={location}&aqi=no"
        try:
            response = requests.get(url)
            data = response.json()
            if response.status_code != 200 or "current" not in data:
                return f"Sorry, I couldn't get the current weather for {location}."
            temp = data["current"]["temp_c"]
            description = data["current"]["condition"]["text"]
            return f"The current weather in {location} is {description.lower()} with {temp}°C."
        except Exception as e:
            return f"Error getting current weather: {e}"

    elif when in forecast_map:
        days = forecast_map[when]
        url = f"http://api.weatherapi.com/v1/forecast.json?key={api_key}&q={location}&days={days}&aqi=no&alerts=no"
        try:
            response = requests.get(url)
            data = response.json()
            if response.status_code != 200 or "forecast" not in data:
                return f"Sorry, I couldn't get the weather forecast for {location}."

            target_day = 0 if days == 1 else days - 1
            forecast_day = data["forecast"]["forecastday"][target_day]
            date = forecast_day["date"]
            condition = forecast_day["day"]["condition"]["text"]
            avg_temp = forecast_day["day"]["avgtemp_c"]
            return f"Weather forecast for {location} on {date}: {condition.lower()}, avg temperature {avg_temp}°C."
        except Exception as e:
            return f"Error getting forecast weather: {e}"

    else:
        return f"Sorry, I can only provide weather for today, tomorrow, or up to 3 days ahead. Try using phrases like 'tomorrow' or 'in 2 days'."

weather_tool = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Get current weather for a location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The place to get weather for (e.g. Prague, Alps)"
                },
                "when": {
                    "type": "string",
                    "description": "Time of the weather (e.g. now, today, tomorrow, in 3 days)",
                    "default": "now"
                }
            },
            "required": ["location"]
        }
    }
}

tools = [weather_tool]

def chat(message, history):
    messages = [{"role": "system", "content": system_message}] + history + [{"role": "user", "content": message}]
    response = openai.chat.completions.create(model=MODEL, messages=messages,  tools=tools)

    if response.choices[0].finish_reason == "tool_calls":
        message = response.choices[0].message
        response, city = handle_tool_call(message)
        messages.append(message)
        messages.append(response)
        response = openai.chat.completions.create(model=MODEL, messages=messages)


    return response.choices[0].message.content


def handle_tool_call(message):
    tool_call = message.tool_calls[0]
    arguments = json.loads(tool_call.function.arguments)
    city = arguments.get("location")
    when = arguments.get("when", "now")
    weather = get_weather(city, when)
    response = {
        "role": "tool",
        "content": json.dumps({"location": city, "weather": weather}),
        "tool_call_id": tool_call.id
    }
    return response, city

gr.ChatInterface(fn=chat, type="messages", js=force_dark_mode).launch()