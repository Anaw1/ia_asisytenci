"""Módulo de Simulación Clínica y Generación de Escenarios Sintéticos.

Proyecto: IA Médica Asistencial (Prototipo Académico por TechMinds).
Este módulo gestiona la creación reproducible de pacientes ficticios, generación
de signos vitales sintéticos basados en perfiles fisiológicos, evaluación secuencial
con el motor de alertas y seguimiento temporal de la cola de atención.
"""

import json
import random
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from alert_engine import AlertEngine
from clinical_scoring import calculate_news2, create_evaluation_from_news2
from config import (
    CONSCIOUSNESS_LEVELS,
    DATE_FORMAT,
    SIM_DEFAULT_DURATION_HOURS,
    SIM_DEFAULT_MEASUREMENT_INTERVAL_MINUTES,
    SIM_DEFAULT_PATIENTS,
    SIM_RANDOM_SEED,
)
from database import (
    delete_simulation_data,
    get_alerts_for_patient,
    get_connection,
    get_evaluations_for_patient,
    get_latest_evaluation,
    get_measurements_for_patient,
    get_patient_by_id,
    get_simulation_events,
    init_db,
    insert_measurement,
    insert_patient,
    insert_simulation_event,
)
from models import (
    Measurement,
    Patient,
    QueueEntry,
    SimulationConfig,
    SimulationEvent,
)
from patient_service import compute_wait_time, register_measurement, register_patient
from prioritization import build_queue, format_queue_for_display
from validation import validate_simulation_config


# Perfiles fisiológicos sintéticos para escenarios de simulación
SYNTHETIC_PROFILES: List[Dict[str, Any]] = [
    {
        'name': 'Estable',
        'patient_name': 'Carlos Gómez (Ficticio)',
        'description': 'Paciente con signos vitales normales y estables',
        'symptoms': 'Dolor lumbar mecánico de 2 días de evolución, afebril, sin signos de alarma',
        'initial_diagnosis': 'Lumbalgia aguda mecánica no complicada',
        'triage_level': 4,
        'base_vitals': {
            'respiratory_rate': 16,
            'oxygen_saturation': 97,
            'supplemental_oxygen': False,
            'systolic_blood_pressure': 120,
            'heart_rate': 75,
            'temperature': 36.8,
            'consciousness_status': 'A',
        },
        'variation': {
            'respiratory_rate': 2,
            'oxygen_saturation': 1,
            'systolic_blood_pressure': 5,
            'heart_rate': 5,
            'temperature': 0.2,
        },
    },
    {
        'name': 'Deterioro leve',
        'patient_name': 'María Fernanda Torres (Ficticio)',
        'description': 'Paciente con tendencia al deterioro gradual',
        'symptoms': 'Tos persistente con expectoración, disnea de medianos esfuerzos y febrícula',
        'initial_diagnosis': 'Infección respiratoria aguda baja / Sospecha de neumonía adquirida en comunidad',
        'triage_level': 3,
        'base_vitals': {
            'respiratory_rate': 20,
            'oxygen_saturation': 94,
            'supplemental_oxygen': False,
            'systolic_blood_pressure': 105,
            'heart_rate': 100,
            'temperature': 37.8,
            'consciousness_status': 'A',
        },
        'variation': {
            'respiratory_rate': 3,
            'oxygen_saturation': 2,
            'systolic_blood_pressure': 10,
            'heart_rate': 8,
            'temperature': 0.4,
        },
        'trend': {
            'respiratory_rate': 1,
            'oxygen_saturation': -0.5,
            'heart_rate': 2,
            'temperature': 0.1,
        },
    },
    {
        'name': 'Crítico',
        'patient_name': 'Jorge Eliécer Silva (Ficticio)',
        'description': 'Paciente con signos vitales preocupantes',
        'symptoms': 'Dolor torácico opresivo retroesternal con diaforesis profusa y disnea severa',
        'initial_diagnosis': 'Síndrome coronario agudo / Sospecha de choque cardiogénico inminente',
        'triage_level': 1,
        'base_vitals': {
            'respiratory_rate': 26,
            'oxygen_saturation': 90,
            'supplemental_oxygen': True,
            'systolic_blood_pressure': 88,
            'heart_rate': 135,
            'temperature': 39.5,
            'consciousness_status': 'V',
        },
        'variation': {
            'respiratory_rate': 2,
            'oxygen_saturation': 2,
            'systolic_blood_pressure': 5,
            'heart_rate': 5,
            'temperature': 0.3,
        },
    },
    {
        'name': 'Datos incompletos',
        'patient_name': 'Ana Sofía Morales (Ficticio)',
        'description': 'Paciente con mediciones parciales (faltan datos)',
        'symptoms': 'Cefalea holocraneana pulsátil intensa acompañada de náuseas y fotofobia',
        'initial_diagnosis': 'Cefalea aguda en estudio / Pendiente completar constantes fisiológicas',
        'triage_level': 3,
        'base_vitals': {
            'respiratory_rate': 18,
            'oxygen_saturation': None,
            'supplemental_oxygen': None,
            'systolic_blood_pressure': 115,
            'heart_rate': 80,
            'temperature': None,
            'consciousness_status': 'A',
        },
        'variation': {
            'respiratory_rate': 2,
            'systolic_blood_pressure': 5,
            'heart_rate': 5,
        },
    },
    {
        'name': 'Mejora gradual',
        'patient_name': 'Luis Alberto Mendoza (Ficticio)',
        'description': 'Paciente que mejora con el tiempo',
        'symptoms': 'Crisis asmática con dificultad ventilatoria, en respuesta a broncodilatadores',
        'initial_diagnosis': 'Crisis asmática aguda moderada en resolución clínica',
        'triage_level': 2,
        'base_vitals': {
            'respiratory_rate': 22,
            'oxygen_saturation': 93,
            'supplemental_oxygen': True,
            'systolic_blood_pressure': 95,
            'heart_rate': 115,
            'temperature': 38.5,
            'consciousness_status': 'A',
        },
        'variation': {
            'respiratory_rate': 2,
            'oxygen_saturation': 1,
            'systolic_blood_pressure': 5,
            'heart_rate': 5,
            'temperature': 0.2,
        },
        'trend': {
            'respiratory_rate': -0.5,
            'oxygen_saturation': 0.5,
            'systolic_blood_pressure': 2,
            'heart_rate': -3,
            'temperature': -0.1,
        },
    },
]


