"""Componentes Visuales y Vistas Reutilizables de Streamlit.

Proyecto: IA Médica Asistencial (Prototipo Académico por TechMinds).
Este módulo provee la interfaz gráfica desacoplada de la lógica de persistencia.
Todas las etiquetas, descripciones y mensajes están en idioma español.
"""

from datetime import datetime
import json
from typing import Any, Callable, Dict, List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from config import (
    ADMIN_STATUS_LABELS,
    ALERT_STATUS_PENDING,
    ALERT_TYPES,
    APP_NAME,
    APP_VERSION,
    CONSCIOUSNESS_LABELS,
    CONSCIOUSNESS_LEVELS,
    DISCLAIMER_TEXT,
    MEASUREMENT_UNITS,
    METHODOLOGY_TEXT,
    NEWS2_RISK_LEVELS,
    PRIORITY_RULES,
    SIM_DEFAULT_DURATION_HOURS,
    SIM_DEFAULT_MEASUREMENT_INTERVAL_MINUTES,
    SIM_DEFAULT_PATIENTS,
    SIM_RANDOM_SEED,
    TEAM_NAME,
    TRIAGE_LEVELS,
    TRIAGE_LEVEL_LABELS,
)
from models import (
    Alert,
    Evaluation,
    Measurement,
    Patient,
    QueueEntry,
    SimulationEvent,
)


