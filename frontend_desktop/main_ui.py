import sys
import requests
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QMessageBox, QMainWindow, QHBoxLayout,
    QStackedWidget, QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy,
    QDialog, QFormLayout, QDialogButtonBox
)
from PySide6.QtGui import QPixmap, QAction, QDoubleValidator
from PySide6.QtCore import Qt, QTimer

# ==============================================================================
# VARIÁVEIS GLOBAIS
# ==============================================================================
access_token = None


# ==============================================================================
# CLASSE DA JANELA DE LOGIN
# ==============================================================================
class JanelaLogin(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Meu Sistema de Gestão - Login")
        self.resize(300, 350)
        self.janela_principal = None

        layout = QVBoxLayout()
        
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
                self.close()
                self.janela_principal = JanelaPrincipal()
                self.janela_principal.show()
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
        self.setStyleSheet("""
            QMainWindow, QWidget { background-color: #f5f5f5; }
            #painelLateral { background-color: #e0e0e0; }
            #painelLateral QPushButton {
                background-color: #e0e0e0; color: #333; border: none;
                border-radius: 5px; padding: 12px; font-size: 16px; text-align: left;
            }
            #painelLateral QPushButton:hover { background-color: #cce7ff; }
            #painelLateral QPushButton:checked { background-color: #0078d7; color: white; }
            QMenuBar { background-color: #dcdcdc; color: #333; }
        """)

        menu_bar = self.menuBar()
        menu_arquivo = menu_bar.addMenu("&Arquivo")
        acao_sair = QAction("Sair", self)
        acao_sair.triggered.connect(self.close)
        menu_arquivo.addAction(acao_sair)
        menu_cadastros = menu_bar.addMenu("&Cadastros")
        self.acao_produtos = QAction("Produtos...", self)
        menu_cadastros.addAction(self.acao_produtos)

        widget_central = QWidget()
        self.setCentralWidget(widget_central)
        layout_principal = QHBoxLayout(widget_central)

        painel_lateral = QWidget()
        painel_lateral.setObjectName("painelLateral")
        painel_lateral.setFixedWidth(200)
        layout_painel_lateral = QVBoxLayout(painel_lateral)
        layout_painel_lateral.setAlignment(Qt.AlignTop)

        self.btn_dashboard = QPushButton("Dashboard")
        self.btn_produtos = QPushButton("Produtos")
        self.btn_estoque = QPushButton("Estoque")
        self.btn_fornecedores = QPushButton("Fornecedores")
        self.btn_naturezas = QPushButton("Naturezas")
        self.btn_usuarios = QPushButton("Usuários")

        layout_painel_lateral.addWidget(self.btn_dashboard)
        layout_painel_lateral.addWidget(self.btn_produtos)
        layout_painel_lateral.addWidget(self.btn_estoque)
        layout_painel_lateral.addWidget(self.btn_fornecedores)
        layout_painel_lateral.addWidget(self.btn_naturezas)
        layout_painel_lateral.addWidget(self.btn_usuarios)
        layout_painel_lateral.addStretch(1)
        layout_principal.addWidget(painel_lateral)

        self.stacked_widget = QStackedWidget()
        layout_principal.addWidget(self.stacked_widget)

        self.tela_dashboard = QLabel("Bem-vindo ao Sistema!\n\nSelecione uma opção no menu lateral para começar.")
        self.tela_dashboard.setAlignment(Qt.AlignCenter)
        self.tela_dashboard.setStyleSheet("font-size: 18px; color: #555;")
        self.tela_produtos = ProdutosWidget()
        self.tela_estoque = EstoqueWidget()

        self.stacked_widget.addWidget(self.tela_dashboard)
        self.stacked_widget.addWidget(self.tela_produtos)
        self.stacked_widget.addWidget(self.tela_estoque)

        self.btn_dashboard.clicked.connect(self.mostrar_tela_dashboard)
        self.btn_produtos.clicked.connect(self.mostrar_tela_produtos)
        self.acao_produtos.triggered.connect(self.mostrar_tela_produtos)
        self.btn_estoque.clicked.connect(self.mostrar_tela_estoque)

        self.statusBar().showMessage("Pronto.")

    def mostrar_tela_dashboard(self):
        self.stacked_widget.setCurrentWidget(self.tela_dashboard)

    def mostrar_tela_produtos(self):
        self.stacked_widget.setCurrentWidget(self.tela_produtos)

    def mostrar_tela_estoque(self):
        self.stacked_widget.setCurrentWidget(self.tela_estoque)


# ==============================================================================
# WIDGET DA TELA DE PRODUTOS
# ==============================================================================
class ProdutosWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.titulo = QLabel("Gestão de Produtos")
        self.titulo.setStyleSheet("font-size: 24px; font-weight: bold;")
        
        layout_botoes = QHBoxLayout()
        self.btn_adicionar = QPushButton("Adicionar Novo")
        self.btn_editar = QPushButton("Editar Selecionado")
        self.btn_excluir = QPushButton("Excluir Selecionado")
        layout_botoes.addWidget(self.btn_adicionar)
        layout_botoes.addWidget(self.btn_editar)
        layout_botoes.addWidget(self.btn_excluir)
        layout_botoes.addStretch(1)
        
        self.input_pesquisa = QLineEdit()
        self.input_pesquisa.setPlaceholderText("Buscar por nome ou código...")
        
        self.tabela_produtos = QTableWidget()
        self.tabela_produtos.setColumnCount(4)
        self.tabela_produtos.setHorizontalHeaderLabels(["Código", "Nome", "Descrição", "Preço"])
        self.tabela_produtos.setAlternatingRowColors(True)
        self.tabela_produtos.horizontalHeader().setStretchLastSection(True)
        self.tabela_produtos.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.layout.addWidget(self.titulo)
        self.layout.addLayout(layout_botoes)
        self.layout.addWidget(self.input_pesquisa)
        self.layout.addWidget(self.tabela_produtos)
        
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.carregar_produtos)

        self.btn_adicionar.clicked.connect(self.abrir_formulario_adicionar)
        self.btn_editar.clicked.connect(self.abrir_formulario_editar)
        self.input_pesquisa.textChanged.connect(self.iniciar_busca_timer)
        
        self.carregar_produtos()

    def abrir_formulario_adicionar(self):
        dialog = FormularioProdutoDialog(self)
        if dialog.exec():
            self.carregar_produtos()

    def abrir_formulario_editar(self):
        linha_selecionada = self.tabela_produtos.currentRow()
        if linha_selecionada < 0:
            QMessageBox.warning(self, "Seleção", "Por favor, selecione um produto na tabela para editar.")
            return
        item = self.tabela_produtos.item(linha_selecionada, 0)
        produto_id = item.data(Qt.UserRole)
        dialog = FormularioProdutoDialog(self, produto_id=produto_id)
        if dialog.exec():
            self.carregar_produtos()

    def iniciar_busca_timer(self):
        self.search_timer.stop()
        self.search_timer.start(300)

    def carregar_produtos(self):
        global access_token
        url = "http://127.0.0.1:5000/api/produtos"
        headers = {'Authorization': f'Bearer {access_token}'}
        params = {'search': self.input_pesquisa.text()} if self.input_pesquisa.text() else {}
        
        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                produtos = response.json()
                self.tabela_produtos.setRowCount(len(produtos))
                for linha, produto in enumerate(produtos):
                    item_codigo = QTableWidgetItem(produto['codigo'])
                    item_codigo.setData(Qt.UserRole, produto['id'])
                    self.tabela_produtos.setItem(linha, 0, item_codigo)
                    self.tabela_produtos.setItem(linha, 1, QTableWidgetItem(produto['nome']))
                    self.tabela_produtos.setItem(linha, 2, QTableWidgetItem(produto['descricao']))
                    self.tabela_produtos.setItem(linha, 3, QTableWidgetItem(produto['preco']))
            else:
                QMessageBox.warning(self, "Erro", f"Erro ao carregar produtos: {response.json().get('erro')}")
        except requests.exceptions.RequestException as e:
            print(f"Erro de Conexão: {e}")

