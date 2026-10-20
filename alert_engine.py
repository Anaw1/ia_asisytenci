"""Motor de reglas de alertas para IA Médica Asistencial.

Este módulo implementa el motor de reglas configurable para la detección,
generación y gestión de alertas clínicas y operativas en el entorno simulado.
Todas las alertas generadas son para soporte académico y toma de decisiones
asistida, sin reemplazar el criterio clínico profesional.
"""

import json
from datetime import datetime
from typing import List, Dict, Optional, Any

from models import Patient, Measurement, Evaluation, Alert
from database import (
    get_connection,
    insert_alert,
    get_alerts_for_patient,
    check_duplicate_alert,
    get_latest_measurement,
    get_latest_evaluation,
    get_measurements_for_patient,
    acknowledge_alert as db_acknowledge_alert,
    get_all_pending_alerts,
    insert_evaluation,
    get_patient_by_id,
)
from clinical_scoring import (
    calculate_news2,
    detect_measurement_changes,
    create_evaluation_from_news2,
    NEWS2Result,
)
from patient_service import compute_wait_time
from config import (
    ALERT_STATUS_PENDING,
    ALERT_STATUS_ACKNOWLEDGED,
    ALERT_TYPES,
    NEWS2_HIGH_SCORE_THRESHOLD,
    NEWS2_LOW_MEDIUM_TRIGGER,
    DATE_FORMAT,
)


class AlertRule:
    """Clase base para reglas configurables de generación de alertas."""

    def __init__(
        self,
        name: str,
        label: str,
        description: str,
        alert_type: str,
        requires_review: bool,
        enabled: bool = True,
    ):
        """Inicializa una regla de alerta.

        Args:
            name: Identificador único interno de la regla.
            label: Etiqueta descriptiva en español.
            description: Explicación en español de la condición evaluada.
            alert_type: Tipo de alerta correspondiente en ALERT_TYPES.
            requires_review: Si la alerta generada requiere revisión obligatoria.
            enabled: Estado de activación de la regla.
        """
        self.name = name
        self.label = label
        self.description = description
        self.alert_type = alert_type
        self.requires_review = requires_review
        self.enabled = enabled

    def evaluate(self, context: Dict[str, Any]) -> Optional[Alert]:
        """Evalúa el contexto y devuelve un objeto Alert si se cumple la condición, o None.

        Args:
            context: Diccionario con los datos del paciente, medición, evaluación y alertas previas.

        Returns:
            Optional[Alert]: Alerta generada o None.
        """
        raise NotImplementedError("Las subclases deben implementar el método evaluate.")


class NewMeasurementRule(AlertRule):
    """Genera una alerta informativa cuando se registra una nueva medición clínica."""

    def __init__(self, enabled: bool = True):
        super().__init__(
            name="new_measurement",
            label="Nueva medición registrada",
            description="Emite una notificación informativa cuando se registran nuevas constantes vitales.",
            alert_type="new_measurement",
            requires_review=False,
            enabled=enabled,
        )

    def evaluate(self, context: Dict[str, Any]) -> Optional[Alert]:
        measurement: Optional[Measurement] = context.get("new_measurement")
        patient: Optional[Patient] = context.get("patient")

        if measurement is None or patient is None or patient.id is None:
            return None

        reason = (
            f"Se ha registrado una nueva medición clínica para el paciente "
            f"(Fuente: {measurement.measurement_source})."
        )
        trigger_data = json.dumps(
            {
                "measurement_id": measurement.id,
                "recorded_at": measurement.recorded_at,
                "measurement_source": measurement.measurement_source,
            },
            ensure_ascii=False,
        )

        return Alert(
            id=None,
            patient_id=patient.id,
            evaluation_id=context.get("evaluation_id"),
            created_at=datetime.now().isoformat(),
            alert_type=self.alert_type,
            reason=reason,
            status=ALERT_STATUS_PENDING,
            acknowledged_at=None,
            rule_name=self.name,
            trigger_data=trigger_data,
        )


