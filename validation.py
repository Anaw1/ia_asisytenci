"""Módulo de validación de entradas y parámetros clínicos para IA Médica Asistencial.

Valida datos de pacientes, mediciones de signos vitales, completitud para NEWS2,
estados administrativos y configuraciones de simulación. Emite advertencias clínicas
para valores atípicos y errores estrictos en español sin sustituir valores inválidos.
"""

from dataclasses import dataclass, field
from datetime import datetime
import re
from typing import Any, Dict, List, Optional, Tuple

from config import (
    ADMIN_STATUSES,
    CONSCIOUSNESS_LEVELS,
    DATE_FORMAT,
    MEASUREMENT_SOURCES,
)


@dataclass
class ValidationResult:
    """Resultado estructurado de una validación de datos."""

    is_valid: bool
    errors: List[str] = field(default_factory=list)  # Mensajes de error en español
    warnings: List[str] = field(default_factory=list)  # Mensajes de advertencia en español
    cleaned_data: Dict[str, Any] = field(default_factory=dict)  # Datos validados y normalizados


def sanitize_string(value: str) -> str:
    """Elimina espacios en blanco iniciales/finales y caracteres de control no imprimibles.

    No sustituye valores no válidos por valores predeterminados.
    """
    if not isinstance(value, str):
        value = str(value)
    # Elimina caracteres de control ASCII (0x00 a 0x1F y 0x7F a 0x9F)
    cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', value)
    return cleaned.strip()


def _is_valid_int(val: Any) -> bool:
    """Verifica si un valor puede representarse estrictamente como número entero."""
    if isinstance(val, bool):
        return False
    if isinstance(val, int):
        return True
    if isinstance(val, str):
        val_str = val.strip()
        if re.match(r'^-?\d+$', val_str):
            return True
    return False


def _is_valid_float(val: Any) -> bool:
    """Verifica si un valor puede representarse como número decimal o entero."""
    if isinstance(val, bool):
        return False
    if isinstance(val, (int, float)):
        return True
    if isinstance(val, str):
        try:
            float(val.strip())
            return True
        except ValueError:
            return False
    return False


def _parse_bool(val: Any) -> Optional[bool]:
    """Interpreta un valor como booleano de manera estricta."""
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        if val == 1:
            return True
        if val == 0:
            return False
        return None
    if isinstance(val, str):
        normalized = val.strip().lower()
        if normalized in ('true', '1', 'si', 'sí', 's', 'verdadero'):
            return True
        if normalized in ('false', '0', 'no', 'n', 'falso'):
            return False
    return None


def validate_patient_code(code: str) -> ValidationResult:
    """Valida el formato del código de paciente.

    Debe ser no vacío, alfanumérico con guiones (-) y tener entre 3 y 20 caracteres.
    """
    if not isinstance(code, str):
        return ValidationResult(
            is_valid=False,
            errors=['El código de paciente debe ser una cadena de texto válida.'],
            warnings=[],
            cleaned_data={},
        )

    sanitized = sanitize_string(code)
    if not sanitized:
        return ValidationResult(
            is_valid=False,
            errors=['El código de paciente no puede estar vacío.'],
            warnings=[],
            cleaned_data={},
        )

    if len(sanitized) < 3 or len(sanitized) > 20:
        return ValidationResult(
            is_valid=False,
            errors=[f'El código de paciente debe tener entre 3 y 20 caracteres (longitud recibida: {len(sanitized)}).'],
            warnings=[],
            cleaned_data={},
        )

    if not re.match(r'^[A-Za-z0-9\-]+$', sanitized):
        return ValidationResult(
            is_valid=False,
            errors=['El código de paciente solo puede contener caracteres alfanuméricos y guiones (-) sin espacios.'],
            warnings=[],
            cleaned_data={},
        )

    return ValidationResult(
        is_valid=True,
        errors=[],
        warnings=[],
        cleaned_data={'patient_code': sanitized},
    )


