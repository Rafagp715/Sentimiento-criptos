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
    # PROMPT ACTUALIZADO: Ahora pedimos tendencia y razón
    prompt = f"""
Eres un analista financiero experto en criptomonedas. Analiza la siguiente noticia.
1. Extrae los SÍMBOLOS o NOMBRES de las criptomonedas que se mencionan explícitamente.
2. Determina la relevancia de la noticia (ALTA, MEDIA, BAJA).
3. Determina si la noticia hará que el precio SUB A (ALCISTA), BAJE (BAJISTA) o se mantenga igual (NEUTRAL).
4. Da una razón muy breve (máximo 10 palabras) de tu decisión.

Responde ÚNICAMENTE con un objeto JSON válido con esta estructura exacta:
{{"monedas": ["BTC", "ETH"], "relevancia": "ALTA", "tendencia": "ALCISTA", "razon": "Aprobación de ETF al contado"}}

Si no se menciona ninguna moneda concreta, devuelve "monedas": [].

Noticia: {titular}
Resumen: {resumen}
"""
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            timeout=30,
        )
        
        respuesta = completion.choices[0].message.content.strip()
        
        # Limpiamos el formato Markdown que a veces añade la IA
        if respuesta.startswith("```json"):
            respuesta = respuesta[7:-3]
        elif respuesta.startswith("```"):
            respuesta = respuesta[3:-3]
        
        datos = json.loads(respuesta)
        return (
            datos.get("monedas", []), 
            datos.get("relevancia", "BAJA").upper(),
            datos.get("tendencia", "NEUTRAL").upper(),
            datos.get("razon", "")
        )
    
    except Exception as e:
        print(f"Error con Groq/JSON: {e}")
        return [], "BAJA", "NEUTRAL", ""

def main():
    feed = feedparser.parse("https://www.coindesk.com/arc/outboundfeeds/rss/")
    
    for entry in feed.entries[:5]:
        titular = entry.title
        resumen = entry.get("summary", "")[:300]
        
        # Ahora recibimos 4 variables
        monedas_detectadas, relevancia, tendencia, razon = analizar_con_groq(titular, resumen)
        
        # --- FILTRO DE REVOLUT X ---
        monedas_validas = []
        for moneda in monedas_detectadas:
            moneda_upper = moneda.upper().strip()
            if moneda_upper in MONEDAS_REVOLUT_X:
                monedas_validas.append(moneda_upper)
            else:
                for simbolo, nombre in MONEDAS_REVOLUT_X.items():
                    if moneda_upper == nombre:
                        monedas_validas.append(simbolo)
                        break
        
        if relevancia in ["ALTA", "MEDIA"] and monedas_validas:
            monedas_str = ", ".join(set(monedas_validas))
            
            # Añadimos iconos visuales según la tendencia para que sea muy fácil de leer en Telegram
            icono = "⚖️"
            if tendencia == "ALCISTA":
                icono = "📈"
            elif tendencia == "BAJISTA":
                icono = "📉"

            mensaje = (
                f"{icono} <b>Tendencia: {tendencia}</b> ({relevancia})\n"
                f"🪙 <b>Monedas:</b> {monedas_str}\n"
                f"💡 <b>Motivo:</b> {razon}\n\n"
                f"📰 {titular}\n\n"
                f"🔗 {entry.link}"
            )
            
            enviar_telegram(mensaje)
            print(f"Alerta enviada ({relevancia} / {tendencia}) - Monedas: {monedas_str} - {titular}")
        else:
            print(f"Descartada ({relevancia}) - Tendencia: {tendencia} - IA detectó: {monedas_detectadas} - {titular}")

if __name__ == "__main__":
    main()
