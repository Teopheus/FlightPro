import os
import sys
import sqlite3
import io
import base64
import json
import locale
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from PIL import Image, ImageDraw, ImageFont
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'segredo_super_secreto_flight_manager'

# --- LOGIN ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- CONFIGURAÇÕES DE CAMINHO ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "database.db")
IMAGE_FOLDER = os.path.join(BASE_DIR, 'static', 'generated')
TEMPLATES_FOLDER = os.path.join(BASE_DIR, 'static', 'templates')
DEFAULT_TEMPLATE_PATH = os.path.join(BASE_DIR, 'static', 'template_fundo.png') 

FONT_BOLD_PATH = os.path.join(BASE_DIR, 'static', 'fonts', 'Montserrat-Bold.ttf')
FONT_REGULAR_PATH = os.path.join(BASE_DIR, 'static', 'fonts', 'Montserrat-Regular.ttf')

os.makedirs(IMAGE_FOLDER, exist_ok=True)
os.makedirs(TEMPLATES_FOLDER, exist_ok=True)

try: locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except: 
    try: locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil')
    except: pass

# --- CLASSES ---
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = str(id); self.username = username; self.password = password

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    data = cursor.fetchone(); conn.close()
    if data: return User(id=data[0], username=data[1], password=data[2])
    return None

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            origin TEXT, destination TEXT, operator TEXT, flight_type TEXT,
            search_date TEXT, image_path TEXT, 
            program_1 TEXT, cost_1 TEXT, dates_1 TEXT, 
            program_2 TEXT, cost_2 TEXT, dates_2 TEXT, 
            origin_2 TEXT, destination_2 TEXT,
            available_dates TEXT,
            prices_json_1 TEXT, prices_json_2 TEXT,
            miles_qty_1 TEXT, prog_id_1 INTEGER, tax_val_1 TEXT, curr_id_1 INTEGER,
            miles_qty_2 TEXT, prog_id_2 INTEGER, tax_val_2 TEXT, curr_id_2 INTEGER,
            selected_bg TEXT
        )
    ''')
    
    cursor.execute("PRAGMA table_info(searches)")
    cols = [info[1] for info in cursor.fetchall()]
    new_cols = [
        ('prices_json_1', 'TEXT'), ('prices_json_2', 'TEXT'),
        ('miles_qty_1', 'TEXT'), ('prog_id_1', 'INTEGER'), ('tax_val_1', 'TEXT'), ('curr_id_1', 'INTEGER'),
        ('miles_qty_2', 'TEXT'), ('prog_id_2', 'INTEGER'), ('tax_val_2', 'TEXT'), ('curr_id_2', 'INTEGER'),
        ('selected_bg', 'TEXT')
    ]
    for cname, ctype in new_cols:
        if cname not in cols:
            try: cursor.execute(f"ALTER TABLE searches ADD COLUMN {cname} {ctype}")
            except: pass

    cursor.execute('''CREATE TABLE IF NOT EXISTS programs (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS currencies (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT)''')
    
    cursor.execute("SELECT count(*) FROM programs")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO programs (name) VALUES (?)", [('Latam Pass',), ('Smiles',), ('AAdvantage',), ('KrissFlyer',), ('TAP Miles&Go',), ('Iberia Plus',), ('Privilege Club',)])
    
    cursor.execute("SELECT count(*) FROM currencies")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO currencies (code) VALUES (?)", [('R$',), ('USD',), ('EUR',), ('£',)])

    cursor.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT)''')
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('admin', generate_password_hash('admin123')))
    
    conn.commit(); conn.close()

# --- HELPER: PROCESSAR PREÇOS ---
def process_prices(prefix, form, conn):
    miles_list = form.getlist(f'miles_{prefix}[]')
    prog_list = form.getlist(f'prog_{prefix}[]')
    curr_list = form.getlist(f'curr_{prefix}[]')
    tax_list = form.getlist(f'tax_{prefix}[]')
    
    prices_data = []
    text_lines = []
    
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM programs")
    progs_map = {str(r[0]): r[1] for r in cursor.fetchall()}
    cursor.execute("SELECT id, code FROM currencies")
    currs_map = {str(r[0]): r[1] for r in cursor.fetchall()}
    
    for i in range(len(miles_list)):
        m = miles_list[i]
        if not m: continue
        p_id = prog_list[i] if i < len(prog_list) else ""
        c_id = curr_list[i] if i < len(curr_list) else ""
        t = tax_list[i] if i < len(tax_list) else ""
        
        prices_data.append({'miles': m, 'prog_id': p_id, 'curr_id': c_id, 'tax': t})
        
        p_name = progs_map.get(p_id, "")
        c_code = currs_map.get(c_id, "")
        try: m_fmt = "{:,.0f}".format(float(m)).replace(',', '.')
        except: m_fmt = m
            
        line = f"{m_fmt} {p_name}"
        if t: line += f" + {c_code} {t}"
        text_lines.append(line)
        
    full_text = "\nOU\n".join(text_lines)
    return json.dumps(prices_data), full_text

