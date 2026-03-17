import streamlit as st
import base64
import requests
import json
import re

# --- CONFIGURATION INITIALE ---
st.set_page_config(page_title="Oclear - Vérification de Chèques", layout="wide", page_icon="🔍")

# --- INITIALISATION DE LA MÉMOIRE (SESSION STATE) ---
if "resultats_valides" not in st.session_state:
    st.session_state.resultats_valides = []
if "resultats_erreurs" not in st.session_state:
    st.session_state.resultats_erreurs = []
if "last_files_hash" not in st.session_state:
    st.session_state.last_files_hash = None

# --- FONCTIONS UTILES ---
def encode_image(file):
    return base64.b64encode(file.read()).decode('utf-8')

def clean_json(text):
    """Nettoie la réponse du modèle pour extraire uniquement le bloc JSON."""
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    text = text.replace("```json", "").replace("```", "").strip()
    return text

# --- INTERFACE SIDEBAR ---
st.sidebar.header("⚙️ Configuration Oclear")
server_url = st.sidebar.text_input("URL ngrok API", value="https://tu-ironfisted-unstrictly.ngrok-free.dev/v1/chat/completions")
model_name = st.sidebar.text_input("Nom du modèle", value="qwen/qwen3.5-9b")

if st.sidebar.button("🗑️ Vider l'historique"):
    st.session_state.resultats_valides = []
    st.session_state.resultats_erreurs = []
    st.rerun()

# --- INTERFACE PRINCIPALE ---
st.title("🔍 Oclear : Analyseur de Chèques")
st.caption("Solution intelligente de vérification bancaire | Par Obertys")

st.markdown("### 📤 Téléchargement des documents")
uploaded_files = st.file_uploader(
    "Déposez les scans de chèques ici (PNG, JPG, JPEG)", 
    type=['png', 'jpg', 'jpeg'], 
    accept_multiple_files=True
)

# LOGIQUE DE NETTOYAGE : Si la liste de fichiers change, on efface les résultats
current_files_hash = [f.name for f in uploaded_files] if uploaded_files else []
if current_files_hash != st.session_state.last_files_hash:
    st.session_state.resultats_valides = []
    st.session_state.resultats_erreurs = []
    st.session_state.last_files_hash = current_files_hash

# --- ACTIONS ---
if st.button("🚀 Lancer l'Analyse Oclear") and uploaded_files:
    st.session_state.resultats_valides = []
    st.session_state.resultats_erreurs = []
    
    headers = {
        "ngrok-skip-browser-warning": "69420",
        "Content-Type": "application/json"
    }

    with st.spinner("Oclear analyse vos documents en local..."):
        for file in uploaded_files:
            try:
                file.seek(0)
                base64_img = encode_image(file)
                
                payload = {
                    "model": model_name,
                    "messages": [
                        {
                            "role": "system", 
                            "content": "Tu es l'intelligence artificielle Oclear spécialisée en OCR bancaire. Réponds UNIQUEMENT en JSON."
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text", 
                                    "text": "Analyse ce chèque bancaire. Extrais : montant_chiffres, montant_lettres, date, beneficiaire, et verification (true si chiffres et lettres concordent)."
                                },
                                {
                                    "type": "image_url", 
                                    "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}
                                }
                            ]
                        }
                    ],
                    "temperature": 0
                }

                response = requests.post(server_url, json=payload, headers=headers, timeout=120)
                response.raise_for_status()
                
                raw_content = response.json()['choices'][0]['message']['content']
                data = json.loads(clean_json(raw_content))
                
                if data.get("verification") == True:
                    st.session_state.resultats_valides.append({"name": file.name, "data": data, "img": base64_img})
                else:
                    st.session_state.resultats_erreurs.append({"name": file.name, "data": data})
                    
            except Exception as e:
                st.error(f"Erreur Oclear sur {file.name} : {str(e)}")

# --- AFFICHAGE DES RÉSULTATS ---
if st.session_state.resultats_valides or st.session_state.resultats_erreurs:
    st.divider()
    col_ok, col_ko = st.columns(2)

    with col_ok:
        st.success(f"✅ Chèques Conformisés ({len(st.session_state.resultats_valides)})")
        for item in st.session_state.resultats_valides:
            with st.expander(f"Détails : {item['name']}"):
                st.json(item['data'])
                st.image(f"data:image/jpeg;base64,{item['img']}", use_container_width=True)

    with col_ko:
        st.error(f"❌ Alertes de conformité ({len(st.session_state.resultats_erreurs)})")
        for item in st.session_state.resultats_erreurs:
            with st.expander(f"⚠️ Anomalie détectée : {item['name']}"):
                st.json(item['data'])

st.sidebar.markdown("---")
st.sidebar.caption("© Obertys 2026 | Powered by Oclear AI")