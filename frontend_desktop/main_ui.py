import sys
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QSpacerItem, QSizePolicy
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt
# --- Bloco Principal de Execução ---
if __name__ == "__main__":
    app = QApplication(sys.argv)

    janela = QWidget()
    janela.setWindowTitle("Meu Sistema de Gestão - Login")
    janela.resize(500, 200) # Ajustei o tamanho para uma janela de login

    
    
    
    
    
    # CÓDIGO NOVO E CORRIGIDO
# --- CARREGAR E REDIMENSIONAR A LOGO ---

# 1. Carrega a imagem original do ficheiro
    logo_pixmap = QPixmap("logo.png")

# 2. Cria uma versão redimensionada da imagem
#    Defina a largura e altura MÁXIMAS que você deseja para a logo.
#    Ajuste estes valores (250, 150) conforme necessário.
    logo_redimensionada = logo_pixmap.scaled(550, 225, Qt.KeepAspectRatio, Qt.SmoothTransformation)

# 3. Cria o QLabel e define a imagem JÁ REDIMENSIONADA
    label_logo = QLabel()
    label_logo.setPixmap(logo_redimensionada)
    label_logo.setAlignment(Qt.AlignCenter)
    
    
    # --- CRIAÇÃO DOS WIDGETS (COMPONENTES) ---
    # Cria os rótulos de texto
    label_login = QLabel("Login:")
    label_senha = QLabel("Senha:")

    # Cria as caixas de entrada de texto
    input_login = QLineEdit()
    input_senha = QLineEdit()
    # Configura o campo de senha para esconder o que é digitado
    input_senha.setEchoMode(QLineEdit.EchoMode.Password)

    # Cria o botão de login
    botao_login = QPushButton("Entrar")

    # --- ORGANIZAÇÃO DOS WIDGETS (LAYOUT) ---)
    layout = QVBoxLayout()
    
    layout.addWidget(label_logo) # Adiciona a logo no topo
    layout.addWidget(label_login)
    layout.addSpacerItem(QSpacerItem(10, 10, QSizePolicy.Minimum, QSizePolicy.Expanding)) # Espaço no topo

    layout.addWidget(label_login)
    layout.addWidget(input_login)
    layout.addWidget(label_senha)
    layout.addWidget(input_senha)
    layout.addWidget(botao_login)

    layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)) # Espaço abaixo

    janela.setLayout(layout) 

    # Exibe a janela
    janela.show()

    # Inicia o loop da aplicação
    sys.exit(app.exec())