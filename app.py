"""
IA Médica Asistencial - Prototipo Académico de Triaje y Priorización Dinámica.

Punto de entrada principal de la aplicación interactiva Streamlit desarrollada por
el equipo TechMinds para investigación académica y demostración docente.
"""

from datetime import datetime
import inspect
from typing import Any, Dict, List, Optional

import streamlit as st

import alert_engine
import config
import dashboard
import database
import models
import patient_service
import prioritization
import simulation
import validation


def init_app_state() -> None:
    """Inicializa la base de datos y las variables requeridas en el estado de sesión."""
    # Inicialización segura de la base de datos
    try:
        database.init_db()
    except Exception:
        st.error(
            "No fue posible inicializar la base de datos del sistema. "
            "Verifique la configuración de almacenamiento local."
        )

    # Inicialización del motor de alertas en sesión
    if "alert_engine" not in st.session_state:
        try:
            st.session_state.alert_engine = alert_engine.AlertEngine()
        except Exception:
            st.error(
                "Error al instanciar el motor de alertas clínicas. "
                "Revise la configuración de reglas."
            )

    # Estado de navegación y paciente seleccionado
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "🏠 Inicio"

    if "selected_patient_id" not in st.session_state:
        st.session_state["selected_patient_id"] = None

    if "simulation_results" not in st.session_state:
        st.session_state["simulation_results"] = None


def create_simulation_config_instance(config_dict: Optional[Dict[str, Any]]) -> models.SimulationConfig:
    """Crea una instancia válida de SimulationConfig resolviendo diferencias de nombres de atributos.

    Args:
        config_dict: Diccionario con parámetros ingresados en el formulario o None.

    Returns:
        Instancia de SimulationConfig lista para ejecutar la simulación.
    """
    if config_dict is None:
        config_dict = {}

    sig = inspect.signature(models.SimulationConfig)
    available_params = set(sig.parameters.keys())
    kwargs: Dict[str, Any] = {}

    # Número de pacientes
    if "num_patients" in available_params:
        kwargs["num_patients"] = int(config_dict.get("num_patients", config.SIM_DEFAULT_PATIENTS))

    # Duración de la simulación en horas
    if "duration_hours" in available_params:
        kwargs["duration_hours"] = float(config_dict.get("duration_hours", config.SIM_DEFAULT_DURATION_HOURS))

    # Intervalo de medición
    if "measurement_interval_minutes" in available_params:
        kwargs["measurement_interval_minutes"] = int(
            config_dict.get(
                "measurement_interval_minutes",
                config_dict.get("measurement_interval", config.SIM_DEFAULT_MEASUREMENT_INTERVAL_MINUTES),
            )
        )
    elif "measurement_interval" in available_params:
        kwargs["measurement_interval"] = int(
            config_dict.get(
                "measurement_interval",
                config_dict.get("measurement_interval_minutes", config.SIM_DEFAULT_MEASUREMENT_INTERVAL_MINUTES),
            )
        )

    # Semilla aleatoria
    if "random_seed" in available_params:
        kwargs["random_seed"] = int(config_dict.get("random_seed", config_dict.get("seed", config.SIM_RANDOM_SEED)))
    elif "seed" in available_params:
        kwargs["seed"] = int(config_dict.get("seed", config_dict.get("random_seed", config.SIM_RANDOM_SEED)))

    return models.SimulationConfig(**kwargs)


# ==============================================================================
# PÁGINAS DE LA APLICACIÓN
# ==============================================================================


def page_home() -> None:
    """Renderiza la página de inicio y visión general de la plataforma académica."""
    try:
        dashboard.render_home_page()
    except Exception:
        st.error("No se pudo cargar la página principal del sistema.")


