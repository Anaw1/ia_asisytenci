"""Modelos de datos para el prototipo académico IA Médica Asistencial.

Define las entidades principales como dataclasses con tipado estricto:
pacientes, mediciones fisiológicas, evaluaciones NEWS2, alertas del sistema,
eventos de simulación y entradas de la cola administrativa.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Patient:
    """Entidad que representa a un paciente registrado en el sistema asistencial."""

    id: Optional[int] = None
    patient_code: str = ''
    full_name: str = ''  # Nombre (ficticio) para humanizar la interfaz asistencial
    created_at: str = ''  # Formato ISO 8601
    arrival_at: str = ''  # Formato ISO 8601
    administrative_status: str = 'en_espera'
    is_simulated: bool = False
    symptoms: str = ''  # Síntomas principales reportados al ingreso
    initial_diagnosis: str = ''  # Impresión clínica o sospecha diagnóstica preliminar
    triage_level: Optional[int] = None  # Puntaje/Nivel de triaje clínico profesional (1 a 5)

    # Campos computados (no persistidos en la tabla patients)
    wait_time_minutes: Optional[float] = None
    pending_alerts_count: int = 0
    last_evaluation_score: Optional[int] = None
    last_evaluation_at: Optional[str] = None

    @property
    def triage_score(self) -> Optional[int]:
        """Alias para puntaje/nivel de triaje clínico profesional."""
        return self.triage_level

    @triage_score.setter
    def triage_score(self, value: Optional[int]) -> None:
        self.triage_level = value

    @property
    def name(self) -> str:
        """Alias para el nombre del paciente."""
        return self.full_name

    @name.setter
    def name(self, value: str) -> None:
        self.full_name = value


@dataclass
class Measurement:
    """Entidad que registra una medición puntual de signos vitales del paciente."""

    id: Optional[int] = None
    patient_id: int = 0
    recorded_at: str = ''  # Formato ISO 8601
    respiratory_rate: Optional[int] = None  # respiraciones/min
    oxygen_saturation: Optional[int] = None  # %
    supplemental_oxygen: Optional[bool] = None  # True/False
    systolic_blood_pressure: Optional[int] = None  # mmHg
    heart_rate: Optional[int] = None  # latidos/min
    temperature: Optional[float] = None  # °C
    consciousness_status: Optional[str] = None  # A/V/P/U
    measurement_source: str = 'manual'
    # Escala de SpO2 de NEWS2: 1 (predeterminada) o 2 (solo si un clínico la indica
    # para insuficiencia respiratoria hipercápnica confirmada).
    spo2_scale: int = 1


@dataclass
class Evaluation:
    """Entidad que almacena el cálculo de alerta temprana (NEWS2) derivado de una medición."""

    id: Optional[int] = None
    patient_id: int = 0
    measurement_id: int = 0
    evaluated_at: str = ''
    scoring_method: str = ''  # ej. 'NEWS2'
    score: Optional[int] = None
    completeness_status: str = ''  # 'complete', 'incomplete', 'error'
    explanation: str = ''  # Explicación comprensible en español
    risk_level: Optional[str] = None  # 'low', 'low_medium', 'medium', 'high'
    parameter_scores: Optional[str] = None  # Cadena JSON con desglose de puntajes


@dataclass
class Alert:
    """Entidad que representa una alerta administrativa o clínica en el sistema."""

    id: Optional[int] = None
    patient_id: int = 0
    evaluation_id: Optional[int] = None
    created_at: str = ''
    alert_type: str = ''  # Clave proveniente de ALERT_TYPES en config.py
    reason: str = ''  # Explicación clara en español
    status: str = 'pendiente'
    acknowledged_at: Optional[str] = None
    rule_name: str = ''  # Regla que detonó la alerta
    trigger_data: Optional[str] = None  # Cadena JSON con datos del evento disparador


@dataclass
class SimulationEvent:
    """Entidad que registra un evento cronológico dentro de una corrida de simulación."""

    id: Optional[int] = None
    simulation_id: str = ''  # Identificador UUID de la ejecución
    patient_id: Optional[int] = None
    event_at: str = ''  # Formato ISO 8601
    event_type: str = ''  # ej. 'ingreso', 'medicion', 'alerta', 'cambio_cola'
    description: str = ''  # Descripción en español
    event_data: Optional[str] = None  # Cadena JSON con información complementaria


@dataclass
class QueueEntry:
    """Representa la posición de un paciente en la cola administrativa. No persistida en DB."""

    position: int = 0
    patient: Optional[Patient] = None
    priority_score: float = 0.0
    reasons: List[str] = field(default_factory=list)
    pending_alerts: int = 0
    last_evaluation: Optional[Evaluation] = None
    wait_time_minutes: float = 0.0
    last_updated: str = ''


@dataclass
class SimulationConfig:
    """Configuración para la ejecución de una simulación sintética de pacientes."""

    num_patients: int = 5
    duration_hours: int = 4
    measurement_interval_minutes: int = 30
    random_seed: int = 42
    simulation_id: str = ''  # Identificador UUID de la corrida
