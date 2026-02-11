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

# --- 2. ESTILOS PRO (ROBOTO + CLEAN UI) ---
custom_css = """
<style>
/* Importamos Roboto desde Google Fonts */
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');

/* Aplicamos Roboto a todo */
html, body, [class*="css"] {
    font-family: 'Roboto', sans-serif;
}

/* Títulos en Negrita */
h1, h2, h3 {
    font-family: 'Roboto', sans-serif;
    font-weight: 700;
}

/* Ocultamos elementos nativos de Streamlit */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stApp { margin-top: -50px; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# --- 3. GESTIÓN DE SECRETOS ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except Exception as e:
    st.error("⚠️ Error de configuración: No se encontró la API Key en los secretos.")
    st.stop()

# --- 4. FUNCIONES DE LÓGICA ---

def create_pdf(text):
    """Genera PDF con firma de marca al pie de página"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Cuerpo del texto
    pdf.set_font("Arial", size=11)
    
    # Manejo básico de caracteres latinos
    try:
        text_encoded = text.encode('latin-1', 'replace').decode('latin-1')
    except:
        text_encoded = text
        
    pdf.multi_cell(0, 6, text_encoded)
    
    # --- FIRMA DE MARCA (FOOTER) ---
    pdf.ln(10) # Espacio vertical
    pdf.set_font("Arial", style="I", size=8) # Cursiva pequeña
    pdf.set_text_color(128, 128, 128) # Color gris
    footer_text = "Generado con Memodi IA - memodiapp.com"
    pdf.cell(0, 10, footer_text, align="C")
    
    return pdf.output(dest='S').encode('latin-1')

def get_pdf_text(pdf_file):
    """Extracción geométrica precisa de subrayados"""
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    all_annotations = []
    
    for page_num, page in enumerate(doc):
        page_annots = []
        for annot in page.annots():
            # 8 = Highlight, 4 = Underline
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
        
        # --- PROMPT CORREGIDO: MODO SILENCIOSO ---
        prompt = f"""
        Actúa como un **Médico Especialista en Medicina Interna** y editor científico.
        
        **OBJETIVO:**
        Procesa los fragmentos extraídos de un PDF para generar un **Resumen Clínico Profesional**.

        **INPUT:**
        {raw_text}

        **REGLAS:**
        1. **Limpieza:** Une palabras cortadas y elimina marcas de página.
        2. **Estructura Narrativa:**
           - **Definición y Epidemiología**
           - **Fisiopatología**
           - **Diagnóstico Diferencial**
           - **Manejo/Tratamiento**
        3. **Rigor Médico:** Mantén intacta terminología y valores.
        4. **Estilo:** Directo, tipo Harrison/UpToDate.

        **FORMATO DE SALIDA (ESTRICTO):**
        - Tu respuesta debe contener **EXCLUSIVAMENTE** el contenido Markdown del resumen.
        - **NO** incluyas introducciones como "Claro, aquí tienes el resumen" o "Como médico especialista...".
        - **NO** expliques lo que hiciste.
        - Comienza DIRECTAMENTE con el título del tema (ej: # Síncope).
        - Termina con la sección: ### 💎 Perlas Clínicas
        """
        
        config = genai.types.GenerationConfig(temperature=0.3)
        response = model.generate_content(prompt, generation_config=config)
        return response.text
        
    except Exception as e:
        return f"Error técnico: {str(e)}"

# --- 5. INTERFAZ DE USUARIO ---

# Logo Centrado
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image("https://memodiapp.com/images/Icontransparentshadow.png", width=120)

st.markdown("<h1 style='text-align: center;'>Memodi Notes</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #555;'>Sube tu PDF subrayado y obtén tu nota clínica.</p>", unsafe_allow_html=True)

uploaded_file = st.file_uploader(" ", type=["pdf"]) 

if uploaded_file:
    # 1. Extracción
    with st.spinner("🔍 Extrayendo tus subrayados..."):
        raw_text = get_pdf_text(uploaded_file)

    if raw_text:
        # 2. IA
        with st.spinner("🧠 Memodi IA está pensando..."):
            resumen_final = summarize_with_ai(raw_text)
        
        if "Error técnico" in resumen_final:
            st.error(resumen_final)
        else:
            st.success("¡Nota Clínica Generada!")
            
            # Firma para exportar
            firma_texto = "\n\n---\nGenerado con Memodi IA - memodiapp.com"
            resumen_firmado = resumen_final + firma_texto
            
            # Visualización
            st.markdown("---")
            st.markdown(resumen_final)
            st.caption("Generado con Memodi IA - memodiapp.com")
            st.markdown("---")
            
            # --- ÁREA DE DESCARGAS ---
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
                    st.error("Error generando PDF")
                    
    else:
        st.warning("⚠️ No se detectó texto subrayado. Asegúrate de usar Adobe o Preview.")
