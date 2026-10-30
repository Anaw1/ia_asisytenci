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


# Mapa de migración de nombres antiguos de página al nuevo flujo de 6 pantallas
LEGACY_PAGE_REDIRECTS: Dict[str, str] = {
    "📋 Panel de Pacientes": "👥 Pacientes",
    "➕ Registrar Paciente": "👥 Pacientes",
    "📊 Registrar Medición": "🩺 Atención",
    "⚡ Evaluación y Alertas": "🩺 Atención",
    "📚 Configuración y Metodología": "📚 Metodología y Configuración",
}

MENU_OPTIONS: List[str] = [
    "🏠 Inicio",
    "👥 Pacientes",
    "🩺 Atención",
    "📈 Cola de Atención",
    "🔬 Simulación",
    "📚 Metodología y Configuración",
]


def init_app_state() -> None:
    """Inicializa la base de datos y las variables requeridas en el estado de sesión."""
    try:
        database.init_db()
    except Exception:
        st.error(
            "No fue posible inicializar la base de datos del sistema. "
            "Verifique la configuración de almacenamiento local."
        )

    if "alert_engine" not in st.session_state:
        try:
            st.session_state.alert_engine = alert_engine.AlertEngine()
        except Exception:
            st.error(
                "Error al instanciar el motor de alertas clínicas. "
                "Revise la configuración de reglas."
            )

    if "current_page" not in st.session_state:
        st.session_state["current_page"] = "🏠 Inicio"
    elif st.session_state["current_page"] in LEGACY_PAGE_REDIRECTS:
        st.session_state["current_page"] = LEGACY_PAGE_REDIRECTS[st.session_state["current_page"]]

    if "selected_patient_id" not in st.session_state:
        st.session_state["selected_patient_id"] = None

    if "simulation_results" not in st.session_state:
        st.session_state["simulation_results"] = None

    if "show_register_form" not in st.session_state:
        st.session_state["show_register_form"] = False

    if "last_care_eval_result" not in st.session_state:
        st.session_state["last_care_eval_result"] = None


def create_simulation_config_instance(config_dict: Optional[Dict[str, Any]]) -> models.SimulationConfig:
    """Crea una instancia válida de SimulationConfig resolviendo diferencias de nombres de atributos."""
    if config_dict is None:
        config_dict = {}

    sig = inspect.signature(models.SimulationConfig)
    available_params = set(sig.parameters.keys())
    kwargs: Dict[str, Any] = {}

    if "num_patients" in available_params:
        kwargs["num_patients"] = int(config_dict.get("num_patients", config.SIM_DEFAULT_PATIENTS))

    if "duration_hours" in available_params:
        kwargs["duration_hours"] = int(round(float(config_dict.get("duration_hours", config.SIM_DEFAULT_DURATION_HOURS))))

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

    if "random_seed" in available_params:
        kwargs["random_seed"] = int(config_dict.get("random_seed", config.SIM_RANDOM_SEED))
    elif "seed" in available_params:
        kwargs["seed"] = int(config_dict.get("seed", config.SIM_RANDOM_SEED))

    return models.SimulationConfig(**kwargs)


# ==============================================================================
# 1. PÁGINA: INICIO
# ==============================================================================


def page_home() -> None:
    """Renderiza la página de inicio con resumen del prototipo, métricas reales y accesos claros."""
    try:
        patients = patient_service.get_patient_list(include_simulated=True)
    except Exception:
        patients = []

    try:
        dashboard.render_home_page(patients=patients)
    except Exception:
        st.error("No se pudo cargar la página principal del sistema.")


# ==============================================================================
# 2. PÁGINA: PACIENTES (LISTADO + REGISTRO + DETALLE)
# ==============================================================================


