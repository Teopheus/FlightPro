import os
import sys
import sqlite3
import io
import base64
import locale
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from PIL import Image, ImageDraw, ImageFont
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
# Em produção, use variável de ambiente
app.secret_key = 'segredo_super_secreto_flight_manager'

# --- LOGIN ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- CONFIGURAÇÕES DE CAMINHO (ABSOLUTO) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "database.db")
IMAGE_FOLDER = os.path.join(BASE_DIR, 'static', 'generated')
TEMPLATE_PATH = os.path.join(BASE_DIR, 'static', 'template_fundo.png') 

FONT_BOLD_PATH = os.path.join(BASE_DIR, 'static', 'fonts', 'Montserrat-Bold.ttf')
FONT_REGULAR_PATH = os.path.join(BASE_DIR, 'static', 'fonts', 'Montserrat-Regular.ttf')

os.makedirs(IMAGE_FOLDER, exist_ok=True)

try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil')
    except:
        pass

# --- USUÁRIO ---
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = str(id)
        self.username = username
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    data = cursor.fetchone()
    conn.close()
    if data:
        return User(id=data[0], username=data[1], password=data[2])
    return None

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            origin TEXT, destination TEXT, operator TEXT, flight_type TEXT,
            search_date TEXT, image_path TEXT, cost REAL, program TEXT, available_dates TEXT
        )
    ''')
    # Migração
    cursor.execute("PRAGMA table_info(searches)")
    cols = [info[1] for info in cursor.fetchall()]
    new_cols = [
        ('program_1', 'TEXT'), ('cost_1', 'TEXT'), ('dates_1', 'TEXT'),
        ('program_2', 'TEXT'), ('cost_2', 'TEXT'), ('dates_2', 'TEXT'),
        ('origin_2', 'TEXT'), ('destination_2', 'TEXT')
    ]
    for cname, ctype in new_cols:
        if cname not in cols:
            try: cursor.execute(f"ALTER TABLE searches ADD COLUMN {cname} {ctype}")
            except: pass

    cursor.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT)''')
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('admin', generate_password_hash('admin123')))
    conn.commit()
    conn.close()

