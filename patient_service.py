"""Servicio de gestión de pacientes y mediciones para IA Médica Asistencial.

Este módulo implementa la lógica de negocio para registrar, consultar y
actualizar información de pacientes y sus mediciones clínicas.
Todas las operaciones son con fines académicos y de simulación.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from models import Patient, Measurement, Evaluation, Alert
from database import (
    get_connection,
    insert_patient,
    get_patient_by_id,
    get_patient_by_code,
    get_all_patients,
    update_patient_status,
    insert_measurement,
    get_measurements_for_patient,
    get_latest_measurement,
    get_evaluations_for_patient,
    get_latest_evaluation,
    get_alerts_for_patient,
)
from validation import (
    validate_patient_code,
    validate_arrival_datetime,
    validate_measurement,
    sanitize_string,
    validate_administrative_status,
    ValidationResult,
)
from config import DATE_FORMAT, ADMIN_STATUSES, ALERT_STATUS_PENDING


def generate_patient_code() -> str:
    """Genera un código ficticio único para el paciente con formato 'PAC-XXXXXXXX'.
    
    Returns:
        str: Código alfanumérico ficticio de paciente.
    """
    return f"PAC-{uuid.uuid4().hex[:8].upper()}"


def compute_wait_time(arrival_at: str) -> float:
    """Calcula el tiempo de espera acumulado en minutos desde la llegada hasta el momento actual.

    Args:
        arrival_at: Cadena de fecha y hora en formato ISO 8601.

    Returns:
        float: Minutos de espera transcurridos (mínimo 0.0).
    """
    if not arrival_at:
        return 0.0
    try:
        clean_arrival = str(arrival_at).replace("Z", "+00:00")
        arrival_dt = datetime.fromisoformat(clean_arrival)

        if arrival_dt.tzinfo is not None:
            now_dt = datetime.now(timezone.utc)
        else:
            now_dt = datetime.now()

        diff_seconds = (now_dt - arrival_dt).total_seconds()
        return max(0.0, round(diff_seconds / 60.0, 1))
    except (ValueError, TypeError):
        return 0.0


def _enrich_patient_with_conn(patient: Patient, conn: Any) -> Patient:
    """Enriquece un objeto Patient con campos calculados reutilizando una conexión existente."""
    patient.wait_time_minutes = compute_wait_time(patient.arrival_at)

    alerts = get_alerts_for_patient(conn, patient.id, status_filter=ALERT_STATUS_PENDING)
    patient.pending_alerts_count = len(alerts)

    latest_eval = get_latest_evaluation(conn, patient.id)
    if latest_eval:
        patient.last_evaluation_score = latest_eval.score
        patient.last_evaluation_at = latest_eval.evaluated_at
    else:
        patient.last_evaluation_score = None
        patient.last_evaluation_at = None

    return patient


def enrich_patient(patient: Patient, db_path: Optional[str] = None) -> Patient:
    """Agrega campos computados a un objeto paciente (espera, alertas y última evaluación).

    Args:
        patient: Objeto Patient a enriquecer.
        db_path: Ruta opcional a la base de datos SQLite.

    Returns:
        Patient: El mismo objeto paciente con sus campos computados actualizados.
    """
    if patient is None or patient.id is None:
        return patient

    conn = get_connection(db_path)
    try:
        return _enrich_patient_with_conn(patient, conn)
    finally:
        conn.close()


def register_patient(
    patient_code: Optional[str] = None,
    arrival_at: Optional[str] = None,
    is_simulated: bool = False,
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Registra un nuevo paciente ficticio en el sistema.

    Args:
        patient_code: Código del paciente. Si es None o vacío, se auto-genera.
        arrival_at: Fecha y hora de llegada (ISO 8601). Si es None, se usa el momento actual.
        is_simulated: Indica si el paciente proviene de la simulación o de ingreso manual.
        db_path: Ruta opcional a la base de datos SQLite.

    Returns:
        Dict[str, Any]: Diccionario con las claves 'success', 'patient_id', 'patient_code', 'errors'.
    """
    errors: List[str] = []

    # Validar o generar código
    if patient_code is not None and str(patient_code).strip():
        code_to_use = sanitize_string(str(patient_code).strip())
        val_code = validate_patient_code(code_to_use)
        if not val_code.is_valid:
            errors.extend(val_code.errors)
    else:
        code_to_use = generate_patient_code()

    # Validar o asignar fecha de llegada
    if arrival_at is not None and str(arrival_at).strip():
        arrival_to_use = sanitize_string(str(arrival_at).strip())
        val_arrival = validate_arrival_datetime(arrival_to_use)
        if not val_arrival.is_valid:
            errors.extend(val_arrival.errors)
    else:
        arrival_to_use = datetime.now().isoformat()

    if errors:
        return {
            "success": False,
            "patient_id": None,
            "patient_code": code_to_use,
            "errors": errors,
        }

    conn = get_connection(db_path)
    try:
        # Verificar que el código no exista previamente
        existing = get_patient_by_code(conn, code_to_use)
        if existing is not None:
            return {
                "success": False,
                "patient_id": None,
                "patient_code": code_to_use,
                "errors": [f"El código de paciente '{code_to_use}' ya se encuentra registrado."],
            }

        now_iso = datetime.now().isoformat()
        patient = Patient(
            id=None,
            patient_code=code_to_use,
            created_at=now_iso,
            arrival_at=arrival_to_use,
            administrative_status="en_espera",
            is_simulated=is_simulated,
            wait_time_minutes=0.0,
            pending_alerts_count=0,
            last_evaluation_score=None,
            last_evaluation_at=None,
        )

        patient_id = insert_patient(conn, patient)
        return {
            "success": True,
            "patient_id": patient_id,
            "patient_code": code_to_use,
            "errors": [],
        }
    except Exception:
        return {
            "success": False,
            "patient_id": None,
            "patient_code": code_to_use,
            "errors": ["Ocurrió un error interno al registrar el paciente."],
        }
    finally:
        conn.close()


