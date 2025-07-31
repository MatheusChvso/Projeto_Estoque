import sys
import requests
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QMessageBox, QMainWindow, QHBoxLayout
)
from PySide6.QtGui import QPixmap, QAction
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    # ...
    QSizePolicy
)
# ==============================================================================
# VARIÁVEIS GLOBAIS
# ==============================================================================
# Guardamos o token aqui para que a janela principal possa usá-lo no futuro.
access_token = None


# ==============================================================================
# CLASSE DA JANELA DE LOGIN
# ==============================================================================
class JanelaLogin(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Meu Sistema de Gestão - Login")
        self.resize(300, 350)
        self.janela_principal = None # Para guardar a referência da janela principal

        # Layout e Widgets
        layout = QVBoxLayout()
        
        # Logo
        logo_pixmap = QPixmap("logo.png")
        logo_redimensionada = logo_pixmap.scaled(250, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.label_logo = QLabel()
        self.label_logo.setPixmap(logo_redimensionada)
        self.label_logo.setAlignment(Qt.AlignCenter)

        self.input_login = QLineEdit()
        self.input_login.setPlaceholderText("Digite seu login")
        self.input_senha = QLineEdit()
        self.input_senha.setPlaceholderText("Digite sua senha")
        self.input_senha.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.botao_login = QPushButton("Entrar")

        layout.addWidget(self.label_logo)
        layout.addWidget(QLabel("Login:"))
        layout.addWidget(self.input_login)
        layout.addWidget(QLabel("Senha:"))
        layout.addWidget(self.input_senha)
        layout.addWidget(self.botao_login)
        
        self.setLayout(layout)

        # Conexão do botão
        self.botao_login.clicked.connect(self.fazer_login)

    def fazer_login(self):
        global access_token
        login = self.input_login.text()
        senha = self.input_senha.text()

        if not login or not senha:
            QMessageBox.warning(self, "Erro de Entrada", "Os campos de login e senha não podem estar vazios.")
            return

        url = "http://127.0.0.1:5000/api/login"
        dados = {"login": login, "senha": senha}

        try:
            response = requests.post(url, json=dados)
            if response.status_code == 200:
                access_token = response.json()['access_token']
                print("Login bem-sucedido! Token guardado.")
                
                self.close() # Fecha a janela de login
                self.janela_principal = JanelaPrincipal() # Cria a janela principal
                self.janela_principal.show() # Exibe a janela principal
            else:
                erro_msg = response.json().get('erro', 'Ocorreu um erro desconhecido.')
                QMessageBox.warning(self, "Erro de Login", f"Falha no login: {erro_msg}")
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Erro de Conexão", f"Não foi possível conectar ao servidor: {e}")


# ==============================================================================
# CLASSE DA JANELA PRINCIPAL
# ==============================================================================
class JanelaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema de Gestão de Estoque")
        self.resize(1280, 720)
        
        # --- APLICAÇÃO DE ESTILOS (QSS) ---
        self.setStyleSheet("""
        /* Estilo geral da janela */
        QMainWindow {
            background-color: #f2f2f2; /* Um cinza bem claro */
    }

        /* Estilo do painel lateral */
        #painelLateral {
            background-color: #e3e3e3; /* Um cinza um pouco mais escuro */
    }

        /* Estilo dos botões DENTRO do painel lateral */
        #painelLateral QPushButton {
            background-color: #dcdcdc;
            color: #333;
            border: 1px solid #c0c0c0;
            border-radius: 5px;
            padding: 10px;
            font-size: 16px;
            text-align: left; /* Alinha o texto à esquerda */
    }

        #painelLateral QPushButton:hover {
        background-color: #cce7ff; /* Um azul claro ao passar o mouse */
        border: 1px solid #0078d7;
    }
""")


        # --- BARRA DE MENUS ---
        menu_bar = self.menuBar()
        
        # Menu Arquivo
        menu_arquivo = menu_bar.addMenu("&Arquivo")
        acao_sair = QAction("Sair", self)
        acao_sair.triggered.connect(self.close) # Conecta a ação para fechar a janela
        menu_arquivo.addAction(acao_sair)

        # Menu Cadastros
        menu_cadastros = menu_bar.addMenu("&Cadastros")
        menu_cadastros.addAction("Produtos...")
        menu_cadastros.addAction("Fornecedores...")
        menu_cadastros.addAction("Naturezas...")
        
        # TODO: Adicionar lógica para mostrar este menu apenas para Admins
        menu_cadastros.addSeparator()
        menu_cadastros.addAction("Usuários...")

        # Menu Estoque
        menu_estoque = menu_bar.addMenu("&Estoque")
        menu_estoque.addAction("Visualizar Estoque...")
        menu_estoque.addAction("Entrada Rápida por Código...")
        
        # --- LAYOUT PRINCIPAL (HORIZONTAL) ---
        layout_principal = QHBoxLayout()

        # --- PAINEL DE NAVEGAÇÃO LATERAL ---
        painel_lateral = QWidget()
        painel_lateral.setObjectName("painelLateral")
        painel_lateral.setFixedWidth(200)
        layout_painel_lateral = QVBoxLayout(painel_lateral)
        layout_painel_lateral.setAlignment(Qt.AlignTop)

        # Botões do painel lateral
        btn_produtos = QPushButton("Produtos")
        btn_estoque = QPushButton("Estoque")
        btn_fornecedores = QPushButton("Fornecedores")
        btn_naturezas = QPushButton("Naturezas")
        btn_usuarios = QPushButton("Usuários")
        
        
        
        # Definimos que os botões podem expandir verticalmente
        btn_produtos.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        btn_estoque.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        btn_fornecedores.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        btn_naturezas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        btn_usuarios.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        layout_painel_lateral.addWidget(btn_produtos)
        layout_painel_lateral.addWidget(btn_estoque)
        layout_painel_lateral.addWidget(btn_fornecedores)
        layout_painel_lateral.addWidget(btn_naturezas)
        layout_painel_lateral.addWidget(btn_usuarios)

        layout_principal.addWidget(painel_lateral)
        layout_painel_lateral.addStretch(1)
        # --- ÁREA DE CONTEÚDO PRINCIPAL ---
        self.area_de_conteudo = QWidget()
        layout_principal.addWidget(self.area_de_conteudo)

        # Widget central para conter o layout principal
        widget_central = QWidget()
        widget_central.setLayout(layout_principal)
        self.setCentralWidget(widget_central)

        # --- BARRA DE STATUS ---
        self.statusBar().showMessage("Bem-vindo! Usuário logado: [Nome do Usuário]")


# ==============================================================================
# BLOCO DE EXECUÇÃO PRINCIPAL
# ==============================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # A aplicação agora começa pela janela de login
    janela_login = JanelaLogin()
    janela_login.show()
    
    sys.exit(app.exec())