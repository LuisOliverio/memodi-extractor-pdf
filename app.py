import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai

# --- 1. CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(
    page_title="Memodi Notes",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- 2. ESTILOS CSS (PARA IFRAME LIMPIO) ---
# Esto elimina el menú de hamburguesa, el footer y el header de colores
# para que parezca una herramienta nativa de tu web.
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
.stApp {
    margin-top: -80px; /* Sube el contenido para aprovechar espacio en iframes */
}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# --- 3. GESTIÓN DE SECRETOS (SEGURIDAD) ---
try:
    # Intenta leer la clave de los secretos de Streamlit Cloud
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except Exception as e:
    st.error("⚠️ Error de configuración del servidor. No se encontró la API Key.")
    st.stop()

# --- 4. FUNCIÓN DE EXTRACCIÓN (ORDENADA Y PRECISA) ---
def get_pdf_text(pdf_file):
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    all_annotations = []
    
    for page_num, page in enumerate(doc):
        # Capturamos anotaciones de la página
        page_annots = []
        for annot in page.annots():
            # 8 = Highlight, 4 = Underline
            if annot.type[0] in (8, 4):
                # Usamos el rectángulo con un pequeño 'padding' (inflación)
                # para asegurar que capturamos letras altas o bajas
                r = annot.rect
                r.x0 -= 1; r.y0 -= 1; r.x1 += 1; r.y1 += 1
                
                text = page.get_text("text", clip=r)
                
                if text.strip():
                    page_annots.append({
                        "text": text.strip(),
                        "y0": annot.rect.y0, # Coordenada vertical
                        "x0": annot.rect.x0, # Coordenada horizontal
                        "page": page_num + 1
                    })
        
        # ORDENAMIENTO CRÍTICO:
        # Primero de Arriba a Abajo (y0), luego de Izquierda a Derecha (x0)
        # Esto corrige el problema de leer columnas desordenadas.
        page_annots.sort(key=lambda x: (x['y0'], x['x0']))
        
        all_annotations.extend(page_annots)

    # Reconstruimos el texto crudo en orden
    raw_text_output = ""
    for item in all_annotations:
        raw_text_output += f"[Pág {item['page']}] {item['text']}\n"
        
    return raw_text_output

# --- 5. FUNCIÓN DE INTELIGENCIA ARTIFICIAL (NUEVO MODELO) ---
def summarize_with_ai(raw_text):
    # Usamos el modelo Flash Lite más reciente
    model_name = 'gemini-flash-lite-latest'
    
    try:
        model = genai.GenerativeModel(model_name)
        
        # PROMPT DE INGENIERÍA MÉDICA
        prompt = f"""
        Actúa como un médico especialista en Medicina Interna con experiencia en edición de textos científicos. Procesa los siguientes fragmentos de texto extraídos de un PDF (que contienen ruido como números de página, palabras cortadas por guiones y saltos de línea abruptos) para generar un resumen profesional siguiendo estas reglas:

Limpieza y Unificación: Une las palabras cortadas por guiones (ej. 'sponta- neous' a 'spontaneous'), elimina las marcas de página (ej. '[Pág 1]') y corrige cualquier error de redacción derivado del escaneo.

Estructura Narrativa: No te limites a enlistar puntos. Crea una narrativa fluida dividida en secciones lógicas: 'Definición y Epidemiología', 'Fisiopatología', 'Diagnóstico Diferencial (especialmente síncope vs. epilepsia)' y 'Manejo/Tratamiento'.

Contenido Médico: Mantén intacta toda la terminología técnica, valores numéricos, umbrales de presión arterial, porcentajes y referencias a medicamentos (Midodrina, Fludrocortisona).

Sección de Puntos Clave: Al final, añade una lista de 'Puntos Clave' o 'Perlas Clínicas' que resuma lo más crítico para un algoritmo diagnóstico (como las 'Red Flags' o maniobras de contrapresión).

Tono: Profesional, directo y con rigor científico, similar a un manual de medicina tipo Harrison o UpToDate.

Texto a procesar:
        {raw_text}
        """
        
        # Configuración para reducir alucinaciones
        generation_config = genai.types.GenerationConfig(
            temperature=0.3, # Baja temperatura = más preciso/menos creativo
        )
        
        response = model.generate_content(prompt, generation_config=generation_config)
        return response.text
        
    except Exception as e:
        return f"Error técnico al conectar con Gemini: {str(e)}"

# --- 6. INTERFAZ DE USUARIO (UI) ---
st.title("🩺 Notas Inteligentes")
st.markdown("Sube tu PDF subrayado (Adobe/Preview) para generar un resumen de estudio instantáneo.")

uploaded_file = st.file_uploader("Arrastra tu PDF aquí (Máx 50MB)", type=["pdf"])

if uploaded_file:
    # Paso 1: Extracción Geométrica
    with st.spinner("Extrayendo tus subrayados..."):
        raw_text = get_pdf_text(uploaded_file)

    if raw_text:
        # Paso 2: Procesamiento Cognitivo (IA)
        with st.spinner("🧠 Gemini está organizando tus apuntes..."):
            resumen_final = summarize_with_ai(raw_text)
        
        # Verificación de errores
        if "Error técnico" in resumen_final:
            st.error(resumen_final)
        else:
            st.success("¡Resumen listo!")
            
            # Visualización
            st.markdown("---")
            st.markdown(resumen_final)
            st.markdown("---")
            
            # Botón de Descarga
            st.download_button(
                label="📥 Descargar Notas (.md)",
                data=resumen_final,
                file_name="memodi_notas.md",
                mime="text/markdown"
            )
    else:
        st.warning("⚠️ No detectamos texto subrayado. Asegúrate de que el PDF tenga capa de texto (no imagen) y uses la herramienta de Resaltar estándar.")
