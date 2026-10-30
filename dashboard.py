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


def get_glassmorphism_css() -> str:
    """Retorna la hoja de estilos CSS Dark Glassmorphism para la plataforma clínica."""
    return """
    <style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

    /* Variables del tema clínico Dark Glassmorphism */
    :root {
        --bg-glass-dark: rgba(15, 23, 42, 0.72);
        --bg-glass-card: rgba(17, 28, 51, 0.65);
        --bg-glass-hover: rgba(26, 41, 74, 0.78);
        --border-glass: rgba(255, 255, 255, 0.09);
        --border-glass-glow: rgba(56, 189, 248, 0.45);
        --primary-cyan: #38bdf8;
        --accent-emerald: #10b981;
        --accent-amber: #f59e0b;
        --accent-coral: #ef4444;
        --text-primary: #f8fafc;
        --text-secondary: #94a3b8;
        --text-muted: #64748b;
    }

    /* Fondo principal con efecto hospitalario difuminado y gradiente oscuro de alta legibilidad */
    .stApp {
        background: 
            radial-gradient(circle at 12% 18%, rgba(20, 50, 95, 0.45) 0%, transparent 40%),
            radial-gradient(circle at 88% 82%, rgba(13, 148, 136, 0.25) 0%, transparent 45%),
            linear-gradient(135deg, rgba(8, 15, 30, 0.94) 0%, rgba(13, 22, 40, 0.96) 50%, rgba(15, 23, 42, 0.98) 100%),
            url('https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?auto=format&fit=crop&w=1920&q=80') center center / cover no-repeat fixed;
        background-color: #080f1e;
        color: var(--text-primary);
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }

    /* Ocultar barra superior por defecto de Streamlit para acabado limpio */
    header[data-testid="stHeader"] {
        background: transparent !important;
        backdrop-filter: none !important;
    }

    /* Barra lateral estilo Dark Glass */
    [data-testid="stSidebar"] {
        background: rgba(10, 17, 32, 0.88) !important;
        backdrop-filter: blur(24px) !important;
        -webkit-backdrop-filter: blur(24px) !important;
        border-right: 1px solid var(--border-glass) !important;
        box-shadow: 4px 0 24px rgba(0, 0, 0, 0.45) !important;
    }

    [data-testid="stSidebar"] .stRadio label {
        color: #cbd5e1 !important;
        transition: all 0.2s ease !important;
        padding: 5px 8px !important;
        border-radius: 8px !important;
    }

    [data-testid="stSidebar"] .stRadio label:hover {
        color: var(--primary-cyan) !important;
        background: rgba(56, 189, 248, 0.08) !important;
    }

    /* Tarjeta de alerta destacada en la barra lateral */
    .sidebar-alert-card {
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.16) 0%, rgba(180, 83, 9, 0.10) 100%);
        border: 1px solid rgba(245, 158, 11, 0.45);
        border-radius: 12px;
        padding: 14px;
        margin: 12px 0 8px 0;
        box-shadow: 0 4px 20px rgba(245, 158, 11, 0.15), inset 0 0 12px rgba(245, 158, 11, 0.05);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        transition: all 0.3s ease;
    }
    .sidebar-alert-card:hover {
        border-color: rgba(245, 158, 11, 0.8);
        box-shadow: 0 6px 24px rgba(245, 158, 11, 0.28);
        transform: translateY(-1px);
    }
    .sidebar-alert-title {
        font-weight: 700;
        color: #fbbf24;
        font-size: 0.95rem;
        margin-bottom: 6px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    .sidebar-alert-sub {
        font-size: 0.8rem;
        color: #fde68a;
        margin-bottom: 10px;
    }

    /* Cabecera superior moderna con perfil de usuario */
    .top-nav-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: var(--bg-glass-dark);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid var(--border-glass);
        border-radius: 16px;
        padding: 16px 26px;
        margin-bottom: 24px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.37);
        position: relative;
        overflow: hidden;
    }
    .top-nav-header::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent 0%, #38bdf8 30%, #10b981 70%, transparent 100%);
    }
    .header-left-title {
        font-size: 1.45rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: #f8fafc;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .header-left-subtitle {
        font-size: 0.88rem;
        color: #94a3b8;
        margin-top: 4px;
        font-weight: 500;
    }
    .header-right-user {
        display: flex;
        align-items: center;
        gap: 14px;
    }
    .user-profile-badge {
        display: flex;
        align-items: center;
        gap: 10px;
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 30px;
        padding: 6px 14px 6px 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }
    .user-avatar-img {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        border: 2px solid #38bdf8;
        object-fit: cover;
    }
    .user-name-text {
        font-size: 0.88rem;
        font-weight: 600;
        color: #f1f5f9;
    }
    .header-pill-btn {
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.1);
        color: #94a3b8;
        padding: 6px 14px;
        border-radius: 20px;
        font-size: 0.82rem;
        font-weight: 600;
        letter-spacing: 0.02em;
    }
    .notification-bell {
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 36px;
        height: 36px;
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 50%;
        color: #e2e8f0;
        font-size: 1rem;
    }
    .bell-badge-pill {
        position: absolute;
        top: -3px;
        right: -3px;
        background: #ef4444;
        color: white;
        font-size: 0.68rem;
        font-weight: 700;
        width: 17px;
        height: 17px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 0 8px rgba(239, 68, 68, 0.6);
    }

    /* Hero Glass Container */
    .glass-hero-container {
        background: var(--bg-glass-dark);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid var(--border-glass);
        border-radius: 18px;
        padding: 26px;
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.45);
        margin-bottom: 26px;
        position: relative;
    }

    /* Tarjetas Modulares Glass */
    .glass-card {
        background: var(--bg-glass-card);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid var(--border-glass);
        border-radius: 14px;
        padding: 22px 24px;
        margin-bottom: 18px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        height: 100%;
    }
    .glass-card:hover {
        border-color: var(--border-glass-glow);
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.4), 0 0 20px rgba(56, 189, 248, 0.12);
        transform: translateY(-2px);
    }

    /* Espaciado general de bloques para reducir densidad visual */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 3rem !important;
        max-width: 1440px !important;
    }
    div[data-testid="stVerticalBlock"] > div {
        margin-bottom: 0.35rem;
    }

    /* Tarjetas de Acceso Rápido / Shortcuts */
    .glass-action-card {
        background: linear-gradient(145deg, rgba(17, 28, 51, 0.72) 0%, rgba(15, 23, 42, 0.82) 100%);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid var(--border-glass);
        border-radius: 14px;
        padding: 22px;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        min-height: 220px;
    }
    .glass-action-card:hover {
        border-color: rgba(56, 189, 248, 0.45);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.45), 0 0 20px rgba(56, 189, 248, 0.15);
        transform: translateY(-3px);
    }
    .action-card-header {
        display: flex;
        align-items: center;
        gap: 14px;
        margin-bottom: 12px;
    }
    .action-icon-wrap {
        width: 44px;
        height: 44px;
        border-radius: 10px;
        background: linear-gradient(135deg, rgba(56, 189, 248, 0.2) 0%, rgba(14, 165, 233, 0.1) 100%);
        border: 1px solid rgba(56, 189, 248, 0.3);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.35rem;
    }
    .action-title {
        font-size: 1.15rem;
        font-weight: 700;
        color: #f1f5f9;
        margin: 0;
    }
    .action-list {
        list-style: none;
        padding: 0;
        margin: 0 0 18px 0;
        font-size: 0.88rem;
        color: #94a3b8;
    }
    .action-list li {
        margin-bottom: 6px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .action-list li::before {
        content: '•';
        color: #38bdf8;
        font-weight: bold;
    }

    /* Banner de Advertencia Regulatoria */
    .glass-warning-banner {
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.14) 0%, rgba(180, 83, 9, 0.08) 100%);
        border: 1px solid rgba(245, 158, 11, 0.38);
        border-radius: 12px;
        padding: 16px 20px;
        margin: 22px 0;
        box-shadow: 0 6px 24px rgba(245, 158, 11, 0.12);
        backdrop-filter: blur(14px);
        font-size: 0.88rem;
        line-height: 1.55;
        color: #fef3c7;
    }

    /* Pie de página institucional */
    .glass-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 16px 4px 8px 4px;
        margin-top: 24px;
        border-top: 1px solid rgba(255, 255, 255, 0.08);
        font-size: 0.84rem;
        color: #64748b;
    }

    /* Sobrescribir Métricas de Streamlit */
    div[data-testid="stMetric"] {
        background: var(--bg-glass-card) !important;
        backdrop-filter: blur(14px) !important;
        -webkit-backdrop-filter: blur(14px) !important;
        border: 1px solid var(--border-glass) !important;
        border-radius: 12px !important;
        padding: 14px 18px !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25) !important;
        transition: all 0.25s ease !important;
    }
    div[data-testid="stMetric"]:hover {
        border-color: var(--border-glass-glow) !important;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.35), 0 0 12px rgba(56, 189, 248, 0.12) !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
        font-size: 0.84rem !important;
        font-weight: 500 !important;
    }
    div[data-testid="stMetricValue"] {
        color: #f8fafc !important;
        font-weight: 700 !important;
        font-size: 1.55rem !important;
    }

    /* Sobrescribir Botones de Streamlit */
    .stButton > button {
        background: linear-gradient(135deg, rgba(30, 58, 138, 0.65) 0%, rgba(15, 23, 42, 0.85) 100%) !important;
        color: #f1f5f9 !important;
        border: 1px solid rgba(56, 189, 248, 0.35) !important;
        border-radius: 10px !important;
        padding: 0.5rem 1.15rem !important;
        font-weight: 600 !important;
        backdrop-filter: blur(10px) !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25) !important;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, rgba(37, 99, 235, 0.85) 0%, rgba(30, 58, 138, 0.95) 100%) !important;
        border-color: rgba(56, 189, 248, 0.65) !important;
        box-shadow: 0 6px 20px rgba(37, 99, 235, 0.35), 0 0 16px rgba(56, 189, 248, 0.2) !important;
        transform: translateY(-1px) !important;
        color: #ffffff !important;
    }
    .stButton > button:active {
        transform: translateY(1px) !important;
    }

    /* Sobrescribir Tablas / DataFrames */
    [data-testid="stDataFrame"] {
        border: 1px solid var(--border-glass) !important;
        border-radius: 12px !important;
        overflow: hidden !important;
        background: rgba(15, 23, 42, 0.5) !important;
        backdrop-filter: blur(14px) !important;
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.25) !important;
    }

    /* Sobrescribir Expanders */
    div[data-testid="stExpander"] {
        background: rgba(17, 28, 51, 0.45) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border: 1px solid var(--border-glass) !important;
        border-radius: 12px !important;
        overflow: hidden !important;
        margin-bottom: 12px !important;
    }

    /* Sobrescribir Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px !important;
        background: rgba(15, 23, 42, 0.5) !important;
        padding: 6px 8px !important;
        border-radius: 12px !important;
        border: 1px solid var(--border-glass) !important;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px !important;
        color: #94a3b8 !important;
        padding: 8px 16px !important;
        font-weight: 500 !important;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(30, 58, 138, 0.6) !important;
        color: #38bdf8 !important;
        border: 1px solid rgba(56, 189, 248, 0.35) !important;
    }
    </style>
    """


