import os
import json
import math
import subprocess
import sys
import re
import argparse

# Añadir la raíz del proyecto al path de búsqueda de módulos para importar de src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils import get_region_names

lote_size = 45

def check_nlm_auth():
    try:
        # Ejecuta un comando sencillo sin confirmación para validar autenticación
        res = subprocess.run(["nlm", "notebook", "list"], capture_output=True, text=True)
        if res.returncode != 0:
            print("Error: No parece que estés autenticado en NotebookLM.")
            print("Por favor ejecuta en tu terminal: nlm login")
            sys.exit(1)
    except FileNotFoundError:
        print("Error: La herramienta CLI 'nlm' no está instalada o no está en el PATH.")
        print("Por favor instala y configura la CLI de NotebookLM antes de continuar.")
        sys.exit(1)

def select_folder(folder_arg=None):
    folders = []
    pdf_base = "pdf"
    if not os.path.exists(pdf_base):
        print(f"Error: La carpeta '{pdf_base}' no existe. Primero debes descargar las actas usando DescargarActas.py.")
        sys.exit(1)
        
    for item in os.listdir(pdf_base):
        item_path = os.path.join(pdf_base, item)
        if os.path.isdir(item_path):
            pdfs = [f for f in os.listdir(item_path) if f.lower().endswith(".pdf")]
            if pdfs:
                folders.append((item, item_path, len(pdfs)))
                
    if not folders:
        print(f"No se encontraron carpetas con archivos PDF dentro de '{pdf_base}'.")
        print("Por favor ejecuta DescargarActas.py primero.")
        sys.exit(1)
        
    folders.sort()
    
    if folder_arg:
        matched = next((f for f in folders if f[0] == folder_arg or f[1] == folder_arg), None)
        if matched:
            print(f"Usando carpeta especificada por argumento: {matched[0]} ({matched[2]} archivos)")
            return matched
        else:
            print(f"Error: La carpeta '{folder_arg}' no fue encontrada o no contiene PDFs en '{pdf_base}'.")
            sys.exit(1)
            
    if len(folders) == 1:
        print(f"Detectada una única carpeta de actas: {folders[0][0]} ({folders[0][2]} archivos)")
        return folders[0]
        
    print("\n=============================================")
    print(" CARPETAS DE ACTAS DISPONIBLES PARA SUBIR")
    print("=============================================")
    for idx, (name, path, count) in enumerate(folders):
        dep_name, mun_name = "", ""
        if len(name) == 5 and name.isdigit():
            dep_code = name[:2]
            mun_code = name[2:]
            dep_name, mun_name = get_region_names(dep_code, mun_code)
        
        region_label = f" ({dep_name} - {mun_name})" if dep_name else ""
        print(f"  {idx + 1:2d}. {name}{region_label} - {count} archivos PDF")
        
    while True:
        sel = input(f"\nSelecciona la carpeta a subir (1-{len(folders)}): ").strip()
        try:
            idx = int(sel) - 1
            if 0 <= idx < len(folders):
                return folders[idx]
        except ValueError:
            pass
        print("Selección inválida. Intenta de nuevo.")

def create_notebook(title):
    print(f"Creando nuevo notebook en NotebookLM: '{title}'...")
    try:
        cmd = ["nlm", "notebook", "create", title, "--json"]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        notebook_id = None
        try:
            data = json.loads(res.stdout)
            if isinstance(data, dict):
                notebook_id = data.get("id") or data.get("notebook_id") or data.get("notebookId")
        except Exception:
            pass
            
        if not notebook_id:
            match = re.search(r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}", res.stdout)
            if match:
                notebook_id = match.group(0)
                
        if notebook_id:
            print(f"[+] Notebook creado con éxito. ID: {notebook_id}")
            return notebook_id
        else:
            print(f"[-] No se pudo extraer el ID del notebook del output:\n{res.stdout}")
            return None
    except Exception as e:
        print(f"[-] Error al crear el notebook: {e}")
        return None

