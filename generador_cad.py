"""
Pasos para construir geometría:

  Paso 1 :
      Cada rectángulo (dedito) = rectángulo de ancho "ly" y altura "grosor", rotado 90°.
      Tras rotar: extensión en X = grosor, extensión en Y = ly.

  Paso 2 (espacio entre):
      pitch = grosor + lz

  Paso 3 (radios de las vueltas):
      r_exterior = grosor + lz/2
      r_interior = lz/2

  Paso 4 (n par):
      Se valida que n sea par, para que las dos puntas libres (donde
      van los pads) queden del mismo lado (arriba).

  Paso 5 (rectángulo extra en el primer y último dedo):
      En la punta LIBRE del primer y del último dedo se pega un
      rectángulo extra: altura grosor, ancho "distSepar+grosor+lz/2",
      alineado igual que los demás dedos (extiende el dedo más allá
      de "ly").

  Paso 6 (segmento horizontal):
      Desde la punta de ese rectángulo extra sale otro rectángulo,
      horizontal: ancho "ydist", altura "grosor". Viaja en el mismo
      sentido que la vuelta vecina (hacia adentro).


  Paso 7 (pads):
      Pegados al final de ese segmento horizontal van los pads,
      tamaño dpads x hpads. La distancia entre los dos pads es fija
      (dist_entre_pads); "ydist" se calcula para que esa distancia se
      cumpla exactamente.

  Paso 8 (rectángulo exterior):
      x_length, y_length -- calculados a partir de "a".

  Paso 9 (margen constante "a"):
      "a" se usa para calcular el tamaño del rectángulo exterior, de
      modo que quede exactamente a distancia "a" de: los dedos
      (izq/der), los pads (arriba), los semicírculos (abajo).

"""

import os
import ezdxf


def generar_microheater_real(
    x_length: float,
    y_length: float,
    lz: float,
    n: int,
    a: float = 5.0,
    distSepar: float = 2.0,
    dpads: float = 3.0,
    hpads: float = 3.0,
    dist_entre_pads: float = 5.0,
    nombre_archivo: str = "microheater_real.dxf",
):
    """
    Construye el microheater y lo exporta a DXF.

    La entrada es x_length, y_length, lz, n (lo que me dan).
    Tanto "grosor" como "ly" se calculan

      - "grosor" sale de exigir que el margen en X también sea
        exactamente "a" 
            x_length = n*grosor + (n-1)*lz + 2*a
            grosor = (x_length - (n-1)*lz - 2*a) / n

      - "ly" sale de y_length, igual que antes, pero usando el grosor
        calculo

    dist_entre_pads : distancia FIJA deseada entre el centro de los dos
        pads. "ydist" se calcula para que esa distancia se cumpla.
    """
    #  Validación n debe ser par 
    if n % 2 != 0 or n < 2:
        raise ValueError(f"n debe ser par y >= 2 (recibido n={n}).")

    # calculo grosor
    grosor = (x_length - (n - 1) * lz - 2 * a) / n
    if grosor <= 0:
        raise ValueError(
            f"grosor calculado salió <= 0 ({grosor:.3f}). x_length es muy "
            "chico para ese lz, n y margen a; sube x_length, baja lz/n, "
            "o revisa el margen a."
        )

    # espacio
    pitch = grosor + lz

    # radios
    r_interior = lz / 2
    r_exterior = grosor + lz / 2

    # ancho total
    ancho_coil = (n - 1) * pitch + grosor

    largo_extra = distSepar + grosor + lz / 2

    # Calculo ly
    ly = y_length - (largo_extra + r_exterior - grosor / 2 + hpads / 2 + 2 * a)
    if ly <= 0:
        raise ValueError(
            f"ly calculado salió <= 0 ({ly:.3f}). y_length es muy chico "
            "para los demás valores fijos (a, grosor, distSepar, hpads, lz); "
            "sube y_length o revisa esos fijos."
        )

    # ydist calculado a partir de la distancia fija entre pads 
       #
    #   dist_entre_pads = ancho_coil - 2*grosor - 2*ydist - dpads
    #  ydist = (ancho_coil - 2*grosor - dpads - dist_entre_pads) / 2
    ydist = (ancho_coil - 2 * grosor - dpads - dist_entre_pads) / 2
    if ydist <= 0:
        raise ValueError(
            f"ydist calculado salió <= 0 ({ydist:.3f}). "
            "dist_entre_pads es muy grande para el ancho del serpentín "
            "resultante; baja dist_entre_pads o revisa n/grosor/lz/dpads."
        )

    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    def add_rect_centrado(cx, cy, w, h, layer):
        """Rectángulo centrado en (cx, cy), ancho w, alto h."""
        rx0, rx1 = cx - w / 2, cx + w / 2
        ry0, ry1 = cy - h / 2, cy + h / 2
        msp.add_lwpolyline(
            [(rx0, ry0), (rx1, ry0), (rx1, ry1), (rx0, ry1), (rx0, ry0)],
            close=True, dxfattribs={"layer": layer},
        )

    def add_rect_por_esquinas(x0, y0, x1, y1, layer):
        """Rectángulo definido directamente por sus esquinas (no centrado)."""
        msp.add_lwpolyline(
            [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)],
            close=True, dxfattribs={"layer": layer},
        )

    centros_x = [-ancho_coil / 2 + grosor / 2 + i * pitch for i in range(n)]
    extremo_izquierdo = -ancho_coil / 2   # borde externo del dedo 0
    extremo_derecho = ancho_coil / 2      # borde externo del dedo n-1

    primera_vuelta_arriba = False

    def vuelta_va_arriba(i):
        base = (i % 2 == 0)
        return base if primera_vuelta_arriba else (not base)

    y_punta_libre_guardada = None  # para calcular el margen superior después

    for i in range(n):
        es_terminal = (i == 0 or i == n - 1)
        cx = centros_x[i]

        if not es_terminal:
            # rec normal: de -ly/2 a +ly/2 (paso 1)
            add_rect_centrado(cx, 0, grosor, ly, "microheater")
        else:
            # Averiguar de qué lado está la punta LIBRE de este rec terminal
            if i == 0:
                conectado_arriba = vuelta_va_arriba(0)
            else:
                conectado_arriba = vuelta_va_arriba(n - 2)

            if conectado_arriba:
                y_min = -ly / 2 - largo_extra
                y_max = ly / 2
                y_punta_libre = y_min
                signo_libre = -1   # la punta libre queda hacia abajo
            else:
                y_min = -ly / 2
                y_max = ly / 2 + largo_extra
                y_punta_libre = y_max
                signo_libre = 1    # la punta libre queda hacia arriba

            y_punta_libre_guardada = y_punta_libre  # igual para ambos recs terminales

            direccion = 1 if i == 0 else -1

            alto_total = y_max - y_min
            cy = (y_max + y_min) / 2
            add_rect_centrado(cx, cy, grosor, alto_total, "microheater")

            # Arranca en el borde
            borde_de_salida = cx + direccion * (grosor / 2)
            cx_horizontal = borde_de_salida + direccion * (ydist / 2)

            cy_pieza = y_punta_libre - signo_libre * (grosor / 2)

            add_rect_centrado(cx_horizontal, cy_pieza, ydist, grosor, "microheater")

            cx_pad = borde_de_salida + direccion * (ydist + dpads / 2)
            add_rect_centrado(cx_pad, cy_pieza, dpads, hpads, "PADS")

    for i in range(n - 1):
        cx_vuelta = (centros_x[i] + centros_x[i + 1]) / 2
        arriba = vuelta_va_arriba(i)
        cy_vuelta = ly / 2 if arriba else -ly / 2
        angulo_inicio, angulo_fin = (0, 180) if arriba else (180, 360)

        msp.add_arc(
            center=(cx_vuelta, cy_vuelta), radius=r_interior,
            start_angle=angulo_inicio, end_angle=angulo_fin,
            dxfattribs={"layer": "microheater"},
        )
        msp.add_arc(
            center=(cx_vuelta, cy_vuelta), radius=r_exterior,
            start_angle=angulo_inicio, end_angle=angulo_fin,
            dxfattribs={"layer": "microheater"},
        )

    # Plaquita
    extremo_superior = y_punta_libre_guardada - grosor / 2 + hpads / 2
    extremo_inferior = -(ly / 2 + r_exterior)

    x0, x1 = -x_length / 2, x_length / 2
    y0 = extremo_inferior - a
    y1 = y0 + y_length

    add_rect_por_esquinas(x0, y0, x1, y1, "RECTANGULO")

    # margenes
    margen_x_real = (x_length - ancho_coil) / 2
    margen_superior_real = y1 - extremo_superior
    margen_inferior_real = extremo_inferior - y0

    ruta_absoluta = os.path.abspath(nombre_archivo)
    doc.saveas(ruta_absoluta)

    return {
        "ruta_absoluta": ruta_absoluta,
        "grosor_calculado": grosor,
        "ly_calculado": ly,
        "ydist_calculado": ydist,
        "pitch": pitch,
        "r_interior": r_interior,
        "r_exterior": r_exterior,
        "largo_extra": largo_extra,
        "ancho_coil": ancho_coil,
        "margen_x_real (vs a)": margen_x_real,
        "margen_superior_real (vs a)": margen_superior_real,
        "margen_inferior_real (vs a)": margen_inferior_real,
    }


