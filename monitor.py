import feedparser
import requests
import os
import json
from openai import OpenAI

# --- CONFIGURACIÓN ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Diccionario de monedas en Revolut X (Símbolo: Nombre completo)
# Esto ayuda a que el filtro no falle si la IA lee "Bitcoin" en vez de "BTC"
MONEDAS_REVOLUT_X = {
    "BTC": "BITCOIN", "ETH": "ETHEREUM", "SOL": "SOLANA", "XRP": "RIPPLE", 
    "ADA": "CARDANO", "DOT": "POLKADOT", "AVAX": "AVALANCHE", "LINK": "CHAINLINK", 
    "MATIC": "POLYGON", "POL": "POLYGON", "LTC": "LITECOIN", "BCH": "BITCOIN CASH", 
    "XLM": "STELLAR", "ALGO": "ALGORAND", "XTZ": "TEZOS", "ATOM": "COSMOS", 
    "UNI": "UNISWAP", "AAVE": "AAVE", "FIL": "FILECOIN", "APT": "APTOS", 
    "ARB": "ARBITRUM", "OP": "OPTIMISM", "SUI": "SUI", "NEAR": "NEAR PROTOCOL", 
    "INJ": "INJECTIVE", "TIA": "CELESTIA", "SEI": "SEI", "PEPE": "PEPE", 
    "SHIB": "SHIBA INU", "DOGE": "DOGECOIN"
}

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
    # El prompt pide a la IA que devuelva un JSON estricto
    prompt = f"""
Eres un analista de criptomonedas experto. Analiza la siguiente noticia.
1. Extrae los SÍMBOLOS o NOMBRES de las criptomonedas que se mencionan explícitamente (ej: BTC, ETH, Solana).
2. Determina la relevancia de la noticia para el precio de esas monedas (ALTA, MEDIA, BAJA).

Responde ÚNICAMENTE con un objeto JSON válido con esta estructura:
{{"monedas": ["BTC", "ETH"], "relevancia": "ALTA"}}

Si no se menciona ninguna moneda concreta, devuelve "monedas": [].

Noticia: {titular}
Resumen: {resumen}
"""
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            timeout=30, # Si la IA tarda más de 30s, se cancela para no bloquear
        )
        
        respuesta = completion.choices[0].message.content.strip()
        
        # Limpiamos el formato Markdown que a veces añade la IA (```json ... ```)
        if respuesta.startswith("```json"):
            respuesta = respuesta[7:-3]
        elif respuesta.startswith("```"):
            respuesta = respuesta[3:-3]
        
        datos = json.loads(respuesta)
        return datos.get("monedas", []), datos.get("relevancia", "BAJA").upper()
    
    except Exception as e:
        print(f"Error con Groq/JSON: {e}")
        return [], "BAJA"

def main():
    # Leer RSS de CoinDesk
    feed = feedparser.parse("https://www.coindesk.com/arc/outboundfeeds/rss/")
    
    # Procesar solo las últimas 5 noticias
    for entry in feed.entries[:5]:
        titular = entry.title
        resumen = entry.get("summary", "")[:300]
        
        monedas_detectadas, relevancia = analizar_con_groq(titular, resumen)
        
        # --- FILTRO DE REVOLUT X ---
        monedas_validas = []
        for moneda in monedas_detectadas:
            moneda_upper = moneda.upper().strip()
            
            # Comprobamos si la IA devolvió el símbolo (ej. "BTC") o el nombre completo (ej. "BITCOIN")
            if moneda_upper in MONEDAS_REVOLUT_X:
                monedas_validas.append(moneda_upper)
            else:
                # Si no está el símbolo, buscamos si coincide con algún nombre completo de nuestro diccionario
                for simbolo, nombre in MONEDAS_REVOLUT_X.items():
                    if moneda_upper == nombre:
                        monedas_validas.append(simbolo)
                        break
        
        # Si la relevancia es ALTA o MEDIA, y hay monedas que cotizan en Revolut X, avisamos
        if relevancia in ["ALTA", "MEDIA"] and monedas_validas:
            # set() elimina duplicados si por ejemplo la IA detectó "BTC" y "Bitcoin" en la misma noticia
            monedas_str = ", ".join(set(monedas_validas)) 
            mensaje = f"🚨 Noticia {relevancia} para: {monedas_str}\n\n{titular}\n\n{entry.link}"
            enviar_telegram(mensaje)
            print(f"Alerta enviada ({relevancia}) - Monedas Revolut X: {monedas_str} - {titular}")
        else:
            # Log para revisar qué está pasando internamente
            print(f"Descartada ({relevancia}) - IA detectó: {monedas_detectadas} - {titular}")

if __name__ == "__main__":
    main()
