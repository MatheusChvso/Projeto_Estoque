import sys
import requests
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout
from PySide6.QtWidgets import QMessageBox
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt

# --- Bloco Principal de Execução ---
if __name__ == "__main__":
    
# --- FUNÇÃO SLOT ---
    def fazer_login():
        login = input_login.text()
        senha = input_senha.text()

    # 1. Validar se os campos não estão vazios
        if not login or not senha:
            QMessageBox.warning(janela, "Erro de Entrada", "Os campos de login e senha não podem estar vazios.")
            return # Para a execução da função aqui

    # 2. Montar o URL e os dados para enviar à API
        url = "http://127.0.0.1:5000/api/login"
        dados = {"login": login, "senha": senha}

        try:
        # 3. Fazer o pedido POST para a API
            response = requests.post(url, json=dados)

        # 4. Tratar a resposta da API
            if response.status_code == 200:
            # Sucesso! A API retornou o token.
                access_token = response.json()['access_token']
                print("Login bem-sucedido! Token:", access_token) # Mantemos o print para depuração
            
                QMessageBox.information(janela, "Sucesso", "Login realizado com sucesso!")
            # Futuramente: aqui vamos guardar o token e abrir a janela principal do sistema.
            # Por agora, podemos fechar a aplicação após o sucesso.
                app.quit()

            else:
            # Falha no login (credenciais erradas, etc.)
                erro_msg = response.json().get('erro', 'Ocorreu um erro desconhecido.')
                QMessageBox.warning(janela, "Erro de Login", f"Falha no login: {erro_msg}")

        except requests.exceptions.RequestException as e:
        # Falha de conexão (ex: o servidor back-end não está a funcionar)
            QMessageBox.critical(janela, "Erro de Conexão", f"Não foi possível conectar ao servidor: {e}")
        
        

    # Cria a "aplicação"
    app = QApplication(sys.argv)

    # Cria a nossa janela
    janela = QWidget()
    janela.setWindowTitle("Meu Sistema de Gestão - Login")
    janela.resize(300, 250) # Aumentei um pouco a altura para a logo

    # --- CARREGAR E REDIMENSIONAR A LOGO ---
    logo_pixmap = QPixmap("logo.png")
    logo_redimensionada = logo_pixmap.scaled(250, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    label_logo = QLabel()
    label_logo.setPixmap(logo_redimensionada)
    label_logo.setAlignment(Qt.AlignCenter)

    # --- CRIAÇÃO DOS WIDGETS (COMPONENTES) ---
    label_login = QLabel("Login:")
    input_login = QLineEdit()
    label_senha = QLabel("Senha:")
    input_senha = QLineEdit()
    input_senha.setEchoMode(QLineEdit.EchoMode.Password)
    botao_login = QPushButton("Entrar")

    # --- ORGANIZAÇÃO DOS WIDGETS (LAYOUT) ---
    layout = QVBoxLayout()
    layout.addWidget(label_logo)
    layout.addWidget(label_login)
    layout.addWidget(input_login)
    layout.addWidget(label_senha)
    layout.addWidget(input_senha)
    layout.addWidget(botao_login)
    janela.setLayout(layout)

    # --- CONEXÃO DO SINAL AO SLOT ---
    botao_login.clicked.connect(fazer_login)

    # Exibe a janela
    janela.show()

    # Inicia o loop da aplicação
    sys.exit(app.exec())