# Valores: estan  los fijo y los que van a llegar por modelo

def main():

    X_LENGTH = 40.0           # ancho del rectángulo exterior (x_length) formulario
    Y_LENGTH = 45.0           # alto del rectángulo exterior (y_length)formulario
    LZ = 3.0                  # espacio libre entre dedos vecinos (lz) ml
    N = 6                     # número de dedos/loops, debe ser PAR (n) ml

    # constantes del diseño
    MARGEN_A = 5.0            # margen constante en los 4 lados (a)
    DIST_SEPAR = 2.0          # longitud extra en la punta del dedo terminal (distSepar)
    DPADS = 3.0               # ancho del pad (dpads)
    HPADS = 3.0               # alto del pad (hpads)
    DIST_ENTRE_PADS = 5.0     # distancia FIJA entre los dos pads

    try:
        info = generar_microheater_real(
            x_length=X_LENGTH,
            y_length=Y_LENGTH,
            lz=LZ,
            n=N,
            a=MARGEN_A,
            distSepar=DIST_SEPAR,
            dpads=DPADS,
            hpads=HPADS,
            dist_entre_pads=DIST_ENTRE_PADS,
            nombre_archivo="microheater_real.dxf",
        )
        print("\n¡Listo! Archivo guardado en:")
        print(f"  {info['ruta_absoluta']}")
        print("\nDatos calculados (ly y ydist salieron solos; revisa los márgenes reales):")
        for k, v in info.items():
            if k == "ruta_absoluta":
                continue
            print(f"  {k}: {v:.3f}" if isinstance(v, float) else f"  {k}: {v}")
    except Exception:
        import traceback
        print("\n¡Algo falló! Este es el error completo:\n")
        traceback.print_exc()


if __name__ == "__main__":
    main()
