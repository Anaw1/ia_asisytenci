"""Módulo de persistencia y base de datos para el prototipo IA Médica Asistencial.

Gestiona conexiones SQLite (con WAL mode y claves foráneas activadas),
inicialización de esquemas e índices, y operaciones CRUD completas
con consultas parametrizadas para todas las entidades.
"""

from datetime import datetime, timedelta
import logging
import os
import sqlite3
from typing import Any, List, Optional

from config import (
    ALERT_STATUS_ACKNOWLEDGED,
    ALERT_STATUS_PENDING,
    DATE_FORMAT,
    DB_PATH,
)
from models import (
    Alert,
    Evaluation,
    Measurement,
    Patient,
    SimulationEvent,
)

logger = logging.getLogger(__name__)


def get_db_path() -> str:
    """Retorna la ruta absoluta al archivo de base de datos SQLite."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(base_dir, DB_PATH))


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Obtiene una conexión a SQLite configurada con WAL mode, claves foráneas y Row factory."""
    path = db_path if db_path is not None else get_db_path()
    db_dir = os.path.dirname(path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Crea todas las tablas e índices si no existen. No elimina datos existentes."""
    conn = get_connection(db_path)
    try:
        with conn:
            cursor = conn.cursor()

            # Tabla patients
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_code TEXT NOT NULL UNIQUE,
                full_name TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                arrival_at TEXT NOT NULL,
                administrative_status TEXT NOT NULL DEFAULT 'en_espera',
                is_simulated INTEGER NOT NULL DEFAULT 0,
                symptoms TEXT NOT NULL DEFAULT '',
                initial_diagnosis TEXT NOT NULL DEFAULT '',
                triage_level INTEGER DEFAULT NULL
            );
            """)
            # Migración segura: agregar nuevas columnas a tablas de pacientes existentes sin pérdida de datos.
            cursor.execute("PRAGMA table_info(patients);")
            patient_cols = [row[1] for row in cursor.fetchall()]
            if "full_name" not in patient_cols:
                cursor.execute("ALTER TABLE patients ADD COLUMN full_name TEXT NOT NULL DEFAULT '';")
            if "symptoms" not in patient_cols:
                cursor.execute("ALTER TABLE patients ADD COLUMN symptoms TEXT NOT NULL DEFAULT '';")
            if "initial_diagnosis" not in patient_cols:
                cursor.execute("ALTER TABLE patients ADD COLUMN initial_diagnosis TEXT NOT NULL DEFAULT '';")
            if "triage_level" not in patient_cols:
                cursor.execute("ALTER TABLE patients ADD COLUMN triage_level INTEGER DEFAULT NULL;")

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_patients_status ON patients(administrative_status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_patients_simulated ON patients(is_simulated);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_patients_triage ON patients(triage_level);")

            # Tabla measurements
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS measurements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                recorded_at TEXT NOT NULL,
                respiratory_rate INTEGER,
                oxygen_saturation INTEGER,
                supplemental_oxygen INTEGER,  -- 0 o 1
                systolic_blood_pressure INTEGER,
                heart_rate INTEGER,
                temperature REAL,
                consciousness_status TEXT,
                measurement_source TEXT NOT NULL DEFAULT 'manual',
                spo2_scale INTEGER NOT NULL DEFAULT 1 CHECK (spo2_scale IN (1, 2)),
                FOREIGN KEY (patient_id) REFERENCES patients(id)
            );
            """)
            # Migración segura: bases creadas antes de añadir spo2_scale conservan sus datos.
            cursor.execute("PRAGMA table_info(measurements);")
            existing_columns = [row[1] for row in cursor.fetchall()]
            if "spo2_scale" not in existing_columns:
                cursor.execute(
                    "ALTER TABLE measurements ADD COLUMN spo2_scale INTEGER NOT NULL DEFAULT 1 "
                    "CHECK (spo2_scale IN (1, 2));"
                )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_measurements_patient ON measurements(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_measurements_recorded ON measurements(recorded_at);")

            # Tabla evaluations
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                measurement_id INTEGER NOT NULL,
                evaluated_at TEXT NOT NULL,
                scoring_method TEXT NOT NULL,
                score INTEGER,
                completeness_status TEXT NOT NULL,
                explanation TEXT NOT NULL DEFAULT '',
                risk_level TEXT,
                parameter_scores TEXT,  -- JSON
                FOREIGN KEY (patient_id) REFERENCES patients(id),
                FOREIGN KEY (measurement_id) REFERENCES measurements(id)
            );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_evaluations_patient ON evaluations(patient_id);")

            # Tabla alerts
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                evaluation_id INTEGER,
                created_at TEXT NOT NULL,
                alert_type TEXT NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pendiente',
                acknowledged_at TEXT,
                rule_name TEXT NOT NULL DEFAULT '',
                trigger_data TEXT,  -- JSON
                FOREIGN KEY (patient_id) REFERENCES patients(id),
                FOREIGN KEY (evaluation_id) REFERENCES evaluations(id)
            );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_patient ON alerts(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);")

            # Tabla simulation_events
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS simulation_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                simulation_id TEXT NOT NULL,
                patient_id INTEGER,
                event_at TEXT NOT NULL,
                event_type TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                event_data TEXT,  -- JSON
                FOREIGN KEY (patient_id) REFERENCES patients(id)
            );
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sim_events_simulation ON simulation_events(simulation_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sim_events_patient ON simulation_events(patient_id);")

        logger.info("Base de datos inicializada exitosamente.")
    except Exception as err:
        logger.error("Error al inicializar la base de datos: %s", err)
        raise
    finally:
        conn.close()


# ==============================================================================
# CONVERTIDORES INTERNOS (ROW -> MODEL)
# ==============================================================================

def _row_to_patient(row: sqlite3.Row) -> Patient:
    """Convierte un registro de SQLite a objeto Patient."""
    keys = row.keys()
    triage_raw = row['triage_level'] if 'triage_level' in keys else None
    return Patient(
        id=row['id'],
        patient_code=row['patient_code'],
        full_name=row['full_name'] if 'full_name' in keys and row['full_name'] is not None else '',
        created_at=row['created_at'],
        arrival_at=row['arrival_at'],
        administrative_status=row['administrative_status'],
        is_simulated=bool(row['is_simulated']),
        symptoms=row['symptoms'] if 'symptoms' in keys and row['symptoms'] is not None else '',
        initial_diagnosis=row['initial_diagnosis'] if 'initial_diagnosis' in keys and row['initial_diagnosis'] is not None else '',
        triage_level=int(triage_raw) if triage_raw is not None else None,
    )


def _row_to_measurement(row: sqlite3.Row) -> Measurement:
    """Convierte un registro de SQLite a objeto Measurement."""
    supp_ox = row['supplemental_oxygen']
    return Measurement(
        id=row['id'],
        patient_id=row['patient_id'],
        recorded_at=row['recorded_at'],
        respiratory_rate=row['respiratory_rate'],
        oxygen_saturation=row['oxygen_saturation'],
        supplemental_oxygen=bool(supp_ox) if supp_ox is not None else None,
        systolic_blood_pressure=row['systolic_blood_pressure'],
        heart_rate=row['heart_rate'],
        temperature=row['temperature'],
        consciousness_status=row['consciousness_status'],
        measurement_source=row['measurement_source'],
        spo2_scale=int(row['spo2_scale']) if 'spo2_scale' in row.keys() and row['spo2_scale'] is not None else 1,
    )


def _row_to_evaluation(row: sqlite3.Row) -> Evaluation:
    """Convierte un registro de SQLite a objeto Evaluation."""
    return Evaluation(
        id=row['id'],
        patient_id=row['patient_id'],
        measurement_id=row['measurement_id'],
        evaluated_at=row['evaluated_at'],
        scoring_method=row['scoring_method'],
        score=row['score'],
        completeness_status=row['completeness_status'],
        explanation=row['explanation'] if row['explanation'] is not None else '',
        risk_level=row['risk_level'],
        parameter_scores=row['parameter_scores'],
    )


def _row_to_alert(row: sqlite3.Row) -> Alert:
    """Convierte un registro de SQLite a objeto Alert."""
    return Alert(
        id=row['id'],
        patient_id=row['patient_id'],
        evaluation_id=row['evaluation_id'],
        created_at=row['created_at'],
        alert_type=row['alert_type'],
        reason=row['reason'],
        status=row['status'],
        acknowledged_at=row['acknowledged_at'],
        rule_name=row['rule_name'] if row['rule_name'] is not None else '',
        trigger_data=row['trigger_data'],
    )


def _row_to_simulation_event(row: sqlite3.Row) -> SimulationEvent:
    """Convierte un registro de SQLite a objeto SimulationEvent."""
    return SimulationEvent(
        id=row['id'],
        simulation_id=row['simulation_id'],
        patient_id=row['patient_id'],
        event_at=row['event_at'],
        event_type=row['event_type'],
        description=row['description'] if row['description'] is not None else '',
        event_data=row['event_data'],
    )


# ==============================================================================
# OPERACIONES CRUD: PACIENTES
# ==============================================================================

def insert_patient(conn: sqlite3.Connection, patient: Patient) -> int:
    """Inserta un nuevo paciente y retorna el id asignado."""
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO patients (
                    patient_code, full_name, created_at, arrival_at, 
                    administrative_status, is_simulated, symptoms, initial_diagnosis, triage_level
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    patient.patient_code,
                    patient.full_name or '',
                    patient.created_at or datetime.now().isoformat(),
                    patient.arrival_at or datetime.now().isoformat(),
                    patient.administrative_status or 'en_espera',
                    1 if patient.is_simulated else 0,
                    patient.symptoms or '',
                    patient.initial_diagnosis or '',
                    patient.triage_level,
                ),
            )
            patient.id = cursor.lastrowid
            return int(patient.id)
    except Exception as err:
        logger.error("Error al insertar paciente con código '%s': %s", patient.patient_code, err)
        raise


def get_patient_by_id(conn: sqlite3.Connection, patient_id: int) -> Optional[Patient]:
    """Obtiene un paciente por su id, retorna None si no existe."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patients WHERE id = ?", (patient_id,))
        row = cursor.fetchone()
        return _row_to_patient(row) if row else None
    except Exception as err:
        logger.error("Error al obtener paciente con id %s: %s", patient_id, err)
        raise


