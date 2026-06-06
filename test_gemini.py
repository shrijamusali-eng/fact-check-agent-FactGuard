from dotenv import load_dotenv
import google.generativeai as genai
import os

load_dotenv()

print(os.getenv("GEMINI_API_KEY"))

genai.configure(
    api_key=os.getenv("GEMINI_API_KEY")
)

model = genai.GenerativeModel("gemini-2.5-flash")

response = model.generate_content(
    "Say hello"
)

print(response.text)