# Servis koji razumije narudžbu

FastAPI servis s jednim endpointom `POST /order`. Iz rečenice gosta (npr. "dvije margarite i jednu colu") izvlači stavke i količine s jelovnika pomoću Gemini modela.

## Pokretanje

Potreban je Python 3 i besplatni API ključ iz Google AI Studija.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Ključ se čita iz varijable okruženja `GEMINI_API_KEY`, nikad iz koda. Napravi datoteku `.env` u korijenu projekta (nalazi se u `.gitignore`, pa ne ulazi u repozitorij):

```
GEMINI_API_KEY=tvoj-kljuc
```

Pokretanje servisa:

```bash
uvicorn main:app --reload
```

Swagger sučelje: http://127.0.0.1:8000/docs

Primjer zahtjeva:

```bash
curl -X POST http://127.0.0.1:8000/order \
  -H 'Content-Type: application/json' \
  -d '{"text": "dva hamburgera i jednu margaritu"}'
```

Testovi (model je lažiran, ne trebaju ključ ni internet): `pytest`

Model je u `main.py` postavljen na `gemini-3.5-flash`. Besplatni modeli se povremeno povlače za nove korisnike (`gemini-2.5-flash` mi je bio nedostupan), pa se naziv mijenja na jednom mjestu.

## Format odgovora

```json
{
  "items": [{"id": "margarita", "quantity": 1}],
  "unavailable": [{"text": "hamburger", "quantity": 2}],
  "suggestions": []
}
```

Polje `suggestions` je moj dodatak formatu iz zadatka. Za pitanje poput "imate li nešto bez mesa?" `items` ostaje prazan, a `suggestions` sadrži jela bez mesa. Model samo prepozna da gost to pita, a popis gradi kod iz `jelovnik.json` (pizze i salate označene kao `bez_mesa`), pa ga model ne može izmisliti i uvijek prati stvarni jelovnik.

## Odluke

- **Id koji nije na jelovniku ide u `unavailable`.** Gost ne smije ostati bez stavke, a model ne smije sam zamijeniti nešto sličnim. Prompt to traži, a kod to jamči: ako model u `items` stavi nepoznat id, kod ga prebaci u `unavailable`.
- **Neispravan izlaz modela daje 502.** Greška nije na strani gosta nego u odgovoru modela (nevaljan JSON, krivi oblik, količina koja nije cijeli broj veći od 0). Vratiti 200 s pogrešnom narudžbom bilo bi gore od greške.
- **Prazan ili predugačak ulaz daje 422.** Greška je u zahtjevu klijenta, pa se model uopće ne zove i ne troši se poziv.
- **Nedostupan Gemini daje 502.** Pokriveni su greška API-ja, timeout (20 s) i pad mreže. Biblioteka dodatno sama ponavlja neuspjele pozive, pa ukupno čekanje može biti dulje od 20 s.
- **Ako količina nije rečena, uzima se 1.** To je najrazumnija pretpostavka za narudžbu poput "jednu cola" ili "margarita".
- **Predomišljanje** ("tri margarite i colu, ma ne, ipak dvije margarite") rješava pravilo u promptu da vrijedi zadnja verzija.

## Što bi se dalo poboljšati i kako provjeriti da sustav radi

Najveći rizik je da model tiho pogriješi a odgovor izgleda ispravno (rečenicu o jelima bez mesa prvotno je proglasio nedostupnom stavkom, uz status 200), pa bih napravio skup stvarnih rečenica s očekivanim rezultatima i pokretao ga protiv pravog modela više puta, jer je model nedeterminističan, te u produkciji pratio udio odgovora s unavailable. Umjesto da JSON samo tražim u promptu, koristio bih Geminijev strukturirani izlaz (response_mime_type i shema odgovora), čime bi se uklonile greške poput JSON-a omotanog u blok koda.

Za stavke u `unavailable` servis sada samo javlja da ih nema, pa gost ostaje bez alternative; poboljšanje je da kod (a ne model, da ne izmišlja) uz svaku takvu stavku vrati popis jela iz iste kategorije koja jesu na jelovniku, bez da ih sam dodaje u narudžbu.