def get_patient_by_code(conn: sqlite3.Connection, patient_code: str) -> Optional[Patient]:
    """Obtiene un paciente por su código único."""
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM patients WHERE patient_code = ?", (patient_code,))
        row = cursor.fetchone()
        return _row_to_patient(row) if row else None
    except Exception as err:
        logger.error("Error al obtener paciente con código '%s': %s", patient_code, err)
        raise


def get_all_patients(
    conn: sqlite3.Connection,
    status_filter: Optional[str] = None,
    include_simulated: bool = True,
) -> List[Patient]:
    """Obtiene todos los pacientes con filtro opcional por estado administrativo."""
    try:
        query = "SELECT * FROM patients WHERE 1=1"
        params: List[Any] = []
        if status_filter is not None:
            query += " AND administrative_status = ?"
            params.append(status_filter)
        if not include_simulated:
            query += " AND is_simulated = 0"
        query += " ORDER BY id ASC"

        cursor = conn.cursor()
        cursor.execute(query, params)
        return [_row_to_patient(row) for row in cursor.fetchall()]
    except Exception as err:
        logger.error("Error al obtener lista de pacientes: %s", err)
        raise


def update_patient_status(conn: sqlite3.Connection, patient_id: int, new_status: str) -> bool:
    """Actualiza el estado administrativo de un paciente."""
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE patients SET administrative_status = ? WHERE id = ?",
                (new_status, patient_id),
            )
            return cursor.rowcount > 0
    except Exception as err:
        logger.error("Error al actualizar estado para paciente %s: %s", patient_id, err)
        raise