class ValueChangeRule(AlertRule):
    """Genera una alerta cuando se detectan variaciones significativas entre mediciones consecutivas."""

    def __init__(self, enabled: bool = True):
        super().__init__(
            name="value_change",
            label="Cambio significativo en signos vitales",
            description="Alerta cuando los signos vitales muestran variaciones o cambios de puntuación NEWS2.",
            alert_type="value_change",
            requires_review=True,
            enabled=enabled,
        )

    def evaluate(self, context: Dict[str, Any]) -> Optional[Alert]:
        changes: List[Dict[str, Any]] = context.get("changes", [])
        patient: Optional[Patient] = context.get("patient")

        if not changes or patient is None or patient.id is None:
            return None

        descriptions = [c.get("description", "") for c in changes if "description" in c]
        reason_summary = "; ".join(descriptions[:2])
        reason = f"Cambio clínico detectado: {reason_summary}"

        trigger_data = json.dumps({"changes": changes}, ensure_ascii=False)

        return Alert(
            id=None,
            patient_id=patient.id,
            evaluation_id=context.get("evaluation_id"),
            created_at=datetime.now().isoformat(),
            alert_type=self.alert_type,
            reason=reason,
            status=ALERT_STATUS_PENDING,
            acknowledged_at=None,
            rule_name=self.name,
            trigger_data=trigger_data,
        )


class IncompleteEvaluationRule(AlertRule):
    """Genera una alerta cuando una evaluación NEWS2 no puede completarse por falta de parámetros obligatorios."""

    def __init__(self, enabled: bool = True):
        super().__init__(
            name="incomplete_evaluation",
            label="Evaluación incompleta de signos vitales",
            description="Alerta cuando faltan parámetros fisiológicos obligatorios para calcular NEWS2.",
            alert_type="incomplete_evaluation",
            requires_review=True,
            enabled=enabled,
        )

    def evaluate(self, context: Dict[str, Any]) -> Optional[Alert]:
        news2_result: Optional[NEWS2Result] = context.get("news2_result")
        patient: Optional[Patient] = context.get("patient")

        if patient is None or patient.id is None or news2_result is None:
            return None

        if news2_result.is_complete:
            return None

        missing_list = news2_result.missing_parameters
        missing_str = ", ".join(missing_list)
        reason = f"Evaluación NEWS2 incompleta: faltan parámetros fisiológicos obligatorios ({missing_str})."

        trigger_data = json.dumps(
            {"missing_parameters": missing_list}, ensure_ascii=False
        )

        return Alert(
            id=None,
            patient_id=patient.id,
            evaluation_id=context.get("evaluation_id"),
            created_at=datetime.now().isoformat(),
            alert_type=self.alert_type,
            reason=reason,
            status=ALERT_STATUS_PENDING,
            acknowledged_at=None,
            rule_name=self.name,
            trigger_data=trigger_data,
        )


class HighScoreRule(AlertRule):
    """Genera una alerta cuando la puntuación NEWS2 alcanza nivel medio, alto o gatillo rojo."""

    def __init__(self, enabled: bool = True):
        super().__init__(
            name="high_score",
            label="Puntuación NEWS2 elevada (Riesgo alto)",
            description="Alerta ante deterioro clínico: puntaje medio (5-6), alto (≥7) o gatillo rojo individual (3).",
            alert_type="high_score",
            requires_review=True,
            enabled=enabled,
        )

    def evaluate(self, context: Dict[str, Any]) -> Optional[Alert]:
        news2_result: Optional[NEWS2Result] = context.get("news2_result")
        patient: Optional[Patient] = context.get("patient")

        if patient is None or patient.id is None or news2_result is None:
            return None

        if not news2_result.is_complete or news2_result.total_score is None:
            return None

        score = news2_result.total_score
        risk_level = news2_result.risk_level

        if score >= NEWS2_HIGH_SCORE_THRESHOLD:
            reason = (
                f"Puntuación NEWS2 crítica ({score} puntos): {news2_result.risk_label}. "
                f"Requiere valoración médica urgente."
            )
        elif risk_level == "medium":
            reason = (
                f"Puntuación NEWS2 moderada ({score} puntos): {news2_result.risk_label}. "
                f"Requiere revisión asistencial."
            )
        elif risk_level == "low_medium":
            reason = (
                f"Alerta de gatillo rojo individual en NEWS2 ({score} puntos): "
                f"al menos un parámetro fisiológico presenta puntuación crítica (3)."
            )
        else:
            return None

        trigger_data = json.dumps(
            {
                "score": score,
                "risk_level": risk_level,
                "risk_label": news2_result.risk_label,
                "scale_used": news2_result.scale_used,
            },
            ensure_ascii=False,
        )

        return Alert(
            id=None,
            patient_id=patient.id,
            evaluation_id=context.get("evaluation_id"),
            created_at=datetime.now().isoformat(),
            alert_type=self.alert_type,
            reason=reason,
            status=ALERT_STATUS_PENDING,
            acknowledged_at=None,
            rule_name=self.name,
            trigger_data=trigger_data,
        )