def get_patient(patient_id: int, db_path: Optional[str] = None) -> Optional[Patient]:
    """Obtiene un paciente por su identificador único junto con sus campos computados.

    Args:
        patient_id: Identificador numérico del paciente.
        db_path: Ruta opcional a la base de datos SQLite.

    Returns:
        Optional[Patient]: Objeto paciente enriquecido o None si no existe.
    """
    conn = get_connection(db_path)
    try:
        patient = get_patient_by_id(conn, patient_id)
        if patient is None:
            return None
        return _enrich_patient_with_conn(patient, conn)
    finally:
        conn.close()


def get_patient_list(
    status_filter: Optional[str] = None,
    include_simulated: bool = True,
    db_path: Optional[str] = None,
) -> List[Patient]:
    """Obtiene la lista de pacientes con sus campos computados actualizados.

    Args:
        status_filter: Filtro por estado administrativo ('en_espera', 'en_atencion', etc.).
        include_simulated: Si es True, incluye registros generados por simulación.
        db_path: Ruta opcional a la base de datos SQLite.

    Returns:
        List[Patient]: Lista de pacientes con datos calculados.
    """
    conn = get_connection(db_path)
    try:
        patients = get_all_patients(
            conn, status_filter=status_filter, include_simulated=include_simulated
        )
        for patient in patients:
            _enrich_patient_with_conn(patient, conn)
        return patients
    finally:
        conn.close()