def page_patient_panel() -> None:
    """Panel de gestión y visualización de pacientes registrados."""
    st.title("📋 Panel de Pacientes")
    st.markdown(
        "Consulte los pacientes activos en el servicio de urgencias, filtre por estado administrativo "
        "y actualice su situación en tiempo real."
    )

    col_filter1, col_filter2 = st.columns([2, 1])

    status_options = ["todos"] + list(config.ADMIN_STATUSES.keys())
    status_labels = {"todos": "Todos los estados", **config.ADMIN_STATUS_LABELS}

    with col_filter1:
        selected_status = st.selectbox(
            "Filtrar por estado administrativo:",
            options=status_options,
            format_func=lambda x: status_labels.get(x, x),
        )

    with col_filter2:
        include_simulated = st.checkbox(
            "Incluir pacientes simulados",
            value=True,
            help="Muestra tanto pacientes ingresados manualmente como generados por el simulador estocástico.",
        )

    status_filter_val = None if selected_status == "todos" else selected_status

    try:
        patients: List[models.Patient] = patient_service.get_patient_list(
            status_filter=status_filter_val,
            include_simulated=include_simulated,
        )
    except Exception:
        st.error("Error al consultar la lista de pacientes desde la base de datos.")
        patients = []

    st.subheader(f"Listado de Pacientes ({len(patients)} registros)")

    if not patients:
        st.info("No se encontraron pacientes con los criterios de búsqueda especificados.")
        return

    try:
        dashboard.render_patient_table(patients)
    except Exception:
        st.error("Error al renderizar la tabla de pacientes.")

    st.divider()
    st.subheader("Detalle y Gestión de Paciente Seleccionado")

    # Mapeo de pacientes para selección detallada
    patient_options = {
        p.id: f"{p.patient_code} - {p.full_name or p.name} (Triaje: {config.TRIAGE_LEVEL_LABELS.get(p.triage_level, 'N/D')}) - {config.ADMIN_STATUS_LABELS.get(p.administrative_status, p.administrative_status)}"
        for p in patients
    }

    current_selection_id = (
        st.session_state["selected_patient_id"]
        if st.session_state["selected_patient_id"] in patient_options
        else list(patient_options.keys())[0]
    )

    selected_id = st.selectbox(
        "Seleccione un paciente para inspeccionar:",
        options=list(patient_options.keys()),
        format_func=lambda pid: patient_options[pid],
        index=list(patient_options.keys()).index(current_selection_id),
    )
    st.session_state["selected_patient_id"] = selected_id

    try:
        patient_obj = patient_service.get_patient(selected_id)
        if patient_obj:
            patient_obj = patient_service.enrich_patient(patient_obj)
            dashboard.render_patient_card(patient_obj)
        else:
            st.warning("No se encontró la información del paciente seleccionado.")
            return
    except Exception:
        st.error("Error al obtener la información detallada del paciente.")
        return

    # Actualización de estado administrativo
    st.markdown("#### Actualizar Estado Administrativo")
    update_col1, update_col2 = st.columns([2, 1])

    current_status = patient_obj.administrative_status
    status_keys = list(config.ADMIN_STATUSES.keys())
    current_index = status_keys.index(current_status) if current_status in status_keys else 0

    with update_col1:
        new_status = st.selectbox(
            "Nuevo estado administrativo:",
            options=status_keys,
            format_func=lambda s: config.ADMIN_STATUS_LABELS.get(s, s),
            index=current_index,
            key=f"status_select_{patient_obj.id}",
        )

    with update_col2:
        st.write("")
        st.write("")
        if st.button("Guardar Cambio de Estado", type="primary", use_container_width=True):
            try:
                res = patient_service.update_status(patient_obj.id, new_status)
                if res.get("success", True):
                    st.success(
                        f"Estado actualizado a: {config.ADMIN_STATUS_LABELS.get(new_status, new_status)}"
                    )
                    st.rerun()
                else:
                    st.error(res.get("error", "No se pudo actualizar el estado administrativo."))
            except Exception:
                st.error("Ocurrió un error inesperado al actualizar el estado del paciente.")

    # Visualización del historial clínico del paciente
    with st.expander("Ver Historial Clínico Completo", expanded=False):
        try:
            history = patient_service.get_patient_history(patient_obj.id)
            measurements = history.get("measurements", [])
            evaluations = history.get("evaluations", [])

            st.markdown("##### Mediciones Registradas")
            if measurements:
                dashboard.render_measurement_history(measurements)
                dashboard.render_vitals_chart(measurements)
            else:
                st.info("Este paciente aún no tiene mediciones de signos vitales.")

            st.markdown("##### Historial de Evaluaciones Clínicas (NEWS2)")
            if evaluations:
                dashboard.render_evaluation_history(evaluations)
            else:
                st.info("Este paciente no cuenta con evaluaciones clínicas calculadas.")
        except Exception:
            st.error("Error al cargar el historial del paciente.")