def get_patients_en_espera(conn: sqlite3.Connection, include_simulated: bool = True) -> List[Patient]:
    """Obtiene pacientes con estado 'en_espera' ordenados cronológicamente por llegada para la cola."""
    try:
        query = "SELECT * FROM patients WHERE administrative_status = 'en_espera'"
        if not include_simulated:
            query += " AND is_simulated = 0"
        query += " ORDER BY arrival_at ASC, id ASC"

        cursor = conn.cursor()
        cursor.execute(query)
        return [_row_to_patient(row) for row in cursor.fetchall()]
    except Exception as err:
        logger.error("Error al consultar pacientes en espera: %s", err)
        raise


# ==============================================================================
# OPERACIONES CRUD: MEDICIONES (MEASUREMENTS)
# ==============================================================================

def insert_measurement(conn: sqlite3.Connection, measurement: Measurement) -> int:
    """Inserta una medición de signos vitales y retorna el id asignado."""
    try:
        supp_ox = None
        if measurement.supplemental_oxygen is not None:
            supp_ox = 1 if measurement.supplemental_oxygen else 0

        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO measurements (
                    patient_id, recorded_at, respiratory_rate, oxygen_saturation,
                    supplemental_oxygen, systolic_blood_pressure, heart_rate,
                    temperature, consciousness_status, measurement_source, spo2_scale
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    measurement.patient_id,
                    measurement.recorded_at or datetime.now().isoformat(),
                    measurement.respiratory_rate,
                    measurement.oxygen_saturation,
                    supp_ox,
                    measurement.systolic_blood_pressure,
                    measurement.heart_rate,
                    measurement.temperature,
                    measurement.consciousness_status,
                    measurement.measurement_source or 'manual',
                    measurement.spo2_scale,
                ),
            )
            measurement.id = cursor.lastrowid
            return int(measurement.id)
    except Exception as err:
        logger.error("Error al insertar medición para paciente %s: %s", measurement.patient_id, err)
        raise


