import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai

# --- 1. FUNCIÓN DE EXTRACCIÓN (LA TUYA) ---
def get_pdf_text_raw(pdf_file):
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    all_text_parts = []

    for page_num, page in enumerate(doc):
        # Capturamos anotaciones
        annotations = []
        for annot in page.annots():
            if annot.type[0] in (8, 4):  # Highlight/Underline
                # Usamos rect simple con padding para velocidad
                r = annot.rect
                r.x0 -= 1; r.y0 -= 1; r.x1 += 1; r.y1 += 1
                text = page.get_text("text", clip=r)
                if text.strip():
                    annotations.append({
                        "text": text.strip(),
                        "y0": annot.rect.y0,
                        "x0": annot.rect.x0,
                        "page": page_num + 1
                    })
        
        # Ordenamos
        annotations.sort(key=lambda x: (x['y0'], x['x0']))
        
        for a in annotations:
            all_text_parts.append(f"[Pág {a['page']}] {a['text']}")
            
    return "\n".join(all_text_parts)

# --- 2. FUNCIÓN DE INTELIGENCIA ARTIFICIAL (GEMINI) ---
def clean_with_ai(raw_text, api_key):
    # Configurar la API
    genai.configure(api_key=api_key)
    
    # Usamos 'gemini-1.5-flash' por ser rápido y barato
    model = genai.GenerativeModel('gemini-flash-lite-latest')
    
    # El Prompt de Ingeniería Médica
    prompt = f"""
    Eres un editor médico experto trabajando para la app 'Memodi'.
    Tu tarea es limpiar y estructurar las siguientes notas extraídas de un PDF médico.
    
    Instrucciones:
    1. Reconstruye las oraciones fragmentadas o cortadas por saltos de línea.
    2. Elimina referencias bibliográficas (ej: [12], (Fig. 1)) que interrumpan la lectura.
    3. Si hay abreviaturas médicas obvias (ej: HTA, DM2), mantenlas.
    4. Corrige errores tipográficos obvios de la extracción (ej: 'l0 mg' -> '10 mg').
    5. Devuelve el resultado como un resumen para el estudio, sin inventar ningún dato.
    
    Texto sucio a procesar:
    {raw_text}
    """
    
    with st.spinner('🤖 Gemini está leyendo y limpiando tus notas...'):
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error de API: {str(e)}"

# --- 3. INTERFAZ GRÁFICA ---
st.set_page_config(page_title="Memodi AI", page_icon="🧠")

st.title("🧠 Memodi AI: Extractor Inteligente")
st.markdown("Sube tu PDF subrayado. La IA lo limpiará y resumirá por ti.")

# Barra lateral para configuración
with st.sidebar:
    st.header("Configuración")
    api_key = st.text_input("Tu API Key de Google", type="password")
    st.info("Consigue tu clave gratis en aistudio.google.com")

uploaded_file = st.file_uploader("Sube PDF", type=["pdf"])

if uploaded_file and api_key:
    # 1. Extraer
    raw_text = get_pdf_text_raw(uploaded_file)
    
    if raw_text:
        st.success("Texto extraído. Enviando a IA...")
        
        # 2. Procesar con IA
        ai_summary = clean_with_ai(raw_text, api_key)
        
        # 3. Mostrar Resultados
        st.subheader("📝 Resumen Limpio")
        st.markdown(ai_summary)
        
        # Botón de descarga
        st.download_button(
            label="📥 Descargar Resumen Final",
            data=ai_summary,
            file_name="resumen_memodi.md",
            mime="text/markdown"
        )
    else:
        st.warning("No se encontró texto subrayado en el PDF.")
        
elif uploaded_file and not api_key:
    st.warning("⚠️ Por favor ingresa tu API Key en la barra lateral para usar la IA.")