def validate_arrival_datetime(arrival_str: str) -> ValidationResult:
    """Valida la fecha y hora de llegada del paciente.

    Debe tener formato ISO 8601 o estándar y no corresponder a un momento futuro.
    """
    if not isinstance(arrival_str, str):
        return ValidationResult(
            is_valid=False,
            errors=['La fecha y hora de llegada debe ser una cadena de texto.'],
            warnings=[],
            cleaned_data={},
        )

    cleaned = sanitize_string(arrival_str)
    if not cleaned:
        return ValidationResult(
            is_valid=False,
            errors=['La fecha y hora de llegada no puede estar vacía.'],
            warnings=[],
            cleaned_data={},
        )

    parsed_dt: Optional[datetime] = None
    try:
        # Intentar formato ISO 8601 estándar
        iso_candidate = cleaned.replace('Z', '+00:00')
        parsed_dt = datetime.fromisoformat(iso_candidate)
    except ValueError:
        try:
            parsed_dt = datetime.strptime(cleaned, DATE_FORMAT)
        except ValueError:
            return ValidationResult(
                is_valid=False,
                errors=[
                    'Formato de fecha y hora no válido. Se requiere formato ISO 8601 (ej. YYYY-MM-DDTHH:MM:SS) '
                    'o formato estándar YYYY-MM-DD HH:MM:SS.'
                ],
                warnings=[],
                cleaned_data={},
            )

    now = datetime.now(parsed_dt.tzinfo) if parsed_dt.tzinfo is not None else datetime.now()
    if parsed_dt > now:
        return ValidationResult(
            is_valid=False,
            errors=['La fecha y hora de llegada no puede ser posterior a la fecha y hora actual del sistema.'],
            warnings=[],
            cleaned_data={},
        )

    return ValidationResult(
        is_valid=True,
        errors=[],
        warnings=[],
        cleaned_data={'arrival_at': cleaned},
    )