# ==============================================================================
# WIDGET DA TELA DE ESTOQUE
# ==============================================================================
class EstoqueWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.titulo = QLabel("Saldos de Estoque")
        self.titulo.setStyleSheet("font-size: 24px; font-weight: bold;")
        self.tabela_estoque = QTableWidget()
        self.tabela_estoque.setColumnCount(3)
        self.tabela_estoque.setHorizontalHeaderLabels(["Código", "Nome do Produto", "Saldo Atual"])
        self.tabela_estoque.setAlternatingRowColors(True)
        self.tabela_estoque.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.layout.addWidget(self.titulo)
        self.layout.addWidget(self.tabela_estoque)
        self.carregar_dados_estoque()

    def carregar_dados_estoque(self):
        global access_token
        url = "http://127.0.0.1:5000/api/estoque/saldos"
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                saldos = response.json()
                self.tabela_estoque.setRowCount(len(saldos))
                for linha, item in enumerate(saldos):
                    self.tabela_estoque.setItem(linha, 0, QTableWidgetItem(item['codigo']))
                    self.tabela_estoque.setItem(linha, 1, QTableWidgetItem(item['nome']))
                    self.tabela_estoque.setItem(linha, 2, QTableWidgetItem(str(item['saldo_atual'])))
            else:
                QMessageBox.warning(self, "Erro", f"Erro ao carregar saldos: {response.json().get('msg') or response.json().get('erro')}")
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Erro de Conexão", f"Não foi possível conectar ao servidor: {e}")