def format_wait_time(minutes: Optional[float]) -> str:
    """Formatea los minutos de espera a un formato legible 'Xh Ym'.

    Args:
        minutes: Minutos de espera transcurridos o None.

    Returns:
        Cadena con el formato 'Xh Ym', 'Ym' o 'N/D'.
    """
    if minutes is None:
        return 'N/D'
    try:
        total_mins = max(0, float(minutes))
        hours = int(total_mins // 60)
        mins = int(total_mins % 60)
        if hours > 0:
            return f'{hours}h {mins}m'
        return f'{mins}m'
    except (ValueError, TypeError):
        return 'N/D'


def format_datetime(dt_str: Optional[str]) -> str:
    """Formatea una cadena de fecha ISO 8601 a un formato legible en español.

    Args:
        dt_str: Cadena ISO 8601 o None.

    Returns:
        Cadena en formato 'DD/MM/AAAA HH:MM' o 'N/D'.
    """
    if not dt_str:
        return 'N/D'
    try:
        clean_str = dt_str.replace('Z', '+00:00')
        dt = datetime.fromisoformat(clean_str)
        return dt.strftime('%d/%m/%Y %H:%M')
    except (ValueError, TypeError):
        return str(dt_str)


def get_risk_color(risk_level: Optional[str]) -> str:
    """Retorna el color asignado a cada nivel de riesgo de NEWS2.

    Args:
        risk_level: Clave de nivel de riesgo ('low', 'low_medium', 'medium', 'high').

    Returns:
        Nombre de color o código hexadecimal.
    """
    colors = {
        'low': 'green',
        'low_medium': 'orange',
        'medium': 'darkorange',
        'high': 'red',
    }
    return colors.get(risk_level or '', 'gray')


def get_status_emoji(status: str) -> str:
    """Retorna un emoji representativo del estado administrativo del paciente.

    Args:
        status: Clave de estado administrativo.

    Returns:
        Emoji representativo.
    """
    emojis = {
        'en_espera': '⏳',
        'en_atencion': '🔵',
        'atendido': '✅',
        'alta': '🏠',
    }
    return emojis.get(status, '❓')


def render_disclaimer() -> None:
    """Muestra el descargo de responsabilidad académica en un cuadro de advertencia visible."""
    st.warning(DISCLAIMER_TEXT, icon='⚠️')


def render_home_page() -> None:
    """Renderiza la página principal con información institucional, alcance y advertencias."""
    st.title(f'🏥 {APP_NAME}')
    st.subheader(f'Equipo de Desarrollo: {TEAM_NAME}')
    st.markdown('---')

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("""
        ### Prototipo Académico de Priorización Dinámica en Urgencias
        
        Este sistema es un **prototipo de investigación y desarrollo académico** que demuestra cómo 
        una aplicación analítica puede apoyar la gestión administrativa y la priorización transparente de pacientes 
        en la cola de espera de un servicio de urgencias simulado.
        
        **Funcionalidades Principales:**
        - 📋 **Registro de Pacientes Ficticios:** Ingreso ágil y trazabilidad con códigos únicos.
        - 📊 **Monitoreo de Signos Vitales:** Captura periódica de parámetros fisiológicos.
        - ⚡ **Evaluación Estandarizada NEWS2:** Cálculo riguroso según la especificación del Royal College of Physicians (2017).
        - 🔔 **Motor de Alertas Configurable:** Detección de deterioro fisiológico, datos incompletos y tiempos de espera prolongados.
        - 📈 **Cola Administrativa Dinámica:** Ordenamiento explicable con desglose de factores de prioridad.
        - 🔬 **Simulación de Escenarios:** Generación de pacientes sintéticos con perfiles clínicos y evolución temporal.
        """)
    with col2:
        st.info(
            f"""
        **Ficha Técnica del Prototipo**
        - **Versión:** `{APP_VERSION}`
        - **Entorno:** Simulación Controlada
        - **Escala de Deterioro:** NEWS2 (2017)
        - **Triage Oficial (I-V):** Humano / No automatizado
        - **Persistencia:** SQLite Transaccional
        """,
            icon='ℹ️',
        )

    render_disclaimer()

    st.markdown('---')
    st.markdown("""
    > **Aviso Ético y Regulatorio:** El presente software **no** realiza diagnósticos médicos, **no** prescribe 
    > tratamientos ni sustituye la valoración clínica presencial. La categorización de triage oficial en Colombia 
    > (Niveles I a V, Resolución 5596 de 2015) es potestad exclusiva del profesional de salud y **no** es asignada 
    > automáticamente por este sistema.
    """)


def render_patient_table(patients: List[Patient]) -> None:
    """Renderiza la tabla de pacientes con estado, tiempo de espera, alertas y último NEWS2.

    Args:
        patients: Lista de objetos Patient a mostrar.
    """
    if not patients:
        st.info('No hay pacientes registrados en este momento.')
        return

    total_patients = len(patients)
    en_espera = sum(1 for p in patients if p.administrative_status == 'en_espera')
    con_alertas = sum(1 for p in patients if (p.pending_alerts_count or 0) > 0)

    m1, m2, m3 = st.columns(3)
    m1.metric('Total Pacientes', total_patients)
    m2.metric('En Espera', en_espera)
    m3.metric('Con Alertas Activas', con_alertas)

    table_data = []
    for p in patients:
        status_label = ADMIN_STATUS_LABELS.get(
            p.administrative_status, p.administrative_status
        )
        status_display = f'{get_status_emoji(p.administrative_status)} {status_label}'
        alerts_display = (
            f'🚨 {p.pending_alerts_count}'
            if (p.pending_alerts_count or 0) > 0
            else '0'
        )
        score_display = (
            str(p.last_evaluation_score)
            if p.last_evaluation_score is not None
            else 'Sin evaluar'
        )
        triage_display = (
            TRIAGE_LEVELS.get(p.triage_level, {}).get('short_label', f'Nivel {p.triage_level}')
            if p.triage_level
            else 'Sin clasificar'
        )
        patient_name = p.full_name or p.name or 'N/D'

        table_data.append({
            'Código': p.patient_code,
            'Nombre': patient_name,
            'Triaje Clínico': triage_display,
            'Estado': status_display,
            'Hora Llegada': format_datetime(p.arrival_at),
            'Tiempo Espera': format_wait_time(p.wait_time_minutes),
            'Alertas': alerts_display,
            'Último NEWS2': score_display,
            'Síntomas': p.symptoms or 'No descritos',
            'Diagnóstico Inicial': p.initial_diagnosis or 'Pendiente',
            'Tipo': 'Simulado' if p.is_simulated else 'Manual',
        })

    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_patient_card(patient: Patient) -> None:
    """Muestra una tarjeta detallada con el resumen clínico y administrativo de un paciente.

    Args:
        patient: Objeto Patient a detallar.
    """
    status_label = ADMIN_STATUS_LABELS.get(
        patient.administrative_status, patient.administrative_status
    )
    emoji = get_status_emoji(patient.administrative_status)
    sim_tag = ' *(Simulado)*' if patient.is_simulated else ' *(Manual)*'
    patient_name = patient.full_name or patient.name or 'Paciente Ficticio'

    triage_info = TRIAGE_LEVELS.get(patient.triage_level or 0, {})
    triage_short = triage_info.get('short_label', f'Nivel {patient.triage_level}' if patient.triage_level else 'Sin Triaje')
    triage_color = triage_info.get('color', '#6c757d')

    st.markdown(
        f"### {emoji} **{patient_name}** (`{patient.patient_code}`){sim_tag} "
        f"<span style='background-color:{triage_color}; color:white; padding:3px 10px; border-radius:12px; font-size:0.85em; margin-left:10px;'>{triage_short}</span>",
        unsafe_allow_html=True,
    )

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric('Estado Administrativo', status_label)
    with col2:
        st.metric('Triaje Clínico', triage_short)
    with col3:
        st.metric('Tiempo de Espera', format_wait_time(patient.wait_time_minutes))
    with col4:
        alerts_val = patient.pending_alerts_count or 0
        st.metric(
            'Alertas Activas',
            f'🚨 {alerts_val}' if alerts_val > 0 else '✅ 0',
        )
    with col5:
        score_val = (
            str(patient.last_evaluation_score)
            if patient.last_evaluation_score is not None
            else 'N/D'
        )
        st.metric('Puntaje NEWS2', score_val)

    # Bloque de información clínica descriptiva
    with st.container():
        st.markdown(
            f"""
            <div style="background-color:rgba(28, 131, 225, 0.08); border-left: 4px solid #1c83e1; padding: 10px 14px; border-radius: 4px; margin: 8px 0;">
                <p style="margin:0 0 6px 0;"><strong>🩺 Síntomas Reportados:</strong> {patient.symptoms or '<em>Sin síntomas descritos al ingreso</em>'}</p>
                <p style="margin:0;"><strong>📋 Diagnóstico Inicial / Sospecha:</strong> {patient.initial_diagnosis or '<em>Pendiente de valoración clínica</em>'}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.caption(
        f'Hora de Ingreso: {format_datetime(patient.arrival_at)} | '
        f'Última Evaluación: {format_datetime(patient.last_evaluation_at)}'
    )


def render_measurement_form() -> Optional[Dict[str, Any]]:
    """Renderiza el formulario de ingreso de signos vitales con validaciones y unidades.

    Returns:
        Diccionario con los datos del formulario si fue enviado, o None.
    """
    with st.form('measurement_input_form', clear_on_submit=False):
        st.subheader('📝 Registro de Signos Vitales')
        st.markdown(
            'Ingrese los valores fisiológicos observados. Cada parámetro incluye su unidad médica estándar.'
        )

        col1, col2 = st.columns(2)
        with col1:
            rr_unit = MEASUREMENT_UNITS.get('respiratory_rate', 'rpm')
            respiratory_rate = st.number_input(
                f'Frecuencia Respiratoria ({rr_unit})',
                min_value=0,
                max_value=60,
                value=16,
                step=1,
                help='Frecuencia de respiraciones por minuto. Normal: 12-20 rpm.',
            )

            spo2_unit = MEASUREMENT_UNITS.get('oxygen_saturation', '%')
            oxygen_saturation = st.number_input(
                f'Saturación de Oxígeno ({spo2_unit})',
                min_value=50,
                max_value=100,
                value=97,
                step=1,
                help='Porcentaje de saturación de oxígeno por oximetría. Normal: >= 96%.',
            )

            supplemental_oxygen = st.checkbox(
                '¿Recibe Oxígeno Suplementario?',
                value=False,
                help='Marque si el paciente se encuentra con soporte de oxígeno (cánula, máscara, venturi).',
            )

            use_spo2_scale_2 = st.checkbox(
                'Usar Escala 2 de SpO2 (indicada por clínico)',
                value=False,
                help=(
                    'NEWS2 usa la Escala 1 por defecto, incluso con oxígeno. La Escala 2 solo debe '
                    'marcarse si un clínico la indicó (insuficiencia respiratoria hipercápnica confirmada).'
                ),
            )

            consciousness_status = st.selectbox(
                'Nivel de Conciencia (Escala AVPU)',
                options=CONSCIOUSNESS_LEVELS,
                format_func=lambda x: f'{x} - {CONSCIOUSNESS_LABELS.get(x, x)}',
                index=0,
                help='A=Alerta, V=Respuesta a la voz, P=Respuesta al dolor, U=Inconsciente.',
            )

        with col2:
            sbp_unit = MEASUREMENT_UNITS.get(
                'systolic_blood_pressure', 'mmHg'
            )
            systolic_bp = st.number_input(
                f'Presión Arterial Sistólica ({sbp_unit})',
                min_value=40,
                max_value=260,
                value=120,
                step=1,
                help='Presión sistólica en milímetros de mercurio. Normal: 111-219 mmHg.',
            )

            hr_unit = MEASUREMENT_UNITS.get('heart_rate', 'lpm')
            heart_rate = st.number_input(
                f'Frecuencia Cardíaca ({hr_unit})',
                min_value=30,
                max_value=240,
                value=75,
                step=1,
                help='Latidos cardíacos por minuto. Normal: 51-90 lpm.',
            )

            temp_unit = MEASUREMENT_UNITS.get('temperature', '°C')
            temperature = st.number_input(
                f'Temperatura Corporal ({temp_unit})',
                min_value=28.0,
                max_value=44.0,
                value=36.8,
                step=0.1,
                format='%.1f',
                help='Temperatura axilar o timpánica. Normal: 36.1 - 38.0 °C.',
            )

            use_current_time = st.checkbox('Registrar con hora actual', value=True)
            custom_dt_str = None
            if not use_current_time:
                custom_dt_str = st.text_input(
                    'Hora personalizada (ISO 8601)',
                    value=datetime.now().isoformat()[:19],
                    help='Formato YYYY-MM-DDTHH:MM:SS',
                )

        submitted = st.form_submit_button(
            '💾 Guardar Medición', use_container_width=True
        )

        if submitted:
            result_data: Dict[str, Any] = {
                'respiratory_rate': int(respiratory_rate),
                'oxygen_saturation': int(oxygen_saturation),
                'supplemental_oxygen': bool(supplemental_oxygen),
                'systolic_blood_pressure': int(systolic_bp),
                'heart_rate': int(heart_rate),
                'temperature': round(float(temperature), 1),
                'consciousness_status': str(consciousness_status),
                'spo2_scale': 2 if use_spo2_scale_2 else 1,
            }
            if custom_dt_str:
                result_data['recorded_at'] = custom_dt_str
            return result_data

    return None


def render_measurement_history(measurements: List[Measurement]) -> None:
    """Muestra el historial de mediciones de un paciente en formato tabular con unidades.

    Args:
        measurements: Lista de objetos Measurement.
    """
    if not measurements:
        st.info('No se han registrado mediciones previas para este paciente.')
        return

    table_data = []
    for m in measurements:
        supp_text = (
            'Sí'
            if m.supplemental_oxygen is True
            else ('No' if m.supplemental_oxygen is False else 'N/D')
        )
        temp_text = (
            f'{m.temperature:.1f} °C' if m.temperature is not None else 'N/D'
        )
        avpu_label = CONSCIOUSNESS_LABELS.get(
            m.consciousness_status, m.consciousness_status or 'N/D'
        )

        table_data.append({
            'Fecha / Hora': format_datetime(m.recorded_at),
            'Frec. Resp. (rpm)': (
                m.respiratory_rate if m.respiratory_rate is not None else 'N/D'
            ),
            'SpO2 (%)': (
                m.oxygen_saturation
                if m.oxygen_saturation is not None
                else 'N/D'
            ),
            'O2 Supl.': supp_text,
            'P. Sistólica (mmHg)': (
                m.systolic_blood_pressure
                if m.systolic_blood_pressure is not None
                else 'N/D'
            ),
            'Frec. Cardíaca (lpm)': (
                m.heart_rate if m.heart_rate is not None else 'N/D'
            ),
            'Temperatura': temp_text,
            'Conciencia': f'{m.consciousness_status or "-"} ({avpu_label})',
            'Origen': m.measurement_source,
        })

    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_vitals_chart(measurements: List[Measurement]) -> None:
    """Renderiza gráficos de líneas con Plotly mostrando la evolución temporal de los signos vitales.

    Args:
        measurements: Lista de objetos Measurement.
    """
    if not measurements:
        st.info(
            'No hay mediciones registradas para graficar tendencias fisiológicas.'
        )
        return

    # Ordenar cronológicamente
    sorted_m = sorted(measurements, key=lambda x: x.recorded_at or '')
    timestamps = [format_datetime(m.recorded_at) for m in sorted_m]

    fig = make_subplots(
        rows=3,
        cols=2,
        subplot_titles=(
            'Frecuencia Respiratoria (rpm)',
            'Saturación de Oxígeno - SpO2 (%)',
            'Presión Arterial Sistólica (mmHg)',
            'Frecuencia Cardíaca (lpm)',
            'Temperatura Corporal (°C)',
            'Nivel de Conciencia (AVPU)',
        ),
        vertical_spacing=0.12,
        horizontal_spacing=0.10,
    )

    # 1. Frecuencia respiratoria
    rr_vals = [m.respiratory_rate for m in sorted_m]
    fig.add_trace(
        go.Scatter(
            x=timestamps,
            y=rr_vals,
            mode='lines+markers',
            name='Frec. Resp.',
            line=dict(color='#2b5c8f'),
        ),
        row=1,
        col=1,
    )

    # 2. SpO2
    spo2_vals = [m.oxygen_saturation for m in sorted_m]
    fig.add_trace(
        go.Scatter(
            x=timestamps,
            y=spo2_vals,
            mode='lines+markers',
            name='SpO2',
            line=dict(color='#1b9e77'),
        ),
        row=1,
        col=2,
    )

    # 3. Presión sistólica
    bp_vals = [m.systolic_blood_pressure for m in sorted_m]
    fig.add_trace(
        go.Scatter(
            x=timestamps,
            y=bp_vals,
            mode='lines+markers',
            name='Presión Sist.',
            line=dict(color='#d95f02'),
        ),
        row=2,
        col=1,
    )

    # 4. Frecuencia cardíaca
    hr_vals = [m.heart_rate for m in sorted_m]
    fig.add_trace(
        go.Scatter(
            x=timestamps,
            y=hr_vals,
            mode='lines+markers',
            name='Frec. Cardíaca',
            line=dict(color='#e7298a'),
        ),
        row=2,
        col=2,
    )

    # 5. Temperatura
    temp_vals = [m.temperature for m in sorted_m]
    fig.add_trace(
        go.Scatter(
            x=timestamps,
            y=temp_vals,
            mode='lines+markers',
            name='Temperatura',
            line=dict(color='#7570b3'),
        ),
        row=3,
        col=1,
    )

    # 6. Conciencia (AVPU codificado a valores numéricos para visualización)
    avpu_numeric = {'A': 0, 'V': 1, 'P': 2, 'U': 3}
    avpu_vals = [avpu_numeric.get(m.consciousness_status or '', None) for m in sorted_m]
    fig.add_trace(
        go.Scatter(
            x=timestamps,
            y=avpu_vals,
            mode='lines+markers',
            name='AVPU',
            line=dict(color='#66a61e'),
        ),
        row=3,
        col=2,
    )

    fig.update_layout(
        title_text='Tendencia Temporal de Parámetros Fisiológicos',
        height=720,
        showlegend=False,
        margin=dict(l=40, r=40, t=60, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_evaluation_result(evaluation: Evaluation) -> None:
    """Muestra el resultado detallado de una evaluación NEWS2, con desglose de parámetros y nivel de riesgo.

    Args:
        evaluation: Objeto Evaluation a presentar.
    """
    risk_info = NEWS2_RISK_LEVELS.get(evaluation.risk_level or '', {})
    risk_label = risk_info.get(
        'label', evaluation.risk_level or 'No determinado'
    )
    clinical_rec = risk_info.get('description', '')

    c1, c2, c3 = st.columns(3)
    c1.metric('Puntaje Total NEWS2', evaluation.score)
    c2.metric('Nivel de Riesgo Clínico', risk_label)
    comp_label = (
        'Completo'
        if evaluation.completeness_status == 'completo'
        else 'Datos Parciales'
    )
    c3.metric('Estado de Medición', comp_label)

    st.markdown(f'**Explicación Clínica:** {evaluation.explanation}')
    if clinical_rec:
        st.info(f'**Respuesta Clínica Estándar:** {clinical_rec}', icon='ℹ️')

    # Desglose de puntajes por parámetro si están disponibles
    param_scores = evaluation.parameter_scores
    if param_scores:
        if isinstance(param_scores, str):
            try:
                param_scores = json.loads(param_scores)
            except Exception:
                param_scores = {}

        if isinstance(param_scores, dict) and param_scores:
            st.markdown('##### Desglose de Parámetros NEWS2')
            labels_map = {
                'respiratory_rate': 'Frecuencia Respiratoria',
                'oxygen_saturation': 'Saturación SpO2',
                'supplemental_oxygen': 'Oxígeno Suplementario',
                'systolic_blood_pressure': 'Presión Sistólica',
                'heart_rate': 'Frecuencia Cardíaca',
                'temperature': 'Temperatura Corporal',
                'consciousness_status': 'Nivel de Conciencia (AVPU)',
            }
            breakdown_list = []
            for k, pts in param_scores.items():
                breakdown_list.append({
                    'Parámetro Fisiológico': labels_map.get(k, k),
                    'Puntos NEWS2': pts,
                })
            df_breakdown = pd.DataFrame(breakdown_list)
            st.dataframe(df_breakdown, use_container_width=True, hide_index=True)


def render_evaluation_history(evaluations: List[Evaluation]) -> None:
    """Renderiza el historial de evaluaciones NEWS2 en tabla y gráfico evolutivo.

    Args:
        evaluations: Lista de objetos Evaluation.
    """
    if not evaluations:
        st.info('No hay evaluaciones clínicas registradas para este paciente.')
        return

    sorted_evals = sorted(evaluations, key=lambda x: x.evaluated_at or '')

    # Gráfico evolutivo del score
    chart_df = pd.DataFrame([
        {
            'Fecha / Hora': format_datetime(e.evaluated_at),
            'Puntaje NEWS2': e.score,
            'Riesgo': NEWS2_RISK_LEVELS.get(e.risk_level or '', {}).get(
                'label', e.risk_level or 'N/D'
            ),
        }
        for e in sorted_evals
    ])

    fig = px.line(
        chart_df,
        x='Fecha / Hora',
        y='Puntaje NEWS2',
        markers=True,
        title='Evolución Temporal de la Puntuación NEWS2',
        color_discrete_sequence=['#d95f02'],
    )
    fig.update_layout(height=320, margin=dict(l=30, r=30, t=50, b=30))
    st.plotly_chart(fig, use_container_width=True)

    # Tabla histórica
    table_rows = []
    for e in reversed(sorted_evals):
        risk_name = NEWS2_RISK_LEVELS.get(e.risk_level or '', {}).get(
            'label', e.risk_level or 'N/D'
        )
        table_rows.append({
            'Fecha / Hora': format_datetime(e.evaluated_at),
            'Puntaje': e.score,
            'Nivel de Riesgo': risk_name,
            'Completitud': e.completeness_status,
            'Detalle': e.explanation,
        })
    df_table = pd.DataFrame(table_rows)
    st.dataframe(df_table, use_container_width=True, hide_index=True)


def render_alert_panel(
    alerts: List[Alert], on_acknowledge: Optional[Callable[[int], bool]] = None
) -> None:
    """Muestra el panel de alertas operativas con secciones pendientes y reconocidas.

    Args:
        alerts: Lista de objetos Alert.
        on_acknowledge: Función de retrollamada para reconocer alertas (recibe alert_id).
    """
    if not alerts:
        st.success('No existen alertas generadas en el sistema.')
        return

    pending = [a for a in alerts if a.status == ALERT_STATUS_PENDING]
    acknowledged = [a for a in alerts if a.status != ALERT_STATUS_PENDING]

    tab_pending, tab_ack = st.tabs([
        f'🚨 Pendientes ({len(pending)})',
        f'✅ Reconocidas ({len(acknowledged)})',
    ])

    with tab_pending:
        if not pending:
            st.success('No hay alertas pendientes de revisión.')
        else:
            for alert in pending:
                type_info = ALERT_TYPES.get(alert.alert_type, {})
                type_name = type_info.get('label', alert.alert_type)
                with st.expander(
                    f'⚠️ [{type_name}] Paciente #{alert.patient_id} - '
                    f'{format_datetime(alert.created_at)}',
                    expanded=True,
                ):
                    st.markdown(f'**Motivo de Alerta:** {alert.reason}')
                    st.caption(
                        f'Regla: `{alert.rule_name}` | Generada: {format_datetime(alert.created_at)}'
                    )

                    if alert.trigger_data:
                        trig = alert.trigger_data
                        if isinstance(trig, str):
                            try:
                                trig = json.loads(trig)
                            except Exception:
                                pass
                        st.json(trig)

                    if on_acknowledge is not None:
                        btn_key = f'ack_alert_btn_{alert.id}'
                        if st.button(
                            f'Marcar como Reconocida (ID {alert.id})',
                            key=btn_key,
                        ):
                            success = on_acknowledge(alert.id)
                            if success:
                                st.success('Alerta reconocida exitosamente.')
                                st.rerun()
                            else:
                                st.error('No fue posible actualizar la alerta.')

    with tab_ack:
        if not acknowledged:
            st.info('No hay alertas en el histórico de reconocidas.')
        else:
            for alert in acknowledged:
                type_info = ALERT_TYPES.get(alert.alert_type, {})
                type_name = type_info.get('label', alert.alert_type)
                with st.expander(
                    f'✅ [{type_name}] Paciente #{alert.patient_id} - '
                    f'{format_datetime(alert.created_at)}',
                    expanded=False,
                ):
                    st.markdown(f'**Motivo:** {alert.reason}')
                    st.caption(
                        f'Regla: `{alert.rule_name}` | Reconocida: {format_datetime(alert.acknowledged_at)}'
                    )


def render_queue_table(queue_data: List[Any]) -> None:
    """Renderiza la cola administrativa de atención en una tabla ordenada y destacada.

    Acepta tanto objetos QueueEntry como diccionarios formateados.

    Args:
        queue_data: Lista de QueueEntry o diccionarios con información de la cola.
    """
    if not queue_data:
        st.info('La cola de atención administrativa no tiene pacientes en espera.')
        return

    # Normalizar entradas a formato homogéneo
    normalized: List[Dict[str, Any]] = []
    for item in queue_data:
        if isinstance(item, QueueEntry):
            p = item.patient
            code = p.patient_code if p else 'N/D'
            name = (p.full_name or p.name) if p else 'N/D'
            tinfo = TRIAGE_LEVELS.get(p.triage_level, {}) if (p and p.triage_level) else {}
            triage_label = tinfo.get('short_label', f"Nivel {p.triage_level}") if (p and p.triage_level) else 'N/D'
            symptoms = p.symptoms if (p and p.symptoms) else 'Sin síntomas'
            initial_dx = p.initial_diagnosis if (p and p.initial_diagnosis) else 'Pendiente'

            reasons_str = (
                ', '.join(item.reasons)
                if isinstance(item.reasons, list)
                else str(item.reasons)
            )
            normalized.append({
                'position': item.position,
                'patient_code': code,
                'patient_name': name,
                'triage_label': triage_label,
                'symptoms': symptoms,
                'initial_diagnosis': initial_dx,
                'priority_score': round(item.priority_score, 2),
                'wait_time_minutes': item.wait_time_minutes,
                'wait_time_formatted': format_wait_time(item.wait_time_minutes),
                'pending_alerts': item.pending_alerts,
                'reasons_str': reasons_str,
            })
        elif isinstance(item, dict):
            pos = item.get('position', item.get('posicion', item.get('Posición', 0)))
            code = item.get('patient_code', item.get('codigo', item.get('Código', 'N/D')))
            name = item.get('patient_name', item.get('nombre', item.get('Nombre', 'N/D')))
            triage_label = item.get('triage_label', item.get('triaje', item.get('Triaje', 'N/D')))
            symptoms = item.get('symptoms', item.get('sintomas', item.get('Síntomas', 'Sin síntomas')))
            initial_dx = item.get('initial_diagnosis', item.get('diagnostico', item.get('Diagnóstico inicial', 'Pendiente')))
            score = round(
                float(item.get('priority_score', item.get('score', item.get('Puntuación prioridad', 0.0)))), 2
            )
            wait_m = item.get(
                'wait_time_minutes', item.get('tiempo_espera_minutos', None)
            )
            wait_str = item.get(
                'wait_time_formatted',
                format_wait_time(wait_m)
                if wait_m is not None
                else item.get('tiempo_espera', item.get('Tiempo espera', 'N/D')),
            )
            alerts = item.get('pending_alerts', item.get('alertas', item.get('Alertas pendientes', 0)))
            r_val = item.get('reasons', item.get('reasons_str', item.get('razon', item.get('Razón del orden', ''))))
            reasons_str = (
                ', '.join(r_val) if isinstance(r_val, list) else str(r_val)
            )
            normalized.append({
                'position': pos,
                'patient_code': code,
                'patient_name': name,
                'triage_label': triage_label,
                'symptoms': symptoms,
                'initial_diagnosis': initial_dx,
                'priority_score': score,
                'wait_time_minutes': wait_m,
                'wait_time_formatted': wait_str,
                'pending_alerts': alerts,
                'reasons_str': reasons_str,
            })

    # Destacar al paciente en la posición 1
    if normalized:
        top_patient = normalized[0]
        st.warning(
            f"🔔 **Próximo Paciente a Llamar:** `{top_patient['patient_code']}` ({top_patient['patient_name']}) | "
            f"Triaje: **{top_patient['triage_label']}** | "
            f"Prioridad: **{top_patient['priority_score']}** | "
            f"Factores: {top_patient['reasons_str'] or 'Tiempo estándar'}",
            icon='🚨',
        )

    table_rows = []
    for entry in normalized:
        table_rows.append({
            'Posición': f"#{entry['position']}",
            'Código': entry['patient_code'],
            'Nombre': entry['patient_name'],
            'Triaje': entry['triage_label'],
            'Puntaje Prioridad': entry['priority_score'],
            'Tiempo Espera': entry['wait_time_formatted'],
            'Alertas': (
                f"🚨 {entry['pending_alerts']}"
                if entry['pending_alerts'] > 0
                else '0'
            ),
            'Síntomas': entry['symptoms'],
            'Diagnóstico': entry['initial_diagnosis'],
            'Factores de Priorización': entry['reasons_str'],
        })

    df = pd.DataFrame(table_rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_queue_chart(queue_data: List[Any]) -> None:
    """Renderiza un gráfico de barras con Plotly mostrando los puntajes de prioridad en la cola.

    Args:
        queue_data: Lista de QueueEntry o diccionarios.
    """
    if not queue_data:
        st.info('No hay pacientes en cola para graficar.')
        return

    codes = []
    scores = []
    positions = []
    for item in queue_data:
        if isinstance(item, QueueEntry):
            code = item.patient.patient_code if item.patient else 'N/D'
            codes.append(code)
            scores.append(round(item.priority_score, 2))
            positions.append(item.position)
        elif isinstance(item, dict):
            code = item.get('patient_code', item.get('codigo', 'N/D'))
            score = round(
                float(item.get('priority_score', item.get('score', 0.0))), 2
            )
            pos = item.get('position', item.get('posicion', 0))
            codes.append(code)
            scores.append(score)
            positions.append(pos)

    df_plot = pd.DataFrame({
        'Paciente': codes,
        'Puntaje Prioridad': scores,
        'Posición': positions,
    })

    fig = px.bar(
        df_plot,
        x='Paciente',
        y='Puntaje Prioridad',
        color='Puntaje Prioridad',
        color_continuous_scale='Reds',
        title='Puntaje de Prioridad Administrativa por Paciente',
        text='Puntaje Prioridad',
    )
    fig.update_traces(textposition='outside')
    fig.update_layout(
        xaxis_title='Paciente en Espera',
        yaxis_title='Puntaje Compuesto',
        height=380,
        margin=dict(l=30, r=30, t=50, b=30),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_simulation_config() -> Dict[str, Any]:
    """Renderiza los controles de configuración para una simulación temporal.

    Returns:
        Diccionario con los parámetros del escenario configurados.
    """
    st.subheader('⚙️ Parámetros del Escenario de Simulación')
    st.markdown(
        'Configure los parámetros para la generación determinista de pacientes sintéticos y evolución temporal.'
    )

    c1, c2 = st.columns(2)
    with c1:
        num_patients = st.number_input(
            'Cantidad de Pacientes Sintéticos',
            min_value=1,
            max_value=30,
            value=SIM_DEFAULT_PATIENTS,
            step=1,
            help='Número de perfiles fisiológicos ficticios a instanciar.',
        )
        duration_hours = st.number_input(
            'Duración Total del Escenario (horas)',
            min_value=1,
            max_value=24,
            value=SIM_DEFAULT_DURATION_HOURS,
            step=1,
            help='Ventana temporal total a simular.',
        )
    with c2:
        measurement_interval = st.number_input(
            'Intervalo entre Mediciones (minutos)',
            min_value=5,
            max_value=120,
            value=SIM_DEFAULT_MEASUREMENT_INTERVAL_MINUTES,
            step=5,
            help='Frecuencia temporal con la que se registran signos vitales.',
        )
        random_seed = st.number_input(
            'Semilla Pseudoaleatoria (Seed)',
            min_value=1,
            max_value=999999,
            value=SIM_RANDOM_SEED,
            step=1,
            help='Semilla fija para asegurar reproducibilidad idéntica.',
        )

    # Vista previa de los 5 perfiles clínicos preprogramados
    with st.expander('👥 Ver Perfiles Clínicos Predefinidos de la Simulación', expanded=True):
        st.markdown(
            'El sistema utiliza perfiles sintéticos con cuadros clínicos y evolución realista:'
        )
        profiles_data = [
            {
                'Perfil': 'Estable',
                'Paciente Ficticio': 'Carlos Gómez (Ficticio)',
                'Triaje': 'Nivel IV (Prioritario)',
                'Diagnóstico Inicial': 'Lumbalgia aguda mecánica no complicada',
                'Síntomas': 'Dolor lumbar mecánico de 2 días de evolución, afebril',
            },
            {
                'Perfil': 'Deterioro leve',
                'Paciente Ficticio': 'María Fernanda Torres (Ficticio)',
                'Triaje': 'Nivel III (Urgencia)',
                'Diagnóstico Inicial': 'Infección respiratoria aguda baja / Sospecha de neumonía',
                'Síntomas': 'Tos persistente con expectoración, disnea de medianos esfuerzos',
            },
            {
                'Perfil': 'Crítico',
                'Paciente Ficticio': 'Jorge Eliécer Silva (Ficticio)',
                'Triaje': 'Nivel I (Reanimación)',
                'Diagnóstico Inicial': 'Síndrome coronario agudo / Choque cardiogénico inminente',
                'Síntomas': 'Dolor torácico opresivo retroesternal con diaforesis profusa y disnea',
            },
            {
                'Perfil': 'Datos incompletos',
                'Paciente Ficticio': 'Ana Sofía Morales (Ficticio)',
                'Triaje': 'Nivel III (Urgencia)',
                'Diagnóstico Inicial': 'Cefalea aguda en estudio (requiere completar signos vitales)',
                'Síntomas': 'Cefalea holocraneana pulsátil intensa, náuseas y fotofobia',
            },
            {
                'Perfil': 'Mejora gradual',
                'Paciente Ficticio': 'Luis Alberto Mendoza (Ficticio)',
                'Triaje': 'Nivel II (Emergencia)',
                'Diagnóstico Inicial': 'Crisis asmática aguda moderada en resolución',
                'Síntomas': 'Crisis asmática con dificultad ventilatoria, en mejoría',
            },
        ]
        st.dataframe(pd.DataFrame(profiles_data), use_container_width=True, hide_index=True)

    return {
        'num_patients': int(num_patients),
        'duration_hours': int(duration_hours),
        'measurement_interval_minutes': int(measurement_interval),
        'random_seed': int(random_seed),
    }


def render_simulation_events(events: List[SimulationEvent]) -> None:
    """Muestra la cronología y tabla de eventos ocurridos durante una simulación.

    Args:
        events: Lista de objetos SimulationEvent.
    """
    if not events:
        st.info('No hay eventos registrados en la simulación.')
        return

    st.markdown('##### 📜 Registro Cronológico de Eventos')

    event_types = sorted(list(set(e.event_type for e in events)))
    selected_filter = st.selectbox(
        'Filtrar por tipo de evento:',
        options=['Todos'] + event_types,
        index=0,
    )

    filtered_events = events
    if selected_filter != 'Todos':
        filtered_events = [e for e in events if e.event_type == selected_filter]

    rows = []
    for ev in filtered_events:
        rows.append({
            'Hora / Fecha': format_datetime(ev.event_at),
            'Tipo de Evento': ev.event_type.upper(),
            'Paciente ID': str(ev.patient_id) if ev.patient_id else '-',
            'Descripción del Evento': ev.description,
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_queue_evolution(queue_snapshots: List[List[Dict[str, Any]]]) -> None:
    """Renderiza el gráfico de evolución de posiciones de los pacientes en la cola temporal.

    Args:
        queue_snapshots: Lista de listas de diccionarios, donde cada sublista representa la cola en un paso.
    """
    if not queue_snapshots:
        st.info('No hay registros de evolución de cola disponibles.')
        return

    records = []
    for step_idx, snapshot in enumerate(queue_snapshots):
        for entry in snapshot:
            p_code = entry.get(
                'patient_code',
                entry.get('codigo', str(entry.get('patient_id', 'N/D'))),
            )
            pos = entry.get('position', entry.get('posicion', 0))
            score = entry.get('priority_score', entry.get('score', 0.0))
            records.append({
                'Paso': step_idx,
                'Paciente': p_code,
                'Posición': pos,
                'Puntaje': score,
            })

    if not records:
        st.info('Los snapshots de cola no contienen pacientes.')
        return

    df_evo = pd.DataFrame(records)
    fig = px.line(
        df_evo,
        x='Paso',
        y='Posición',
        color='Paciente',
        markers=True,
        title='Dinámica Temporal de Posiciones en Cola Administrativa',
    )
    # Invertir eje Y para que la posición #1 esté arriba
    fig.update_yaxes(autorange='reversed', dtick=1)
    fig.update_layout(
        xaxis_title='Paso Temporal de Simulación',
        yaxis_title='Posición en Cola (1 = Mayor Prioridad)',
        height=420,
        margin=dict(l=30, r=30, t=50, b=30),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_simulation_results(results: Dict[str, Any]) -> None:
    """Renderiza las métricas, evolución y bitácora de resultados de una simulación.

    Args:
        results: Diccionario de resultados devuelto por run_simulation.
    """
    if not results.get('success', False):
        errs = results.get('errors', [])
        err_msg = ', '.join(errs) if errs else 'Error desconocido durante la ejecución.'
        st.error(f'La simulación no pudo completarse: {err_msg}')
        return

    st.success(
        f"Simulación ejecutada con éxito (ID: `{results.get('simulation_id', 'N/D')}`)"
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric('Pacientes Creados', results.get('patients_created', 0))
    c2.metric('Mediciones Tomadas', results.get('total_measurements', 0))
    c3.metric('Alertas Generadas', results.get('total_alerts', 0))
    c4.metric('Total Eventos Registrados', results.get('total_events', 0))

    st.markdown('---')

    # Visualización detallada de los pacientes creados en la simulación
    patients = results.get('patients', [])
    if patients:
        st.subheader('👥 Pacientes Ficticios Incorporados en Urgencias')
        rows = []
        for p in patients:
            prof = p.get('profile', {})
            t_lvl = prof.get('triage_level')
            t_label = TRIAGE_LEVEL_LABELS.get(t_lvl, f'Nivel {t_lvl}') if 'TRIAGE_LEVEL_LABELS' in globals() else f'Nivel {t_lvl}'
            rows.append({
                'Código': p.get('code'),
                'Nombre del Paciente': prof.get('patient_name'),
                'Perfil': prof.get('name'),
                'Triaje Inicial': t_label,
                'Síntomas Reportados': prof.get('symptoms'),
                'Diagnóstico Inicial': prof.get('initial_diagnosis'),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.info(
            '💡 **Paso siguiente:** Puedes explorar el detalle de cada paciente en el **📋 Panel de Pacientes** '
            'o ver su posición y factores de atención en la **📈 Cola de Atención**.'
        )
        st.markdown('---')

    snapshots = results.get('queue_snapshots', [])
    if snapshots:
        render_queue_evolution(snapshots)

    events = results.get('events', [])
    if events:
        render_simulation_events(events)


def render_news2_explanation() -> None:
    """Renderiza la explicación técnica y tablas de referencia de la escala clínica NEWS2."""
    st.subheader('📖 Metodología NEWS2 (Royal College of Physicians, 2017)')
    st.markdown("""
    La escala **NEWS2** (National Early Warning Score 2) es un estándar clínico internacional diseñado 
    para detectar oportunamente el deterioro fisiológico agudo en pacientes adultos. Evalúa 7 parámetros fisiológicos 
    y asigna puntajes de 0 a 3 según el grado de desviación de los valores normales.
    """)

    parameters_table = [
        {
            'Parámetro Fisiológico': 'Frecuencia Respiratoria (rpm)',
            '3 Puntos': '<= 8',
            '2 Puntos': '-',
            '1 Punto': '9 - 11',
            '0 Puntos (Normal)': '12 - 20',
            '1 Punto ': '21 - 24',
            '2 Puntos ': '-',
            '3 Puntos ': '>= 25',
        },
        {
            'Parámetro Fisiológico': 'Saturación SpO2 Escala 1 (%)',
            '3 Puntos': '<= 91',
            '2 Puntos': '92 - 93',
            '1 Punto': '94 - 95',
            '0 Puntos (Normal)': '>= 96',
            '1 Punto ': '-',
            '2 Puntos ': '-',
            '3 Puntos ': '-',
        },
        {
            'Parámetro Fisiológico': 'Oxígeno Suplementario',
            '3 Puntos': '-',
            '2 Puntos': 'Sí',
            '1 Punto': '-',
            '0 Puntos (Normal)': 'Aire ambiente (No)',
            '1 Punto ': '-',
            '2 Puntos ': '-',
            '3 Puntos ': '-',
        },
        {
            'Parámetro Fisiológico': 'Presión Sistólica (mmHg)',
            '3 Puntos': '<= 90',
            '2 Puntos': '91 - 100',
            '1 Punto': '101 - 110',
            '0 Puntos (Normal)': '111 - 219',
            '1 Punto ': '-',
            '2 Puntos ': '-',
            '3 Puntos ': '>= 220',
        },
        {
            'Parámetro Fisiológico': 'Frecuencia Cardíaca (lpm)',
            '3 Puntos': '<= 40',
            '2 Puntos': '-',
            '1 Punto': '41 - 50',
            '0 Puntos (Normal)': '51 - 90',
            '1 Punto ': '91 - 110',
            '2 Puntos ': '111 - 130',
            '3 Puntos ': '>= 131',
        },
        {
            'Parámetro Fisiológico': 'Nivel de Conciencia (AVPU)',
            '3 Puntos': 'V, P o U',
            '2 Puntos': '-',
            '1 Punto': '-',
            '0 Puntos (Normal)': 'Alerta (A)',
            '1 Punto ': '-',
            '2 Puntos ': '-',
            '3 Puntos ': '-',
        },
        {
            'Parámetro Fisiológico': 'Temperatura (°C)',
            '3 Puntos': '<= 35.0',
            '2 Puntos': '-',
            '1 Punto': '35.1 - 36.0',
            '0 Puntos (Normal)': '36.1 - 38.0',
            '1 Punto ': '38.1 - 39.0',
            '2 Puntos ': '>= 39.1',
            '3 Puntos ': '-',
        },
    ]

    st.markdown('##### Matriz de Puntuación Fisiológica')
    st.dataframe(
        pd.DataFrame(parameters_table), use_container_width=True, hide_index=True
    )

    st.markdown('##### Estratificación de Riesgo Clínico y Umbrales de Respuesta')
    risk_thresholds = [
        {
            'Puntuación Agregada': '0 a 4 puntos',
            'Nivel de Riesgo': 'Bajo',
            'Respuesta Clínica Estándar Recomendada': (
                'Evaluación periódica por enfermería en sala de espera/observación.'
            ),
        },
        {
            'Puntuación Agregada': 'Puntaje de 3 en un solo parámetro',
            'Nivel de Riesgo': 'Bajo-Medio (Alerta Roja)',
            'Respuesta Clínica Estándar Recomendada': (
                'Evaluación médica urgente del parámetro extremo específico.'
            ),
        },
        {
            'Puntuación Agregada': '5 a 6 puntos',
            'Nivel de Riesgo': 'Medio',
            'Respuesta Clínica Estándar Recomendada': (
                'Revisión médica urgente y optimización del monitoreo continuo.'
            ),
        },
        {
            'Puntuación Agregada': '7 o más puntos',
            'Nivel de Riesgo': 'Alto',
            'Respuesta Clínica Estándar Recomendada': (
                'Respuesta médica inmediata por equipo de emergencias / evaluación para UCI.'
            ),
        },
    ]
    st.dataframe(
        pd.DataFrame(risk_thresholds), use_container_width=True, hide_index=True
    )

    st.caption("""
    *Referencia Formal:* Royal College of Physicians. *National Early Warning Score (NEWS) 2: 
    Standardising the assessment of acute-illness severity in the NHS*. Updated report of a working party. 
    London: RCP, 2017.
    """)


def render_methodology_page() -> None:
    """Renderiza la pantalla completa de metodología, reglas administrativas y limitaciones."""
    st.title('📚 Configuración y Metodología')
    st.markdown(METHODOLOGY_TEXT)

    render_news2_explanation()

    st.markdown('---')
    st.subheader('⚖️ Reglas Administrativas de Priorización en Cola')
    st.markdown("""
    La cola de atención administrativa combina el riesgo clínico (NEWS2), las alertas operativas 
    activas y el tiempo de espera acumulado mediante una fórmula explicable y transparente:
    """)

    rules_df = pd.DataFrame(PRIORITY_RULES)
    st.dataframe(rules_df, use_container_width=True, hide_index=True)

    st.markdown('---')
    st.subheader('⚠️ Limitaciones Formales del Prototipo')
    st.markdown("""
    - **No apto para uso asistencial real:** Este sistema es un simulador académico y carece de validación clínica o regulatoria.
    - **Independencia del Triage Legal:** Las categorías oficiales de Triage I a V (Resolución 5596 de 2015 del Ministerio de Salud) 
      **no** son asignadas automáticamente por umbrales algorítmicos.
    - **NEWS2 es informativo:** La escala NEWS2 cuantifica riesgo fisiológico general, no diagnósticos etiológicos.
    - **Cola administrativa simulada:** El orden sugerido es una asistencia visual y no reemplaza el criterio médico.
    - **Ficticio y confidencialidad:** No se almacenan ni procesan datos reales de pacientes identificables.
    """)
