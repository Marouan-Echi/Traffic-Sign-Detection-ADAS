# Traffic Sign Detection & ADAS

Ce projet fournit un système d’**aide à la conduite (ADAS)** pour la détection et l’alerte sur les panneaux de signalisation, le franchissement de ligne, et la distance avec capteurs ultrasoniques. Il combine des technologies de vision par ordinateur (YOLOv8), un capteur ultrason, et une interface web Flask pour un système complet d’assistance en temps réel.

---

## 1. Structure du projet

- **`adas_pi.py`**  
  Script principal ADAS (caméra + détection de voies, panneaux, ultrason, synthèse vocale).
- **`main.py`**  
  Application Flask pour interface web (upload et streaming).
- **`test.py`**  
  Serveur Flask diffusant la webcam du PC en MJPEG sur `/video`.
- **`static/models/best.pt`**  
  Modèle YOLOv8 entraîné pour la détection des panneaux.
- **`static/coco.txt`** (ou équivalent)  
  Liste des classes YOLO pour la détection.
- **`static/input/gvideo/`**, **`static/input/gphoto/`**  
  Dossiers d’entrée pour vidéos et photos uploadées.
- **`static/input/photo/`**  
  Dossier de sortie pour images annotées.

---

## 2. Installation & Prérequis

### 2.1. Prérequis

- Python 3.10+ (PC ou Raspberry Pi).
- Git (optionnel).
- Sur Raspberry Pi :  
  - Caméra activée dans `raspi-config` (pour caméra CSI).  
  - Optionnel : `picamera2` pour la caméra Pi.

### 2.2. Création de l’environnement virtuel

Dans le dossier du projet (`traffic-sign-detection`) :

```bash
# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\activate

# Raspberry Pi (Linux)
python3 -m venv .venv
source .venv/bin/activate
```

Installer les dépendances de base (adapter si `requirements.txt` existe) :

```bash
pip install flask opencv-python ultralytics torch pyttsx3
```

### 2.3. Installation spécifique Raspberry Pi

Pour utiliser la caméra CSI avec Picamera2 :

```bash
sudo apt-get update
sudo apt-get install -y python3-picamera2
```

Pour la synthèse vocale (optionnel) :

```bash
sudo apt-get install -y espeak-ng
```

---

## 3. `adas_pi.py` – ADAS temps réel

### 3.1. Fonctionnalités principales

- **Camera** (`Camera`) :  
  - Utilise `Picamera2` si `ADAS_USE_PICAMERA=1`.  
  - Sinon `cv2.VideoCapture` (index, device, URL).  
  - Choix via variable `ADAS_CAM_DEVICE`.

- **LaneDetector** :  
  - Détecte les lignes blanches/jaunes dans une zone définie.  
  - Détection de franchissement de ligne selon la position des roues.  
  - Affiche lignes et messages d’alerte.

- **SignDetector** :  
  - Utilise modèle YOLO (`best.pt` par défaut).  
  - Labels récupérés via modèle, fichiers ou mapping par défaut.  
  - Affiche boîtes, labels et scores sur image.  
  - Synthèse vocale (TTS) avec pyttsx3 si disponible.

- **UltrasonicSensor** :  
  - Lecture asynchrone d’un capteur ultrason via GPIO (ou simulation).  
  - Buzzer si obstacle trop proche (seuil par défaut 10 cm).  
  - Affiche la distance en overlay.

- **Overlay** :  
  - Superpose voies, “roues”, panneaux, distance, alertes.  
  - Persistance des panneaux quelques secondes.

### 3.2. Variables d’environnement importantes

- `ADAS_DISPLAY` (par défaut `1`) :  
  - `1` = affiche fenêtre OpenCV `ADAS`  
  - `0` = mode headless

- `ADAS_ANALYZE_INPUT` :  
  - `0` = caméra temps réel  
  - `1` = analyse offline dossier images

- `ADAS_MODEL` : chemin du modèle YOLO (par défaut `static/models/best.pt`).

- `ADAS_LABELS` : chemin fichier labels (par défaut `static/models/coco.txt`).

- `ADAS_USE_PICAMERA` :  
  - `1` = `Picamera2`  
  - `0` = OpenCV `VideoCapture`.

- `ADAS_CAM_DEVICE` : source vidéo OpenCV (index, device Linux, URL).

