from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client()

models = ["gemini-2.5-flash-lite", "gemini-3.5-flash", "gemini-3.1-flash-lite"]

for m in models:
  try:
    resp = client.models.generate_content(
      model = m,
      contents = "Reci bok na hrvatskom",
    )
    print("OK ", m, "->", resp.text[:60])
  except Exception as e:
    print("FAIL", m, "->", e)