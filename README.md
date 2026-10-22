# IA Médica Asistencial: Sistema de Triaje y Priorización Dinámica

**Prototipo Académico y Experimental de Soporte en Urgencias**  
**Desarrollado por el equipo TechMinds**

---

> [!WARNING]
> ### DESCARGO DE RESPONSABILIDAD MÉDICA Y ACADÉMICA
> **ESTE SOFTWARE ES EXCLUSIVAMENTE UN PROTOTIPO ACADÉMICO Y DOCENTE.**  
> Todos los datos de pacientes, constantes vitales y registros clínicos contenidos o generados por esta aplicación son **estrictamente ficticios y sintéticos**.  
> **NO UTILIZAR PARA LA TOMA DE DECISIONES CLÍNICAS REALES, ATENCIÓN DIRECTA DE PACIENTES NI ASIGNACIÓN NORMATIVA DE TRIAJE MÉDICO.**  
> El sistema no cuenta con certificación como dispositivo médico o software clínico (SaMD) ante autoridades regulatorias (como FDA, CE o INVIMA).

---

## 📖 Descripción del Proyecto

**IA Médica Asistencial** es una plataforma interactiva y modular desarrollada por **TechMinds** para simular y analizar los flujos de atención y detección temprana de deterioro en servicios de urgencias hospitalarias.

El proyecto integra:
1. **Detección fisiológica temprana**: Cálculo de **NEWS2 (National Early Warning Score 2)** según las tablas del *Royal College of Physicians (2017)*, con las limitaciones indicadas en la sección «Limitaciones» (p. ej., la escala de conciencia es AVPU: no registra «nueva confusión»). No ha sido validado clínicamente.
2. **Motor reactivo de alertas**: Reglas configurables que detectan nuevas mediciones, cambios entre mediciones sucesivas, evaluaciones incompletas, puntuaciones elevadas, esperas prolongadas y alertas sin reconocer.
3. **Priorización administrativa dinámica**: Orden administrativo **simulado** de la cola de espera según reglas explícitas (alertas pendientes, puntuación NEWS2 y tiempo de espera), con la justificación de la posición de cada paciente. No sustituye el triaje ni el criterio clínico.
4. **Simulador reproducible de urgencias**: Genera pacientes ficticios con perfiles sintéticos y llegadas escalonadas; la misma semilla produce las mismas mediciones y puntuaciones.

---

## ⚙️ Requisitos Previos

- **Python 3.9** o superior (recomendado Python 3.10 o 3.11).
- Gestor de paquetes **pip**.
- Sistema operativo: **Windows 10/11**, Linux o macOS.

---

## 🚀 Instalación (Windows)

Abra un terminal de comandos (`cmd.exe` o `PowerShell`) y siga los siguientes pasos:

1. **Clonar o ubicarse en la carpeta raíz del proyecto:**
   ```cmd
   cd "C:\Users\Ana sofia\.gemini\antigravity\worktrees\splendid-faraday\ia_medica_asistencial_triage"
   ```

2. **Crear el entorno virtual de Python:**
   ```cmd
   python -m venv venv
   ```

3. **Activar el entorno virtual:**
   ```cmd
   venv\Scripts\activate
   ```

4. **Instalar las dependencias oficiales:**
   ```cmd
   pip install -r requirements.txt
   ```

---

## 🖥️ Ejecución de la Aplicación

Con el entorno virtual activado, inicie la interfaz web interactiva con Streamlit:

```cmd
streamlit run app.py
```

La aplicación se abrirá automáticamente en su navegador web predeterminado en `http://localhost:8501`.

---

## 🧪 Ejecución de Pruebas Automatizadas

El proyecto cuenta con un conjunto de pruebas unitarias y de integración desarrolladas con **pytest**:

```cmd
pytest tests/ -v
```

Para verificar cobertura de código (si tiene configurado pytest-cov):
```cmd
pytest --cov=. tests/
```

---

## 📁 Estructura del Proyecto

