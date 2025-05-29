from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
import qrcode
from io import BytesIO
from PIL import Image

def gerar_crachas(inscritos):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    largura_cracha = 9 * cm
    altura_cracha = 6 * cm
    espacamento_coluna = 0.5 * cm
    espacamento_linha = 0.5 * cm

    colunas = 2
    linhas = 4  # agora com 4 linhas

    largura_total = colunas * largura_cracha + (colunas - 1) * espacamento_coluna
    altura_total = linhas * altura_cracha + (linhas - 1) * espacamento_linha

    margem_esquerda = (A4[0] - largura_total) / 2
    margem_superior = A4[1] - 2 * cm  # margem de 2 cm no topo

    crachas_por_pagina = colunas * linhas
    total = len(inscritos)

    for i, inscrito in enumerate(inscritos):
        index = i % crachas_por_pagina
        col = index % colunas
        row = index // colunas

        x = margem_esquerda + col * (largura_cracha + espacamento_coluna)
        y = margem_superior - (row + 1) * altura_cracha - row * espacamento_linha

        # Borda (opcional)
        c.rect(x, y, largura_cracha, altura_cracha)

        # QR Code
        qr = qrcode.make(inscrito[2])
        qr_img = qr.resize((120, 120))
        qr_buffer = BytesIO()
        qr_img.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)

        qr_reader = ImageReader(qr_buffer)
        c.drawImage(
            qr_reader,
            x + (largura_cracha - 120) / 2,
            y + altura_cracha - 125,
            width=120,
            height=120
        )

        # Nome
        c.setFont("Helvetica-Bold", 11)
        c.drawCentredString(x + largura_cracha / 2, y + altura_cracha - 135 - 0, formatar_nome(inscrito[0]))

        # Igreja
        c.setFont("Helvetica", 10)
        c.drawCentredString(x + largura_cracha / 2, y + altura_cracha - 135 - 10, inscrito[1])

        # Igreja
        c.setFont("Helvetica", 9)
        c.drawCentredString(x + largura_cracha / 2, y + altura_cracha - 135 - 25, 'Mini seminário 07/06/2025')

        if (index + 1) == crachas_por_pagina and (i + 1) < total:
            c.showPage()

    c.save()
    buffer.seek(0)
    return buffer

def formatar_nome(nome_completo):
    partes = nome_completo.strip().split()
    if len(partes) == 1:
        return partes[0].upper()
    return f"{partes[0]} {partes[-1]}".upper()
