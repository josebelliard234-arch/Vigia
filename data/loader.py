import io
import re
import pandas as pd
from datetime import datetime

from data.database import clean_text

# Mapa unico de nombres de meses en espanol
_MESES_ES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}


def _fecha_a_semana_iso(fecha):
    """Convierte una fecha/datetime a etiqueta ISO tipo '2026-W23'."""
    semana = fecha.isocalendar()[1]
    return f"{fecha.year}-W{semana:02d}"


def _fecha_segura(anio, mes, dia):
    """Construye datetime o devuelve None si los componentes no forman una fecha valida."""
    try:
        return datetime(int(anio), int(mes), int(dia))
    except Exception:
        return None


def _semana_iso_desde_partes(anio, mes, dia):
    """Convierte partes de fecha a etiqueta ISO, conservando fallback None."""
    fecha = _fecha_segura(anio, mes, dia)
    return _fecha_a_semana_iso(fecha) if fecha else None


def _mes_numero(mes_txt):
    """Devuelve el numero de mes para los nombres/abreviaturas soportados actualmente."""
    return _MESES_ES.get(str(mes_txt).lower())


def _semana_iso_desde_patrones(texto, patrones):
    """Busca dia/mes/anio con patrones nombrados y devuelve la semana ISO si es valida."""
    if not texto or str(texto) == "nan":
        return None
    txt = str(texto).lower()
    for patron in patrones:
        m = re.search(patron, txt)
        if not m:
            continue
        mes = _mes_numero(m.group("mes"))
        if mes:
            semana = _semana_iso_desde_partes(m.group("anio"), mes, m.group("dia"))
            if semana:
                return semana
    return None


def _semana_iso_desde_valor_excel(val):
    """Extrae semana ISO desde un valor de Excel o desde texto de fecha conocido."""
    try:
        if hasattr(val, "year"):
            return _fecha_a_semana_iso(val)
    except Exception:
        pass

    val = str(val)

    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", val)
    if m:
        return _semana_iso_desde_partes(m.group(3), m.group(2), m.group(1))

    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", val)
    if m:
        return _semana_iso_desde_partes(m.group(1), m.group(2), m.group(3))

    return None


def parse_week_label(filename):
    """
    Intenta extraer la semana ISO del nombre del archivo.
    Soporta:
      - Formato YYYY-Wnn  (ej: 2026-W19)
      - Formato con mes en espanol (ej: 5_de_Mayo_2026 o 18_de_mayo_2026)
      - Formato DD_MM_YYYY o DD-MM-YYYY
    """
    nombre = filename.lower()

    # 1) Formato YYYY-Wnn
    m = re.search(r"(\d{4}-W\d{2})", filename, re.IGNORECASE)
    if m:
        return m.group(1)

    # 2a/2b) Formatos con mes en texto
    semana = _semana_iso_desde_patrones(nombre, [
        r"del?[_\- ](?P<dia>\d{1,2})[_\- ]al[_\- ]\d{1,2}[_\- ]de[_\- ](?P<mes>\w+)[_\- ](?P<anio>\d{4})",
        r"(?P<dia>\d{1,2})[_\- ]de[_\- ](?P<mes>\w+)[_\- ](?P<anio>\d{4})",
    ])
    if semana:
        return semana

    # 3) Formato DD_MM_YYYY o DD-MM-YYYY
    m = re.search(r"(\d{1,2})[_\-](\d{1,2})[_\-](\d{4})", nombre)
    if m:
        semana = _semana_iso_desde_partes(m.group(3), m.group(2), m.group(1))
        if semana:
            return semana

    return filename  # fallback: devuelve el nombre tal cual


def extract_date_from_excel(file_bytes):
    """
    Busca una fecha en las primeras filas del Excel.
    Soporta formatos DD/MM/YYYY y YYYY-MM-DD.
    """
    try:
        df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=0, header=None, nrows=5)
        for row in range(5):
            for col in range(8):
                try:
                    semana = _semana_iso_desde_valor_excel(df.iloc[row, col])
                    if semana:
                        return semana
                except Exception:
                    continue
    except Exception:
        pass
    return None


