"""Cálculo clínico del puntaje NEWS2 (National Early Warning Score 2).

Basado en la especificación del Royal College of Physicians (RCP, 2017).
Este módulo calcula el puntaje de advertencia temprana fisiológica (0 a 20)
y determina el nivel de riesgo clínico.

IMPORTANTE:
- NEWS2 es un sistema de puntuación fisiológica para detectar deterioro clínico.
- NEWS2 NO es una categoría de triaje clínico (I a V, como Manchester o ESI).
- No se auto-asignan categorías de triaje I-V en este sistema.
- Las decisiones clínicas deben ser tomadas exclusivamente por profesionales de salud.
- Este módulo no interactúa con bases de datos ni con interfaces de usuario.
"""

from typing import Dict, Optional, Tuple, List, Any
from dataclasses import dataclass
import json
from datetime import datetime

from models import Measurement, Evaluation
from config import (
    NEWS2_LOW_SCORE_RANGE,
    NEWS2_LOW_MEDIUM_TRIGGER,
    NEWS2_MEDIUM_SCORE_RANGE,
    NEWS2_HIGH_SCORE_THRESHOLD,
    NEWS2_RISK_LEVELS,
    DATE_FORMAT,
)


@dataclass
class NEWS2ParameterResult:
    """Resultado individual de puntuación de un parámetro fisiológico en NEWS2."""

    parameter_name: str  # Nombre en español
    value: Any  # Valor medido
    score: int  # Puntuación asignada (0 a 3)
    explanation: str  # Explicación en español


@dataclass
class NEWS2Result:
    """Resultado consolidado del cálculo del protocolo NEWS2."""

    total_score: Optional[int]  # Puntuación agregada (None si incompleto)
    parameter_results: List[NEWS2ParameterResult]
    risk_level: Optional[str]  # 'low', 'low_medium', 'medium', 'high'
    risk_label: str  # Etiqueta descriptiva en español
    is_complete: bool
    missing_parameters: List[str]  # Nombres en español de parámetros faltantes
    explanation: str  # Resumen clínico explicativo en español
    scale_used: str  # 'Escala 1' o 'Escala 2'


def score_respiratory_rate(rate: int) -> NEWS2ParameterResult:
    """Evalúa la frecuencia respiratoria según la especificación NEWS2.

    Umbrales RCP:
        <= 8: 3 puntos
        9-11: 1 punto
        12-20: 0 puntos
        21-24: 2 puntos
        >= 25: 3 puntos

    Args:
        rate: Respiraciones por minuto.

    Returns:
        NEWS2ParameterResult: Resultado con puntuación y explicación.
    """
    param_name = "Frecuencia respiratoria"
    if rate <= 8:
        return NEWS2ParameterResult(param_name, rate, 3, "Crítica baja (≤8 rpm)")
    if 9 <= rate <= 11:
        return NEWS2ParameterResult(param_name, rate, 1, "Baja (9-11 rpm)")
    if 12 <= rate <= 20:
        return NEWS2ParameterResult(param_name, rate, 0, "Normal (12-20 rpm)")
    if 21 <= rate <= 24:
        return NEWS2ParameterResult(param_name, rate, 2, "Elevada (21-24 rpm)")
    return NEWS2ParameterResult(param_name, rate, 3, "Crítica alta (≥25 rpm)")


def score_oxygen_saturation_scale1(spo2: int) -> NEWS2ParameterResult:
    """Evalúa la saturación de oxígeno usando la Escala 1 (paciente sin oxígeno suplementario).

    Umbrales RCP Escala 1:
        <= 91: 3 puntos
        92-93: 2 puntos
        94-95: 1 punto
        >= 96: 0 puntos

    Args:
        spo2: Porcentaje de saturación de oxígeno (%).

    Returns:
        NEWS2ParameterResult: Resultado con puntuación y explicación.
    """
    param_name = "Saturación de oxígeno (Escala 1)"
    if spo2 <= 91:
        return NEWS2ParameterResult(param_name, spo2, 3, "Crítica baja (≤91%)")
    if 92 <= spo2 <= 93:
        return NEWS2ParameterResult(param_name, spo2, 2, "Baja (92-93%)")
    if 94 <= spo2 <= 95:
        return NEWS2ParameterResult(param_name, spo2, 1, "Límite bajo (94-95%)")
    return NEWS2ParameterResult(param_name, spo2, 0, "Normal (≥96%)")


