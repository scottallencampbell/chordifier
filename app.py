from flask import Flask, abort, request, send_from_directory, render_template
app = Flask(__name__)

import api
import web

app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['UPLOAD_EXTENSIONS'] = ['.wav', '.mp3']
app.config['UPLOAD_FOLDER'] = './uploads'
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
app.config['MAX_CONTENT_LENGTH'] = 50 * 1000 * 1000

if __name__ == '__main__':
    app.run(host="localhost", port=5000, debug=True)