# Supermercados conocidos para detectar formato nuevo
_SUPERMERCADOS_CONOCIDOS = {
    "bravo", "pricesmart", "ole", "carrefour", "nacional", "jumbo",
    "plaza lama", "unidos", "la sirena", "la sirena market", "ritmo",
    "aprezio", "iberia", "el super"
}
# Columnas de resumen a ignorar en formato nuevo
_COLS_RESUMEN = {
    "resumen general", "media y/o", "promedio global", "precios minimo",
    "precios maximo", "moda", "mediana", "desviacion", "minimo", "maximo",
    "estandar", "n0.", "no.", "descripcion de productos"
}


def _extraer_semana_de_texto(texto):
    """Extrae semana ISO de un texto como 'Semana del 1 al 7 de Junio 2026'."""
    return _semana_iso_desde_patrones(texto, [
        r"del?\s+(?P<dia>\d{1,2})\s+(?:al\s+\d{1,2}\s+de\s+)?(?P<mes>\w+)\s+(?P<anio>\d{4})",
    ])


def _es_formato_nuevo(xl):
    """
    Detecta si el Excel es el formato nuevo (monitoreo con supermercados como columnas).
    Criterio: tiene pocas hojas y alguna contiene palabras clave de supermercados en su nombre.
    """
    hojas_lower = [h.lower() for h in xl.sheet_names]
    palabras_monitoreo = ["monit", "comp.", "resumen semanal", "comp. prod"]
    for h in hojas_lower:
        if any(p in h for p in palabras_monitoreo):
            return True
    return False


def _parse_formato_nuevo(file_bytes, semana):
    """Parser para el formato nuevo: una hoja principal con supermercados como columnas."""
    xl = pd.ExcelFile(io.BytesIO(file_bytes))
    rows = []

    # Buscar la hoja de datos principal (la primera que tenga productos)
    hoja_principal = xl.sheet_names[0]
    df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=hoja_principal, header=None)

    # Extraer semana del texto interno si no viene del nombre
    if not semana or semana == hoja_principal:
        for i in range(8):
            for j in range(min(5, len(df.columns))):
                txt = _extraer_semana_de_texto(df.iloc[i, j])
                if txt:
                    semana = txt
                    break
            if semana and re.match(r"\d{4}-W\d{2}", semana):
                break

    # Encontrar la fila de supermercados (fila con >= 3 nombres de supermercados)
    fila_supermercados = None
    store_cols = {}
    for fila_idx in range(min(15, len(df))):
        candidatos = {}
        for col_idx in range(len(df.columns)):
            val = str(df.iloc[fila_idx, col_idx]).strip()
            if val == "nan" or val == "":
                continue
            val_lower = val.lower()
            # Excluir columnas de resumen
            if any(ex in val_lower for ex in _COLS_RESUMEN):
                continue
            # Excluir numeros solos
            try:
                float(val)
                continue
            except Exception:
                pass
            # Es un supermercado si esta en la lista conocida O si no es un titulo largo
            if len(val) < 40 and col_idx >= 2:
                candidatos[col_idx] = val
        if len(candidatos) >= 3:
            fila_supermercados = fila_idx
            store_cols = candidatos
            break

    if not store_cols:
        return pd.DataFrame()

    # Filtrar solo columnas que son supermercados (excluir columnas de estadisticas)
    store_cols_filtrado = {}
    for col_idx, nombre in store_cols.items():
        nombre_lower = nombre.lower()
        if any(ex in nombre_lower for ex in _COLS_RESUMEN):
            continue
        store_cols_filtrado[col_idx] = nombre

    # Leer datos desde la fila siguiente al header de supermercados
    categoria = None
    for i in range(fila_supermercados + 1, len(df)):
        row = df.iloc[i].tolist()
        id_val   = row[0]
        prod_val = row[1] if len(row) > 1 else None
        pres_val = row[2] if len(row) > 2 else None

        # Categoria
        if isinstance(id_val, str) and re.match(r"\d+[-]", str(id_val).strip()):
            categoria = str(id_val).strip()
            continue

        if not isinstance(id_val, (int, float)) or pd.isna(id_val):
            continue
        if prod_val is None or pd.isna(prod_val):
            continue

        try:
            id_prod = int(id_val)
        except Exception:
            continue

        producto     = clean_text(prod_val)
        presentacion = clean_text(pres_val) if pres_val is not None and not pd.isna(pres_val) else ""

        for col_idx, supermercado in store_cols_filtrado.items():
            if col_idx >= len(row):
                continue
            precio = row[col_idx]
            if pd.isna(precio):
                continue
            try:
                precio_f = float(precio)
                if precio_f > 0:
                    rows.append({
                        "semana":       semana,
                        "provincia":    "Santo Domingo",
                        "supermercado": supermercado,
                        "categoria":    categoria or "Sin categoria",
                        "id_producto":  id_prod,
                        "producto":     producto,
                        "presentacion": presentacion,
                        "precio":       precio_f,
                    })
            except Exception:
                pass

    return pd.DataFrame(rows)


