
import os


def generar_microheater_comsol(
    x_length: float,
    y_length: float,
    lz: float,
    n: int,
    a: float = 5.0,
    distSepar: float = 2.0,
    dpads: float = 3.0,
    hpads: float = 3.0,
    dist_entre_pads: float = 5.0,
    nombre_archivo: str = "microheater.mph",
):
    
    import mph  

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

    # Arrancar comsol y modelo vacio

    client = mph.start()

    # Limpiar modelos anteriores de esta sesión
    client.clear()

    model = client.create("microheater")

    model.java.component().create("comp1", True)
    model.java.component("comp1").geom().create("geom1", 2)
    geom = model.java.component("comp1").geom("geom1")
    contador = {"r": 0, "c": 0, "dif": 0}

    def nuevo_tag(tipo):
        contador[tipo] += 1
        return f"{tipo}{contador[tipo]}"

    def rect(cx, cy, w, h):
        """Crea un rectángulo centrado en (cx,cy), ancho w, alto h."""
        tag = nuevo_tag("r")
        feat = geom.feature().create(tag, "Rectangle")
        feat.set("base", "center")
        feat.set("pos", [cx, cy])
        feat.set("size", [w, h])
        return tag

    def vuelta(cx, cy, arriba):
        """
        Crea la banda curva de una vuelta.
        """
        angulo_inicio = 0 if arriba else 180

        tag_out = nuevo_tag("c")
        f_out = geom.feature().create(tag_out, "Circle")
        f_out.set("pos", [cx, cy])
        f_out.set("r", r_exterior)
        f_out.set("angle", "180")
        f_out.set("rot", str(angulo_inicio))

        tag_in = nuevo_tag("c")
        f_in = geom.feature().create(tag_in, "Circle")
        f_in.set("pos", [cx, cy])
        f_in.set("r", r_interior)
        f_in.set("angle", "180")
        f_in.set("rot", str(angulo_inicio))

        tag_dif = nuevo_tag("dif")
        f_dif = geom.feature().create(tag_dif, "Difference")
        f_dif.selection("input").set(tag_out)
        f_dif.selection("input2").set(tag_in)
    
    y_punta_libre_guardada = None

    for i in range(n):
        es_terminal = (i == 0 or i == n - 1)
        cx = centros_x[i]

        if not es_terminal:
            rect(cx, 0, grosor, ly)
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

            y_punta_libre_guardada = y_punta_libre

            direccion = 1 if i == 0 else -1

            alto_total = y_max - y_min
            cy = (y_max + y_min) / 2
            rect(cx, cy, grosor, alto_total)

            borde_de_salida = cx + direccion * (grosor / 2)
            cx_horizontal = borde_de_salida + direccion * (ydist / 2)
            cy_pieza = y_punta_libre - signo_libre * (grosor / 2)

            rect(cx_horizontal, cy_pieza, ydist, grosor)

            cx_pad = borde_de_salida + direccion * (ydist + dpads / 2)
            rect(cx_pad, cy_pieza, dpads, hpads)

    for i in range(n - 1):
        cx_vuelta = (centros_x[i] + centros_x[i + 1]) / 2
        arriba = vuelta_va_arriba(i)
        cy_vuelta = ly / 2 if arriba else -ly / 2
        vuelta(cx_vuelta, cy_vuelta, arriba)

    extremo_inferior = -(ly / 2 + r_exterior)
    y0 = extremo_inferior - a
    cy_rect_exterior = y0 + y_length / 2
    rect(0, cy_rect_exterior, x_length, y_length)

    geom.run()

    ruta_absoluta = os.path.abspath(nombre_archivo)
    model.save(ruta_absoluta)


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
    }


def main():
    X_LENGTH = 40.0
    Y_LENGTH = 45.0
    LZ = 3.0
    N = 6

    MARGEN_A = 5.0
    DIST_SEPAR = 2.0
    DPADS = 3.0
    HPADS = 3.0
    DIST_ENTRE_PADS = 5.0

    try:
        info = generar_microheater_comsol(
            x_length=X_LENGTH,
            y_length=Y_LENGTH,
            lz=LZ,
            n=N,
            a=MARGEN_A,
            distSepar=DIST_SEPAR,
            dpads=DPADS,
            hpads=HPADS,
            dist_entre_pads=DIST_ENTRE_PADS,
            nombre_archivo="microheater.mph",
        )
        print("\n¡Listo! Archivo .mph guardado en:")
        print(f"  {info['ruta_absoluta']}")
        print("\nDatos calculados:")
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
