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
app.secret_key = 'segredo_super_secreto_flight_manager'

# --- LOGIN MANAGER ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- CONFIGS ---
DB_NAME = "database.db"
IMAGE_FOLDER = os.path.join('static', 'generated')
TEMPLATE_PATH = os.path.join('static', 'template_fundo.png')
FONT_BOLD_PATH = os.path.join('static', 'fonts', 'Montserrat-Bold.ttf')
FONT_REGULAR_PATH = os.path.join('static', 'fonts', 'Montserrat-Regular.ttf')

os.makedirs(IMAGE_FOLDER, exist_ok=True)

try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil')
    except:
        pass

# --- MODELO USUÁRIO ---
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

# --- BANCO DE DADOS (COM MIGRAÇÃO AUTO) ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Tabela Base
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            origin TEXT,
            destination TEXT,
            operator TEXT,
            flight_type TEXT,
            search_date TEXT,
            image_path TEXT,
            cost REAL, 
            program TEXT,
            available_dates TEXT
        )
    ''')
    
    # Migração: Adiciona colunas novas se não existirem
    cursor.execute("PRAGMA table_info(searches)")
    columns = [info[1] for info in cursor.fetchall()]
    
    # Lista de colunas novas (incluindo as de origem/destino da volta)
    new_cols = [
        ('program_1', 'TEXT'), ('cost_1', 'TEXT'), ('dates_1', 'TEXT'),
        ('program_2', 'TEXT'), ('cost_2', 'TEXT'), ('dates_2', 'TEXT'),
        ('origin_2', 'TEXT'), ('destination_2', 'TEXT') # <--- NOVAS
    ]
    
    for col_name, col_type in new_cols:
        if col_name not in columns:
            print(f"Migrando BD: Criando coluna {col_name}...")
            try:
                cursor.execute(f"ALTER TABLE searches ADD COLUMN {col_name} {col_type}")
            except Exception as e:
                print(f"Erro ao migrar {col_name}: {e}")

    # Tabela Usuários
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password TEXT)''')
    
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('admin', generate_password_hash('admin123')))
        
    conn.commit()
    conn.close()

# --- MOTOR GRÁFICO ---
def create_image_object(data):
    try:
        img = Image.open(TEMPLATE_PATH).convert("RGB")
    except FileNotFoundError:
        img = Image.new('RGB', (1080, 1080), color=(255, 255, 255))
    
    draw = ImageDraw.Draw(img)

    def load_font(path, size):
        try: return ImageFont.truetype(path, size)
        except: return ImageFont.load_default()

    # Fontes
    font_header_sm = load_font(FONT_REGULAR_PATH, 28)
    font_header_lg = load_font(FONT_BOLD_PATH, 45)
    font_cost      = load_font(FONT_BOLD_PATH, 32)
    font_dates     = load_font(FONT_BOLD_PATH, 24)
    font_footer    = load_font(FONT_REGULAR_PATH, 18)
    font_sep       = load_font(FONT_REGULAR_PATH, 20)
    font_vagas     = load_font(FONT_REGULAR_PATH, 14)

    # Cores
    c_blue, c_dark, c_grey, c_white = "#0054a6", "#333333", "#777777", "#ffffff"
    margin_left = 50

    # Cabeçalho Fixo (Opção 1)
    flight_type = (data.get('flight_type') or "").upper()
    operator = (data.get('operator') or "").upper()
    origin = (data.get('origin') or "")
    dest = (data.get('destination') or "")

    draw.text((margin_left, 50), f"{flight_type} {operator}", fill=c_blue, font=font_header_sm)
    draw.text((margin_left, 100), f"{origin} - {dest}", fill=c_blue, font=font_header_lg)

    # --- FUNÇÃO DE BLOCO ---
    def draw_block(start_y, prog_txt, cost_txt, dates_txt):
        curr_y = start_y
        
        # Formata Custo
        cost_display = cost_txt or ""
        try:
            val = float(str(cost_txt).replace(',', '.'))
            if val > 0:
                cost_display = locale.currency(val, grouping=True) if 'locale' in sys.modules else f"R$ {val:,.2f}"
        except: pass

        progs = [p.strip() for p in (prog_txt or "").split('\n') if p.strip()]
        
        if not progs:
            if cost_display:
                draw.text((margin_left, curr_y), f"Custo: {cost_display}", fill=c_dark, font=font_cost)
                curr_y += 45
        else:
            for i, p in enumerate(progs):
                if i > 0:
                    draw.text((margin_left + 20, curr_y), "OU", fill=c_grey, font=font_sep)
                    curr_y += 30
                
                line = p
                if i == 0 and cost_display:
                    line += f" + {cost_display}"
                
                draw.text((margin_left, curr_y), line, fill=c_dark, font=font_cost)
                curr_y += 45
        
        # Datas
        curr_y += 10
        d_lines = (dates_txt or "").split('\n')
        for l in d_lines:
            if l.strip():
                draw.text((margin_left, curr_y), l.strip().upper(), fill=c_dark, font=font_dates)
                curr_y += 35
        
        return curr_y + 40 

    # Desenha Bloco 1
    cursor_y = 200
    cursor_y = draw_block(cursor_y, data.get('program_1'), data.get('cost_1'), data.get('dates_1'))

    # Desenha Bloco 2
    if data.get('program_2') or data.get('dates_2'):
        # Verifica se tem Rota Específica para o Bloco 2
        orig2 = data.get('origin_2')
        dest2 = data.get('destination_2')
        
        if orig2 and dest2:
            # Desenha Novo Cabeçalho de Rota
            draw.text((margin_left, cursor_y + 10), f"{orig2} - {dest2}", fill=c_blue, font=font_header_lg)
            cursor_y += 70 # Empurra cursor para baixo

        if cursor_y < 920:
            cursor_y = draw_block(cursor_y, data.get('program_2'), data.get('cost_2'), data.get('dates_2'))

    # Rodapé
    footer_txt = "Pesquisa realizada..."
    if data.get('search_date'):
        try:
            dt = datetime.strptime(data.get('search_date'), '%Y-%m-%d')
            footer_txt = dt.strftime("Pesquisa realizada no dia %d de %B de %Y.")
        except: pass
    
    draw.text((margin_left, 940), "Em parênteses a quantidade de vagas em cada data.", fill=c_white, font=font_vagas)
    draw.text((margin_left, 970), footer_txt, fill=c_white, font=font_footer)

    return img

# --- ROTAS ---

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