def render_top_header(pending_alerts_count: int = 0) -> None:
    """Renderiza la cabecera superior moderna con título y perfil de usuario activo."""
    badge_color = "#ef4444" if pending_alerts_count > 0 else "#10b981"
    st.markdown(
        f"""
        <div class="top-nav-header">
            <div class="header-left">
                <div class="header-left-title">
                    <span>🏥 {APP_NAME} — Sistema de Priorización Dinámica en Urgencias</span>
                </div>
                <div class="header-left-subtitle">
                    Equipo de Desarrollo: <strong style="color:#38bdf8;">{TEAM_NAME}</strong> &bull; Entorno Académico Simulado
                </div>
            </div>
            <div class="header-right-user">
                <div class="user-profile-badge">
                    <img src="https://images.unsplash.com/photo-1622253692010-333f2da6031d?auto=format&fit=crop&w=100&q=80" class="user-avatar-img" alt="Avatar Dr. Silva" />
                    <span class="user-name-text">Dr. A. Silva (Simulación)</span>
                </div>
                <div class="header-pill-btn">Prototipo v{APP_VERSION}</div>
                <div class="notification-bell" title="Alertas clínicas u operativas pendientes">
                    🔔<span class="bell-badge-pill" style="background:{badge_color};">{pending_alerts_count}</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def apply_dark_glass_theme(
    fig: go.Figure,
    height: Optional[int] = None,
    title: Optional[str] = None,
) -> go.Figure:
    """Aplica un tema Dark Glassmorphism consistente a cualquier figura de Plotly.

    Args:
        fig: Figura de Plotly a estilizar.
        height: Altura opcional en píxeles.
        title: Título opcional del gráfico.

    Returns:
        Figura con tema oscuro, fondos transparentes y tipografía médica moderna.
    """
    layout_args: Dict[str, Any] = {
        'template': 'plotly_dark',
        'paper_bgcolor': 'rgba(0,0,0,0)',
        'plot_bgcolor': 'rgba(0,0,0,0)',
        'font': dict(
            family='Inter, -apple-system, sans-serif',
            color='#e2e8f0',
            size=11,
        ),
        'hoverlabel': dict(
            bgcolor='rgba(15, 23, 42, 0.95)',
            bordercolor='rgba(56, 189, 248, 0.5)',
            font=dict(family='Inter, sans-serif', color='#f8fafc', size=11),
        ),
        'margin': dict(l=30, r=25, t=40 if title else 20, b=25),
    }
    if height is not None:
        layout_args['height'] = height
    if title is not None:
        layout_args['title'] = dict(
            text=title,
            font=dict(family='Inter, sans-serif', size=13, color='#f1f5f9'),
        )
    fig.update_layout(**layout_args)
    fig.update_xaxes(
        showgrid=True,
        gridcolor='rgba(255, 255, 255, 0.06)',
        zerolinecolor='rgba(255, 255, 255, 0.1)',
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor='rgba(255, 255, 255, 0.06)',
        zerolinecolor='rgba(255, 255, 255, 0.1)',
    )
    return fig


def create_home_network_chart() -> go.Figure:
    """Genera el esquema conceptual ilustrativo de la arquitectura NEWS2 y priorización."""
    nodes = [
        {"id": "NEWS2", "label": "Motor NEWS2", "x": 0.0, "y": 0.0, "color": "#f59e0b", "size": 22, "type": "Cálculo Fisiológico"},
        {"id": "SpO2", "label": "SpO2 (%)", "x": -0.6, "y": 0.55, "color": "#06b6d4", "size": 15, "type": "Parámetro Vital"},
        {"id": "FC", "label": "FC (lpm)", "x": -0.75, "y": 0.05, "color": "#06b6d4", "size": 15, "type": "Parámetro Vital"},
        {"id": "FR", "label": "FR (rpm)", "x": -0.5, "y": -0.55, "color": "#06b6d4", "size": 15, "type": "Parámetro Vital"},
        {"id": "TA", "label": "PAS (mmHg)", "x": 0.1, "y": -0.65, "color": "#06b6d4", "size": 15, "type": "Parámetro Vital"},
        {"id": "Temp", "label": "Temp (°C)", "x": 0.55, "y": -0.45, "color": "#06b6d4", "size": 15, "type": "Parámetro Vital"},
        {"id": "AVPU", "label": "AVPU / O2", "x": 0.2, "y": 0.65, "color": "#06b6d4", "size": 15, "type": "Parámetro Vital"},
        {"id": "Triaje", "label": "Triaje Inicial (I-V)", "x": 0.75, "y": 0.45, "color": "#ef4444", "size": 17, "type": "Clasificación en Admisión"},
        {"id": "Alertas", "label": "Motor de Alertas", "x": 0.78, "y": -0.15, "color": "#f97316", "size": 17, "type": "Reglas Reactivas"},
        {"id": "Prioridad", "label": "Cola Administrativa", "x": 0.45, "y": 0.08, "color": "#8b5cf6", "size": 19, "type": "Ordenamiento Explicable"},
    ]

    edges = [
        ("SpO2", "NEWS2"), ("FC", "NEWS2"), ("FR", "NEWS2"), ("TA", "NEWS2"),
        ("Temp", "NEWS2"), ("AVPU", "NEWS2"),
        ("NEWS2", "Prioridad"), ("NEWS2", "Alertas"),
        ("Triaje", "Prioridad"), ("Alertas", "Prioridad"),
    ]

    node_dict = {n["id"]: n for n in nodes}

    edge_x: List[Optional[float]] = []
    edge_y: List[Optional[float]] = []
    for src, dst in edges:
        edge_x.extend([node_dict[src]["x"], node_dict[dst]["x"], None])
        edge_y.extend([node_dict[src]["y"], node_dict[dst]["y"], None])

    edge_trace = go.Scatter(
        x=edge_x,
        y=edge_y,
        mode="lines",
        line=dict(color="rgba(56, 189, 248, 0.32)", width=1.5),
        hoverinfo="none",
    )

    node_x = [n["x"] for n in nodes]
    node_y = [n["y"] for n in nodes]
    node_color = [n["color"] for n in nodes]
    node_size = [n["size"] for n in nodes]
    node_text = [f"<b>{n['label']}</b><br>Componente: {n['type']}" for n in nodes]

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        hoverinfo="text",
        text=[n["label"] for n in nodes],
        textposition="top center",
        textfont=dict(family="Inter, sans-serif", size=10, color="#94a3b8"),
        hovertext=node_text,
        marker=dict(
            color=node_color,
            size=node_size,
            line=dict(color="rgba(255, 255, 255, 0.8)", width=1.5),
        ),
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    apply_dark_glass_theme(
        fig,
        height=310,
        title="Esquema Conceptual Ilustrativo: Flujo NEWS2 y Priorización",
    )
    fig.update_layout(
        showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        margin=dict(l=10, r=10, t=35, b=10),
    )
    return fig


def create_home_triage_bar_chart(patients: Optional[List[Patient]] = None) -> go.Figure:
    """Genera el gráfico de distribución actual de pacientes registrados por nivel de triaje."""
    categories = ['I', 'II', 'III', 'IV', 'V', 'S/C']
    level_keys = [1, 2, 3, 4, 5, None]
    pts = patients or []

    en_espera = []
    en_atencion = []
    con_alertas = []

    for lvl in level_keys:
        matching = [p for p in pts if p.triage_level == lvl]
        en_espera.append(sum(1 for p in matching if p.administrative_status == 'en_espera'))
        en_atencion.append(sum(1 for p in matching if p.administrative_status == 'en_atencion'))
        con_alertas.append(
            sum(
                1
                for p in matching
                if p.administrative_status in ('en_espera', 'en_atencion')
                and (p.pending_alerts_count or 0) > 0
            )
        )

    fig = go.Figure(data=[
        go.Bar(name='En Espera', x=categories, y=en_espera, marker_color='#06b6d4'),
        go.Bar(name='En Atención', x=categories, y=en_atencion, marker_color='#f59e0b'),
        go.Bar(name='Con Alertas', x=categories, y=con_alertas, marker_color='#ef4444'),
    ])

    fig.update_layout(
        barmode='group',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=10, color="#94a3b8"),
        ),
    )
    apply_dark_glass_theme(
        fig, height=195, title="Pacientes Activos por Triaje (Base de Datos Local)"
    )
    fig.update_layout(
        xaxis_title="Nivel Triaje (S/C = Sin clasificar)",
        yaxis_title="Pacientes",
        margin=dict(l=25, r=20, t=38, b=25),
    )
    return fig


def render_disclaimer() -> None:
    """Muestra el descargo de responsabilidad académica en un cuadro de advertencia visible."""
    st.warning(DISCLAIMER_TEXT, icon='⚠️')


def render_home_page(patients: Optional[List[Patient]] = None) -> None:
    """Renderiza la página principal con resumen del prototipo, métricas reales y accesos claros."""
    pts = patients or []
    total_active = sum(1 for p in pts if p.administrative_status in ('en_espera', 'en_atencion'))
    manual_count = sum(1 for p in pts if not p.is_simulated)
    sim_count = sum(1 for p in pts if p.is_simulated)

    st.markdown('<div class="glass-hero-container">', unsafe_allow_html=True)

    col_left, col_center, col_right = st.columns([1.45, 1.35, 1.2])

    with col_left:
        st.markdown(
            """
            <h3 style="font-weight:700; color:#f8fafc; margin-top:0; margin-bottom:12px;">
                Prototipo Académico de Priorización Dinámica en Urgencias
            </h3>
            <p style="color:#94a3b8; font-size:0.9rem; line-height:1.6; margin-bottom:16px;">
                Este sistema es un <strong>prototipo de investigación y docencia académica</strong> que demuestra cómo 
                estructurar el registro de pacientes ficticios, el cálculo de deterioro fisiológico <strong>NEWS2</strong> 
                y una cola administrativa explicable sin sustituir el criterio médico ni el triaje clínico presencial.
            </p>
            <div style="font-weight:600; color:#cbd5e1; margin-bottom:10px; font-size:0.92rem;">
                Flujo de Trabajo Integrado:
            </div>
            <ul style="list-style:none; padding-left:0; margin:0; font-size:0.86rem; color:#94a3b8; line-height:1.7;">
                <li style="margin-bottom:6px;"><span style="color:#38bdf8;">👥</span> <strong style="color:#e2e8f0;">1. Pacientes:</strong> Admisión, listado filtrable y consulta de ficha clínica e historial.</li>
                <li style="margin-bottom:6px;"><span style="color:#10b981;">🩺</span> <strong style="color:#e2e8f0;">2. Atención:</strong> Captura de signos vitales, evaluación NEWS2 (RCP 2017) y gestión de alertas.</li>
                <li style="margin-bottom:6px;"><span style="color:#a855f7;">📈</span> <strong style="color:#e2e8f0;">3. Cola de Atención:</strong> Ordenamiento administrativo explicable según triaje, NEWS2, alertas y espera.</li>
                <li style="margin-bottom:6px;"><span style="color:#06b6d4;">🔬</span> <strong style="color:#e2e8f0;">4. Simulación:</strong> Escenarios sintéticos reproducibles claramente diferenciados de registros manuales.</li>
            </ul>
            """,
            unsafe_allow_html=True,
        )

    with col_center:
        fig_network = create_home_network_chart()
        st.plotly_chart(
            fig_network, use_container_width=True, config={'displayModeBar': False}
        )
        st.caption(
            "📌 *Diagrama estático demostrativo de la arquitectura conceptual del prototipo (no representa telemetría en vivo).*"
        )

    with col_right:
        fig_bar = create_home_triage_bar_chart(pts)
        st.plotly_chart(
            fig_bar, use_container_width=True, config={'displayModeBar': False}
        )

        st.markdown(
            f"""
            <div class="glass-card" style="padding:14px; margin-top:8px;">
                <div style="font-weight:700; color:#38bdf8; font-size:0.88rem; margin-bottom:6px; display:flex; align-items:center; gap:6px;">
                    ℹ️ Estado Actual de la Base de Datos Local
                </div>
                <div style="font-size:0.8rem; color:#94a3b8; line-height:1.55;">
                    <div>• <strong>Registros totales:</strong> <code style="color:#f8fafc;">{len(pts)}</code> ({manual_count} manuales / {sim_count} simulados)</div>
                    <div>• <strong>En espera o atención activa:</strong> <code style="color:#38bdf8;">{total_active}</code></div>
                    <div>• <strong>Escala fisiológica:</strong> NEWS2 (RCP, 2017)</div>
                    <div>• <strong>Versión del prototipo:</strong> <code style="color:#38bdf8;">{APP_VERSION}</code></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)

    # Fila de 3 Tarjetas de Acceso Rápido a las tareas principales (en español)
    sc1, sc2, sc3 = st.columns(3)

    with sc1:
        st.markdown(
            """
            <div class="glass-action-card">
                <div>
                    <div class="action-card-header">
                        <div class="action-icon-wrap">👥</div>
                        <div>
                            <div class="action-title">Gestión y Admisión de Pacientes</div>
                            <div style="font-size:0.78rem; color:#94a3b8;">Listado, Filtros y Nuevo Ingreso</div>
                        </div>
                    </div>
                    <ul class="action-list">
                        <li>Consulta del padrón de pacientes y su estado</li>
                        <li>Admisión de nuevos pacientes ficticios</li>
                        <li>Verificación explícita de triaje e historial</li>
                    </ul>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            "👥 Ir a Pacientes y Admisión",
            key="btn_quick_patients",
            use_container_width=True,
        ):
            st.session_state["current_page"] = "👥 Pacientes"
            st.rerun()

    with sc2:
        st.markdown(
            """
            <div class="glass-action-card">
                <div>
                    <div class="action-card-header">
                        <div class="action-icon-wrap">🩺</div>
                        <div>
                            <div class="action-title">Atención Clínica y Evaluación NEWS2</div>
                            <div style="font-size:0.78rem; color:#94a3b8;">Signos Vitales, Desglose y Alertas</div>
                        </div>
                    </div>
                    <ul class="action-list">
                        <li>Captura de los 7 parámetros fisiológicos</li>
                        <li>Cálculo y desglose inmediato de NEWS2</li>
                        <li>Revisión diferenciada de alertas y cambios</li>
                    </ul>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            "🩺 Ir a Atención y Evaluación NEWS2",
            key="btn_quick_care",
            use_container_width=True,
        ):
            st.session_state["current_page"] = "🩺 Atención"
            st.rerun()

    with sc3:
        st.markdown(
            """
            <div class="glass-action-card">
                <div>
                    <div class="action-card-header">
                        <div class="action-icon-wrap">📈</div>
                        <div>
                            <div class="action-title">Cola de Atención y Simulación</div>
                            <div style="font-size:0.78rem; color:#94a3b8;">Priorización Explicable y Escenarios</div>
                        </div>
                    </div>
                    <ul class="action-list">
                        <li>Ordenamiento administrativo de pacientes en espera</li>
                        <li>Explicación transparente de factores de prioridad</li>
                        <li>Simulador académico de perfiles clínicos</li>
                    </ul>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            "📈 Ir a Cola de Atención",
            key="btn_quick_queue",
            use_container_width=True,
        ):
            st.session_state["current_page"] = "📈 Cola de Atención"
            st.rerun()

    # Banner de Aviso Legal y Académico en estilo Glass Amber
    st.markdown(
        """
        <div class="glass-warning-banner">
            <strong>⚠️ AVISO LEGAL Y ACADÉMICO:</strong> Este software es un prototipo desarrollado con fines estrictamente 
            académicos e investigativos por el equipo <strong>TechMinds</strong>. Todos los datos de pacientes, nombres, 
            mediciones y asistencias no representan personas vivas ni sustituyen el juicio clínico profesional. Cualquier asignación 
            de prioridad es puramente administrativa para demostración y docencia del sistema.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Pie de página institucional
    st.markdown(
        f"""
        <div class="glass-footer">
            <div>
                <span style="color:#94a3b8; font-weight:500;">⚖️ Prototipo Académico sin validez diagnóstica ni asistencial real</span>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
                <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#38bdf8;"></span>
                <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:#a855f7;"></span>
                <strong style="color:#e2e8f0;">{TEAM_NAME}</strong>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_patient_table(patients: List[Patient]) -> None:
    """Renderiza la tabla de pacientes con estado, tiempo de espera, alertas clínicas y último NEWS2.

    Args:
        patients: Lista de objetos Patient a mostrar.
    """
    if not patients:
        st.info('No hay pacientes registrados en este momento.')
        return

    total_patients = len(patients)
    en_espera = sum(1 for p in patients if p.administrative_status == 'en_espera')
    con_alertas = sum(1 for p in patients if (p.pending_alerts_count or 0) > 0)
    simulados = sum(1 for p in patients if p.is_simulated)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric('Pacientes Listados', total_patients)
    m2.metric('En Sala de Espera', en_espera)
    m3.metric('Con Alertas Clínicas', con_alertas)
    m4.metric('Origen Simulado', simulados)

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
            else 'Pendiente de clasificar'
        )
        patient_name = p.full_name or p.name or 'N/D'
        wait_display = (
            'Finalizada (0m)'
            if p.administrative_status in ('atendido', 'alta')
            else format_wait_time(p.wait_time_minutes)
        )

        table_data.append({
            'Código': p.patient_code,
            'Nombre': patient_name,
            'Triaje Registrado': triage_display,
            'Estado': status_display,
            'Tiempo Espera': wait_display,
            'Último NEWS2': score_display,
            'Alertas Clínicas': alerts_display,
            'Origen': '🔬 Simulado' if p.is_simulated else '👤 Manual',
        })

    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_patient_card(
    patient: Patient, latest_measurement: Optional[Measurement] = None
) -> None:
    """Muestra una tarjeta detallada con el resumen clínico y administrativo de un paciente.

    Args:
        patient: Objeto Patient a detallar.
        latest_measurement: Última medición registrada del paciente (opcional).
    """
    status_label = ADMIN_STATUS_LABELS.get(
        patient.administrative_status, patient.administrative_status
    )
    emoji = get_status_emoji(patient.administrative_status)
    sim_tag = ' *(Paciente Simulado)*' if patient.is_simulated else ' *(Ingreso Manual)*'
    patient_name = patient.full_name or patient.name or 'Paciente Ficticio'

    triage_info = TRIAGE_LEVELS.get(patient.triage_level or 0, {})
    triage_short = (
        triage_info.get('short_label', f'Nivel {patient.triage_level}')
        if patient.triage_level
        else 'Pendiente de verificación / Sin clasificar'
    )
    triage_color = triage_info.get('color', '#64748b')

    st.markdown(
        f"### {emoji} **{patient_name}** (`{patient.patient_code}`){sim_tag} "
        f"<span style='background-color:{triage_color}; color:white; padding:4px 12px; border-radius:12px; font-size:0.82em; margin-left:10px;'>{triage_short}</span>",
        unsafe_allow_html=True,
    )

    wait_val = (
        'Finalizada'
        if patient.administrative_status in ('atendido', 'alta')
        else format_wait_time(patient.wait_time_minutes)
    )

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric('Estado Administrativo', status_label)
    with col2:
        st.metric(
            'Triaje Registrado',
            triage_info.get('short_label', 'Sin clasificar') if patient.triage_level else 'Sin clasificar',
        )
    with col3:
        st.metric('Tiempo de Espera', wait_val)
    with col4:
        alerts_val = patient.pending_alerts_count or 0
        st.metric(
            'Alertas Clínicas Activas',
            f'🚨 {alerts_val}' if alerts_val > 0 else '✅ 0',
        )
    with col5:
        score_val = (
            str(patient.last_evaluation_score)
            if patient.last_evaluation_score is not None
            else 'Pendiente'
        )
        st.metric('Último NEWS2', score_val)

    # Resumen de última medición si está disponible
    latest_meas_html = ""
    if latest_measurement is not None:
        o2_str = "Sí" if latest_measurement.supplemental_oxygen else "No"
        latest_meas_html = (
            f"<p style='margin:6px 0 0 0; font-size:0.88rem; color:#cbd5e1;'>"
            f"<strong>📊 Última Medición ({format_datetime(latest_measurement.recorded_at)}):</strong> "
            f"FR: <code>{latest_measurement.respiratory_rate if latest_measurement.respiratory_rate is not None else 'N/D'} rpm</code> &bull; "
            f"SpO2: <code>{latest_measurement.oxygen_saturation if latest_measurement.oxygen_saturation is not None else 'N/D'}%</code> (O2: {o2_str}) &bull; "
            f"PAS: <code>{latest_measurement.systolic_blood_pressure if latest_measurement.systolic_blood_pressure is not None else 'N/D'} mmHg</code> &bull; "
            f"FC: <code>{latest_measurement.heart_rate if latest_measurement.heart_rate is not None else 'N/D'} lpm</code> &bull; "
            f"Temp: <code>{latest_measurement.temperature if latest_measurement.temperature is not None else 'N/D'} °C</code> &bull; "
            f"AVPU: <code>{latest_measurement.consciousness_status or 'N/D'}</code>"
            f"</p>"
        )

    # Bloque de información clínica descriptiva
    with st.container():
        st.markdown(
            f"""
            <div style="background-color:rgba(28, 131, 225, 0.08); border-left: 4px solid #38bdf8; padding: 12px 16px; border-radius: 6px; margin: 12px 0;">
                <p style="margin:0 0 6px 0;"><strong>🩺 Síntomas Reportados:</strong> {patient.symptoms or '<em>Sin síntomas descritos al ingreso</em>'}</p>
                <p style="margin:0;"><strong>📋 Diagnóstico Inicial / Sospecha:</strong> {patient.initial_diagnosis or '<em>Pendiente de valoración clínica</em>'}</p>
                {latest_meas_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.caption(
        f'Hora de Ingreso: {format_datetime(patient.arrival_at)} | '
        f'Última Evaluación NEWS2: {format_datetime(patient.last_evaluation_at)}'
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
            line=dict(color='#38bdf8', width=2),
            marker=dict(size=7),
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
            line=dict(color='#10b981', width=2),
            marker=dict(size=7),
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
            line=dict(color='#f59e0b', width=2),
            marker=dict(size=7),
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
            line=dict(color='#ec4899', width=2),
            marker=dict(size=7),
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
            line=dict(color='#a855f7', width=2),
            marker=dict(size=7),
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
            line=dict(color='#14b8a6', width=2),
            marker=dict(size=7),
        ),
        row=3,
        col=2,
    )

    apply_dark_glass_theme(
        fig,
        height=720,
        title='Tendencia Temporal de Parámetros Fisiológicos',
    )
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)


def render_evaluation_result(evaluation: Evaluation) -> None:
    """Muestra el resultado detallado de una evaluación NEWS2: primero puntuación y desglose, luego explicación.

    Args:
        evaluation: Objeto Evaluation a presentar.
    """
    risk_info = NEWS2_RISK_LEVELS.get(evaluation.risk_level or '', {})
    risk_label = risk_info.get(
        'label', evaluation.risk_level or 'Evaluación incompleta'
    )
    clinical_rec = risk_info.get('description', '')

    c1, c2, c3 = st.columns(3)
    c1.metric(
        'Puntaje Agregado NEWS2',
        str(evaluation.score) if evaluation.score is not None else 'Incompleto',
    )
    c2.metric('Estratificación de Riesgo', risk_label)
    comp_label = (
        'Completo (7/7 parámetros)'
        if evaluation.completeness_status == 'completo'
        else 'Datos Parciales / Incompleto'
    )
    c3.metric('Completitud de Medición', comp_label)

    # 1. Mostrar desglose de puntajes por parámetro
    param_scores = evaluation.parameter_scores
    if param_scores:
        if isinstance(param_scores, str):
            try:
                param_scores = json.loads(param_scores)
            except Exception:
                param_scores = {}

        if isinstance(param_scores, dict) and param_scores:
            st.markdown('##### Desglose de Puntuación por Parámetro Fisiológico')
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
                    'Puntos NEWS2 (0 a 3)': pts,
                    'Estado del Parámetro': (
                        '🔴 Gatillo extremo (3 pts)'
                        if pts == 3
                        else ('🟠 Alteración moderada (2 pts)' if pts == 2 else ('🟡 Desviación leve (1 pto)' if pts == 1 else '🟢 Rango normal (0 pts)'))
                    ),
                })
            df_breakdown = pd.DataFrame(breakdown_list)
            st.dataframe(df_breakdown, use_container_width=True, hide_index=True)

    # 2. Explicar el resultado y la respuesta recomendada
    st.markdown('##### Explicación del Resultado Clínico')
    st.markdown(f'**Síntesis de Evaluación:** {evaluation.explanation}')
    if clinical_rec:
        st.info(f'**Orientación según Protocolo RCP NEWS2:** {clinical_rec}', icon='ℹ️')


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
            'Puntaje NEWS2': e.score if e.score is not None else 0,
            'Riesgo': NEWS2_RISK_LEVELS.get(e.risk_level or '', {}).get(
                'label', e.risk_level or 'Incompleto'
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
        color_discrete_sequence=['#38bdf8'],
    )
    apply_dark_glass_theme(fig, height=300, title='Evolución Temporal de la Puntuación NEWS2')
    st.plotly_chart(fig, use_container_width=True)

    # Tabla histórica
    table_rows = []
    for e in reversed(sorted_evals):
        risk_name = NEWS2_RISK_LEVELS.get(e.risk_level or '', {}).get(
            'label', e.risk_level or 'Incompleto'
        )
        table_rows.append({
            'Fecha / Hora': format_datetime(e.evaluated_at),
            'Puntaje': e.score if e.score is not None else 'Incompleto',
            'Nivel de Riesgo': risk_name,
            'Completitud': e.completeness_status,
            'Detalle': e.explanation,
        })
    df_table = pd.DataFrame(table_rows)
    st.dataframe(df_table, use_container_width=True, hide_index=True)


