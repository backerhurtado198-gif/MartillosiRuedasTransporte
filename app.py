from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'martillos_secreto_absoluto_2026'

def init_db():
    conn = sqlite3.connect('mototaxi.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS configuracion (clave TEXT PRIMARY KEY, valor TEXT)''')
    
    c.execute("SELECT valor FROM configuracion WHERE clave = 'admin_pin'")
    if not c.fetchone():
        c.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('admin_pin', '159715')")
        
    c.execute("SELECT valor FROM configuracion WHERE clave = 'tarifa_global'")
    if not c.fetchone():
        c.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('tarifa_global', '100.00')")
    
    c.execute('''CREATE TABLE IF NOT EXISTS drivers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        pin TEXT,
        unidad TEXT,
        padrino TEXT,
        ganancias_pendientes REAL DEFAULT 0.0,
        total_ganado REAL DEFAULT 0.0,
        saldo REAL DEFAULT 0.0
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS passengers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        cedula TEXT,
        telefono TEXT,
        usuario TEXT,
        pin TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS rides (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tipo TEXT,
        precio REAL DEFAULT 0.0,
        estado TEXT DEFAULT 'Pendiente',
        chofer TEXT,
        pasajero TEXT,
        comision REAL DEFAULT 0.0,
        padrino TEXT DEFAULT 'Ninguno',
        comision_padrino REAL DEFAULT 0.0
    )''')
    
    for col, col_type in [('ganancias_pendientes', 'REAL DEFAULT 0.0'), ('total_ganado', 'REAL DEFAULT 0.0'), ('padrino', 'TEXT'), ('saldo', 'REAL DEFAULT 0.0')]:
        try:
            c.execute(f"ALTER TABLE drivers ADD COLUMN {col} {col_type}")
        except:
            pass

    for col, col_type in [('cedula', 'TEXT'), ('telefono', 'TEXT'), ('usuario', 'TEXT'), ('pin', 'TEXT')]:
        try:
            c.execute(f"ALTER TABLE passengers ADD COLUMN {col} {col_type}")
        except:
            pass

    for col, col_type in [('origen_lat', 'TEXT'), ('origen_lng', 'TEXT'), ('destino_lat', 'TEXT'), ('destino_lng', 'TEXT')]:
        try:
            c.execute(f"ALTER TABLE rides ADD COLUMN {col} {col_type}")
        except:
            pass

    conn.commit()
    conn.close()

init_db()

def get_tarifa_global():
    try:
        conn = sqlite3.connect('mototaxi.db')
        c = conn.cursor()
        c.execute("SELECT valor FROM configuracion WHERE clave = 'tarifa_global'")
        row = c.fetchone()
        conn.close()
        return float(row[0]) if row and row[0] else 100.00
    except:
        return 100.00

@app.route('/')
def index():
    return redirect(url_for('login_page'))

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        pin = request.form.get('pin')
        if not pin:
            return redirect(url_for('login_page'))
        pin_str = str(pin).strip()
        
        conn = sqlite3.connect('mototaxi.db')
        c = conn.cursor()
        c.execute("SELECT valor FROM configuracion WHERE clave = 'admin_pin'")
        row = c.fetchone()
        admin_pin = row[0] if row and row[0] else '159715'
        
        if pin_str == admin_pin:
            session.clear()
            session['rol'] = 'admin'
            conn.close()
            return redirect(url_for('admin'))
        
        c.execute("SELECT id, name FROM drivers WHERE pin = ?", (pin_str,))
        driver = c.fetchone()
        conn.close()
        
        if driver:
            session.clear()
            session['rol'] = 'chofer'
            session['chofer_id'] = driver[0]
            session['chofer_nombre'] = driver[1]
            return redirect(url_for('chofer_panel'))
            
        return redirect(url_for('login_page'))
    return render_template('login.html')

@app.route('/login_pasajero', methods=['GET', 'POST'])
def login_pasajero():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        pin = request.form.get('pin')
        if not usuario or not pin:
            return redirect(url_for('login_pasajero'))
        
        conn = sqlite3.connect('mototaxi.db')
        c = conn.cursor()
        c.execute("SELECT id, name FROM passengers WHERE usuario = ? AND pin = ?", (str(usuario).strip(), str(pin).strip()))
        passenger = c.fetchone()
        conn.close()
        
        if passenger:
            session.clear()
            session['rol'] = 'pasajero'
            session['pasajero_id'] = passenger[0]
            session['pasajero_nombre'] = passenger[1]
            return redirect(url_for('pasajero_panel'))
        return redirect(url_for('login_pasajero'))
    return render_template('login_pasajero.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_page'))

