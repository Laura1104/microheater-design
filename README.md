# Microheater Design — Automated Microheater Design & Inverse Optimization



https://github.com/user-attachments/assets/0eacf1d6-d695-405c-9b12-4b27d3a1ed68




[English](#english) | [Español](#español)

---

<a id="english"></a>

## English

Web application and inverse design pipeline for serpentine microheaters (**`Proyecto-microheaterwebvercel`**), built with **Python**, **Flask**, **scikit-learn**, **SciPy**, and **ezdxf**. The system combines surrogate models trained on **COMSOL Multiphysics** simulations (`datos_comsol.csv`) with evolutionary optimization (`differential_evolution`) to recommend geometry and drive current according to the selected strategy, while supporting CAD (`.dxf`), PCB Gerber, and COMSOL script/model workflows.

> **Production deployment:** `https://microheater-design.vercel.app`

### Key Features

- **Surrogate models (`GradientBoostingRegressor`):** Predict region-of-interest temperature (`comp1.temp_roi` / `temp_objetivo`) and thermal uniformity (`comp1.std_dev`) without retraining per request.
- **Inverse optimization with three strategies (`resolver_inverso`):**
  - **Strategy A (Temp Only):** Minimizes squared error against the target temperature.
  - **Strategy B (Energy Efficiency):** Penalizes high currents to reduce electrical power draw while meeting the target temperature.
  - **Strategy C (High Uniformity):** Penalizes `std_dev` to promote a more uniform thermal distribution.
- **Shared geometric validation:** Checks constraints such as an even number of fingers (`n >= 2`), `lz > 0`, track width limits relative to pads (`grosor <= min(dpads, hpads)`), pad spacing (`ydist > 0`), finger length (`ly > 0`), and clearance between turns and pads.
- **Bilingual web interface (EN / ES):** Lets users set plate dimensions (`x_length`, `y_length`), target temperature (`temp_target`), and optimization strategy (`A`, `B`, `C`), view predictions, and export files.

### Project Structure

```text
Proyecto-microheaterwebvercel/
├── comsol/
│   ├── __init__.py
│   └── generador_comsol.py
├── modelo/
│   ├── datos_comsol.csv
│   ├── modelo_subrogado_temperatura.pkl
│   ├── modelo_subrogado_uniformidad.pkl
│   ├── modelo.ipynb
│   └── modelofin.ipynb
├── static/
│   └── images/
├── templates/
│   └── index.html
├── .gitignore
├── app.py
├── generador_cad.py
├── generador_gerber.py
├── requirements.txt
└── vercel.json
```

### Parameters & Geometric Criteria

Keep base parameters consistent across training, optimization, and geometry generation:

| Parameter | Description | Reference Criterion / Value |
| :--- | :--- | :--- |
| `x_length`, `y_length` | Plate dimensions (mm) | Configurable via the form in `templates/index.html` |
| `n` | Number of serpentine fingers/segments | Even integer (`n >= 2`) so both terminals stay on the same side |
| `lz` | Gap between adjacent fingers (mm) | Optimized via `differential_evolution` |
| `corriente` | Drive current (A) | Optimized according to the selected strategy |
| `a` | Perimeter margin (mm) | Keep consistent across dataset/optimizer and generators |
| `dpads`, `hpads` | Contact pad dimensions (mm) | Default `1.7` mm |
| `dist_entre_pads` | Fixed distance between pads (mm) | Determines `ydist` |
| `distSepar` | Extension at terminal tips (mm) | Must not overlap adjacent curve clearance |

### Model Training & Artifacts

1. Review and run the notebooks in `modelo/` (`modelo.ipynb` / `modelofin.ipynb`) on `modelo/datos_comsol.csv` to train and export the surrogate models.
2. Make sure the model artifacts loaded by `app.py` (such as `modelo/modelo_subrogado_temperatura.pkl`, `modelo/modelo_subrogado_uniformidad.pkl`, or any `.joblib` files used by the app) are tracked in Git and not ignored by `.gitignore`.
3. Load models once when `app.py` starts (using path resolution relative to `Path(__file__).resolve().parent`) for fast inference.

### Local Setup & Execution

1. Clone the repository and install dependencies from `requirements.txt`:

```bash
git clone <YOUR_REPOSITORY_URL>
cd Proyecto-microheaterwebvercel
pip install -r requirements.txt
```

2. Start the Flask app locally:

```bash
python app.py
```

3. Open the local URL shown by Flask in your browser (typically `http://127.0.0.1:5000`).

### Vercel Deployment & COMSOL (`.mph`) Export

#### Web Deployment on Vercel
- Ensure all packages imported by `app.py` and the generators (`flask`, `numpy`, `pandas`, `scipy`, `scikit-learn`, `joblib`, `ezdxf`, etc.) are listed in `requirements.txt` and that `vercel.json` points to the entry point properly.
- Share the production domain `https://microheater-design.vercel.app` (and verify authentication protection is disabled if public access is intended).
- In Vercel's serverless runtime, the filesystem is read-only except for `/tmp`; write temporary files to `/tmp` or stream them in memory.

#### COMSOL Multiphysics (`.mph`) Export

> **Important:** Generating `.mph` files via `comsol/generador_comsol.py` (`mph.start()`) **does not run from the Vercel deployment**. To generate `.mph` files, users must run it **locally on their own computer** and **have COMSOL Multiphysics installed** (with an active license and `MPh` configured).

Vercel's serverless environment does not have COMSOL Multiphysics installed or an active simulation engine license, and running a heavy multiphysics engine inside a serverless function is not practical.

- **Local execution (COMSOL required):** Run the COMSOL generator on a machine with COMSOL Multiphysics installed using the parameters obtained from the web app.
- **Web deployment (Vercel):** Focused on fast surrogate-model inference and exporting files that do not require the COMSOL engine.

### Academic Context

Developed as part of academic research and coursework in **Biomedical Engineering / Systems Engineering** at **Universidad de los Andes** (Bogotá, Colombia).

---

<a id="español"></a>

## Español

Aplicación web y pipeline de diseño inverso para microcalentadores serpentín (**`Proyecto-microheaterwebvercel`**), desarrollada con **Python**, **Flask**, **scikit-learn**, **SciPy** y **ezdxf**. El sistema combina modelos subrogados entrenados sobre simulaciones de **COMSOL Multiphysics** (`datos_comsol.csv`) con optimización evolutiva (`differential_evolution`) para proponer geometría y corriente según la estrategia seleccionada, además de generar archivos CAD (`.dxf`), Gerber (PCB) y scripts/modelos para COMSOL.

> **Despliegue en producción:** `https://microheater-design.vercel.app`

### Características principales

- **Modelos subrogados con `GradientBoostingRegressor`:** Predicen la temperatura en la región de interés (`comp1.temp_roi` / `temp_objetivo`) y la uniformidad térmica (`comp1.std_dev`) sin reentrenar en cada petición.
- **Optimización inversa con tres estrategias (`resolver_inverso`):**
  - **Estrategia A (Solo temperatura):** Minimiza el error cuadrático frente a la temperatura objetivo.
  - **Estrategia B (Eficiencia energética):** Penaliza corrientes altas para reducir el consumo eléctrico manteniendo la temperatura deseada.
  - **Estrategia C (Alta uniformidad):** Penaliza `std_dev` para favorecer una distribución térmica más homogénea.
- **Validación geométrica compartida:** Verifica condiciones como número par de dedos (`n >= 2`), `lz > 0`, límite de grosor respecto a los pads (`grosor <= min(dpads, hpads)`), separación entre pads (`ydist > 0`), largo de dedo (`ly > 0`) y holgura entre curvas y pads.
- **Interfaz web bilingüe (EN / ES):** Permite definir dimensiones de la placa (`x_length`, `y_length`), temperatura objetivo (`temp_target`) y estrategia (`A`, `B`, `C`), consultar predicciones y gestionar la exportación de archivos.

### Estructura del proyecto

```text
Proyecto-microheaterwebvercel/
├── comsol/
│   ├── __init__.py
│   └── generador_comsol.py
├── modelo/
│   ├── datos_comsol.csv
│   ├── modelo_subrogado_temperatura.pkl
│   ├── modelo_subrogado_uniformidad.pkl
│   ├── modelo.ipynb
│   └── modelofin.ipynb
├── static/
│   └── images/
├── templates/
│   └── index.html
├── .gitignore
├── app.py
├── generador_cad.py
├── generador_gerber.py
├── requirements.txt
└── vercel.json
```

### Parámetros y criterios geométricos

Para evitar inconsistencias entre el entrenamiento, la optimización y la generación de archivos, mantén alineados los parámetros base:

| Parámetro | Descripción | Criterio / valor de referencia |
| :--- | :--- | :--- |
| `x_length`, `y_length` | Dimensiones de la placa (mm) | Configurables desde el formulario en `templates/index.html` |
| `n` | Número de dedos/tramos del serpentín | Entero par (`n >= 2`) para que ambos terminales queden del mismo lado |
| `lz` | Separación libre entre dedos vecinos (mm) | Optimizado mediante `differential_evolution` |
| `corriente` | Corriente de alimentación (A) | Optimizada según la estrategia elegida |
| `a` | Margen perimetral (mm) | Mantener coherente entre dataset/optimizador y generadores |
| `dpads`, `hpads` | Dimensiones de los pads de contacto (mm) | Por defecto `1.7` mm |
| `dist_entre_pads` | Distancia fija entre pads (mm) | Determina `ydist` |
| `distSepar` | Extensión en puntas terminales (mm) | Sujeta a no invadir la zona de la curva vecina |

### Entrenamiento y exportación de modelos

1. Revisa y ejecuta los notebooks en `modelo/` (`modelo.ipynb` / `modelofin.ipynb`) sobre `modelo/datos_comsol.csv` para entrenar y guardar los modelos subrogados.
2. Asegúrate de que los archivos de modelo utilizados por `app.py` (por ejemplo `modelo/modelo_subrogado_temperatura.pkl`, `modelo/modelo_subrogado_uniformidad.pkl` o los archivos `.joblib` que cargue tu aplicación) estén incluidos en el repositorio y no bloqueados por `.gitignore`.
3. Carga los modelos al iniciar `app.py` (usando rutas relativas seguras basadas en `Path(__file__).resolve().parent`) para responder rápido en cada petición.

### Instalación y ejecución local

1. Clona el repositorio e instala las dependencias de `requirements.txt`:

```bash
git clone <URL_DE_TU_REPOSITORIO>
cd Proyecto-microheaterwebvercel
pip install -r requirements.txt
```

2. Inicia la aplicación Flask en local:

```bash
python app.py
```

3. Abre la URL local que muestre Flask en tu navegador (habitualmente `http://127.0.0.1:5000`).

### Despliegue en Vercel y exportación a COMSOL (`.mph`)

#### Despliegue web en Vercel
- Verifica que todas las librerías importadas por `app.py` y los generadores (`flask`, `numpy`, `pandas`, `scipy`, `scikit-learn`, `joblib`, `ezdxf`, etc.) figuren en `requirements.txt` y que `vercel.json` apunte correctamente a tu aplicación.
- Comparte siempre el dominio de producción `https://microheater-design.vercel.app` (verificando que no haya bloqueo de autenticación si deseas acceso público).
- En el entorno *serverless* de Vercel, el sistema de archivos es de solo lectura excepto `/tmp`; escribe archivos temporales en `/tmp` o envíalos en memoria.

#### Exportación a COMSOL Multiphysics (`.mph`)

> **Importante:** La generación de archivos `.mph` mediante `comsol/generador_comsol.py` (`mph.start()`) **no funciona desde el despliegue web en Vercel**. Para generarlo, la persona debe ejecutarlo **en su propio computador (local)** y **tener COMSOL Multiphysics instalado** (con licencia activa y `MPh` configurado).

Esto ocurre porque el entorno *serverless* de Vercel no cuenta con COMSOL Multiphysics instalado ni con licencia activa del motor de simulación, y ejecutar un motor multiphysics pesado dentro de una función *serverless* no es viable.

- **En local (requiere COMSOL instalado):** Ejecuta el generador en tu equipo usando los parámetros obtenidos en la web para crear el archivo `.mph`.
- **En la web (Vercel):** La aplicación está enfocada en la predicción/optimización con los modelos subrogados y en la exportación de archivos que no dependen del motor de COMSOL.

### Contexto académico

Proyecto desarrollado en el marco de estudios e investigación en **Ingeniería Biomédica / Ingeniería de Sistemas** en la **Universidad de los Andes** (Bogotá, Colombia).