class LongWaitRule(AlertRule):
    """Genera una alerta cuando el tiempo de espera del paciente excede el umbral determinado."""

    def __init__(self, wait_threshold_minutes: int = 60, enabled: bool = True, **kwargs):
        super().__init__(
            name="long_wait",
            label="Tiempo de espera prolongado sin reevaluación",
            description=f"Alerta cuando el paciente en espera supera los {wait_threshold_minutes} minutos sin atención.",
            alert_type="long_wait",
            requires_review=True,
            enabled=enabled,
        )
        self.wait_threshold_minutes = wait_threshold_minutes

    def evaluate(self, context: Dict[str, Any]) -> Optional[Alert]:
        patient: Optional[Patient] = context.get("patient")
        if patient is None or patient.id is None:
            return None

        # Solo aplica si el paciente se encuentra activamente en espera
        if patient.administrative_status != "en_espera":
            return None

        wait_time = context.get("wait_time_minutes", 0.0)
        if wait_time >= self.wait_threshold_minutes:
            reason = (
                f"Tiempo de espera prolongado: el paciente lleva {wait_time:.0f} minutos en espera "
                f"(umbral configurado: {self.wait_threshold_minutes} min)."
            )
            trigger_data = json.dumps(
                {
                    "wait_time_minutes": wait_time,
                    "threshold_minutes": self.wait_threshold_minutes,
                },
                ensure_ascii=False,
            )

            return Alert(
                id=None,
                patient_id=patient.id,
                evaluation_id=context.get("evaluation_id"),
                created_at=datetime.now().isoformat(),
                alert_type=self.alert_type,
                reason=reason,
                status=ALERT_STATUS_PENDING,
                acknowledged_at=None,
                rule_name=self.name,
                trigger_data=trigger_data,
            )

        return None


class UnacknowledgedAlertRule(AlertRule):
    """Genera una alerta cuando existen múltiples alertas acumuladas sin reconocer."""

    def __init__(self, enabled: bool = True):
        super().__init__(
            name="unacknowledged_alert",
            label="Alerta previa sin reconocer",
            description="Alerta cuando un paciente acumula múltiples avisos clínicos sin gestión asistencial.",
            alert_type="unacknowledged_alert",
            requires_review=True,
            enabled=enabled,
        )

    def evaluate(self, context: Dict[str, Any]) -> Optional[Alert]:
        patient: Optional[Patient] = context.get("patient")
        if patient is None or patient.id is None:
            return None

        pending_alerts: List[Alert] = context.get("pending_alerts", [])
        if len(pending_alerts) >= 2:
            reason = (
                f"Acumulación de alertas: el paciente presenta {len(pending_alerts)} alertas "
                f"pendientes de reconocimiento."
            )
            trigger_data = json.dumps(
                {
                    "pending_count": len(pending_alerts),
                    "alert_ids": [a.id for a in pending_alerts if a.id is not None],
                },
                ensure_ascii=False,
            )

            return Alert(
                id=None,
                patient_id=patient.id,
                evaluation_id=context.get("evaluation_id"),
                created_at=datetime.now().isoformat(),
                alert_type=self.alert_type,
                reason=reason,
                status=ALERT_STATUS_PENDING,
                acknowledged_at=None,
                rule_name=self.name,
                trigger_data=trigger_data,
            )

        return None


