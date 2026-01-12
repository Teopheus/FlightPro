import os
import sqlite3
import json
import locale
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS 
from PIL import Image, ImageDraw, ImageFont
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask import send_file, make_response

app = Flask(__name__)
app.secret_key = 'segredo_super_secreto_flight_manager'

# --- CORS (Permite que o React localhost:5173 fale com este Python) ---
CORS(app, 
     resources={r"/*": {"origins": ["http://localhost:5173", "http://127.0.0.1:5173"]}}, 
     supports_credentials=True,
     expose_headers=["Content-Type", "Authorization"],
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "OPTIONS", "DELETE", "PUT"]
)

login_manager = LoginManager()
login_manager.init_app(app)

# --- PASTAS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "database.db")
IMAGE_FOLDER = os.path.join(BASE_DIR, 'static', 'generated')
TEMPLATES_FOLDER = os.path.join(BASE_DIR, 'static', 'templates')
FONTS_FOLDER = os.path.join(BASE_DIR, 'static', 'fonts')

# Garante que as pastas existam
os.makedirs(IMAGE_FOLDER, exist_ok=True)
os.makedirs(TEMPLATES_FOLDER, exist_ok=True)
os.makedirs(FONTS_FOLDER, exist_ok=True)

# Nomes das Fontes (Baseado no seu arquivo original)
FONT_BOLD_NAME = 'Montserrat-Bold.ttf'
FONT_REGULAR_NAME = 'Montserrat-Regular.ttf'

try: locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except: pass

# --- CLASSES E DB HELPERS ---
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = str(id); self.username = username; self.password = password

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect(DB_NAME); cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    data = cursor.fetchone()
    conn.close()
    if data: return User(id=data[0], username=data[1], password=data[2])
    return None

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = dict_factory 
    return conn

def init_and_migrate_db():
    """Inicializa banco e cria colunas faltantes automaticamente."""
    conn = get_db(); cursor = conn.cursor()
    
    # 1. Tabelas Principais
    cursor.execute('''CREATE TABLE IF NOT EXISTS searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            user_id INTEGER, created_at TEXT,
            origin TEXT, destination TEXT, operator TEXT, flight_type TEXT,
            search_date TEXT, image_path TEXT, selected_bg TEXT,
            dates_1 TEXT, dates_2 TEXT, origin_2 TEXT, destination_2 TEXT, 
            prices_1 TEXT, prices_2 TEXT
        )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS programs (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS currencies (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT)''')

    # 2. Seed Admin
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('admin', generate_password_hash('admin123')))

    # 3. Seed Programas Básicos
    cursor.execute("SELECT count(*) as c FROM programs")
    if cursor.fetchone()['c'] == 0:
        cursor.executemany("INSERT INTO programs (name) VALUES (?)", [('Latam Pass',), ('Smiles',), ('AAdvantage',), ('TAP Miles&Go',), ('Iberia Plus',)])
    
    cursor.execute("SELECT count(*) as c FROM currencies")
    if cursor.fetchone()['c'] == 0:
        cursor.executemany("INSERT INTO currencies (code) VALUES (?)", [('R$',), ('USD',), ('EUR',)])

    # 4. Migração de Colunas (Anti-Erro)
    needed_cols = [
        ('user_id', 'INTEGER'), ('created_at', 'TEXT'), 
        ('prices_1', 'TEXT'), ('prices_2', 'TEXT'), 
        ('dates_1', 'TEXT'), ('dates_2', 'TEXT'), 
        ('selected_bg', 'TEXT')
    ]
    cursor.execute("PRAGMA table_info(searches)")
    existing = [r['name'] for r in cursor.fetchall()]
    for col, ctype in needed_cols:
        if col not in existing:
            try: cursor.execute(f"ALTER TABLE searches ADD COLUMN {col} {ctype}")
            except: pass
            
    conn.commit(); conn.close()

# --- ENGINE GRÁFICA (Portado da sua versão original) ---
def load_font(name, size):
    path = os.path.join(FONTS_FOLDER, name)
    try: return ImageFont.truetype(path, size)
    except: return ImageFont.load_default()

