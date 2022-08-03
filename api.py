from __main__ import app
import json
import os
from flask import Flask, jsonify, request, redirect, Response, url_for
from analyzer import analyze
from flask_cors import CORS
from werkzeug.utils import secure_filename
import dataclasses

class EnhancedJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        return super().default(o)

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in app.config['UPLOAD_EXTENSIONS'] 

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
    file = data.get("file",None)

    if file is None:
        return Response('No filename was included', status=400)
    
    filename = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file))        
    chords = analyze(filename)
    
    return jsonify(chords)
    