def page_register_patient() -> None:
    """Formulario para la admisión y registro de un nuevo paciente."""
    st.title("➕ Registrar Nuevo Paciente")
    st.markdown(
        "Registre el ingreso de un paciente al servicio de urgencias. "
        "El identificador generado o suministrado servirá para el seguimiento durante todo el flujo de atención."
    )

    try:
        dashboard.render_disclaimer()
    except Exception:
        pass

    with st.form("form_register_patient", clear_on_submit=False):
        col_name, col_triage = st.columns([3, 2])
        with col_name:
            full_name_input = st.text_input(
                "Nombre completo del paciente (ficticio):",
                placeholder="Ej. Carlos Gómez (Ficticio)",
                help="Nombre del paciente para humanizar la atención asistencial.",
            )
        with col_triage:
            triage_level_input = st.selectbox(
                "Nivel de Triaje Profesional Inicial:",
                options=[1, 2, 3, 4, 5],
                format_func=lambda x: config.TRIAGE_LEVELS[x]['short_label'],
                index=2,  # Nivel III predeterminado
                help="Clasificación clínica profesional de admisión (I: Reanimación a V: No urgente).",
            )

        col_code1, col_code2 = st.columns([1, 2])
        with col_code1:
            auto_code = st.checkbox("Generar código automáticamente", value=True)
        with col_code2:
            if auto_code:
                suggested_code = patient_service.generate_patient_code()
                st.text_input(
                    "Código de paciente (autogenerado):",
                    value=suggested_code,
                    disabled=True,
                    help="Código único generado automáticamente siguiendo el estándar PAC-XXXXXX.",
                )
                final_code = suggested_code
            else:
                final_code = st.text_input(
                    "Código de paciente personalizado:",
                    placeholder="Ej. PAC-001234",
                    help="Ingrese un código único que cumpla con el formato institucional PAC-XXXXXX.",
                )

        col_symptom1, col_symptom2 = st.columns(2)
        with col_symptom1:
            symptom_suggestion = st.selectbox(
                "Motivo de consulta / Síntoma frecuente sugerido:",
                options=["-- Escribir síntoma personalizado o manual --"] + config.COMMON_SYMPTOMS,
            )
            symptoms_input = st.text_area(
                "Descripción detallada de síntomas reportados:",
                value="" if symptom_suggestion.startswith("--") else symptom_suggestion,
                placeholder="Describa el motivo de consulta, tiempo de evolución y síntomas principales...",
                help="Descripción clínica o textual de los síntomas reportados al ingreso.",
                height=100,
            )

        with col_symptom2:
            initial_diagnosis_input = st.text_area(
                "Diagnóstico inicial / Impresión diagnóstica:",
                placeholder="Ej. Sospecha de síndrome coronario agudo / Descarte de neumonía...",
                help="Sospecha diagnóstica inicial del personal asistencial al ingreso.",
                height=100,
            )

        col_date, col_time = st.columns(2)
        with col_date:
            arr_date = st.date_input("Fecha de llegada:", value=datetime.now().date())
        with col_time:
            arr_time = st.time_input("Hora de llegada:", value=datetime.now().time())

        is_simulated = st.checkbox(
            "Marcar como paciente simulado / de prueba",
            value=False,
            help="Indica si el paciente corresponde a una prueba sintética.",
        )

        submitted = st.form_submit_button("Registrar Paciente en Admisión", type="primary")

    if submitted:
        clean_code = final_code.strip() if final_code else None
        clean_name = full_name_input.strip() if full_name_input else None
        clean_symptoms = symptoms_input.strip() if symptoms_input else ""
        clean_dx = initial_diagnosis_input.strip() if initial_diagnosis_input else ""
        arrival_datetime_str = datetime.combine(arr_date, arr_time).isoformat()

        # Validación previa con validation.py
        if clean_code:
            code_val = validation.validate_patient_code(clean_code)
            if not code_val.is_valid:
                for err in code_val.errors:
                    st.error(f"Error en código de paciente: {err}")
                return

        if clean_name:
            name_val = validation.validate_patient_name(clean_name, required=False)
            if not name_val.is_valid:
                for err in name_val.errors:
                    st.error(f"Error en nombre: {err}")
                return

        arr_val = validation.validate_arrival_datetime(arrival_datetime_str)
        if not arr_val.is_valid:
            for err in arr_val.errors:
                st.error(f"Error en fecha/hora de llegada: {err}")
            return

        with st.spinner("Guardando registro de admisión..."):
            try:
                reg_res = patient_service.register_patient(
                    patient_code=clean_code,
                    full_name=clean_name,
                    arrival_at=arrival_datetime_str,
                    symptoms=clean_symptoms,
                    initial_diagnosis=clean_dx,
                    triage_level=triage_level_input,
                    is_simulated=is_simulated,
                )
                if reg_res.get("success", False) or "patient_id" in reg_res:
                    assigned_code = reg_res.get("patient_code", clean_code)
                    assigned_name = reg_res.get("full_name", clean_name or "Paciente Ficticio")
                    patient_id = reg_res.get("patient_id", "")
                    triage_lbl = config.TRIAGE_LEVEL_LABELS.get(triage_level_input, f"Nivel {triage_level_input}")
                    st.success(
                        f"¡Paciente registrado exitosamente! "
                        f"**{assigned_name}** | Código: **{assigned_code}** | Triaje: **{triage_lbl}** (ID: {patient_id})."
                    )
                    st.session_state["selected_patient_id"] = patient_id
                else:
                    st.error(reg_res.get("error", "No fue posible registrar el paciente."))
            except Exception:
                st.error("Ocurrió un error inesperado durante el registro del paciente.")


