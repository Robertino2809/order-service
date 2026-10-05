import json
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client()

with open('jelovnik.json', 'r', encoding='utf-8') as f:
    menu = json.load(f)

menu_lines = []
for item in menu:
    menu_lines.append(f"- {item['id']}: {item['naziv']} ({item['kategorija']})")
menu_text = "\n".join(menu_lines)

system_prompt = f"""
Ti si asistent restorana. Gost ti kaže narudžbu jednom rečenicom, a ti iz nje izvučeš što je naručio.

Jelovnik (koristi samo ove id-eve):
{menu_text}

Pravila:
- Ako gost naruči nešto što je na jelovniku, dodaj ga u 'items' s točnim id-em s jelovnika i količinom koju je gost rekao.
- Ako gost naruči nešto čega nema na jelovniku, upiši to u "unavailable" s tekstom koji je gost rekao i količinom. Svaku takvu stavku zapiši, nijednu ne preskoči.
- Nikad nemoj zamijeniti stavku koje nema na jelovniku nekom drugom, čak i ako je slična. Primjer: ako gost traži hamburger, ne dodaj pizzu u "items".
- Ako količina nije rečena, uzmi da je količina 1.

Odgovori isključivo JSON-om ovog oblika, bez dodatnog teksta:
{{"items": [{{"id": "...", "quantity": 1}}], "unavailable": [{{"text": "...", "quantity": 1}}]}}
"""

resp = client.models.generate_content(
    model="gemini-3.5-flash",
    contents="dva hamburgera i jednu margaritu",
    config=types.GenerateContentConfig(system_instruction=system_prompt),
)
print(resp.text)

try:  
  data = json.loads(resp.text)
except json.JSONDecodeError:
   print("Model nije vratio valjan JSON")
   exit()


valid_ids = {item["id"] for item in menu}

for x in data["items"]:
    print(x["id"], x["id"] in valid_ids)