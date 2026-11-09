import feedparser
import requests
import os
from openai import OpenAI

# --- CONFIGURACIÓN ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
MONEDA_OBJETIVO = "Bitcoin" 

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_API_KEY,
)

def enviar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error enviando a Telegram: {e}")

def analizar_con_groq(titular, resumen):
    prompt = f"""
Eres un analista de criptomonedas. Analiza la siguiente noticia y determina si es RELEVANTE para el precio de {MONEDA_OBJETIVO} a corto plazo (subida o bajada).
Responde SOLO con una de estas tres palabras: ALTA, MEDIA, BAJA.

Noticia: {titular}
Resumen: {resumen}
"""
    try:
        completion = client.chat.completions.create(
            timeout=30,
            # Aquí está el modelo actualizado que reemplaza al antiguo
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        return completion.choices[0].message.content.strip().upper()
    except Exception as e:
        print(f"Error con Groq: {e}")
        return "BAJA"

def main():
    # Leer RSS de CoinDesk
    feed = feedparser.parse("https://www.coindesk.com/arc/outboundfeeds/rss/")
    
    # Procesar solo las últimas 5 noticias
    for entry in feed.entries[:5]:
        titular = entry.title
        resumen = entry.get("summary", "")[:300]
        
        relevancia = analizar_con_groq(titular, resumen)
        
        # Comprobamos si la respuesta contiene "ALTA"
        if "ALTA" in relevancia:
            mensaje = f"🚨 Noticia relevante para {MONEDA_OBJETIVO}:\n\n{titular}\n\n{entry.link}"
            enviar_telegram(mensaje)
            print(f"Alerta enviada: {titular}")
        else:
            print(f"Noticia descartada ({relevancia}): {titular}")

if __name__ == "__main__":
    main()
    