```
ia_medica_asistencial_triage/
│
├── app.py                  # Punto de entrada de la aplicación Streamlit y enrutamiento
├── config.py               # Constantes del sistema, parámetros por defecto y textos
├── models.py               # Clases de dominio y dataclasses (Patient, Measurement, Alert, etc.)
├── database.py             # Capa de persistencia SQLite y migraciones de esquema
├── validation.py           # Reglas de validación rigurosas y sanitización de entradas
├── patient_service.py      # Lógica de negocio de pacientes y registro de signos vitales
├── clinical_scoring.py     # Cálculo estricto de NEWS2 y variaciones fisiológicas
├── alert_engine.py         # Motor de reglas reactivas y ciclo de vida de alertas
├── prioritization.py       # Algoritmo de priorización dinámica y explicabilidad de cola
├── simulation.py           # Motor de simulación estocástica de urgencias
├── dashboard.py            # Componentes visuales reutilizables, gráficos Plotly y tablas
├── requirements.txt        # Dependencias esenciales del proyecto
├── .gitignore              # Patrones de exclusión para Git
├── README.md               # Documentación general y técnica del proyecto
└── tests/                  # Suite de pruebas unitarias y validación clínica
```

### Descripción de Módulos

- **[app.py](file:///C:/Users/Ana%20sofia/.gemini/antigravity/worktrees/splendid-faraday/ia_medica_asistencial_triage/app.py)**: Orquestador visual con navegación lateral, manejo de sesión y coordinación de servicios.
- **`config.py`**: Parámetros globales del sistema, rangos de referencia fisiológicos, constantes de bases de datos y textos informativos.
- **`models.py`**: Modelos de datos desacoplados con tipado estricto mediante `@dataclass` (`Patient`, `Measurement`, `Evaluation`, `Alert`, `QueueEntry`, `SimulationEvent`, `SimulationConfig`).
- **`database.py`**: Gestión de conexiones SQLite seguras mediante consultas parametrizadas (`?`), creación automática de tablas e índices de rendimiento.
- **`validation.py`**: Verificación de integridad fisiológica y administrativa, límites válidos de signos vitales y sanitización contra inyecciones.
- **`patient_service.py`**: Servicios para la admisión de pacientes, asignación de código estándar (`PAC-XXXXXX`), captura de constantes y cálculo de tiempos de espera.
- **`clinical_scoring.py`**: Implementación determinista de las tablas NEWS2 publicadas por el RCP, diferenciando Escala 1 y Escala 2 de saturación de oxígeno.
- **`alert_engine.py`**: Motor reactivo configurable que evalúa signos vitales, detecta descompensación y gestiona la resolución y acuse de recibo de alertas.
- **`prioritization.py`**: Ordenamiento dinámico de la fila de atención que equilibra gravedad clínica (NEWS2), presencia de alertas no atendidas y equidad temporal (espera en minutos).
- **`simulation.py`**: Generación de escenarios de flujo continuo de pacientes sintéticos y evolución hemodinámica en el tiempo.
- **`dashboard.py`**: Funciones de interfaz para métricas, gráficos temporales de constantes vitales, evolución de la cola y cuadros explicativos.

---

## ✨ Resumen de Funcionalidades

### Funcionalidades Implementadas y Operativas ✅
- **Gestión Clínica y Humanizada de Pacientes**: Admisión con nombre completo (ficticio), código unificado (`PAC-XXXXXX`), registro temporal exacto de llegada (ISO 8601), cálculo dinámico del tiempo de espera en vivo, registro estructurado de síntomas, diagnóstico inicial o sospecha clínica, y control de estados administrativos (`en_espera`, `en_atencion`, `atendido`, `alta`).
- **Triaje Clínico Profesional (Niveles I a V)**: Clasificación de urgencia basada en estándares clínicos reconocidos (Resolución 5596 de 2015 del Ministerio de Salud / Sistema Manchester / ESI) con 5 niveles de gravedad (I: Reanimación, II: Emergencia, III: Urgencia, IV: Prioritario, V: No urgente).
- **Separación de Tres Capas**:
  1. *Triaje Clínico Inicial*: Clasificación de entrada realizada por personal asistencial.
  2. *Deterioro Fisiológico Agudo (NEWS2)*: Monitoreo periódico y evolutivo de constantes vitales (0 a 20).
  3. *Priorización Administrativa de Cola*: Sugerencia explicable del orden de atención combinando nivel de triaje, alertas activas, score NEWS2 y tiempo de espera acumulado.
- **Captura Completa de Signos Vitales**: Frecuencia respiratoria, SpO2 (Escala 1 general y Escala 2 para insuficiencia respiratoria hipercápnica), soporte de oxígeno suplementario, tensión arterial sistólica, pulso cardíaco, conciencia en escala AVPU y temperatura corporal.
- **Scoring Clínico NEWS2**: Puntuación individual por parámetro (0 a 3) y score acumulado total (0 a 20), categorizado en riesgo Bajo, Bajo-Medio (alerta 3 en un solo parámetro), Medio o Alto según especificación RCP 2017.
- **Detección de Variaciones Críticas**: Notificación inmediata si hay variaciones de puntuación entre mediciones sucesivas (cambios hemodinámicos relevantes).
- **Gestión Integral de Alertas**: Panel para acuse de recibo (`acknowledge`) por parte del personal, con trazabilidad de estado (`pendiente` / `reconocida`).
- **Cola Dinámica Explicable**: Lista ordenada en tiempo real con desgloses cuantitativos y transparentes de qué factores colocaron al paciente en su puesto actual (Triaje: +120/+90/+50/+20 pts, Alertas: +100 pts, NEWS2: +80/+60/+40/+20 pts, Espera: +1 pt/10 min).
- **Simulador de Urgencias Estocástico**: Inyección controlada de perfiles sintéticos diferenciados (Estable, Deterioro leve, Crítico, Datos incompletos, Mejora gradual) con nombres ficticios, diagnósticos iniciales y síntomas realistas.
- **Configuración de Reglas**: Activación y desactivación dinámica de reglas del motor de inferencia sin reiniciar el servidor.
- **Migración Segura y No Destructiva**: Actualización automática del esquema SQLite mediante `PRAGMA table_info` y `ALTER TABLE ADD COLUMN` sin pérdida de registros preexistentes.

### Funcionalidades Pendientes / Roadmap Futuro ⏳
- **Módulo Predictivo de Machine Learning**: Modelos avanzados para estimar tiempo de permanencia en sala o probabilidad de hospitalización en UCI (la dependencia `scikit-learn` se encuentra reservada en `requirements.txt` para este fin).
- **Control de Acceso Basado en Roles (RBAC)**: Autenticación médica y perfiles diferenciados (médico, enfermero de triaje, administrativo, auditor).
- **Interoperabilidad Hospitalaria**: Integración con estándares HL7 FHIR para conexión con registros médicos electrónicos (EHR/HIS).
- **Persistencia en Base de Datos de Producción**: Migración de SQLite a PostgreSQL con pooling de conexiones para entornos concurrentes masivos.

---

## 🩺 Documentación Clínica de NEWS2

### Fuente Oficial
> **Royal College of Physicians (RCP)**  
> *National Early Warning Score (NEWS) 2: Standardising the assessment of acute-illness severity in the NHS.*  
> Londres: RCP, 2017.

### Parámetros Fisiológicos Evaluados

El score NEWS2 evalúa 6 parámetros fisiológicos cardinales más la presencia de oxígeno suplementario:

| Parámetro Fisiológico | 3 Puntos | 2 Puntos | 1 Punto | 0 Puntos | 1 Punto | 2 Puntos | 3 Puntos |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Frecuencia Respiratoria** (rpm) | ≤ 8 | - | 9 - 11 | **12 - 20** | - | 21 - 24 | ≥ 25 |
| **Saturación O2 - Escala 1** (%) | ≤ 91 | 92 - 93 | 94 - 95 | **≥ 96** | - | - | - |
| **Saturación O2 - Escala 2** (%) *(Hipercapnia/EPOC)* | ≤ 83 | 84 - 85 | 86 - 87 | **88 - 92** | 93 - 94 (con O2) | 95 - 96 (con O2) | ≥ 97 (con O2) |
| **Soporte de Oxígeno** | - | Aire ambiente | - | **No (Aire)** | - | Sí (Oxígeno) | - |
| **Presión Arterial Sistólica** (mmHg) | ≤ 90 | 91 - 100 | 101 - 110 | **111 - 219** | - | - | ≥ 220 |
| **Frecuencia Cardíaca** (lpm) | ≤ 40 | - | 41 - 50 | **51 - 90** | 91 - 110 | 111 - 130 | ≥ 131 |
| **Nivel de Conciencia** | - | - | - | **A (Alerta)** | - | - | **V, P, U** |
| **Temperatura Corporal** (°C) | ≤ 35.0 | - | 35.1 - 36.0 | **36.1 - 38.0** | 38.1 - 39.0 | ≥ 39.1 | - |

*(Nota: En la escala AVPU estándar del prototipo: A = Alerta [0 pts], V = Responde a la Voz [3 pts], P = Responde al Dolor [3 pts], U = Sin Respuesta [3 pts]. La detección de C / Nueva Confusión se documenta como mejora futura).*

### Estratificación de Riesgo y Umbrales
- **Riesgo Bajo (0 - 4 puntos)**: Deterioro fisiológico leve; se recomienda monitorización periódica de rutina.
- **Riesgo Bajo-Medio (Puntaje de 3 en un solo parámetro)**: Requiere evaluación médica prioritaria inmediata por sospecha de falla orgánica focal.
- **Riesgo Medio (5 - 6 puntos)**: Alerta clínica importante; requiere valoración urgente y aumento de la frecuencia de controles.
- **Riesgo Alto (7 o más puntos)**: Emergencia clínica; amerita evaluación inmediata por equipo de respuesta rápida o consideración de ingreso a unidad de cuidados intensivos.

> [!IMPORTANT]
> **Distinción entre Triaje y NEWS2:**  
> NEWS2 es una escala de detección temprana de **deterioro clínico agudo**. **No asigna categorías de triaje formal (Nivel I - V del Sistema de Triaje Manchester o ESI)**. La clasificación de triaje requiere la valoración integral del motivo de consulta, factores de riesgo y discriminadores clínicos por parte de un profesional calificado.

---

## ⚠️ Limitaciones Conocidas del Prototipo

1. **No validado para uso clínico**: No cuenta con validación prospectiva en entornos asistenciales reales.
2. **Sin asignación automática de Triaje I-V**: Se rechaza explícitamente el uso de umbrales numéricos para clasificar en categorías normativas de triaje sin criterio profesional.
3. **Ausencia de autenticación y control de accesos**: No incluye sistema de login, contraseñas ni segregación de permisos por rol.
4. **Almacenamiento SQLite local**: Base de datos diseñada para desarrollo monopuesto. No es apta para alta concurrencia o entornos distribuidos en la nube.
5. **Datos exclusivamente sintéticos**: Toda información precargada o generada es ficticia.
6. **Sin integración con HIS/EHR**: No se comunica con bases de datos ni monitores físicos de pacientes.
7. **Módulo de Machine Learning experimental**: Las funciones basadas en scikit-learn no forman parte del circuito clínico operativo actual.

---

## 🛠️ Stack Tecnológico

- **Lenguaje**: Python 3.9+
- **Interfaz de Usuario**: Streamlit
- **Visualización y Gráficos**: Plotly / Plotly Express
- **Procesamiento de Datos**: Pandas
- **Persistencia de Datos**: SQLite3 (nativo de Python)
- **Marco de Pruebas**: Pytest
- **Computación Científica**: Scikit-Learn (reservado para futuras extensiones)

---

## 🗄️ Respaldo y Restablecimiento de la Base de Datos

La base de datos SQLite se crea automáticamente en la raíz del proyecto con el nombre `triage_techminds.db`.

### Respaldo (Backup)
Con la aplicación detenida:
```cmd
copy triage_techminds.db triage_techminds_backup.db
```

### Restablecimiento a Estado Inicial (Reset)
Si desea eliminar todos los datos y reiniciar el sistema desde cero:
```cmd
del triage_techminds.db
```
Al volver a iniciar la aplicación (`streamlit run app.py`), la función `init_db()` recreará todas las tablas limpias automáticamente.

---

## 🔍 Identificación de Características No Implementadas

Para garantizar total transparencia en auditorías de código:
- Todas las capacidades futuras o experimentales están señalizadas en los docstrings de los módulos correspondientes.
- La interfaz de usuario muestra avisos explícitos en los apartados que constituyen herramientas de apoyo administrativo y no diagnóstico.
- La ausencia de modelos predictivos de Machine Learning en la toma de decisiones está claramente documentada tanto en la página de Metodología como en este archivo.

---

## 📄 Licencia

Este proyecto está distribuido bajo la licencia de **Uso Académico y Docente**. Queda prohibida su explotación comercial o uso asistencial en seres humanos.

---

## 👥 Créditos del Equipo

Proyecto desarrollado por el equipo **TechMinds**:
- **Equipo de Desarrollo e Ingeniería**: TechMinds Core Team
- **Diseño Arquitectural y Modelado de Triaje**: TechMinds Clinical AI Research Group
- **Institución**: Prototipo Académico de Informática Médica
