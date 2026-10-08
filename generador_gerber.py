"""
microheater_a_gerber.py
------------------------
Genera el MISMO serpentín que microheater_comsol_real.py (DXF) y
microheater_a_comsol.py (COMSOL), con las mismas fórmulas, pero como
archivos GERBER (formato RS-274X), el estándar que usan las
fabricantes de PCB. Este mismo Gerber se puede abrir/importar en
Altium (y en KiCad, etc.), por eso no hace falta un script aparte
para Altium: Altium no se puede escribir desde Python, pero sí lee
Gerber.

SE GENERAN 2 ARCHIVOS (+ un .zip con los dos):
    <nombre>_cobre.gtl     -> capa de COBRE superior: el serpentín
                              (dedos, tramos horizontales, vueltas)
                              y los pads.
    <nombre>_contorno.gko  -> CONTORNO de la placa: el rectángulo
                              exterior (x_length x y_length).
    (Así se separa en el mundo real: el cobre y el borde de la
     placa van en capas distintas.)

DECISIONES DE DISEÑO (para que sepas qué se hizo y por qué):
    - Unidades: milímetros. Formato de coordenadas 4.6 (6 decimales).
    - El origen (0,0) se pone en la ESQUINA INFERIOR IZQUIERDA de la
      placa, para que todas las coordenadas sean positivas (muchas
      herramientas de PCB lo prefieren). Por eso, a cada coordenada
      del diseño (que en el DXF está centrado en el origen) se le
      suma un desplazamiento (ox, oy).
    - Dedos y tramos horizontales: se dibujan como "regiones" rellenas
      (G36/G37). Las piezas se traslapan donde se tocan, y en Gerber
      el cobre se suma, así que el resultado es una sola pista
      continua (igual que el "unir" automático de COMSOL).
    - Vueltas (semicírculos gruesos): también una región, con arcos
      (G03 = arco antihorario, G02 = horario) en vez de segmentos.
    - Pads: se "flashean" (D03) con una apertura rectangular
      dpads x hpads -- así las herramientas los reconocen como pads
      de verdad, no solo como un dibujo de cobre.
    - El contorno se traza con una línea de 0.1 mm de ancho.

Requisitos: ninguno (solo la librería estándar de Python).
"""

import os
import zipfile


