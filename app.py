import os
import uuid
from flask import Flask, jsonify, render_template, request, send_file

# Importamos las funciones de los generadores
from generador_cad import generar_microheater_real
from generador_gerber import generar_microheater_gerber

app = Flask(__name__)
ultimo_comsol = None


@app.route('/')
def index():
  return render_template('index.html')


# ==========================================
# 1. CAD (.DXF)
# ==========================================
@app.route('/generar_cad', methods=['POST'])
def generar_cad():
  try:
    data = request.get_json() or {}

    x_length = float(data.get('x_length', 30.0))
    y_length = float(data.get('y_length', 35.0))
    n = int(data.get('n', 6))
    lz = float(data.get('lz', 3.0))

    if n % 2 != 0:
      n += 1

    nombre_dxf = 'microheater_generado.dxf'
    ruta_salida = os.path.join('/tmp', nombre_dxf)

    generar_microheater_real(
        x_length=x_length,
        y_length=y_length,
        lz=lz,
        n=n,
        a=5.0,
        distSepar=2.0,
        dpads=3.0,
        hpads=3.0,
        dist_entre_pads=5.0,
        nombre_archivo=ruta_salida,
    )

    return jsonify({
        'status': 'ok',
        'n_vueltas': n,
        'lz': lz,
        'corriente': '0.35',
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
# 2. GERBER (.ZIP)
# ==========================================
@app.route('/generar_gerber', methods=['POST'])
def generar_gerber():
  try:
    data = request.get_json() or {}

    x_length = float(data.get('x_length', 30.0))
    y_length = float(data.get('y_length', 35.0))
    n = int(data.get('n', 6))
    lz = float(data.get('lz', 3.0))

    if n % 2 != 0:
      n += 1

    generar_microheater_gerber(
        x_length=x_length,
        y_length=y_length,
        lz=lz,
        n=n,
        a=5.0,
        distSepar=2.0,
        dpads=3.0,
        hpads=3.0,
        dist_entre_pads=5.0,
        carpeta_salida='/tmp',
        nombre_base='microheater_disenado',
    )

    return jsonify({
        'status': 'ok',
        'n_vueltas': n,
        'lz': lz,
        'corriente': '0.35',
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
# 3. COMSOL (.MPH)
# ==========================================
@app.route('/generar_comsol', methods=['POST'])
def generar_comsol():

  # Vercel no puede ejecutar COMSOL
  if os.environ.get('VERCEL'):
    return jsonify({
        'status': 'error',
        'mensaje': 'La generación de COMSOL está disponible únicamente en la versión local.'
    }), 501

  try:
    global ultimo_comsol

    data = request.get_json() or {}

    x_length = float(data.get('x_length', 30.0))
    y_length = float(data.get('y_length', 35.0))
    n = int(data.get('n', 6))
    lz = float(data.get('lz', 3.0))

    if n % 2 != 0:
      n += 1

    nombre_mph = f'microheater_disenado_{uuid.uuid4().hex[:8]}.mph'
    ruta_salida = os.path.join(app.root_path, nombre_mph)

    ultimo_comsol = nombre_mph

    from comsol.generador_comsol import generar_microheater_comsol

    generar_microheater_comsol(
        x_length=x_length,
        y_length=y_length,
        lz=lz,
        n=n,
        a=5.0,
        distSepar=2.0,
        dpads=3.0,
        hpads=3.0,
        dist_entre_pads=5.0,
        nombre_archivo=ruta_salida,
    )

    return jsonify({
        'status': 'ok',
        'n_vueltas': n,
        'lz': lz,
        'corriente': '0.35',
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
  
if __name__ == '__main__':
  app.run(debug=False, threaded=False, port=5000)