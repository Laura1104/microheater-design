import os
import uuid
import joblib
import numpy as np
import pandas as pd
from flask import Flask, jsonify, render_template, request, send_file
from scipy.optimize import differential_evolution

# Importamos las funciones de los generadores
from generador_cad import generar_microheater_real
from generador_gerber import generar_microheater_gerber

app = Flask(__name__)
ultimo_comsol = None

# ==========================================
# CARGAR LOS MODELOS SUBROGADOS AL INICIAR
# ==========================================
# Apuntamos a la carpeta 'modelo/' tal como la tienes estructurada
MODELO_TEMP_PATH = os.path.join('modelo', 'modelo_subrogado_temperatura.pkl')
MODELO_STD_PATH = os.path.join('modelo', 'modelo_subrogado_uniformidad.pkl')

try:
  modelo_temp = joblib.load(MODELO_TEMP_PATH)
  modelo_std = joblib.load(MODELO_STD_PATH)
  print(' ¡Modelos subrogados cargados exitosamente en la aplicación!')
except Exception as e:
  print(
      f'No se pudieron cargar los modelos .pkl ({e}). Asegúrate'
      ' de haberlos guardado en la carpeta modelo/.'
  )


# ==========================================
# FUNCIÓN DE DISEÑO INVERSO (OPTIMIZADOR)
# ==========================================
def resolver_inverso(
    x_user, y_user, temp_target, estrategia='C', a=0.5, maxiter=25
):
  def funcion_costo(params):
    n_float, lz_val, i_val = params
    n_par = int(np.round(n_float))
    if n_par % 2 != 0:
      n_par += 1
    if n_par < 2:
      n_par = 2

    # Restricción geométrica dura
    grosor_calc = (x_user - (n_par - 1) * lz_val - 2 * a) / n_par
    if grosor_calc <= 0.1:
      return 1e6  # Penalización alta si la geometría no es viable

    input_eval = pd.DataFrame(
        [[x_user, y_user, n_par, lz_val, i_val]],
        columns=['x_length', 'y_length', 'n', 'lz', 'corriente'],
    )

    t_pred = modelo_temp.predict(input_eval)[0]
    error_temp = (t_pred - temp_target) ** 2

    # --- ESTRATEGIAS ---
    if estrategia == 'A':
      return error_temp  # Solo precisión térmica
    elif estrategia == 'B':
      return error_temp + 0.1 * i_val  # Temperatura + Eficiencia Energética
    elif estrategia == 'C':
      std_pred = modelo_std.predict(input_eval)[0]
      return (
          error_temp + 0.5 * std_pred
      )  # Temperatura + Alta Uniformidad Térmica

    return error_temp

  # Límites: n (2 a 36), lz (0.2 a 3.0 mm), corriente (0.1 a 1.0 A)
  bounds = [(2, 36), (0.2, 3.0), (0.1, 1.0)]
  res = differential_evolution(
      funcion_costo, bounds, seed=42, maxiter=maxiter, popsize=10
  )

  n_opt = int(np.round(res.x[0]))
  if n_opt % 2 != 0:
    n_opt += 1
  if n_opt < 2:
    n_opt = 2

  lz_opt = round(float(res.x[1]), 3)
  i_opt = round(float(res.x[2]), 3)

  input_final = pd.DataFrame(
      [[x_user, y_user, n_opt, lz_opt, i_opt]],
      columns=['x_length', 'y_length', 'n', 'lz', 'corriente'],
  )

  t_final = float(modelo_temp.predict(input_final)[0])
  std_final = float(modelo_std.predict(input_final)[0])

  return n_opt, lz_opt, i_opt, t_final, std_final


@app.route('/')
def index():
  return render_template('index.html')


# ==========================================
# 1. CAD (.DXF) - USANDO EL MODELO INTELIGENTE
# ==========================================
@app.route('/generar_cad', methods=['POST'])
def generar_cad():
  try:
    data = request.get_json() or {}

    x_length = float(data.get('x_length', 30.0))
    y_length = float(data.get('y_length', 35.0))
    temp_target = float(
        data.get('temp_target', 40.0)
    )  # Temperatura que pide el usuario
    estrategia = data.get(
        'estrategia', 'C'
    )  # Estrategia seleccionada (A, B o C)

    # AQUÍ LLAMAMOS AL OPTIMIZADOR CON LOS MODELOS .PKL
    n, lz, corriente, t_lograda, std_lograda = resolver_inverso(
        x_user=x_length,
        y_user=y_length,
        temp_target=temp_target,
        estrategia=estrategia,
    )

    nombre_dxf = 'microheater_generado.dxf'
    ruta_salida = os.path.join('/tmp', nombre_dxf)

    generar_microheater_real(
        x_length=x_length,
        y_length=y_length,
        lz=lz,
        n=n,
        a=2.0,
        distSepar=2,
        dpads=1.7,
        hpads=1.7,
        dist_entre_pads=3.0,
        nombre_archivo=ruta_salida,
    )

    return jsonify({
        'status': 'ok',
        'n_vueltas': n,
        'lz': lz,
        'corriente': corriente,
        'temperatura_lograda': round(t_lograda, 2),
        'uniformidad_std': round(std_lograda, 2),
        'descarga_url': '/descargar_cad',
    })

  except Exception as e:
    return jsonify({'status': 'error', 'mensaje': str(e)}), 400