# --- MOTOR GRÁFICO (COM TEMAS DE COR) ---
def create_image_object(data):
    bg_name = data.get('selected_bg')
    bg_path = DEFAULT_TEMPLATE_PATH
    
    if bg_name:
        possible_path = os.path.join(TEMPLATES_FOLDER, bg_name)
        if os.path.exists(possible_path):
            bg_path = possible_path
    
    try:
        img = Image.open(bg_path).convert("RGBA")
        if img.size != (1080, 1080): img = img.resize((1080, 1080))
    except FileNotFoundError:
        img = Image.new('RGBA', (1080, 1080), color=(255, 255, 255, 255))

    draw = ImageDraw.Draw(img)

    # --- CONFIGURAÇÃO DE CORES (TEMAS) ---
    # Defina aqui as cores para cada arquivo de background
    THEMES = {
        'first_class.png': {
            'header': '#d4af37',  # Dourado (Exemplo)
            'route':  '#d4af37',  # Dourado
            'text':   '#ffffff',  # Branco (para fundo escuro)
            'footer': '#d4af37'   # Dourado
        },
        'executiva_milhas.png': {
            'header': '#0054a6',  # Azul Padrão
            'route':  '#0054a6',
            'text':   '#222222',  # Preto
            'footer': '#ffffff'   # Branco (texto sobre barra azul)
        },
        # Caso o arquivo não esteja na lista, usa este padrão:
        'default': {
            'header': '#0054a6', 
            'route':  '#0054a6', 
            'text':   '#222222',
            'footer': '#ffffff'
        }
    }

    # Seleciona o tema baseado no nome do arquivo (ou usa default)
    theme = THEMES.get(bg_name, THEMES['default'])
    
    c_header = theme['header']
    c_route  = theme['route']
    c_text   = theme['text']
    c_footer = theme['footer']

    def load_font(path, size):
        try: return ImageFont.truetype(path, size)
        except: return ImageFont.load_default()

    font_airline = load_font(FONT_REGULAR_PATH, 40)
    font_route = load_font(FONT_BOLD_PATH, 50)
    font_offer_title = load_font(FONT_BOLD_PATH, 22)
    font_dates = load_font(FONT_BOLD_PATH, 20)
    font_footer_reg = load_font(FONT_REGULAR_PATH, 20)
    
    MARGIN_X, MARGIN_TOP = 70, 50

    flight_type = (data.get('flight_type') or "").upper()
    operator = (data.get('operator') or "").upper()
    origin = (data.get('origin') or "")
    dest = (data.get('destination') or "")

    # USANDO AS CORES DO TEMA
    cursor_y = MARGIN_TOP
    draw.text((MARGIN_X, cursor_y), f"{flight_type} {operator}", fill=c_header, font=font_airline)
    cursor_y += 50
    draw.text((MARGIN_X, cursor_y), f"{origin} - {dest}", fill=c_route, font=font_route)
    cursor_y += 110

    def draw_text_block(start_y, title_rota, prog_txt, cost_txt, dates_txt):
        curr_y = start_y
        if title_rota:
            draw.text((MARGIN_X, curr_y), title_rota, fill=c_route, font=font_route)
            curr_y += 80

        progs = [p.strip() for p in (prog_txt or "").split('\n') if p.strip()]
        if not progs:
            if cost_txt:
                draw.text((MARGIN_X, curr_y), f"Investimento: {cost_txt}", fill=c_text, font=font_offer_title)
                curr_y += 60
        else:
            for i, p in enumerate(progs):
                full_offer_text = p
                if i == 0 and cost_txt: full_offer_text += f" + {cost_txt}"
                draw.text((MARGIN_X, curr_y), full_offer_text, fill=c_text, font=font_offer_title)
                curr_y += 55 

        curr_y += 15 
        d_lines = (dates_txt or "").split('\n')
        for l in d_lines:
            if l.strip():
                draw.text((MARGIN_X, curr_y), l.strip().upper(), fill=c_text, font=font_dates)
                curr_y += 40 
        return curr_y + 60 

    cursor_y = draw_text_block(cursor_y, None, data.get('program_1'), data.get('cost_1'), data.get('dates_1'))
    
    orig2, dest2 = data.get('origin_2'), data.get('destination_2')
    has_data2 = data.get('program_2') or data.get('dates_2')
    title_2 = f"{orig2} - {dest2}" if (orig2 and dest2) else None

    if (title_2 or has_data2) and cursor_y < 850:
        cursor_y = draw_text_block(cursor_y, title_2, data.get('program_2'), data.get('cost_2'), data.get('dates_2'))

    if data.get('search_date'):
        footer_y_start = 1080 - 150 
        text_y = footer_y_start + 100 
        try:
            d = datetime.strptime(data.get('search_date'), '%Y-%m-%d')
            meses = {1:'Janeiro', 2:'Fevereiro', 3:'Março', 4:'Abril', 5:'Maio', 6:'Junho', 7:'Julho', 8:'Agosto', 9:'Setembro', 10:'Outubro', 11:'Novembro', 12:'Dezembro'}
            dt_str = f"Atualizado: {d.day} de {meses.get(d.month, d.month)}"
            draw.text((MARGIN_X, text_y), dt_str, fill=c_footer, font=font_footer_reg)
        except: pass

    return img.convert("RGB")

