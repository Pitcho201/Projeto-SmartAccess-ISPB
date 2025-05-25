import face_recognition
import numpy as np
from scipy.spatial.distance import euclidean


def extrair_vetor_estrutural(landmarks):
    """
    Extrai um vetor numérico a partir de landmarks faciais.
    Medidas geométricas: distâncias e proporções entre pontos principais.
    """
    def dist(p1, p2):
        return euclidean(p1, p2)

    try:
        olho_esq = landmarks['left_eye']
        olho_dir = landmarks['right_eye']
        nariz = landmarks['nose_tip']
        boca = landmarks['top_lip'] + landmarks['bottom_lip']
        queixo = landmarks['chin']

        centro_olhos = np.mean([olho_esq[0], olho_dir[3]], axis=0)
        centro_boca = np.mean([boca[0], boca[6]], axis=0)
        centro_nariz = nariz[2]
        centro_queixo = queixo[8]

        vetor = [
            dist(olho_esq[0], olho_esq[3]),
            dist(olho_dir[0], olho_dir[3]),
            dist(olho_esq[0], olho_dir[3]),
            dist(centro_olhos, centro_nariz),
            dist(centro_nariz, centro_boca),
            dist(centro_boca, centro_queixo),
            dist(queixo[0], queixo[16]),
            dist(boca[0], boca[6]),
            dist(boca[3], boca[9])
        ]
        return np.array(vetor)
    except (KeyError, IndexError):
        return None


def calcular_distancia_estrutural(v1, v2):
    if v1 is None or v2 is None:
        return float('inf')
    return euclidean(v1, v2)


def extrair_landmarks_da_imagem(image):
    face_locations = face_recognition.face_locations(image)
    if not face_locations:
        return None, None

    all_landmarks = face_recognition.face_landmarks(image, face_locations)
    if all_landmarks:
        return face_locations[0], all_landmarks[0]
    return None, None
