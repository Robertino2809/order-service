import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai import errors

import json

load_dotenv()

client = genai.Client(http_options=types.HttpOptions(timeout=20000))

app = FastAPI()

with open("jelovnik.json", "r", encoding="utf-8") as f:
    menu = json.load(f)

valid_ids = {item["id"] for item in menu}

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
- Ako gost samo pita o jelovniku ili traži preporuku, a ništa ne naručuje, ne dodaj ništa u "items" ni u "unavailable". Brojevi koji opisuju goste ("za nas dvoje") nisu količina nijedne stavke.
- Ako gost pita za jela bez mesa, postavi "wants_meatless_suggestions" na true, inače na false.
- Ako se gost predomisli usred rečenice, vrijedi zadnja verzija.

Odgovori isključivo JSON-om ovog oblika, bez dodatnog teksta:
{{"items": [{{"id": "...", "quantity": 1}}], "unavailable": [{{"text": "...", "quantity": 1}}], "wants_meatless_suggestions": false}}
"""


class OrderRequest(BaseModel):
    text: str

    @field_validator("text")
    @classmethod
    def text_not_blank(cls, v):
        v = v.strip()
        if len(v) > 500:
            raise ValueError("text je predugačak (najviše 500 znakova)")
        if not v:
            raise ValueError("text ne smije biti prazan")
        return v


def is_valid_quantity(qty):
    return isinstance(qty, int) and not isinstance(qty, bool) and qty >= 1


@app.post("/order")
def order(req: OrderRequest):
    try:
        resp = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=req.text,
            config=types.GenerateContentConfig(system_instruction=system_prompt),
        )
    except (errors.APIError, httpx.HTTPError):
        raise HTTPException(
            status_code=502,
            detail="Usluga prepoznavanja narudžbe trenutno nije dostupna.",
        )

    try:
        data = json.loads(resp.text)
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=502, detail="Model nije vratio valjan odgovor")

    if not isinstance(data, dict):
        raise HTTPException(status_code=502, detail="Model nije vratio valjan odgovor")

    items = data.get("items", [])
    unavailable = data.get("unavailable", [])

    if not isinstance(items, list) or not isinstance(unavailable, list):
        raise HTTPException(status_code=502, detail="Model nije vratio valjan odgovor")

    clean_unavailable = []
    for u in unavailable:
        if not isinstance(u, dict):
            raise HTTPException(
                status_code=502, detail="Model je vratio neispravnu stavku"
            )
        text = u.get("text")
        qty = u.get("quantity")
        if not isinstance(text, str) or not text.strip():
            raise HTTPException(
                status_code=502, detail="Model je vratio neispravnu stavku"
            )
        if not is_valid_quantity(qty):
            raise HTTPException(
                status_code=502, detail="Model je vratio neispravnu količinu"
            )
        clean_unavailable.append({"text": text, "quantity": qty})
    unavailable = clean_unavailable

    wants_meatless = data.get("wants_meatless_suggestions") is True

    suggestions = []
    if wants_meatless:
        suggestions = [
            i["id"]
            for i in menu
            if i["bez_mesa"] and i["kategorija"] in ("pizza", "salata")
        ]

    valid_items = []
    for x in items:
        if not isinstance(x, dict):
            raise HTTPException(
                status_code=502, detail="Model je vratio neispravnu stavku"
            )
        item_id = x.get("id")
        qty = x.get("quantity")
        if not isinstance(item_id, str):
            raise HTTPException(
                status_code=502, detail="Model je vratio neispravnu stavku"
            )
        if not is_valid_quantity(qty):
            raise HTTPException(
                status_code=502, detail="Model je vratio neispravnu količinu"
            )

        if item_id in valid_ids:
            valid_items.append({"id": item_id, "quantity": qty})
        else:
            unavailable.append({"text": item_id, "quantity": qty})

    return {
        "items": valid_items,
        "unavailable": unavailable,
        "suggestions": suggestions,
    }
