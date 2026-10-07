import os
from flask import Flask, jsonify, render_template, request, send_file
import numpy as np
import pandas as pd
import joblib
from tensorflow.keras.models import load_model
from scipy.optimize import differential_evolution

# Importamos tu función generadora CAD
from generador_cad import generar_serpentin_real

app = Flask(__name__)

# ==========================================
# 1. Cargar Modelo ML, Scaler y FEATURES
# ==========================================
FEATURES = ["Corriente", "n_in", "x_length", "y_length", "grosor"]

# Cargamos exactamente tus archivos de la raíz del proyecto
MODEL_PATH = os.path.join(app.root_path, 'best_temperature_model.keras')
SCALER_PATH = os.path.join(app.root_path, 'temperature_scaler.pkl')

model_nn = load_model(MODEL_PATH)
scaler = joblib.load(SCALER_PATH)

# ==========================================
# 2. Algoritmo de Diseño Inverso de Ana
# ==========================================
def inverse_design(temperatura_objetivo, x_length, y_length, grosor=0.00015, corriente_bounds=(0.1, 0.5), n_loops_min=3):
    n_loops_max = int(np.floor((x_length + 5) / (2 * grosor)))
    if n_loops_max < n_loops_min:
        n_loops_max = n_loops_min
        
    n_loops_bounds = (n_loops_min, n_loops_max)

    def predict_temperature_fv(corriente, n_loops):
        n_loops = int(round(n_loops))
        entrada = pd.DataFrame([{
            "Corriente": corriente,
            "n_in": n_loops,
            "x_length": x_length,
            "y_length": y_length,
            "grosor": grosor
        }])
        entrada = entrada[FEATURES]
        entrada_scaled = scaler.transform(entrada)
        temperatura_predicha = model_nn.predict(entrada_scaled, verbose=0).ravel()[0]
        return float(temperatura_predicha)

    def objective(parameters):
        corriente = parameters[0]
        n_loops = int(round(parameters[1]))
        temperatura_predicha = predict_temperature_fv(corriente, n_loops)
        return abs(temperatura_predicha - temperatura_objetivo)

    bounds = [corriente_bounds, n_loops_bounds]

    resultado = differential_evolution(objective, bounds=bounds, seed=42, polish=True)

    corriente_optima = float(resultado.x[0])
    n_loops_optimo = int(round(resultado.x[1]))
    n_loops_optimo = int(np.clip(n_loops_optimo, n_loops_min, n_loops_max))

    temperatura_predicha = predict_temperature_fv(corriente_optima, n_loops_optimo)
    error = temperatura_predicha - temperatura_objetivo

    return {
        "Target temperature (°C)": temperatura_objetivo,
        "Predicted temperature (°C)": temperatura_predicha,
        "Current (A)": corriente_optima,
        "Number of loops": n_loops_optimo,
        "Maximum number of loops": int(n_loops_max),
        "x_length": x_length,
        "y_length": y_length,
        "Thickness": grosor,
        "Error (°C)": error,
        "Absolute error (°C)": abs(error)
    }

# ==========================================
# 3. Rutas de Flask
# ==========================================
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/generar_cad', methods=['POST'])
def generar_cad():
    try:
        data = request.get_json() or {}

        # 1. Parámetros principales ingresados desde el Frontend
        temp_objetivo = float(data.get('temp_objetivo', 45.0))
        x_target = float(data.get('x_length', 30.0))  # Ancho deseado de la placa (mm)
        y_target = float(data.get('y_length', 35.0))  # Alto deseado de la placa (mm)

        # 2. Valores por defecto/constantes fijas
        grosor_fijo = float(data.get('grosor', 0.00015))  # Revisa la unidad utilizada durante el entrenamiento
        a_fijo = 5.0
        dist_separ_fijo = 2.0
        hpads_fijo = 3.0
        lz = float(data.get('lz', 3.0))

        # 3. EJECUTAR EL DISEÑO INVERSO DE ANA
        res_ana = inverse_design(
            temperatura_objetivo=temp_objetivo,
            x_length=x_target,
            y_length=y_target,
            grosor=grosor_fijo
        )

        n = res_ana["Number of loops"]
        corriente_calculada = res_ana["Current (A)"]
        temp_estimada = res_ana["Predicted temperature (°C)"]

        # Forzamos n par si lo requiere la función CAD
        if n % 2 != 0:
            n += 1

        # 4. Cálculo de ly a partir de y_target
        ly_calculado = (
            y_target
            - (2 * a_fijo)
            - (2 * grosor_fijo)
            - lz
            - dist_separ_fijo
            - (hpads_fijo / 2)
        )

        if ly_calculado <= 1.0:
            ly_calculado = 1.0

        # 5. Generar archivo DXF
        nombre_dxf = 'serpentin_generado.dxf'
        ruta_salida = os.path.join(app.root_path, nombre_dxf)

        info_cad = generar_serpentin_real(
            lz=lz,
            ly=ly_calculado,
            n=n,
            grosor=grosor_fijo,
            a=a_fijo,
            distSepar=dist_separ_fijo,
            hpads=hpads_fijo,
            nombre_archivo=ruta_salida,
        )

        # 6. Respuesta JSON al Frontend
        return jsonify({
            'status': 'ok',
            'temperatura_estimada': round(temp_estimada, 2),
            'corriente_calculada': round(corriente_calculada, 4),
            'n_vueltas': n,
            'lz': lz,
            'ly': round(ly_calculado, 2),
            'x_length_real': round(info_cad['x_length_calculado'], 2),
            'y_length_real': round(info_cad['y_length_calculado'], 2),
            'descarga_url': '/descargar_cad',
        })

    except Exception as e:
        return jsonify({'status': 'error', 'mensaje': str(e)}), 400


@app.route('/descargar_cad', methods=['GET'])
def descargar_cad():
    ruta_salida = os.path.join(app.root_path, 'serpentin_generado.dxf')
    if os.path.exists(ruta_salida):
        return send_file(
            ruta_salida,
            as_attachment=True,
            download_name='serpentin_disenado.dxf',
        )
    return jsonify({'status': 'error', 'mensaje': 'Archivo no encontrado'}), 404


if __name__ == '__main__':
    app.run(debug=True, port=5000)