def parse_excel_bruto(file_bytes, filename):
    """
    Parser inteligente: detecta automaticamente el formato del Excel
    (formato nuevo con supermercados como columnas, o formato viejo con hojas por provincia).
    """
    semana = extract_date_from_excel(file_bytes) or parse_week_label(filename)
    xl = pd.ExcelFile(io.BytesIO(file_bytes))

    # Detectar formato
    if _es_formato_nuevo(xl):
        return _parse_formato_nuevo(file_bytes, semana)

    # Formato viejo: una hoja por provincia
    rows = []
    skip_sheets = {"Resumen General"}
    for sheet in xl.sheet_names:
        if sheet in skip_sheets:
            continue
        provincia = sheet
        df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet, header=None)
        store_cols = {}
        header_row = df.iloc[0]
        for col_idx in range(3, len(header_row)):
            val = str(header_row[col_idx]).strip()
            if val and val != "nan":
                store_cols[col_idx] = val
        categoria = None
        for _, row in df.iterrows():
            id_val   = row[0]
            prod_val = row[1]
            pres_val = row[2]
            if isinstance(id_val, str) and re.match(r"\d+[-]", id_val):
                categoria = id_val.strip()
                continue
            if not isinstance(id_val, (int, float)) or pd.isna(id_val):
                continue
            if pd.isna(prod_val):
                continue
            id_prod      = int(id_val)
            producto     = clean_text(prod_val)
            presentacion = clean_text(pres_val) if not pd.isna(pres_val) else ""
            for col_idx, supermercado in store_cols.items():
                precio = row[col_idx]
                if pd.isna(precio):
                    continue
                rows.append({
                    "semana":       semana,
                    "provincia":    provincia,
                    "supermercado": supermercado,
                    "categoria":    categoria or "Sin categoria",
                    "id_producto":  id_prod,
                    "producto":     producto,
                    "presentacion": presentacion,
                    "precio":       float(precio),
                })
    return pd.DataFrame(rows)


def fecha_inicio_a_semana_iso(texto):
    """
    De un texto como 'Semana del 1 al 7 de Junio 2026' extrae la FECHA DE INICIO
    (1 de Junio) y devuelve su semana ISO -> '2026-W23'. None si no puede.
    """
    return _semana_iso_desde_patrones(texto, [
        r"del?\s+(?P<dia>\d{1,2})\s+al\s+\d{1,2}\s+de\s+(?P<mes>\w+)\s+(?:del?\s+)?(?P<anio>\d{4})",
        r"del?\s+(?P<dia>\d{1,2})\s+de\s+(?P<mes>\w+)\s+(?:del?\s+)?(?P<anio>\d{4})",
    ])


