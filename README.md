# Traffic Sign Detection & ADAS

Ce projet fournit un système d’**aide à la conduite (ADAS)** avec :

- Détection de **panneaux de signalisation** via YOLOv8.
- Détection de **franchissement de ligne** (lane departure).
- Mesure de **distance avec capteur ultrason**.
- Interface **web Flask** pour :
  - Uploader des vidéos / images.
  - Lancer un flux type « Dash Cam ».
- Mode **ADAS temps réel** avec fenêtre OpenCV (`adas_pi.py`).
- Possibilité de **streamer la webcam d’un PC vers un Raspberry Pi**.

---

## 1. Structure du projet

- **`adas_pi.py`**  
  Script principal ADAS (caméra + lanes + panneaux + ultrason + TTS).
- **`main.py`**  
  Application Flask (interface web) pour upload et streaming.
- **`test.py`**  
  Petit serveur Flask qui diffuse la webcam du PC en MJPEG sur `/video`.
- **`static/models/best.pt`**  
  Modèle YOLO pour la détection des panneaux.
- **`static/coco.txt`** (ou équivalent)  
  Fichier texte avec la liste des classes YOLO.
- **`static/input/gvideo/`**, **`static/input/gphoto/`**  
  Dossiers d’entrée pour vidéos / photos uploadées.
- **`static/input/photo/`**  
  Dossier de sortie pour les images annotées (`dskjds.jpg`, etc.).

---

## 2. Installation

### 2.1. Prérequis

- Python 3.10+ (PC et/ou Raspberry Pi).
- Git (optionnel).
- Sur le Raspberry Pi :  
  - Caméra activée dans `raspi-config` (si caméra CSI).
  - Optionnel : `picamera2` si utilisation directe de la caméra Pi.

### 2.2. Création de l’environnement virtuel

Dans le dossier du projet (`traffic-sign-detection`) :

```bash
# Windows (PowerShell)
python -m venv .venv
.\.venv\Scripts\activate

# Raspberry Pi (Linux)
python3 -m venv .venv
source .venv/bin/activate
```

Installer les dépendances de base (adapter si tu as déjà un `requirements.txt`) :

```bash
pip install flask opencv-python ultralytics torch pyttsx3
```

Sur Raspberry Pi, si tu veux utiliser la **caméra CSI** via Picamera2 :

```bash
sudo apt-get update
sudo apt-get install -y python3-picamera2
```

Pour la synthèse vocale (optionnel, Pi) :

```bash
sudo apt-get install -y espeak-ng
```

---

## 3. `adas_pi.py` – ADAS temps réel

### 3.1. Fonctionnalités

- **Camera** (`Camera`):
  - Utilise soit :
    - `Picamera2` (caméra Pi) si `ADAS_USE_PICAMERA=1`.
    - `cv2.VideoCapture` :
      - Soit par **index** (0, 1, …).
      - Soit par **device/URL** (ex. `/dev/video20`, `rtsp://...`, `http://.../video`).
  - Sélection via `ADAS_CAM_DEVICE`.

- **LaneDetector** :
  - Détection de lignes de route (blanc / jaune) dans une région d’intérêt.
  - Détection de franchissement de ligne par rapport à deux “rectangles roues”.
  - Dessin :
    - Lignes de voie.
    - Rectangles des “roues”.
    - Message "Attention, franchissement de ligne" si sortie de voie.

- **SignDetector** :
  - Charge un modèle YOLO (`best.pt` par défaut).
  - Récupère les noms de classes depuis :
    - `model.names`, ou
    - un fichier de labels (`coco.txt`), ou
    - un mapping par défaut.
  - Transforme les labels en français lisibles (`_prettify_label`).
  - Affiche sur l’image :
    - Boîtes englobantes des panneaux.
    - Nom du panneau et score.
  - **TTS (pyttsx3)** :
    - Annonce vocale des panneaux et des alertes.
    - Si `pyttsx3` ou eSpeak ne sont pas disponibles, le TTS est désactivé proprement (message `[SignDetector] TTS désactivé ...`).