def page_register_measurement() -> None:
    """Captura de signos vitales y evaluación inmediata de NEWS2 y alertas."""
    st.title("📊 Registrar Medición de Signos Vitales")
    st.markdown(
        "Capture los signos vitales del paciente. Al guardar, el sistema calculará "
        "el puntaje NEWS2 según la especificación del Royal College of Physicians (2017) "
        "y emitirá alertas reactivas si se detecta deterioro fisiológico."
    )

    try:
        all_patients = patient_service.get_patient_list(include_simulated=True)
    except Exception:
        st.error("No se pudo obtener la lista de pacientes.")
        return

    # Pacientes aptos para recibir mediciones (en espera o en atención)
    eligible_patients = [
        p for p in all_patients if p.administrative_status in ("en_espera", "en_atencion")
    ]

    if not eligible_patients:
        st.warning(
            "No hay pacientes actualmente en estado 'En Espera' o 'En Atención' para registrar mediciones. "
            "Por favor, registre un nuevo paciente o actualice el estado de uno existente."
        )
        return

    patient_choices = {
        p.id: f"{p.patient_code} - {p.full_name or p.name} (Triaje: {config.TRIAGE_LEVEL_LABELS.get(p.triage_level, 'N/D')}) - {config.ADMIN_STATUS_LABELS.get(p.administrative_status, p.administrative_status)}"
        for p in eligible_patients
    }

    default_patient_id = (
        st.session_state["selected_patient_id"]
        if st.session_state["selected_patient_id"] in patient_choices
        else list(patient_choices.keys())[0]
    )

    selected_patient_id = st.selectbox(
        "Seleccione el paciente al que se le toman los signos vitales:",
        options=list(patient_choices.keys()),
        format_func=lambda pid: patient_choices[pid],
        index=list(patient_choices.keys()).index(default_patient_id),
    )
    st.session_state["selected_patient_id"] = selected_patient_id

    st.markdown("---")
    st.subheader("Formulario de Captura de Signos Vitales")

    try:
        form_data = dashboard.render_measurement_form()
    except Exception:
        st.error("Error al renderizar el formulario de signos vitales.")
        form_data = None

    if form_data is not None:
        # Validación de datos ingresados
        val_res = validation.validate_measurement(form_data)
        if not val_res.is_valid:
            for err in val_res.errors:
                st.error(f"Dato inválido: {err}")
            return

        with st.spinner("Registrando medición y evaluando condición clínica..."):
            try:
                reg_res = patient_service.register_measurement(
                    patient_id=selected_patient_id,
                    measurement_data=form_data,
                    source="manual",
                )
            except Exception:
                st.error("Error al persistir la medición en la base de datos.")
                return

            if not reg_res.get("success", False):
                for err in reg_res.get("errors", ["Error al guardar la medición."]):
                    st.error(err)
                return

            st.success("Medición fisiológica registrada satisfactoriamente.")
            for warn in reg_res.get("warnings", []):
                st.warning(warn)

            # Evaluación clínica inmediata mediante el motor de alertas
            try:
                measurement_obj = reg_res["measurement"]
                eval_res = st.session_state.alert_engine.evaluate_new_measurement(
                    patient_id=selected_patient_id,
                    measurement=measurement_obj,
                )
            except Exception:
                st.error("Error al procesar la evaluación clínica y alertas con el motor de reglas.")
                eval_res = {}

            # Visualización de resultados de NEWS2 y alertas generadas
            evaluation = eval_res.get("evaluation")
            if evaluation:
                st.subheader("Resultado de la Evaluación Clínica NEWS2")
                dashboard.render_evaluation_result(evaluation)

            alerts = eval_res.get("alerts", [])
            if alerts:
                st.warning(f"Se han generado {len(alerts)} alerta(s) de riesgo clínico.")
                dashboard.render_alert_panel(alerts)

            changes = eval_res.get("changes", [])
            if changes:
                with st.expander("Variaciones Fisiológicas Relevantes Detectadas", expanded=True):
                    for chg in changes:
                        st.info(f"• {chg.get('description', chg)}")

    # Mostrar histórico de mediciones y gráficos de tendencia
    st.divider()
    st.subheader("Evolución Temporal de Signos Vitales del Paciente")
    try:
        history = patient_service.get_patient_history(selected_patient_id)
        measurements = history.get("measurements", [])
        if measurements:
            dashboard.render_measurement_history(measurements)
            dashboard.render_vitals_chart(measurements)
        else:
            st.info("No se registran mediciones previas para este paciente.")
    except Exception:
        st.error("Error al cargar el historial temporal del paciente.")