def save_lotes_mapping(filepath, lotes_data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(lotes_data, f, indent=4, ensure_ascii=False)

def main():
    check_nlm_auth()
    
    parser = argparse.ArgumentParser(description="Subir actas de votación a Google NotebookLM.")
    parser.add_argument("--folder", type=str, help="Nombre de la carpeta en pdf/ a subir (ej. 07034)")
    parser.add_argument("--size", type=int, default=45, help="Tamaño de lote (cantidad de actas por notebook, default 45)")
    args = parser.parse_args()
    
    global lote_size
    lote_size = args.size
    
    selected_folder = select_folder(args.folder)
    folder_name, folder_path, pdf_count = selected_folder
    
    dep_code, mun_code = "00", folder_name
    if len(folder_name) == 5 and folder_name.isdigit():
        dep_code = folder_name[:2]
        mun_code = folder_name[2:]
        
    dep_name, mun_name = get_region_names(dep_code, mun_code)
    region_label = f"{dep_name} - {mun_name}" if dep_name else folder_name
    os.makedirs("lotes", exist_ok=True)
    mapping_path = os.path.join("lotes", f"lotes_{dep_code}_{mun_code}.json")
    
    lotes_mapping = []
    if os.path.exists(mapping_path):
        try:
            with open(mapping_path, "r", encoding="utf-8") as f:
                lotes_mapping = json.load(f)
            print(f"Cargado mapeo existente desde '{mapping_path}'")
        except Exception as e:
            print(f"Advertencia: No se pudo leer {mapping_path}: {e}")
    else:
        old_path = os.path.join("lotes", "lotes_notebooklm.json")
        if dep_code == "01" and mun_code == "280" and os.path.exists(old_path):
            # Compatibilidad para Turbo Antioquia
            try:
                with open(old_path, "r", encoding="utf-8") as f:
                    lotes_mapping = json.load(f)
                print(f"Cargado mapeo existente para Turbo desde '{old_path}'")
                save_lotes_mapping(mapping_path, lotes_mapping)
            except Exception as e:
                print(f"Advertencia: No se pudo migrar {old_path}: {e}")

    # Obtener PDFs
    all_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.lower().endswith(".pdf")]
    all_files.sort()
    
    total_files = len(all_files)
    total_lotes = math.ceil(total_files / lote_size)
    print(f"\nSe encontraron {total_files} actas. Subiendo en {total_lotes} lotes de hasta {lote_size} actas...")
    
    for i in range(total_lotes):
        lote_num = i + 1
        start_idx = i * lote_size
        end_idx = min(start_idx + lote_size, total_files)
        lote_files = all_files[start_idx:end_idx]
        
        # Buscar lote existente
        lote_data = next((l for l in lotes_mapping if l.get("lote") == lote_num), None)
        
        notebook_title = f"{region_label} - Lote {lote_num}"
        
        if lote_data:
            notebook_id = lote_data.get("notebook_id")
            if "archivos" not in lote_data:
                lote_data["archivos"] = []
            print(f"\n--- Lote {lote_num}: Reutilizando notebook '{lote_data.get('nombre', notebook_title)}' (ID: {notebook_id}) ---")
        else:
            notebook_id = create_notebook(notebook_title)
            if not notebook_id:
                print(f"[-] Saltando Lote {lote_num} debido a error al crear notebook.")
                continue
                
            lote_data = {
                "lote": lote_num,
                "nombre": notebook_title,
                "notebook_id": notebook_id,
                "archivos": []
            }
            lotes_mapping.append(lote_data)
            save_lotes_mapping(mapping_path, lotes_mapping)
            
        print(f"Subiendo archivos a este lote ({len(lote_data['archivos'])}/{len(lote_files)} ya subidos)...")
        for idx, filepath in enumerate(lote_files):
            filename = os.path.basename(filepath)
            
            if filename in lote_data["archivos"]:
                print(f"  [{idx + 1}/{len(lote_files)}] Saltando {filename} (ya subido)")
                continue
                
            print(f"  [{idx + 1}/{len(lote_files)}] Subiendo {filename} ...")
            try:
                cmd_add = ["nlm", "source", "add", notebook_id, "-f", filepath]
                subprocess.run(cmd_add, capture_output=True, text=True, check=True)
                lote_data["archivos"].append(filename)
                save_lotes_mapping(mapping_path, lotes_mapping)
            except Exception as e:
                print(f"    [-] Error al subir {filename}: {e}")
                
    print("\n=== PROCESO DE SUBIDA COMPLETADO ===")
    print(f"Se ha guardado el mapeo final de notebooks en '{mapping_path}'.")

if __name__ == "__main__":
    main()
