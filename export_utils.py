import os, io
from datetime import datetime
from flask import send_file, current_app
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import cm

def exportar_pdf(tipo, dados):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=3*cm, bottomMargin=3*cm)

    styles = getSampleStyleSheet()
    elementos = []

    # Cabeçalho com logo e texto
    logo_path = os.path.join(current_app.root_path, 'static', 'img', 'log.jpg')
    if os.path.exists(logo_path):
        img = Image(logo_path, width=3*cm, height=3*cm)
        img.hAlign = 'CENTER'
        elementos.append(img)
        elementos.append(Spacer(1, 0.2*cm))

    elementos.append(Paragraph("<b><font size=10 color='black'>MINISTÉRIO DO ENSINO SUPERIOR, CIÊNCIA, TECNOLOGIA E INOVAÇÃO</font></b>", styles['Title']))
    elementos.append(Paragraph("<b><font size=10 color='black'>INSTITUTO SUPERIOR POLITÉCNICO DO BIÉ</font></b>", styles['Title']))
    
    elementos.append(Spacer(1, 0.5*cm))

    titulo = "Lista de Estudantes" if tipo == 'estudantes' else "Registros de Entradas"
    elementos.append(Paragraph(f"<b><font size=13>{titulo}</font></b>", styles['Title']))
    elementos.append(Spacer(1, 0.2*cm))
    data_hora = datetime.now().strftime('%d/%m/%Y %H:%M')
    elementos.append(Paragraph(f"Gerado em: {data_hora}", styles['Normal']))
    elementos.append(Spacer(1, 0.5*cm))

    # Dados da tabela
    if tipo == 'estudantes':
        headers = ['ID', 'Nome', 'Nº BI', 'Curso', 'Período', 'Ano', 'Nascimento']
        linhas = [[
            est['id'], est['nome'], est['numero_bi'], est['curso'],
            est['periodo'], est['ano_frequencia'], est['data_nascimento']
        ] for est in dados]
    else:
        headers = ['ID', 'Data/Hora', 'Nome', 'Nº BI', 'Curso']
        linhas = [[e['id'], e['data_hora'], e['nome'], e['numero_bi'], e['curso']] for e in dados]

    data = [headers] + linhas
    tabela = Table(data, repeatRows=1, hAlign='LEFT')
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6)
    ]))

    elementos.append(tabela)
    elementos.append(Spacer(1, 1*cm))

    # Rodapé
    elementos.append(Spacer(1, 1*cm))
    rodape = [
        "E-mail: ispb.bie@gmail.com    NIF: 5000308765",
        "Telefone: 922408061",
        "Cidade do Cuito-Bié, entre as ruas: Padre Fidalgo, Artur de Paiva e Francisco de Leite Cardoso"
    ]
    for linha in rodape:
        elementos.append(Paragraph(f"<font size=8 color='black'>{linha}</font>", styles['Normal']))

    doc.build(elementos)
    buffer.seek(0)
    nome_arquivo = f'{tipo}.pdf'
    return send_file(buffer, mimetype='application/pdf', download_name=nome_arquivo, as_attachment=True)