def generar_microheater_gerber(
    x_length: float,
    y_length: float,
    lz: float,
    n: int,
    a: float = 5.0,
    distSepar: float = 2.0,
    dpads: float = 3.0,
    hpads: float = 3.0,
    dist_entre_pads: float = 5.0,
    carpeta_salida: str = ".",
    nombre_base: str = "microheater",
):
    """
    Genera los archivos Gerber del serpentín.

    Mismos parámetros y mismas fórmulas que generar_microheater_real()
    (el de DXF) -- ver ese archivo para el detalle de cada fórmula.
    Retorna un dict con las rutas de los archivos y los valores
    calculados.
    """
    # ============================================================
    # 1) MISMAS FÓRMULAS que en los otros scripts
    # ============================================================
    if n % 2 != 0 or n < 2:
        raise ValueError(f"n debe ser par y >= 2 (recibido n={n}).")

    grosor = (x_length - (n - 1) * lz - 2 * a) / n
    if grosor <= 0:
        raise ValueError(
            f"grosor calculado salió <= 0 ({grosor:.3f}). Revisa x_length/lz/n/a."
        )

    pitch = grosor + lz
    r_interior = lz / 2
    r_exterior = grosor + lz / 2
    ancho_coil = (n - 1) * pitch + grosor
    largo_extra = distSepar + grosor + lz / 2

    ly = y_length - (largo_extra + r_exterior - grosor / 2 + hpads / 2 + 2 * a)
    if ly <= 0:
        raise ValueError(f"ly calculado salió <= 0 ({ly:.3f}). Revisa y_length.")

    ydist = (ancho_coil - 2 * grosor - dpads - dist_entre_pads) / 2
    if ydist <= 0:
        raise ValueError(
            f"ydist calculado salió <= 0 ({ydist:.3f}). Revisa dist_entre_pads/n/lz/dpads."
        )

    centros_x = [-ancho_coil / 2 + grosor / 2 + i * pitch for i in range(n)]

    primera_vuelta_arriba = False

    def vuelta_va_arriba(i):
        base = (i % 2 == 0)
        return base if primera_vuelta_arriba else (not base)

    # ============================================================
    # 2) Desplazamiento: origen en la esquina inferior izquierda
    # ============================================================
    # En el diseño (como en el DXF) el rectángulo exterior va de
    #   x: -x_length/2 .. +x_length/2
    #   y: y0 .. y0 + y_length,   con y0 = -(ly/2 + r_exterior) - a
    # Para que la esquina inferior izquierda quede en (0,0):
    y0 = -(ly / 2 + r_exterior) - a
    ox = x_length / 2
    oy = -y0

    def n6(v):
        """Convierte mm a entero en formato 4.6 (6 decimales implícitos)."""
        return int(round(v * 1_000_000))

    def xy(x, y):
        """Texto de coordenadas Gerber, ya desplazado al origen nuevo."""
        return f"X{n6(x + ox)}Y{n6(y + oy)}"

    # ============================================================
    # 3) Capa de COBRE
    # ============================================================
    cobre = []     # líneas de comandos que van dentro del archivo
    pads = []      # centros (x, y) de los pads, para flashearlos al final

    def region_rect(cx, cy, w, h):
        """Rectángulo relleno centrado en (cx,cy), ancho w, alto h."""
        x0, x1 = cx - w / 2, cx + w / 2
        y0_, y1 = cy - h / 2, cy + h / 2
        cobre.append("G36*")
        cobre.append(f"{xy(x0, y0_)}D02*")   # D02 = mover sin dibujar
        cobre.append(f"{xy(x1, y0_)}D01*")   # D01 = dibujar línea
        cobre.append(f"{xy(x1, y1)}D01*")
        cobre.append(f"{xy(x0, y1)}D01*")
        cobre.append(f"{xy(x0, y0_)}D01*")   # cerrar
        cobre.append("G37*")

    def region_vuelta(cx, cy, arriba):
        """
        Semicírculo grueso (banda entre r_interior y r_exterior).

        arriba=True : mitad superior (forma "∩"), de 0° a 180°.
        arriba=False: mitad inferior (forma "∪"), de 180° a 360°.

        Contorno de la región (siempre en este orden):
          1. arco EXTERIOR antihorario (G03)
          2. línea recta al borde del arco interior
          3. arco INTERIOR horario (G02), de regreso
          4. línea recta que cierra la región
        I y J son el desplazamiento desde el punto de inicio del arco
        hasta su centro.
        """
        ro, ri = r_exterior, r_interior
        if arriba:
            p_ext_ini = (cx + ro, cy)   # ángulo 0°
            p_ext_fin = (cx - ro, cy)   # ángulo 180°
            p_int_ini = (cx - ri, cy)   # ángulo 180°
            p_int_fin = (cx + ri, cy)   # ángulo 0°
            ij_ext = (-ro, 0.0)         # centro - inicio
            ij_int = (+ri, 0.0)
        else:
            p_ext_ini = (cx - ro, cy)   # ángulo 180°
            p_ext_fin = (cx + ro, cy)   # ángulo 360°
            p_int_ini = (cx + ri, cy)   # ángulo 360°
            p_int_fin = (cx - ri, cy)   # ángulo 180°
            ij_ext = (+ro, 0.0)
            ij_int = (-ri, 0.0)

        cobre.append("G36*")
        cobre.append(f"{xy(*p_ext_ini)}D02*")
        cobre.append("G03*")  # arco antihorario
        cobre.append(f"{xy(*p_ext_fin)}I{n6(ij_ext[0])}J{n6(ij_ext[1])}D01*")
        cobre.append("G01*")  # volver a líneas rectas
        cobre.append(f"{xy(*p_int_ini)}D01*")
        cobre.append("G02*")  # arco horario
        cobre.append(f"{xy(*p_int_fin)}I{n6(ij_int[0])}J{n6(ij_int[1])}D01*")
        cobre.append("G01*")
        cobre.append(f"{xy(*p_ext_ini)}D01*")  # cerrar
        cobre.append("G37*")

    # --- Dedos, tramos horizontales y pads (misma lógica que en el DXF) ---
    for i in range(n):
        es_terminal = (i == 0 or i == n - 1)
        cx = centros_x[i]

        if not es_terminal:
            region_rect(cx, 0, grosor, ly)
        else:
            if i == 0:
                conectado_arriba = vuelta_va_arriba(0)
            else:
                conectado_arriba = vuelta_va_arriba(n - 2)

            if conectado_arriba:
                y_min = -ly / 2 - largo_extra
                y_max = ly / 2
                y_punta_libre = y_min
                signo_libre = -1
            else:
                y_min = -ly / 2
                y_max = ly / 2 + largo_extra
                y_punta_libre = y_max
                signo_libre = 1

            direccion = 1 if i == 0 else -1

            region_rect(cx, (y_max + y_min) / 2, grosor, y_max - y_min)

            borde_de_salida = cx + direccion * (grosor / 2)
            cx_horizontal = borde_de_salida + direccion * (ydist / 2)
            cy_pieza = y_punta_libre - signo_libre * (grosor / 2)
            region_rect(cx_horizontal, cy_pieza, ydist, grosor)

            cx_pad = borde_de_salida + direccion * (ydist + dpads / 2)
            pads.append((cx_pad, cy_pieza))

    # --- Vueltas entre dedos consecutivos ---
    for i in range(n - 1):
        cx_vuelta = (centros_x[i] + centros_x[i + 1]) / 2
        arriba = vuelta_va_arriba(i)
        cy_vuelta = ly / 2 if arriba else -ly / 2
        region_vuelta(cx_vuelta, cy_vuelta, arriba)

    # --- Armar el archivo de cobre ---
    lineas_cobre = [
        "G04 microheater - capa de cobre superior (generado por microheater_a_gerber.py)*",
        "%MOMM*%",
        "%FSLAX46Y46*%",
        "%TF.FileFunction,Copper,L1,Top*%",
        "%TF.FilePolarity,Positive*%",
        f"%ADD10R,{dpads:.6f}X{hpads:.6f}*%",   # apertura rectangular = el pad
        "G75*",                                 # arcos multi-cuadrante
        "%LPD*%",                               # polaridad "dark" (dibuja cobre)
        "G01*",
    ]
    lineas_cobre += cobre
    lineas_cobre.append("D10*")                  # seleccionar la apertura del pad
    for (px, py) in pads:
        lineas_cobre.append(f"{xy(px, py)}D03*")  # D03 = "flash" (estampar)
    lineas_cobre.append("M02*")                  # fin del archivo

    # ============================================================
    # 4) Capa de CONTORNO (rectángulo exterior)
    # ============================================================
    xa, xb = -x_length / 2, x_length / 2
    ya, yb = y0, y0 + y_length
    lineas_contorno = [
        "G04 microheater - contorno de la placa (generado por microheater_a_gerber.py)*",
        "%MOMM*%",
        "%FSLAX46Y46*%",
        "%TF.FileFunction,Profile,NP*%",
        "%TF.FilePolarity,Positive*%",
        "%ADD10C,0.100000*%",                    # línea de 0.1 mm
        "G75*",
        "%LPD*%",
        "G01*",
        "D10*",
        f"{xy(xa, ya)}D02*",
        f"{xy(xb, ya)}D01*",
        f"{xy(xb, yb)}D01*",
        f"{xy(xa, yb)}D01*",
        f"{xy(xa, ya)}D01*",
        "M02*",
    ]

    # ============================================================
    # 5) Escribir los archivos y el .zip
    # ============================================================
    os.makedirs(carpeta_salida, exist_ok=True)
    ruta_cobre = os.path.abspath(os.path.join(carpeta_salida, f"{nombre_base}_cobre.gtl"))
    ruta_contorno = os.path.abspath(os.path.join(carpeta_salida, f"{nombre_base}_contorno.gko"))
    ruta_zip = os.path.abspath(os.path.join(carpeta_salida, f"{nombre_base}_gerber.zip"))

    with open(ruta_cobre, "w", encoding="ascii") as f:
        f.write("\n".join(lineas_cobre) + "\n")
    with open(ruta_contorno, "w", encoding="ascii") as f:
        f.write("\n".join(lineas_contorno) + "\n")
    with zipfile.ZipFile(ruta_zip, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(ruta_cobre, os.path.basename(ruta_cobre))
        z.write(ruta_contorno, os.path.basename(ruta_contorno))

    return {
        "ruta_cobre": ruta_cobre,
        "ruta_contorno": ruta_contorno,
        "ruta_zip": ruta_zip,
        "grosor_calculado": grosor,
        "ly_calculado": ly,
        "ydist_calculado": ydist,
        "pitch": pitch,
        "r_interior": r_interior,
        "r_exterior": r_exterior,
        "largo_extra": largo_extra,
        "ancho_coil": ancho_coil,
    }


def main():
    # --- Lo que te dan a ti como parámetro (en la página web vienen del formulario) ---
    X_LENGTH = 40.0
    Y_LENGTH = 45.0
    LZ = 3.0
    N = 6

    # --- Fijos ---
    MARGEN_A = 5.0
    DIST_SEPAR = 2.0
    DPADS = 2.0
    HPADS = 2.0
    DIST_ENTRE_PADS = 5.0

    try:
        info = generar_microheater_gerber(
            x_length=X_LENGTH,
            y_length=Y_LENGTH,
            lz=LZ,
            n=N,
            a=MARGEN_A,
            distSepar=DIST_SEPAR,
            dpads=DPADS,
            hpads=HPADS,
            dist_entre_pads=DIST_ENTRE_PADS,
            nombre_base="microheater",
        )
        print("\n¡Listo! Archivos Gerber guardados en:")
        print(f"  Cobre:    {info['ruta_cobre']}")
        print(f"  Contorno: {info['ruta_contorno']}")
        print(f"  ZIP:      {info['ruta_zip']}")
        print("\nDatos calculados:")
        for k, v in info.items():
            if k.startswith("ruta_"):
                continue
            print(f"  {k}: {v:.3f}" if isinstance(v, float) else f"  {k}: {v}")
    except Exception:
        import traceback
        print("\n¡Algo falló! Este es el error completo:\n")
        traceback.print_exc()


if __name__ == "__main__":
    main()
