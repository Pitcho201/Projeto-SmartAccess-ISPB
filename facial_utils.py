import os
import sqlite3
import face_recognition
import pickle
from landmark_utils import extrair_landmarks_da_imagem, extrair_vetor_estrutural, calcular_distancia_estrutural


def buscar_dados_estudante(numero_bi):
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    estudante = conn.execute("SELECT * FROM estudantes WHERE numero_bi = ?", (numero_bi,)).fetchone()
    conn.close()
    return dict(estudante) if estudante else {}


def carregar_rostos_conhecidos_incremental(existing_names=None):
    encodings_novos = []
    nomes_novos = []
    dados_novos = {}
    vetores_estruturais_novos = {}

    if existing_names is None:
        existing_names = set()

    print("🔄 Verificando novos rostos...")

    for filename in os.listdir('known_faces'):
        if filename.endswith(('.jpg', '.jpeg', '.png')):
            numero_bi = os.path.splitext(filename)[0]
            if numero_bi in existing_names:
                continue

            path = os.path.join('known_faces', filename)
            imagem = face_recognition.load_image_file(path)
            encoding = face_recognition.face_encodings(imagem)
            _, landmarks = extrair_landmarks_da_imagem(imagem)
            vetor_estrutural = extrair_vetor_estrutural(landmarks)

            if encoding:
                encodings_novos.append(encoding[0])
                nomes_novos.append(numero_bi)
                dados_novos[numero_bi] = buscar_dados_estudante(numero_bi)
                vetores_estruturais_novos[numero_bi] = vetor_estrutural
                print(f"✅ Novo rosto carregado: {numero_bi}")
            else:
                print(f"⚠️ Nenhum rosto detectado em {filename}")

    print(f"✔️ Total de novos rostos: {len(encodings_novos)}")
    return encodings_novos, nomes_novos, dados_novos, vetores_estruturais_novos


def identificar_rosto(frame, encodings_base, nomes_base, dados_base, vetores_estruturais_base, tolerance=0.4):
    import cv2
    import numpy as np

    small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
    rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_small)
    encodings = face_recognition.face_encodings(rgb_small, face_locations)

    if not encodings or not face_locations:
        return {"sucesso": False, "mensagem": "❌ Nenhum rosto detectado."}

    face_areas = [(b - t) * (r - l) for t, r, b, l in face_locations]
    largest_index = int(np.argmax(face_areas))
    face_encoding = encodings[largest_index]
    top, right, bottom, left = face_locations[largest_index]

    landmarks = face_recognition.face_landmarks(rgb_small, [face_locations[largest_index]])
    vetor_estrutural = extrair_vetor_estrutural(landmarks[0]) if landmarks else None

    matches = face_recognition.compare_faces(encodings_base, face_encoding, tolerance=tolerance)
    face_distances = face_recognition.face_distance(encodings_base, face_encoding)

    melhor_indice = None
    menor_distancia = float('inf')

    for i, match in enumerate(matches):
        if match:
            estrutura_ref = vetores_estruturais_base.get(nomes_base[i])
            distancia_geo = calcular_distancia_estrutural(vetor_estrutural, estrutura_ref)
            if distancia_geo < menor_distancia:
                menor_distancia = distancia_geo
                melhor_indice = i

    if melhor_indice is not None:
        numero_bi = nomes_base[melhor_indice]
        dados_estudante = dados_base.get(numero_bi, {})
        return {
            "sucesso": True,
            "numero_bi": numero_bi,
            "dados": dados_estudante,
            "coordenadas": (top * 4, right * 4, bottom * 4, left * 4),
            "dimensoes": frame.shape[:2]
        }

    return {"sucesso": False, "mensagem": "❌ Rosto não reconhecido."}


def salvar_cache(encodings, nomes, dados, estruturas, caminho='face_cache.pkl'):
    with open(caminho, 'wb') as f:
        pickle.dump((encodings, nomes, dados, estruturas), f)

def carregar_cache(caminho='face_cache.pkl'):
    if os.path.exists(caminho):
        with open(caminho, 'rb') as f:
            return pickle.load(f)
    return None, None, None, None