def render_alert_panel(
    alerts: List[Alert], on_acknowledge: Optional[Callable[[int], bool]] = None
) -> None:
    """Muestra el panel de alertas diferenciando riesgo elevado, cambios fisiológicos y avisos informativos.

    Args:
        alerts: Lista de objetos Alert.
        on_acknowledge: Función de retrollamada para reconocer alertas (recibe alert_id).
    """
    if not alerts:
        st.success('No existen alertas ni notificaciones registradas para este contexto.')
        return

    review_alerts = [
        a for a in alerts if ALERT_TYPES.get(a.alert_type, {}).get('requires_review', True)
    ]
    info_notifications = [
        a for a in alerts if not ALERT_TYPES.get(a.alert_type, {}).get('requires_review', True)
    ]

    pending_review = [a for a in review_alerts if a.status == ALERT_STATUS_PENDING]
    ack_review = [a for a in review_alerts if a.status != ALERT_STATUS_PENDING]

    tab_pending, tab_ack, tab_info = st.tabs([
        f'🚨 Alertas de Riesgo y Cambios Pendientes ({len(pending_review)})',
        f'✅ Alertas Reconocidas ({len(ack_review)})',
        f'ℹ️ Notificaciones Informativas ({len(info_notifications)})',
    ])

    with tab_pending:
        if not pending_review:
            st.success('No hay alertas de riesgo clínico ni cambios fisiológicos pendientes de revisión.')
        else:
            for alert in pending_review:
                type_info = ALERT_TYPES.get(alert.alert_type, {})
                type_name = type_info.get('label', alert.alert_type)
                category = type_info.get('category', 'riesgo_clinico')
                if category == 'cambio_fisiologico' or alert.alert_type == 'value_change':
                    badge_icon = '📉'
                    badge_tag = 'Cambio Fisiológico'
                elif category == 'operativa':
                    badge_icon = '⏱️'
                    badge_tag = 'Alerta Operativa'
                else:
                    badge_icon = '🚨'
                    badge_tag = 'Alerta de Riesgo Clínico'

                with st.expander(
                    f'{badge_icon} [{badge_tag} — {type_name}] Paciente #{alert.patient_id} • '
                    f'{format_datetime(alert.created_at)}',
                    expanded=True,
                ):
                    st.markdown(f'**Detalle del aviso:** {alert.reason}')
                    st.caption(
                        f'Categoría: **{badge_tag}** | Regla: `{alert.rule_name}` | Generada: {format_datetime(alert.created_at)}'
                    )

                    if alert.trigger_data:
                        trig = alert.trigger_data
                        if isinstance(trig, str):
                            try:
                                trig = json.loads(trig)
                            except Exception:
                                pass
                        with st.expander('Ver datos técnicos del disparador', expanded=False):
                            st.json(trig)

                    if on_acknowledge is not None and alert.id is not None:
                        btn_key = f'ack_alert_btn_{alert.id}'
                        if st.button(
                            f'✓ Reconocer Alerta #{alert.id}',
                            key=btn_key,
                        ):
                            success = on_acknowledge(alert.id)
                            if success:
                                st.success('Alerta reconocida exitosamente.')
                                st.rerun()
                            else:
                                st.error('No fue posible actualizar la alerta.')

    with tab_ack:
        if not ack_review:
            st.info('No hay alertas en el histórico de reconocidas.')
        else:
            for alert in ack_review:
                type_info = ALERT_TYPES.get(alert.alert_type, {})
                type_name = type_info.get('label', alert.alert_type)
                with st.expander(
                    f'✅ [{type_name}] Paciente #{alert.patient_id} • '
                    f'{format_datetime(alert.created_at)}',
                    expanded=False,
                ):
                    st.markdown(f'**Motivo:** {alert.reason}')
                    st.caption(
                        f'Regla: `{alert.rule_name}` | Reconocida: {format_datetime(alert.acknowledged_at)}'
                    )

    with tab_info:
        st.caption(
            'Las notificaciones informativas registran eventos de trazabilidad (como la captura de una nueva medición) '
            'y no constituyen alertas de riesgo clínico ni suman puntos en la cola de prioridad.'
        )
        if not info_notifications:
            st.info('No se registran notificaciones informativas.')
        else:
            info_rows = [
                {
                    'Fecha / Hora': format_datetime(a.created_at),
                    'Paciente ID': f'#{a.patient_id}',
                    'Tipo': ALERT_TYPES.get(a.alert_type, {}).get('label', a.alert_type),
                    'Descripción': a.reason,
                }
                for a in info_notifications
            ]
            st.dataframe(pd.DataFrame(info_rows), use_container_width=True, hide_index=True)


