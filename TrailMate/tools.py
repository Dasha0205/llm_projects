import os
import requests
import openai

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

image_tool = {
    "type": "function",
    "function": {
        "name": "generate_image",
        "description": "Generate an image based on a prompt",
        "parameters": {
            "type": "object",
            "properties": {
                "prompt":{
                    "type": "string",
                    "description": "Description of the image to generate",
                }
            },
            "required": ["prompt"]
        }
    }
}


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

def generate_image(prompt: str) -> str:

    response = openai.images.generate(model = "dall-e-3",
                                          prompt = prompt,
                                          size = "1024x1024",
                                          n=1,
                                          response_format="b64_json")
    image_base64 = response.data[0].b64_json
    # Return as base64 image URL
    return f"data:image/png;base64,{image_base64}"
