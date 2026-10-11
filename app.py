from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)
app.secret_key = 'clave_secreta_super_segura'

def get_db():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()
    db.execute('''
        CREATE TABLE IF NOT EXISTS carreras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lat_origen TEXT,
            lng_origen TEXT,
            destino TEXT,
            referencia TEXT,
            estado TEXT DEFAULT 'pendiente'
        )
    ''')
    db.commit()

init_db()

@app.route('/')
def index():
    return redirect(url_for('pasajero'))

@app.route('/pasajero')
def pasajero():
    return render_template('pasajero.html')

@app.route('/chofer')
def chofer():
    db = get_db()
    carreras = db.execute("SELECT * FROM carreras WHERE estado = 'pendiente'").fetchall()
    return render_template('chofer.html', carreras=carreras)

@app.route('/pedir_carrera', methods=['POST'])
def pedir_carrera():
    lat = request.form.get('latitud_origen')
    lng = request.form.get('longitud_origen')
    destino = request.form.get('destino')
    referencia = request.form.get('referencia', '')
    
    db = get_db()
    db.execute(
        "INSERT INTO carreras (lat_origen, lng_origen, destino, referencia, estado) VALUES (?, ?, ?, ?, 'pendiente')",
        (lat, lng, destino, referencia)
    )
    db.commit()
    
    return '''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <title>Solicitud Enviada</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body class="bg-light text-center mt-5">
        <div class="container" style="max-width: 500px;">
            <div class="alert alert-success p-4 shadow-sm">
                <h3>¡Solicitud enviada al chofer! 🏍️</h3>
                <p class="mb-3">Tu ubicación GPS y destino han sido transmitidos con éxito.</p>
                <a href="/pasajero" class="btn btn-primary w-100 mb-2">Pedir otro viaje</a>
                <a href="/chofer" class="btn btn-success w-100">Ver Panel de Chofer (Prueba)</a>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/aceptar_carrera/<int:id>')
def aceptar_carrera(id):
    db = get_db()
    db.execute("UPDATE carreras SET estado = 'aceptada' WHERE id = ?", (id,))
    db.commit()
    return redirect(url_for('chofer'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)
