import cv2
from flask import Flask, Response

app = Flask(__name__)

def gen_frames():
    cap = cv2.VideoCapture(0)  # webcam PC
    if not cap.isOpened():
        print("Impossible d'ouvrir la caméra")
        return
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/video')
def video():
    return Response(gen_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    # écoute sur toutes les interfaces, port 5001 par ex.
    app.run(host='0.0.0.0', port=5001, debug=False)