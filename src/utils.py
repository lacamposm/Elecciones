import os
import json
import requests
import sys

def download_file(url, path, headers=None):
    if headers is None:
        headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36"
        }
    print(f"Descargando {os.path.basename(path)} desde {url}...")
    r = requests.get(url, headers=headers, timeout=60, allow_redirects=True)
    r.raise_for_status()
    with open(path, "wb") as f:
        f.write(r.content)

def load_departments():
    tree_path = os.path.join("data", "departmentsTree.json")
    if not os.path.exists(tree_path):
        os.makedirs("data", exist_ok=True)
        url = "https://divulgacione14presidente.registraduria.gov.co/assets/temis/divipol_json/departmentsTree.json"
        try:
            download_file(url, tree_path)
        except Exception as e:
            print(f"Advertencia: No se pudo descargar {tree_path}: {e}")
            return None
            
    try:
        with open(tree_path, "r", encoding="utf-8") as f:
            tree_data = json.load(f)
        departments = []
        edges = tree_data.get("data", {}).get("departmentsTree", {}).get("edges", [])
        for edge in edges:
            node = edge.get("node", {})
            dep_code = node.get("idDepartmentCode")
            dep_name = node.get("departmentName")
            municipalities = []
            for mun in node.get("municipalities", []):
                municipalities.append({
                    "code": mun.get("municipalityCode"),
                    "name": mun.get("municipalityName")
                })
            municipalities.sort(key=lambda x: x["name"])
            departments.append({
                "code": dep_code,
                "name": dep_name,
                "municipalities": municipalities
            })
        departments.sort(key=lambda x: x["name"])
        return departments
    except Exception as e:
        print(f"Advertencia: Error al cargar {tree_path}: {e}")
        return None

def get_region_names(dep_code, mun_code):
    tree_path = os.path.join("data", "departmentsTree.json")
    if not os.path.exists(tree_path):
        return "", ""
    try:
        with open(tree_path, "r", encoding="utf-8") as f:
            tree_data = json.load(f)
        edges = tree_data.get("data", {}).get("departmentsTree", {}).get("edges", [])
        for edge in edges:
            node = edge.get("node", {})
            if node.get("idDepartmentCode") == dep_code:
                dep_name = node.get("departmentName")
                for mun in node.get("municipalities", []):
                    if mun.get("municipalityCode") == mun_code:
                        return dep_name, mun.get("municipalityName")
                return dep_name, ""
        return "", ""
    except Exception:
        return "", ""

def select_region_interactively(departments):
    if not departments:
        print("\nNo se pudo cargar la lista de departamentos de forma interactiva.")
        dep = input("Ingresa Departamento (DOS (2) dígitos, ej 03) [ENTER para 01 - ANTIOQUIA]: ").strip()
        if len(dep) == 0:
            dep = "01"
        assert len(dep)==2, f"Código de departamento errado {dep}"
        mun = input("Ingresa Municipio (TRES (3) dígitos, ej 052) [ENTER para 280 - TURBO]: ").strip()
        if len(mun) == 0:
            mun = "280"
        else:
            assert len(mun)==3, f"Código de municipio errado {mun}"
        return dep, mun

    print("\n=============================================")
    print(" BÚSQUEDA INTERACTIVA DE DEPARTAMENTO Y MUNICIPIO")
    print("=============================================")
    print("\nDepartamentos disponibles:")
    for idx, dep_item in enumerate(departments):
        print(f"  {idx + 1:2d}. {dep_item['name']} (Código: {dep_item['code']})")
        
    while True:
        sel = input("\nSelecciona el número del Departamento [ENTER para 01 - ANTIOQUIA]: ").strip()
        if len(sel) == 0:
            dep_selected = next(d for d in departments if d["code"] == "01")
            break
        if len(sel) == 2 and sel.isdigit():
            dep_selected = next((d for d in departments if d["code"] == sel), None)
            if dep_selected:
                break
        try:
            idx = int(sel) - 1
            if 0 <= idx < len(departments):
                dep_selected = departments[idx]
                break
        except ValueError:
            pass
        print("Selección inválida. Intenta de nuevo.")

    print(f"\n» Seleccionaste Departamento: {dep_selected['name']} (Código: {dep_selected['code']})")
    
    municipalities = dep_selected["municipalities"]
    print("\nMunicipios disponibles en este departamento:")
    for idx, mun_item in enumerate(municipalities):
        print(f"  {idx + 1:3d}. {mun_item['name']} (Código: {mun_item['code']})")
        
    while True:
        sel = input(f"\nSelecciona el número del Municipio [ENTER para TURBO/primer municipio]: ").strip()
        if len(sel) == 0:
            turbo = next((m for m in municipalities if m["code"] == "280"), None)
            mun_selected = turbo if turbo else municipalities[0]
            break
        if len(sel) == 3 and sel.isdigit():
            mun_selected = next((m for m in municipalities if m["code"] == sel), None)
            if mun_selected:
                break
        try:
            idx = int(sel) - 1
            if 0 <= idx < len(municipalities):
                mun_selected = municipalities[idx]
                break
        except ValueError:
            pass
        print("Selección inválida. Intenta de nuevo.")
        
    print(f"\n» Seleccionaste Municipio: {mun_selected['name']} (Código: {mun_selected['code']})")
    return dep_selected["code"], mun_selected["code"]
