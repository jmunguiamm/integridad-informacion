# 🧭 Taller de Integridad de la Información

Aplicación Streamlit para talleres educativos sobre desinformación y sesgos informativos. Permite recopilar percepciones de participantes, generar análisis mediante IA, crear noticias con diferentes encuadres narrativos y visualizar resultados en tiempo real.

## 📋 Objetivo

Taller interactivo que busca **entender cómo las narrativas cambian la forma en que percibimos las noticias** y desarrollar una mirada crítica frente a la desinformación. El sistema utiliza análisis de IA para identificar temas dominantes en las percepciones de los participantes y genera contenido educativo personalizado.

## 🏗️ Arquitectura Técnica

- **Frontend**: Streamlit (aplicación web interactiva)
- **Almacenamiento**: Google Sheets (respuestas de formularios)
- **IA y Análisis**: OpenAI API (análisis de emociones, generación de noticias)
- **Procesamiento**: pandas, numpy
- **Visualización**: Plotly, matplotlib, wordcloud

## 🔄 Flujo del Taller

1. **Configuración**: Formador completa datos del taller (Form 0) y selecciona fecha
2. **Cuestionario 1**: Participantes reportan percepciones de inseguridad y exposición a noticias
3. **Análisis IA**: Identificación automática del tema dominante y emociones asociadas
4. **Noticia neutral**: Generación de una noticia factual basada en el tema dominante
5. **Noticias con encuadres**: Tres versiones de la misma noticia con diferentes narrativas (desconfianza, polarización, miedo/control)
6. **Cuestionario 2**: Participantes reaccionan ante las diferentes versiones de noticias
7. **Análisis final**: Dashboard con resultados, análisis de emociones por encuadre, impactos por género y conclusiones

## ⚙️ Configuración

### Variables de Entorno Requeridas

Crear archivo `.streamlit/secrets.toml` o configurar variables de entorno:

```toml
# Google Sheets
FORMS_SHEET_ID = "tu-sheet-id"
FORM0_TAB = "nombre-tab-form0"
FORM1_TAB = "nombre-tab-form1"
FORM2_TAB = "nombre-tab-form2"
GOOGLE_SERVICE_ACCOUNT = "{\"type\": \"service_account\", ...}"  # JSON como string

# URLs de Formularios Google
FORM0_URL = "https://docs.google.com/forms/..."
FORM1_URL = "https://docs.google.com/forms/..."
FORM2_URL = "https://docs.google.com/forms/..."

# OpenAI API
OPENAI_API_KEY = "sk-..."
```

### Credenciales de Google Sheets

1. Crear una cuenta de servicio en [Google Cloud Console](https://console.cloud.google.com/)
2. Habilitar Google Sheets API y Google Drive API
3. Generar clave JSON y guardarla como `GOOGLE_SERVICE_ACCOUNT`
4. Compartir el Google Sheet con el email de la cuenta de servicio

## 🚀 Instalación

### 1. Clonar el repositorio

```bash
git clone <repository-url>
cd Streamlit
```

### 2. Crear entorno virtual

```bash
python -m venv venv

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Windows (CMD)
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar credenciales

Copiar `.streamlit/secrets.toml.example` a `.streamlit/secrets.toml` y completar las variables requeridas.

### 5. Ejecutar la aplicación

```bash
streamlit run app.py
```

La aplicación estará disponible en `http://localhost:8501`

## 📁 Estructura del Proyecto

```
Streamlit/
├── app.py                      # Aplicación principal (router y páginas)
├── requirements.txt            # Dependencias Python
├── config/
│   └── secrets.py             # Gestión de credenciales
├── data/
│   ├── sheets.py              # Integración con Google Sheets
│   ├── cleaning.py            # Normalización de datos
│   └── utils.py               # Utilidades de fechas y datos
├── services/
│   ├── ai_analysis.py         # Análisis con OpenAI (emociones, género, general)
│   └── news_generator.py      # Generación de noticias con encuadres
├── components/
│   ├── navigation.py          # Contexto de navegación entre páginas
│   ├── whatsapp_bubble/       # Componente de visualización tipo WhatsApp
│   ├── qr_utils/              # Generación de códigos QR
│   └── image_repo.py          # Repositorio de imágenes por tema
└── images/                    # Imágenes del taller
```

## 📦 Dependencias Principales

- **streamlit** ≥1.28.0: Framework web
- **pandas** ≥2.0.0: Procesamiento de datos
- **gspread** ≥6.1.4: API de Google Sheets
- **google-auth** ≥2.36.0: Autenticación Google
- **openai** ≥1.51.0: API de OpenAI
- **plotly** ≥5.15.0: Gráficos interactivos
- **wordcloud** 1.9.3: Nube de palabras
- **qrcode[pil]** ≥7.4: Generación de códigos QR

Ver `requirements.txt` para lista completa.

## 🔑 Funcionalidades Clave

- **Recopilación de datos**: Integración con Google Forms vía Google Sheets
- **Análisis de IA**: Identificación automática de temas dominantes y patrones emocionales
- **Generación de contenido**: Creación de noticias neutrales y con diferentes encuadres narrativos
- **Visualización interactiva**: Dashboard con Looker Studio y gráficos en tiempo real
- **Análisis diferenciado**: Por género, por encuadre narrativo, por contexto del grupo

## 🌐 Despliegue

### Streamlit Cloud

1. Subir código a GitHub
2. Conectar repositorio en [share.streamlit.io](https://share.streamlit.io)
3. Configurar secrets en la interfaz de Streamlit Cloud

### Local con Docker

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.address", "0.0.0.0"]
```

## 📝 Notas Técnicas

- La aplicación filtra datos por fecha del taller seleccionada
- Los análisis se cachean en `st.session_state` para mejorar rendimiento
- Las imágenes se asignan automáticamente según el tema dominante identificado
- Los formularios deben estar configurados en Google Forms con campos específicos (ver código para detalles)

## 📄 Licencia

[Especificar licencia del proyecto]