def page_evaluation_and_alerts() -> None:
    """Visualización del estado NEWS2, historial de evaluaciones y atención de alertas."""
    st.title("⚡ Evaluación Clínica y Gestión de Alertas")
    st.markdown(
        "Monitoreo continuo del puntaje de alerta temprana (NEWS2) y resolución de "
        "alertas activas generadas por el motor de inferencia."
    )

    try:
        patients = patient_service.get_patient_list(include_simulated=True)
    except Exception:
        st.error("No se pudo cargar la lista de pacientes.")
        patients = []

    if not patients:
        st.info("No hay pacientes registrados en el sistema.")
        return

    patient_map = {
        p.id: f"{p.patient_code} - {p.full_name or p.name} (Triaje: {config.TRIAGE_LEVEL_LABELS.get(p.triage_level, 'N/D')}) - {config.ADMIN_STATUS_LABELS.get(p.administrative_status, p.administrative_status)}"
        for p in patients
    }

    default_id = (
        st.session_state["selected_patient_id"]
        if st.session_state["selected_patient_id"] in patient_map
        else list(patient_map.keys())[0]
    )

    selected_patient_id = st.selectbox(
        "Seleccione paciente para evaluar:",
        options=list(patient_map.keys()),
        format_func=lambda pid: patient_map[pid],
        index=list(patient_map.keys()).index(default_id),
    )
    st.session_state["selected_patient_id"] = selected_patient_id

    tab_eval, tab_alerts, tab_global_alerts = st.tabs(
        ["Evaluación NEWS2", "Alertas del Paciente", "Todas las Alertas Pendientes"]
    )

    with tab_eval:
        st.subheader("Última Evaluación Clínica Registrada")
        try:
            history = patient_service.get_patient_history(selected_patient_id)
            evaluations = history.get("evaluations", [])
            if evaluations:
                latest_eval = evaluations[-1]
                dashboard.render_evaluation_result(latest_eval)
                st.divider()
                st.subheader("Histórico Completo de Evaluaciones")
                dashboard.render_evaluation_history(evaluations)
            else:
                st.info("El paciente seleccionado aún no cuenta con evaluaciones clínicas calculadas.")
        except Exception:
            st.error("Error al cargar las evaluaciones del paciente.")

    def acknowledge_callback(alert_id: int) -> None:
        """Callback ejecutado al presionar atender alerta."""
        try:
            ack_res = st.session_state.alert_engine.acknowledge_alert(alert_id)
            if ack_res.get("success", True):
                st.success(f"Alerta #{alert_id} atendida exitosamente.")
                st.rerun()
            else:
                st.error(ack_res.get("error", "No fue posible atender la alerta."))
        except Exception:
            st.error("Error al registrar la atención de la alerta.")

    with tab_alerts:
        st.subheader("Alertas Pendientes del Paciente Seleccionado")
        try:
            patient_alerts = st.session_state.alert_engine.get_pending_alerts(patient_id=selected_patient_id)
            if patient_alerts:
                dashboard.render_alert_panel(patient_alerts, on_acknowledge=acknowledge_callback)
            else:
                st.success("No hay alertas clínicas pendientes para este paciente.")
        except Exception:
            st.error("Error al consultar las alertas del paciente.")

    with tab_global_alerts:
        st.subheader("Consola General de Alertas Pendientes en Urgencias")
        try:
            all_pending_alerts = st.session_state.alert_engine.get_pending_alerts()
            if all_pending_alerts:
                st.warning(f"Hay {len(all_pending_alerts)} alerta(s) activas en el servicio.")
                dashboard.render_alert_panel(all_pending_alerts, on_acknowledge=acknowledge_callback)
            else:
                st.success("No existen alertas clínicas pendientes en el servicio de urgencias.")
        except Exception:
            st.error("Error al consultar las alertas globales del sistema.")


