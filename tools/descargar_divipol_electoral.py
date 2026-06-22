import requests
import json
import os

# Lista de posibles URLs para obtener la DIVIPOL electoral con nombres legibles
urls_to_try = [
    # Dominio de Segunda Vuelta (Temis divipol_json)
    "https://e14segundavueltapresidente.registraduria.gov.co/assets/temis/divipol_json/divipol.json",
    "https://e14segundavueltapresidente.registraduria.gov.co/assets/temis/divipol_json/departamentos.json",
    "https://e14segundavueltapresidente.registraduria.gov.co/assets/temis/divipol_json/municipios.json",
    "https://e14segundavueltapresidente.registraduria.gov.co/assets/divipol.json",
    "https://e14segundavueltapresidente.registraduria.gov.co/assets/i18n/es.json",
    
    # Dominio de Divulgación General / Primera Vuelta (Temis divipol_json)
    "https://divulgacione14presidente.registraduria.gov.co/assets/temis/divipol_json/divipol.json",
    "https://divulgacione14presidente.registraduria.gov.co/assets/temis/divipol_json/departamentos.json",
    "https://divulgacione14presidente.registraduria.gov.co/assets/temis/divipol_json/municipios.json",
    "https://divulgacione14presidente.registraduria.gov.co/assets/divipol.json",
    "https://divulgacione14presidente.registraduria.gov.co/assets/i18n/es.json"
]

headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
    "accept": "application/json, text/plain, */*"
}

found = False

print("=== Buscando archivo de DIVIPOL Electoral en los servidores de la Registraduría ===")
print("Este proceso se ejecuta desde tu máquina local para evitar el geobloqueo de red.\n")

for url in urls_to_try:
    print(f"Probando: {url} ...")
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            content_type = r.headers.get("content-type", "").lower()
            if "json" in content_type or url.endswith(".json"):
                # Intentar parsear como JSON
                try:
                    data = r.json()
                    filename = url.split("/")[-1]
                    # Guardar con un nombre distintivo según el dominio
                    if "e14segundavueltapresidente" in url:
                        filename = "segunda_vuelta_" + filename
                    else:
                        filename = "divulgacion_" + filename
                        
                    with open(filename, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=4, ensure_ascii=False)
                        
                    print(f"\n[+] ¡ÉXITO! Se descargó y guardó: {filename}")
                    print(f"    URL origen: {url}")
                    
                    # Mostrar una pequeña muestra del contenido
                    if isinstance(data, dict):
                        print("    Estructura (llaves principales):", list(data.keys())[:10])
                    elif isinstance(data, list):
                        print(f"    Estructura (lista de {len(data)} elementos). Ejemplo del primero:")
                        print(data[0])
                    
                    found = True
                except Exception as je:
                    print(f"    [-] Respondio 200 pero no parece un JSON valido: {je}")
        else:
            print(f"    [-] Código de estado: {r.status_code}")
    except Exception as e:
        print(f"    [-] Error de conexión: {e}")
    print("-" * 50)

if not found:
    print("\n[-] No se pudo descargar automáticamente ningún JSON de Divipol desde las URLs habituales.")
    print("Sugerencia manual:")
    print("1. Abre en tu navegador de preferencia: https://divulgacione14presidente.registraduria.gov.co/home")
    print("2. Abre las Herramientas de Desarrollador (F12) e ingresa a la pestaña 'Red' (Network).")
    print("3. Recarga la página y filtra por 'Fetch/XHR' o escribe '.json' en el buscador.")
    print("4. Busca algún archivo .json que se descargue (como 'divipol.json', 'es.json', etc.) y dinos su nombre o guárdalo en esta carpeta.")
else:
    print("\n=== Búsqueda finalizada. Revisa los archivos JSON guardados ===")