def generate_synthetic_measurement(
    profile: Dict[str, Any], step: int, rng: random.Random
) -> Dict[str, Any]:
    """Genera una medición sintética basada en un perfil clínico, paso temporal y RNG.

    Aplica la fórmula: base_vitals + variacion_aleatoria + (tendencia * paso).
    Acota los valores numéricos a rangos biológicamente coherentes.
    Omite deliberadamente los parámetros con valor None para simular registros incompletos.

    Args:
        profile: Diccionario con la definición del perfil sintético.
        step: Índice del paso temporal (entero >= 0).
        rng: Instancia de random.Random para garantizar reproducibilidad exacta.

    Returns:
        Diccionario con los signos vitales generados.
    """
    base = profile.get('base_vitals', {})
    variation = profile.get('variation', {})
    trend = profile.get('trend', {})

    measurement: Dict[str, Any] = {}

    # Límites fisiológicos válidos para acotamiento (min, max, es_flotante)
    clamp_rules = {
        'respiratory_rate': (0, 60, False),
        'oxygen_saturation': (0, 100, False),
        'systolic_blood_pressure': (0, 300, False),
        'heart_rate': (0, 250, False),
        'temperature': (25.0, 45.0, True),
    }

    for key, (min_val, max_val, is_float) in clamp_rules.items():
        base_val = base.get(key)
        if base_val is not None:
            var_limit = variation.get(key, 0.0)
            trend_val = trend.get(key, 0.0)
            delta = rng.uniform(-var_limit, var_limit) if var_limit > 0 else 0.0
            computed = base_val + (trend_val * step) + delta
            clamped = max(min_val, min(max_val, computed))
            if is_float:
                measurement[key] = round(float(clamped), 1)
            else:
                measurement[key] = int(round(clamped))

    # Oxígeno suplementario
    supp_o2 = base.get('supplemental_oxygen')
    if supp_o2 is not None:
        measurement['supplemental_oxygen'] = bool(supp_o2)

    # Estado de conciencia (AVPU)
    consciousness = base.get('consciousness_status')
    if consciousness is not None:
        if consciousness in CONSCIOUSNESS_LEVELS:
            measurement['consciousness_status'] = str(consciousness)
        else:
            measurement['consciousness_status'] = 'A'

    return measurement


