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
        padding: 20px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        height: 100%;
    }
    .glass-card:hover {
        border-color: var(--border-glass-glow);
        box-shadow: 0 12px 32px rgba(0, 0, 0, 0.4), 0 0 20px rgba(56, 189, 248, 0.12);
        transform: translateY(-2px);
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


def render_top_header() -> None:
    """Renderiza la cabecera superior moderna con título y perfil de usuario activo."""
    st.markdown(
        f"""
        <div class="top-nav-header">
            <div class="header-left">
                <div class="header-left-title">
                    <span>🏥 {APP_NAME} - Sistema de Priorización Dinámica en Urgencias</span>
                </div>
                <div class="header-left-subtitle">
                    Equipo de Desarrollo: <strong style="color:#38bdf8;">{TEAM_NAME}</strong>
                </div>
            </div>
            <div class="header-right-user">
                <div class="user-profile-badge">
                    <img src="https://images.unsplash.com/photo-1622253692010-333f2da6031d?auto=format&fit=crop&w=100&q=80" class="user-avatar-img" alt="Avatar Dr. Silva" />
                    <span class="user-name-text">Dr. A. Silva</span>
                    <span style="font-size:0.7rem; color:#94a3b8;">▼</span>
                </div>
                <div class="header-pill-btn">Fork</div>
                <div class="notification-bell">
                    🔔<span class="bell-badge-pill">1</span>
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
    """Genera el gráfico interactivo de red fisiológica y triaje con estética Dark Glass."""
    nodes = [
        {"id": "NEWS2", "label": "Motor NEWS2", "x": 0.0, "y": 0.0, "color": "#f59e0b", "size": 22, "type": "Hub Central"},
        {"id": "SpO2", "label": "SpO2 (98%)", "x": -0.6, "y": 0.55, "color": "#06b6d4", "size": 15, "type": "Signo Vital"},
        {"id": "FC", "label": "FC (76 lpm)", "x": -0.75, "y": 0.05, "color": "#06b6d4", "size": 15, "type": "Signo Vital"},
        {"id": "FR", "label": "FR (16 rpm)", "x": -0.5, "y": -0.55, "color": "#06b6d4", "size": 15, "type": "Signo Vital"},
        {"id": "TA", "label": "TA (120/80)", "x": 0.1, "y": -0.65, "color": "#06b6d4", "size": 15, "type": "Signo Vital"},
        {"id": "Temp", "label": "Temp (36.8°C)", "x": 0.55, "y": -0.45, "color": "#06b6d4", "size": 15, "type": "Signo Vital"},
        {"id": "AVPU", "label": "AVPU (Alerta)", "x": 0.2, "y": 0.65, "color": "#06b6d4", "size": 15, "type": "Signo Vital"},
        {"id": "Triaje1", "label": "Triaje I", "x": 0.72, "y": 0.5, "color": "#ef4444", "size": 17, "type": "Reanimación"},
        {"id": "Triaje2", "label": "Triaje II", "x": 0.82, "y": 0.12, "color": "#f97316", "size": 17, "type": "Emergencia"},
        {"id": "Triaje3", "label": "Triaje III", "x": 0.72, "y": -0.22, "color": "#eab308", "size": 17, "type": "Urgencia"},
        {"id": "Prioridad", "label": "Prioridad Cola", "x": 0.45, "y": 0.05, "color": "#8b5cf6", "size": 19, "type": "Cola Dinámica"},
    ]

    edges = [
        ("SpO2", "NEWS2"), ("FC", "NEWS2"), ("FR", "NEWS2"), ("TA", "NEWS2"),
        ("Temp", "NEWS2"), ("AVPU", "NEWS2"),
        ("NEWS2", "Prioridad"),
        ("NEWS2", "Triaje1"), ("NEWS2", "Triaje2"), ("NEWS2", "Triaje3"),
        ("Triaje1", "Prioridad"), ("Triaje2", "Prioridad"), ("Triaje3", "Prioridad"),
        ("SpO2", "FC"), ("FR", "SpO2"), ("Temp", "TA"), ("AVPU", "SpO2"),
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
    node_text = [f"<b>{n['label']}</b><br>Nivel: {n['type']}" for n in nodes]

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
    apply_dark_glass_theme(fig, height=330, title="Red Fisiológica y Dinámica de Triaje")
    fig.update_layout(
        showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        margin=dict(l=10, r=10, t=35, b=10),
    )
    return fig


def create_home_triage_bar_chart() -> go.Figure:
    """Genera el gráfico de barras apiladas de priorización en tiempo real por niveles de triaje."""
    categories = ['I', 'II', 'III', 'IV', 'V']
    en_espera = [2, 7, 11, 15, 8]
    en_atencion = [1, 4, 5, 3, 2]
    alertas_activas = [2, 3, 2, 0, 0]

    fig = go.Figure(data=[
        go.Bar(name='En Espera', x=categories, y=en_espera, marker_color='#06b6d4'),
        go.Bar(name='En Atención', x=categories, y=en_atencion, marker_color='#f59e0b'),
        go.Bar(name='Alertas Críticas', x=categories, y=alertas_activas, marker_color='#ef4444'),
    ])

    fig.update_layout(
        barmode='stack',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=10, color="#94a3b8"),
        ),
    )
    apply_dark_glass_theme(fig, height=190, title="Priorización en Tiempo Real")
    fig.update_layout(
        xaxis_title="Nivel Triaje",
        yaxis_title="Pacientes",
        margin=dict(l=25, r=20, t=35, b=25),
    )
    return fig


def render_disclaimer() -> None:
    """Muestra el descargo de responsabilidad académica en un cuadro de advertencia visible."""
    st.warning(DISCLAIMER_TEXT, icon='⚠️')


def render_home_page() -> None:
    """Renderiza la página principal con diseño Dark Glassmorphism idéntico al mockup."""
    # Contenedor Glass Principal (Hero Container con 3 columnas)
    st.markdown('<div class="glass-hero-container">', unsafe_allow_html=True)

    col_left, col_center, col_right = st.columns([1.5, 1.4, 1.1])

    with col_left:
        st.markdown(
            """
            <h3 style="font-weight:700; color:#f8fafc; margin-top:0; margin-bottom:12px;">
                Prototipo Académico de Priorización Dinámica en Urgencias
            </h3>
            <p style="color:#94a3b8; font-size:0.9rem; line-height:1.55; margin-bottom:16px;">
                Este sistema es un <strong>prototipo de investigación y desarrollo académico</strong> que demuestra cómo 
                una aplicación analítica moderna puede apoyar la gestión administrativa y la priorización transparente de pacientes 
                en la cola de espera de un servicio de urgencias simulado.
            </p>
            <div style="font-weight:600; color:#cbd5e1; margin-bottom:10px; font-size:0.92rem;">
                Funcionalidades Principales:
            </div>
            <ul style="list-style:none; padding-left:0; margin:0; font-size:0.86rem; color:#94a3b8; line-height:1.65;">
                <li style="margin-bottom:6px;"><span style="color:#38bdf8;">📋</span> <strong style="color:#e2e8f0;">Registro de Pacientes Ficticios:</strong> Ingreso ágil y trazabilidad con códigos únicos.</li>
                <li style="margin-bottom:6px;"><span style="color:#10b981;">📊</span> <strong style="color:#e2e8f0;">Monitoreo de Signos Vitales:</strong> Captura periódica de parámetros fisiológicos.</li>
                <li style="margin-bottom:6px;"><span style="color:#f59e0b;">⚡</span> <strong style="color:#e2e8f0;">Evaluación Estandarizada NEWS2:</strong> Cálculo riguroso según la especificación del Royal College of Physicians (2017).</li>
                <li style="margin-bottom:6px;"><span style="color:#ef4444;">🔔</span> <strong style="color:#e2e8f0;">Motor de Alertas Configurable:</strong> Detección de deterioro fisiológico, datos incompletos y tiempos prolongados.</li>
                <li style="margin-bottom:6px;"><span style="color:#a855f7;">📈</span> <strong style="color:#e2e8f0;">Cola Administrativa Dinámica:</strong> Ordenamiento explicable con desglose de factores de prioridad.</li>
                <li style="margin-bottom:6px;"><span style="color:#06b6d4;">🔬</span> <strong style="color:#e2e8f0;">Simulación de Escenarios:</strong> Pacientes sintéticos con perfiles clínicos y evolución temporal.</li>
            </ul>
            """,
            unsafe_allow_html=True,
        )

    with col_center:
        fig_network = create_home_network_chart()
        st.plotly_chart(
            fig_network, use_container_width=True, config={'displayModeBar': False}
        )

    with col_right:
        fig_bar = create_home_triage_bar_chart()
        st.plotly_chart(
            fig_bar, use_container_width=True, config={'displayModeBar': False}
        )

        st.markdown(
            f"""
            <div class="glass-card" style="padding:14px; margin-top:8px;">
                <div style="font-weight:700; color:#38bdf8; font-size:0.88rem; margin-bottom:6px; display:flex; align-items:center; gap:6px;">
                    ℹ️ Ficha Técnica del Prototipo
                </div>
                <div style="font-size:0.8rem; color:#94a3b8; line-height:1.5;">
                    <div>• <strong>Versión:</strong> <code style="color:#38bdf8;">{APP_VERSION}</code></div>
                    <div>• <strong>Entorno:</strong> Simulación Controlada</div>
                    <div>• <strong>Persistencia:</strong> SQLite Transaccional</div>
                    <div>• <strong>Escala de Deterioro:</strong> NEWS2 (2017)</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)

    # Fila de 3 Tarjetas de Acceso Rápido / Shortcuts
    sc1, sc2, sc3 = st.columns(3)

    with sc1:
        st.markdown(
            """
            <div class="glass-action-card">
                <div>
                    <div class="action-card-header">
                        <div class="action-icon-wrap">👥</div>
                        <div>
                            <div class="action-title">Patient Registration</div>
                            <div style="font-size:0.78rem; color:#94a3b8;">Admisión y Gestión Clínica</div>
                        </div>
                    </div>
                    <ul class="action-list">
                        <li>Registro rápido de pacientes ficticios</li>
                        <li>Asignación de código y tiempo de espera</li>
                        <li>Captura de síntomas y diagnóstico inicial</li>
                    </ul>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            "➕ Abrir Registro de Pacientes",
            key="btn_quick_register",
            use_container_width=True,
        ):
            st.session_state["current_page"] = "➕ Registrar Paciente"
            st.rerun()

    with sc2:
        st.markdown(
            """
            <div class="glass-action-card">
                <div>
                    <div class="action-card-header">
                        <div class="action-icon-wrap">🩺</div>
                        <div>
                            <div class="action-title">Vital Signs Monitor</div>
                            <div style="font-size:0.78rem; color:#94a3b8;">Monitoreo Fisiológico Continuo</div>
                        </div>
                    </div>
                    <ul class="action-list">
                        <li>Registro de 7 signos vitales estándar</li>
                        <li>Gráficos multivariables de tendencias</li>
                        <li>Histórico temporal por paciente</li>
                    </ul>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            "📊 Abrir Registro de Medición",
            key="btn_quick_vitals",
            use_container_width=True,
        ):
            st.session_state["current_page"] = "📊 Registrar Medición"
            st.rerun()

    with sc3:
        st.markdown(
            """
            <div class="glass-action-card">
                <div>
                    <div class="action-card-header">
                        <div class="action-icon-wrap">⚡</div>
                        <div>
                            <div class="action-title">New EWS2 Evaluation</div>
                            <div style="font-size:0.78rem; color:#94a3b8;">Estratificación y Alertas</div>
                        </div>
                    </div>
                    <ul class="action-list">
                        <li>Cálculo automatizado de puntaje NEWS2</li>
                        <li>Estratificación de riesgo clínico (RCP)</li>
                        <li>Reconocimiento y gestión de alertas</li>
                    </ul>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(
            "⚡ Ir a Evaluaciones y Alertas",
            key="btn_quick_evals",
            use_container_width=True,
        ):
            st.session_state["current_page"] = "⚡ Evaluación y Alertas"
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
                <a href="#" style="color:#94a3b8; text-decoration:none; font-weight:500;">⚖️ Aviso Ético y Regulatorio</a>
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
        color_discrete_sequence=['#38bdf8'],
    )
    apply_dark_glass_theme(fig, height=320, title='Evolución Temporal de la Puntuación NEWS2')
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
        color_discrete_sequence=['#38bdf8', '#10b981', '#f59e0b', '#ec4899', '#a855f7'],
    )
    # Invertir eje Y para que la posición #1 esté arriba
    fig.update_yaxes(autorange='reversed', dtick=1)
    apply_dark_glass_theme(
        fig, height=420, title='Dinámica Temporal de Posiciones en Cola Administrativa'
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
