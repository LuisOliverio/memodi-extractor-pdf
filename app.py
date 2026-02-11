import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Memodi Tools", layout="centered")

# --- OCULTAR ELEMENTOS DE STREAMLIT ---
# Esto ayuda a que se vea más limpio dentro del iframe
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# --- GESTIÓN DE SECRETOS (INVISIBLE) ---
try:
    # Intenta leer la clave de los secretos de Streamlit
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except Exception as e:
    # Si falla, muestra un error genérico (no pide la clave)
    st.error("⚠️ Error de configuración en el servidor. Contacta a soporte@memodi.mx")
    st.stop()

# --- FUNCIONES ---
def get_pdf_text(pdf_file):
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    text_parts = []
    
    for page in doc:
        # Lógica geométrica simple y robusta
        for annot in page.annots():
            if annot.type[0] in (8, 4):
                r = annot.rect
                r.x0 -= 1; r.y0 -= 1; r.x1 += 1; r.y1 += 1
                text = page.get_text("text", clip=r)
                if text.strip():
                    text_parts.append(text.strip())
                    
    return "\n".join(text_parts)

def summarize_with_ai(raw_text):
    model = genai.GenerativeModel('gemini-flash-lite-latest')
    prompt = f"""
    Actúa como un asistente médico experto.
    Analiza estos fragmentos de texto extraídos de un documento médico subrayado:
    
    {raw_text}
    
    Tu tarea:
    1. Une las frases cortadas.
    2. Elimina referencias bibliográficas.
    3. Genera un resumen de estudio claro y estructurado (Bullet points).
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Error técnico: {str(e)}"

# --- INTERFAZ ---
st.title("🩺 Memodi Notes")
st.markdown("Sube tu PDF subrayado y obtén tu resumen al instante.")

uploaded_file = st.file_uploader("Sube PDF (Máx 50MB)", type=["pdf"])

if uploaded_file:
    with st.spinner("Leyendo documento..."):
        raw_text = get_pdf_text(uploaded_file)

    if raw_text:
        with st.spinner("Generando resumen con IA..."):
            resumen = summarize_with_ai(raw_text)
            
        st.success("¡Resumen listo!")
        st.markdown(resumen)
        st.download_button("Descargar Notas", resumen, "notas_memodi.md")
    else:
        st.info("No detectamos texto subrayado. Asegúrate de usar Adobe o Preview.")