def page_queue() -> None:
    """Cola de atención dinámica y priorización administrativa multidimensional."""
    st.title("📈 Cola de Atención Dinámica")
    st.markdown(
        "Priorización administrativa en tiempo real calculada a partir del puntaje NEWS2, "
        "alertas clínicas activas y tiempo acumulado de espera en la sala."
    )

    # Advertencia obligatoria
    st.warning(
        "⚠️ **AVISO METODOLÓGICO Y DE ALCANCE ACADÉMICO:** "
        "La cola de atención es una herramienta de ordenamiento y soporte a la gestión de flujos. "
        "**NO constituye triaje clínico normativo (Manchester/ESI I-V)** ni reemplaza el diagnóstico "
        "o la decisión del profesional de salud a cargo."
    )

    col_q1, col_q2 = st.columns([2, 1])
    with col_q1:
        include_simulated = st.checkbox(
            "Incluir pacientes simulados en la cola",
            value=True,
            help="Permite visualizar en el ordenamiento pacientes creados por el motor de simulación.",
        )
    with col_q2:
        if st.button("Actualizar Cola", type="secondary", use_container_width=True):
            st.rerun()

    try:
        queue: List[models.QueueEntry] = prioritization.build_queue(include_simulated=include_simulated)
    except Exception:
        st.error("Error al construir la cola de atención dinámica.")
        queue = []

    try:
        summary = prioritization.get_queue_summary(queue)
    except Exception:
        summary = {}

    st.subheader("Métricas Generales de la Cola")
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)

    with m_col1:
        st.metric(
            "Pacientes en Cola",
            summary.get("total_patients", len(queue)),
        )
    with m_col2:
        st.metric(
            "Riesgo Alto (NEWS2 ≥ 7)",
            summary.get("high_risk_count", 0),
        )
    with m_col3:
        st.metric(
            "Alertas Pendientes",
            summary.get("pending_alerts_count", 0),
        )
    with m_col4:
        avg_wait = summary.get("avg_wait_minutes", 0.0)
        st.metric(
            "Espera Promedio",
            dashboard.format_wait_time(avg_wait) if hasattr(dashboard, "format_wait_time") else f"{avg_wait:.1f} min",
        )

    st.divider()

    if not queue:
        st.info("No hay pacientes en espera de atención en este momento.")
        return

    col_view1, col_view2 = st.columns([3, 2])
    with col_view1:
        st.subheader("Orden de Prioridad Actual")
        try:
            dashboard.render_queue_table(queue)
        except Exception:
            st.error("Error al renderizar la tabla de la cola.")

    with col_view2:
        st.subheader("Distribución de Prioridad y Factores")
        try:
            dashboard.render_queue_chart(queue)
        except Exception:
            st.error("Error al renderizar el gráfico de la cola.")

    st.divider()
    st.subheader("Explicabilidad de la Posición en Cola")
    st.markdown(
        "Seleccione un paciente de la cola para inspeccionar los factores matemáticos que determinaron su lugar:"
    )

    entry_options = {
        entry.patient_id: f"#{entry.position} - Paciente: {entry.patient_code} (Prioridad: {entry.priority_score:.1f})"
        for entry in queue
    }

    selected_queue_id = st.selectbox(
        "Seleccione paciente en cola:",
        options=list(entry_options.keys()),
        format_func=lambda pid: entry_options[pid],
    )

    selected_entry = next((e for e in queue if e.patient_id == selected_queue_id), None)
    if selected_entry:
        try:
            explanation = prioritization.explain_position(selected_entry)
            st.info(explanation)
        except Exception:
            st.error("Error al generar la explicación de posición.")


