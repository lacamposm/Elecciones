import requests
import json

base_url = "https://divulgacione14presidente.registraduria.gov.co/assets/temis/divipol_json/"

files = ["allDepartments.json", "departmentsTree.json"]
headers = {
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
}

for file in files:
    url = base_url + file
    print(f"Descargando {file} desde {url}...")
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            with open(file, "w", encoding="utf-8") as f:
                json.dump(r.json(), f, indent=4, ensure_ascii=False)
            print(f"[+] ¡Descargado con éxito! Guardado como: {file}")
        else:
            print(f"[-] Error: código de estado {r.status_code}")
    except Exception as e:
        print(f"[-] Error de conexión al descargar {file}: {e}")