### 3.3. Exemple de lancement (PC)

```bash
.\.venv\Scripts\activate
$env:ADAS_DISPLAY="1"
$env:ADAS_ANALYZE_INPUT="0"
python adas_pi.py
```

---

## 4. `main.py` – Interface Web Flask

### 4.1. Fonctionnalités

- Page d’accueil `/` avec boutons **Upload** et **Stream from your Dash Cam**.

- Endpoint `/upload` (POST) :  
  - `.mp4` → sauvegarde dans `static/input/gvideo/`, traitement, lancement `adas_pi.py`, redirection vers flux vidéo traitée.  
  - Image → sauvegarde dans `static/input/gphoto/`, détection panneaux, lancement `adas_pi.py`, redirection vers image annotée.

- `/video_feed_signs` : flux MJPEG vidéo + panneaux.

- `/camera_feed` : lance `adas_pi.py` en mode temps réel.

- `/video_feed_sign` : affiche image annotée.

### 4.2. Fonction `run_adas()`

```python
def run_adas():
    """Lance adas_pi.py en processus séparé."""
    python_exe = sys.executable
    script_path = os.path.join(os.path.dirname(__file__), "adas_pi.py")
    env = os.environ.copy()
    env.setdefault("ADAS_DISPLAY", "1")
    env.setdefault("ADAS_ANALYZE_INPUT", "0")
    subprocess.Popen([python_exe, script_path], env=env)
```

### 4.3. Exemple de lancement Web (PC)

```bash
.\.venv\Scripts\activate
$env:ADAS_DISPLAY="1"
$env:ADAS_ANALYZE_INPUT="0"
python main.py
```

Puis ouvrir `http://127.0.0.1:5000/`.

---

## 5. `test.py` – Streaming webcam PC vers Raspberry Pi

### 5.1. Rôle

- Lit webcam PC (`VideoCapture(0)`).
- Diffuse flux MJPEG sur `http://PC_IP:5001/video`.
- Permet Pi d’utiliser webcam PC comme source vidéo.

### 5.2. Lancement

Sur PC :

```bash
.\.venv\Scripts\activate
python test.py
```

Console affiche les URLs disponibles. Utiliser dans `ADAS_CAM_DEVICE` sur Pi.

---

## 6. Flux typiques d’utilisation

### 6.1. ADAS temps réel sur PC

1. Brancher la caméra (webcam).
2. Activer venv.
3. Set variables:

```bash
$env:ADAS_DISPLAY="1"
$env:ADAS_ANALYZE_INPUT="0"
python adas_pi.py
```

4. Regarder la fenêtre `ADAS`.

### 6.2. ADAS temps réel sur Raspberry Pi

- Configurer caméra Pi ou USB :

```bash
export ADAS_USE_PICAMERA="1"
# ou pour caméra USB
export ADAS_USE_PICAMERA="0"
export ADAS_CAM_DEVICE="/dev/video20"
```

- Lancer :

```bash
export ADAS_DISPLAY="1"
export ADAS_ANALYZE_INPUT="0"
python adas_pi.py
```

### 6.3. Webcam PC utilisée par Pi

1. Sur PC, lancer `test.py`.
2. Sur Pi, configurer variables :

```bash
export ADAS_CAM_DEVICE="http://IP_DU_PC:5001/video"
export ADAS_USE_PICAMERA="0"
export ADAS_DISPLAY="1"
export ADAS_ANALYZE_INPUT="0"
python adas_pi.py
```

---

## 7. Remarques et limitations

- **OpenCV headless** :  
  Pas de fenêtre `cv2.imshow` si version headless installée.

- **TTS (pyttsx3)** :  
  Désactivé si eSpeak non disponible, sans impact sur pipeline.

- **Serveurs Flask (`main.py`, `test.py`)** :  
  Ne pas exposer en prod sans serveur WSGI adapté.

---

## 8. Personnalisation

- Durée d’affichage des panneaux :

```python
sign_persist_sec = 1.5  # augmenter selon besoin
```

- Seuil alerte ultrason :

```python
ultra = UltrasonicSensor(alert_threshold_cm=10.0)
```

- Changer modèle YOLO :

```bash
export ADAS_MODEL="static/models/ton_modele.pt"
