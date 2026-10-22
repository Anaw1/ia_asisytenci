"""Gestión y priorización de la cola administrativa de espera.

Este módulo implementa el ordenamiento administrativo simulado para la sala de espera
en el prototipo IA Médica Asistencial.

AVISO CLÍNICO OBLIGATORIO:
- La puntuación de prioridad aquí calculada es una herramienta estrictamente
  ADMINISTRATIVA y SIMULADA para optimizar el flujo de trabajo en el prototipo.
- NO constituye una decisión médica, NO es un triaje clínico (Categorías I-V como Manchester o ESI)
  y NUNCA debe sustituir el juicio clínico ni la valoración profesional presencial.
- Ningún paciente debe ser desestimado ni despriorizado arbitrariamente basándose
  únicamente en un puntaje numérico bajo.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple

from models import Patient, QueueEntry, Evaluation, Alert
from database import (
    get_connection,
    get_patients_en_espera,
    get_latest_evaluation,
    get_alerts_for_patient,
    get_all_pending_alerts,
)
from patient_service import compute_wait_time, enrich_patient
from config import (
    PRIORITY_RULES,
    ALERT_STATUS_PENDING,
    ALERT_TYPES,
    NEWS2_HIGH_SCORE_THRESHOLD,
    NEWS2_MEDIUM_SCORE_RANGE,
    TRIAGE_LEVELS,
    DATE_FORMAT,
)


def _get_alert_count(entry: QueueEntry) -> int:
    """Obtiene de manera segura el número de alertas pendientes de una entrada."""
    if isinstance(entry.pending_alerts, list):
        return len(entry.pending_alerts)
    try:
        return int(entry.pending_alerts)
    except (TypeError, ValueError):
        return 0


def calculate_priority_score(
    patient: Patient,
    evaluation: Optional[Evaluation],
    pending_alerts: List[Alert],
    wait_time_minutes: float,
) -> Tuple[float, List[str]]:
    """Calcula la puntuación de prioridad administrativa y genera los motivos explicativos.

    Esta ponderación es un mecanismo de ordenamiento administrativo para la cola simulada.
    Se compone de factores transparentes y configurables:
    1. Alertas clínicas pendientes que requieren revisión (+100 pts por cada una).
    2. Evaluación NEWS2:
       - Puntaje >= 7 (alto riesgo): +80 pts
       - Puntaje 5-6 (riesgo medio): +60 pts
       - Gatillo rojo individual (parámetro = 3): +40 pts
       - Puntaje 1-4 (riesgo bajo): +20 pts
    3. Evaluación incompleta o ausente (+40 pts por necesidad de toma de datos).
    4. Tiempo de espera transcurrido (+1 pto por cada 10 minutos de espera).

    Args:
        patient: Objeto Patient evaluado.
        evaluation: Última evaluación clínica registrada (o None).
        pending_alerts: Lista de alertas pendientes asociadas al paciente.
        wait_time_minutes: Minutos acumulados en espera.

    Returns:
        Tuple[float, List[str]]: Puntuación calculada y lista de razones explicativas en español.
    """
    score: float = 0.0
    reasons: List[str] = []

    # 1. Puntuación / Nivel de triaje clínico profesional inicial (Niveles I a V)
    triage_lvl = getattr(patient, "triage_level", None) if patient else None
    if triage_lvl is not None and triage_lvl in TRIAGE_LEVELS:
        tinfo = TRIAGE_LEVELS[triage_lvl]
        t_weight = tinfo.get("priority_weight", 0.0)
        t_short = tinfo.get("short_label", f"Nivel {triage_lvl}")
        if t_weight > 0.0:
            score += t_weight
            reasons.append(
                f"+{t_weight:.0f} pts: Triaje Clínico Inicial {t_short} "
                f"(prioridad médica presencial asignada al ingreso)"
            )
        else:
            reasons.append(f"0 pts: Triaje Clínico Inicial {t_short} (consulta no urgente)")

    # 2. Alertas pendientes que requieren revisión asistencial
    for alert in pending_alerts:
        alert_info = ALERT_TYPES.get(alert.alert_type, {})
        requires_review = alert_info.get("requires_review", True)
        if requires_review:
            score += 100.0
            label = alert_info.get("label", alert.alert_type)
            reasons.append(f"+100 pts: Alerta clínica pendiente de revisión ({label})")

    # 2. Evaluación clínica NEWS2 o necesidad de datos
    if evaluation is None or evaluation.completeness_status == "incompleto" or evaluation.score is None:
        score += 40.0
        reasons.append(
            "+40 pts: Evaluación NEWS2 incompleta o pendiente (requiere registro de constantes fisiológicas)"
        )
    else:
        news2_score = evaluation.score
        if news2_score >= NEWS2_HIGH_SCORE_THRESHOLD:
            score += 80.0
            reasons.append(
                f"+80 pts: NEWS2 en nivel alto ({news2_score} pts - riesgo clínico alto de deterioro)"
            )
        elif news2_score >= NEWS2_MEDIUM_SCORE_RANGE[0]:
            score += 60.0
            reasons.append(
                f"+60 pts: NEWS2 en nivel medio ({news2_score} pts - riesgo clínico medio)"
            )
        elif evaluation.risk_level == "low_medium":
            score += 40.0
            reasons.append(
                f"+40 pts: NEWS2 con gatillo rojo individual ({news2_score} pts totales, parámetro individual = 3)"
            )
        elif 1 <= news2_score <= 4:
            score += 20.0
            reasons.append(
                f"+20 pts: NEWS2 en nivel bajo ({news2_score} pts)"
            )
        else:
            reasons.append("0 pts: NEWS2 basal normal (0 pts)")

    # 3. Contribución por tiempo de espera (+1 punto por cada 10 minutos)
    wait_points = round(wait_time_minutes / 10.0, 1)
    if wait_points > 0.0:
        score += wait_points
        reasons.append(
            f"+{wait_points:.1f} pts: Tiempo acumulado en sala de espera ({wait_time_minutes:.0f} min, +1 pto/10 min)"
        )

    if not reasons:
        reasons.append("Puntaje base de ingreso sin factores de alerta adicionales")

    return round(score, 1), reasons


def build_queue(
    db_path: Optional[str] = None, include_simulated: bool = True
) -> List[QueueEntry]:
    """Construye y ordena la cola administrativa de pacientes en espera.

    1. Obtiene los pacientes con estado administrativo 'en_espera'.
    2. Recopila la última evaluación, alertas pendientes y tiempo de espera de cada paciente.
    3. Calcula la puntuación de prioridad y motivos correspondientes.
    4. Ordena descendentemente por puntuación de prioridad y tiempo de espera.
    5. Asigna las posiciones correlativas (1, 2, 3...).

    AVISO: La cola resultante es una sugerencia administrativa simulada
    y NO reemplaza la clasificación clínica ni el triaje médico.

    Args:
        db_path: Ruta opcional a la base de datos SQLite.
        include_simulated: Si es True, incluye registros generados por simulación.

    Returns:
        List[QueueEntry]: Lista de entradas de la cola debidamente ordenadas.
    """
    conn = get_connection(db_path)
    entries_data: List[Dict[str, Any]] = []

    try:
        patients = get_patients_en_espera(conn, include_simulated=include_simulated)
        for patient in patients:
            latest_eval = get_latest_evaluation(conn, patient.id)
            pending_alerts = get_alerts_for_patient(
                conn, patient.id, status_filter=ALERT_STATUS_PENDING
            )
            wait_time = compute_wait_time(patient.arrival_at)

            # Actualizar campos calculados del paciente
            patient.wait_time_minutes = wait_time
            patient.pending_alerts_count = len(pending_alerts)
            patient.last_evaluation_score = latest_eval.score if latest_eval else None
            patient.last_evaluation_at = latest_eval.evaluated_at if latest_eval else None

            score, reasons = calculate_priority_score(
                patient, latest_eval, pending_alerts, wait_time
            )

            entries_data.append({
                "patient": patient,
                "priority_score": score,
                "reasons": reasons,
                "pending_alerts": pending_alerts,
                "last_evaluation": latest_eval,
                "wait_time_minutes": wait_time,
            })
    finally:
        conn.close()

    # Ordenamiento: prioridad descendente, tiempo de espera descendente, fecha de llegada ascendente
    entries_data.sort(
        key=lambda item: (
            item["priority_score"],
            item["wait_time_minutes"],
            -(datetime.fromisoformat(item["patient"].arrival_at.replace("Z", "+00:00")).timestamp()
              if item["patient"].arrival_at else 0.0),
        ),
        reverse=True,
    )

    now_iso = datetime.now().isoformat()
    queue_entries: List[QueueEntry] = []

    for index, data in enumerate(entries_data, start=1):
        queue_entries.append(
            QueueEntry(
                position=index,
                patient=data["patient"],
                priority_score=data["priority_score"],
                reasons=data["reasons"],
                pending_alerts=len(data["pending_alerts"]),
                last_evaluation=data["last_evaluation"],
                wait_time_minutes=data["wait_time_minutes"],
                last_updated=now_iso,
            )
        )

    return queue_entries


def get_queue_summary(queue: List[QueueEntry]) -> Dict[str, Any]:
    """Genera estadísticas consolidadas del estado actual de la cola de espera.

    Args:
        queue: Lista de entradas QueueEntry de la cola.

    Returns:
        Dict[str, Any]: Diccionario con total_patients, avg_wait_time, max_wait_time,
                        patients_with_alerts, patients_with_high_score, last_updated.
    """
    total = len(queue)
    if total > 0:
        avg_wait = round(sum(e.wait_time_minutes for e in queue) / total, 1)
        max_wait = round(max((e.wait_time_minutes for e in queue), default=0.0), 1)
    else:
        avg_wait = 0.0
        max_wait = 0.0

    with_alerts = sum(1 for e in queue if _get_alert_count(e) > 0)
    with_high_score = sum(
        1
        for e in queue
        if e.last_evaluation is not None
        and e.last_evaluation.score is not None
        and e.last_evaluation.score >= NEWS2_HIGH_SCORE_THRESHOLD
    )

    return {
        "total_patients": total,
        "avg_wait_time": avg_wait,
        "max_wait_time": max_wait,
        "patients_with_alerts": with_alerts,
        "patients_with_high_score": with_high_score,
        "last_updated": datetime.now().isoformat(),
    }


def explain_position(entry: QueueEntry) -> str:
    """Genera una explicación en español que sustenta la posición del paciente en la cola.

    Args:
        entry: Entrada individual de la cola.

    Returns:
        str: Explicación transparente de la ordenación administrativa.
    """
    reasons_str = "; ".join(entry.reasons)
    return (
        f"Posición #{entry.position}: Paciente {entry.patient.patient_code if entry.patient else 'N/D'} "
        f"con puntuación de prioridad administrativa {entry.priority_score:.1f}. "
        f"Factores determinantes: {reasons_str}. "
        f"[Nota: Esta ordenación es administrativa y simulada; no sustituye la clasificación clínica ni el juicio profesional]."
    )


def format_queue_for_display(queue: List[QueueEntry]) -> List[Dict[str, Any]]:
    """Formatea las entradas de la cola para su presentación visual en la interfaz de usuario.

    Args:
        queue: Lista de entradas QueueEntry.

    Returns:
        List[Dict[str, Any]]: Lista de registros adecuada para su visualización tabular.
    """
    display_rows: List[Dict[str, Any]] = []
    for entry in queue:
        eval_text = "Sin evaluación"
        if entry.last_evaluation is not None:
            if (
                entry.last_evaluation.completeness_status == "incompleto"
                or entry.last_evaluation.score is None
            ):
                eval_text = "Incompleta"
            else:
                risk = entry.last_evaluation.risk_level or "N/D"
                eval_text = f"NEWS2: {entry.last_evaluation.score} ({risk})"

        p = entry.patient
        patient_code = p.patient_code if p else "N/D"
        patient_name = (p.full_name or p.name) if p else "N/D"

        triage_text = "N/D"
        if p and p.triage_level:
            tinfo = TRIAGE_LEVELS.get(p.triage_level, {})
            triage_text = tinfo.get("short_label", f"Nivel {p.triage_level}")

        symptoms_text = p.symptoms if (p and p.symptoms) else "Sin síntomas registrados"
        dx_text = p.initial_diagnosis if (p and p.initial_diagnosis) else "Pendiente de diagnóstico"

        display_rows.append({
            "Posición": entry.position,
            "Código": patient_code,
            "Nombre": patient_name,
            "Triaje": triage_text,
            "Tiempo espera": f"{entry.wait_time_minutes:.0f} min",
            "Última evaluación": eval_text,
            "Alertas pendientes": _get_alert_count(entry),
            "Síntomas": symptoms_text,
            "Diagnóstico inicial": dx_text,
            "Puntuación prioridad": round(entry.priority_score, 1),
            "Razón del orden": "; ".join(entry.reasons),
        })

    return display_rows
