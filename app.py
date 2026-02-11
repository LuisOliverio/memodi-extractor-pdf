import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
from fpdf import FPDF

# --- 1. CONFIGURACIÓN ---
st.set_page_config(
    page_title="Memodi Notes",
    page_icon="🧠",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- 2. ESTILOS (IFRAME MODE) ---
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stApp { margin-top: -50px; }
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# --- 3. GESTIÓN DE SECRETOS ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except Exception as e:
    st.error("⚠️ Error de configuración: No se encontró la API Key.")
    st.stop()

# --- 4. FUNCIONES DE UTILIDAD ---

def create_pdf(text):
    """Genera un PDF simple a partir del texto"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=11)
    
    # Manejo básico de caracteres latinos para FPDF (Arial estándar no soporta todo Unicode)
    # Reemplazamos caracteres problemáticos comunes si fuera necesario o codificamos a latin-1
    try:
        # Intentamos codificar a latin-1 para compatibilidad con Arial
        text_encoded = text.encode('latin-1', 'replace').decode('latin-1')
    except:
        text_encoded = text # Fallback

    pdf.multi_cell(0, 6, text_encoded)
    return pdf.output(dest='S').encode('latin-1')

def get_pdf_text(pdf_file):
    """Extracción geométrica precisa"""
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    all_annotations = []
    
    for page_num, page in enumerate(doc):
        page_annots = []
        for annot in page.annots():
            if annot.type[0] in (8, 4): # Highlight / Underline
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
    # --- MODELO SOLICITADO ---
    model_name = 'gemini-flash-lite-latest'
    
    try:
        model = genai.GenerativeModel(model_name)
        
        prompt = f"""
        Actúa como un **Médico Especialista en Medicina Interna** con experiencia en edición de textos científicos.
        
        **OBJETIVO:**
        Procesa los siguientes fragmentos de texto extraídos de un PDF (que contienen ruido como números de página, palabras cortadas por guiones y saltos de línea abruptos) para generar un **Resumen Clínico Profesional**.

        **INPUT (TEXTO SUCIO):**
        {raw_text}

        **REGLAS DE PROCESAMIENTO:**
        1. **Limpieza y Unificación:** Une palabras cortadas, elimina marcas de página.
        2. **Estructura Narrativa:** Crea una narrativa fluida dividida en secciones lógicas:
           - **Definición y Epidemiología**
           - **Fisiopatología**
           - **Diagnóstico Diferencial**
           - **Manejo/Tratamiento**
        3. **Rigor Médico:** Mantén intacta terminología, dosis y valores.
        4. **Tono:** Profesional tipo Harrison/UpToDate.

        **SALIDA FINAL:**
        Añade al final:
        ### 💎 Perlas Clínicas
        Lista de puntos clave críticos (Red Flags, maniobras).
        """
        
        config = genai.types.GenerationConfig(temperature=0.3)
        response = model.generate_content(prompt, generation_config=config)
        return response.text
        
    except Exception as e:
        return f"Error técnico al generar el resumen: {str(e)}"

# --- 5. INTERFAZ DE USUARIO ---

# Logo Centrado
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image("https://memodiapp.com/images/Icontransparentshadow.png", width=120)

st.markdown("<h1 style='text-align: center;'>Memodi Notes</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>Sube tu PDF subrayado y obtén tu nota clínica.</p>", unsafe_allow_html=True)

uploaded_file = st.file_uploader(" ", type=["pdf"]) # Label vacío para limpieza visual

if uploaded_file:
    # Extracción
    with st.spinner("🔍 Extrayendo tus subrayados..."):
        raw_text = get_pdf_text(uploaded_file)

    if raw_text:
        # IA
        with st.spinner("🧠 Memodi IA está pensando..."):
            resumen_final = summarize_with_ai(raw_text)
        
        if "Error técnico" in resumen_final:
            st.error(resumen_final)
        else:
            st.success("¡Nota Clínica Generada!")
            
            st.markdown("---")
            st.markdown(resumen_final)
            st.markdown("---")
            
            # --- SECCIÓN DE DESCARGAS ---
            st.subheader("📥 Exportar Nota")
            d_col1, d_col2, d_col3 = st.columns(3)
            
            # 1. Markdown
            with d_col1:
                st.download_button(
                    label="📄 Markdown (.md)",
                    data=resumen_final,
                    file_name="Nota_Memodi.md",
                    mime="text/markdown"
                )
            
            # 2. Texto Plano
            with d_col2:
                st.download_button(
                    label="📝 Texto (.txt)",
                    data=resumen_final,
                    file_name="Nota_Memodi.txt",
                    mime="text/plain"
                )

            # 3. PDF
            with d_col3:
                # Generamos el PDF al vuelo
                try:
                    pdf_bytes = create_pdf(resumen_final)
                    st.download_button(
                        label="📕 PDF (.pdf)",
                        data=pdf_bytes,
                        file_name="Nota_Memodi.pdf",
                        mime="application/pdf"
                    )
                except Exception as e:
                    st.warning("Error al generar PDF")
                    
    else:
        st.warning("⚠️ No se detectó texto subrayado. Usa Adobe/Preview.")