def page_simulation() -> None:
    """Motor de simulación estocástica de flujo de pacientes y eventos en urgencias."""
    st.title("🔬 Simulación de Flujo y Estrés del Servicio")
    st.markdown(
        "Genere escenarios estocásticos de afluencia de pacientes, variaciones de signos vitales "
        "y eventos de deterioro para evaluar la reactividad de la cola y las alertas."
    )

    try:
        config_data = dashboard.render_simulation_config()
    except Exception:
        st.error("Error al cargar los controles de configuración de simulación.")
        config_data = None

    col_btn1, col_btn2 = st.columns([1, 1])

    with col_btn1:
        run_clicked = st.button("▶ Iniciar Simulación", type="primary", use_container_width=True)

    with col_btn2:
        clear_clicked = st.button(
            "🗑 Limpiar Datos de Simulación",
            type="secondary",
            use_container_width=True,
            help="Elimina pacientes, mediciones y alertas marcadas como simuladas.",
        )

    if clear_clicked:
        with st.spinner("Eliminando datos sintéticos de simulación..."):
            try:
                clear_res = simulation.clear_simulation_data()
                if clear_res.get("success", True):
                    st.session_state["simulation_results"] = None
                    st.success("Datos de simulación eliminados correctamente de la base de datos.")
                    st.rerun()
                else:
                    st.error(clear_res.get("error", "Error al limpiar datos simulados."))
            except Exception:
                st.error("Error inesperado al intentar limpiar los datos de simulación.")

    if run_clicked:
        sim_config = create_simulation_config_instance(config_data)

        # Validación formal de parámetros
        val_res = validation.validate_simulation_config(
            num_patients=sim_config.num_patients,
            duration_hours=getattr(sim_config, "duration_hours", 4.0),
            measurement_interval=getattr(
                sim_config,
                "measurement_interval_minutes",
                getattr(sim_config, "measurement_interval", 30),
            ),
            seed=getattr(sim_config, "random_seed", getattr(sim_config, "seed", 42)),
        )

        if not val_res.is_valid:
            for err in val_res.errors:
                st.error(f"Configuración inválida: {err}")
            return

        with st.spinner("Ejecutando simulación clínica estocástica..."):
            try:
                results = simulation.run_simulation(sim_config)
                st.session_state["simulation_results"] = results
                st.success("¡Simulación completada satisfactoriamente!")
            except Exception:
                st.error("Ocurrió un error inesperado durante la ejecución de la simulación.")

    # Mostrar resultados persistidos en sesión si existen
    results = st.session_state.get("simulation_results")
    if results:
        st.divider()
        st.subheader("Resultados de la Simulación")
        try:
            dashboard.render_simulation_results(results)
        except Exception:
            st.error("Error al renderizar el resumen de la simulación.")

        events = results.get("events", [])
        if events:
            st.divider()
            st.subheader("Línea de Tiempo de Eventos Simulados")
            try:
                dashboard.render_simulation_events(events)
            except Exception:
                st.error("Error al renderizar los eventos de la simulación.")

        snapshots = results.get("queue_snapshots", [])
        if snapshots:
            st.divider()
            st.subheader("Evolución Temporal de la Cola de Atención")
            try:
                dashboard.render_queue_evolution(snapshots)
            except Exception:
                st.error("Error al renderizar la evolución de la cola.")