# --- HELPER: LISTAR TEMPLATES ---
def get_available_templates():
    files = []
    if os.path.exists(TEMPLATES_FOLDER):
        files = [f for f in os.listdir(TEMPLATES_FOLDER) if f.lower().endswith('.png')]
    return sorted(files)

# --- ROTAS ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form['username']
        pwd = request.form['password']
        conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (user,))
        ud = cursor.fetchone(); conn.close()
        if ud and check_password_hash(ud[2], pwd):
            login_user(User(id=ud[0], username=ud[1], password=ud[2]))
            return redirect(url_for('dashboard'))
        flash('Credenciais inválidas', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout(): logout_user(); return redirect(url_for('login'))

@app.route('/')
def index(): return redirect(url_for('dashboard' if current_user.is_authenticated else 'login'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = sqlite3.connect(DB_NAME); conn.row_factory = sqlite3.Row; cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as t FROM searches")
    total = cursor.fetchone()['t']
    cursor.execute("SELECT destination, COUNT(*) as c FROM searches GROUP BY destination ORDER BY c DESC LIMIT 5")
    dest_rows = cursor.fetchall(); conn.close()
    return render_template('dashboard.html', total_searches=total, dest_labels=[r['destination'] for r in dest_rows], dest_data=[r['c'] for r in dest_rows])

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    conn = sqlite3.connect(DB_NAME); conn.row_factory = sqlite3.Row; cursor = conn.cursor()
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_program':
            cursor.execute("INSERT INTO programs (name) VALUES (?)", (request.form['name'],))
        elif action == 'delete_program':
            cursor.execute("DELETE FROM programs WHERE id = ?", (request.form['id'],))
        elif action == 'add_currency':
            cursor.execute("INSERT INTO currencies (code) VALUES (?)", (request.form['code'],))
        elif action == 'delete_currency':
            cursor.execute("DELETE FROM currencies WHERE id = ?", (request.form['id'],))
        conn.commit()
        return redirect(url_for('settings'))
    cursor.execute("SELECT * FROM programs ORDER BY name")
    programs = cursor.fetchall()
    cursor.execute("SELECT * FROM currencies ORDER BY id")
    currencies = cursor.fetchall()
    conn.close()
    return render_template('settings.html', programs=programs, currencies=currencies)

@app.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    conn = sqlite3.connect(DB_NAME); conn.row_factory = sqlite3.Row; cursor = conn.cursor()
    
    if request.method == 'POST':
        json_1, text_1 = process_prices("1", request.form, conn)
        json_2, text_2 = process_prices("2", request.form, conn)
        
        visual_data = request.form.to_dict()
        visual_data['program_1'] = text_1; visual_data['cost_1'] = "" 
        visual_data['program_2'] = text_2; visual_data['cost_2'] = ""

        img = create_image_object(visual_data)
        fname = f"search_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
        img.save(os.path.join(IMAGE_FOLDER, fname))

        cursor.execute('''
            INSERT INTO searches (
                origin, destination, operator, flight_type, search_date, image_path,
                program_1, cost_1, dates_1, prices_json_1,
                program_2, cost_2, dates_2, prices_json_2,
                origin_2, destination_2, selected_bg
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            visual_data.get('origin'), visual_data.get('destination'), visual_data.get('operator'), visual_data.get('flight_type'), 
            visual_data.get('search_date'), fname,
            text_1, "", visual_data.get('dates_1'), json_1,
            text_2, "", visual_data.get('dates_2'), json_2,
            visual_data.get('origin_2'), visual_data.get('destination_2'),
            visual_data.get('selected_bg')
        ))
        conn.commit(); conn.close()
        return redirect(url_for('list_searches'))
    
    cursor.execute("SELECT * FROM programs ORDER BY name")
    programs = cursor.fetchall()
    cursor.execute("SELECT * FROM currencies ORDER BY id")
    currencies = cursor.fetchall()
    conn.close()
    return render_template('register.html', search=None, programs=programs, currencies=currencies, templates=get_available_templates())

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_search(id):
    conn = sqlite3.connect(DB_NAME); conn.row_factory = sqlite3.Row; cursor = conn.cursor()
    
    if request.method == 'POST':
        json_1, text_1 = process_prices("1", request.form, conn)
        json_2, text_2 = process_prices("2", request.form, conn)
        
        visual_data = request.form.to_dict()
        visual_data['program_1'] = text_1; visual_data['cost_1'] = ""
        visual_data['program_2'] = text_2; visual_data['cost_2'] = ""
        
        img = create_image_object(visual_data)
        fname = f"search_{id}_{datetime.now().strftime('%H%M%S')}.png"
        img.save(os.path.join(IMAGE_FOLDER, fname))
        
        cursor.execute('''
            UPDATE searches SET 
                origin=?, destination=?, operator=?, flight_type=?, search_date=?, image_path=?,
                program_1=?, cost_1=?, dates_1=?, prices_json_1=?,
                program_2=?, cost_2=?, dates_2=?, prices_json_2=?,
                origin_2=?, destination_2=?, selected_bg=?
            WHERE id=?
        ''', (
            visual_data.get('origin'), visual_data.get('destination'), visual_data.get('operator'), visual_data.get('flight_type'), 
            visual_data.get('search_date'), fname,
            text_1, "", visual_data.get('dates_1'), json_1,
            text_2, "", visual_data.get('dates_2'), json_2,
            visual_data.get('origin_2'), visual_data.get('destination_2'),
            visual_data.get('selected_bg'),
            id
        ))
        conn.commit(); conn.close()
        return redirect(url_for('list_searches'))
    
    cursor.execute("SELECT * FROM searches WHERE id = ?", (id,))
    search = dict(cursor.fetchone())
    if search.get('prices_json_1'): search['prices_1'] = json.loads(search['prices_json_1'])
    if search.get('prices_json_2'): search['prices_2'] = json.loads(search['prices_json_2'])
    
    cursor.execute("SELECT * FROM programs ORDER BY name")
    programs = cursor.fetchall()
    cursor.execute("SELECT * FROM currencies ORDER BY id")
    currencies = cursor.fetchall()
    conn.close()
    return render_template('register.html', search=search, programs=programs, currencies=currencies, templates=get_available_templates())

@app.route('/list')
@login_required
def list_searches():
    conn = sqlite3.connect(DB_NAME); conn.row_factory = sqlite3.Row; cursor = conn.cursor()
    f_date = request.args.get('date'); f_origin = request.args.get('origin')
    f_dest = request.args.get('destination'); f_operator = request.args.get('operator')
    query = "SELECT * FROM searches WHERE 1=1"
    params = []
    if f_date: query += " AND search_date = ?"; params.append(f_date)
    if f_origin: query += " AND origin LIKE ?"; params.append(f'%{f_origin}%')
    if f_dest: query += " AND destination LIKE ?"; params.append(f'%{f_dest}%')
    if f_operator: query += " AND operator LIKE ?"; params.append(f'%{f_operator}%')
    query += " ORDER BY id DESC"
    cursor.execute(query, params)
    searches = cursor.fetchall(); conn.close()
    return render_template('list.html', searches=searches)

@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_search(id):
    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
    cursor.execute("SELECT image_path FROM searches WHERE id = ?", (id,)); row = cursor.fetchone()
    if row and os.path.exists(os.path.join(IMAGE_FOLDER, row[0])):
        try: os.remove(os.path.join(IMAGE_FOLDER, row[0]))
        except: pass
    cursor.execute("DELETE FROM searches WHERE id = ?", (id,)); conn.commit(); conn.close()
    return redirect(url_for('list_searches'))

if __name__ == '__main__': init_db(); app.run(debug=True, port=5000, host='0.0.0.0')