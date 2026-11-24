# Microheater Design — Automated Microheater Design & Inverse Optimization

Aplicación web y pipeline de diseño inverso para microcalentadores serpentín (**`Proyecto-microheaterwebvercel`**), desarrollada con **Python**, **Flask**, **scikit-learn**, **SciPy** y **ezdxf**. El sistema combina modelos subrogados entrenados sobre simulaciones de **COMSOL Multiphysics** (`datos_comsol.csv`) con optimización evolutiva (`differential_evolution`) para proponer geometría y corriente según la estrategia seleccionada, además de generar archivos CAD (`.dxf`), Gerber (PCB) y scripts/modelos para COMSOL.

> **Despliegue en producción:** `https://microheater-design.vercel.app`

---

## Características principales

- **Modelos subrogados con `GradientBoostingRegressor`:** Predicen la temperatura en la región de interés (`comp1.temp_roi` / `temp_objetivo`) y la uniformidad térmica (`comp1.std_dev`) sin reentrenar en cada petición.
- **Optimización inversa con tres estrategias (`resolver_inverso`):**
  - **Estrategia A (Solo temperatura):** Minimiza el error cuadrático frente a la temperatura objetivo.
  - **Estrategia B (Eficiencia energética):** Penaliza corrientes altas para reducir el consumo eléctrico manteniendo la temperatura deseada.
  - **Estrategia C (Alta uniformidad):** Penaliza `std_dev` para favorecer una distribución térmica más homogénea.
- **Validación geométrica compartida:** Verifica condiciones como número par de dedos (`n >= 2`), `lz > 0`, límite de grosor respecto a los pads (`grosor <= min(dpads, hpads)`), separación entre pads (`ydist > 0`), largo de dedo (`ly > 0`) y holgura entre curvas y pads.
- **Interfaz web bilingüe (EN / ES):** Permite definir dimensiones de la placa (`x_length`, `y_length`), temperatura objetivo (`temp_target`) y estrategia (`A`, `B`, `C`), consultar predicciones y gestionar la exportación de archivos.

---

## Estructura del proyecto

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

---

## Parámetros y criterios geométricos

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

---

## Entrenamiento y exportación de modelos

1. Revisa y ejecuta los notebooks en `modelo/` (`modelo.ipynb` / `modelofin.ipynb`) sobre `modelo/datos_comsol.csv` para entrenar y guardar los modelos subrogados.
2. Asegúrate de que los archivos de modelo utilizados por `app.py` (por ejemplo `modelo/modelo_subrogado_temperatura.pkl`, `modelo/modelo_subrogado_uniformidad.pkl` o los archivos `.joblib` que cargue tu aplicación) estén incluidos en el repositorio y no bloqueados por `.gitignore`.
3. Carga los modelos al iniciar `app.py` (usando rutas relativas seguras basadas en `Path(__file__).resolve().parent`) para responder rápido en cada petición.

---

## Instalación y ejecución local

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

---

## Despliegue en Vercel y exportación a COMSOL (`.mph`)

### Despliegue web en Vercel
- Verifica que todas las librerías importadas por `app.py` y los generadores (`flask`, `numpy`, `pandas`, `scipy`, `scikit-learn`, `joblib`, `ezdxf`, etc.) figuren en `requirements.txt` y que `vercel.json` apunte correctamente a tu aplicación.
- Comparte siempre el dominio de producción `https://microheater-design.vercel.app` (verificando que no haya bloqueo de autenticación si deseas acceso público).
- En el entorno *serverless* de Vercel, el sistema de archivos es de solo lectura excepto `/tmp`; escribe archivos temporales en `/tmp` o envíalos en memoria.

### Exportación a COMSOL Multiphysics (`.mph`)

> **Importante:** La generación de archivos `.mph` mediante `comsol/generador_comsol.py` (`mph.start()`) **no funciona desde el despliegue web en Vercel**. Para generarlo, la persona debe ejecutarlo **en su propio computador (local)** y **tener COMSOL Multiphysics instalado** (con licencia activa y `MPh` configurado).

Esto ocurre porque el entorno *serverless* de Vercel no cuenta con COMSOL Multiphysics instalado ni con licencia activa del motor de simulación, y ejecutar un motor multiphysics pesado dentro de una función *serverless* no es viable.

- **En local (requiere COMSOL instalado):** Ejecuta el generador en tu equipo usando los parámetros obtenidos en la web para crear el archivo `.mph`.
- **En la web (Vercel):** La aplicación está enfocada en la predicción/optimización con los modelos subrogados y en la exportación de archivos que no dependen del motor de COMSOL.

---

## Contexto académico

Proyecto desarrollado en el marco de estudios e investigación en **Ingeniería Biomédica / Ingeniería de Sistemas** en la **Universidad de los Andes** (Bogotá, Colombia).