def _render_patient_registration_section(expanded_default: bool = False) -> None:
    """Renderiza el formulario de registro de un nuevo paciente sin asignar triaje silencioso."""
    with st.expander(
        "➕ Registrar Nuevo Paciente en Admisión",
        expanded=expanded_default or st.session_state.get("show_register_form", False),
    ):
        st.markdown(
            "Complete los datos de ingreso del paciente ficticio. "
            "**Nota clínica:** el nivel de triaje no se preasigna automáticamente; seleccione explícitamente "
            "la categoría valorada en admisión o déjelo como *Pendiente de verificación / Sin clasificar*."
        )

        triage_options: List[Optional[int]] = [None, 1, 2, 3, 4, 5]
        triage_labels_map: Dict[Optional[int], str] = {
            None: "⏳ Pendiente de verificación / Sin clasificar en admisión",
            **{lvl: info["label"] for lvl, info in config.TRIAGE_LEVELS.items()},
        }

        with st.form("form_register_patient", clear_on_submit=False):
            col_name, col_triage = st.columns([3, 2])
            with col_name:
                full_name_input = st.text_input(
                    "Nombre completo del paciente (ficticio):",
                    placeholder="Ej. Carlos Andrés Mendoza (Ficticio)",
                    help="Nombre ficticio del paciente para humanizar el seguimiento académico.",
                )
            with col_triage:
                triage_level_input = st.selectbox(
                    "Clasificación de Triaje en Admisión:",
                    options=triage_options,
                    format_func=lambda x: triage_labels_map.get(x, "Sin clasificar"),
                    index=0,
                    help="Seleccione explícitamente el nivel I a V si ya fue valorado, o manténgalo pendiente de verificación.",
                )

            col_code1, col_code2 = st.columns([1, 2])
            with col_code1:
                auto_code = st.checkbox("Generar código institucional automáticamente", value=True)
            with col_code2:
                if auto_code:
                    suggested_code = patient_service.generate_patient_code()
                    st.text_input(
                        "Código de paciente (se asignará automáticamente al guardar):",
                        value=suggested_code,
                        disabled=True,
                        help="Código único generado siguiendo el estándar PAC-XXXXXXXX.",
                    )
                    final_code = None
                else:
                    final_code = st.text_input(
                        "Código de paciente personalizado:",
                        placeholder="Ej. PAC-001234",
                        help="Ingrese un código único que cumpla con el formato alfanumérico institucional.",
                    )

            col_symptom1, col_symptom2 = st.columns(2)
            with col_symptom1:
                symptom_suggestion = st.selectbox(
                    "Plantilla rápida de síntomas (opcional):",
                    options=["-- Escribir síntoma personalizado --"] + config.COMMON_SYMPTOMS,
                )
                symptoms_input = st.text_area(
                    "Síntomas principales reportados:",
                    value="" if symptom_suggestion.startswith("--") else symptom_suggestion,
                    placeholder="Describa el motivo de consulta, tiempo de evolución y síntomas referidos...",
                    height=95,
                )

            with col_symptom2:
                initial_diagnosis_input = st.text_area(
                    "Impresión diagnóstica / Sospecha inicial:",
                    placeholder="Ej. Síndrome febril agudo en estudio / Pendiente valoración médica...",
                    height=95,
                )

            col_date, col_time, col_sim = st.columns([1.2, 1.2, 1.6])
            with col_date:
                arr_date = st.date_input("Fecha de ingreso:", value=datetime.now().date())
            with col_time:
                arr_time = st.time_input("Hora de ingreso:", value=datetime.now().time())
            with col_sim:
                st.write("")
                st.write("")
                is_simulated = st.checkbox(
                    "Marcar como paciente simulado / sintético",
                    value=False,
                    help="Permite filtrarlo separadamente de los registros manuales.",
                )

            submitted = st.form_submit_button("💾 Registrar Paciente en Admisión", type="primary", use_container_width=True)

        if submitted:
            clean_code = final_code.strip() if final_code else None
            clean_name = full_name_input.strip() if full_name_input else None
            clean_symptoms = symptoms_input.strip() if symptoms_input else ""
            clean_dx = initial_diagnosis_input.strip() if initial_diagnosis_input else ""
            arrival_datetime_str = datetime.combine(arr_date, arr_time).isoformat()

            with st.spinner("Validando y registrando admisión..."):
                reg_res = patient_service.register_patient(
                    patient_code=clean_code,
                    full_name=clean_name,
                    arrival_at=arrival_datetime_str,
                    symptoms=clean_symptoms,
                    initial_diagnosis=clean_dx,
                    triage_level=triage_level_input,
                    is_simulated=is_simulated,
                )
                if reg_res.get("success", False):
                    assigned_code = reg_res.get("patient_code", clean_code)
                    assigned_name = reg_res.get("full_name", clean_name or "Paciente Ficticio")
                    patient_id = reg_res.get("patient_id")
                    triage_lbl = (
                        config.TRIAGE_LEVEL_LABELS.get(triage_level_input, f"Nivel {triage_level_input}")
                        if triage_level_input is not None
                        else "Pendiente de verificación / Sin clasificar"
                    )
                    st.session_state["selected_patient_id"] = patient_id
                    st.session_state["show_register_form"] = False
                    st.success(
                        f"✅ Paciente registrado: **{assigned_name}** (`{assigned_code}`) | "
                        f"Triaje: **{triage_lbl}**."
                    )
                    st.rerun()
                else:
                    for err in reg_res.get("errors", ["No fue posible registrar el paciente."]):
                        st.error(err)


