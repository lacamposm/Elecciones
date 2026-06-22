import os
import sys
import json
import requests
import argparse
import csv
from datetime import datetime as dt

# Añadir la raíz del proyecto al path de búsqueda de módulos para importar de src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils import load_departments, select_region_interactively, download_file

parser = argparse.ArgumentParser(description="Descargar formularios E-14 de Colombia.")
parser.add_argument("--dep", type=str, help="Código de departamento (2 dígitos, ej. 01)")
parser.add_argument("--mun", type=str, help="Código de municipio (3 dígitos, ej. 280)")
parser.add_argument("--redownload", action="store_true", help="Forzar la descarga de la base de datos de códigos")
args = parser.parse_args()

if args.dep and args.mun:
    dep = args.dep.zfill(2)
    mun = args.mun.zfill(3)
    print(f"Usando argumentos CLI - Departamento: {dep}, Municipio: {mun}")
else:
    deps = load_departments()
    dep, mun = select_region_interactively(deps)
# La autenticación de AWS Cognito fue removida ya que las descargas de PDFs se realizan de forma pública/anónima.

## DESCARGAR JSON DE CODIGOS
codes_path = os.path.join("data", "allTransmissionCodes.json")

def download_transmcodes():
    txcodesurl="https://e14segundavueltapresidente.registraduria.gov.co/assets/temis/divipol_json/allTransmissionCodes.json"
    # txcodesurl="https://divulgacione14presidente.registraduria.gov.co/assets/temis/divipol_json/allTransmissionCodes.json"
    codes_headers={
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "authority": "e14segundavueltapresidente.registraduria.gov.co",
        "accept-encoding": "gzip, deflate, br, zstd",
        "get":"GET",
        "Referer":f"https://e14segundavueltapresidente.registraduria.gov.co/departamento/{dep if dep is not None else '01'}",        
        # "Referer":f"https://divulgacione14presidente.registraduria.gov.co/departamento/{dep}",        
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "none",
    }
    r = requests.get(txcodesurl, headers=codes_headers, timeout=60, allow_redirects=True)
    r.raise_for_status()
    if "json" not in r.headers.get("content-type", "").lower():
            raise RuntimeError(f"No devolvió JSON: {r.headers.get('content-type')}")
    os.makedirs("data", exist_ok=True)
    with open(codes_path, "wb") as f:
        f.write(r.content)

if not os.path.exists(codes_path) or args.redownload:
    print("Descargando base de datos de códigos (allTransmissionCodes.json)...")
    download_transmcodes()
    print("Se descargó la lista de códigos con éxito.")
else:
    print("Usando base de datos de códigos local (allTransmissionCodes.json).")


## PARSE JSON DE CODIGOS 
with open(codes_path, encoding="utf-8") as f:
    data = json.load(f)["data"]

def iter_nodes(obj):
    for status in obj.values():
        nodes = status.get("nodes", [])

        for chunk in nodes:
            if isinstance(chunk, dict):
                yield chunk

            elif isinstance(chunk, list):
                yield from chunk

def filtrar(obj, dep, mun):
    for node in iter_nodes(obj):

        if (
            node.get("idDepartmentCode") == dep
            and (mun is None or node.get("municipalityCode") == mun)
        ):
            yield {
                "dep": node.get("idDepartmentCode"),
                "mun": node.get("municipalityCode").zfill(3),
                "zona": node.get("idZoneCode").zfill(3),
                "puesto": node.get("standCode"),
                "mesa": node.get("numberStand"),
                "expected_name": node.get("expectedName"),
            }

resultados=list(filtrar(data, dep, mun))
print(f"{len(resultados)} actas encontradas.")

### DESCARGAR PDFS
def build_pdf_url(dep, mun, zona, puesto, mesa, corp_text, expected_name):
    return (
        "https://e14segundavueltapresidente.registraduria.gov.co"
        f"/assets/temis/pdf/{dep}/{mun}/{zona}/{puesto}/{mesa}/{corp_text}/{expected_name}"
    )

def download_pdf(url, path):
    headers={
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "authority": "e14segundavueltapresidente.registraduria.gov.co",
        "get":"GET",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "en-GB,en;q=0.9,en-US;q=0.8,es;q=0.7,zh-CN;q=0.6,zh;q=0.5,es-MX;q=0.4",
        "cache-control": "max-age=0"
    }
    r = requests.get(url, headers=headers, timeout=60, allow_redirects=True)
    r.raise_for_status()
    if "pdf" not in r.headers.get("content-type", "").lower():
        raise RuntimeError(f"No devolvió PDF: {r.headers.get('content-type')}")
    with open(path, "wb") as f:
        f.write(r.content)

# Crear subcarpeta para departamento y municipio encadenados (ej. pdf/01280)
folder_name = f"{dep}{mun}"
folder_path = os.path.join("pdf", folder_name)
os.makedirs(folder_path, exist_ok=True)

# Guardar la lista de actas en un archivo CSV local para auditoría
csv_path = os.path.join(folder_path, "actas_mapeo.csv")
try:
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["dep", "mun", "zona", "puesto", "mesa", "expected_name"])
        writer.writeheader()
        writer.writerows(resultados)
    print(f"Se guardó la lista de códigos en formato CSV en: {csv_path}")
except Exception as e:
    print(f"Advertencia: No se pudo guardar la lista en CSV: {e}")

print(f"Los archivos se guardarán en la carpeta: {folder_path}")

for el in resultados:
    dep=el["dep"]
    mun=el["mun"]
    zona=el["zona"]
    puesto=el["puesto"]
    mesa=el["mesa"]
    pdfname=el["expected_name"]
    corp="PRE"

    # Nombre de archivo sin timestamp T{hora} para mantener consistencia e idempotencia
    filename=f"Dep{dep}-Mun{mun}-Zona{zona}-Puesto{puesto}-Mesa{mesa}_{pdfname}"
    if not filename.endswith(".pdf"):
        filename += ".pdf"
    
    filepath = os.path.join(folder_path, filename)
    
    # Idempotencia: Verificar si ya existe el archivo
    if os.path.exists(filepath):
        print(f"Saltando: Mun {mun} - Zona {zona} - Puesto {puesto} - Mesa {mesa} (Ya existe)")
        continue

    print(f"Descargando: Mun {mun} - Zona {zona} - Puesto {puesto} - Mesa {mesa}")
    try:
        download_pdf(build_pdf_url(dep,mun,zona,puesto,mesa,corp,pdfname), filepath)
    except Exception as e:
        print(f"Error al descargar Mun {mun} - Zona {zona} - Puesto {puesto} - Mesa {mesa}: {e}")

print("====FINALIZADO====")