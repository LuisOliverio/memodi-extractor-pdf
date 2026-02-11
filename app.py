import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
from fpdf import FPDF
import time

# --- 1. CONFIGURACIÓN ---
st.set_page_config(
    page_title="Memodi Notes",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- 2. SEGURIDAD & ESTILOS "MODO NINJA" ---
custom_css = """
<style>
/* Importamos Roboto */
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');

html, body, [class*="css"] { font-family: 'Roboto', sans-serif; }
h1, h2, h3 { font-family: 'Roboto', sans-serif; font-weight: 700; }

/* --- CSS NUCLEAR PARA OCULTAR INTERFAZ DE STREAMLIT --- */

/* 1. Ocultar la barra superior (Menu hamburguesa, Deploy, Settings, Fullscreen) */
[data-testid="stToolbar"] { 
    visibility: hidden !important; 
    display: none !important; 
}

/* 2. Ocultar el Header (la franja vacía arriba) */
[data-testid="stHeader"] { 
    visibility: hidden !important; 
    display: none !important; 
    height: 0px !important;
}

/* 3. Ocultar Footer ("Made with Streamlit") */
footer { 
    visibility: hidden !important; 
    display: none !important; 
}

/* 4. Subir el contenido para aprovechar el espacio liberado */
.stApp { 
    margin-top: -60px !important; 
}

/* 5. Ocultar botón "Deploy" específico si aparece flotando */
.stDeployButton { 
    display:none !important; 
}

/* 6. Ocultar decoraciones de imágenes (botón fullscreen de imágenes individuales) */
[data-testid="stImageCaption"] { display: none; }
button[title="View fullscreen"] { display: none !important; }

</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# --- 3. GESTIÓN DE SECRETOS ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    # Contraseña Maestra (Definida en Secrets o default)
    app_password = st.secrets.get("APP_PASSWORD", "MEMODI_VIP_2025")
    genai.configure(api_key=api_key)
except Exception as e:
    st.error("⚠️ Error crítico de configuración.")
    st.stop()

# --- 4. SISTEMA DE LOGIN (CANDADO) ---
def check_password():
    """Retorna True solo si la clave es correcta"""
    
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if st.session_state.password_correct:
        return True

    # Interfaz de Login
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.image("https://memodiapp.com/images/Icontransparentshadow.png", width=100)
        st.markdown("<h3 style='text-align: center;'>Acceso Memodi Notes</h3>", unsafe_allow_html=True)
        
        pwd_input = st.text_input("Ingresa tu Clave de Acceso:", type="password")
        
        if st.button("Ingresar", use_container_width=True):
            if pwd_input == app_password:
                st.session_state.password_correct = True
                st.rerun()
            else:
                st.error("⛔ Clave incorrecta")
                
    return False

# ⛔ BLOQUEO DE SEGURIDAD
if not check_password():
    st.stop()

# ==========================================
# 🚀 APLICACIÓN REAL (SOLO VISIBLE CON CLAVE)
# ==========================================

def create_pdf(text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=11)
    try:
        text_encoded = text.encode('latin-1', 'replace').decode('latin-1')
    except:
        text_encoded = text
    pdf.multi_cell(0, 6, text_encoded)
    pdf.ln(10)
    pdf.set_font("Arial", style="I", size=8)
    pdf.set_text_color(128, 128, 128)
    footer_text = "Generado con Memodi IA - memodiapp.com"
    pdf.cell(0, 10, footer_text, align="C")
    return pdf.output(dest='S').encode('latin-1')

def get_pdf_text(pdf_file):
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    all_annotations = []
    for
