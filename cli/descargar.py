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
parser.add_argument("--all", action="store_true", help="Descargar todos los departamentos y municipios de Colombia")
parser.add_argument("--no-capitals", action="store_true", help="Descargar solo municipios no capitales (ignorar código '001')")
parser.add_argument("--only-capitals", action="store_true", help="Descargar solo municipios capitales (código '001')")
parser.add_argument("--redownload", action="store_true", help="Forzar la descarga de la base de datos de códigos")
args = parser.parse_args()

dep = None
mun = None

if args.all:
    print("Modo CLI - Descargando todos los departamentos y municipios de Colombia")
elif args.dep:
    dep = args.dep.zfill(2)
    if args.mun:
        mun = args.mun.zfill(3)
        print(f"Modo CLI - Departamento: {dep}, Municipio: {mun}")
    else:
        print(f"Modo CLI - Descargando todo el Departamento: {dep}")
else:
    deps = load_departments()
    dep, mun = select_region_interactively(deps)

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

def filtrar(obj, dep=None, mun=None, no_capitals=False, only_capitals=False):
    for node in iter_nodes(obj):
        dep_node = node.get("idDepartmentCode")
        mun_node = node.get("municipalityCode")
        
        # Ignorar Consulados (departamento 88)
        if dep_node == "88":
            continue
            
        # Si se filtró por departamento específico
        if dep is not None and dep_node != dep:
            continue
            
        # Si se filtró por municipio específico
        if mun is not None and mun_node != mun:
            continue
            
        # Si no queremos capitales, omitimos el código '001'
        if no_capitals and mun_node == "001":
            continue
            
        # Si queremos solo capitales, omitimos los que no tengan el código '001'
        if only_capitals and mun_node != "001":
            continue
            
        yield {
            "dep": dep_node,
            "mun": mun_node.zfill(3),
            "zona": node.get("idZoneCode").zfill(3),
            "puesto": node.get("standCode"),
            "mesa": node.get("numberStand"),
            "expected_name": node.get("expectedName"),
        }

resultados = list(filtrar(data, dep, mun, args.no_capitals, args.only_capitals))
print(f"Total general de actas encontradas para descargar: {len(resultados)}")

# Agrupar por (departamento, municipio) para procesar ordenadamente
from collections import defaultdict
actas_por_municipio = defaultdict(list)
for el in resultados:
    actas_por_municipio[(el["dep"], el["mun"])].append(el)

municipios_a_procesar = sorted(actas_por_municipio.keys())
total_municipios = len(municipios_a_procesar)
print(f"Se procesarán {total_municipios} municipios.")

# Importar helper para nombres de regiones
from src.utils import get_region_names

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

# Procesar cada municipio secuencialmente
for m_idx, (dep_c, mun_c) in enumerate(municipios_a_procesar):
    m_list = actas_por_municipio[(dep_c, mun_c)]
    dep_name, mun_name = get_region_names(dep_c, mun_c)
    region_label = f"{dep_name} - {mun_name}" if dep_name else f"Dep {dep_c} - Mun {mun_c}"
    
    print(f"\n======================================================================")
    print(f" [Municipio {m_idx + 1}/{total_municipios}] {region_label} ({len(m_list)} actas)")
    print(f"======================================================================")
    
    folder_name = f"{dep_c}{mun_c}"
    folder_path = os.path.join("pdf", folder_name)
    os.makedirs(folder_path, exist_ok=True)
    
    # Escribir actas_mapeo.csv para este municipio
    csv_path = os.path.join(folder_path, "actas_mapeo.csv")
    try:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["dep", "mun", "zona", "puesto", "mesa", "expected_name"])
            writer.writeheader()
            writer.writerows(m_list)
    except Exception as e:
        print(f"  Advertencia: No se pudo guardar actas_mapeo.csv: {e}")
        
    for idx, el in enumerate(m_list):
        zona = el["zona"]
        puesto = el["puesto"]
        mesa = el["mesa"]
        pdfname = el["expected_name"]
        corp = "PRE"
        
        filename = f"Dep{dep_c}-Mun{mun_c}-Zona{zona}-Puesto{puesto}-Mesa{mesa}_{pdfname}"
        if not filename.endswith(".pdf"):
            filename += ".pdf"
            
        filepath = os.path.join(folder_path, filename)
        
        if os.path.exists(filepath):
            # Imprimir solo reporte resumido cada 10 archivos existentes para no inundar el log en descargas masivas
            if idx % 10 == 0 or idx == len(m_list) - 1:
                print(f"  [{idx + 1}/{len(m_list)}] Saltando: Mesa {mesa} y anteriores (Ya existe)")
            continue
            
        print(f"  [{idx + 1}/{len(m_list)}] Descargando: Mesa {mesa} ...")
        try:
            url = build_pdf_url(dep_c, mun_c, zona, puesto, mesa, corp, pdfname)
            download_pdf(url, filepath)
        except Exception as e:
            print(f"    [-] Error al descargar Mesa {mesa}: {e}")

print("\n==== PROCESO DE DESCARGA FINALIZADO ====")