def get_measurements_for_patient(conn: sqlite3.Connection, patient_id: int) -> List[Measurement]:
    """Obtiene todas las mediciones de un paciente ordenadas por recorded_at ASC."""
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM measurements WHERE patient_id = ? ORDER BY recorded_at ASC, id ASC",
            (patient_id,),
        )
        return [_row_to_measurement(row) for row in cursor.fetchall()]
    except Exception as err:
        logger.error("Error al consultar mediciones del paciente %s: %s", patient_id, err)
        raise


def get_latest_measurement(conn: sqlite3.Connection, patient_id: int) -> Optional[Measurement]:
    """Obtiene la medición más reciente de un paciente."""
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM measurements WHERE patient_id = ? ORDER BY recorded_at DESC, id DESC LIMIT 1",
            (patient_id,),
        )
        row = cursor.fetchone()
        return _row_to_measurement(row) if row else None
    except Exception as err:
        logger.error("Error al obtener la medición más reciente del paciente %s: %s", patient_id, err)
        raise


# ==============================================================================
# OPERACIONES CRUD: EVALUACIONES (EVALUATIONS)
# ==============================================================================

def insert_evaluation(conn: sqlite3.Connection, evaluation: Evaluation) -> int:
    """Inserta una evaluación clínica y retorna el nuevo id generado."""
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO evaluations (
                    patient_id, measurement_id, evaluated_at, scoring_method,
                    score, completeness_status, explanation, risk_level, parameter_scores
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evaluation.patient_id,
                    evaluation.measurement_id,
                    evaluation.evaluated_at or datetime.now().isoformat(),
                    evaluation.scoring_method,
                    evaluation.score,
                    evaluation.completeness_status,
                    evaluation.explanation or '',
                    evaluation.risk_level,
                    evaluation.parameter_scores,
                ),
            )
            evaluation.id = cursor.lastrowid
            return int(evaluation.id)
    except Exception as err:
        logger.error("Error al registrar evaluación para paciente %s: %s", evaluation.patient_id, err)
        raise