def run_simulation(
    config: SimulationConfig, db_path: Optional[str] = None
) -> Dict[str, Any]:
    """Ejecuta una simulación temporal completa de pacientes en urgencias.

    Etapas de ejecución:
    1. Valida la configuración de la simulación.
    2. Inicializa el generador de números aleatorios con semilla determinista.
    3. Registra pacientes ficticios con horas de llegada escalonadas.
    4. En cada intervalo temporal:
       a. Genera signos vitales para pacientes activos.
       b. Registra mediciones en la base de datos.
       c. Ejecuta el motor de alertas y calcula evaluaciones NEWS2.
       d. Recalcula y captura el estado de la cola administrativa.
       e. Registra los eventos correspondientes en el historial.
    5. Consolida y retorna las estadísticas y trazabilidad del escenario.

    Args:
        config: Objeto SimulationConfig con los parámetros del experimento.
        db_path: Ruta opcional al archivo SQLite de la base de datos.

    Returns:
        Diccionario con simulation_id, config, métricas agregadas, eventos y snapshots de cola.
    """
    errors: List[str] = []

    # 1. Validar configuración
    validation = validate_simulation_config(
        config.num_patients,
        config.duration_hours,
        config.measurement_interval_minutes,
        config.random_seed,
    )
    if not validation.is_valid:
        return {
            'simulation_id': config.simulation_id or str(uuid.uuid4()),
            'config': config,
            'patients_created': 0,
            'total_measurements': 0,
            'total_alerts': 0,
            'total_events': 0,
            'queue_snapshots': [],
            'events': [],
            'success': False,
            'errors': validation.errors,
        }

    # 2. Inicializar identificador y generador pseudoaleatorio reproducible
    sim_id = config.simulation_id if config.simulation_id else str(uuid.uuid4())
    config.simulation_id = sim_id
    rng = random.Random(config.random_seed)

    duration_minutes = config.duration_hours * 60
    interval_minutes = config.measurement_interval_minutes
    num_steps = max(1, int(duration_minutes // interval_minutes))

    # Base temporal en el pasado para que los tiempos de espera sean realistas
    sim_start_time = datetime.now().replace(microsecond=0) - timedelta(
        minutes=duration_minutes
    )

    init_db(db_path)
    conn = get_connection(db_path)
    try:
        # 3. Crear pacientes con llegadas escalonadas
        sim_patients: List[Dict[str, Any]] = []
        stagger_span = duration_minutes * 0.5
        stagger_delta = (
            stagger_span / max(1, config.num_patients - 1)
            if config.num_patients > 1
            else 0.0
        )

        for i in range(config.num_patients):
            profile = SYNTHETIC_PROFILES[i % len(SYNTHETIC_PROFILES)]
            arrival_offset = int(i * stagger_delta)
            arrival_dt = sim_start_time + timedelta(minutes=arrival_offset)
            arrival_iso = arrival_dt.isoformat()

            reg_result = register_patient(
                full_name=profile.get('patient_name'),
                arrival_at=arrival_iso,
                symptoms=profile.get('symptoms'),
                initial_diagnosis=profile.get('initial_diagnosis'),
                triage_level=profile.get('triage_level'),
                is_simulated=True,
                db_path=db_path,
            )

            if not reg_result.get('success'):
                err_msg = (
                    f"Error al registrar paciente sintético {i + 1}: "
                    f"{', '.join(reg_result.get('errors', []))}"
                )
                errors.append(err_msg)
                continue

            patient_id = reg_result['patient_id']
            patient_code = reg_result['patient_code']

            sim_patients.append({
                'id': patient_id,
                'code': patient_code,
                'profile': profile,
                'arrival_dt': arrival_dt,
                'step_count': 0,
            })

            # Registrar evento de ingreso
            event_ingreso = SimulationEvent(
                id=None,
                simulation_id=sim_id,
                patient_id=patient_id,
                event_at=arrival_iso,
                event_type='ingreso',
                description=(
                    f"Ingreso de paciente {patient_code} (Perfil: {profile['name']})"
                ),
                event_data=json.dumps(
                    {
                        'patient_code': patient_code,
                        'profile': profile['name'],
                        'description': profile['description'],
                        'arrival_at': arrival_iso,
                    },
                    ensure_ascii=False,
                ),
            )
            insert_simulation_event(conn, event_ingreso)

        if not sim_patients:
            return {
                'simulation_id': sim_id,
                'config': config,
                'patients_created': 0,
                'total_measurements': 0,
                'total_alerts': 0,
                'total_events': 0,
                'queue_snapshots': [],
                'events': [],
                'success': False,
                'errors': errors
                or [
                    'No fue posible registrar pacientes para la simulación.'
                ],
            }

        # 4. Bucle temporal de la simulación
        alert_engine = AlertEngine(db_path=db_path)
        queue_snapshots: List[List[Dict[str, Any]]] = []
        total_measurements = 0
        total_alerts = 0

        for step in range(num_steps + 1):
            current_time = sim_start_time + timedelta(
                minutes=step * interval_minutes
            )
            current_iso = current_time.isoformat()

            for patient_data in sim_patients:
                # El paciente sólo recibe mediciones a partir de su hora de llegada
                if current_time < patient_data['arrival_dt']:
                    continue

                measurement_dict = generate_synthetic_measurement(
                    patient_data['profile'], patient_data['step_count'], rng
                )
                measurement_dict['recorded_at'] = current_iso
                patient_data['step_count'] += 1

                # Registrar medición
                try:
                    meas_result = register_measurement(
                        patient_data['id'],
                        measurement_dict,
                        source='simulacion',
                        db_path=db_path,
                    )
                except Exception as ex:
                    errors.append(
                        f"Fallo al registrar medición para {patient_data['code']}: {str(ex)}"
                    )
                    continue

                if meas_result.get('success'):
                    total_measurements += 1

                    # Evento de medición registrada
                    event_med = SimulationEvent(
                        id=None,
                        simulation_id=sim_id,
                        patient_id=patient_data['id'],
                        event_at=current_iso,
                        event_type='medicion',
                        description=(
                            f"Medición registrada para paciente {patient_data['code']} "
                            f"(Paso {patient_data['step_count']})"
                        ),
                        event_data=json.dumps(
                            measurement_dict, ensure_ascii=False
                        ),
                    )
                    insert_simulation_event(conn, event_med)

                    # Evaluar la medición (persiste la evaluación NEWS2 y genera alertas)
                    try:
                        eval_outcome = alert_engine.evaluate_new_measurement(
                            patient_data['id'], meas_result['measurement']
                        )
                        alerts = eval_outcome.get('alerts', [])
                        for alert_item in alerts:
                            total_alerts += 1
                            event_alerta = SimulationEvent(
                                id=None,
                                simulation_id=sim_id,
                                patient_id=patient_data['id'],
                                event_at=current_iso,
                                event_type='alerta',
                                description=(
                                    f"Alerta generada ({alert_item.alert_type}): "
                                    f"{alert_item.reason}"
                                ),
                                event_data=json.dumps(
                                    {
                                        'alert_type': alert_item.alert_type,
                                        'reason': alert_item.reason,
                                        'rule_name': alert_item.rule_name,
                                    },
                                    ensure_ascii=False,
                                ),
                            )
                            insert_simulation_event(conn, event_alerta)
                    except Exception as alert_ex:
                        errors.append(
                            f"Error al evaluar alertas de {patient_data['code']}: {str(alert_ex)}"
                        )

                    # Registrar evento de evaluación si existe evaluación reciente
                    try:
                        latest_eval = get_latest_evaluation(
                            conn, patient_data['id']
                        )
                        if latest_eval:
                            event_eval = SimulationEvent(
                                id=None,
                                simulation_id=sim_id,
                                patient_id=patient_data['id'],
                                event_at=current_iso,
                                event_type='evaluacion',
                                description=(
                                    f"Evaluación NEWS2 para paciente {patient_data['code']}: "
                                    f"puntaje {latest_eval.score} (Riesgo: {latest_eval.risk_level or 'N/D'})"
                                ),
                                event_data=json.dumps(
                                    {
                                        'score': latest_eval.score,
                                        'risk_level': latest_eval.risk_level,
                                        'explanation': latest_eval.explanation,
                                        'completeness_status': latest_eval.completeness_status,
                                    },
                                    ensure_ascii=False,
                                ),
                            )
                            insert_simulation_event(conn, event_eval)
                    except Exception as eval_ex:
                        errors.append(
                            f"Error al consultar evaluación para {patient_data['code']}: {str(eval_ex)}"
                        )

            # Construir y registrar snapshot de la cola en este paso
            try:
                queue_entries = build_queue(
                    db_path=db_path, include_simulated=True
                )
                formatted_snapshot = format_queue_for_display(queue_entries)
                queue_snapshots.append(formatted_snapshot)

                event_cola = SimulationEvent(
                    id=None,
                    simulation_id=sim_id,
                    patient_id=None,
                    event_at=current_iso,
                    event_type='cambio_cola',
                    description=(
                        f"Actualización de cola en el paso {step + 1} "
                        f"({len(queue_entries)} pacientes en espera)"
                    ),
                    event_data=json.dumps(
                        [
                            {
                                'position': q.position,
                                'patient_id': (
                                    q.patient.id if q.patient else None
                                ),
                                'patient_code': (
                                    q.patient.patient_code if q.patient else ''
                                ),
                                'priority_score': q.priority_score,
                            }
                            for q in queue_entries
                        ],
                        ensure_ascii=False,
                    ),
                )
                insert_simulation_event(conn, event_cola)
            except Exception as queue_ex:
                errors.append(
                    f"Error al actualizar la cola en paso {step}: {str(queue_ex)}"
                )

        # 5. Obtener todos los eventos persistidos
        all_events = get_simulation_events(conn, sim_id)

        return {
            'simulation_id': sim_id,
            'config': config,
            'patients': sim_patients,
            'patients_created': len(sim_patients),
            'total_measurements': total_measurements,
            'total_alerts': total_alerts,
            'total_events': len(all_events),
            'queue_snapshots': queue_snapshots,
            'events': all_events,
            'success': len(errors) == 0,
            'errors': errors,
        }

    finally:
        conn.close()


def get_simulation_results(
    simulation_id: str, db_path: Optional[str] = None
) -> Dict[str, Any]:
    """Recupera los resultados y la historia clínica completa de una simulación previa.

    Args:
        simulation_id: Identificador único de la simulación.
        db_path: Ruta opcional a la base de datos SQLite.

    Returns:
        Diccionario con eventos, listado de pacientes con sus historiales y resumen.
    """
    conn = get_connection(db_path)
    try:
        events = get_simulation_events(conn, simulation_id)
        if not events:
            return {
                'simulation_id': simulation_id,
                'patients_created': 0,
                'total_measurements': 0,
                'total_alerts': 0,
                'total_events': 0,
                'events': [],
                'patients': [],
                'success': False,
                'errors': [
                    f"No se encontraron eventos asociados a la simulación '{simulation_id}'."
                ],
            }

        patient_ids = set()
        total_measurements = 0
        total_alerts = 0
        for ev in events:
            if ev.patient_id is not None:
                patient_ids.add(ev.patient_id)
            if ev.event_type == 'medicion':
                total_measurements += 1
            elif ev.event_type == 'alerta':
                total_alerts += 1

        patients_data = []
        for pid in sorted(patient_ids):
            patient = get_patient_by_id(conn, pid)
            if patient:
                measurements = get_measurements_for_patient(conn, pid)
                evaluations = get_evaluations_for_patient(conn, pid)
                alerts = get_alerts_for_patient(conn, pid)
                patients_data.append({
                    'patient': patient,
                    'measurements': measurements,
                    'evaluations': evaluations,
                    'alerts': alerts,
                })

        return {
            'simulation_id': simulation_id,
            'patients_created': len(patients_data),
            'total_measurements': total_measurements,
            'total_alerts': total_alerts,
            'total_events': len(events),
            'events': events,
            'patients': patients_data,
            'success': True,
            'errors': [],
        }
    finally:
        conn.close()


def clear_simulation_data(
    simulation_id: Optional[str] = None, db_path: Optional[str] = None
) -> Dict[str, Any]:
    """Elimina registros generados por la simulación.

    Si se proporciona simulation_id, borra únicamente los datos de dicha simulación.
    Si es None, elimina todos los datos sintéticos de simulación.

    Args:
        simulation_id: Identificador de la simulación o None para todas.
        db_path: Ruta opcional a la base de datos.

    Returns:
        Diccionario con indicador de éxito y cantidad de registros eliminados.
    """
    conn = get_connection(db_path)
    try:
        deleted_count = delete_simulation_data(conn, simulation_id=simulation_id)
        return {
            'success': True,
            'deleted_count': deleted_count,
            'simulation_id': simulation_id,
            'errors': [],
        }
    except Exception as e:
        return {
            'success': False,
            'deleted_count': 0,
            'simulation_id': simulation_id,
            'errors': [f'Error al eliminar datos de simulación: {str(e)}'],
        }
    finally:
        conn.close()