# --- MOTOR GRÁFICO (POSICIONAMENTO AJUSTADO) ---
def create_image_object(data):
    # 1. Carrega o Template Pronto
    try:
        img = Image.open(TEMPLATE_PATH).convert("RGBA")
        if img.size != (1080, 1080):
            img = img.resize((1080, 1080))
            
    except FileNotFoundError:
        print(f"ERRO: Não encontrou {TEMPLATE_PATH}")
        img = Image.new('RGBA', (1080, 1080), color=(255, 255, 255, 255))

    draw = ImageDraw.Draw(img)

    def load_font(path, size):
        try: return ImageFont.truetype(path, size)
        except: return ImageFont.load_default()

    # --- FONTES (TAMANHOS RESTAURADOS PARA "GRANDE") ---
    # No seu código anterior elas estavam pequenas (28/38), voltei para o padrão JUMBO
    font_airline     = load_font(FONT_REGULAR_PATH, 40) # Cia Aérea
    font_route       = load_font(FONT_BOLD_PATH, 50)    # Rota (Bem grande)
    font_offer_title = load_font(FONT_BOLD_PATH, 22)    # Preço/Milhas
    font_dates       = load_font(FONT_BOLD_PATH, 20)    # Datas
    
    # Fonte menor para data de atualização no rodapé
    font_footer_reg  = load_font(FONT_REGULAR_PATH, 20)

    # Cores
    c_blue_header   = "#0054a6" 
    c_text_dark     = "#222222" 
    c_white         = "#ffffff"
    
    # Margens Ajustadas (SUBIMOS O TOPO)
    MARGIN_X = 70     
    MARGIN_TOP = 50   # <--- AQUI: Mudamos de 110 para 50 para subir tudo

    # Dados
    flight_type = (data.get('flight_type') or "").upper()
    operator = (data.get('operator') or "").upper()
    origin = (data.get('origin') or "")
    dest = (data.get('destination') or "")

    # ==========================
    # 2. ESCREVE O CONTEÚDO
    # ==========================
    cursor_y = MARGIN_TOP
    
    # Linha 1: Cia Aérea
    draw.text((MARGIN_X, cursor_y), f"{flight_type} {operator}", fill=c_blue_header, font=font_airline)
    cursor_y += 50 # Reduzi um pouco o espaço aqui para aproximar da rota
    
    # Linha 2: Rota (Origem - Destino)
    draw.text((MARGIN_X, cursor_y), f"{origin} - {dest}", fill=c_blue_header, font=font_route)
    cursor_y += 110 # Espaço para começar os dados

    def draw_text_block(start_y, title_rota, prog_txt, cost_txt, dates_txt):
        curr_y = start_y
        
        # Título opcional (ex: Volta)
        if title_rota:
            draw.text((MARGIN_X, curr_y), title_rota, fill=c_blue_header, font=font_route)
            curr_y += 80

        # Formatação Custo
        cost_display = cost_txt or ""
        try:
            val = float(str(cost_txt).replace(',', '.'))
            if val > 0:
                cost_display = locale.currency(val, grouping=True) if 'locale' in sys.modules else f"R$ {val:,.2f}"
        except: pass

        # Programas
        progs = [p.strip() for p in (prog_txt or "").split('\n') if p.strip()]
        
        if not progs:
            if cost_display:
                draw.text((MARGIN_X, curr_y), f"Investimento: {cost_display}", fill=c_text_dark, font=font_offer_title)
                curr_y += 60
        else:
            for i, p in enumerate(progs):
                full_offer_text = p
                if i == 0 and cost_display:
                    full_offer_text += f" + {cost_display}"
                # Texto da Oferta
                draw.text((MARGIN_X, curr_y), full_offer_text, fill=c_text_dark, font=font_offer_title)
                curr_y += 55 

        # Datas
        curr_y += 15 
        d_lines = (dates_txt or "").split('\n')
        for l in d_lines:
            if l.strip():
                draw.text((MARGIN_X, curr_y), l.strip().upper(), fill=c_text_dark, font=font_dates)
                curr_y += 40 
        
        return curr_y + 60 

    # Bloco 1
    cursor_y = draw_text_block(cursor_y, None, data.get('program_1'), data.get('cost_1'), data.get('dates_1'))

    # Bloco 2
    orig2 = data.get('origin_2')
    dest2 = data.get('destination_2')
    has_data2 = data.get('program_2') or data.get('dates_2')
    title_2 = f"{orig2} - {dest2}" if (orig2 and dest2) else None

    # Verifica se cabe antes do rodapé
    if (title_2 or has_data2) and cursor_y < 850:
        cursor_y = draw_text_block(cursor_y, title_2, data.get('program_2'), data.get('cost_2'), data.get('dates_2'))

    # ==========================
    # 3. DATA NO RODAPÉ
    # ==========================
    if data.get('search_date'):
        footer_height = 150
        footer_y_start = 1080 - footer_height 
        text_y = footer_y_start + 100 

        try:
            d = datetime.strptime(data.get('search_date'), '%Y-%m-%d')
            meses = {1:'Janeiro', 2:'Fevereiro', 3:'Março', 4:'Abril', 5:'Maio', 6:'Junho', 7:'Julho', 8:'Agosto', 9:'Setembro', 10:'Outubro', 11:'Novembro', 12:'Dezembro'}
            dt_str = f"Atualizado: {d.day} de {meses.get(d.month, d.month)}"
            
            draw.text((MARGIN_X, text_y), dt_str, fill=c_white, font=font_footer_reg)
        except: pass

    return img.convert("RGB")

