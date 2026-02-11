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

# --- 2. SEGURIDAD & ESTILOS ---
# Ocultamos menú, footer, header Y el botón de Fullscreen/Deploy
custom_css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');

html, body, [class*="css"] { font-family: 'Roboto', sans-serif; }
h1, h2, h3 { font-family: 'Roboto', sans-serif; font-weight: 700; }

/* Ocultar TODO lo de Streamlit */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stApp { margin-top: -50px; }

/* Ocultar botones de la barra superior (Fullscreen, etc) */
[data-testid="stToolbar"] { visibility: hidden !important; display: none !important; }
.stDeployButton { display:none; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# --- 3. GESTIÓN DE SECRETOS ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    # Intentamos leer la contraseña maestra desde los secretos
    # Si no existe, usamos una por defecto para que no falle
    app_password = st.secrets.get("APP_PASSWORD", "MEMODI_VIP_2025")
    genai.configure(api_key=api_key)
except Exception as e:
    st.error("⚠️ Error de configuración del servidor.")
    st.stop()

# --- 4. SISTEMA DE LOGIN SIMPLE ---
def check_password():
    """Retorna True si el usuario está logueado"""
    
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
                st.rerun() # Recarga la página para mostrar la app
            else:
                st.error("⛔ Clave incorrecta")
                
    return False

# ⛔ SI NO HAY LOGIN, DETENEMOS TODO AQUÍ
if not check_password():
    st.stop()

# ==========================================
# 🚀 A PARTIR DE AQUÍ, SOLO VE LA APP QUIEN TIENE LA CLAVE
# ==========================================

# --- 5. FUNCIONES DE LÓGICA (Tu código original) ---

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
    for page_num, page in enumerate(doc):
        page_annots = []
        for annot in page.annots():
            if annot.type[0] in (8, 4):
                r = annot.rect
                r.x0 -= 1; r.y0 -= 1; r.x1 += 1; r.y1 += 1
                text = page.get_text("text", clip=r)
                if text.strip():
                    page_annots.append({
                        "text": text.strip(),
                        "y0": annot.rect.y0,
                        "x0": annot.rect.x0,
                        "page": page_num + 1
                    })
        page_annots.sort(key=lambda x: (x['y0'], x['x0']))
        all_annotations.extend(page_annots)
    raw_output = ""
    for item in all_annotations:
        raw_output += f"[Pág {item['page']}] {item['text']}\n"
    return raw_output

def summarize_with_ai(raw_text):
    model_name = 'gemini-flash-lite-latest'
    try:
        model = genai.GenerativeModel(model_name)
        prompt = f"""
        Actúa como un **Médico Especialista en Medicina Interna** y editor científico.
        **OBJETIVO:** Procesa los fragmentos de un PDF para generar un **Resumen Clínico Profesional**.
        **INPUT:** {raw_text}
        **REGLAS:**
        1. Limpieza y unión de palabras.
        2. Estructura Narrativa (Definición, Fisiopatología, Dx Dif, Tx).
        3. Rigor médico absoluto.
        4. Estilo directo.
        **FINAL:** ### 💎 Perlas Clínicas
        """
        config = genai.types.GenerationConfig(temperature=0.3)
        response = model.generate_content(prompt, generation_config=config)
        return response.text
    except Exception as e:
        return f"Error técnico: {str(e)}"

# --- 6. INTERFAZ DE USUARIO (SOLO VISIBLE TRAS LOGIN) ---

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image("https://memodiapp.com/images/Icontransparentshadow.png", width=120)

st.markdown("<h1 style='text-align: center;'>Memodi Notes</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #555;'>Sube tu PDF subrayado y obtén tu nota clínica.</p>", unsafe_allow_html=True)

uploaded_file = st.file_uploader(" ", type=["pdf"]) 

if uploaded_file:
    with st.spinner("🔍 Extrayendo tus subrayados..."):
        raw_text = get_pdf_text(uploaded_file)

    if raw_text:
        with st.spinner("🧠 Memodi IA está pensando..."):
            resumen_final = summarize_with_ai(raw_text)
        
        if "Error técnico" in resumen_final:
            st.error(resumen_final)
        else:
            st.success("¡Nota Clínica Generada!")
            
            firma_texto = "\n\n---\nGenerado con Memodi IA - memodiapp.com"
            resumen_firmado = resumen_final + firma_texto
            
            st.markdown("---")
            st.markdown(resumen_final)
            st.caption("Generado con Memodi IA - memodiapp.com")
            st.markdown("---")
            
            st.subheader("📥 Exportar Nota")
            d1, d2, d3 = st.columns(3)
            with d1:
                st.download_button("📄 Markdown", resumen_firmado, "Nota_Memodi.md", "text/markdown")
            with d2:
                st.download_button("📝 Texto", resumen_firmado, "Nota_Memodi.txt", "text/plain")
            with d3:
                try:
                    pdf_bytes = create_pdf(resumen_final)
                    st.download_button("📕 PDF", pdf_bytes, "Nota_Memodi.pdf", "application/pdf")
                except:
                    st.error("Error PDF")
    else:
        st.warning("⚠️ No se detectó texto subrayado.")