def validate_measurement(data: Dict[str, Any]) -> ValidationResult:
    """Valida una medición de signos vitales.

    Verifica rangos fisiológicos permitidos:
    - respiratory_rate: entero, rango 0-60 (típico: 8-25)
    - oxygen_saturation: entero, rango 0-100 (típico: 85-100)
    - supplemental_oxygen: booleano
    - systolic_blood_pressure: entero, rango 0-300 (típico: 80-200)
    - heart_rate: entero, rango 0-250 (típico: 40-150)
    - temperature: flotante, rango 25.0-45.0 (típico: 35.0-40.0)
    - consciousness_status: uno de CONSCIOUSNESS_LEVELS ('A', 'V', 'P', 'U')
    - measurement_source: uno de MEASUREMENT_SOURCES ('manual', 'simulacion')

    Los campos pueden omitirse o ser None; pero si se proporcionan, deben ser válidos.
    Emite advertencias para valores fuera de rangos típicos sin descartar la medición.
    """
    errors: List[str] = []
    warnings: List[str] = []
    cleaned: Dict[str, Any] = {}

    if not isinstance(data, dict):
        return ValidationResult(
            is_valid=False,
            errors=['Los datos de la medición deben proporcionarse en un diccionario.'],
            warnings=[],
            cleaned_data={},
        )

    # 1. Frecuencia respiratoria
    if 'respiratory_rate' in data and data['respiratory_rate'] is not None:
        val = data['respiratory_rate']
        if not _is_valid_int(val):
            errors.append('La frecuencia respiratoria debe ser un número entero (respiraciones/min).')
        else:
            int_val = int(val)
            if int_val < 0 or int_val > 60:
                errors.append(f'La frecuencia respiratoria ({int_val}) está fuera del rango fisiológico permitido (0-60 resp/min).')
            else:
                cleaned['respiratory_rate'] = int_val
                if int_val < 8 or int_val > 25:
                    warnings.append(f'Frecuencia respiratoria ({int_val} resp/min) fuera del rango clínico típico esperado (8-25 resp/min).')

    # 2. Saturación de oxígeno
    if 'oxygen_saturation' in data and data['oxygen_saturation'] is not None:
        val = data['oxygen_saturation']
        if not _is_valid_int(val):
            errors.append('La saturación de oxígeno debe ser un número entero (%).')
        else:
            int_val = int(val)
            if int_val < 0 or int_val > 100:
                errors.append(f'La saturación de oxígeno ({int_val}%) está fuera del rango permitido (0-100%).')
            else:
                cleaned['oxygen_saturation'] = int_val
                if int_val < 85:
                    warnings.append(f'Saturación de oxígeno ({int_val}%) fuera del rango típico esperado (85-100%).')

    # 3. Oxígeno suplementario
    if 'supplemental_oxygen' in data and data['supplemental_oxygen'] is not None:
        val = data['supplemental_oxygen']
        parsed_bool = _parse_bool(val)
        if parsed_bool is None:
            errors.append('El valor de oxígeno suplementario debe ser booleano (Sí/No o Verdadero/Falso).')
        else:
            cleaned['supplemental_oxygen'] = parsed_bool

    # 4. Presión arterial sistólica
    if 'systolic_blood_pressure' in data and data['systolic_blood_pressure'] is not None:
        val = data['systolic_blood_pressure']
        if not _is_valid_int(val):
            errors.append('La presión arterial sistólica debe ser un número entero (mmHg).')
        else:
            int_val = int(val)
            if int_val < 0 or int_val > 300:
                errors.append(f'La presión arterial sistólica ({int_val} mmHg) está fuera del rango fisiológico permitido (0-300 mmHg).')
            else:
                cleaned['systolic_blood_pressure'] = int_val
                if int_val < 80 or int_val > 200:
                    warnings.append(f'Presión arterial sistólica ({int_val} mmHg) fuera del rango clínico típico esperado (80-200 mmHg).')

    # 5. Frecuencia cardíaca
    if 'heart_rate' in data and data['heart_rate'] is not None:
        val = data['heart_rate']
        if not _is_valid_int(val):
            errors.append('La frecuencia cardíaca debe ser un número entero (latidos/min).')
        else:
            int_val = int(val)
            if int_val < 0 or int_val > 250:
                errors.append(f'La frecuencia cardíaca ({int_val} lpm) está fuera del rango fisiológico permitido (0-250 latidos/min).')
            else:
                cleaned['heart_rate'] = int_val
                if int_val < 40 or int_val > 150:
                    warnings.append(f'Frecuencia cardíaca ({int_val} lpm) fuera del rango clínico típico esperado (40-150 latidos/min).')

    # 6. Temperatura
    if 'temperature' in data and data['temperature'] is not None:
        val = data['temperature']
        if not _is_valid_float(val):
            errors.append('La temperatura corporal debe ser un número decimal (°C).')
        else:
            float_val = round(float(val), 2)
            if float_val < 25.0 or float_val > 45.0:
                errors.append(f'La temperatura corporal ({float_val} °C) está fuera del rango fisiológico permitido (25.0-45.0 °C).')
            else:
                cleaned['temperature'] = float_val
                if float_val < 35.0 or float_val > 40.0:
                    warnings.append(f'Temperatura corporal ({float_val} °C) fuera del rango clínico típico esperado (35.0-40.0 °C).')

    # 7. Nivel de conciencia (AVPU)
    if 'consciousness_status' in data and data['consciousness_status'] is not None:
        val = str(data['consciousness_status']).strip().upper()
        if val not in CONSCIOUSNESS_LEVELS:
            errors.append(
                f"El estado de conciencia ('{data['consciousness_status']}') debe pertenecer a la escala AVPU ({', '.join(CONSCIOUSNESS_LEVELS)})."
            )
        else:
            cleaned['consciousness_status'] = val

    # 8. Origen de la medición
    if 'measurement_source' in data and data['measurement_source'] is not None:
        val = sanitize_string(str(data['measurement_source']))
        if val not in MEASUREMENT_SOURCES:
            errors.append(
                f"El origen de medición ('{val}') no es válido. Opciones permitidas: {', '.join(MEASUREMENT_SOURCES)}."
            )
        else:
            cleaned['measurement_source'] = val
    else:
        cleaned['measurement_source'] = 'manual'

    # 9. Escala de SpO2 de NEWS2 (1 por defecto; 2 solo por indicación clínica)
    if 'spo2_scale' in data and data['spo2_scale'] is not None:
        if _is_valid_int(data['spo2_scale']) and int(data['spo2_scale']) in (1, 2):
            cleaned['spo2_scale'] = int(data['spo2_scale'])
        else:
            errors.append('La escala de SpO2 debe ser 1 o 2.')
    else:
        cleaned['spo2_scale'] = 1

    # Campos contextuales opcionales
    if 'patient_id' in data and data['patient_id'] is not None:
        if _is_valid_int(data['patient_id']):
            cleaned['patient_id'] = int(data['patient_id'])
        else:
            errors.append('El identificador de paciente (patient_id) debe ser un número entero.')

    if 'recorded_at' in data and data['recorded_at'] is not None:
        cleaned['recorded_at'] = sanitize_string(str(data['recorded_at']))

    is_valid = len(errors) == 0
    return ValidationResult(
        is_valid=is_valid,
        errors=errors,
        warnings=warnings,
        cleaned_data=cleaned if is_valid else {},
    )


