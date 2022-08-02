from __main__ import app
import os
from werkzeug.utils import secure_filename
from flask import Flask, abort, request, send_from_directory, render_template

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'icons/favicon.ico', mimetype='image/vnd.microsoft.icon')

def home():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():    
    files = request.files    
    formData = request.files['file']     
    
    for item in files:        
        uploaded_file = files.get(item)  
        uploaded_file.filename = secure_filename(uploaded_file.filename)
        if uploaded_file.filename != '':            
            file_ext = os.path.splitext(uploaded_file.filename)[1]           
        if file_ext not in app.config['UPLOAD_EXTENSIONS']:            
            abort(400)         
        
        filename = os.path.join(app.config['UPLOAD_FOLDER'], uploaded_file.filename)
        uploaded_file.save(filename)

        return ''

@app.route('/uploads/<path:path>')
def send_upload(path):
    return send_from_directory('uploads', path)
