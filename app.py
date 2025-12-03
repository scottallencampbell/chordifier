import os
import json
from flask import Flask, abort, jsonify, request, redirect, Response, url_for, send_from_directory, render_template
from analyzer import analyze
from flask_cors import CORS
from werkzeug.utils import secure_filename
import dataclasses

class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        return super().default(o)

app = Flask(__name__)
CORS(app)  # Initialize CORS

app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['UPLOAD_EXTENSIONS'] = ['.wav', '.mp3']
# Use /tmp for serverless environments (Vercel), fallback to ./uploads for local
app.config['UPLOAD_FOLDER'] = os.environ.get('UPLOAD_FOLDER', '/tmp' if os.path.exists('/tmp') else './uploads')
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
app.config['MAX_CONTENT_LENGTH'] = 50 * 1000 * 1000

# Create upload directory if it doesn't exist
upload_folder = app.config['UPLOAD_FOLDER']
if not os.path.exists(upload_folder):
    os.makedirs(upload_folder, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in app.config['UPLOAD_EXTENSIONS'] 

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'icons/favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/upload', methods=['POST'])
def upload():    
    files = request.files    
    
    for item in files:        
        uploaded_file = files.get(item)  
        uploaded_file.filename = secure_filename(uploaded_file.filename)
        if uploaded_file.filename != '':            
            file_ext = os.path.splitext(uploaded_file.filename)[1]           
        if file_ext not in app.config['UPLOAD_EXTENSIONS']:            
            abort(400)         
        
        filename = os.path.join(app.config['UPLOAD_FOLDER'], uploaded_file.filename)
        uploaded_file.save(filename)
        return uploaded_file.filename

@app.route('/uploads/<path:path>')
def send_upload(path):
    return send_from_directory(app.config['UPLOAD_FOLDER'], path)

@app.route('/analyze', methods=['POST'])
def analyze_track():
    if len(request.files) == 0:
        return Response('No files were uploaded', status=400)

    if 'file' not in request.files:
        return Response('No file part was included', status=400)

    file = request.files['file']

    if file.filename == '':
        return Response('No filename was included', status=400)
        
    if not allowed_file(file.filename): 
        return Response('File type not allowed', status=400)

    filename = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
    file.save(filename)
            
    chords = analyze(filename)
    
    return jsonify(chords)

@app.route('/analyze/uploaded', methods=['POST'])
def analyze_track_already_uploaded():  
    
    data = json.loads(request.data)
    file = data.get("file", None)

    if file is None:
        return Response('No filename was included', status=400)
    
    filename = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file))        
    print(filename)
    chords = analyze(filename)

    return jsonify(chords)
    
if __name__ == '__main__':
    app.run()