def get_evaluations_for_patient(conn: sqlite3.Connection, patient_id: int) -> List[Evaluation]:
    """Obtiene todas las evaluaciones de un paciente ordenadas por evaluated_at ASC."""
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM evaluations WHERE patient_id = ? ORDER BY evaluated_at ASC, id ASC",
            (patient_id,),
        )
        return [_row_to_evaluation(row) for row in cursor.fetchall()]
    except Exception as err:
        logger.error("Error al listar evaluaciones del paciente %s: %s", patient_id, err)
        raise


def get_latest_evaluation(conn: sqlite3.Connection, patient_id: int) -> Optional[Evaluation]:
    """Obtiene la evaluación clínica más reciente de un paciente."""
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM evaluations WHERE patient_id = ? ORDER BY evaluated_at DESC, id DESC LIMIT 1",
            (patient_id,),
        )
        row = cursor.fetchone()
        return _row_to_evaluation(row) if row else None
    except Exception as err:
        logger.error("Error al obtener última evaluación del paciente %s: %s", patient_id, err)
        raise


# ==============================================================================
# OPERACIONES CRUD: ALERTAS (ALERTS)
# ==============================================================================

def insert_alert(conn: sqlite3.Connection, alert: Alert) -> int:
    """Inserta una alerta en la base de datos y retorna su id generado."""
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO alerts (
                    patient_id, evaluation_id, created_at, alert_type,
                    reason, status, acknowledged_at, rule_name, trigger_data
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    alert.patient_id,
                    alert.evaluation_id,
                    alert.created_at or datetime.now().isoformat(),
                    alert.alert_type,
                    alert.reason,
                    alert.status or ALERT_STATUS_PENDING,
                    alert.acknowledged_at,
                    alert.rule_name or '',
                    alert.trigger_data,
                ),
            )
            alert.id = cursor.lastrowid
            return int(alert.id)
    except Exception as err:
        logger.error("Error al registrar alerta para paciente %s: %s", alert.patient_id, err)
        raise


def get_alerts_for_patient(
    conn: sqlite3.Connection,
    patient_id: int,
    status_filter: Optional[str] = None,
) -> List[Alert]:
    """Obtiene las alertas asociadas a un paciente con filtro opcional de estado."""
    try:
        query = "SELECT * FROM alerts WHERE patient_id = ?"
        params: List[Any] = [patient_id]
        if status_filter is not None:
            query += " AND status = ?"
            params.append(status_filter)
        query += " ORDER BY created_at DESC, id DESC"

        cursor = conn.cursor()
        cursor.execute(query, params)
        return [_row_to_alert(row) for row in cursor.fetchall()]
    except Exception as err:
        logger.error("Error al obtener alertas del paciente %s: %s", patient_id, err)
        raise


def get_all_pending_alerts(conn: sqlite3.Connection) -> List[Alert]:
    """Obtiene todas las alertas pendientes registradas en el sistema."""
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM alerts WHERE status = ? ORDER BY created_at ASC, id ASC",
            (ALERT_STATUS_PENDING,),
        )
        return [_row_to_alert(row) for row in cursor.fetchall()]
    except Exception as err:
        logger.error("Error al consultar alertas pendientes: %s", err)
        raise


