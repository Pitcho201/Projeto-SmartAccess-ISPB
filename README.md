SmartAccess ISPBié

Sistema de controle de entrada de estudantes com reconhecimento facial, desenvolvido para o Instituto Superior Politécnico do Bié.

🎯 Objetivo

Automatizar o registro de presença de estudantes através de reconhecimento facial, integrando banco de dados, imagens e controle administrativo.

---

🧰 Tecnologias utilizadas

- **Python 3.9+**
- **Flask**
- **face_recognition**
- **OpenCV**
- **SQLite**
- **Bootstrap 5**
- **JavaScript (getUserMedia, validações)**

---

🖥️ Funcionalidades

- Reconhecimento facial com webcam, celular ou câmera USB
- Registro automático da presença com data e hora
- Cadastro, edição e eliminação de estudantes
- Upload ou captura de imagem do rosto
- Filtros por curso e data de entrada
- Alertas visuais e sonoros



⚙️ Instalação

```bash
git clone https://github.com/Pitcho201/Projeto-SmartAccess-ISPB.git
cd Projeto-SmartAccess-ISPB
python -m venv venv39
venv39\Scripts\activate    # Windows
pip install -r requirements.txt
