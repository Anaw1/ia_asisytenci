"""Módulo de configuración para el prototipo académico IA Médica Asistencial.

Define constantes del sistema, parámetros de simulación, esquemas de alertas,
umbrales clínicos NEWS2 (Royal College of Physicians, 2017), reglas de priorización
administrativa y textos metodológicos/legales de descargo de responsabilidad.
"""

from typing import Any, Dict, List, Tuple

# ==============================================================================
# IDENTIFICACIÓN Y CONFIGURACIÓN GENERAL DEL SISTEMA
# ==============================================================================
APP_NAME: str = 'IA Médica Asistencial'
TEAM_NAME: str = 'TechMinds'
APP_VERSION: str = '1.0.0-alpha'
DB_PATH: str = 'triage_techminds.db'  # Ruta relativa, resuelta en tiempo de ejecución
DATE_FORMAT: str = '%Y-%m-%d %H:%M:%S'
DEFAULT_PAGE_SIZE: int = 20

# ==============================================================================
# ESTADOS ADMINISTRATIVOS DE ATENCIÓN
# ==============================================================================
ADMIN_STATUSES: Dict[str, str] = {
    'en_espera': 'En espera',
    'en_atencion': 'En atención',
    'atendido': 'Atendido',
    'alta': 'Alta',
}

# Alias de compatibilidad
ADMIN_STATUS_LABELS: Dict[str, str] = ADMIN_STATUSES

# ==============================================================================
# UNIDADES DE MEDIDA CLÍNICA (DOCUMENTADAS)
# ==============================================================================
MEASUREMENT_UNITS: Dict[str, str] = {
    'respiratory_rate': 'respiraciones/min',
    'oxygen_saturation': '%',
    'supplemental_oxygen': 'Sí/No',
    'systolic_blood_pressure': 'mmHg',
    'heart_rate': 'latidos/min',
    'temperature': '°C',
    'consciousness_status': 'AVPU scale',
}

# ==============================================================================
# NIVELES DE CONCIENCIA - ESCALA AVPU
# ==============================================================================
CONSCIOUSNESS_LEVELS: List[str] = ['A', 'V', 'P', 'U']  # Alert, Voice, Pain, Unresponsive

CONSCIOUSNESS_LABELS: Dict[str, str] = {
    'A': 'Alerta (A)',
    'V': 'Responde a la voz (V)',
    'P': 'Responde al dolor (P)',
    'U': 'Sin respuesta / Inconsciente (U)',
}

# ==============================================================================
# ORIGEN DE MEDICIONES
# ==============================================================================
MEASUREMENT_SOURCES: List[str] = ['manual', 'simulacion']

# ==============================================================================
# PARÁMETROS PREDETERMINADOS DE SIMULACIÓN
# ==============================================================================
SIM_DEFAULT_PATIENTS: int = 5
SIM_DEFAULT_DURATION_HOURS: int = 4
SIM_DEFAULT_MEASUREMENT_INTERVAL_MINUTES: int = 30
SIM_RANDOM_SEED: int = 42

# ==============================================================================
# ESTADOS Y TIPOS DE ALERTAS ADMINISTRATIVO-CLÍNICAS
# ==============================================================================
ALERT_STATUS_PENDING: str = 'pendiente'
ALERT_STATUS_ACKNOWLEDGED: str = 'reconocida'

ALERT_TYPES: Dict[str, Dict[str, Any]] = {
    'new_measurement': {
        'label': 'Nueva medición registrada',
        'requires_review': False,
    },
    'value_change': {
        'label': 'Cambio significativo en signos vitales',
        'requires_review': True,
    },
    'incomplete_evaluation': {
        'label': 'Evaluación incompleta de signos vitales',
        'requires_review': True,
    },
    'high_score': {
        'label': 'Puntuación NEWS2 elevada (Riesgo alto)',
        'requires_review': True,
    },
    'long_wait': {
        'label': 'Tiempo de espera prolongado sin reevaluación',
        'requires_review': True,
    },
    'unacknowledged_alert': {
        'label': 'Alerta previa sin reconocer',
        'requires_review': True,
    },
}

