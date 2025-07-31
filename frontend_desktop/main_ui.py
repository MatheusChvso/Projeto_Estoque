import sys
import requests
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QMessageBox, QMainWindow, QHBoxLayout,
    QStackedWidget, # <-- Adicione aqui
    QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy
)
from PySide6.QtGui import QPixmap, QAction
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    # ...
    QDialog, QFormLayout, QDialogButtonBox
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
# ==============================================================================
# CLASSE DA JANELA PRINCIPAL (COM ESTILOS)
# ==============================================================================
class JanelaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema de Gestão de Estoque")
        self.resize(1280, 720)

        # --- APLICAÇÃO DE ESTILOS (QSS) ---
        # Este bloco de texto define a aparência de vários componentes da janela.
        self.setStyleSheet("""
            /* Estilo geral da janela e do widget central */
            QMainWindow, QWidget {
                background-color: #f5f5f5; /* Um cinza claro para o fundo */
            }

            /* Estilo do painel lateral */
            #painelLateral {
                background-color: #e0e0e0; /* Um cinza um pouco mais escuro */
            }

            /* Estilo dos botões DENTRO do painel lateral */
            #painelLateral QPushButton {
                background-color: #e0e0e0;
                color: #333;
                border: none; /* Sem borda para um look mais limpo */
                border-radius: 5px;
                padding: 12px;
                font-size: 16px;
                text-align: left; /* Alinha o texto à esquerda */
            }

            /* Efeito ao passar o mouse por cima do botão */
            #painelLateral QPushButton:hover {
                background-color: #cce7ff;
            }
            
            /* Estilo para o botão selecionado (ainda não implementado, mas útil para o futuro) */
            #painelLateral QPushButton:checked {
                background-color: #0078d7;
                color: white;
            }
            
            /* Estilo da Barra de Menus */
            QMenuBar {
                background-color: #dcdcdc;
                color: #333;
            }
        """)

        # --- BARRA DE MENUS ---
        menu_bar = self.menuBar()
        menu_arquivo = menu_bar.addMenu("&Arquivo")
        acao_sair = QAction("Sair", self)
        acao_sair.triggered.connect(self.close)
        menu_arquivo.addAction(acao_sair)
        menu_cadastros = menu_bar.addMenu("&Cadastros")
        self.acao_produtos = QAction("Produtos...", self) # TORNANDO A AÇÃO UM ATRIBUTO
        menu_cadastros.addAction(self.acao_produtos)
        # ... (pode adicionar as outras ações do menu aqui se precisar conectá-las)

        # --- LAYOUT GERAL E WIDGET CENTRAL ---
        widget_central = QWidget()
        self.setCentralWidget(widget_central)
        layout_principal = QHBoxLayout(widget_central)

        # --- PAINEL DE NAVEGAÇÃO LATERAL ---
        painel_lateral = QWidget()
        painel_lateral.setObjectName("painelLateral")
        painel_lateral.setFixedWidth(200)
        layout_painel_lateral = QVBoxLayout(painel_lateral)
        layout_painel_lateral.setAlignment(Qt.AlignTop)

        # Botões do painel lateral
        # TORNANDO OS BOTÕES ATRIBUTOS DA CLASSE com 'self.'
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

        # --- ÁREA DE CONTEÚDO (USANDO QStackedWidget) ---
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

        # --- CONEXÃO DOS SINAIS AOS SLOTS ---
        # Agora conectamos os atributos 'self.btn...'
        self.btn_dashboard.clicked.connect(self.mostrar_tela_dashboard)
        self.btn_produtos.clicked.connect(self.mostrar_tela_produtos)
        self.acao_produtos.triggered.connect(self.mostrar_tela_produtos)
        self.btn_estoque.clicked.connect(self.mostrar_tela_estoque)

        # --- BARRA DE STATUS ---
        self.statusBar().showMessage("Pronto.")
 
            # --- FUNÇÕES (SLOTS) PARA NAVEGAÇÃO ---
    def mostrar_tela_dashboard(self):
        # Diz ao QStackedWidget para mostrar a tela_dashboard
        self.stacked_widget.setCurrentWidget(self.tela_dashboard)

    def mostrar_tela_produtos(self):
        # Diz ao QStackedWidget para mostrar a tela_produtos
        self.stacked_widget.setCurrentWidget(self.tela_produtos)

    def mostrar_tela_estoque(self):
        # Diz ao QStackedWidget para mostrar a tela_estoque
        self.stacked_widget.setCurrentWidget(self.tela_estoque)
        
        
                

# Dentro do seu main_ui.py

class ProdutosWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        self.layout = QVBoxLayout(self)
        
        self.titulo = QLabel("Gestão de Produtos")
        self.titulo.setStyleSheet("font-size: 24px; font-weight: bold;")
        
        # --- Layout para os Botões de Ação ---
        layout_botoes = QHBoxLayout()
        self.btn_adicionar = QPushButton("Adicionar Novo")
        self.btn_editar = QPushButton("Editar Selecionado")
        self.btn_excluir = QPushButton("Excluir Selecionado")
        layout_botoes.addWidget(self.btn_adicionar)
        layout_botoes.addWidget(self.btn_editar)
        layout_botoes.addWidget(self.btn_excluir)
        layout_botoes.addStretch(1) # Empurra os botões para a esquerda
        
        # --- Barra de Pesquisa ---
        self.input_pesquisa = QLineEdit()
        self.input_pesquisa.setPlaceholderText("Buscar por nome ou código...")
        
        # --- Tabela de Produtos ---
        self.tabela_produtos = QTableWidget()
        self.tabela_produtos.setColumnCount(4)
        self.tabela_produtos.setHorizontalHeaderLabels(["Código", "Nome", "Descrição", "Preço"])
        self.tabela_produtos.setAlternatingRowColors(True)
        self.tabela_produtos.horizontalHeader().setStretchLastSection(True)
        self.tabela_produtos.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        # Adiciona todos os widgets e layouts ao layout principal da tela
        self.layout.addWidget(self.titulo)
        self.layout.addLayout(layout_botoes)
        self.layout.addWidget(self.input_pesquisa)
        self.layout.addWidget(self.tabela_produtos)
        
        # --- Configuração do Timer para Debounce da Pesquisa ---
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.carregar_produtos)

        # --- Conexões dos Sinais (Ações do Usuário) ---
        self.btn_adicionar.clicked.connect(self.abrir_formulario_adicionar)
        # A linha abaixo foi REMOVIDA porque o botão self.btn_pesquisar não existe mais.
        # self.btn_pesquisar.clicked.connect(self.carregar_produtos)
        self.input_pesquisa.textChanged.connect(self.iniciar_busca_timer)
        
        # Carga inicial dos dados no final, depois de tudo estar configurado
        self.carregar_produtos()

    def abrir_formulario_adicionar(self):
        dialog = FormularioProdutoDialog(self)
        if dialog.exec():
            self.carregar_produtos()

    def iniciar_busca_timer(self):
        """Reinicia o cronómetro sempre que o texto é alterado."""
        self.search_timer.stop()
        self.search_timer.start(300)

    def carregar_produtos(self):
        """Busca os produtos na API e atualiza a tabela."""
        global access_token
        url = "http://127.0.0.1:5000/api/produtos"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        termo_busca = self.input_pesquisa.text()
        params = {}
        if termo_busca:
            params['search'] = termo_busca
        
        try:
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                produtos = response.json()
                self.tabela_produtos.setRowCount(0)
                self.tabela_produtos.setRowCount(len(produtos))
                
                for linha, produto in enumerate(produtos):
                    self.tabela_produtos.setItem(linha, 0, QTableWidgetItem(produto['codigo']))
                    self.tabela_produtos.setItem(linha, 1, QTableWidgetItem(produto['nome']))
                    self.tabela_produtos.setItem(linha, 2, QTableWidgetItem(produto['descricao']))
                    self.tabela_produtos.setItem(linha, 3, QTableWidgetItem(produto['preco']))
            else:
                QMessageBox.warning(self, "Erro", f"Erro ao carregar produtos: {response.json().get('erro')}")

        except requests.exceptions.RequestException as e:
            print(f"Erro de Conexão: {e}")



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
        
        # Chamada inicial para carregar os dados
        self.carregar_dados_estoque()

    def carregar_dados_estoque(self):
        global access_token
        # Usamos o nosso NOVO endpoint eficiente
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
                    # Convertemos o número do saldo para string para exibir na tabela
                    self.tabela_estoque.setItem(linha, 2, QTableWidgetItem(str(item['saldo_atual'])))
            else:
                QMessageBox.warning(self, "Erro", f"Erro ao carregar saldos: {response.json().get('msg') or response.json().get('erro')}")

        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Erro de Conexão", f"Não foi possível conectar ao servidor: {e}")





# --- JANELA DE DIÁLOGO PARA O FORMULÁRIO DE PRODUTO ---
class FormularioProdutoDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Adicionar Novo Produto")

        # Layout do formulário (ótimo para pares de label-campo)
        self.layout = QFormLayout(self)

        # Campos do formulário
        self.input_codigo = QLineEdit()
        self.input_nome = QLineEdit()
        self.input_descricao = QLineEdit()
        self.input_preco = QLineEdit()
        self.input_codigoB = QLineEdit()
        self.input_codigoC = QLineEdit()

        # Adiciona os campos ao layout do formulário
        self.layout.addRow("Código:", self.input_codigo)
        self.layout.addRow("Nome:", self.input_nome)
        self.layout.addRow("Descrição:", self.input_descricao)
        self.layout.addRow("Preço:", self.input_preco)
        self.layout.addRow("Código B:", self.input_codigoB)
        self.layout.addRow("Código C:", self.input_codigoC)

        # Botões padrão (Salvar e Cancelar)
        self.botoes = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.botoes.accepted.connect(self.accept) # Conecta o sinal de "aceitar"
        self.botoes.rejected.connect(self.reject) # Conecta o sinal de "rejeitar"
        
        self.layout.addWidget(self.botoes)

    # Esta função é chamada quando o usuário clica em "Salvar"
    def accept(self):
        global access_token
        url = "http://127.0.0.1:5000/api/produtos"
        headers = {'Authorization': f'Bearer {access_token}'}

        dados_produto = {
            "codigo": self.input_codigo.text(),
            "nome": self.input_nome.text(),
            "descricao": self.input_descricao.text(),
            "preco": self.input_preco.text(),
            "codigoB": self.input_codigoB.text(),
            "codigoC": self.input_codigoC.text()
        }

        try:
            response = requests.post(url, headers=headers, json=dados_produto)
            if response.status_code == 201:
                QMessageBox.information(self, "Sucesso", "Produto adicionado com sucesso!")
                super().accept() # Fecha o diálogo com sucesso
            else:
                # Se a API retornar um erro, exibe-o
                erro = response.json().get('erro', 'Erro desconhecido do servidor.')
                QMessageBox.warning(self, "Erro", f"Não foi possível adicionar o produto: {erro}")
        
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Erro de Conexão", f"Não foi possível conectar ao servidor: {e}")






# ==============================================================================
# BLOCO DE EXECUÇÃO PRINCIPAL
# ==============================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # A aplicação agora começa pela janela de login
    janela_login = JanelaLogin()
    janela_login.show()
    
    sys.exit(app.exec())