# ==============================================================================
# JANELA DE DIÁLOGO PARA FORMULÁRIO DE PRODUTO
# ==============================================================================
class FormularioProdutoDialog(QDialog):
    def __init__(self, parent=None, produto_id=None):
        super().__init__(parent)
        self.produto_id = produto_id
        self.setWindowTitle("Adicionar Novo Produto" if self.produto_id is None else "Editar Produto")
        self.layout = QFormLayout(self)

        self.input_codigo = QLineEdit()
        self.input_nome = QLineEdit()
        self.input_descricao = QLineEdit()
        self.input_preco = QLineEdit()
        self.input_preco.setValidator(QDoubleValidator(0.00, 999999.99, 2))
        self.input_codigoB = QLineEdit()
        self.input_codigoC = QLineEdit()

        self.layout.addRow("Código:", self.input_codigo)
        self.layout.addRow("Nome:", self.input_nome)
        self.layout.addRow("Descrição:", self.input_descricao)
        self.layout.addRow("Preço:", self.input_preco)
        self.layout.addRow("Código B:", self.input_codigoB)
        self.layout.addRow("Código C:", self.input_codigoC)

        self.botoes = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.botoes.accepted.connect(self.accept)
        self.botoes.rejected.connect(self.reject)
        self.layout.addWidget(self.botoes)

        if self.produto_id:
            self.carregar_dados_produto()

    def carregar_dados_produto(self):
        global access_token
        url = f"http://127.0.0.1:5000/api/produtos/{self.produto_id}"
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                dados = response.json()
                self.input_codigo.setText(dados.get('codigo', ''))
                self.input_nome.setText(dados.get('nome', ''))
                self.input_descricao.setText(dados.get('descricao', ''))
                self.input_preco.setText(dados.get('preco', '0.00'))
                # O back-end precisa de retornar estes campos para que eles sejam preenchidos
                # self.input_codigoB.setText(dados.get('codigoB', ''))
                # self.input_codigoC.setText(dados.get('codigoC', ''))
            else:
                QMessageBox.warning(self, "Erro", "Não foi possível carregar os dados do produto.")
                self.close()
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Erro de Conexão", f"Erro ao carregar dados: {e}")
            self.close()

    def accept(self):
        global access_token
        headers = {'Authorization': f'Bearer {access_token}'}
        dados_produto = {
            "codigo": self.input_codigo.text(),
            "nome": self.input_nome.text(),
            "descricao": self.input_descricao.text(),
            "preco": self.input_preco.text().replace(',', '.'), # Garante que o decimal use ponto
            "codigoB": self.input_codigoB.text(),
            "codigoC": self.input_codigoC.text()
        }

        try:
            if self.produto_id is None:
                url = "http://127.0.0.1:5000/api/produtos"
                response = requests.post(url, headers=headers, json=dados_produto)
                status_sucesso, msg_sucesso = 201, "Produto adicionado com sucesso!"
            else:
                url = f"http://127.0.0.1:5000/api/produtos/{self.produto_id}"
                response = requests.put(url, headers=headers, json=dados_produto)
                status_sucesso, msg_sucesso = 200, "Produto atualizado com sucesso!"

            if response.status_code == status_sucesso:
                QMessageBox.information(self, "Sucesso", msg_sucesso)
                super().accept()
            else:
                erro = response.json().get('erro', 'Erro desconhecido.')
                QMessageBox.warning(self, "Erro", f"Não foi possível salvar o produto: {erro}")
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Erro de Conexão", f"Erro ao salvar: {e}")

# ==============================================================================
# BLOCO DE EXECUÇÃO PRINCIPAL
# ==============================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    janela_login = JanelaLogin()
    janela_login.show()
    sys.exit(app.exec())