from flask import Flask
app = Flask(__name__)

import web
import api

app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['UPLOAD_EXTENSIONS'] = ['.wav', '.mp3']
app.config['UPLOAD_FOLDER'] = './uploads'
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
app.config['MAX_CONTENT_LENGTH'] = 50 * 1000 * 1000

if __name__ == '__main__':
    app.run()