def score_oxygen_saturation_scale2(spo2: int, on_oxygen: bool) -> NEWS2ParameterResult:
    """Evalúa la saturación de oxígeno usando la Escala 2 (paciente con oxígeno suplementario o hipercapnia).

    Umbrales RCP Escala 2:
        Con oxígeno suplementario:
            <= 83: 3 puntos
            84-85: 2 puntos
            86-87: 1 punto
            88-92: 0 puntos (rango objetivo)
            93-94: 1 punto
            95-96: 2 puntos
            >= 97: 3 puntos
        Aire ambiente (sin oxígeno):
            <= 83: 3 puntos
            84-85: 2 puntos
            86-87: 1 punto
            >= 88: 0 puntos

    Args:
        spo2: Porcentaje de saturación de oxígeno (%).
        on_oxygen: Indica si el paciente recibe oxígeno suplementario.

    Returns:
        NEWS2ParameterResult: Resultado con puntuación y explicación.
    """
    param_name = "Saturación de oxígeno (Escala 2)"
    if on_oxygen:
        if spo2 <= 83:
            return NEWS2ParameterResult(param_name, spo2, 3, "Crítica baja con O2 (≤83%)")
        if 84 <= spo2 <= 85:
            return NEWS2ParameterResult(param_name, spo2, 2, "Baja con O2 (84-85%)")
        if 86 <= spo2 <= 87:
            return NEWS2ParameterResult(param_name, spo2, 1, "Límite bajo con O2 (86-87%)")
        if 88 <= spo2 <= 92:
            return NEWS2ParameterResult(param_name, spo2, 0, "Rango objetivo con O2 (88-92%)")
        if 93 <= spo2 <= 94:
            return NEWS2ParameterResult(param_name, spo2, 1, "Elevada con O2 (93-94%)")
        if 95 <= spo2 <= 96:
            return NEWS2ParameterResult(param_name, spo2, 2, "Elevada con O2 (95-96%)")
        return NEWS2ParameterResult(param_name, spo2, 3, "Crítica alta con O2 (≥97%)")
    else:
        if spo2 <= 83:
            return NEWS2ParameterResult(param_name, spo2, 3, "Crítica baja aire ambiente (≤83%)")
        if 84 <= spo2 <= 85:
            return NEWS2ParameterResult(param_name, spo2, 2, "Baja aire ambiente (84-85%)")
        if 86 <= spo2 <= 87:
            return NEWS2ParameterResult(param_name, spo2, 1, "Límite bajo aire ambiente (86-87%)")
        return NEWS2ParameterResult(param_name, spo2, 0, "Normal o en rango aire ambiente (≥88%)")


def score_supplemental_oxygen(on_oxygen: bool) -> NEWS2ParameterResult:
    """Evalúa el uso de oxígeno suplementario.

    Umbrales RCP:
        Aire ambiente: 0 puntos
        Oxígeno suplementario: 2 puntos

    Args:
        on_oxygen: True si recibe oxígeno suplementario, False si respira aire ambiente.

    Returns:
        NEWS2ParameterResult: Resultado con puntuación y explicación.
    """
    param_name = "Oxígeno suplementario"
    if on_oxygen:
        return NEWS2ParameterResult(param_name, True, 2, "Oxígeno suplementario en uso (+2)")
    return NEWS2ParameterResult(param_name, False, 0, "Aire ambiente / Sin oxígeno suplementario (+0)")


def score_systolic_bp(sbp: int) -> NEWS2ParameterResult:
    """Evalúa la presión arterial sistólica según NEWS2.

    Umbrales RCP:
        <= 90: 3 puntos
        91-100: 2 puntos
        101-110: 1 punto
        111-219: 0 puntos
        >= 220: 3 puntos

    Args:
        sbp: Presión arterial sistólica en mmHg.

    Returns:
        NEWS2ParameterResult: Resultado con puntuación y explicación.
    """
    param_name = "Presión arterial sistólica"
    if sbp <= 90:
        return NEWS2ParameterResult(param_name, sbp, 3, "Crítica baja (≤90 mmHg)")
    if 91 <= sbp <= 100:
        return NEWS2ParameterResult(param_name, sbp, 2, "Baja (91-100 mmHg)")
    if 101 <= sbp <= 110:
        return NEWS2ParameterResult(param_name, sbp, 1, "Límite bajo (101-110 mmHg)")
    if 111 <= sbp <= 219:
        return NEWS2ParameterResult(param_name, sbp, 0, "Normal (111-219 mmHg)")
    return NEWS2ParameterResult(param_name, sbp, 3, "Crítica alta (≥220 mmHg)")