# ==============================================================================
# REGLAS DE PRIORIZACIÓN DE COLA (ADMINISTRATIVAS, NO CLÍNICAS)
# ==============================================================================
PRIORITY_RULES: List[Dict[str, Any]] = [
    {
        'name': 'triage_clinical_level',
        'description': 'Pondera la clasificación inicial de triaje clínico profesional asignada en la admisión (Niveles I a V).',
        'weight': 120,
    },
    {
        'name': 'pending_alerts',
        'description': 'Prioriza pacientes que poseen alertas activas pendientes de reconocimiento.',
        'weight': 100,
    },
    {
        'name': 'high_news2_score',
        'description': 'Prioriza pacientes con puntuación NEWS2 agregada alta (>= 7) o gatillo individual.',
        'weight': 80,
    },
    {
        'name': 'wait_time',
        'description': 'Prioriza pacientes con mayor tiempo acumulado en sala de espera administrativa.',
        'weight': 60,
    },
    {
        'name': 'incomplete_evaluation',
        'description': 'Prioriza pacientes con registros incompletos que requieren completar signos vitales.',
        'weight': 40,
    },
]

# ==============================================================================
# CLASIFICACIÓN DE TRIAJE PROFESIONAL (ESTÁNDAR COLOMBIANO / INTERNACIONAL I-V)
# ==============================================================================
TRIAGE_LEVELS: Dict[int, Dict[str, Any]] = {
    1: {
        'roman': 'I',
        'label': 'Nivel I - Reanimación (Riesgo vital inminente)',
        'short_label': 'Nivel I (Reanimación)',
        'description': 'Atención médica inmediata. Requiere reanimación y soporte vital avanzado sin demora.',
        'color': '#dc3545',  # Rojo
        'max_wait_minutes': 0,
        'priority_weight': 120.0,
    },
    2: {
        'roman': 'II',
        'label': 'Nivel II - Emergencia (Alto riesgo / Potencial inestabilidad)',
        'short_label': 'Nivel II (Emergencia)',
        'description': 'Situación de alto riesgo o potencial deterioro rápido. Tiempo objetivo de atención: ≤ 30 minutos.',
        'color': '#fd7e14',  # Naranja
        'max_wait_minutes': 30,
        'priority_weight': 90.0,
    },
    3: {
        'roman': 'III',
        'label': 'Nivel III - Urgencia (Condición aguda estable)',
        'short_label': 'Nivel III (Urgencia)',
        'description': 'Condición clínica que requiere evaluación diagnóstica e intervenciones. Tiempo objetivo: ≤ 60 minutos.',
        'color': '#ffc107',  # Amarillo
        'max_wait_minutes': 60,
        'priority_weight': 50.0,
    },
    4: {
        'roman': 'IV',
        'label': 'Nivel IV - Prioritario / Urgencia Menor',
        'short_label': 'Nivel IV (Prioritario)',
        'description': 'Condición médica sin compromiso vital inminente; consulta médica prioritaria. Tiempo objetivo: ≤ 120 minutos.',
        'color': '#28a745',  # Verde
        'max_wait_minutes': 120,
        'priority_weight': 20.0,
    },
    5: {
        'roman': 'V',
        'label': 'Nivel V - No Urgente (Baja complejidad)',
        'short_label': 'Nivel V (No Urgente)',
        'description': 'Problema clínico crónico o subagudo sin deterioro funcional inmediato. Tiempo objetivo: ≤ 180 minutos.',
        'color': '#17a2b8',  # Azul
        'max_wait_minutes': 180,
        'priority_weight': 0.0,
    },
}

TRIAGE_LEVEL_LABELS: Dict[int, str] = {
    lvl: info['short_label'] for lvl, info in TRIAGE_LEVELS.items()
}