def parsear_fecha_usuario(txt):
    """
    Acepta D/M/A en cualquier permutacion de digitos:
    2/5/26, 02/05/26, 2/5/2026, 02/05/2026, etc.
    Devuelve datetime o None si no se puede parsear.
    """
    txt = txt.strip().replace("-", "/").replace(".", "/")
    partes = txt.split("/")
    if len(partes) != 3:
        return None
    try:
        d, m, a = int(partes[0]), int(partes[1]), int(partes[2])
        if a < 100:
            a += 2000
        return _fecha_segura(a, m, d)
    except Exception:
        return None


def extraer_fechas_monitoreo(file_bytes):
    """
    Lee las 3 hojas del archivo de monitoreo y devuelve un dict con la semana ISO
    detectada en cada una (para validar contra lo que escribe el usuario):
      {
        'monitoreo':   '2026-W23' | None,   (fecha de inicio de la hoja principal)
        'comparativa': texto crudo | None,
        'resumen':     texto crudo | None,
      }
    """
    res = {"monitoreo": None, "comparativa": None, "resumen": None,
           "monitoreo_txt": None, "comparativa_txt": None, "resumen_txt": None}
    try:
        xl = pd.ExcelFile(io.BytesIO(file_bytes))
        for hoja in xl.sheet_names:
            hl = hoja.lower()
            df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=hoja, header=None, nrows=8)
            # Buscar texto de fecha en las primeras filas
            texto_encontrado = None
            for i in range(min(8, len(df))):
                for j in range(min(6, len(df.columns))):
                    val = str(df.iloc[i, j])
                    if val != "nan" and ("semana" in val.lower() or "del " in val.lower()
                                         or "vs" in val.lower() or "resumen desde" in val.lower()):
                        texto_encontrado = val
                        break
                if texto_encontrado:
                    break
            if texto_encontrado:
                if "monit" in hl:
                    res["monitoreo"]     = fecha_inicio_a_semana_iso(texto_encontrado)
                    res["monitoreo_txt"] = texto_encontrado
                elif "comp" in hl:
                    res["comparativa"]     = fecha_inicio_a_semana_iso(texto_encontrado)
                    res["comparativa_txt"] = texto_encontrado
                elif "resumen" in hl:
                    res["resumen"]     = fecha_inicio_a_semana_iso(texto_encontrado)
                    res["resumen_txt"] = texto_encontrado
    except Exception:
        pass
    return res


# ============================================================
# LECTOR DE EXCEL - HISTORIAL VALIDADO
# ============================================================
def parse_historial_validado(file_bytes):
    try:
        df = pd.read_excel(io.BytesIO(file_bytes), sheet_name='Resumen', header=9)
        fechas = [c for c in df.columns if hasattr(c, 'year')]
        df_clean = df.dropna(subset=[df.columns[0]])
        df_clean = df_clean[pd.to_numeric(df_clean[df.columns[0]], errors='coerce').notna()]
        rows = []
        for _, row in df_clean.iterrows():
            id_prod      = int(row[df.columns[0]])
            producto     = clean_text(row[df.columns[1]])
            presentacion = clean_text(row[df.columns[2]])
            for fecha in fechas:
                try:
                    precio = float(row[fecha])
                    if precio > 0:
                        semana = fecha.isocalendar()[1]
                        anio   = fecha.year
                        rows.append({
                            "semana":       f"{anio}-W{semana:02d}",
                            "provincia":    "Santo Domingo",
                            "supermercado": "Promedio Validado",
                            "categoria":    "Referencia",
                            "id_producto":  id_prod,
                            "producto":     producto,
                            "presentacion": presentacion,
                            "precio":       precio,
                        })
                except Exception:
                    pass
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame()