def create_real_image(data):
    # 1. Background
    bg_name = data.get('selected_bg')
    bg_path = None
    if bg_name: bg_path = os.path.join(TEMPLATES_FOLDER, bg_name)
    
    try:
        if bg_path and os.path.exists(bg_path):
            img = Image.open(bg_path).convert("RGBA")
            if img.size != (1080, 1080): img = img.resize((1080, 1080))
        else:
            img = Image.new('RGBA', (1080, 1080), (255, 255, 255, 255))
    except:
        img = Image.new('RGBA', (1080, 1080), (255, 255, 255, 255))

    draw = ImageDraw.Draw(img)

    # 2. Temas (Cores exatas do seu original)
    THEMES = {
        'first_class.png':      {'header': '#d4af37', 'route': '#d4af37', 'text': '#ffffff', 'footer': '#d4af37'}, # Dourado
        'executiva_milhas.png': {'header': '#0054a6', 'route': '#0054a6', 'text': '#222222', 'footer': '#ffffff'}, # Azul/Preto
        'default':              {'header': '#0054a6', 'route': '#0054a6', 'text': '#222222', 'footer': '#ffffff'}
    }
    
    # Lógica de seleção de tema
    theme = THEMES.get(bg_name, THEMES['default'])
    # Se o nome do arquivo contiver 'first', força dourado
    if 'first' in (bg_name or '').lower(): theme = THEMES['first_class.png']
    
    c_header = theme['header']
    c_route  = theme['route']
    c_text   = theme['text']
    c_footer = theme['footer']

    # 3. Fontes
    font_airline = load_font(FONT_REGULAR_NAME, 40)
    font_route = load_font(FONT_BOLD_NAME, 50)
    font_offer_title = load_font(FONT_BOLD_NAME, 22)
    font_dates = load_font(FONT_BOLD_NAME, 20)
    font_footer = load_font(FONT_REGULAR_NAME, 20)

    # 4. Dados
    MARGIN_X = 70
    cursor_y = 50
    
    op = (data.get('operator') or "").upper()
    ft = (data.get('flight_type') or "").upper()
    orig = (data.get('origin') or "").upper()
    dest = (data.get('destination') or "").upper()

    # Desenhar Topo
    draw.text((MARGIN_X, cursor_y), f"{ft} {op}", fill=c_header, font=font_airline)
    cursor_y += 50
    draw.text((MARGIN_X, cursor_y), f"{orig} - {dest}", fill=c_route, font=font_route)
    cursor_y += 110

    # Helper para buscar nomes no DB
    def get_names_from_ids(prog_id, curr_id):
        conn = get_db(); c = conn.cursor()
        p_name = ""; c_code = ""
        if prog_id:
            c.execute("SELECT name FROM programs WHERE id=?", (prog_id,))
            r = c.fetchone()
            if r: p_name = r['name']
        if curr_id:
            c.execute("SELECT code FROM currencies WHERE id=?", (curr_id,))
            r = c.fetchone()
            if r: c_code = r['code']
        conn.close()
        return p_name, c_code

    # Função para desenhar blocos (Preço + Datas)
    def draw_block(start_y, title_rota, prices_json, dates_txt):
        curr_y = start_y
        
        # Título opcional (para opção 2)
        if title_rota:
            draw.text((MARGIN_X, curr_y), title_rota, fill=c_route, font=font_route)
            curr_y += 80
        
        # Parse Preços JSON -> Texto Formatado
        if not prices_json:
             draw.text((MARGIN_X, curr_y), "Consulte valores", fill=c_text, font=font_offer_title)
             curr_y += 60
        else:
            if isinstance(prices_json, str):
                try: prices_json = json.loads(prices_json)
                except: prices_json = []
            
            for i, p in enumerate(prices_json):
                p_name, c_code = get_names_from_ids(p.get('prog_id'), p.get('curr_id'))
                miles = p.get('miles', '')
                tax = p.get('tax', '')
                
                # Formata milhas
                try: m_fmt = "{:,.0f}".format(float(miles)).replace(',', '.')
                except: m_fmt = miles
                
                txt = f"{m_fmt} {p_name}"
                if tax and tax != '0': txt += f" + {c_code} {tax}"
                
                draw.text((MARGIN_X, curr_y), txt, fill=c_text, font=font_offer_title)
                curr_y += 55
        
        curr_y += 15
        # Datas
        d_lines = (dates_txt or "").split('\n')
        for l in d_lines:
            if l.strip():
                draw.text((MARGIN_X, curr_y), l.strip().upper(), fill=c_text, font=font_dates)
                curr_y += 40
        
        return curr_y + 60

    # Bloco 1
    cursor_y = draw_block(cursor_y, None, data.get('prices_1'), data.get('dates_1'))

    # Bloco 2 (Se houver)
    orig2 = data.get('origin_2')
    dest2 = data.get('destination_2')
    has_data2 = data.get('prices_2') or data.get('dates_2')
    
    if (orig2 and dest2) or has_data2:
        if cursor_y < 850:
            title = f"{orig2} - {dest2}" if (orig2 and dest2) else None
            cursor_y = draw_block(cursor_y, title, data.get('prices_2'), data.get('dates_2'))

    # Rodapé
    if data.get('search_date'):
        footer_y = 1080 - 150
        try:
            d = datetime.strptime(data.get('search_date'), '%Y-%m-%d')
            meses = {1:'Janeiro', 2:'Fevereiro', 3:'Março', 4:'Abril', 5:'Maio', 6:'Junho', 7:'Julho', 8:'Agosto', 9:'Setembro', 10:'Outubro', 11:'Novembro', 12:'Dezembro'}
            dt_str = f"Atualizado: {d.day} de {meses.get(d.month, d.month)}"
            draw.text((MARGIN_X, footer_y), dt_str, fill=c_footer, font=font_footer)
        except: pass

    return img.convert("RGB")