def score_heart_rate(hr: int) -> NEWS2ParameterResult:
    """Evalúa la frecuencia cardíaca / pulso según NEWS2.

    Umbrales RCP:
        <= 40: 3 puntos
        41-50: 1 punto
        51-90: 0 puntos
        91-110: 1 punto
        111-130: 2 puntos
        >= 131: 3 puntos

    Args:
        hr: Latidos por minuto (lpm).

    Returns:
        NEWS2ParameterResult: Resultado con puntuación y explicación.
    """
    param_name = "Frecuencia cardíaca"
    if hr <= 40:
        return NEWS2ParameterResult(param_name, hr, 3, "Bradicardia severa (≤40 lpm)")
    if 41 <= hr <= 50:
        return NEWS2ParameterResult(param_name, hr, 1, "Bradicardia leve (41-50 lpm)")
    if 51 <= hr <= 90:
        return NEWS2ParameterResult(param_name, hr, 0, "Normal (51-90 lpm)")
    if 91 <= hr <= 110:
        return NEWS2ParameterResult(param_name, hr, 1, "Taquicardia leve (91-110 lpm)")
    if 111 <= hr <= 130:
        return NEWS2ParameterResult(param_name, hr, 2, "Taquicardia moderada (111-130 lpm)")
    return NEWS2ParameterResult(param_name, hr, 3, "Taquicardia severa (≥131 lpm)")


def score_consciousness(level: str) -> NEWS2ParameterResult:
    """Evalúa el nivel de conciencia mediante la escala AVPU.

    Umbrales RCP:
        A (Alerta): 0 puntos
        V (Voz), P (Dolor), U (Sin respuesta): 3 puntos

    Args:
        level: Estado de conciencia ('A', 'V', 'P', 'U').

    Returns:
        NEWS2ParameterResult: Resultado con puntuación y explicación.
    """
    param_name = "Nivel de conciencia (AVPU)"
    normalized = str(level).strip().upper() if level else "U"
    if normalized == "A":
        return NEWS2ParameterResult(param_name, "A", 0, "Alerta (A)")
    if normalized == "V":
        return NEWS2ParameterResult(param_name, "V", 3, "Responde a estímulo verbal (V)")
    if normalized == "P":
        return NEWS2ParameterResult(param_name, "P", 3, "Responde a estímulo doloroso (P)")
    if normalized == "U":
        return NEWS2ParameterResult(param_name, "U", 3, "Sin respuesta (U)")
    return NEWS2ParameterResult(param_name, normalized, 3, f"Alteración de conciencia ({normalized})")


def score_temperature(temp: float) -> NEWS2ParameterResult:
    """Evalúa la temperatura corporal en grados Celsius.

    Umbrales RCP:
        <= 35.0: 3 puntos
        35.1-36.0: 1 punto
        36.1-38.0: 0 puntos
        38.1-39.0: 1 punto
        >= 39.1: 2 puntos

    Args:
        temp: Temperatura corporal en °C.

    Returns:
        NEWS2ParameterResult: Resultado con puntuación y explicación.
    """
    param_name = "Temperatura corporal"
    if temp <= 35.0:
        return NEWS2ParameterResult(param_name, temp, 3, "Hipotermia severa (≤35.0 °C)")
    if 35.1 <= temp <= 36.0:
        return NEWS2ParameterResult(param_name, temp, 1, "Hipotermia leve (35.1 - 36.0 °C)")
    if 36.1 <= temp <= 38.0:
        return NEWS2ParameterResult(param_name, temp, 0, "Normal (36.1 - 38.0 °C)")
    if 38.1 <= temp <= 39.0:
        return NEWS2ParameterResult(param_name, temp, 1, "Febrícula / Elevada (38.1 - 39.0 °C)")
    return NEWS2ParameterResult(param_name, temp, 2, "Fiebre alta (≥39.1 °C)")


