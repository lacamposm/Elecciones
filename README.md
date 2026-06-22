# Auditoría de Actas E-14 de Colombia

Este proyecto proporciona un conjunto de herramientas y scripts automatizados en Python para descargar todos los Formularios E-14 de cualquier Departamento o Municipio de Colombia directamente desde la Registraduría Nacional del Estado Civil, y procesarlos masivamente en **Google NotebookLM** para auditorías e identificación de irregularidades.

---

## 🚀 Guía de Inicio Rápido (Replicación en cualquier Región)

Sigue estos sencillos pasos para replicar la descarga y auditoría en tu departamento o municipio:

### 1. Prerrequisitos e Instalación

Asegúrate de tener instalado Python (versión >= 3.8). 

1. **Clona o descarga este repositorio** en tu máquina local.
2. **Instala las librerías necesarias** ejecutando la siguiente línea en tu terminal o consola:
   ```bash
   pip install -r requirements.txt
   ```

### 2. Autenticación en Google NotebookLM

Los scripts se integran con la interfaz de comandos de Google NotebookLM (`nlm`) para subir y agrupar automáticamente tus actas en notebooks de análisis.

1. Instala la herramienta CLI de NotebookLM (si no la tienes instalada):
   ```bash
   npm install -g @google/notebooklm-cli
   # O si usas otro gestor de paquetes de nlm
   ```
2. **Inicia sesión con tu cuenta de Google** ejecutando:
   ```bash
   nlm login
   ```
   *Esto abrirá tu navegador para que otorgues acceso seguro a NotebookLM.*

---

## 📂 Flujo de Trabajo

### Paso 1: Descargar las Actas E-14

Ejecuta el script de descarga desde la terminal:
```bash
python cli/descargar.py
```

* **Modo Interactivo (Recomendado)**: El script detectará si tienes las bases de datos de la Registraduría y te presentará un menú numerado para seleccionar cómodamente tu **Departamento** y luego el **Municipio** (por ejemplo, `ANTIOQUIA` -> `TURBO`). Ya no necesitas saber los códigos electorales de antemano.
* **Modo Automatizado (CLI)**: Si deseas saltarte los menús y ejecutarlo en una sola línea (útil para scripts de automatización), usa los argumentos `--dep` y `--mun`:
  ```bash
  python cli/descargar.py --dep 01 --mun 280
  ```
  *(01 es Antioquia, 280 es Turbo. El script guardará los PDFs en la carpeta `pdf/01280`).*

---

### Paso 2: Subir y Crear Notebooks en NotebookLM

Una vez finalizada la descarga de los PDFs, ejecuta:
```bash
python cli/subir.py
```

* **Modo Interactivo (Recomendado)**: Si tienes descargas de múltiples regiones, te mostrará un menú para que elijas cuál deseas procesar.
* **Modo Automatizado (CLI)**: Si deseas ejecutar el proceso en una sola línea o en un script programado, especifica el nombre de la carpeta usando `--folder` y el tamaño del lote con `--size` (default 45):
  ```bash
  python cli/subir.py --folder 07034 --size 45
  ```

El script automatiza lo siguiente:
1. **Creación Automática de Notebooks**: Creará los notebooks necesarios en tu cuenta de NotebookLM (ej. `"BOYACA - BUSBANZA - Lote 1"`) agrupando las actas en lotes óptimos.
2. **Idempotencia Estricta (Guardado de progreso)**: Si la subida se interrumpe debido a problemas de conexión o límites de tasa, puedes volver a ejecutar el script y este **omitirá automáticamente los PDFs que ya se subieron**, reanudando el proceso exactamente donde quedó. El mapeo se guarda en `lotes/lotes_<dep>_<mun>.json`.

---

### Paso 3: Realizar la Auditoría

Con las actas subidas a tus Notebooks en NotebookLM, puedes abrir la interfaz web de [Google NotebookLM](https://notebooklm.google.com) o usar comandos en la terminal (`nlm query`) para realizar preguntas de auditoría masivas, tales como:
* *"¿Hay actas donde falte alguna de las firmas de los jurados?"*
* *"Encuentra actas que tengan enmendaduras, tachones o modificaciones evidentes en la tabla de votos."*
* *"Genera una lista de mesas donde el total de votos supere el límite de votantes registrados."*

---

## 📁 Estructura del Proyecto

* **`cli/`**: Herramientas de Interfaz de Línea de Comandos (CLI) ejecutables:
  * **`cli/descargar.py`**: Script de búsqueda y descarga de actas (antes `DescargarActas.py`).
  * **`cli/subir.py`**: Script de subida y gestión de lotes a Google NotebookLM (antes `subir_actas_notebooklm.py`).
* **`src/`**: Paquete interno de Python que agrupa la lógica común del proyecto:
  * **`src/utils.py`**: Módulo central de utilidades que agrupa lógica de red (descarga), parsing del árbol de departamentos, menús interactivos de selección y resolución de nombres geográficos.
* **`data/`**: Carpeta que almacena los archivos de datos electorales estáticos y del sistema:
  * **`data/departmentsTree.json`**: Estructura de árbol electoral de la Registraduría (se descarga automáticamente si falta).
  * **`data/departmentsTree.csv`**: Versión plana en formato CSV de la geografía electoral completa de Colombia. Muy útil para abrir en Excel, buscar códigos de municipios, zonas y puestos de votación y contar mesas.
* **`lotes/`**: Directorio donde se guardan de forma organizada y privada los archivos de estado de NotebookLM:
  * **`lotes/lotes_<dep>_<mun>.json`**: Registro local de los IDs de notebooks creados y los PDFs subidos a cada lote.
* **`tools/`**: Directorio de scripts secundarios e históricos de depuración (ej. `descargar_divipol_electoral.py`).
* **`pdf/`**: Carpeta donde se almacenan las actas descargadas organizadas por carpetas `DEP+MUN` (ej. `pdf/01280`).
  * **`pdf/<dep><mun>/actas_mapeo.csv`**: Archivo CSV local generado automáticamente al descargar una región, que contiene la lista completa de mesas y sus nombres de archivo correspondientes para facilitar la auditoría.