# --- ROTAS WEB ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form['username']
        pwd = request.form['password']
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (user,))
        ud = cursor.fetchone()
        conn.close()
        if ud and check_password_hash(ud[2], pwd):
            login_user(User(id=ud[0], username=ud[1], password=ud[2]))
            return redirect(url_for('dashboard'))
        flash('Credenciais inválidas', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
def index():
    return redirect(url_for('dashboard' if current_user.is_authenticated else 'login'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as t FROM searches")
    total = cursor.fetchone()['t']
    cursor.execute("SELECT destination, COUNT(*) as c FROM searches GROUP BY destination ORDER BY c DESC LIMIT 5")
    dest_rows = cursor.fetchall()
    conn.close()
    return render_template('dashboard.html', 
                           total_searches=total, total_volume=0, avg_ticket=0,
                           dest_labels=[r['destination'] for r in dest_rows], 
                           dest_data=[r['c'] for r in dest_rows],
                           airline_labels=[], airline_data=[], time_labels=[], time_data=[])

@app.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    if request.method == 'POST':
        d = request.form.to_dict()
        img = create_image_object(d)
        fname = f"search_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
        img.save(os.path.join(IMAGE_FOLDER, fname))

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO searches (
                origin, destination, operator, flight_type, search_date, image_path,
                program_1, cost_1, dates_1,
                program_2, cost_2, dates_2,
                origin_2, destination_2
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            d.get('origin'), d.get('destination'), d.get('operator'), d.get('flight_type'), 
            d.get('search_date'), fname,
            d.get('program_1'), d.get('cost_1'), d.get('dates_1'),
            d.get('program_2'), d.get('cost_2'), d.get('dates_2'),
            d.get('origin_2'), d.get('destination_2')
        ))
        conn.commit()
        conn.close()
        return redirect(url_for('list_searches'))
    return render_template('register.html', search=None)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_search(id):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if request.method == 'POST':
        d = request.form.to_dict()
        img = create_image_object(d)
        fname = f"search_{id}_{datetime.now().strftime('%H%M%S')}.png"
        img.save(os.path.join(IMAGE_FOLDER, fname))
        
        cursor.execute('''
            UPDATE searches SET 
                origin=?, destination=?, operator=?, flight_type=?, search_date=?, image_path=?,
                program_1=?, cost_1=?, dates_1=?,
                program_2=?, cost_2=?, dates_2=?,
                origin_2=?, destination_2=?
            WHERE id=?
        ''', (
            d.get('origin'), d.get('destination'), d.get('operator'), d.get('flight_type'), 
            d.get('search_date'), fname,
            d.get('program_1'), d.get('cost_1'), d.get('dates_1'),
            d.get('program_2'), d.get('cost_2'), d.get('dates_2'),
            d.get('origin_2'), d.get('destination_2'),
            id
        ))
        conn.commit()
        conn.close()
        return redirect(url_for('list_searches'))
    
    cursor.execute("SELECT * FROM searches WHERE id = ?", (id,))
    search = cursor.fetchone()
    conn.close()
    return render_template('register.html', search=search)

@app.route('/list')
@login_required
def list_searches():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM searches ORDER BY id DESC")
    searches = cursor.fetchall()
    conn.close()
    return render_template('list.html', searches=searches)

@app.route('/delete/<int:id>', methods=['POST'])
@login_required
def delete_search(id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT image_path FROM searches WHERE id = ?", (id,))
    row = cursor.fetchone()
    if row and os.path.exists(os.path.join(IMAGE_FOLDER, row[0])):
        try: os.remove(os.path.join(IMAGE_FOLDER, row[0]))
        except: pass
    cursor.execute("DELETE FROM searches WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('list_searches'))

@app.route('/api/preview', methods=['POST'])
@login_required
def api_preview():
    img = create_image_object(request.json)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return jsonify({'image': base64.b64encode(buf.getvalue()).decode()})

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000, host='0.0.0.0')