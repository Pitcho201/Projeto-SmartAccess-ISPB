from flask import Flask, render_template, redirect, url_for, request, session, send_from_directory, jsonify, abort,send_file, Response
from werkzeug.security import check_password_hash
import sqlite3
import face_recognition
import numpy as np
import base64
import cv2
import os
import csv
import io
from export_utils import exportar_pdf 
from datetime import datetime
from werkzeug.utils import secure_filename
import logging
from facial_utils import identificar_rosto, carregar_rostos_conhecidos_incremental,salvar_cache, carregar_cache

known_face_encodings, known_face_names, known_face_data, known_face_estruturas = carregar_cache()
if not known_face_encodings:
    known_face_encodings, known_face_names, known_face_data, known_face_estruturas = carregar_rostos_conhecidos_incremental()
    salvar_cache(known_face_encodings, known_face_names, known_face_data, known_face_estruturas)

app = Flask(__name__)
app.secret_key = '945718730Jpn'

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


#Acessar a pasta de foto


ADMINISTRADORES = ['admin']  # Adicione os usuários autorizados aqui

@app.route('/known_faces/<filename>')
def known_faces(filename):
    usuario = session.get('usuario')
    if not usuario or usuario not in ADMINISTRADORES:
        abort(403)  # Acesso negado

    caminho = os.path.join('known_faces', filename)
    if not os.path.exists(caminho):
        abort(404)

    return send_from_directory('known_faces', filename)



def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        senha = request.form['senha']
        conn = get_db_connection()
        admin = conn.execute('SELECT * FROM administradores WHERE usuario = ?', (usuario,)).fetchone()
        conn.close()
        if admin and check_password_hash(admin['senha'], senha):
            session['usuario'] = usuario
            return redirect(url_for('dashboard'))
        else:
            return "Credenciais inválidas. <a href='/login'>Tentar novamente</a>"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('index'))

@app.route('/dashboard/', defaults={'curso': 'Informática'})
@app.route('/dashboard/<curso>')
def dashboard(curso):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    estudantes = conn.execute('SELECT * FROM estudantes WHERE curso = ?', (curso,)).fetchall()
    conn.close()
    return render_template('dashboard.html', estudantes=estudantes, curso=curso)