# --- ROTAS API ---

@app.route('/api/login', methods=['POST', 'OPTIONS'])
def api_login():
    if request.method == 'OPTIONS': return jsonify({'status': 'ok'}), 200
    try:
        data = request.json
        conn = get_db(); c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username=?", (data.get('username'),))
        u = c.fetchone(); conn.close()
        if u and check_password_hash(u['password'], data.get('password')):
            login_user(User(id=u['id'], username=u['username'], password=u['password']))
            return jsonify({'success': True})
        return jsonify({'success': False}), 401
    except: return jsonify({'success': False}), 500

@app.route('/api/logout', methods=['POST'])
@login_required
def api_logout(): logout_user(); return jsonify({'success': True})

@app.route('/api/check_auth', methods=['GET'])
def check_auth():
    return jsonify({'authenticated': current_user.is_authenticated, 'username': current_user.username if current_user.is_authenticated else ''})

@app.route('/api/searches', methods=['POST'])
@login_required
def create_search():
    try:
        d = request.json
        conn = get_db(); c = conn.cursor()
        
        # Gera Imagem Inicial
        img = create_real_image(d)
        fname = f"search_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
        img.save(os.path.join(IMAGE_FOLDER, fname))
        
        # Salva no Banco
        p1 = json.dumps(d.get('prices_1', []))
        p2 = json.dumps(d.get('prices_2', []))
        
        c.execute('''INSERT INTO searches (user_id, created_at, origin, destination, operator, flight_type, search_date, image_path, selected_bg, dates_1, dates_2, origin_2, destination_2, prices_1, prices_2) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                  (current_user.id, datetime.now().isoformat(), d.get('origin'), d.get('destination'), d.get('operator'), d.get('flight_type'), d.get('search_date'), fname, d.get('selected_bg'), d.get('dates_1'), d.get('dates_2'), d.get('origin_2'), d.get('destination_2'), p1, p2))
        conn.commit(); conn.close()
        return jsonify({'success': True})
    except Exception as e:
        print(f"Erro Create: {e}")
        return jsonify({'success': False, 'msg': str(e)}), 500

@app.route('/api/searches', methods=['GET'])
@login_required
def list_searches():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM searches ORDER BY id DESC")
    rows = c.fetchall()
    res = []
    for r in rows:
        try: r['prices_1'] = json.loads(r['prices_1']) if r.get('prices_1') else []
        except: r['prices_1'] = []
        try: r['prices_2'] = json.loads(r['prices_2']) if r.get('prices_2') else []
        except: r['prices_2'] = []
        res.append(r)
    conn.close()
    return jsonify(res)

@app.route('/api/searches/<int:id>', methods=['DELETE'])
@login_required
def delete_search(id):
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT image_path FROM searches WHERE id=?", (id,))
    r = c.fetchone()
    if r and r['image_path']:
        try: os.remove(os.path.join(IMAGE_FOLDER, r['image_path']))
        except: pass
    c.execute("DELETE FROM searches WHERE id=?", (id,)); conn.commit(); conn.close()
    return jsonify({'success': True})

@app.route('/api/generate/<int:id>', methods=['GET'])
def generate_image_on_demand(id):
    print(f"\n--- DEBUG: Solicitando Imagem ID {id} ---")
    
    conn = get_db(); cursor = conn.cursor()
    cursor.execute("SELECT * FROM searches WHERE id = ?", (id,))
    row = cursor.fetchone()
    conn.close()

    if not row: return "Registro não encontrado no DB", 404

    filename = row['image_path']
    if not filename: 
        filename = f"search_{id}_recovered.png"
    
    # TRUQUE: Usa caminho absoluto para evitar confusão de pastas
    absolute_image_folder = os.path.abspath(IMAGE_FOLDER)
    full_path = os.path.join(absolute_image_folder, filename)
    
    print(f"--> Caminho Absoluto: {full_path}")

    # Auto-Regeneração
    if not os.path.exists(full_path):
        print(f"--> Arquivo não existe. Criando agora...")
        try:
            if isinstance(row.get('prices_1'), str): row['prices_1'] = json.loads(row['prices_1'])
            if isinstance(row.get('prices_2'), str): row['prices_2'] = json.loads(row['prices_2'])
        except: row['prices_1'] = []

        try:
            img = create_real_image(row)
            img.save(full_path)
            print("--> Imagem salva com sucesso!")
            
            # Atualiza nome no banco se estava vazio
            if not row['image_path']:
                conn = get_db(); c = conn.cursor()
                c.execute("UPDATE searches SET image_path=? WHERE id=?", (filename, id))
                conn.commit(); conn.close()
        except Exception as e:
            print(f"Erro CRÍTICO na geração: {e}")
            return f"Erro interno: {e}", 500

    # ENTREGA COM HEADERS ANTI-CACHE
    if os.path.exists(full_path):
        try:
            response = make_response(send_file(full_path, mimetype='image/png'))
            # Força o navegador a não salvar cache (útil se ele decorou o 404)
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            return response
        except Exception as e:
            print(f"Erro ao enviar arquivo existente: {e}")
            return f"Erro ao entregar: {e}", 500
    else:
        print("--> O arquivo SUMIU mesmo após tentar gerar.")
        return "Arquivo inacessível", 404

@app.route('/api/config', methods=['GET'])
@login_required
def get_config():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT * FROM programs ORDER BY name"); progs = c.fetchall()
    c.execute("SELECT * FROM currencies ORDER BY id"); currs = c.fetchall()
    conn.close()
    temps = sorted([f for f in os.listdir(TEMPLATES_FOLDER) if f.endswith('.png')]) if os.path.exists(TEMPLATES_FOLDER) else []
    return jsonify({'programs': progs, 'currencies': currs, 'templates': temps})

# Rotas de Programs e Currencies
@app.route('/api/programs', methods=['POST'])
@login_required
def add_prog():
    conn = get_db(); c = conn.cursor()
    c.execute("INSERT INTO programs (name) VALUES (?)", (request.json.get('name'),))
    conn.commit(); conn.close(); return jsonify({'success': True})

@app.route('/api/programs/<int:id>', methods=['DELETE'])
@login_required
def del_prog(id):
    conn = get_db(); c = conn.cursor()
    c.execute("DELETE FROM programs WHERE id=?", (id,)); conn.commit(); conn.close(); return jsonify({'success': True})

@app.route('/api/currencies', methods=['POST'])
@login_required
def add_curr():
    conn = get_db(); c = conn.cursor()
    c.execute("INSERT INTO currencies (code) VALUES (?)", (request.json.get('code'),))
    conn.commit(); conn.close(); return jsonify({'success': True})

@app.route('/api/currencies/<int:id>', methods=['DELETE'])
@login_required
def del_curr(id):
    conn = get_db(); c = conn.cursor()
    c.execute("DELETE FROM currencies WHERE id=?", (id,)); conn.commit(); conn.close(); return jsonify({'success': True})

@app.route('/api/dashboard', methods=['GET'])
@login_required
def dashboard():
    conn = get_db(); c = conn.cursor()
    c.execute("SELECT COUNT(*) as t FROM searches")
    return jsonify({'total': c.fetchone()['t']})

@app.route('/static/generated/<path:filename>')
def serve_gen(filename): return send_from_directory(IMAGE_FOLDER, filename)

if __name__ == '__main__':
    if not os.path.exists(DB_NAME): init_and_migrate_db()
    init_and_migrate_db() # Roda sempre para garantir colunas
    app.run(debug=True, port=5000, host='0.0.0.0')