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
# Em produção, use uma variável de ambiente
app.secret_key = 'segredo_super_secreto_flight_manager'

# --- CONFIGURAÇÃO DE LOGIN ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# --- CONFIGURAÇÕES DE ARQUIVOS ---
DB_NAME = "database.db"
IMAGE_FOLDER = os.path.join('static', 'generated')
TEMPLATE_PATH = os.path.join('static', 'template_fundo.png')
FONT_BOLD_PATH = os.path.join('static', 'fonts', 'Montserrat-Bold.ttf')
FONT_REGULAR_PATH = os.path.join('static', 'fonts', 'Montserrat-Regular.ttf')

os.makedirs(IMAGE_FOLDER, exist_ok=True)

# Tenta configurar moeda brasileira
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil')
    except:
        pass

# --- MODELO DE USUÁRIO ---
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

# --- BANCO DE DADOS (COM MIGRAÇÃO) ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Tabela de Pesquisas (Base)
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
    
    # 2. Migração Automática: Adiciona colunas novas se não existirem
    cursor.execute("PRAGMA table_info(searches)")
    columns = [info[1] for info in cursor.fetchall()]
    
    new_columns = [
        ('program_1', 'TEXT'), ('cost_1', 'REAL'), ('dates_1', 'TEXT'),
        ('program_2', 'TEXT'), ('cost_2', 'REAL'), ('dates_2', 'TEXT')
    ]
    
    for col_name, col_type in new_columns:
        if col_name not in columns:
            print(f"Migrando BD: Adicionando coluna {col_name}...")
            try:
                cursor.execute(f"ALTER TABLE searches ADD COLUMN {col_name} {col_type}")
            except Exception as e:
                print(f"Erro ao adicionar {col_name}: {e}")

    # 3. Tabela de Usuários
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    ''')
    
    # 4. Usuário Admin Padrão
    cursor.execute("SELECT * FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        hashed_pw = generate_password_hash('admin123')
        cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('admin', hashed_pw))
        
    conn.commit()
    conn.close()

# --- MOTOR DE GERAÇÃO DE IMAGEM ---
def create_image_object(data):
    try:
        img = Image.open(TEMPLATE_PATH).convert("RGB")
    except FileNotFoundError:
        img = Image.new('RGB', (1080, 1080), color=(255, 255, 255))
    
    draw = ImageDraw.Draw(img)

    # Carregamento de Fontes
    def load_font(path, system_alt, size):
        try: return ImageFont.truetype(path, size)
        except: return ImageFont.load_default()

    font_header_sm = load_font(FONT_REGULAR_PATH, "arial.ttf", 28)
    font_header_lg = load_font(FONT_BOLD_PATH, "arialbd.ttf", 45)
    font_cost      = load_font(FONT_BOLD_PATH, "arialbd.ttf", 32)
    font_dates     = load_font(FONT_BOLD_PATH, "arialbd.ttf", 24)
    font_footer    = load_font(FONT_REGULAR_PATH, "arial.ttf", 18)
    font_sep       = load_font(FONT_REGULAR_PATH, "arial.ttf", 20)
    font_vagas     = load_font(FONT_REGULAR_PATH, "arial.ttf", 14)

    color_blue, color_dark, color_grey, color_white = "#0054a6", "#333333", "#777777", "#ffffff"
    margin_left = 50

    # Dados Gerais
    flight_type = (data.get('flight_type') or "").upper()
    operator = (data.get('operator') or "").upper()
    origin = (data.get('origin') or "")
    destination = (data.get('destination') or "")

    # Desenha Cabeçalho Fixo
    draw.text((margin_left, 50), f"{flight_type} {operator}", fill=color_blue, font=font_header_sm)
    draw.text((margin_left, 100), f"{origin} - {destination}", fill=color_blue, font=font_header_lg)

    # --- FUNÇÃO AUXILIAR DE DESENHO DE BLOCO ---
    def draw_section(start_y, p_prog, p_cost, p_dates):
        current_y = start_y
        
        # Formata Custo
        try:
            val = float(p_cost or 0)
            c_fmt = locale.currency(val, grouping=True) if 'locale' in sys.modules and val > 0 else (f"R$ {val:,.2f}" if val > 0 else "")
        except:
            c_fmt = str(p_cost) if p_cost else ""

        programs = [x.strip() for x in (p_prog or "").split('\n') if x.strip()]
        
        if not programs:
            if c_fmt:
                draw.text((margin_left, current_y), f"Custo: {c_fmt}", fill=color_dark, font=font_cost)
                current_y += 45
        else:
            for i, line in enumerate(programs):
                if i > 0:
                    draw.text((margin_left + 20, current_y), "OU", fill=color_grey, font=font_sep)
                    current_y += 30
                
                text = line
                if i == 0 and c_fmt:
                    text += f" + {c_fmt}"
                
                draw.text((margin_left, current_y), text, fill=color_dark, font=font_cost)
                current_y += 45
        
        # Datas
        current_y += 10
        d_lines = (p_dates or "").split('\n')
        for l in d_lines:
            if l.strip():
                draw.text((margin_left, current_y), l.strip().upper(), fill=color_dark, font=font_dates)
                current_y += 35
        
        return current_y + 40 # Retorna Y para o próximo bloco

    # Desenha Bloco 1
    y_pos = 200
    y_pos = draw_section(y_pos, data.get('program_1'), data.get('cost_1'), data.get('dates_1'))

    # Desenha Bloco 2 (Se existir)
    if data.get('program_2') or data.get('dates_2'):
        # Verifica limite de altura para não estourar
        if y_pos < 920:
            y_pos = draw_section(y_pos, data.get('program_2'), data.get('cost_2'), data.get('dates_2'))

    # Rodapé
    footer_date = "Pesquisa realizada..."
    if data.get('search_date'):
        try:
            footer_date = datetime.strptime(data.get('search_date'), '%Y-%m-%d').strftime("Pesquisa realizada no dia %d de %B de %Y.")
        except: pass
    
    # Texto de aviso de vagas
    draw.text((margin_left, 940), "Em parênteses a quantidade de vagas em cada data.", fill=color_white, font=font_vagas)
    draw.text((margin_left, 970), footer_date, fill=color_white, font=font_footer)

    return img

# --- ROTAS ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        ud = cursor.fetchone()
        conn.close()
        
        if ud and check_password_hash(ud[2], password):
            login_user(User(id=ud[0], username=ud[1], password=ud[2]))
            return redirect(url_for('dashboard'))
        else:
            flash('Login inválido', 'danger')
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
    # Mantive lógica simples para o dashboard funcionar
    # Usamos cost_1 como referência de valor para os KPIs
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as t, SUM(cost_1) as v, AVG(cost_1) as a FROM searches")
    kpis = cursor.fetchone()
    
    cursor.execute("SELECT destination, COUNT(*) as c FROM searches GROUP BY destination ORDER BY c DESC LIMIT 5")
    dest = cursor.fetchall()
    
    cursor.execute("SELECT operator, COUNT(*) as c FROM searches GROUP BY operator ORDER BY c DESC LIMIT 5")
    airline = cursor.fetchall()
    
    cursor.execute("SELECT strftime('%m/%Y', search_date) as m, COUNT(*) as c FROM searches WHERE search_date IS NOT NULL GROUP BY m ORDER BY search_date ASC LIMIT 6")
    time = cursor.fetchall()
    conn.close()

    return render_template('dashboard.html', 
                           total_searches=kpis['t'] or 0, 
                           total_volume=kpis['v'] or 0, 
                           avg_ticket=kpis['a'] or 0,
                           dest_labels=[r['destination'] for r in dest], dest_data=[r['c'] for r in dest],
                           airline_labels=[r['operator'] for r in airline], airline_data=[r['c'] for r in airline],
                           time_labels=[r['m'] for r in time], time_data=[r['c'] for r in time])

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
        # Salva nos campos novos E nos antigos (para compatibilidade)
        cursor.execute('''
            INSERT INTO searches (
                origin, destination, operator, flight_type, search_date, image_path,
                program_1, cost_1, dates_1,
                program_2, cost_2, dates_2,
                cost, program, available_dates
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            d.get('origin'), d.get('destination'), d.get('operator'), d.get('flight_type'), 
            d.get('search_date'), fname,
            d.get('program_1'), d.get('cost_1'), d.get('dates_1'),
            d.get('program_2'), d.get('cost_2'), d.get('dates_2'),
            d.get('cost_1'), d.get('program_1'), d.get('dates_1') # Retrocompatibilidade
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
                cost=?, program=?, available_dates=?
            WHERE id=?
        ''', (
            d.get('origin'), d.get('destination'), d.get('operator'), d.get('flight_type'), 
            d.get('search_date'), fname,
            d.get('program_1'), d.get('cost_1'), d.get('dates_1'),
            d.get('program_2'), d.get('cost_2'), d.get('dates_2'),
            d.get('cost_1'), d.get('program_1'), d.get('dates_1'),
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