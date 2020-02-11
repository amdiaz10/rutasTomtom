
# A very simple Flask Hello World app for you to get started with...

from flask import Flask
from flask import render_template

app = Flask(__name__)

@app.route('/')
def hello_world():
    return ("OXXEOTime.html")

@app.route('/index/')
def index():
    return app.send_static_file('index.html')

@app.route('/ruta/<string:id>/')
def ruta(id):
    return render_template('ruta.html', num_ruta=id)
    #return 'Pagina para poner todas las rutas que se estan usando'