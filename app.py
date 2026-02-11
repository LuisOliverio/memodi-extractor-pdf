import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai

# --- 1. CONFIGURACIÓN ---
st.set_page_config(
    page_title="Memodi Notes",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- 2. ESTILOS (IFRAME MODE) ---
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stApp { margin-top: -80px; }
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

# --- 4. EXTRACCIÓN GEOMÉTRICA (MOTOR MEMODI) ---
def get_pdf_text(pdf_file):
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    all_annotations = []
    
    for page_num, page in enumerate(doc):
        page_annots = []
        for annot in page.annots():
            if annot.type[0] in (8, 4): # Highlight / Underline
                # Padding para capturar bien el texto
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
        
        # Ordenamos por lectura humana (Arriba->Abajo, Izquierda->Derecha)
        page_annots.sort(key=lambda x: (x['y0'], x['x0']))
        all_annotations.extend(page_annots)

    # Formateamos la salida cruda
    raw_output = ""
    for item in all_annotations:
        raw_output += f"[Pág {item['page']}] {item['text']}\n"
        
    return raw_output

# --- 5. CEREBRO CLÍNICO (GEMINI FLASH LITE) ---
def summarize_with_ai(raw_text):
    # Modelo rápido y eficiente
    model_name = 'gemini-flash-lite-latest'
    
    try:
        model = genai.GenerativeModel(model_name)
        
        # --- TU PROMPT DE ALTA ESPECIALIDAD ---
        prompt = f"""
        Actúa como un **Médico Especialista** con experiencia en edición de textos científicos.
        
        **OBJETIVO:**
        Procesa los siguientes fragmentos de texto extraídos de un PDF (que contienen ruido como números de página, palabras cortadas por guiones y saltos de línea abruptos) para generar un **Resumen Clínico Profesional**.

        **INPUT (TEXTO SUCIO):**
        {raw_text}

        **REGLAS DE PROCESAMIENTO:**
        1. **Limpieza y Unificación:** Une las palabras cortadas por guiones (ej. 'sponta- neous' a 'spontaneous'), elimina las marcas de página (ej. '[Pág 1]') y corrige errores de escaneo.
        2. **Estructura Narrativa:** No hagas una simple lista. Crea una narrativa fluida dividida en estas secciones lógicas (si la información está disponible):
           - **Definición y Epidemiología**
           - **Fisiopatología**
           - **Diagnóstico Diferencial** (Enfatiza distinciones clave ej. Síncope vs Epilepsia)
           - **Manejo/Tratamiento**
        3. **Rigor Médico:** Mantén intacta toda la terminología técnica, valores numéricos, umbrales de presión arterial, porcentajes y referencias a medicamentos (dosis, nombres exactos).
        4. **Tono:** Profesional, directo y con rigor científico, similar a un manual tipo **Harrison** o **UpToDate**.

        **SALIDA FINAL:**
        Al terminar la narrativa, añade una sección obligatoria llamada:
        ### 💎 Tus anotaciones más importantes
        Una lista de puntos clave (bullet points) con lo más crítico para un algoritmo diagnóstico (Red Flags, maniobras, decisiones clave).
        """
        
        # Temperatura baja para evitar alucinaciones en dosis/datos
        config = genai.types.GenerationConfig(temperature=0.3)
        
        response = model.generate_content(prompt, generation_config=config)
        return response.text
        
    except Exception as e:
        return f"Error técnico al generar el resumen: {str(e)}"

# --- 6. INTERFAZ DE USUARIO ---
st.title("🧠 Memodi Notes")
st.markdown("Sube tu PDF subrayado para generar un resumen personlizado")

uploaded_file = st.file_uploader("Sube PDF (Máx 50MB)", type=["pdf"])

if uploaded_file:
    # 1. Extracción
    with st.spinner("Extrayendo evidencia del texto..."):
        raw_text = get_pdf_text(uploaded_file)

    if raw_text:
        # 2. Análisis Clínico
        with st.spinner("🧠 Memodi IA está pensando..."):
            resumen_final = summarize_with_ai(raw_text)
        
        if "Error técnico" in resumen_final:
            st.error(resumen_final)
        else:
            st.success("¡Nota Clínica Lista!")
            
            st.markdown("---")
            st.markdown(resumen_final)
            st.markdown("---")
            
            st.download_button(
                label="📥 Descargar Nota (.md)",
                data=resumen_final,
                file_name="Nota_Clinica_Memodi.md",
                mime="text/markdown"
            )
    else:
        st.warning("⚠️ No se detectó texto subrayado. Asegúrate de usar un PDF nativo.")
