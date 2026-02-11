import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
from fpdf import FPDF
import pandas as pd

# --- 1. CONFIGURACIÓN ---
st.set_page_config(
    page_title="Memodi Notes",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- 2. ESTILOS PRO (ROBOTO + NUCLEAR V3) ---
custom_css = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');

html, body, [class*="css"] { font-family: 'Roboto', sans-serif; }
h1, h2, h3 { font-family: 'Roboto', sans-serif; font-weight: 700; }

/* OCULTAR INTERFAZ STREAMLIT */
[data-testid="stToolbar"], [data-testid="stHeader"], [data-testid="stDecoration"], [data-testid="stStatusWidget"], footer {
    visibility: hidden !important; display: none !important;
}

.block-container {
    padding-top: 0rem !important;
    padding-bottom: 0rem !important;
    margin-top: -30px !important;
}

button[title="View fullscreen"] { display: none !important; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# Espaciador para compensar el recorte del iframe en WordPress
st.markdown("<div style='margin-top: 55px;'></div>", unsafe_allow_html=True)

# --- 3. GESTIÓN DE SECRETOS ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except Exception as e:
    st.error("⚠️ Error de configuración de API Key.")
    st.stop()

# --- HELPER: LOGO ---
def mostrar_logo():
    st.markdown(
        """
        <div style="display: flex; justify-content: center; margin-bottom: 10px;">
            <img src="https://memodiapp.com/images/Icontransparentshadow.png" width="100">
        </div>
        """,
        unsafe_allow_html=True
    )

# --- 4. SISTEMA DE LOGIN (GOOGLE SHEETS) ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    if st.session_state.password_correct:
        return True

    # Lectura de la hoja de Google
    sheet_id = "1LLGwm7CTENFw4ZNU7S--j4DmiOEL7mSSqMJIlo-_FY4"
    sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
    
    try:
        df = pd.read_csv(sheet_url)
        # Buscamos en la columna 'Password' donde 'Activo' sea TRUE o VERDADERO
        # Asegúrate de que tus columnas en el Excel se llamen exactamente 'Password' y 'Activo'
        valid_passwords = df[df['Activo'].astype(str).str.upper() == 'TRUE']['Password'].astype(str).tolist()
    except Exception as e:
        st.error("⚠️ Error conectando con la base de datos de accesos. Verifica que la hoja sea pública (Lector).")
        return False

    mostrar_logo()
    st.markdown("<h3 style='text-align: center;'>Acceso Memodi Notes</h3>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        pwd_input = st.text_input("Clave de Acceso:", type="password", label_visibility="collapsed", placeholder="Ingresa tu clave aquí")
        if st.button("Ingresar", use_container_width=True):
            if pwd_input in valid_passwords:
                st.session_state.password_correct = True
                st.rerun()
            else:
                st.error("⛔ Clave incorrecta o cuenta inactiva.")
    return False

if not check_password():
    st.stop()

# ==========================================
# 🚀 APP PRINCIPAL (Lógica Médica)
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
    for page_num, page in enumerate(doc):
        page_annots = []
        for annot in page.annots():
            if annot.type[0] in (8, 4):
                r = annot.rect
                r.x0 -= 1; r.y0 -= 1; r.x1 += 1; r.y1 += 1
                text = page.get_text("text", clip=r)
                if text.strip():
                    page_annots.append({"text": text.strip(), "y0": annot.rect.y0, "x0": annot.rect.x0, "page": page_num + 1})
        page_annots.sort(key=lambda x: (x['y0'], x['x0']))
        all_annotations.extend(page_annots)
    return "".join([f"[Pág {item['page']}] {item['text']}\n" for item in all_annotations])

def summarize_with_ai(raw_text):
    model_name = 'gemini-flash-lite-latest'
    try:
        model = genai.GenerativeModel(model_name)
        prompt = f"""Actúa como Médico Especialista en Medicina Interna. Procesa los fragmentos: {raw_text}. 
        Reglas: Limpieza, estructura narrativa (Definición, Fisiopatología, Dx Dif, Tx), rigor médico, estilo Harrison. 
        Salida: Solo Markdown, sin intros, termina con ### 💎 Perlas Clínicas."""
        response = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(temperature=0.3))
        return response.text
    except Exception as e:
        return f"Error técnico: {str(e)}"

# --- UI ---
mostrar_logo()
st.markdown("<h1 style='text-align: center;'>Memodi Notes</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #555;'>Sube tu PDF subrayado y obtén tu nota clínica.</p>", unsafe_allow_html=True)

uploaded_file = st.file_uploader(" ", type=["pdf"]) 

if uploaded_file:
    with st.spinner("🔍 Extrayendo subrayados..."):
        raw_text = get_pdf_text(uploaded_file)
    if raw_text:
        with st.spinner("🧠 Memodi IA está pensando..."):
            resumen_final = summarize_with_ai(raw_text)
        if "Error técnico" in resumen_final:
            st.error(resumen_final)
        else:
            st.success("¡Nota Clínica Lista!")
            resumen_firmado = resumen_final + "\n\n---\nGenerado con Memodi IA - memodiapp.com"
            st.markdown("---")
            st.markdown(resumen_final)
            st.caption("Generado con Memodi IA - memodiapp.com")
            st.markdown("---")
            st.subheader("📥 Exportar")
            d1, d2, d3 = st.columns(3)
            with d1: st.download_button("📄 Markdown", resumen_firmado, "Nota.md")
            with d2: st.download_button("📝 Texto", resumen_firmado, "Nota.txt")
            with d3:
                try:
                    st.download_button("📕 PDF", create_pdf(resumen_final), "Nota.pdf")
                except: st.error("Error PDF")