def acknowledge_alert(conn: sqlite3.Connection, alert_id: int) -> bool:
    """Marca una alerta como reconocida con la marca de tiempo actual."""
    try:
        now_iso = datetime.now().isoformat()
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE alerts SET status = ?, acknowledged_at = ? WHERE id = ?",
                (ALERT_STATUS_ACKNOWLEDGED, now_iso, alert_id),
            )
            return cursor.rowcount > 0
    except Exception as err:
        logger.error("Error al reconocer alerta con id %s: %s", alert_id, err)
        raise


def check_duplicate_alert(
    conn: sqlite3.Connection,
    patient_id: int,
    alert_type: str,
    since_minutes: int = 5,
) -> bool:
    """Verifica si ya existe una alerta del mismo tipo para el paciente dentro de la ventana de minutos."""
    try:
        cutoff_dt = datetime.now() - timedelta(minutes=since_minutes)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT created_at FROM alerts
            WHERE patient_id = ? AND alert_type = ?
            ORDER BY created_at DESC
            LIMIT 15
            """,
            (patient_id, alert_type),
        )
        rows = cursor.fetchall()
        for row in rows:
            raw_time = row['created_at']
            try:
                if 'T' in raw_time:
                    alert_dt = datetime.fromisoformat(raw_time)
                else:
                    alert_dt = datetime.strptime(raw_time, DATE_FORMAT)

                # Homogeneizar zonas horarias si aplica
                if alert_dt.tzinfo is not None and cutoff_dt.tzinfo is None:
                    cutoff_compare = cutoff_dt.astimezone(alert_dt.tzinfo)
                elif alert_dt.tzinfo is None and cutoff_dt.tzinfo is not None:
                    alert_dt = alert_dt.astimezone(cutoff_dt.tzinfo)
                    cutoff_compare = cutoff_dt
                else:
                    cutoff_compare = cutoff_dt

                if alert_dt >= cutoff_compare:
                    return True
            except Exception:
                if raw_time >= cutoff_dt.isoformat():
                    return True
        return False
    except Exception as err:
        logger.error(
            "Error al verificar duplicidad de alertas para paciente %s y tipo '%s': %s",
            patient_id,
            alert_type,
            err,
        )
        raise


# ==============================================================================
# OPERACIONES: EVENTOS DE SIMULACIÓN Y LIMPIEZA
# ==============================================================================

def insert_simulation_event(conn: sqlite3.Connection, event: SimulationEvent) -> int:
    """Inserta un evento de simulación y retorna su id asignado."""
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO simulation_events (
                    simulation_id, patient_id, event_at, event_type, description, event_data
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event.simulation_id,
                    event.patient_id,
                    event.event_at or datetime.now().isoformat(),
                    event.event_type,
                    event.description or '',
                    event.event_data,
                ),
            )
            event.id = cursor.lastrowid
            return int(event.id)
    except Exception as err:
        logger.error("Error al insertar evento de simulación: %s", err)
        raise


def get_simulation_events(conn: sqlite3.Connection, simulation_id: str) -> List[SimulationEvent]:
    """Obtiene todos los eventos asociados a una corrida de simulación ordenados cronológicamente."""
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM simulation_events WHERE simulation_id = ? ORDER BY event_at ASC, id ASC",
            (simulation_id,),
        )
        return [_row_to_simulation_event(row) for row in cursor.fetchall()]
    except Exception as err:
        logger.error("Error al obtener eventos de la simulación '%s': %s", simulation_id, err)
        raise


def delete_simulation_data(conn: sqlite3.Connection, simulation_id: Optional[str] = None) -> int:
    """Elimina datos de simulación respetando la integridad referencial.

    Si se proporciona simulation_id, elimina únicamente los registros vinculados a esa corrida.
    Si simulation_id es None, elimina todos los datos simulados existentes.
    Retorna la cantidad total de pacientes simulados eliminados.
    """
    try:
        with conn:
            cursor = conn.cursor()
            if simulation_id is not None:
                # Obtener identificadores de pacientes generados en esta simulación
                cursor.execute(
                    """
                    SELECT DISTINCT patient_id FROM simulation_events
                    WHERE simulation_id = ? AND patient_id IS NOT NULL
                    """,
                    (simulation_id,),
                )
                rows = cursor.fetchall()
                patient_ids = [row[0] for row in rows if row[0] is not None]

                if patient_ids:
                    placeholders = ",".join("?" for _ in patient_ids)
                    cursor.execute(f"DELETE FROM alerts WHERE patient_id IN ({placeholders})", patient_ids)
                    cursor.execute(f"DELETE FROM evaluations WHERE patient_id IN ({placeholders})", patient_ids)
                    cursor.execute(f"DELETE FROM measurements WHERE patient_id IN ({placeholders})", patient_ids)
                    cursor.execute("DELETE FROM simulation_events WHERE simulation_id = ?", (simulation_id,))
                    cursor.execute(f"DELETE FROM patients WHERE id IN ({placeholders})", patient_ids)
                    deleted_patients = cursor.rowcount
                else:
                    cursor.execute("DELETE FROM simulation_events WHERE simulation_id = ?", (simulation_id,))
                    deleted_patients = 0

                return deleted_patients
            else:
                cursor.execute("SELECT id FROM patients WHERE is_simulated = 1")
                rows = cursor.fetchall()
                patient_ids = [row[0] for row in rows if row[0] is not None]

                if patient_ids:
                    placeholders = ",".join("?" for _ in patient_ids)
                    cursor.execute(f"DELETE FROM alerts WHERE patient_id IN ({placeholders})", patient_ids)
                    cursor.execute(f"DELETE FROM evaluations WHERE patient_id IN ({placeholders})", patient_ids)
                    cursor.execute(f"DELETE FROM measurements WHERE patient_id IN ({placeholders})", patient_ids)

                cursor.execute("DELETE FROM simulation_events")
                cursor.execute("DELETE FROM patients WHERE is_simulated = 1")
                return len(patient_ids)
    except Exception as err:
        logger.error("Error al eliminar datos de simulación: %s", err)
        raise


def delete_patient(conn: sqlite3.Connection, patient_id: int) -> bool:
    """Elimina un paciente y todos sus registros dependientes respetando la integridad referencial.

    Elimina en orden:
    1. Alertas asociadas
    2. Evaluaciones asociadas
    3. Mediciones asociadas
    4. Eventos de simulación asociados
    5. Fila del paciente en la tabla patients

    Args:
        conn: Conexión SQLite activa.
        patient_id: Identificador numérico del paciente.

    Returns:
        True si el paciente fue eliminado, False si no existía.
    """
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM patients WHERE id = ?", (patient_id,))
            if not cursor.fetchone():
                return False

            cursor.execute("DELETE FROM alerts WHERE patient_id = ?", (patient_id,))
            cursor.execute("DELETE FROM evaluations WHERE patient_id = ?", (patient_id,))
            cursor.execute("DELETE FROM measurements WHERE patient_id = ?", (patient_id,))
            cursor.execute("DELETE FROM simulation_events WHERE patient_id = ?", (patient_id,))
            cursor.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
            return cursor.rowcount > 0
    except Exception as err:
        logger.error("Error al eliminar paciente ID %s: %s", patient_id, err)
        raise


def delete_patient_by_code(conn: sqlite3.Connection, patient_code: str) -> bool:
    """Elimina un paciente a partir de su código institucional unificado (ej. 'PAC-XXXXXX').

    Args:
        conn: Conexión SQLite activa.
        patient_code: Código del paciente.

    Returns:
        True si fue eliminado, False si no se encontró.
    """
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM patients WHERE patient_code = ?", (patient_code,))
        row = cursor.fetchone()
        if not row:
            return False
        return delete_patient(conn, row['id'])
    except Exception as err:
        logger.error("Error al buscar paciente por código '%s' para eliminación: %s", patient_code, err)
        raise