- **UltrasonicSensor** :
  - Lecture asynchrone d’un capteur ultrason via GPIO (ou simulation si pas de GPIO).
  - Commande d’un buzzer si l’obstacle est en-dessous d’un seuil (par défaut 10 cm).
  - Affichage de la distance sur l’overlay.

- **Overlay** :
  - Dessin simultané :
    - Lignes de voie.
    - Rectangles “roues” (verts/rouges si alerte).
    - Panneaux détectés (boîte + label + confiance).
    - Distance ultrason.
  - Persistance des panneaux quelques secondes (`sign_persist_sec`) pour que le texte reste lisible.

### 3.2. Variables d’environnement importantes

- `ADAS_DISPLAY` (par défaut `1`)  
  - `1` → affiche une fenêtre OpenCV `ADAS`.  
  - `0` → mode headless (pas de fenêtre).

- `ADAS_ANALYZE_INPUT`  
  - `0` → mode caméra temps réel.
  - `1` → mode “analyse offline” d’un dossier d’images (`static/input/gphoto` par défaut) avec export CSV.

- `ADAS_MODEL`  
  - Chemin du modèle YOLO (par défaut `static/models/best.pt`).

- `ADAS_LABELS`  
  - Chemin du fichier de labels (par défaut `static/models/coco.txt` si présent).

- `ADAS_USE_PICAMERA`  
  - `1` → tente d’utiliser `Picamera2` (caméra Pi).
  - `0` → utilise OpenCV (`cv2.VideoCapture`).

- `ADAS_CAM_DEVICE`  
  - Choix de la source vidéo OpenCV :
    - `"0"`, `"1"`… → index de caméra.
    - `"/dev/video20"`… → device spécifique sur Linux.
    - `"http://IP:PORT/video"` → flux réseau (ex. webcam du PC).

### 3.3. Lancement de base (PC)

```bash
.\.venv\Scripts\activate
$env:ADAS_DISPLAY="1"
$env:ADAS_ANALYZE_INPUT="0"
python adas_pi.py
```

---

## 4. `main.py` – Interface Web Flask

### 4.1. Fonctionnalités

- Page d’accueil `/` :
  - Bouton **Upload** pour une vidéo ou une image.
  - Bouton **Stream from your Dash Cam**.

- `/upload` (POST) :
  - Si fichier `.mp4` :
    - Sauvegarde dans `static/input/gvideo/`.
    - Ouvre la vidéo pour traitement (`gen_new`).
    - Lance `adas_pi.py` via `run_adas()`.
    - Redirige vers `/video_feed_signs` (flux vidéo traité).
  - Si fichier image (`.png`, `.jpeg`, `.jpg`) :
    - Sauvegarde dans `static/input/gphoto/`.
    - Appelle `gen_new2` pour détecter les panneaux sur l’image.
    - Lance `adas_pi.py` via `run_adas()`.
    - Redirige vers `/video_feed_sign` (page avec l’image annotée).

- `/video_feed_signs` :
  - Diffuse un flux MJPEG (vidéo + panneaux) pour la vidéo uploadée.

- `/camera_feed` :
  - Ne gère plus directement la caméra OpenCV.
  - Appelle `run_adas()` pour lancer `adas_pi.py` (mode temps réel).
  - Redirige vers `/`.

- `/video_feed_sign` :
  - Affiche l’image annotée après détection (`preview_photo.html`).

### 4.2. Fonction `run_adas()`

```python
def run_adas():
    """Lance le script adas_pi.py dans un processus séparé."""
    python_exe = sys.executable
    script_path = os.path.join(os.path.dirname(__file__), "adas_pi.py")
    env = os.environ.copy()
    env.setdefault("ADAS_DISPLAY", "1")
    env.setdefault("ADAS_ANALYZE_INPUT", "0")
    subprocess.Popen([python_exe, script_path], env=env)
```

- Lance `adas_pi.py` en arrière-plan avec le même Python que Flask.
- Utilise les variables d’environnement existantes (par ex. `ADAS_CAM_DEVICE`).