def validate_measurement_completeness(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Verifica si todos los campos requeridos para el cálculo NEWS2 están presentes.

    Campos requeridos:
    respiratory_rate, oxygen_saturation, supplemental_oxygen,
    systolic_blood_pressure, heart_rate, temperature, consciousness_status.

    Retorna una tupla (es_completo, lista_de_nombres_faltantes_en_español).
    """
    required_fields: Dict[str, str] = {
        'respiratory_rate': 'Frecuencia respiratoria',
        'oxygen_saturation': 'Saturación de oxígeno',
        'supplemental_oxygen': 'Oxígeno suplementario',
        'systolic_blood_pressure': 'Presión arterial sistólica',
        'heart_rate': 'Frecuencia cardíaca',
        'temperature': 'Temperatura',
        'consciousness_status': 'Nivel de conciencia (AVPU)',
    }

    missing: List[str] = []
    for field_name, spanish_label in required_fields.items():
        val = data.get(field_name)
        if val is None:
            missing.append(spanish_label)
        elif isinstance(val, str) and not val.strip():
            missing.append(spanish_label)

    return (len(missing) == 0, missing)


def validate_administrative_status(status: str) -> ValidationResult:
    """Valida que el estado administrativo pertenezca a los estados permitidos del sistema."""
    if not isinstance(status, str):
        return ValidationResult(
            is_valid=False,
            errors=['El estado administrativo debe ser una cadena de texto.'],
            warnings=[],
            cleaned_data={},
        )

    sanitized = sanitize_string(status)
    if sanitized not in ADMIN_STATUSES:
        return ValidationResult(
            is_valid=False,
            errors=[f"El estado administrativo '{status}' no es válido. Estados permitidos: {', '.join(ADMIN_STATUSES)}."],
            warnings=[],
            cleaned_data={},
        )

    return ValidationResult(
        is_valid=True,
        errors=[],
        warnings=[],
        cleaned_data={'administrative_status': sanitized},
    )


def validate_simulation_config(
    num_patients: int,
    duration_hours: int,
    measurement_interval: int,
    seed: int,
) -> ValidationResult:
    """Valida los parámetros de configuración de una simulación.

    Restricciones:
    - num_patients: entero entre 1 y 50
    - duration_hours: entero entre 1 y 24
    - measurement_interval: entero entre 5 y 120 minutos
    - seed: cualquier número entero
    """
    errors: List[str] = []
    cleaned: Dict[str, Any] = {}

    # 1. Cantidad de pacientes
    if not _is_valid_int(num_patients):
        errors.append('La cantidad de pacientes en simulación debe ser un número entero.')
    else:
        val_patients = int(num_patients)
        if val_patients < 1 or val_patients > 50:
            errors.append(f'La cantidad de pacientes ({val_patients}) debe estar entre 1 y 50.')
        else:
            cleaned['num_patients'] = val_patients

    # 2. Duración en horas
    if not _is_valid_int(duration_hours):
        errors.append('La duración de la simulación en horas debe ser un número entero.')
    else:
        val_duration = int(duration_hours)
        if val_duration < 1 or val_duration > 24:
            errors.append(f'La duración de la simulación ({val_duration} horas) debe estar entre 1 y 24 horas.')
        else:
            cleaned['duration_hours'] = val_duration

    # 3. Intervalo de medición en minutos
    if not _is_valid_int(measurement_interval):
        errors.append('El intervalo de medición en minutos debe ser un número entero.')
    else:
        val_interval = int(measurement_interval)
        if val_interval < 5 or val_interval > 120:
            errors.append(f'El intervalo entre mediciones ({val_interval} min) debe estar entre 5 y 120 minutos.')
        else:
            cleaned['measurement_interval_minutes'] = val_interval

    # 4. Semilla aleatoria
    if not _is_valid_int(seed):
        errors.append('La semilla aleatoria (seed) debe ser un número entero.')
    else:
        cleaned['random_seed'] = int(seed)

    is_valid = len(errors) == 0
    return ValidationResult(
        is_valid=is_valid,
        errors=errors,
        warnings=[],
        cleaned_data=cleaned if is_valid else {},
    )