class AlertEngine:
    """Motor principal de gestión, evaluación y ejecución de reglas de alerta."""

    def __init__(self, db_path: Optional[str] = None):
        """Inicializa el motor de alertas.

        Args:
            db_path: Ruta opcional a la base de datos SQLite.
        """
        self.db_path = db_path
        self.rules: List[AlertRule] = []
        self._register_default_rules()

    def _register_default_rules(self) -> None:
        """Registra el conjunto predeterminado de reglas de alerta."""
        self.rules = [
            NewMeasurementRule(),
            ValueChangeRule(),
            IncompleteEvaluationRule(),
            HighScoreRule(),
            LongWaitRule(wait_threshold_minutes=60),
            UnacknowledgedAlertRule(),
        ]

    def add_rule(self, rule: AlertRule) -> None:
        """Añade una regla personalizada al motor de alertas.

        Args:
            rule: Instancia de AlertRule a registrar.
        """
        self.rules.append(rule)

    def enable_rule(self, rule_name: str) -> bool:
        """Activa una regla existente por su nombre o alias.

        Args:
            rule_name: Nombre interno de la regla.

        Returns:
            bool: True si la regla fue encontrada y activada, False en caso contrario.
        """
        for rule in self.rules:
            if rule.name == rule_name or rule_name.lower() in (rule.name.lower(), rule.alert_type.lower()):
                rule.enabled = True
                return True
        return False

    def disable_rule(self, rule_name: str) -> bool:
        """Desactiva una regla existente por su nombre o alias.

        Args:
            rule_name: Nombre interno de la regla.

        Returns:
            bool: True si la regla fue encontrada y desactivada, False en caso contrario.
        """
        for rule in self.rules:
            if rule.name == rule_name or rule_name.lower() in (rule.name.lower(), rule.alert_type.lower()):
                rule.enabled = False
                return True
        return False

    def get_rules_status(self) -> List[Dict[str, Any]]:
        """Devuelve la lista de reglas configuradas con su estado y detalles.

        Returns:
            List[Dict[str, Any]]: Lista con metadatos y estado de cada regla.
        """
        return [
            {
                "name": rule.name,
                "label": rule.label,
                "description": rule.description,
                "alert_type": rule.alert_type,
                "requires_review": rule.requires_review,
                "enabled": rule.enabled,
            }
            for rule in self.rules
        ]

    def evaluate_patient(
        self,
        patient_id: int,
        new_measurement: Optional[Measurement] = None,
        evaluation_id: Optional[int] = None,
        news2_result: Optional[NEWS2Result] = None,
        changes: Optional[List[Dict[str, Any]]] = None,
    ) -> List[Alert]:
        """Evalúa todas las reglas activas para un paciente determinado.

        Crea y persiste las alertas que se activen, evitando duplicados en los últimos 5 minutos.

        Args:
            patient_id: Identificador del paciente.
            new_measurement: Medición recién registrada (opcional).
            evaluation_id: Identificador de la evaluación asociada (opcional).
            news2_result: Resultado precalculado de NEWS2 (opcional).
            changes: Lista precalculada de cambios respecto a medición anterior (opcional).

        Returns:
            List[Alert]: Lista de alertas creadas y persistidas en la base de datos.
        """
        conn = get_connection(self.db_path)
        new_alerts: List[Alert] = []
        try:
            patient = get_patient_by_id(conn, patient_id)
            if patient is None:
                return []

            pending_alerts = get_alerts_for_patient(
                conn, patient_id, status_filter=ALERT_STATUS_PENDING
            )
            wait_time = compute_wait_time(patient.arrival_at) if patient.arrival_at else 0.0

            # Determinar medición para evaluación NEWS2 si no fue provista
            if news2_result is None:
                m_to_eval = new_measurement or get_latest_measurement(conn, patient_id)
                if m_to_eval is not None:
                    news2_result = calculate_news2(m_to_eval)

            # Determinar evaluación id si no fue provista
            if evaluation_id is None:
                latest_ev = get_latest_evaluation(conn, patient_id)
                if latest_ev is not None:
                    evaluation_id = latest_ev.id

            # Determinar cambios si no fueron provistos
            if changes is None:
                all_meas = get_measurements_for_patient(conn, patient_id)
                if len(all_meas) >= 2:
                    # all_meas está ordenada ASC: el último es el más reciente
                    changes = detect_measurement_changes(all_meas[-1], all_meas[-2])
                else:
                    changes = []

            context = {
                "patient": patient,
                "new_measurement": new_measurement,
                "evaluation_id": evaluation_id,
                "news2_result": news2_result,
                "changes": changes,
                "pending_alerts": pending_alerts,
                "wait_time_minutes": wait_time,
            }

            for rule in self.rules:
                if not rule.enabled:
                    continue

                alert_candidate = rule.evaluate(context)
                if alert_candidate is not None:
                    # Evitar duplicados recientes
                    is_duplicate = check_duplicate_alert(
                        conn, patient_id, alert_candidate.alert_type, since_minutes=5
                    )
                    if not is_duplicate:
                        alert_id = insert_alert(conn, alert_candidate)
                        alert_candidate.id = alert_id
                        new_alerts.append(alert_candidate)

            return new_alerts
        finally:
            conn.close()

    def evaluate_new_measurement(
        self, patient_id: int, measurement: Measurement
    ) -> Dict[str, Any]:
        """Procesa una nueva medición: calcula NEWS2, detecta cambios y ejecuta reglas de alertas.

        Punto de entrada principal tras registrar una medición para un paciente.

        Args:
            patient_id: Identificador del paciente.
            measurement: Medición recién registrada.

        Returns:
            Dict[str, Any]: Diccionario con 'evaluation', 'alerts', 'changes'.
        """
        if measurement is None or measurement.id is None:
            raise ValueError(
                "La medición debe registrarse en la base de datos (con id) antes de evaluarla."
            )

        # 1. Calcular NEWS2
        news2_result = calculate_news2(measurement)

        # 2. Persistir evaluación
        evaluation = create_evaluation_from_news2(patient_id, measurement.id, news2_result)
        conn = get_connection(self.db_path)
        changes: List[Dict[str, Any]] = []
        try:
            eval_id = insert_evaluation(conn, evaluation)
            evaluation.id = eval_id

            # 3. Detectar cambios frente a medición anterior
            all_meas = get_measurements_for_patient(conn, patient_id)
            prev_meas = None
            # all_meas viene ordenada ASC; buscar la penúltima (la anterior a la actual)
            for m in reversed(all_meas):
                if m.id != measurement.id:
                    prev_meas = m
                    break

            if prev_meas is not None:
                changes = detect_measurement_changes(measurement, prev_meas)
        finally:
            conn.close()

        # 4. Evaluar reglas de alerta
        alerts = self.evaluate_patient(
            patient_id=patient_id,
            new_measurement=measurement,
            evaluation_id=evaluation.id,
            news2_result=news2_result,
            changes=changes,
        )

        # 5. Devolver resultados
        return {
            "evaluation": evaluation,
            "alerts": alerts,
            "changes": changes,
        }

    def acknowledge_alert(self, alert_id: int) -> bool:
        """Registra el reconocimiento asistencial de una alerta pendiente.

        Args:
            alert_id: Identificador de la alerta.

        Returns:
            bool: True si la alerta fue reconocida exitosamente, False en caso contrario.
        """
        conn = get_connection(self.db_path)
        try:
            return db_acknowledge_alert(conn, alert_id)
        finally:
            conn.close()

    def get_pending_alerts(self, patient_id: Optional[int] = None) -> List[Alert]:
        """Obtiene las alertas pendientes, opcionalmente filtradas por paciente.

        Args:
            patient_id: Identificador opcional del paciente.

        Returns:
            List[Alert]: Lista de alertas en estado pendiente.
        """
        conn = get_connection(self.db_path)
        try:
            if patient_id is not None:
                return get_alerts_for_patient(
                    conn, patient_id, status_filter=ALERT_STATUS_PENDING
                )
            return get_all_pending_alerts(conn)
        finally:
            conn.close()

    def get_alert_history(self, patient_id: int) -> List[Alert]:
        """Obtiene el historial completo de alertas de un paciente.

        Args:
            patient_id: Identificador del paciente.

        Returns:
            List[Alert]: Lista cronológica de todas las alertas del paciente.
        """
        conn = get_connection(self.db_path)
        try:
            return get_alerts_for_patient(conn, patient_id)
        finally:
            conn.close()