def determine_risk_level(
    total_score: int, parameter_results: List[NEWS2ParameterResult]
) -> Tuple[str, str]:
    """Determina el nivel de riesgo clínico de deterioro según el estándar RCP NEWS2.

    Reglas RCP:
        - Alto (high): Puntuación total >= 7
        - Medio (medium): Puntuación total de 5 a 6
        - Bajo-Medio (low_medium): Puntuación total de 1 a 4 con al menos un parámetro individual = 3 (gatillo rojo)
        - Bajo (low): Puntuación total de 0 a 4 sin ningún parámetro individual = 3

    Args:
        total_score: Puntuación acumulada de NEWS2.
        parameter_results: Lista de resultados de cada parámetro evaluado.

    Returns:
        Tuple[str, str]: Clave interna ('low', 'low_medium', 'medium', 'high') y etiqueta descriptiva en español.
    """
    if total_score >= NEWS2_HIGH_SCORE_THRESHOLD:
        label = NEWS2_RISK_LEVELS.get("high", {}).get("label", "Riesgo clínico alto")
        return "high", label

    if total_score >= NEWS2_MEDIUM_SCORE_RANGE[0]:
        label = NEWS2_RISK_LEVELS.get("medium", {}).get("label", "Riesgo clínico medio")
        return "medium", label

    has_individual_three = any(param.score >= NEWS2_LOW_MEDIUM_TRIGGER for param in parameter_results)
    if has_individual_three:
        label = NEWS2_RISK_LEVELS.get("low_medium", {}).get(
            "label", "Riesgo clínico bajo-medio (Puntuación individual de 3)"
        )
        return "low_medium", label

    label = NEWS2_RISK_LEVELS.get("low", {}).get("label", "Riesgo clínico bajo")
    return "low", label


def calculate_news2(measurement: Measurement) -> NEWS2Result:
    """Calcula la puntuación integral NEWS2 a partir de un registro de medición.

    Aplica la Escala 1 para SpO2 si el paciente no recibe oxígeno suplementario,
    o la Escala 2 si el paciente recibe oxígeno suplementario.

    Si falta algún parámetro fisiológico obligatorio, devuelve un resultado incompleto
    con las puntuaciones parciales calculables.

    Args:
        measurement: Objeto Measurement con los signos vitales del paciente.

    Returns:
        NEWS2Result: Estructura completa con puntuaciones, nivel de riesgo y explicaciones.
    """
    missing_params: List[str] = []
    param_results: List[NEWS2ParameterResult] = []

    # Frecuencia respiratoria
    if measurement.respiratory_rate is not None:
        param_results.append(score_respiratory_rate(measurement.respiratory_rate))
    else:
        missing_params.append("Frecuencia respiratoria")

    # Oxígeno suplementario y Escala de SpO2.
    # NEWS2 (RCP, 2017): la Escala 1 es la predeterminada, incluso con oxígeno.
    # La Escala 2 solo se usa cuando un clínico la indica (hipercapnia confirmada).
    on_oxygen = bool(measurement.supplemental_oxygen) if measurement.supplemental_oxygen is not None else False
    use_scale_2 = getattr(measurement, "spo2_scale", 1) == 2
    scale_used = "Escala 2" if use_scale_2 else "Escala 1"

    if measurement.oxygen_saturation is not None:
        if use_scale_2:
            param_results.append(score_oxygen_saturation_scale2(measurement.oxygen_saturation, on_oxygen=on_oxygen))
        else:
            param_results.append(score_oxygen_saturation_scale1(measurement.oxygen_saturation))
    else:
        missing_params.append("Saturación de oxígeno")

    if measurement.supplemental_oxygen is not None:
        param_results.append(score_supplemental_oxygen(on_oxygen))
    else:
        missing_params.append("Oxígeno suplementario")

    # Presión arterial sistólica
    if measurement.systolic_blood_pressure is not None:
        param_results.append(score_systolic_bp(measurement.systolic_blood_pressure))
    else:
        missing_params.append("Presión arterial sistólica")

    # Frecuencia cardíaca
    if measurement.heart_rate is not None:
        param_results.append(score_heart_rate(measurement.heart_rate))
    else:
        missing_params.append("Frecuencia cardíaca")

    # Temperatura corporal
    if measurement.temperature is not None:
        param_results.append(score_temperature(measurement.temperature))
    else:
        missing_params.append("Temperatura corporal")

    # Nivel de conciencia
    if measurement.consciousness_status is not None and str(measurement.consciousness_status).strip():
        param_results.append(score_consciousness(measurement.consciousness_status))
    else:
        missing_params.append("Nivel de conciencia (AVPU)")

    is_complete = len(missing_params) == 0

    if not is_complete:
        partial_score = sum(p.score for p in param_results)
        missing_str = ", ".join(missing_params)
        explanation = (
            f"Evaluación NEWS2 incompleta (puntuación parcial disponible: {partial_score} puntos). "
            f"Faltan los siguientes parámetros fisiológicos: {missing_str}."
        )
        return NEWS2Result(
            total_score=None,
            parameter_results=param_results,
            risk_level=None,
            risk_label="Evaluación incompleta",
            is_complete=False,
            missing_parameters=missing_params,
            explanation=explanation,
            scale_used=scale_used,
        )

    total_score = sum(p.score for p in param_results)
    risk_key, risk_label = determine_risk_level(total_score, param_results)
    breakdown = "; ".join(f"{p.parameter_name}: {p.score} ({p.explanation})" for p in param_results)
    explanation = (
        f"Puntuación agregada NEWS2: {total_score} puntos ({risk_label}). "
        f"Protocolo SpO2 aplicado: {scale_used}. Desglose: {breakdown}."
    )

    return NEWS2Result(
        total_score=total_score,
        parameter_results=param_results,
        risk_level=risk_key,
        risk_label=risk_label,
        is_complete=True,
        missing_parameters=[],
        explanation=explanation,
        scale_used=scale_used,
    )


