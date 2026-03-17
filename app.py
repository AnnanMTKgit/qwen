import streamlit as st
import base64
import requests
import json
import re
import time
from text_to_num import text2num
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
  "montant_chiffres": "Valeur numérique du montant",
  "montant_lettres": "Texte exact écrit",
  "date": "JJ/MM/AAAA",
  "lieu": "VVille d'émission lié au pays d'origine du chèque",
  "beneficiaire": "Nom de la personne ou entreprise bénéficiaire",
  "Signature":"Présence ou absence de signature (Oui/Non)"
}

"""

def encode_image(file):
    return base64.b64encode(file.read()).decode('utf-8')
def extraire_nombre_pur(chaine):
    # \d correspond à n'importe quel chiffre (0-9)
    # [^\d] signifie "tout ce qui n'est PAS un chiffre"
    # On remplace tout ce qui n'est pas un chiffre par une chaîne vide ""
    nombre_nettoye = re.sub(r'[^\d]', '', chaine)
    
    # On convertit en entier si la chaîne n'est pas vide
    return int(nombre_nettoye) if nombre_nettoye else 0
def correct_mont(l): #nouveau
        f=[]
        i=0
        while i<len(l)-1:
            if (l[i] =='dix' and (l[i+1] in {'neuf','sept','huit'})) or (l[i] =='quatre'and l[i+1]=='vingt'):
                f.append(l[i]+'-'+l[i+1])
                i+=2
            else:
                f.append(l[i])
                i+=1
        if i==len(l)-1:
            f.append(l[i])
        return f
def conforme(montant_en_lettres,montant_en_chiffres):  #nouveau
    try:
        d=montant_en_lettres.lower().split()
        d=[i for i in d if i in [
        "zéro", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf", "dix",
        "onze", "douze", "treize", "quatorze", "quinze", "seize", "vingt", "trente", "quarante",
        "cinquante", "soixante", "quatre-vingt", "cent", "mille", "million", "milliard", "millions", "milliards", "cents"
    ]] 
        d=correct_mont(d)
        
        d=' '.join(d)
        d=text2num(d,'fr')
        
        if d==extraire_nombre_pur(montant_en_chiffres):
            return True
        else:
            return False
    except:
            
            return False

def clean_json(text):
    """Nettoie la réponse du modèle pour extraire uniquement le bloc JSON."""
    # Supprime les balises <think>...</think> si le modèle réfléchit à voix haute
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    # Supprime les blocs de code Markdown ```json ... ```
    text = text.replace("```json", "").replace("```", "").strip()
    return text

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Oclear- OCR Chèques", layout="wide", page_icon="🏦")

st.title("🏦 Système de Vérification de Chèques - Obertys")
st.sidebar.header("⚙️ Configuration Serveur")
server_url = st.sidebar.text_input("URL ngrok API", value=NGROK_URL)
model_name = st.sidebar.text_input("Nom du modèle (LM Studio)", value="qwen/qwen3.5-9b")

# --- MESSAGE D'AVERTISSEMENT ---
st.warning(f"⚠️ **Note importante :** Le traitement utilise les ressources locales de votre serveur. Pour garantir la stabilité du système et éviter tout plantage, merci de ne pas dépasser ** 10 chèques** pour le moment.")
st.markdown("### 📤 Téléchargement des scans")
uploaded_files = st.file_uploader("Glissez vos images de chèques ici", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)

if st.button("🔍 Lancer l'Analyse") and uploaded_files:
    valides = []
    invalides = []
    total_files = len(uploaded_files)
    progress_bar = st.progress(0)
    status_text = st.empty() # Espace vide pour le texte dynamique
    with st.spinner("Traitement en cours sur votre Mac distant..."):
        for i, file in enumerate(uploaded_files):
            percent_complete = int((i / total_files) * 100)
            progress_bar.progress(percent_complete)
            status_text.info(f"⏳ Traitement de l'image {i+1}/{total_files} : **{file.name}**")
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
                
                if conforme(data.get("montant_lettres"), data.get("montant_chiffres")) == True:
                    valides.append({"name": file.name, "image": file, "data": data})
                else:
                    invalides.append({"name": file.name,"image": file, "data": data})
                    
            except Exception as e:
                st.error(f"Erreur sur le fichier {file.name} : {str(e)}")
        
            # Fin du traitement
        progress_bar.progress(100)
        status_text.success(f"✅ Analyse terminée ! {total_files} images traitées.")
        time.sleep(1) # Petit délai pour laisser l'utilisateur voir le 100%
        status_text.empty() # On nettoie la barre
        progress_bar.empty()
    # --- AFFICHAGE DES RÉSULTATS ---
    st.divider()
    col_ok, col_ko = st.columns(2)

    with col_ok:
        st.success(f"✅ Chèques Conformes ({len(valides)})")
        for item in valides:
            with st.expander(f"Détails : {item['name']}"):
                st.image(item['image'], use_column_width=True)
                st.json(item['data'])

    with col_ko:
        st.error(f"❌ Erreurs ou Non-conformités ({len(invalides)})")
        for item in invalides:
            st.warning(f"Fichier : {item['name']}")
            st.image(item['image'], use_column_width=True)
            st.json(item['data'])

st.sidebar.markdown("---")
st.sidebar.caption("Oclear | 2026")