@app.route('/registrar', methods=['GET', 'POST'])
def registrar():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        nome = request.form['nome']
        dia_nascimento = request.form.get('dia_nascimento')
        mes_nascimento = request.form.get('mes_nascimento')
        ano_nascimento = request.form.get('ano_nascimento')
        data_nascimento = f"{ano_nascimento}-{int(mes_nascimento):02}-{int(dia_nascimento):02}"
        numero_bi = request.form['numero_bi']
        curso = request.form['curso']
        periodo = request.form['periodo']
        ano_frequencia = request.form['ano_frequencia']

        conn = get_db_connection()
        try:
            conn.execute('''
                INSERT INTO estudantes (nome, data_nascimento, numero_bi, curso, periodo, ano_frequencia)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (nome, data_nascimento, numero_bi, curso, periodo, ano_frequencia))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return "Erro: Número de BI já registrado."
        conn.close()

        caminho_foto = os.path.join("known_faces", f"{numero_bi}.jpg")
        imagem_capturada = request.form.get('imagem_capturada')
        if imagem_capturada:
            try:
                header, encoded = imagem_capturada.split(",", 1)
                imagem_bytes = base64.b64decode(encoded)
                with open(caminho_foto, "wb") as f:
                    f.write(imagem_bytes)
            except Exception as e:
                print("Erro ao salvar imagem:", e)
        elif 'foto_manual' in request.files:
            arquivo = request.files['foto_manual']
            if arquivo and arquivo.filename:
                arquivo.save(caminho_foto)
        return redirect(url_for('dashboard'))
    return render_template('registrar.html')

@app.route('/entradas', methods=['GET'])
def entradas():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    curso = request.args.get('curso', 'Informática')
    termo = request.args.get('termo', '').strip()
    data_inicio = request.args.get('data_inicio', '').strip()
    data_fim = request.args.get('data_fim', '').strip()

    conn = get_db_connection()
    cursor = conn.cursor()
    sql = '''
        SELECT e.id, e.data_hora, s.nome, s.numero_bi, s.curso
        FROM entradas e
        INNER JOIN estudantes s ON e.estudante_id = s.id
        WHERE s.curso = ?
    '''
    params = [curso]

    if termo:
        sql += ' AND (s.nome LIKE ? OR s.numero_bi LIKE ?)'
        params += [f'%{termo}%', f'%{termo}%']

    if data_inicio:
        sql += ' AND date(e.data_hora) >= date(?)'
        params.append(data_inicio)

    if data_fim:
        sql += ' AND date(e.data_hora) <= date(?)'
        params.append(data_fim)

    sql += ' ORDER BY e.data_hora DESC'
    cursor.execute(sql, tuple(params))
    registros = cursor.fetchall()
    conn.close()

    return render_template('entradas.html', registros=registros, curso=curso, termo=termo, data_inicio=data_inicio, data_fim=data_fim)

@app.route('/excluir_entrada/<int:id>')
def excluir_entrada(id):
    if 'usuario' not in session:
        return redirect(url_for('login'))
    conn = get_db_connection()
    conn.execute('DELETE FROM entradas WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('entradas'))

@app.route('/reconhecer')
def reconhecer():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('reconhecer.html')

def registrar_entrada(numero_bi):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM estudantes WHERE numero_bi = ?", (numero_bi,))
    estudante = cursor.fetchone()
    if not estudante:
        conn.close()
        return f"❌ Estudante com BI {numero_bi} não encontrado."
    estudante_id = estudante["id"]
    hoje = datetime.now().strftime('%Y-%m-%d')
    cursor.execute("SELECT * FROM entradas WHERE estudante_id = ? AND data_hora LIKE ?", (estudante_id, hoje + '%'))
    if cursor.fetchone():
        conn.close()
        return f"ℹ️ Entrada já registrada hoje para {numero_bi}"
    agora = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("INSERT INTO entradas (estudante_id, data_hora) VALUES (?, ?)", (estudante_id, agora))
    conn.commit()
    conn.close()
    return f"✅ Entrada registrada às {agora} para {numero_bi}"

@app.route('/processar_reconhecimento', methods=['POST'])
def processar_reconhecimento():
    if 'usuario' not in session:
        return jsonify({"sucesso": False, "mensagem": "Acesso negado."})

    dados = request.get_json()
    imagem_base64 = dados.get('imagem', '')
    if not imagem_base64:
        return jsonify({"sucesso": False, "mensagem": "Imagem não recebida."})

    try:
        header, encoded = imagem_base64.split(",", 1)
        imagem_bytes = base64.b64decode(encoded)
        nparr = np.frombuffer(imagem_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        resultado = identificar_rosto(frame, known_face_encodings, known_face_names, known_face_data, known_face_estruturas)

        if not resultado.get("sucesso"):
            return jsonify({"sucesso": False, "mensagem": resultado.get("mensagem", "Erro")})

        numero_bi = resultado["numero_bi"]
        dados = resultado["dados"]
        top, right, bottom, left = resultado["coordenadas"]
        altura, largura = resultado["dimensoes"]

        mensagem_entrada = registrar_entrada(numero_bi)
        dados["url_imagem"] = url_for('known_faces', filename=f"{numero_bi}.jpg")

        return jsonify({
            "sucesso": True,
            "mensagem": mensagem_entrada,
            "dimensoes": {
                "top": top, "right": right, "bottom": bottom, "left": left,
                "videoWidth": largura, "videoHeight": altura
            },
            "dados": dados
        })

    except Exception as e:
        logging.error(f"Erro técnico: {e}")
        return jsonify({"sucesso": False, "mensagem": f"⚠️ Erro técnico: {str(e)}"})
#recarregar Rosto
@app.route('/recarregar_rostos', methods=['POST'])
def recarregar_rostos():
    global known_face_encodings, known_face_names, known_face_data, known_face_estruturas

    existentes = set(known_face_names)
    novos_encodings, novos_nomes, novos_dados, novos_estruturas = carregar_rostos_conhecidos_incremental(existentes)

    if not novos_nomes:
        return jsonify({"sucesso": True, "mensagem": "ℹ️ Nenhum novo rosto foi encontrado."})

    known_face_encodings.extend(novos_encodings)
    known_face_names.extend(novos_nomes)
    known_face_data.update(novos_dados)
    known_face_estruturas.update(novos_estruturas)

    return jsonify({
        "sucesso": True,
        "mensagem": f"✅ {len(novos_nomes)} novo(s) rosto(s) carregado(s)."
    })
    from facial_utils import salvar_cache
salvar_cache(known_face_encodings, known_face_names, known_face_data, known_face_estruturas)


# O restante das rotas permanece igual (gerenciar_estudante, verificar_rosto, etc.)
...

# (continuação do código anterior)

@app.route('/estudante/<int:id>', methods=['GET', 'POST'])
def gerenciar_estudante(id):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    estudante = conn.execute('SELECT * FROM estudantes WHERE id = ?', (id,)).fetchone()
    if not estudante:
        conn.close()
        return "Estudante não encontrado."

    caminho_foto = os.path.join('known_faces', f"{estudante['numero_bi']}.jpg")
    existe_foto = os.path.exists(caminho_foto)

    if request.method == 'POST':
        if 'eliminar' in request.form:
            conn.execute('DELETE FROM estudantes WHERE id = ?', (id,))
            conn.execute('DELETE FROM entradas WHERE estudante_id = ?', (id,))
            conn.commit()
            conn.close()
            if os.path.exists(caminho_foto):
                os.remove(caminho_foto)
            return redirect(url_for('dashboard'))

        if 'editar' in request.form:
            nome = request.form['nome']
            numero_bi = request.form['numero_bi']
            curso = request.form['curso']
            periodo = request.form['periodo']
            ano_frequencia = request.form['ano_frequencia']
            data_nascimento = request.form.get('data_nascimento')
            conn.execute('''
                UPDATE estudantes
                SET nome = ?, numero_bi = ?, curso = ?, periodo = ?, ano_frequencia = ?, data_nascimento = ?
                WHERE id = ?
            ''', (nome, numero_bi, curso, periodo, ano_frequencia, data_nascimento, id))
            conn.commit()
            if 'nova_foto' in request.files:
                arquivo = request.files['nova_foto']
                if arquivo and arquivo.filename:
                    caminho_foto_novo = os.path.join('known_faces', f"{numero_bi}.jpg")
                    arquivo.save(caminho_foto_novo)
            conn.close()
            return redirect(url_for('dashboard', curso=curso))

    conn.close()
    return render_template('gerenciar_estudante.html', estudante=estudante, existe_foto=existe_foto, now=datetime.now().timestamp())


@app.route('/verificar_rosto', methods=['POST'])
def verificar_rosto():
    dados = request.get_json()
    imagem_base64 = dados.get('imagem', '')
    if not imagem_base64:
        return jsonify({"sucesso": False, "mensagem": "Imagem não recebida."})
    try:
        header, encoded = imagem_base64.split(",", 1)
        imagem_bytes = base64.b64decode(encoded)
        nparr = np.frombuffer(imagem_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        face_locations = face_recognition.face_locations(rgb_small)
        if not face_locations:
            return jsonify({"sucesso": False, "mensagem": "❌ Nenhum rosto detectado."})
        top, right, bottom, left = face_locations[0]
        scale = 4
        return jsonify({
            "sucesso": True,
            "dimensions": {
                "top": top * scale,
                "right": right * scale,
                "bottom": bottom * scale,
                "left": left * scale
            }
        })
    except Exception as e:
        return jsonify({"sucesso": False, "mensagem": f"Erro: {str(e)}"})
   #Opções 
@app.route('/opcoes')
def opcoes():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    return render_template('opcoes.html')
#Backup
@app.route('/backup', methods=['POST'])
def gerar_backup():
    if 'usuario' not in session:
        return jsonify({'sucesso': False, 'mensagem': 'Acesso negado'})

    import zipfile
    import io
    from datetime import datetime

    data = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        if os.path.exists('database.db'):
            zipf.write('database.db')
        for root, _, files in os.walk('known_faces'):
            for file in files:
                caminho_completo = os.path.join(root, file)
                caminho_rel = os.path.relpath(caminho_completo)
                zipf.write(caminho_completo, arcname=caminho_rel)

    zip_buffer.seek(0)
    return send_file(
        zip_buffer,
        as_attachment=True,
        download_name=f'backup_{data}.zip',
        mimetype='application/zip'
    )
#exportar_csv
@app.route('/exportar_csv', methods=['POST'])
def exportar_csv():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    tipo = request.form.get('tipo', 'entradas_csv')
    conn = get_db_connection()

    if tipo.endswith('_pdf'):
        if tipo.startswith('estudantes'):
            dados = conn.execute('SELECT * FROM estudantes').fetchall()
            return exportar_pdf('estudantes', dados)
        else:
            dados = conn.execute('''
                SELECT e.id, e.data_hora, s.nome, s.numero_bi, s.curso
                FROM entradas e
                INNER JOIN estudantes s ON e.estudante_id = s.id
                ORDER BY e.data_hora DESC
            ''').fetchall()
            return exportar_pdf('entradas', dados)

    output = io.StringIO()
    writer = csv.writer(output)

    if tipo.startswith('estudantes'):
        dados = conn.execute('SELECT * FROM estudantes').fetchall()
        writer.writerow(['ID', 'Nome', 'Número BI', 'Curso', 'Período', 'Ano Frequência', 'Data Nascimento'])
        for est in dados:
            writer.writerow([est['id'], est['nome'], est['numero_bi'], est['curso'], est['periodo'], est['ano_frequencia'], est['data_nascimento']])
        nome_arquivo = 'estudantes.csv'
    else:
        dados = conn.execute('''
            SELECT e.id, e.data_hora, s.nome, s.numero_bi, s.curso
            FROM entradas e
            INNER JOIN estudantes s ON e.estudante_id = s.id
            ORDER BY e.data_hora DESC
        ''').fetchall()
        writer.writerow(['ID Entrada', 'Data/Hora', 'Nome', 'Número BI', 'Curso'])
        for e in dados:
            writer.writerow([e['id'], e['data_hora'], e['nome'], e['numero_bi'], e['curso']])
        nome_arquivo = 'entradas.csv'

    conn.close()
    output.seek(0)

    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename={nome_arquivo}'}
    )


#Redefinir
@app.route('/resetar_banco', methods=['POST'])
def resetar_banco():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    tipo = request.form.get('tipo')
    conn = get_db_connection()
    cursor = conn.cursor()

    if tipo == 'entradas':
        cursor.execute('DELETE FROM entradas')
    elif tipo == 'estudantes':
        cursor.execute('DELETE FROM entradas')
        cursor.execute('DELETE FROM estudantes')
        for nome_arquivo in os.listdir('known_faces'):
            os.remove(os.path.join('known_faces', nome_arquivo))
    elif tipo == 'tudo':
        cursor.execute('DELETE FROM entradas')
        cursor.execute('DELETE FROM estudantes')
        for nome_arquivo in os.listdir('known_faces'):
            os.remove(os.path.join('known_faces', nome_arquivo))

    conn.commit()
    conn.close()

    return redirect(url_for('opcoes'))


if __name__ == '__main__':
    from facial_utils import carregar_cache, salvar_cache, carregar_rostos_conhecidos_incremental

    known_face_encodings, known_face_names, known_face_data, known_face_estruturas = carregar_cache()
    if not known_face_encodings:
        known_face_encodings, known_face_names, known_face_data, known_face_estruturas = carregar_rostos_conhecidos_incremental()
        salvar_cache(known_face_encodings, known_face_names, known_face_data, known_face_estruturas)

    app.run(debug=True, host='0.0.0.0', port=5000)