# ==============================================================================
# SÍNTOMAS COMUNES SUGERIDOS (PARA APOYO EN FORMULARIO Y SIMULACIÓN)
# ==============================================================================
COMMON_SYMPTOMS: List[str] = [
    'Dolor torácico opresivo con irradiación a miembro superior',
    'Dificultad respiratoria aguda y disnea de reposo',
    'Cefalea intensa súbita de inicio fulminante',
    'Dolor abdominal agudo con defensa muscular',
    'Fiebre cuantificada con escalofríos y malestar general',
    'Alteración del estado de conciencia o síncope',
    'Traumatismo contuso en extremidad con limitación funcional',
    'Tos persistente con expectoración mucopurulenta',
    'Crisis hipertensiva asintomática',
    'Lipotimia y sensación de mareo postural',
]

# ==============================================================================
# UMBRALES DE RIESGO CLÍNICO NEWS2 (ROYAL COLLEGE OF PHYSICIANS, 2017)
# ==============================================================================
NEWS2_LOW_SCORE_RANGE: Tuple[int, int] = (0, 4)  # Puntuación agregada 0-4
NEWS2_LOW_MEDIUM_TRIGGER: int = 3               # Puntuación individual de 3 en cualquier parámetro
NEWS2_MEDIUM_SCORE_RANGE: Tuple[int, int] = (5, 6)  # Puntuación agregada 5-6
NEWS2_HIGH_SCORE_THRESHOLD: int = 7             # Puntuación agregada >= 7

NEWS2_RISK_LEVELS: Dict[str, Dict[str, str]] = {
    'low': {
        'label': 'Riesgo bajo',
        'description': 'Puntuación NEWS2 agregada de 0 a 4. Monitoreo clínico de rutina y reevaluación estándar.',
    },
    'low_medium': {
        'label': 'Riesgo bajo-medio (Gatillo de parámetro individual)',
        'description': 'Puntuación NEWS2 agregada de 0 a 4 con al menos un parámetro individual con puntaje 3. Requiere evaluación médica urgente.',
    },
    'medium': {
        'label': 'Riesgo medio',
        'description': 'Puntuación NEWS2 agregada de 5 a 6. Respuesta urgente y aumento en la frecuencia de monitoreo clínico.',
    },
    'high': {
        'label': 'Riesgo alto',
        'description': 'Puntuación NEWS2 agregada de 7 o más. Respuesta clínica de emergencia inmediata y evaluación por equipo de respuesta rápida.',
    },
}

# ==============================================================================
# DESCARGOS DE RESPONSABILIDAD LEGAL Y METODOLOGÍA
# ==============================================================================
DISCLAIMER_TEXT: str = (
    "AVISO LEGAL Y ACADÉMICO: Este software es un prototipo desarrollado con fines "
    "estrictamente académicos e investigativos por el equipo TechMinds. "
    "Todos los datos de pacientes, nombres, mediciones y eventos son completamente ficticios o simulados. "
    "Esta herramienta NO es un dispositivo médico certificado, NO realiza diagnósticos clínicos vinculantes "
    "y NO está autorizada para la toma de decisiones asistenciales reales en seres humanos. "
    "Cualquier asignación de prioridad es puramente administrativa para demostración del sistema."
)

METHODOLOGY_TEXT: str = (
    "METODOLOGÍA CLÍNICA Y LIMITACIONES:\n"
    "1. Triaje Profesional en Admisión: El sistema registra el nivel de triaje clínico profesional "
    "(Niveles I a V según normativa de urgencias), capturado presencialmente por el equipo asistencial.\n"
    "2. Escala de Advertencia Temprana (NEWS2): La implementación de la puntuación de deterioro "
    "fisiológico sigue las especificaciones oficiales del Royal College of Physicians (RCP, 2017).\n"
    "3. Diferenciación Conceptual Estricta: Se mantiene una estricta separación entre:\n"
    "   - El triaje clínico profesional inicial (clasificación médica en admisión).\n"
    "   - La puntuación NEWS2 (detector dinámico de descompensación hemodinámica).\n"
    "   - La prioridad administrativa de cola (orden heurístico explicable que equilibra triaje, NEWS2, alertas y espera).\n"
    "4. Prioridad Administrativa de Cola: El orden en la cola administrativa es un índice heurístico "
    "ponderado para gestión operativa del prototipo, no un juicio diagnóstico sustitutivo."
)