def render_queue_table(queue_data: List[Any]) -> None:
    """Renderiza la cola administrativa de atención en una tabla compacta con opción de detalle ampliado.

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
            triage_label = (
                tinfo.get('short_label', f"Nivel {p.triage_level}")
                if (p and p.triage_level)
                else 'Sin clasificar'
            )
            symptoms = p.symptoms if (p and p.symptoms) else 'Sin síntomas'
            initial_dx = p.initial_diagnosis if (p and p.initial_diagnosis) else 'Pendiente'

            eval_str = 'Sin evaluar'
            if item.last_evaluation is not None:
                if item.last_evaluation.completeness_status == 'incompleto' or item.last_evaluation.score is None:
                    eval_str = 'Incompleta'
                else:
                    r_lbl = NEWS2_RISK_LEVELS.get(item.last_evaluation.risk_level or '', {}).get(
                        'label', item.last_evaluation.risk_level or ''
                    )
                    eval_str = f"{item.last_evaluation.score} pts ({r_lbl})"

            reasons_str = (
                ' • '.join(item.reasons)
                if isinstance(item.reasons, list)
                else str(item.reasons)
            )
            normalized.append({
                'position': item.position,
                'patient_code': code,
                'patient_name': name,
                'triage_label': triage_label,
                'news2_display': eval_str,
                'symptoms': symptoms,
                'initial_diagnosis': initial_dx,
                'priority_score': round(item.priority_score, 1),
                'wait_time_minutes': item.wait_time_minutes,
                'wait_time_formatted': format_wait_time(item.wait_time_minutes),
                'pending_alerts': item.pending_alerts,
                'reasons_str': reasons_str,
            })
        elif isinstance(item, dict):
            pos = item.get('position', item.get('posicion', item.get('Posición', 0)))
            code = item.get('patient_code', item.get('codigo', item.get('Código', 'N/D')))
            name = item.get('patient_name', item.get('nombre', item.get('Nombre', 'N/D')))
            triage_label = item.get('triage_label', item.get('triaje', item.get('Triaje', 'Sin clasificar')))
            eval_str = item.get('news2_display', item.get('Última evaluación', 'N/D'))
            symptoms = item.get('symptoms', item.get('sintomas', item.get('Síntomas', 'Sin síntomas')))
            initial_dx = item.get('initial_diagnosis', item.get('diagnostico', item.get('Diagnóstico inicial', 'Pendiente')))
            score = round(
                float(item.get('priority_score', item.get('score', item.get('Puntuación prioridad', 0.0)))), 1
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
                ' • '.join(r_val) if isinstance(r_val, list) else str(r_val)
            )
            normalized.append({
                'position': pos,
                'patient_code': code,
                'patient_name': name,
                'triage_label': triage_label,
                'news2_display': eval_str,
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
            f"🔔 **Siguiente en Orden Administrativo (#1):** `{top_patient['patient_code']}` — **{top_patient['patient_name']}** | "
            f"Triaje: **{top_patient['triage_label']}** | "
            f"NEWS2: **{top_patient['news2_display']}** | "
            f"Puntaje Prioridad: **{top_patient['priority_score']} pts**",
            icon='🚨',
        )

    compact_rows = []
    full_rows = []
    for entry in normalized:
        alert_badge = (
            f"🚨 {entry['pending_alerts']}"
            if entry['pending_alerts'] > 0
            else '0'
        )
        compact_rows.append({
            'Posición': f"#{entry['position']}",
            'Código': entry['patient_code'],
            'Paciente': entry['patient_name'],
            'Triaje': entry['triage_label'],
            'Último NEWS2': entry['news2_display'],
            'Alertas Clínicas': alert_badge,
            'Espera': entry['wait_time_formatted'],
            'Prioridad (pts)': entry['priority_score'],
        })
        full_rows.append({
            'Posición': f"#{entry['position']}",
            'Código': entry['patient_code'],
            'Paciente': entry['patient_name'],
            'Triaje': entry['triage_label'],
            'Último NEWS2': entry['news2_display'],
            'Alertas Clínicas': alert_badge,
            'Espera': entry['wait_time_formatted'],
            'Prioridad (pts)': entry['priority_score'],
            'Síntomas': entry['symptoms'],
            'Diagnóstico Inicial': entry['initial_diagnosis'],
            'Factores de Priorización': entry['reasons_str'],
        })

    st.dataframe(pd.DataFrame(compact_rows), use_container_width=True, hide_index=True)
    with st.expander('📋 Ver tabla detallada con síntomas, diagnóstico inicial y factores completos', expanded=False):
        st.dataframe(pd.DataFrame(full_rows), use_container_width=True, hide_index=True)


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
        color_continuous_scale=['#06b6d4', '#38bdf8', '#f59e0b', '#ef4444'],
        title='Puntaje de Prioridad Administrativa por Paciente',
        text='Puntaje Prioridad',
    )
    fig.update_traces(textposition='outside')
    apply_dark_glass_theme(
        fig, height=380, title='Puntaje de Prioridad Administrativa por Paciente'
    )
    fig.update_layout(
        xaxis_title='Paciente en Espera',
        yaxis_title='Puntaje Compuesto',
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
    with st.expander('👥 Ver Perfiles Clínicos Predefinidos de la Simulación', expanded=False):
        st.markdown(
            'El sistema utiliza perfiles sintéticos con cuadros clínicos y evolución fisiológica controlada:'
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

    st.markdown('##### 📜 Registro Cronológico de Eventos de la Simulación')

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
            'Hora / Fecha Simulada': format_datetime(ev.event_at),
            'Tipo de Evento': ev.event_type.upper(),
            'Paciente ID': f'#{ev.patient_id}' if ev.patient_id else '-',
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
                entry.get('codigo', entry.get('Código', str(entry.get('patient_id', 'N/D')))),
            )
            pos = entry.get('position', entry.get('posicion', entry.get('Posición', 0)))
            score = entry.get('priority_score', entry.get('score', entry.get('Puntuación prioridad', 0.0)))
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
        title='Dinámica Temporal de Posiciones en Cola Administrativa (Simulación)',
        color_discrete_sequence=['#38bdf8', '#10b981', '#f59e0b', '#ec4899', '#a855f7'],
    )
    # Invertir eje Y para que la posición #1 esté arriba
    fig.update_yaxes(autorange='reversed', dtick=1)
    apply_dark_glass_theme(
        fig, height=400, title='Dinámica Temporal de Posiciones en Cola Administrativa (Simulación)'
    )
    fig.update_layout(
        xaxis_title='Paso Temporal de Simulación',
        yaxis_title='Posición en Cola (1 = Mayor Prioridad)',
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
        f"Escenario sintético ejecutado con éxito (ID de corrida: `{results.get('simulation_id', 'N/D')}`)"
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric('Pacientes Sintéticos', results.get('patients_created', 0))
    c2.metric('Mediciones Generadas', results.get('total_measurements', 0))
    c3.metric('Alertas Clínicas/Operativas', results.get('total_alerts', 0))
    c4.metric('Eventos de Bitácora', results.get('total_events', 0))

    st.markdown('---')

    # Visualización detallada de los pacientes creados en la simulación
    patients = results.get('patients', [])
    if patients:
        st.subheader('👥 Pacientes Sintéticos Incorporados en el Escenario')
        rows = []
        for p in patients:
            prof = p.get('profile', {})
            t_lvl = prof.get('triage_level')
            t_label = TRIAGE_LEVEL_LABELS.get(t_lvl, f'Nivel {t_lvl}') if 'TRIAGE_LEVEL_LABELS' in globals() else f'Nivel {t_lvl}'
            rows.append({
                'Código': p.get('code'),
                'Nombre del Paciente': prof.get('patient_name'),
                'Perfil Fisiológico': prof.get('name'),
                'Triaje Inicial': t_label,
                'Síntomas Reportados': prof.get('symptoms'),
                'Diagnóstico Inicial': prof.get('initial_diagnosis'),
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.info(
            '💡 **Trazabilidad:** Todos estos pacientes quedan marcados con la etiqueta **🔬 Simulado**. '
            'Puede excluirlos en cualquier momento de la vista de **👥 Pacientes** o de la **📈 Cola de Atención** '
            'mediante el filtro correspondiente, o limpiarlos con el botón **🗑 Limpiar Datos de Simulación**.'
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
    st.subheader('📖 Especificación Técnica NEWS2 (Royal College of Physicians, 2017)')
    st.markdown("""
    La escala **NEWS2** (*National Early Warning Score 2*) es un estándar clínico internacional diseñado 
    para cuantificar el grado de alteración fisiológica aguda en pacientes adultos. Evalúa **7 parámetros fisiológicos** 
    y asigna entre **0 y 3 puntos** a cada uno según su desviación respecto al rango normal.
    """)

    parameters_table = [
        {
            'Parámetro Fisiológico': 'Frecuencia Respiratoria (rpm)',
            '3 Pts (Extremo Bajo)': '≤ 8',
            '2 Pts (Bajo)': '—',
            '1 Pto (Leve Bajo)': '9 – 11',
            '0 Pts (Rango Normal)': '12 – 20',
            '1 Pto (Leve Alto)': '—',
            '2 Pts (Alto)': '21 – 24',
            '3 Pts (Extremo Alto)': '≥ 25',
        },
        {
            'Parámetro Fisiológico': 'Saturación SpO2 — Escala 1 (%)',
            '3 Pts (Extremo Bajo)': '≤ 91',
            '2 Pts (Bajo)': '92 – 93',
            '1 Pto (Leve Bajo)': '94 – 95',
            '0 Pts (Rango Normal)': '≥ 96',
            '1 Pto (Leve Alto)': '—',
            '2 Pts (Alto)': '—',
            '3 Pts (Extremo Alto)': '—',
        },
        {
            'Parámetro Fisiológico': 'Saturación SpO2 — Escala 2 (%)',
            '3 Pts (Extremo Bajo)': '≤ 83',
            '2 Pts (Bajo)': '84 – 85',
            '1 Pto (Leve Bajo)': '86 – 87',
            '0 Pts (Rango Normal)': '88 – 92 (u ≥88 aire)',
            '1 Pto (Leve Alto)': '93 – 94 (con O2)',
            '2 Pts (Alto)': '95 – 96 (con O2)',
            '3 Pts (Extremo Alto)': '≥ 97 (con O2)',
        },
        {
            'Parámetro Fisiológico': 'Oxígeno Suplementario',
            '3 Pts (Extremo Bajo)': '—',
            '2 Pts (Bajo)': 'Sí (+2 pts)',
            '1 Pto (Leve Bajo)': '—',
            '0 Pts (Rango Normal)': 'Aire ambiente (0 pts)',
            '1 Pto (Leve Alto)': '—',
            '2 Pts (Alto)': '—',
            '3 Pts (Extremo Alto)': '—',
        },
        {
            'Parámetro Fisiológico': 'Presión Arterial Sistólica (mmHg)',
            '3 Pts (Extremo Bajo)': '≤ 90',
            '2 Pts (Bajo)': '91 – 100',
            '1 Pto (Leve Bajo)': '101 – 110',
            '0 Pts (Rango Normal)': '111 – 219',
            '1 Pto (Leve Alto)': '—',
            '2 Pts (Alto)': '—',
            '3 Pts (Extremo Alto)': '≥ 220',
        },
        {
            'Parámetro Fisiológico': 'Frecuencia Cardíaca (lpm)',
            '3 Pts (Extremo Bajo)': '≤ 40',
            '2 Pts (Bajo)': '—',
            '1 Pto (Leve Bajo)': '41 – 50',
            '0 Pts (Rango Normal)': '51 – 90',
            '1 Pto (Leve Alto)': '91 – 110',
            '2 Pts (Alto)': '111 – 130',
            '3 Pts (Extremo Alto)': '≥ 131',
        },
        {
            'Parámetro Fisiológico': 'Nivel de Conciencia (AVPU)',
            '3 Pts (Extremo Bajo)': '—',
            '2 Pts (Bajo)': '—',
            '1 Pto (Leve Bajo)': '—',
            '0 Pts (Rango Normal)': 'Alerta (A)',
            '1 Pto (Leve Alto)': '—',
            '2 Pts (Alto)': '—',
            '3 Pts (Extremo Alto)': 'V, P o U',
        },
        {
            'Parámetro Fisiológico': 'Temperatura Corporal (°C)',
            '3 Pts (Extremo Bajo)': '≤ 35.0',
            '2 Pts (Bajo)': '—',
            '1 Pto (Leve Bajo)': '35.1 – 36.0',
            '0 Pts (Rango Normal)': '36.1 – 38.0',
            '1 Pto (Leve Alto)': '38.1 – 39.0',
            '2 Pts (Alto)': '≥ 39.1',
            '3 Pts (Extremo Alto)': '—',
        },
    ]

    st.markdown('##### Matriz Oficial de Puntuación Fisiológica NEWS2')
    st.dataframe(
        pd.DataFrame(parameters_table), use_container_width=True, hide_index=True
    )

    st.markdown('##### Estratificación de Riesgo Clínico y Umbrales de Respuesta')
    risk_thresholds = [
        {
            'Puntuación Agregada': '0 a 4 puntos (sin parámetros en 3)',
            'Nivel de Riesgo': 'Bajo (low)',
            'Respuesta Clínica Estándar Recomendada': (
                'Monitoreo clínico rutinario por enfermería en sala de espera u observación.'
            ),
        },
        {
            'Puntuación Agregada': '1 a 4 puntos con al menos un parámetro = 3',
            'Nivel de Riesgo': 'Bajo-Medio / Gatillo Rojo Individual (low_medium)',
            'Respuesta Clínica Estándar Recomendada': (
                'Revisión urgente por profesional médico para evaluar el parámetro fisiológico extremo.'
            ),
        },
        {
            'Puntuación Agregada': '5 a 6 puntos',
            'Nivel de Riesgo': 'Medio (medium)',
            'Respuesta Clínica Estándar Recomendada': (
                'Evaluación médica urgente y aumento de la frecuencia de monitoreo clínico.'
            ),
        },
        {
            'Puntuación Agregada': '7 o más puntos',
            'Nivel de Riesgo': 'Alto (high)',
            'Respuesta Clínica Estándar Recomendada': (
                'Valoración médica de emergencia inmediata y consideración de traslado a área crítica.'
            ),
        },
    ]
    st.dataframe(
        pd.DataFrame(risk_thresholds), use_container_width=True, hide_index=True
    )

    st.caption(
        "*Referencia Formal:* Royal College of Physicians. *National Early Warning Score (NEWS) 2: "
        "Standardising the assessment of acute-illness severity in the NHS*. Updated report of a working party. "
        "London: RCP, 2017."
    )


def render_methodology_page() -> None:
    """Renderiza los principios metodológicos, las reglas administrativas de cola y las limitaciones del prototipo."""
    st.subheader('🏛️ Fundamentos Metodológicos y Separación Conceptual')
    st.markdown(METHODOLOGY_TEXT)

    st.markdown('---')
    st.subheader('⚖️ Factores de Ponderación de la Cola Administrativa')
    st.markdown("""
    La cola de atención administrativa combina la clasificación de triaje registrada al ingreso, el puntaje NEWS2,
    las alertas clínicas/operativas pendientes y el tiempo de espera acumulado (con un tope máximo de **36 puntos**
    equivalente a 6 horas para impedir que esperas antiguas desplacen a pacientes con riesgo agudo elevado):
    """)

    formatted_rules = [
        {
            'Identificador': r.get('name', ''),
            'Descripción del Factor': r.get('description', ''),
            'Peso de Referencia (pts)': r.get('weight', 0),
        }
        for r in PRIORITY_RULES
    ]
    st.dataframe(pd.DataFrame(formatted_rules), use_container_width=True, hide_index=True)

    st.markdown('---')
    st.subheader('⚠️ Limitaciones Formales del Prototipo Académico')
    st.markdown("""
    - **No apto para uso asistencial real:** Este software es un prototipo académico y carece de certificación como dispositivo médico.
    - **Independencia del Triaje Normativo:** Las categorías de Triaje I a V no son calculadas automáticamente por el algoritmo; se registran como dato de admisión o quedan explícitamente pendientes de verificación.
    - **NEWS2 mide deterioro fisiológico agudo:** No reemplaza el diagnóstico diferencial ni descarta patologías graves con signos vitales inicialmente conservados.
    - **Ordenamiento administrativo sugerido:** La posición en la cola es un apoyo heurístico explicable y nunca sustituye el criterio del personal de salud.
    - **Datos estrictamente ficticios:** Todos los pacientes y escenarios corresponden a casos sintéticos o académicos.
    """)
