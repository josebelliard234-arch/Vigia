from datetime import datetime

_MESES_ABREV = ["ene", "feb", "mar", "abr", "may", "jun",
                "jul", "ago", "sep", "oct", "nov", "dic"]


def semana_label_a_datetime(lbl):
    """Convierte 2026-W22 al primer dia (lunes) de esa semana ISO."""
    try:
        anio, wk = int(lbl[:4]), int(lbl[6:])
        return datetime.fromisocalendar(anio, wk, 1)
    except Exception:
        return None


def fmt_sem(lbl, modo="corta"):
    """
    Formatea una semana ISO ('2026-W23') en texto legible.
      corta: '1-7 jun'              -> tarjetas, filtros, titulos, columnas
      larga: '1-7 jun 2026'         -> notas, tooltips, captions
    Casos especiales:
      Cruza mes:  '30 may-5 jun'  /  '30 may-5 jun 2026'
      Cruza anio:  '29 dic 2025-4 ene 2026'  (siempre incluye ambos anios)
    """
    try:
        anio, wk = int(lbl[:4]), int(lbl[6:])
        lunes   = datetime.fromisocalendar(anio, wk, 1)
        domingo = datetime.fromisocalendar(anio, wk, 7)
        ml = _MESES_ABREV[lunes.month - 1]
        md = _MESES_ABREV[domingo.month - 1]
        if lunes.year != domingo.year:
            return f"{lunes.day} {ml} {lunes.year}-{domingo.day} {md} {domingo.year}"
        if lunes.month != domingo.month:
            base = f"{lunes.day} {ml}-{domingo.day} {md}"
            return f"{base} {lunes.year}" if modo == "larga" else base
        base = f"{lunes.day}-{domingo.day} {ml}"
        return f"{base} {lunes.year}" if modo == "larga" else base
    except Exception:
        return lbl


def ordenar_semanas_iso(labels):
    """Ordena etiquetas ISO tipo 2026-W23 de forma cronologica para el eje X."""
    unicas = []
    for lbl in labels:
        if lbl and lbl not in unicas:
            unicas.append(lbl)

    return sorted(
        unicas,
        key=lambda lbl: semana_label_a_datetime(lbl) or datetime.max
    )