@app.route('/descargar_cad', methods=['GET'])
def descargar_cad():
  ruta_salida = os.path.join('/tmp', 'microheater_generado.dxf')
  if os.path.exists(ruta_salida):
    return send_file(
        ruta_salida,
        as_attachment=True,
        download_name='microheater_disenado.dxf',
    )
  return jsonify({'status': 'error', 'mensaje': 'Archivo no encontrado'}), 404


# ==========================================
# 2. GERBER (.ZIP) - USANDO EL MODELO INTELIGENTE
# ==========================================
@app.route('/generar_gerber', methods=['POST'])
def generar_gerber():
  try:
    data = request.get_json() or {}

    x_length = float(data.get('x_length', 30.0))
    y_length = float(data.get('y_length', 35.0))
    temp_target = float(data.get('temp_target', 40.0))
    estrategia = data.get('estrategia', 'C')

    # LLAMAMOS AL OPTIMIZADOR
    n, lz, corriente, t_lograda, std_lograda = resolver_inverso(
        x_user=x_length,
        y_user=y_length,
        temp_target=temp_target,
        estrategia=estrategia,
    )

    generar_microheater_gerber(
        x_length=x_length,
        y_length=y_length,
        lz=lz,
        n=n,
        a=2.0,
        distSepar=2.0,
        dpads=1.7,
        hpads=1.7,
        dist_entre_pads=3.0,
        carpeta_salida='/tmp',
        nombre_base='microheater_disenado',
    )

    return jsonify({
        'status': 'ok',
        'n_vueltas': n,
        'lz': lz,
        'corriente': corriente,
        'temperatura_lograda': round(t_lograda, 2),
        'uniformidad_std': round(std_lograda, 2),
        'descarga_url': '/descargar_gerber',
    })

  except Exception as e:
    return jsonify({'status': 'error', 'mensaje': str(e)}), 400


@app.route('/descargar_gerber', methods=['GET'])
def descargar_gerber():
  ruta_zip = os.path.join('/tmp', 'microheater_disenado_gerber.zip')
  if os.path.exists(ruta_zip):
    return send_file(
        ruta_zip,
        as_attachment=True,
        download_name='microheater_gerber.zip',
    )
  return jsonify({'status': 'error', 'mensaje': 'Archivo no encontrado'}), 404


# ==========================================
# 3. COMSOL (.MPH) - USANDO EL MODELO INTELIGENTE
# ==========================================

@app.route('/generar_comsol', methods=['POST'])
def generar_comsol():

    if os.environ.get('VERCEL'):
        return jsonify({
            'status': 'error',
            'mensaje': (
                'La generación de COMSOL está disponible únicamente en la versión '
                'local.'
            ),
        }), 501

    try:
        global ultimo_comsol

        data = request.get_json() or {}

        x_length = float(data.get('x_length', 30.0))
        y_length = float(data.get('y_length', 35.0))
        temp_target = float(data.get('temp_target', 40.0))
        estrategia = data.get('estrategia', 'C')

        # LLAMAMOS AL OPTIMIZADOR
        n, lz, corriente, t_lograda, std_lograda = resolver_inverso(
            x_user=x_length,
            y_user=y_length,
            temp_target=temp_target,
            estrategia=estrategia,
        )

        # GENERAMOS EL NOMBRE Y LA RUTA DEL ARCHIVO
        nombre_mph = f'microheater_disenado_{uuid.uuid4().hex[:8]}.mph'
        ruta_salida = os.path.join(app.root_path, nombre_mph)

        ultimo_comsol = nombre_mph

        # IMPORTAMOS EL GENERADOR DE COMSOL
        from comsol.generador_comsol import generar_microheater_comsol

        # GENERAMOS EL MODELO .MPH
        generar_microheater_comsol(
            x_length=x_length,
            y_length=y_length,
            lz=lz,
            n=n,
            a=2.0,
            distSepar=2.0,
            dpads=1.7,
            hpads=1.7,
            dist_entre_pads=3.0,
            nombre_archivo=ruta_salida,
        )

        return jsonify({
            'status': 'ok',
            'n_vueltas': n,
            'lz': lz,
            'corriente': corriente,
            'temperatura_lograda': round(t_lograda, 2),
            'uniformidad_std': round(std_lograda, 2),
            'descarga_url': '/descargar_comsol',
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'mensaje': f'Error COMSOL: {str(e)}'
        }), 400


@app.route('/descargar_comsol', methods=['GET'])
def descargar_comsol():

    if ultimo_comsol:
        ruta_mph = os.path.join(app.root_path, ultimo_comsol)

        if os.path.exists(ruta_mph):
            return send_file(
                ruta_mph,
                as_attachment=True,
                download_name='microheater_disenado.mph',
            )

    return jsonify({
        'status': 'error',
        'mensaje': 'Archivo no encontrado'
    }), 404


# ==========================================
# EJECUTAR APLICACIÓN
# ==========================================

if __name__ == '__main__':
    app.run(
        host='127.0.0.1',
        port=5050,
        debug=True,
        threaded=True
    )