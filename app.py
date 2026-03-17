import streamlit as st
import base64
import requests
import json
import re

# --- CONFIGURATION DU TUNNEL ---
# Utilisez l'URL ngrok que vous avez validée avec curl
NGROK_URL = "https://tu-ironfisted-unstrictly.ngrok-free.dev/v1/chat/completions"

# Headers pour bypasser l'avertissement ngrok et définir le format JSON
HEADERS = {
    "ngrok-skip-browser-warning": "69420",
    "Content-Type": "application/json"
}

# --- PROMPTS EXPERTS ---
PROMPT_SYSTEM = """Tu es un assistant expert en analyse de documents bancaires. 
Ton rôle est d'extraire les données avec une précision chirurgicale.
Réponds UNIQUEMENT par un objet JSON valide. Ne fournis aucune explication ni pensée interne."""

PROMPT_USER = """Analyse l'image de ce chèque et extrais rigoureusement les informations suivantes :

### FORMAT DE SORTIE (JSON UNIQUEMENT) :
{
  "montant_chiffres": 0.0,
  "montant_lettres": "Texte exact écrit",
  "date": "JJ/MM/AAAA",
  "lieu": "Ville d'émission",
  "beneficiaire": "Nom du bénéficiaire",
  "verification": true
}

Note : 'verification' est True si 'montant_chiffres' est strictement égal au 'montant_lettres' converti. 
Si une donnée est illisible, écris null."""

def encode_image(file):
    return base64.b64encode(file.read()).decode('utf-8')

def clean_json(text):
    """Nettoie la réponse du modèle pour extraire uniquement le bloc JSON."""
    # Supprime les balises <think>...</think> si le modèle réfléchit à voix haute
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    # Supprime les blocs de code Markdown ```json ... ```
    text = text.replace("```json", "").replace("```", "").strip()
    return text

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Boutique Ba - OCR Chèques", layout="wide", page_icon="🏦")

st.title("🏦 Système de Vérification de Chèques - Obertys")
st.sidebar.header("⚙️ Configuration Serveur")
server_url = st.sidebar.text_input("URL ngrok API", value=NGROK_URL)
model_name = st.sidebar.text_input("Nom du modèle (LM Studio)", value="qwen/qwen3.5-9b")

st.markdown("### 📤 Téléchargement des scans")
uploaded_files = st.file_uploader("Glissez vos images de chèques ici", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

if st.button("🔍 Lancer l'Analyse") and uploaded_files:
    valides = []
    invalides = []
    
    with st.spinner("Traitement en cours sur votre Mac distant..."):
        for file in uploaded_files:
            try:
                base64_img = encode_image(file)
                
                payload = {
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": PROMPT_SYSTEM},
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": PROMPT_USER},
                                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
                            ]
                        }
                    ],
                    "temperature": 0
                }

                response = requests.post(server_url, json=payload, headers=HEADERS, timeout=120)
                response.raise_for_status()
                
                raw_content = response.json()['choices'][0]['message']['content']
                json_str = clean_json(raw_content)
                data = json.loads(json_str)
                
                if data.get("verification") == True:
                    valides.append({"name": file.name, "image": file, "data": data})
                else:
                    invalides.append({"name": file.name, "data": data})
                    
            except Exception as e:
                st.error(f"Erreur sur le fichier {file.name} : {str(e)}")

    # --- AFFICHAGE DES RÉSULTATS ---
    st.divider()
    col_ok, col_ko = st.columns(2)

    with col_ok:
        st.success(f"✅ Chèques Conformes ({len(valides)})")
        for item in valides:
            with st.expander(f"Détails : {item['name']}"):
                st.image(item['image'], use_container_width=True)
                st.json(item['data'])

    with col_ko:
        st.error(f"❌ Erreurs ou Non-conformités ({len(invalides)})")
        for item in invalides:
            st.warning(f"Fichier : {item['name']}")
            st.json(item['data'])

st.sidebar.markdown("---")
st.sidebar.caption("Oclear | 2026")