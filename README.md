# 🚀 Streamlit Template App

Un template completo para comenzar proyectos con Streamlit desde cero. Este template incluye una estructura organizada, componentes reutilizables y ejemplos de funcionalidades comunes.

## 📋 Características

- **🏠 Dashboard principal** con métricas y datos de muestra
- **📊 Análisis de datos** con carga de archivos CSV
- **📈 Visualizaciones** con Plotly (gráficos interactivos)
- **📝 Formularios** para entrada de datos y configuración
- **⚙️ Configuración** de la aplicación
- **🎨 UI moderna** con CSS personalizado
- **📱 Diseño responsivo** con layout wide

## 🛠️ Estructura del Proyecto

```
Streamlit/
├── app.py                      # Aplicación principal
├── requirements.txt            # Dependencias
├── README.md                   # Documentación
├── .streamlit/
│   └── config.toml            # Configuración de Streamlit
├── utils/
│   ├── __init__.py
│   └── helpers.py             # Funciones auxiliares
└── components/
    ├── __init__.py
    ├── sidebar.py             # Componente de navegación
    ├── charts.py              # Componentes de gráficos
    └── forms.py               # Formularios
```

## 🚀 Instalación y Configuración

### 1. Clonar o descargar el template

```bash
# Si tienes git
git clone <repository-url>
cd Streamlit

# O simplemente descarga los archivos
```

### 2. Crear un entorno virtual (recomendado)

```bash
# Windows (PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Windows (Command Prompt)
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Ejecutar la aplicación

```bash
streamlit run app.py
```

La aplicación se abrirá automáticamente en tu navegador en `http://localhost:8501`

## 📚 Páginas Incluidas

### 🏠 Home
- Dashboard con métricas principales
- Tabla de datos de muestra
- Botón de descarga de datos

### 📊 Data Analysis
- Carga de archivos CSV
- Vista previa de datos
- Estadísticas básicas
- Información de columnas

### 📈 Charts & Visualizations
- Diferentes tipos de gráficos (línea, barras, scatter, histograma, heatmap)
- Opciones de personalización
- Gráficos interactivos con Plotly

### 📝 Forms & Input
- Formulario de contacto
- Formulario de entrada de datos
- Validación de campos

### ⚙️ Settings
- Configuración de la aplicación
- Preferencias de tema y idioma
- Configuración de datos y notificaciones

## 🔧 Personalización

### Cambiar el tema

Edita el archivo `.streamlit/config.toml`:

```toml
[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
```

### Añadir nuevas páginas

1. Añade la nueva página a `components/sidebar.py`:
```python
pages = [
    # ... páginas existentes
    {"name": "Mi Nueva Página", "icon": "🆕"}
]
```

2. Crea la función en `app.py`:
```python
def render_mi_nueva_pagina():
    st.header("Mi Nueva Página")
    # Tu contenido aquí

def main():
    # ... código existente
    elif page == "Mi Nueva Página":
        render_mi_nueva_pagina()
```

### Añadir nuevos componentes

Crea archivos en la carpeta `components/` siguiendo el patrón existente:

```python
import streamlit as st

def mi_componente():
    st.write("Mi componente personalizado")
```

## 📦 Dependencias Principales

- **streamlit**: Framework principal
- **pandas**: Manipulación de datos
- **numpy**: Operaciones numéricas
- **plotly**: Gráficos interactivos
- **matplotlib/seaborn**: Gráficos adicionales

### Dependencias Opcionales

- **streamlit-option-menu**: Menús de navegación avanzados
- **streamlit-aggrid**: Tablas interactivas
- **scikit-learn**: Machine learning
- **openpyxl**: Lectura de archivos Excel

## 🎨 Estilos CSS

El template incluye estilos CSS personalizados en `app.py`. Puedes modificarlos o añadir nuevos:

```python
st.markdown("""
<style>
    .mi-clase-personalizada {
        color: #ff6b6b;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)
```

## 📊 Gestión de Datos

### Cargar datos

```python
from utils.helpers import load_data

# Cargar archivo CSV
df = load_data("mi_archivo.csv")
```

### Generar datos de muestra

```python
from utils.helpers import generate_sample_data

# Generar 100 filas de datos de muestra
sample_df = generate_sample_data(100)
```

### Validar formularios

```python
from utils.helpers import validate_email

if validate_email("usuario@ejemplo.com"):
    st.success("Email válido")
```

## 🔍 Funcionalidades Avanzadas

### Session State

El template utiliza `st.session_state` para mantener datos entre interacciones:

```python
# Guardar datos
st.session_state.mi_dato = "valor"

# Recuperar datos
if "mi_dato" in st.session_state:
    st.write(st.session_state.mi_dato)
```

### Caché de datos

```python
@st.cache_data
def procesar_datos_pesados(datos):
    # Procesamiento que tarda mucho tiempo
    return datos_procesados
```

### Descarga de archivos

```python
# Generar CSV para descarga
csv = df.to_csv(index=False)
st.download_button(
    label="📥 Descargar CSV",
    data=csv,
    file_name="datos.csv",
    mime="text/csv"
)
```

## 🚀 Despliegue

### Streamlit Cloud

1. Sube tu código a GitHub
2. Ve a [share.streamlit.io](https://share.streamlit.io)
3. Conecta tu repositorio
4. Configura las variables de entorno si es necesario

### Docker

Crea un `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.address", "0.0.0.0"]
```

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 🆘 Soporte

Si tienes problemas o preguntas:

1. Revisa la [documentación oficial de Streamlit](https://docs.streamlit.io)
2. Busca en los [foros de la comunidad](https://discuss.streamlit.io)
3. Abre un issue en este repositorio

## 🔄 Actualizaciones

Para mantener el template actualizado:

```bash
# Actualizar Streamlit
pip install --upgrade streamlit

# Actualizar todas las dependencias
pip install --upgrade -r requirements.txt
```

---

**¡Disfruta creando aplicaciones increíbles con Streamlit! 🎉**
