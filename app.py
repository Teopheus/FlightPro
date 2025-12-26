import os
import sqlite3
import io
import base64
import locale
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify
from PIL import Image, ImageDraw, ImageFont

app = Flask(__name__)

# --- CONFIGURAÇÕES GERAIS ---
DB_NAME = "database.db"
IMAGE_FOLDER = os.path.join('static', 'generated')
TEMPLATE_PATH = os.path.join('static', 'template_fundo.png')

# Caminhos de Fontes (Recomendado: Montserrat ou Roboto)
# Se não existirem, o sistema usará Arial ou padrão.
FONT_BOLD_PATH = os.path.join('static', 'fonts', 'Montserrat-Bold.ttf')
FONT_REGULAR_PATH = os.path.join('static', 'fonts', 'Montserrat-Regular.ttf')

os.makedirs(IMAGE_FOLDER, exist_ok=True)

# Configuração de Localização (Moeda R$)
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil')
    except:
        print("Aviso: Locale pt_BR não detectado. A formatação de moeda será genérica.")

# --- BANCO DE DADOS ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Tabela com suporte a todas as colunas necessárias
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            origin TEXT,
            destination TEXT,
            available_dates TEXT,
            program TEXT,
            operator TEXT,
            flight_type TEXT,
            cost REAL,
            search_date TEXT,
            image_path TEXT
        )
    ''')
    conn.commit()
    conn.close()

# --- MOTOR DE GERAÇÃO DE IMAGEM ---
def create_image_object(data):
    """
    Gera um objeto de imagem (PIL) baseado nos dados do dicionário 'data'.
    Não salva no disco, apenas cria na memória.
    """
    
    # 1. Carrega Template ou cria fundo branco
    try:
        img = Image.open(TEMPLATE_PATH).convert("RGB")
    except FileNotFoundError:
        img = Image.new('RGB', (1080, 1080), color=(255, 255, 255))
        draw_temp = ImageDraw.Draw(img)
        draw_temp.text((10, 10), "ERRO: Template não encontrado", fill="red")

    draw = ImageDraw.Draw(img)

    # 2. Carregamento Seguro de Fontes
    def load_font(path, system_alt, size):
        try:
            return ImageFont.truetype(path, size)
        except:
            try:
                return ImageFont.truetype(system_alt, size)
            except:
                return ImageFont.load_default()

    font_header_sm = load_font(FONT_REGULAR_PATH, "arial.ttf", 28)
    font_header_lg = load_font(FONT_BOLD_PATH, "arialbd.ttf", 45)
    font_cost      = load_font(FONT_BOLD_PATH, "arialbd.ttf", 32)
    font_dates     = load_font(FONT_BOLD_PATH, "arialbd.ttf", 26)
    font_footer    = load_font(FONT_REGULAR_PATH, "arial.ttf", 18)
    font_sep       = load_font(FONT_REGULAR_PATH, "arial.ttf", 20) # Fonte para o "OU"

    # 3. Definições de Estilo
    color_blue = "#0054a6"
    color_dark = "#333333"
    color_grey = "#777777"
    color_white = "#ffffff"
    margin_left = 50

    # 4. Tratamento de Dados (Evita erros com None)
    flight_type = (data.get('flight_type') or "").upper()
    operator = (data.get('operator') or "").upper()
    origin = (data.get('origin') or "")
    destination = (data.get('destination') or "")
    
    # Processa Programas (quebra linhas)
    programs_raw = (data.get('program') or "")
    # Cria lista ignorando linhas vazias
    program_list = [p.strip() for p in programs_raw.split('\n') if p.strip()]
    
    dates_text = (data.get('available_dates') or "")
    search_date_str = (data.get('search_date') or "")
    
    # Formatação de Moeda
    try:
        cost_val = float(data.get('cost', 0))
        try:
            cost_fmt = locale.currency(cost_val, grouping=True)
        except:
            cost_fmt = f"R$ {cost_val:,.2f}"
    except ValueError:
        cost_fmt = "R$ 0,00"

    # 5. Desenho dos Elementos
    
    # Cabeçalho
    draw.text((margin_left, 50), f"{flight_type} {operator}", fill=color_blue, font=font_header_sm)
    draw.text((margin_left, 100), f"{origin} - {destination}", fill=color_blue, font=font_header_lg)

    # Lógica de Programas Múltiplos com "OU"
    current_y = 200
    line_height = 45
    sep_height = 30

    if not program_list:
        # Fallback se não tiver programa
        draw.text((margin_left, current_y), f"Custo: {cost_fmt}", fill=color_dark, font=font_cost)
        current_y += line_height
    else:
        for i, prog in enumerate(program_list):
            # Se não é o primeiro, desenha o separador "OU"
            if i > 0:
                draw.text((margin_left + 20, current_y), "OU", fill=color_grey, font=font_sep)
                current_y += sep_height
            
            # Monta a linha de texto
            text_line = prog
            # Adiciona o valor monetário apenas na primeira linha (padrão estético)
            if i == 0:
                text_line += f" + {cost_fmt}"
            
            draw.text((margin_left, current_y), text_line, fill=color_dark, font=font_cost)
            current_y += line_height

    # Datas (Posicionadas dinamicamente abaixo dos programas)
    y_dates = current_y + 40
    for line in dates_text.split('\n'):
        clean_line = line.strip().upper()
        if clean_line:
            draw.text((margin_left, y_dates), clean_line, fill=color_dark, font=font_dates)
            y_dates += 40

    # Rodapé
    footer_text = "Pesquisa realizada..."
    if search_date_str:
        try:
            dt = datetime.strptime(search_date_str, '%Y-%m-%d')
            footer_text = dt.strftime("Pesquisa realizada no dia %d de %B de %Y.")
        except:
            footer_text = f"Pesquisa realizada em {search_date_str}."
            
    draw.text((margin_left, 970), footer_text, fill=color_white, font=font_footer)

    return img

# --- ROTAS ---

@app.route('/')
def index():
    return redirect(url_for('list_searches'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    # Rota para CRIAR novo registro
    if request.method == 'POST':
        data = request.form.to_dict()
        
        # 1. Gera e salva imagem
        img = create_image_object(data)
        filename = f"search_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
        img.save(os.path.join(IMAGE_FOLDER, filename))

        # 2. Salva no BD
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO searches (origin, destination, available_dates, program, operator, flight_type, cost, search_date, image_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('origin'), data.get('destination'), data.get('available_dates'), 
            data.get('program'), data.get('operator'), data.get('flight_type'), 
            data.get('cost'), data.get('search_date'), filename
        ))
        conn.commit()
        conn.close()
        return redirect(url_for('list_searches'))
    
    # GET: Renderiza formulário vazio
    return render_template('register.html', search=None)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_search(id):
    # Rota para EDITAR registro existente
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if request.method == 'POST':
        data = request.form.to_dict()
        
        # 1. Gera nova imagem (pode sobrescrever ou criar nova versão)
        img = create_image_object(data)
        # Adiciona sufixo v2, v3 etc ou timestamp para evitar cache do navegador
        filename = f"search_{id}_{datetime.now().strftime('%H%M%S')}.png"
        img.save(os.path.join(IMAGE_FOLDER, filename))

        # 2. Atualiza BD
        cursor.execute('''
            UPDATE searches 
            SET origin=?, destination=?, available_dates=?, program=?, 
                operator=?, flight_type=?, cost=?, search_date=?, image_path=?
            WHERE id=?
        ''', (
            data.get('origin'), data.get('destination'), data.get('available_dates'),
            data.get('program'), data.get('operator'), data.get('flight_type'),
            data.get('cost'), data.get('search_date'), filename, id
        ))
        conn.commit()
        conn.close()
        return redirect(url_for('list_searches'))

    # GET: Busca dados para preencher o form
    cursor.execute("SELECT * FROM searches WHERE id = ?", (id,))
    search = cursor.fetchone()
    conn.close()
    
    if not search:
        return "Registro não encontrado", 404

    return render_template('register.html', search=search)

@app.route('/delete/<int:id>', methods=['POST'])
def delete_search(id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Busca arquivo para deletar
    cursor.execute("SELECT image_path FROM searches WHERE id = ?", (id,))
    row = cursor.fetchone()
    if row:
        path = os.path.join(IMAGE_FOLDER, row[0])
        if os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass # Ignora erro se arquivo já não existir
    
    # 2. Remove do BD
    cursor.execute("DELETE FROM searches WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('list_searches'))

@app.route('/api/preview', methods=['POST'])
def api_preview():
    # Rota AJAX para o Live Preview
    data = request.json
    img = create_image_object(data)
    
    # Converte para base64
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    img_b64 = base64.b64encode(buf.getvalue()).decode()
    
    return jsonify({'image': img_b64})

@app.route('/list')
def list_searches():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM searches ORDER BY id DESC")
    searches = cursor.fetchall()
    conn.close()
    return render_template('list.html', searches=searches)

@app.route('/dashboard')
def dashboard():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. KPIs GERAIS
    cursor.execute("SELECT COUNT(*) as total_searches, SUM(cost) as total_cost, AVG(cost) as avg_cost FROM searches")
    kpis = cursor.fetchone()
    
    total_searches = kpis['total_searches'] or 0
    total_volume = kpis['total_cost'] or 0
    avg_ticket = kpis['avg_cost'] or 0

    # 2. TOP 5 DESTINOS
    cursor.execute("""
        SELECT destination, COUNT(*) as count 
        FROM searches 
        GROUP BY destination 
        ORDER BY count DESC 
        LIMIT 5
    """)
    top_destinations = cursor.fetchall()
    
    # Prepara listas para o Chart.js
    dest_labels = [row['destination'] for row in top_destinations]
    dest_data = [row['count'] for row in top_destinations]

    # 3. TOP CIAS AÉREAS
    cursor.execute("""
        SELECT operator, COUNT(*) as count 
        FROM searches 
        GROUP BY operator 
        ORDER BY count DESC 
        LIMIT 5
    """)
    top_airlines = cursor.fetchall()
    airline_labels = [row['operator'] for row in top_airlines]
    airline_data = [row['count'] for row in top_airlines]

    # 4. EVOLUÇÃO MENSAL (Últimos 6 meses)
    # SQLite usa strftime para extrair mês/ano
    cursor.execute("""
        SELECT strftime('%m/%Y', search_date) as month_year, COUNT(*) as count
        FROM searches
        WHERE search_date IS NOT NULL
        GROUP BY month_year
        ORDER BY search_date ASC
        LIMIT 6
    """)
    timeline = cursor.fetchall()
    time_labels = [row['month_year'] for row in timeline]
    time_data = [row['count'] for row in timeline]

    conn.close()

    return render_template('dashboard.html', 
                           total_searches=total_searches,
                           total_volume=total_volume,
                           avg_ticket=avg_ticket,
                           dest_labels=dest_labels,
                           dest_data=dest_data,
                           airline_labels=airline_labels,
                           airline_data=airline_data,
                           time_labels=time_labels,
                           time_data=time_data)

if __name__ == '__main__':
    init_db()
    # Adicione host='0.0.0.0' aqui:
    app.run(debug=True, port=5000, host='0.0.0.0')