### 4.3. Lancement de l’interface Web

#### Sur PC (démo locale)

```bash
.\.venv\Scripts\activate
$env:ADAS_DISPLAY="1"
$env:ADAS_ANALYZE_INPUT="0"
python main.py
```

Puis ouvrir `http://127.0.0.1:5000/`.

#### Sur Raspberry Pi (usage réel)

```bash
source .venv/bin/activate

export ADAS_CAM_DEVICE="http://IP_DU_PC:5001/video"   # ou /dev/videoX ou autre
export ADAS_USE_PICAMERA="0"
export ADAS_DISPLAY="1"
export ADAS_ANALYZE_INPUT="0"

python main.py
```

---

## 5. `test.py` – Streaming de la webcam du PC vers le Pi

### 5.1. Rôle

- Lit la webcam du PC (`VideoCapture(0)`).
- Diffuse le flux sur `http://PC_IP:5001/video` au format MJPEG.
- Permet au Raspberry Pi de **consommer la webcam du PC comme source vidéo** via `ADAS_CAM_DEVICE`.

### 5.2. Lancement

Sur le **PC** :

```bash
.\.venv\Scripts\activate
python test.py
```

La console affiche par exemple :

```text
Running on http://127.0.0.1:5001
Running on http://10.17.140.241:5001
```

- Tester dans le navigateur du PC :

  `http://127.0.0.1:5001/video`

- Sur le Raspberry Pi, utiliser cette URL dans `ADAS_CAM_DEVICE` :

  ```bash
  export ADAS_CAM_DEVICE="http://10.17.140.241:5001/video"
  ```

---

## 6. Flux typiques d’utilisation

### 6.1. ADAS temps réel sur PC

1. Branche la caméra (webcam).
2. Dans le venv :

   ```bash
   $env:ADAS_DISPLAY="1"
   $env:ADAS_ANALYZE_INPUT="0"
   python adas_pi.py
   ```

3. Regarder la fenêtre `ADAS`.

### 6.2. ADAS temps réel sur Raspberry Pi avec caméra Pi ou USB

1. Configurer la variable caméra :
   - Caméra Pi via Picamera2 :

     ```bash
     export ADAS_USE_PICAMERA="1"
     ```

   - Webcam USB via /dev/videoX :

     ```bash
     export ADAS_USE_PICAMERA="0"
     export ADAS_CAM_DEVICE="/dev/video20"  # exemple
     ```

2. Lancer :

   ```bash
   export ADAS_DISPLAY="1"
   export ADAS_ANALYZE_INPUT="0"
   python adas_pi.py
   ```

### 6.3. Webcam du PC utilisée par le Pi

1. Sur le **PC**, lancer `test.py`.
2. Sur le **Pi**, définir :

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
  Si OpenCV a été installé en version *headless*, `cv2.imshow`/fenêtre `ADAS` ne fonctionnera pas.  
  Sur PC, préférer `opencv-python` (et pas `opencv-python-headless`).

- **TTS (pyttsx3)** :
  - Sur certaines plateformes (Pi sans eSpeak), le TTS est automatiquement désactivé.
  - Le reste du pipeline ADAS continue de fonctionner.

- **Serveurs Flask (`main.py`, `test.py`)** :
  - En mode développement, ne pas exposer directement sur Internet.
  - Pour une utilisation en production, utiliser un serveur WSGI adapté (gunicorn, uwsgi, etc.).

---

## 8. Personnalisation

- Modifier la durée d’affichage des panneaux :

  Dans `adas_pi.py` (dans `main()`):

  ```python
  sign_persist_sec = 1.5  # augmenter à 3.0, 5.0, etc.
  ```

- Modifier le seuil d’alerte ultrason :

  ```python
  ultra = UltrasonicSensor(alert_threshold_cm=10.0)
  ```

- Changer le modèle YOLO des panneaux :

  ```bash
  export ADAS_MODEL="static/models/ton_modele.pt"
  ```

---
#   T r a f f i c - S i g n - D e t e c t i o n - A D A S  
 