def page_config_and_methodology() -> None:
    """Documentación técnica, fundamentación de NEWS2 y reglas del motor de alertas."""
    st.title("📚 Configuración y Metodología")
    st.markdown(
        "Consulte los fundamentos clínicos del score NEWS2 (Royal College of Physicians), "
        "las limitaciones del prototipo académico y configure las reglas activas del motor de alertas."
    )

    tab_methodology, tab_news2, tab_rules = st.tabs(
        ["Metodología y Alcance", "Especificación NEWS2", "Reglas de Alerta"]
    )

    with tab_methodology:
        try:
            dashboard.render_methodology_page()
        except Exception:
            st.error("Error al cargar la página de metodología.")

    with tab_news2:
        try:
            dashboard.render_news2_explanation()
        except Exception:
            st.error("Error al cargar la explicación detallada de NEWS2.")

    with tab_rules:
        st.subheader("Estado y Configuración de Reglas del Motor de Alertas")
        st.markdown(
            "Active o desactive las reglas de detección de riesgo fisiológico. "
            "Los cambios impactarán en la evaluación reactiva de las próximas mediciones."
        )

        try:
            rules_status = st.session_state.alert_engine.get_rules_status()
        except Exception:
            st.error("Error al consultar el estado de las reglas de alerta.")
            rules_status = {}

        if not rules_status:
            st.info("No hay reglas de alerta configuradas o expuestas por el motor.")
        else:
            for rule_name, is_enabled in rules_status.items():
                rule_desc = config.PRIORITY_RULES.get(rule_name, {}).get("description", rule_name)
                toggled = st.toggle(
                    f"**{rule_name}**: {rule_desc}",
                    value=is_enabled,
                    key=f"rule_toggle_{rule_name}",
                )

                if toggled != is_enabled:
                    try:
                        if toggled:
                            st.session_state.alert_engine.enable_rule(rule_name)
                            st.toast(f"Regla '{rule_name}' activada.", icon="✅")
                        else:
                            st.session_state.alert_engine.disable_rule(rule_name)
                            st.toast(f"Regla '{rule_name}' desactivada.", icon="⏸️")
                    except Exception:
                        st.error(f"Error al cambiar el estado de la regla '{rule_name}'.")


# ==============================================================================
# ENRUTAMIENTO PRINCIPAL
# ==============================================================================


def main() -> None:
    """Función principal de ejecución y enrutamiento de la aplicación."""
    # Configuración de página de Streamlit (OBLIGATORIAMENTE primera llamada Streamlit)
    st.set_page_config(
        page_title="IA Médica Asistencial | Triaje y Priorización",
        page_icon="🏥",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Inicialización del entorno
    init_app_state()

    # Barra lateral de navegación
    st.sidebar.title("🏥 IA Médica Asistencial")
    st.sidebar.caption(f"{config.APP_NAME} v{config.APP_VERSION}")
    st.sidebar.caption(f"Desarrollado por: **{config.TEAM_NAME}**")

    st.sidebar.markdown("---")

    menu_options = [
        "🏠 Inicio",
        "📋 Panel de Pacientes",
        "➕ Registrar Paciente",
        "📊 Registrar Medición",
        "⚡ Evaluación y Alertas",
        "📈 Cola de Atención",
        "🔬 Simulación",
        "📚 Configuración y Metodología",
    ]

    selected_nav = st.sidebar.radio(
        "Navegación:",
        options=menu_options,
        index=menu_options.index(st.session_state["current_page"])
        if st.session_state["current_page"] in menu_options
        else 0,
    )
    st.session_state["current_page"] = selected_nav

    # Conteo rápido de alertas en la barra lateral
    try:
        pending_alerts_count = len(st.session_state.alert_engine.get_pending_alerts())
        if pending_alerts_count > 0:
            st.sidebar.warning(f"⚠️ {pending_alerts_count} alerta(s) clínica(s) pendiente(s)")
    except Exception:
        pass

    st.sidebar.markdown("---")
    st.sidebar.caption(
        "**Uso Académico Exclusivo.** "
        "No utilizar para decisiones clínicas reales ni triaje normativo."
    )

    # Enrutamiento de páginas
    page_router = {
        "🏠 Inicio": page_home,
        "📋 Panel de Pacientes": page_patient_panel,
        "➕ Registrar Paciente": page_register_patient,
        "📊 Registrar Medición": page_register_measurement,
        "⚡ Evaluación y Alertas": page_evaluation_and_alerts,
        "📈 Cola de Atención": page_queue,
        "🔬 Simulación": page_simulation,
        "📚 Configuración y Metodología": page_config_and_methodology,
    }

    render_func = page_router.get(selected_nav, page_home)
    try:
        render_func()
    except Exception:
        st.error(
            "Ocurrió un error inesperado al procesar la vista solicitada. "
            "Por favor, vuelva a intentar la operación."
        )


if __name__ == "__main__":
    main()