@app.route('/admin')
def admin():
    if session.get('rol') != 'admin':
        return redirect(url_for('login_page'))
    
    conn = sqlite3.connect('mototaxi.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM passengers")
    passengers = c.fetchall()
    c.execute("SELECT * FROM drivers")
    drivers = c.fetchall()
    c.execute("SELECT * FROM rides")
    rides = c.fetchall()
    
    total_ventas = sum(r['precio'] for r in rides if r['estado'] in ['En Curso', 'Completada'])
    total_comision_sistema = sum(r['comision'] for r in rides if r['estado'] in ['En Curso', 'Completada'])
    total_comision_padrinos = sum(r['comision_padrino'] for r in rides if r['estado'] in ['En Curso', 'Completada'])
    saldo_deuda_choferes = sum(d['ganancias_pendientes'] for d in drivers)
    
    conn.close()
    tarifa_global = get_tarifa_global()
    return render_template('admin.html', passengers=passengers, drivers=drivers, rides=rides, 
                           tarifa_global=tarifa_global, 
                           total_ventas=round(total_ventas, 2), 
                           total_comision_sistema=round(total_comision_sistema, 2), 
                           total_comision_padrinos=round(total_comision_padrinos, 2), 
                           saldo_deuda_choferes=round(saldo_deuda_choferes, 2))

@app.route('/actualizar_tarifa', methods=['POST'])
def actualizar_tarifa():
    if session.get('rol') != 'admin':
        return redirect(url_for('login_page'))
    nueva_tarifa = request.form.get('tarifa_global')
    if nueva_tarifa:
        try:
            val = float(nueva_tarifa)
            conn = sqlite3.connect('mototaxi.db')
            c = conn.cursor()
            c.execute("INSERT OR REPLACE INTO configuracion (clave, valor) VALUES ('tarifa_global', ?)", (str(val),))
            conn.commit()
            conn.close()
        except ValueError:
            pass
    return redirect(url_for('admin'))

@app.route('/registrar_pasajero', methods=['POST'])
def registrar_pasajero_admin():
    if session.get('rol') != 'admin':
        return redirect(url_for('login_page'))
    name = request.form.get('name')
    cedula = request.form.get('cedula')
    telefono = request.form.get('telefono')
    usuario = request.form.get('usuario')
    pin = request.form.get('pin')
    
    if name and cedula and telefono and usuario and pin:
        conn = sqlite3.connect('mototaxi.db')
        c = conn.cursor()
        c.execute("INSERT INTO passengers (name, cedula, telefono, usuario, pin) VALUES (?, ?, ?, ?, ?)", 
                  (name, cedula, telefono, usuario, pin))
        conn.commit()
        conn.close()
    return redirect(url_for('admin'))

@app.route('/eliminar_pasajero/<int:pasajero_id>')
def eliminar_pasajero(pasajero_id):
    if session.get('rol') != 'admin':
        return redirect(url_for('login_page'))
    conn = sqlite3.connect('mototaxi.db')
    c = conn.cursor()
    c.execute("DELETE FROM passengers WHERE id = ?", (pasajero_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/registrar_chofer', methods=['POST'])
def registrar_chofer():
    if session.get('rol') != 'admin':
        return redirect(url_for('login_page'))
    name = request.form.get('name')
    pin = request.form.get('pin')
    unidad = request.form.get('unidad')
    padrino = request.form.get('padrino', 'Sin Padrino (Independiente)')
    if name and pin and unidad:
        conn = sqlite3.connect('mototaxi.db')
        c = conn.cursor()
        c.execute("INSERT INTO drivers (name, pin, unidad, padrino, ganancias_pendientes, total_ganado, saldo) VALUES (?, ?, ?, ?, 0.0, 0.0, 0.0)", 
                  (name, pin, unidad, padrino))
        conn.commit()
        conn.close()
    return redirect(url_for('admin'))

@app.route('/eliminar_chofer/<int:chofer_id>')
def eliminar_chofer(chofer_id):
    if session.get('rol') != 'admin':
        return redirect(url_for('login_page'))
    conn = sqlite3.connect('mototaxi.db')
    c = conn.cursor()
    c.execute("DELETE FROM drivers WHERE id = ?", (chofer_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/recargar_chofer/<int:chofer_id>', methods=['POST'])
def recargar_chofer(chofer_id):
    if session.get('rol') != 'admin':
        return redirect(url_for('login_page'))
    monto = request.form.get('monto')
    if monto:
        try:
            val = float(monto)
            conn = sqlite3.connect('mototaxi.db')
            c = conn.cursor()
            c.execute("UPDATE drivers SET saldo = saldo + ? WHERE id = ?", (val, chofer_id))
            conn.commit()
            conn.close()
        except ValueError:
            pass
    return redirect(url_for('admin'))

@app.route('/pagar_chofer/<int:chofer_id>')
def pagar_chofer(chofer_id):
    if session.get('rol') != 'admin':
        return redirect(url_for('login_page'))
    conn = sqlite3.connect('mototaxi.db')
    c = conn.cursor()
    c.execute("UPDATE drivers SET ganancias_pendientes = 0.0 WHERE id = ?", (chofer_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin'))

@app.route('/pasajero')
def pasajero_panel():
    if session.get('rol') != 'pasajero':
        return redirect(url_for('login_pasajero'))
    conn = sqlite3.connect('mototaxi.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM passengers WHERE id = ?", (session.get('pasajero_id'),))
    pasajero = c.fetchone()
    if not pasajero:
        conn.close()
        return redirect(url_for('logout'))
    
    c.execute("SELECT * FROM rides WHERE pasajero = ? ORDER BY id DESC", (pasajero['name'],))
    rides = c.fetchall()
    conn.close()
    
    tarifa_global = get_tarifa_global()
    return render_template('pasajero.html', pasajero=pasajero, rides=rides, tarifa_global=tarifa_global)

@app.route('/solicitar_carrera', methods=['POST'])
def solicitar_carrera():
    if session.get('rol') != 'pasajero':
        return redirect(url_for('login_pasajero'))
    
    pasajero_id = session.get('pasajero_id')
    precio = get_tarifa_global()
    
    conn = sqlite3.connect('mototaxi.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT name FROM passengers WHERE id = ?", (pasajero_id,))
    p = c.fetchone()
    
    if not p:
        conn.close()
        return redirect(url_for('pasajero_panel'))
    
    pasajero_nombre = p['name']
    tipo = request.form.get('tipo') or 'Moto-Taxi Standard'
    comision = round(precio * 0.15, 2)

    origen_lat = request.form.get('origen_lat', '')
    origen_lng = request.form.get('origen_lng', '')
    destino_lat = request.form.get('destino_lat', '')
    destino_lng = request.form.get('destino_lng', '')
    
    c.execute("""INSERT INTO rides 
                 (tipo, precio, estado, chofer, pasajero, comision, padrino, comision_padrino, origen_lat, origen_lng, destino_lat, destino_lng) 
                 VALUES (?, ?, 'Pendiente', 'Sin Asignar', ?, ?, 'Ninguno', 0.0, ?, ?, ?, ?)""",
              (tipo, precio, pasajero_nombre, comision, origen_lat, origen_lng, destino_lat, destino_lng))
    conn.commit()
    conn.close()
    return redirect(url_for('pasajero_panel'))

@app.route('/registro_pasajero', methods=['GET', 'POST'])
def registro_pasajero():
    if request.method == 'POST':
        name = request.form.get('name')
        cedula = request.form.get('cedula')
        telefono = request.form.get('telefono')
        usuario = request.form.get('usuario')
        pin = request.form.get('pin')
        
        if name and cedula and telefono and usuario and pin:
            conn = sqlite3.connect('mototaxi.db')
            c = conn.cursor()
            c.execute("SELECT id FROM passengers WHERE usuario = ? OR cedula = ?", (usuario.strip(), cedula.strip()))
            if not c.fetchone():
                c.execute("INSERT INTO passengers (name, cedula, telefono, usuario, pin) VALUES (?, ?, ?, ?, ?)", 
                          (name.strip(), cedula.strip(), telefono.strip(), usuario.strip(), pin.strip()))
                conn.commit()
            conn.close()
            return redirect(url_for('login_pasajero'))
    return render_template('registro_pasajero.html')

@app.route('/chofer')
def chofer_panel():
    if session.get('rol') != 'chofer':
        return redirect(url_for('login_page'))
    conn = sqlite3.connect('mototaxi.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM drivers WHERE id = ?", (session.get('chofer_id'),))
    chofer = c.fetchone()
    if not chofer:
        conn.close()
        return redirect(url_for('logout'))
    
    c.execute("SELECT * FROM rides WHERE estado = 'Pendiente' OR chofer = ? ORDER BY id DESC", (chofer['name'],))
    rides = c.fetchall()
    conn.close()
    return render_template('chofer.html', chofer=chofer, rides=rides)

@app.route('/aceptar_carrera/<int:ride_id>')
def aceptar_carrera(ride_id):
    if session.get('rol') != 'chofer':
        return redirect(url_for('login_page'))
    
    chofer_id = session.get('chofer_id')
    chofer_nombre = session.get('chofer_nombre')
    
    conn = sqlite3.connect('mototaxi.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT padrino FROM drivers WHERE id = ?", (chofer_id,))
    d = c.fetchone()
    padrino = d['padrino'] if d and d['padrino'] else 'Ninguno'
    
    c.execute("UPDATE rides SET estado = 'En Curso', chofer = ?, padrino = ? WHERE id = ? AND estado = 'Pendiente'", 
              (chofer_nombre, padrino, ride_id))
    conn.commit()
    conn.close()
    return redirect(url_for('chofer_panel'))

@app.route('/completar_carrera/<int:ride_id>')
def completar_carrera(ride_id):
    if session.get('rol') != 'chofer':
        return redirect(url_for('login_page'))
    
    chofer_id = session.get('chofer_id')
    chofer_nombre = session.get('chofer_nombre')
    
    conn = sqlite3.connect('mototaxi.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM rides WHERE id = ? AND chofer = ? AND estado = 'En Curso'", (ride_id, chofer_nombre))
    ride = c.fetchone()
    
    if ride:
        precio = ride['precio']
        comision_sistema = round(precio * 0.15, 2)
        padrino = ride['padrino']
        comision_padrino = round(precio * 0.03, 2) if padrino and padrino not in ['Ninguno', 'Sin Padrino (Independiente)'] else 0.0
        
        ganancia_chofer = round(precio - comision_sistema, 2)
        
        c.execute("UPDATE rides SET estado = 'Completada', comision = ?, comision_padrino = ? WHERE id = ?", 
                  (comision_sistema, comision_padrino, ride_id))
        
        c.execute("UPDATE drivers SET ganancias_pendientes = ganancias_pendientes + ?, total_ganado = total_ganado + ? WHERE id = ?",
                  (ganancia_chofer, ganancia_chofer, chofer_id))
        conn.commit()
    conn.close()
    return redirect(url_for('chofer_panel'))

if __name__ == '__main__':
    app.run(debug=True, port=5000)


@app.route('/padrino_dashboard/<int:padrino_id>')
def padrino_dashboard(padrino_id):
    try:
        conexion = sqlite3.connect('mototaxi.db')
        conexion.row_factory = sqlite3.Row
        cursor = conexion.cursor()
        
        # Buscar padrino
        cursor.execute("SELECT * FROM usuarios WHERE id = ?", (padrino_id,))
        padrino = cursor.fetchone()
        
        if not padrino:
            conexion.close()
            return "Padrino no encontrado", 404
            
        codigo = dict(padrino).get('codigo_referido') or f"MYR-{padrino['id']}"
        
        # Buscar ahijados
        cursor.execute("SELECT * FROM usuarios WHERE referido_por = ?", (codigo,))
        ahijados_db = cursor.fetchall()
        
        ahijados = []
        total_ganancias = 0.0
        for a in ahijados_db:
            a_dict = dict(a)
            nombre = a_dict.get('name') or a_dict.get('usuario') or 'Usuario'
            tipo = a_dict.get('tipo_cuenta') or 'General'
            
            # Calcular 3% de comisiones si existe tabla carreras
            comision = 0.0
            ahijados.append({
                "name": nombre,
                "tipo_cuenta": tipo,
                "comision_generada": comision
            })
            
        conexion.close()
        return render_template('padrino_dashboard.html', padrino=padrino, ahijados=ahijados, total_ganancias=total_ganancias)
    except Exception as e:
        return f"Error en panel de padrino: {str(e)}"
