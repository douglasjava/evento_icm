import os
import pandas as pd
import uuid
from flask import Blueprint, render_template, request, jsonify, redirect, flash
from datetime import datetime
from flask import send_file
import unicodedata
import re
from .models import get_db
from app.utils.pdf_generator import gerar_crachas
import csv
from flask import send_file
from io import StringIO
import io
import zipfile
from flask import send_file
from werkzeug.utils import secure_filename



UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        file = request.files.get('file')

        if not file or not allowed_file(file.filename):
            flash('Envie um arquivo CSV válido.')
            return redirect(request.url)

        filepath = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(filepath)

        df = pd.read_csv(filepath)

        # Renomeia colunas para facilitar acesso
        df.columns = [col.strip().lower() for col in df.columns]

        db = get_db()
        cursor = db.cursor()

        cursor.execute("DELETE FROM inscritos")

        for _, row in df.iterrows():
            nome = str(row.get('nome', '')).strip()
            telefone = str(row.get('telefone', '')).strip()
            igreja = str(row.get('igreja', '')).strip()
            funcao = str(row.get('função', '')).strip()

            qrcode = str(uuid.uuid4())  # ID único

            cursor.execute("""
                INSERT INTO inscritos (nome, igreja, telefone, funcao, qrcode)
                VALUES (?, ?, ?, ?, ?)
            """, (nome, igreja, telefone, funcao, qrcode))

        db.commit()
        flash('Inscritos importados com sucesso!')
        return redirect('/')

    return render_template('upload.html')

@bp.route('/generate')
def generate():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT nome, igreja, qrcode FROM inscritos")
    rows = cursor.fetchall()

    # Organiza os inscritos por igreja
    igrejas = {}
    for nome, igreja, qrcode in rows:
        igreja_sanitizada = secure_filename(igreja) or "Sem_Igreja"
        igrejas.setdefault(igreja_sanitizada, []).append((nome, igreja, qrcode))

    # Cria o arquivo zip em memória
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for igreja_nome, inscritos in igrejas.items():
            pdf_buffer = gerar_crachas(inscritos)  # retorna um BytesIO
            pdf_filename = f"{igreja_nome}.pdf"
            zip_file.writestr(pdf_filename, pdf_buffer.getvalue())

    zip_buffer.seek(0)

    return send_file(
        zip_buffer,
        as_attachment=True,
        download_name="crachas_por_igreja.zip",
        mimetype='application/zip'
    )


@bp.route("/scanner")
def scan_qrcode():
    return render_template("leitura.html")


@bp.route('/check-in', methods=['POST'])
def check_in():
    data = request.get_json(silent=True) or {}
    codigo = data.get('codigo', '').strip()

    if not codigo:
        return jsonify({'msg': 'QR Code inválido.'}), 400

    db = get_db()
    cur = db.cursor()
    cur.execute(
        "SELECT id, nome, igreja, presente FROM inscritos WHERE qrcode = ?",
        (codigo,)
    )
    row = cur.fetchone()

    if not row:
        return jsonify({'msg': 'QR Code não encontrado.'}), 404

    if row['presente']:
        return jsonify({
            'msg': 'Participante já conferido.',
            'nome': row['nome'],
            'igreja': row['igreja']
        }), 200

    # marca presença
    cur.execute(
        "UPDATE inscritos SET presente = 1, data_presenca = ? WHERE id = ?",
        (datetime.now().isoformat(sep=' ', timespec='seconds'), row['id'])
    )
    db.commit()

    return jsonify({
        'msg': 'Check-in realizado!',
        'nome': row['nome'],
        'igreja': row['igreja']
    }), 200

@bp.route('/dashboard')
def dashboard():
    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT COUNT(*) FROM inscritos")
    total_inscritos = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM inscritos WHERE presente = 1")
    total_presentes = cur.fetchone()[0]

    percentual = round((total_presentes / total_inscritos) * 100, 1) if total_inscritos else 0

    # Presentes por igreja
    cur.execute("""
        SELECT igreja, COUNT(*) as presentes
        FROM inscritos
        WHERE presente = 1
        GROUP BY igreja
    """)

    igrejas = cur.fetchall()
    igrejas = [{'igreja': sanitize_text(row['igreja']), 'presentes': row['presentes']} for row in igrejas]

    return render_template('dashboard.html',
                           total_inscritos=total_inscritos,
                           total_presentes=total_presentes,
                           percentual=percentual,
                           igrejas=igrejas)

@bp.route('/download-presentes')
def download_presentes():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT nome, igreja, data_presenca FROM inscritos WHERE presente = 1")

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Nome', 'Igreja', 'Data de Presença'])

    for row in cur.fetchall():
        writer.writerow([row['nome'], row['igreja'], row['data_presenca']])

    output.seek(0)
    return send_file(
        BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        download_name='presentes.csv',
        as_attachment=True
    )

def sanitize_text(text):
    # Remove acentos
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
    # Remove caracteres especiais, mantendo letras, números e espaços
    text = re.sub(r'[^\w\s-]', '', text)
    return text.strip()