# ============================================================
# LECTOR - RESUMEN POR SUPERMERCADO
# ============================================================
def parse_resumen_supermercado(file_bytes):
    try:
        df = pd.read_excel(io.BytesIO(file_bytes), sheet_name='Resumen por supermercado', header=None)
        results = []

        def leer_bloque(fila_header):
            header = df.iloc[fila_header].tolist()
            fecha = None
            supermercados = []
            for val in header:
                if hasattr(val, 'year'):
                    fecha = val
                elif isinstance(val, str) and val.strip() not in ['No.', 'nan', '']:
                    supermercados.append(val.strip())
                elif isinstance(val, float) and not pd.isna(val) and val > 100:
                    supermercados.append(str(int(val)))

            rows = []
            for i in range(fila_header + 1, df.shape[0]):
                row = df.iloc[i].tolist()
                if pd.isna(row[0]) or str(row[0]) == 'nan':
                    break
                if not isinstance(row[0], (int, float)):
                    break
                try:
                    id_prod = int(row[0])
                except Exception:
                    break
                producto     = clean_text(row[1])
                presentacion = clean_text(row[2])
                semana_lbl   = f"{fecha.year}-W{fecha.isocalendar()[1]:02d}"
                for j, sup in enumerate(supermercados):
                    try:
                        precio = float(row[3 + j])
                        if precio > 0:
                            rows.append({
                                "semana":       semana_lbl,
                                "id_producto":  id_prod,
                                "producto":     producto,
                                "presentacion": presentacion,
                                "supermercado": sup,
                                "precio":       precio
                            })
                    except Exception:
                        pass
            return pd.DataFrame(rows)

        # Encontrar filas con headers
        for i in range(df.shape[0]):
            row = df.iloc[i].tolist()
            if any(hasattr(x, 'year') for x in row):
                bloque = leer_bloque(i)
                if not bloque.empty:
                    results.append(bloque)

        if results:
            return pd.concat(results, ignore_index=True)
        return pd.DataFrame()
    except Exception:
        return pd.DataFrame()


# ============================================================
# LECTOR - TABLA 21 (PRODUCTOS CLAVE)
# ============================================================
def parse_tabla21(file_bytes):
    try:
        df = pd.read_excel(io.BytesIO(file_bytes), sheet_name='Tabla 21', header=None)
        rows = []
        fecha_ant = None
        fecha_act = None

        # Encontrar fila de header
        header_fila = None
        for i in range(df.shape[0]):
            row = df.iloc[i].dropna().tolist()
            if len(row) >= 4 and 'Producto' in str(row):
                header_fila = i
                # Extraer fechas
                for val in row:
                    if hasattr(val, 'year'):
                        if fecha_ant is None:
                            fecha_ant = val
                        else:
                            fecha_act = val
                break

        if header_fila is None:
            return pd.DataFrame()

        for i in range(header_fila + 1, df.shape[0]):
            row = df.iloc[i].tolist()
            non_nan = [x for x in row if str(x) != 'nan']
            if len(non_nan) < 4:
                continue
            # Saltar fila de nota final
            if isinstance(non_nan[0], str) and 'considerará' in non_nan[0]:
                continue
            try:
                # Puede haber una columna extra al inicio
                if isinstance(non_nan[0], str) and len(non_nan[0]) < 3:
                    non_nan = non_nan[1:]
                producto     = clean_text(non_nan[0])
                presentacion = clean_text(non_nan[1])
                precio_ant   = float(non_nan[2])
                precio_act   = float(non_nan[3])
                var_abs      = float(non_nan[4]) if len(non_nan) > 4 else precio_act - precio_ant
                var_pct      = float(non_nan[5]) if len(non_nan) > 5 else (var_abs / precio_ant)
                rows.append({
                    "producto":      producto,
                    "presentacion":  presentacion,
                    "precio_sem_ant": precio_ant,
                    "precio_sem_act": precio_act,
                    "variacion_abs":  var_abs,
                    "variacion_pct":  var_pct * 100 if abs(var_pct) < 1 else var_pct,
                    "fecha_ant":     str(fecha_ant.date()) if fecha_ant else "",
                    "fecha_act":     str(fecha_act.date()) if fecha_act else "",
                })
            except Exception:
                pass

        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame()