def page_patients() -> None:
    """Vista unificada de listado, admisión y ficha detallada de pacientes."""
    col_title, col_action = st.columns([3, 1.2])
    with col_title:
        st.title("👥 Gestión y Padrón de Pacientes")
        st.markdown(
            "Consulte el listado general de pacientes, registre nuevos ingresos y revise la ficha clínica "
            "y administrativa de cada paciente seleccionado."
        )
    with col_action:
        st.write("")
        if st.button(
            "➕ Nuevo Paciente" if not st.session_state.get("show_register_form") else "✖ Ocultar Formulario",
            type="primary",
            use_container_width=True,
        ):
            st.session_state["show_register_form"] = not st.session_state.get("show_register_form", False)
            st.rerun()

    # Sección desplegable de registro de paciente
    _render_patient_registration_section()

    st.divider()

    # Controles de filtrado del listado principal
    col_filter1, col_filter2 = st.columns([2, 1])
    status_options = ["todos"] + list(config.ADMIN_STATUSES.keys())
    status_labels = {"todos": "Todos los estados administrativos", **config.ADMIN_STATUS_LABELS}

    with col_filter1:
        selected_status = st.selectbox(
            "Filtrar listado por estado administrativo:",
            options=status_options,
            format_func=lambda x: status_labels.get(x, x),
        )

    with col_filter2:
        st.write("")
        include_simulated = st.checkbox(
            "Incluir pacientes simulados",
            value=True,
            help="Permite incluir o excluir de la tabla los pacientes sintéticos generados por el módulo de simulación.",
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
        st.info(
            "No se encontraron pacientes con los filtros actuales. "
            "Use el botón **➕ Nuevo Paciente** arriba para registrar un ingreso."
        )
        return

    dashboard.render_patient_table(patients)

    st.divider()
    st.subheader("Ficha Detallada del Paciente Seleccionado")

    patient_options = {
        p.id: (
            f"{p.patient_code} — {p.full_name or p.name} | "
            f"Triaje: {config.TRIAGE_LEVEL_LABELS.get(p.triage_level, 'Sin clasificar')} | "
            f"Estado: {config.ADMIN_STATUS_LABELS.get(p.administrative_status, p.administrative_status)}"
        )
        for p in patients
    }

    current_selection_id = (
        st.session_state["selected_patient_id"]
        if st.session_state["selected_patient_id"] in patient_options
        else list(patient_options.keys())[0]
    )

    sel_col1, sel_col2 = st.columns([3, 1.2])
    with sel_col1:
        selected_id = st.selectbox(
            "Seleccione un paciente para inspeccionar su detalle e historial:",
            options=list(patient_options.keys()),
            format_func=lambda pid: patient_options[pid],
            index=list(patient_options.keys()).index(current_selection_id),
        )
        st.session_state["selected_patient_id"] = selected_id
    with sel_col2:
        st.write("")
        if st.button("🩺 Ir a Atención de este Paciente", type="primary", use_container_width=True):
            st.session_state["selected_patient_id"] = selected_id
            st.session_state["current_page"] = "🩺 Atención"
            st.rerun()

    try:
        history = patient_service.get_patient_history(selected_id)
        patient_obj = history.get("patient")
        measurements = history.get("measurements", [])
        evaluations = history.get("evaluations", [])
        alerts = history.get("alerts", [])
        latest_meas = measurements[-1] if measurements else None
    except Exception:
        st.error("Error al obtener la ficha detallada del paciente.")
        return

    if not patient_obj:
        st.warning("No se encontró la información del paciente seleccionado.")
        return

    dashboard.render_patient_card(patient_obj, latest_measurement=latest_meas)

    # Gestión de estado administrativo
    st.markdown("#### Gestión de Estado Administrativo")
    update_col1, update_col2 = st.columns([2.5, 1])

    current_status = patient_obj.administrative_status
    status_keys = list(config.ADMIN_STATUSES.keys())
    current_index = status_keys.index(current_status) if current_status in status_keys else 0

    with update_col1:
        new_status = st.selectbox(
            "Cambiar estado administrativo del paciente:",
            options=status_keys,
            format_func=lambda s: config.ADMIN_STATUS_LABELS.get(s, s),
            index=current_index,
            key=f"status_select_{patient_obj.id}",
            help="Al pasar a 'Atendido' o 'Alta', el paciente sale de la cola de espera activa y detiene su contador de espera.",
        )

    with update_col2:
        st.write("")
        if st.button("Actualizar Estado", use_container_width=True):
            res = patient_service.update_status(patient_obj.id, new_status)
            if res.get("success", False):
                st.success(
                    f"Estado actualizado a: {config.ADMIN_STATUS_LABELS.get(new_status, new_status)}"
                )
                st.rerun()
            else:
                for err in res.get("errors", ["No se pudo actualizar el estado."]):
                    st.error(err)

    # Historial clínico y alertas en desplegables ordenados
    with st.expander(
        f"📊 Historial de Mediciones ({len(measurements)}) y Evaluaciones NEWS2 ({len(evaluations)})",
        expanded=False,
    ):
        if measurements:
            st.markdown("##### Constantes Vitales Registradas")
            dashboard.render_measurement_history(measurements)
            dashboard.render_vitals_chart(measurements)
        else:
            st.info("Este paciente aún no registra mediciones de signos vitales.")

        if evaluations:
            st.markdown("##### Evolución de Evaluaciones NEWS2")
            dashboard.render_evaluation_history(evaluations)
        else:
            st.info("Este paciente aún no cuenta con evaluaciones NEWS2.")

    with st.expander("🗑️ Dar de Baja / Eliminar Paciente del Registro", expanded=False):
        st.warning(
            f"⚠️ **Advertencia:** Esta acción eliminará permanentemente al paciente "
            f"**{patient_obj.full_name or 'Sin nombre'}** (`{patient_obj.patient_code}`) "
            f"y todos sus registros asociados.",
            icon="⚠️",
        )
        confirm_delete = st.checkbox(
            f"Confirmo que deseo eliminar definitivamente a {patient_obj.patient_code}",
            key=f"chk_confirm_delete_{patient_obj.id}",
        )
        if st.button(
            "🗑 Eliminar Paciente Definitivamente",
            type="primary",
            disabled=not confirm_delete,
            key=f"btn_delete_patient_{patient_obj.id}",
            use_container_width=True,
        ):
            del_res = patient_service.delete_patient(patient_obj.id)
            if del_res.get("success"):
                st.session_state["selected_patient_id"] = None
                st.success(del_res.get("message", "Paciente eliminado exitosamente."))
                st.rerun()
            else:
                errors_msg = ", ".join(del_res.get("errors", ["Error desconocido"]))
                st.error(f"No fue posible eliminar al paciente: {errors_msg}")


# ==============================================================================
# 3. PÁGINA: ATENCIÓN (MEDICIÓN -> PUNTUACIÓN Y DESGLOSE -> EXPLICACIÓN -> ALERTAS E HISTORIAL)
# ==============================================================================


def page_care() -> None:
    """Flujo clínico integrado: registrar medición -> puntuación y desglose -> explicación -> alertas e historial."""
    st.title("🩺 Atención Clínica, Evaluación NEWS2 y Alertas")
    st.markdown(
        "Flujo integrado por paciente: **1. Registrar medición** → **2. Puntuación y desglose NEWS2** → "
        "**3. Explicación del resultado** → **4. Revisión de alertas e historial**."
    )

    col_f1, col_f2 = st.columns([2, 1])
    with col_f1:
        only_active = st.checkbox(
            "Mostrar únicamente pacientes en espera o en atención activa",
            value=False,
            help="Desmarque para consultar también el historial de pacientes ya atendidos o dados de alta.",
        )
    with col_f2:
        include_simulated = st.checkbox(
            "Incluir pacientes simulados",
            value=True,
            key="care_include_sim",
        )

    try:
        all_patients = patient_service.get_patient_list(include_simulated=include_simulated)
    except Exception:
        st.error("No se pudo obtener la lista de pacientes.")
        return

    if only_active:
        eligible_patients = [
            p for p in all_patients if p.administrative_status in ("en_espera", "en_atencion")
        ]
    else:
        eligible_patients = all_patients

    if not eligible_patients:
        st.info(
            "No hay pacientes disponibles con los filtros seleccionados. "
            "Diríjase a **👥 Pacientes** para registrar un nuevo ingreso."
        )
        return

    patient_choices = {
        p.id: (
            f"{p.patient_code} — {p.full_name or p.name} | "
            f"Triaje: {config.TRIAGE_LEVEL_LABELS.get(p.triage_level, 'Sin clasificar')} | "
            f"Estado: {config.ADMIN_STATUS_LABELS.get(p.administrative_status, p.administrative_status)} | "
            f"NEWS2: {p.last_evaluation_score if p.last_evaluation_score is not None else 'S/E'}"
        )
        for p in eligible_patients
    }

    default_patient_id = (
        st.session_state["selected_patient_id"]
        if st.session_state["selected_patient_id"] in patient_choices
        else list(patient_choices.keys())[0]
    )

    selected_patient_id = st.selectbox(
        "Paciente activo en contexto de atención:",
        options=list(patient_choices.keys()),
        format_func=lambda pid: patient_choices[pid],
        index=list(patient_choices.keys()).index(default_patient_id),
    )
    st.session_state["selected_patient_id"] = selected_patient_id

    try:
        history = patient_service.get_patient_history(selected_patient_id)
        patient_obj = history.get("patient")
        measurements: List[models.Measurement] = history.get("measurements", [])
        evaluations: List[models.Evaluation] = history.get("evaluations", [])
        patient_alerts: List[models.Alert] = history.get("alerts", [])
        latest_meas = measurements[-1] if measurements else None
    except Exception:
        st.error("Error al recuperar el contexto clínico del paciente.")
        return

    if patient_obj:
        dashboard.render_patient_card(patient_obj, latest_measurement=latest_meas)

    st.divider()

    # ------------------------------------------------------------------
    # PASO 1: REGISTRAR MEDICIÓN DE SIGNOS VITALES
    # ------------------------------------------------------------------
    st.subheader("1. Registrar Medición de Signos Vitales")
    form_data = dashboard.render_measurement_form()

    if form_data is not None:
        val_res = validation.validate_measurement(form_data)
        if not val_res.is_valid:
            for err in val_res.errors:
                st.error(f"Dato inválido: {err}")
        else:
            with st.spinner("Guardando medición y ejecutando evaluación NEWS2 y motor de reglas..."):
                reg_res = patient_service.register_measurement(
                    patient_id=selected_patient_id,
                    measurement_data=form_data,
                    source="manual",
                )
                if not reg_res.get("success", False):
                    for err in reg_res.get("errors", ["Error al guardar la medición."]):
                        st.error(err)
                else:
                    for warn in reg_res.get("warnings", []):
                        st.warning(warn)

                    measurement_obj = reg_res["measurement"]
                    eval_res = st.session_state.alert_engine.evaluate_new_measurement(
                        patient_id=selected_patient_id,
                        measurement=measurement_obj,
                    )
                    st.session_state["last_care_eval_result"] = {
                        "patient_id": selected_patient_id,
                        "evaluation": eval_res.get("evaluation"),
                        "clinical_alerts": eval_res.get("clinical_alerts", []),
                        "informative_notifications": eval_res.get("informative_notifications", []),
                        "changes": eval_res.get("changes", []),
                    }

                    clinical_alerts = eval_res.get("clinical_alerts", [])
                    if clinical_alerts:
                        st.warning(
                            f"⚠️ Medición registrada. Se activaron **{len(clinical_alerts)} alerta(s)** "
                            f"clínicas o de cambio fisiológico que requieren revisión."
                        )
                    else:
                        st.success(
                            "✅ Medición fisiológica registrada satisfactoriamente. "
                            "No se activaron alertas de riesgo clínico (notificación informativa de trazabilidad registrada)."
                        )

                    # Recargar historial actualizado tras la nueva medición
                    history = patient_service.get_patient_history(selected_patient_id)
                    measurements = history.get("measurements", [])
                    evaluations = history.get("evaluations", [])
                    patient_alerts = history.get("alerts", [])

    st.divider()

    # ------------------------------------------------------------------
    # PASOS 2 Y 3: MOSTRAR PUNTUACIÓN Y DESGLOSE -> EXPLICAR EL RESULTADO
    # ------------------------------------------------------------------
    st.subheader("2. Puntuación NEWS2, Desglose por Parámetro y Explicación del Resultado")

    latest_eval = evaluations[-1] if evaluations else None
    if latest_eval is not None:
        dashboard.render_evaluation_result(latest_eval)
    else:
        st.info(
            "Este paciente aún no tiene una evaluación NEWS2 registrada. "
            "Complete y guarde el formulario de signos vitales arriba para calcular su puntuación."
        )

    # Mostrar variaciones respecto a la medición previa si existen
    last_care = st.session_state.get("last_care_eval_result")
    if last_care and last_care.get("patient_id") == selected_patient_id:
        changes = last_care.get("changes", [])
        if changes:
            relevant_changes = [c for c in changes if c.get("is_clinically_relevant", True)]
            minor_changes = [c for c in changes if not c.get("is_clinically_relevant", True)]
            if relevant_changes:
                st.markdown("##### 📉 Cambios Fisiológicos Clínicamente Relevantes (vs. medición previa)")
                for chg in relevant_changes:
                    st.warning(f"• {chg.get('description', chg)}")
            if minor_changes:
                with st.expander("Ver oscilaciones menores dentro del rango normal (sin cambio de puntaje NEWS2)", expanded=False):
                    for chg in minor_changes:
                        st.caption(f"• {chg.get('description', chg)}")

    st.divider()

    # ------------------------------------------------------------------
    # PASO 4: REVISAR ALERTAS E HISTORIAL
    # ------------------------------------------------------------------
    st.subheader("3. Revisión de Alertas, Cambios Fisiológicos e Historial del Paciente")

    def acknowledge_callback(alert_id: int) -> bool:
        """Reconoce una alerta pendiente y actualiza el estado."""
        try:
            return bool(st.session_state.alert_engine.acknowledge_alert(alert_id))
        except Exception:
            return False

    tab_p_alerts, tab_p_history, tab_global_alerts = st.tabs([
        "🔔 Alertas y Notificaciones del Paciente",
        f"📈 Historial de Mediciones ({len(measurements)}) y Evaluaciones ({len(evaluations)})",
        "🌐 Consola Global de Alertas en Urgencias",
    ])

    with tab_p_alerts:
        dashboard.render_alert_panel(patient_alerts, on_acknowledge=acknowledge_callback)

    with tab_p_history:
        if measurements:
            st.markdown("##### Evolución Multivariable de Signos Vitales")
            dashboard.render_vitals_chart(measurements)
            with st.expander("Ver tabla histórica detallada de mediciones", expanded=False):
                dashboard.render_measurement_history(measurements)
        else:
            st.info("No se registran mediciones previas para este paciente.")

        if len(evaluations) > 1:
            st.markdown("##### Evolución Histórica del Puntaje NEWS2")
            dashboard.render_evaluation_history(evaluations)

    with tab_global_alerts:
        st.markdown(
            "Vista consolidada de todas las alertas clínicas y operativas pendientes en el servicio de urgencias:"
        )
        all_pending_clinical = st.session_state.alert_engine.get_pending_clinical_alerts()
        if all_pending_clinical:
            st.warning(
                f"Hay **{len(all_pending_clinical)}** alerta(s) clínica(s) u operativa(s) pendientes de reconocimiento en el servicio."
            )
            dashboard.render_alert_panel(all_pending_clinical, on_acknowledge=acknowledge_callback)
        else:
            st.success("No existen alertas clínicas ni operativas pendientes de revisión en el servicio.")


# ==============================================================================
# 4. PÁGINA: COLA DE ATENCIÓN
# ==============================================================================


def page_queue() -> None:
    """Cola de atención dinámica y priorización administrativa explicable."""
    st.title("📈 Cola Administrativa de Atención")
    st.markdown(
        "Ordenamiento administrativo explicable de pacientes en estado **En Espera**, calculado a partir "
        "del triaje registrado en admisión, el puntaje NEWS2, las alertas clínicas pendientes y el tiempo de espera "
        "(con tope máximo de 36 pts por espera para no desplazar pacientes con riesgo agudo elevado)."
    )

    st.warning(
        "⚠️ **AVISO METODOLÓGICO Y DE ALCANCE ACADÉMICO:** "
        "Esta cola es una sugerencia administrativa simulada para gestión de flujo en el prototipo. "
        "**NO constituye triaje clínico normativo** ni reemplaza el diagnóstico o la decisión médica presencial."
    )

    col_q1, col_q2 = st.columns([2.5, 1])
    with col_q1:
        include_simulated = st.checkbox(
            "Incluir pacientes simulados en la cola administrativa",
            value=True,
            help="Desmarque para visualizar únicamente pacientes registrados manualmente.",
        )
    with col_q2:
        if st.button("🔄 Recalcular Cola", type="secondary", use_container_width=True):
            st.rerun()

    try:
        queue: List[models.QueueEntry] = prioritization.build_queue(include_simulated=include_simulated)
        summary = prioritization.get_queue_summary(queue)
    except Exception:
        st.error("Error al construir la cola de atención dinámica.")
        queue = []
        summary = {}

    st.subheader("Resumen Operativo de Pacientes en Espera")
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)

    with m_col1:
        st.metric(
            "Pacientes en Cola (En Espera)",
            summary.get("total_patients", len(queue)),
        )
    with m_col2:
        st.metric(
            "Riesgo Alto (NEWS2 ≥ 7)",
            summary.get("patients_with_high_score", 0),
        )
    with m_col3:
        st.metric(
            "Alertas Clínicas Pendientes",
            summary.get("pending_alerts_count", 0),
            help=f"Pacientes con alertas activas en cola: {summary.get('patients_with_alerts', 0)}",
        )
    with m_col4:
        avg_wait = summary.get("avg_wait_time", 0.0)
        st.metric(
            "Espera Promedio en Sala",
            dashboard.format_wait_time(avg_wait),
        )

    st.divider()

    if not queue:
        st.info(
            "No hay pacientes en estado 'En Espera' con los criterios seleccionados. "
            "(Los pacientes con estado 'En Atención', 'Atendido' o 'Alta' no forman parte de la cola de espera)."
        )
        return

    col_view1, col_view2 = st.columns([3.1, 1.9])
    with col_view1:
        st.subheader("Orden de Prioridad Actual")
        dashboard.render_queue_table(queue)

    with col_view2:
        st.subheader("Comparativa de Puntajes")
        dashboard.render_queue_chart(queue)

    st.divider()
    st.subheader("Explicabilidad de la Posición en Cola")
    st.markdown(
        "Seleccione un paciente en espera para revisar el resumen de los factores que determinaron su posición:"
    )

    entry_options = {}
    for entry in queue:
        pid = entry.patient_id if entry.patient_id is not None else (entry.patient.id if entry.patient else id(entry))
        pcode = entry.patient_code or (entry.patient.patient_code if entry.patient else "N/D")
        pname = entry.patient_name or ((entry.patient.full_name or entry.patient.name) if entry.patient else "")
        label = f"Posición #{entry.position} — {pcode}"
        if pname:
            label += f" ({pname})"
        label += f" | Prioridad: {entry.priority_score:.1f} pts"
        entry_options[pid] = label

    selected_queue_id = st.selectbox(
        "Paciente en cola:",
        options=list(entry_options.keys()),
        format_func=lambda pid: entry_options.get(pid, str(pid)),
    )

    selected_entry = next(
        (
            e for e in queue
            if (e.patient_id == selected_queue_id)
            or (e.patient and e.patient.id == selected_queue_id)
            or id(e) == selected_queue_id
        ),
        None,
    )
    if selected_entry:
        p_obj = selected_entry.patient
        p_name = (p_obj.full_name or p_obj.name) if p_obj else "N/D"
        p_code = p_obj.patient_code if p_obj else "N/D"

        st.markdown(
            f"""
            <div class="glass-card" style="padding:18px 22px; margin-top:8px;">
                <div style="font-size:1.05rem; font-weight:700; color:#f8fafc; margin-bottom:10px;">
                    📌 Posición #{selected_entry.position}: {p_name} (<code>{p_code}</code>) — 
                    <span style="color:#38bdf8;">{selected_entry.priority_score:.1f} puntos administrativos</span>
                </div>
                <div style="font-size:0.9rem; color:#cbd5e1; margin-bottom:6px; font-weight:600;">
                    Desglose de factores aplicados:
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        for reason_item in selected_entry.reasons:
            st.markdown(f"- {reason_item}")

        with st.expander("🔍 Ver explicación textual íntegra y nota metodológica", expanded=False):
            st.info(prioritization.explain_position(selected_entry))


# ==============================================================================
# 5. PÁGINA: SIMULACIÓN
# ==============================================================================


def page_simulation() -> None:
    """Motor de simulación académica de escenarios sintéticos."""
    st.title("🔬 Simulación Académica de Escenarios")
    st.markdown(
        "Genere escenarios sintéticos reproducibles con perfiles fisiológicos contrastados para evaluar "
        "el cálculo NEWS2, la activación de alertas y la evolución de la cola administrativa."
    )

    st.info(
        "ℹ️ **Aislamiento y Trazabilidad de Datos Simulados:** Todos los pacientes creados en este módulo se "
        "identifican como **🔬 Simulado**. Puede filtrarlos o excluirlos en las vistas de **👥 Pacientes** y "
        "**📈 Cola de Atención**, o eliminarlos completamente con el botón **🗑 Limpiar Datos de Simulación**."
    )

    config_data = dashboard.render_simulation_config()

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        run_clicked = st.button("▶ Ejecutar Escenario de Simulación", type="primary", use_container_width=True)
    with col_btn2:
        clear_clicked = st.button(
            "🗑 Limpiar Datos de Simulación",
            type="secondary",
            use_container_width=True,
            help="Elimina únicamente los pacientes, mediciones, evaluaciones y alertas generados por simulación.",
        )

    if clear_clicked:
        with st.spinner("Eliminando registros sintéticos de simulación..."):
            clear_res = simulation.clear_simulation_data()
            if clear_res.get("success", False):
                st.session_state["simulation_results"] = None
                deleted_n = clear_res.get("deleted_count", 0)
                st.success(f"Se eliminaron correctamente {deleted_n} paciente(s) simulado(s) y sus eventos asociados.")
                st.rerun()
            else:
                for err in clear_res.get("errors", ["Error al limpiar datos simulados."]):
                    st.error(err)

    if run_clicked:
        sim_config = create_simulation_config_instance(config_data)
        val_res = validation.validate_simulation_config(
            num_patients=int(sim_config.num_patients),
            duration_hours=int(sim_config.duration_hours),
            measurement_interval=int(sim_config.measurement_interval_minutes),
            seed=int(sim_config.random_seed),
        )

        if not val_res.is_valid:
            for err in val_res.errors:
                st.error(f"Configuración inválida: {err}")
            return

        with st.spinner("Ejecutando simulación temporal reproducible..."):
            results = simulation.run_simulation(sim_config)
            st.session_state["simulation_results"] = results

    results = st.session_state.get("simulation_results")
    if results:
        st.divider()
        dashboard.render_simulation_results(results)


# ==============================================================================
# 6. PÁGINA: METODOLOGÍA Y CONFIGURACIÓN
# ==============================================================================


def page_config_and_methodology() -> None:
    """Documentación metodológica, especificación NEWS2 y configuración de reglas del motor de alertas."""
    st.title("📚 Metodología, Especificación NEWS2 y Reglas de Alerta")
    st.markdown(
        "Consulte la especificación clínica NEWS2 (Royal College of Physicians, 2017), "
        "los factores de ponderación de la cola administrativa, los límites del prototipo "
        "y gestione la activación de reglas del motor de alertas."
    )

    tab_methodology, tab_news2, tab_rules = st.tabs([
        "🏛️ Metodología y Límites del Prototipo",
        "📖 Especificación Oficial NEWS2",
        "⚙️ Configuración de Reglas de Alerta",
    ])

    with tab_methodology:
        dashboard.render_methodology_page()

    with tab_news2:
        dashboard.render_news2_explanation()

    with tab_rules:
        st.subheader("Estado y Configuración de Reglas del Motor de Alertas")
        st.markdown(
            "Active o desactive las reglas evaluadas por `AlertEngine`. "
            "Los cambios aplicados aquí afectan inmediatamente a las evaluaciones de nuevas mediciones registradas en la sesión."
        )

        try:
            rules_status: List[Dict[str, Any]] = st.session_state.alert_engine.get_rules_status()
        except Exception:
            st.error("Error al consultar el estado de las reglas de alerta.")
            rules_status = []

        if not rules_status:
            st.info("No hay reglas de alerta registradas en el motor.")
        else:
            category_labels = {
                "riesgo_clinico": "🚨 Alerta de Riesgo Clínico (Requiere revisión)",
                "cambio_fisiologico": "📉 Alerta de Cambio Fisiológico (Requiere revisión)",
                "operativa": "⏱️ Alerta Operativa / Administrativa (Requiere revisión)",
                "informativa": "ℹ️ Notificación Informativa de Trazabilidad (No suma prioridad)",
            }

            for rule_info in rules_status:
                r_name = rule_info.get("name", "")
                r_label = rule_info.get("label", r_name)
                r_desc = rule_info.get("description", "")
                r_cat = rule_info.get("category", "riesgo_clinico" if rule_info.get("requires_review") else "informativa")
                is_enabled = bool(rule_info.get("enabled", True))
                cat_badge = category_labels.get(r_cat, r_cat)

                with st.container():
                    col_r1, col_r2 = st.columns([3.5, 1])
                    with col_r1:
                        st.markdown(f"**{r_label}** (`{r_name}`)")
                        st.caption(f"{cat_badge} — {r_desc}")
                    with col_r2:
                        toggled = st.toggle(
                            "Regla activa" if is_enabled else "Regla inactiva",
                            value=is_enabled,
                            key=f"rule_toggle_{r_name}",
                        )
                        if toggled != is_enabled:
                            if toggled:
                                st.session_state.alert_engine.enable_rule(r_name)
                                st.toast(f"Regla '{r_label}' activada.", icon="✅")
                            else:
                                st.session_state.alert_engine.disable_rule(r_name)
                                st.toast(f"Regla '{r_label}' desactivada.", icon="⏸️")
                            st.rerun()
                    st.markdown("---")


# ==============================================================================
# ENRUTAMIENTO PRINCIPAL
# ==============================================================================


def main() -> None:
    """Función principal de ejecución y enrutamiento de la aplicación."""
    st.set_page_config(
        page_title="IA Médica Asistencial | Triaje y Priorización",
        page_icon="🏥",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(dashboard.get_glassmorphism_css(), unsafe_allow_html=True)

    init_app_state()

    # Conteo real de alertas clínicas/operativas pendientes (excluyendo notificaciones informativas)
    try:
        pending_clinical_alerts = st.session_state.alert_engine.get_pending_clinical_alerts()
        pending_alerts_count = len(pending_clinical_alerts)
    except Exception:
        pending_alerts_count = 0

    dashboard.render_top_header(pending_alerts_count=pending_alerts_count)

    # Barra lateral de navegación estilizada
    st.sidebar.markdown(
        f"""
        <div style="padding: 10px 0 6px 0;">
            <div style="font-size: 1.25rem; font-weight: 800; color: #f8fafc; display: flex; align-items: center; gap: 8px;">
                <span>🏥</span> {config.APP_NAME}
            </div>
            <div style="font-size: 0.8rem; color: #38bdf8; font-weight: 600; margin-top: 2px;">
                v{config.APP_VERSION} &bull; Prototipo Académico
            </div>
            <div style="font-size: 0.78rem; color: #94a3b8; margin-top: 2px;">
                Desarrollado por: <strong style="color: #f1f5f9;">{config.TEAM_NAME}</strong>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.sidebar.markdown("---")

    current_page = st.session_state.get("current_page", MENU_OPTIONS[0])
    if current_page in LEGACY_PAGE_REDIRECTS:
        current_page = LEGACY_PAGE_REDIRECTS[current_page]
    if current_page not in MENU_OPTIONS:
        current_page = MENU_OPTIONS[0]

    selected_nav = st.sidebar.radio(
        "Flujo de Trabajo:",
        options=MENU_OPTIONS,
        index=MENU_OPTIONS.index(current_page),
    )
    if selected_nav != st.session_state.get("current_page"):
        st.session_state["current_page"] = selected_nav
        st.rerun()

    # Tarjeta destacada de alertas clínicas pendientes en la barra lateral
    if pending_alerts_count > 0:
        st.sidebar.markdown(
            f"""
            <div class="sidebar-alert-card">
                <div class="sidebar-alert-title">
                    <span>⚠️</span> {pending_alerts_count} alerta(s) clínica(s) pendiente(s)
                </div>
                <div class="sidebar-alert-sub">Requieren revisión asistencial u operativa en sala.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.sidebar.button("Revisar en Atención", key="btn_sidebar_view_alerts", use_container_width=True):
            st.session_state["current_page"] = "🩺 Atención"
            st.rerun()
    else:
        st.sidebar.markdown(
            """
            <div class="sidebar-alert-card" style="border-color: rgba(16, 185, 129, 0.4); background: linear-gradient(135deg, rgba(16, 185, 129, 0.14) 0%, rgba(5, 150, 105, 0.08) 100%);">
                <div class="sidebar-alert-title" style="color: #34d399;">
                    <span>✅</span> Sin alertas de riesgo activas
                </div>
                <div class="sidebar-alert-sub" style="color: #a7f3d0;">No hay alertas clínicas pendientes de reconocimiento.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        """
        <div style="font-size: 0.78rem; color: #94a3b8; line-height: 1.45; padding: 4px;">
            <strong>Uso Académico Exclusivo.</strong><br>
            No utilizar para decisiones clínicas reales ni triaje normativo.
        </div>
        """,
        unsafe_allow_html=True,
    )

    page_router = {
        "🏠 Inicio": page_home,
        "👥 Pacientes": page_patients,
        "🩺 Atención": page_care,
        "📈 Cola de Atención": page_queue,
        "🔬 Simulación": page_simulation,
        "📚 Metodología y Configuración": page_config_and_methodology,
    }

    render_func = page_router.get(selected_nav, page_home)
    render_func()


if __name__ == "__main__":
    main()