def register_measurement(
    patient_id: int,
    measurement_data: Dict[str, Any],
    source: str = "manual",
    db_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Registra una nueva medición clínica para un paciente.

    Args:
        patient_id: Identificador del paciente.
        measurement_data: Diccionario con los parámetros clínicos medidos.
        source: Origen de la medición ('manual' o 'simulacion').
        db_path: Ruta opcional a la base de datos SQLite.

    Returns:
        Dict[str, Any]: Diccionario con 'success', 'measurement_id', 'errors', 'warnings'.
    """
    val_res = validate_measurement(measurement_data)
    if not val_res.is_valid:
        return {
            "success": False,
            "measurement_id": None,
            "errors": val_res.errors,
            "warnings": val_res.warnings,
        }

    cleaned = val_res.cleaned_data
    conn = get_connection(db_path)
    try:
        patient = get_patient_by_id(conn, patient_id)
        if patient is None:
            return {
                "success": False,
                "measurement_id": None,
                "errors": ["El paciente especificado no existe en el sistema."],
                "warnings": val_res.warnings,
            }

        rec_at = cleaned.get("recorded_at") or datetime.now().isoformat()
        # Los campos ausentes se conservan como None: no se sustituyen por valores
        # "normales", para que la evaluación pueda declararse incompleta.
        measurement = Measurement(
            id=None,
            patient_id=patient_id,
            recorded_at=rec_at,
            respiratory_rate=cleaned.get("respiratory_rate"),
            oxygen_saturation=cleaned.get("oxygen_saturation"),
            supplemental_oxygen=cleaned.get("supplemental_oxygen"),
            systolic_blood_pressure=cleaned.get("systolic_blood_pressure"),
            heart_rate=cleaned.get("heart_rate"),
            temperature=cleaned.get("temperature"),
            consciousness_status=cleaned.get("consciousness_status"),
            measurement_source=source,
            spo2_scale=cleaned.get("spo2_scale", 1),
        )

        measurement_id = insert_measurement(conn, measurement)
        return {
            "success": True,
            "measurement_id": measurement_id,
            "measurement": measurement,
            "errors": [],
            "warnings": val_res.warnings,
        }
    except Exception:
        return {
            "success": False,
            "measurement_id": None,
            "errors": ["Error interno al registrar la medición clínica."],
            "warnings": val_res.warnings,
        }
    finally:
        conn.close()


def get_patient_history(
    patient_id: int, db_path: Optional[str] = None
) -> Dict[str, Any]:
    """Obtiene el historial completo de un paciente (datos, mediciones, evaluaciones y alertas).

    Args:
        patient_id: Identificador del paciente.
        db_path: Ruta opcional a la base de datos SQLite.

    Returns:
        Dict[str, Any]: Diccionario con 'patient', 'measurements', 'evaluations', 'alerts'.
    """
    conn = get_connection(db_path)
    try:
        patient = get_patient_by_id(conn, patient_id)
        if patient is not None:
            _enrich_patient_with_conn(patient, conn)

        measurements = get_measurements_for_patient(conn, patient_id)
        evaluations = get_evaluations_for_patient(conn, patient_id)
        alerts = get_alerts_for_patient(conn, patient_id)

        return {
            "patient": patient,
            "measurements": measurements,
            "evaluations": evaluations,
            "alerts": alerts,
        }
    finally:
        conn.close()


def update_status(
    patient_id: int, new_status: str, db_path: Optional[str] = None
) -> Dict[str, Any]:
    """Actualiza el estado administrativo del paciente.

    Args:
        patient_id: Identificador del paciente.
        new_status: Nuevo estado ('en_espera', 'en_atencion', 'atendido', 'alta').
        db_path: Ruta opcional a la base de datos SQLite.

    Returns:
        Dict[str, Any]: Diccionario con 'success' y 'errors'.
    """
    val_status = validate_administrative_status(new_status)
    if not val_status.is_valid:
        return {"success": False, "errors": val_status.errors}

    cleaned_status = val_status.cleaned_data.get("administrative_status", new_status)
    conn = get_connection(db_path)
    try:
        patient = get_patient_by_id(conn, patient_id)
        if patient is None:
            return {
                "success": False,
                "errors": ["El paciente especificado no existe en el sistema."],
            }

        success = update_patient_status(conn, patient_id, cleaned_status)
        return {
            "success": success,
            "errors": [] if success else ["No se pudo actualizar el estado en la base de datos."],
        }
    except Exception:
        return {
            "success": False,
            "errors": ["Error interno al actualizar el estado administrativo."],
        }
    finally:
        conn.close()