def detect_measurement_changes(
    current: Measurement, previous: Measurement
) -> List[Dict[str, Any]]:
    """Compara dos mediciones consecutivas de un paciente e identifica variaciones clínicas relevantes.

    Args:
        current: Medición más reciente.
        previous: Medición inmediatamente anterior.

    Returns:
        List[Dict[str, Any]]: Lista de cambios significativos con parámetro, valores y descripción en español.
    """
    changes: List[Dict[str, Any]] = []

    if previous is None or current is None:
        return changes

    # 1. Frecuencia respiratoria
    if current.respiratory_rate is not None and previous.respiratory_rate is not None:
        if current.respiratory_rate != previous.respiratory_rate:
            prev_s = score_respiratory_rate(previous.respiratory_rate).score
            curr_s = score_respiratory_rate(current.respiratory_rate).score
            diff = current.respiratory_rate - previous.respiratory_rate
            diff_sign = f"+{diff}" if diff > 0 else f"{diff}"
            changes.append({
                "parameter": "Frecuencia respiratoria",
                "previous_value": previous.respiratory_rate,
                "current_value": current.respiratory_rate,
                "change": f"{previous.respiratory_rate} -> {current.respiratory_rate} rpm ({diff_sign})",
                "score_change": f"{prev_s} -> {curr_s}",
                "description": (
                    f"Frecuencia respiratoria cambió de {previous.respiratory_rate} a "
                    f"{current.respiratory_rate} rpm (puntuación NEWS2: {prev_s} a {curr_s})."
                ),
            })

    # 2. Saturación de oxígeno
    if current.oxygen_saturation is not None and previous.oxygen_saturation is not None:
        if current.oxygen_saturation != previous.oxygen_saturation:
            changes.append({
                "parameter": "Saturación de oxígeno",
                "previous_value": previous.oxygen_saturation,
                "current_value": current.oxygen_saturation,
                "change": f"{previous.oxygen_saturation}% -> {current.oxygen_saturation}%",
                "description": (
                    f"Saturación de oxígeno varió de {previous.oxygen_saturation}% a "
                    f"{current.oxygen_saturation}%."
                ),
            })

    # 3. Oxígeno suplementario
    curr_o2 = bool(current.supplemental_oxygen)
    prev_o2 = bool(previous.supplemental_oxygen)
    if curr_o2 != prev_o2:
        curr_text = "Oxígeno suplementario" if curr_o2 else "Aire ambiente"
        prev_text = "Oxígeno suplementario" if prev_o2 else "Aire ambiente"
        changes.append({
            "parameter": "Oxígeno suplementario",
            "previous_value": prev_text,
            "current_value": curr_text,
            "change": f"{prev_text} -> {curr_text}",
            "description": f"Soporte ventilatorio modificado de {prev_text} a {curr_text}.",
        })

    # 4. Presión arterial sistólica
    if current.systolic_blood_pressure is not None and previous.systolic_blood_pressure is not None:
        if current.systolic_blood_pressure != previous.systolic_blood_pressure:
            prev_s = score_systolic_bp(previous.systolic_blood_pressure).score
            curr_s = score_systolic_bp(current.systolic_blood_pressure).score
            changes.append({
                "parameter": "Presión arterial sistólica",
                "previous_value": previous.systolic_blood_pressure,
                "current_value": current.systolic_blood_pressure,
                "change": f"{previous.systolic_blood_pressure} -> {current.systolic_blood_pressure} mmHg",
                "score_change": f"{prev_s} -> {curr_s}",
                "description": (
                    f"Presión sistólica cambió de {previous.systolic_blood_pressure} a "
                    f"{current.systolic_blood_pressure} mmHg (puntuación NEWS2: {prev_s} a {curr_s})."
                ),
            })

    # 5. Frecuencia cardíaca
    if current.heart_rate is not None and previous.heart_rate is not None:
        if current.heart_rate != previous.heart_rate:
            prev_s = score_heart_rate(previous.heart_rate).score
            curr_s = score_heart_rate(current.heart_rate).score
            changes.append({
                "parameter": "Frecuencia cardíaca",
                "previous_value": previous.heart_rate,
                "current_value": current.heart_rate,
                "change": f"{previous.heart_rate} -> {current.heart_rate} lpm",
                "score_change": f"{prev_s} -> {curr_s}",
                "description": (
                    f"Frecuencia cardíaca varió de {previous.heart_rate} a "
                    f"{current.heart_rate} lpm (puntuación NEWS2: {prev_s} a {curr_s})."
                ),
            })

    # 6. Temperatura corporal
    if current.temperature is not None and previous.temperature is not None:
        if round(current.temperature, 1) != round(previous.temperature, 1):
            prev_s = score_temperature(previous.temperature).score
            curr_s = score_temperature(current.temperature).score
            changes.append({
                "parameter": "Temperatura corporal",
                "previous_value": previous.temperature,
                "current_value": current.temperature,
                "change": f"{previous.temperature:.1f} -> {current.temperature:.1f} °C",
                "score_change": f"{prev_s} -> {curr_s}",
                "description": (
                    f"Temperatura corporal varió de {previous.temperature:.1f} a "
                    f"{current.temperature:.1f} °C (puntuación NEWS2: {prev_s} a {curr_s})."
                ),
            })

    # 7. Nivel de conciencia
    curr_c = str(current.consciousness_status).strip().upper() if current.consciousness_status else ""
    prev_c = str(previous.consciousness_status).strip().upper() if previous.consciousness_status else ""
    if curr_c != prev_c:
        changes.append({
            "parameter": "Nivel de conciencia (AVPU)",
            "previous_value": prev_c,
            "current_value": curr_c,
            "change": f"{prev_c} -> {curr_c}",
            "description": f"Nivel de conciencia alterado de '{prev_c}' a '{curr_c}'.",
        })

    return changes


def create_evaluation_from_news2(
    patient_id: int, measurement_id: int, news2_result: NEWS2Result
) -> Evaluation:
    """Crea una instancia del modelo Evaluation a partir del resultado del cálculo NEWS2.

    Args:
        patient_id: Identificador del paciente.
        measurement_id: Identificador de la medición evaluada.
        news2_result: Objeto con los resultados calculados de NEWS2.

    Returns:
        Evaluation: Objeto de modelo listo para ser persistido.
    """
    param_scores_map = {
        param.parameter_name: param.score for param in news2_result.parameter_results
    }

    return Evaluation(
        id=None,
        patient_id=patient_id,
        measurement_id=measurement_id,
        evaluated_at=datetime.now().isoformat(),
        scoring_method="NEWS2",
        score=news2_result.total_score,
        completeness_status="completo" if news2_result.is_complete else "incompleto",
        explanation=news2_result.explanation,
        risk_level=news2_result.risk_level,
        parameter_scores=json.dumps(param_scores_map, ensure_ascii=False),
    )
