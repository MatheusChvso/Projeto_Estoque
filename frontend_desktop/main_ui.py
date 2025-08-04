# ==============================================================================
# 1. IMPORTS
# Centraliza todas as bibliotecas necessárias para a aplicação.
# ==============================================================================
import sys
import requests
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit,
    QPushButton, QVBoxLayout, QMessageBox, QMainWindow, QHBoxLayout,
    QStackedWidget, QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy,
    QDialog, QFormLayout, QDialogButtonBox, QListWidget, QListWidgetItem
)
from PySide6.QtGui import QPixmap, QAction, QDoubleValidator
from PySide6.QtCore import Qt, QTimer

# ==============================================================================
# 2. VARIÁVEIS GLOBAIS
# Variáveis que precisam de ser acedidas por diferentes partes da aplicação.
# ==============================================================================
access_token = None

# ==============================================================================
# 3. CLASSE DA JANELA DE LOGIN
# Responsável por autenticar o usuário e iniciar a aplicação principal.
# ==============================================================================
class JanelaLogin(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Meu Sistema de Gestão - Login")
        self.resize(300, 350)
        self.janela_principal = None # Referência para a janela principal

        # Criação da interface de login
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

        # Adiciona os widgets ao layout
        layout.addWidget(self.label_logo)
        layout.addWidget(QLabel("Login:"))
        layout.addWidget(self.input_login)
        layout.addWidget(QLabel("Senha:"))
        layout.addWidget(self.input_senha)
        layout.addWidget(self.botao_login)
        self.setLayout(layout)

        # Conecta o clique do botão à função de login
        self.botao_login.clicked.connect(self.fazer_login)

    def fazer_login(self):
        """Envia as credenciais para a API e trata a resposta."""
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
# 4. JANELA DE DIÁLOGO PARA FORMULÁRIO DE PRODUTO
# Esta classe é definida ANTES da ProdutosWidget porque é usada por ela.
# ==============================================================================
class FormularioProdutoDialog(QDialog):
    def __init__(self, parent=None, produto_id=None):
        super().__init__(parent)
        self.produto_id = produto_id
        self.setWindowTitle("Adicionar Novo Produto" if self.produto_id is None else "Editar Produto")
        self.setMinimumSize(400, 500)
        self.layout = QFormLayout(self)

        # Criação dos campos de entrada do formulário
        self.input_codigo = QLineEdit()
        self.input_nome = QLineEdit()
        self.input_descricao = QLineEdit()
        self.input_preco = QLineEdit()
        self.input_preco.setValidator(QDoubleValidator(0.00, 999999.99, 2))
        self.input_codigoB = QLineEdit()
        self.input_codigoC = QLineEdit()
        self.lista_fornecedores = QListWidget()
        self.lista_fornecedores.setSelectionMode(QListWidget.SelectionMode.MultiSelection)

        # Adiciona os campos ao layout do formulário
        self.layout.addRow("Código:", self.input_codigo)
        self.layout.addRow("Nome:", self.input_nome)
        self.layout.addRow("Descrição:", self.input_descricao)
        self.layout.addRow("Preço:", self.input_preco)
        self.layout.addRow("Código B:", self.input_codigoB)
        self.layout.addRow("Código C:", self.input_codigoC)
        self.layout.addRow("Fornecedores:", self.lista_fornecedores)

        # Botões padrão de Salvar e Cancelar
        self.botoes = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.botoes.accepted.connect(self.accept)
        self.botoes.rejected.connect(self.reject)
        self.layout.addWidget(self.botoes)

        # Carrega dados necessários para o formulário
        self.carregar_listas_de_apoio()
        if self.produto_id:
            self.carregar_dados_produto()

    def carregar_listas_de_apoio(self):
        """Busca a lista de todos os fornecedores para preencher as opções."""
        global access_token
        url = "http://127.0.0.1:5000/api/fornecedores"
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                fornecedores = response.json()
                for forn in fornecedores:
                    item = QListWidgetItem(forn['nome'])
                    item.setData(Qt.UserRole, forn['id']) # Guarda o ID "escondido"
                    self.lista_fornecedores.addItem(item)
            else:
                QMessageBox.warning(self, "Erro", "Não foi possível carregar a lista de fornecedores.")
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Erro de Conexão", f"Erro ao carregar listas: {e}")

    def carregar_dados_produto(self):
        """Se estiver em modo de edição, busca os dados do produto e preenche o formulário."""
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
                self.input_codigoB.setText(dados.get('codigoB', ''))
                self.input_codigoC.setText(dados.get('codigoC', ''))
                # TODO: Marcar os fornecedores que já estão associados a este produto
            else:
                QMessageBox.warning(self, "Erro", "Não foi possível carregar os dados do produto.")
                self.close()
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Erro de Conexão", f"Erro ao carregar dados: {e}")
            self.close()

    def accept(self):
        """Chamada quando o botão 'Salvar' é clicado. Envia os dados para a API."""
        global access_token
        headers = {'Authorization': f'Bearer {access_token}'}
        dados_produto = {
            "codigo": self.input_codigo.text(),
            "nome": self.input_nome.text(),
            "descricao": self.input_descricao.text(),
            "preco": self.input_preco.text().replace(',', '.'),
            "codigoB": self.input_codigoB.text(),
            "codigoC": self.input_codigoC.text()
        }
        
        produto_salvo_id = None
        try:
            if self.produto_id is None: # Modo Adicionar
                url_produto = "http://127.0.0.1:5000/api/produtos"
                response = requests.post(url_produto, headers=headers, json=dados_produto)
                if response.status_code == 201:
                    produto_salvo_id = response.json().get('id_produto_criado')
                else:
                    raise Exception(response.json().get('erro', 'Erro desconhecido'))
            else: # Modo Editar
                url_produto = f"http://127.0.0.1:5000/api/produtos/{self.produto_id}"
                response = requests.put(url_produto, headers=headers, json=dados_produto)
                if response.status_code == 200:
                    produto_salvo_id = self.produto_id
                else:
                    raise Exception(response.json().get('erro', 'Erro desconhecido'))

            if produto_salvo_id:
                # TODO: Limpar associações antigas antes de adicionar as novas no modo de edição
                itens_selecionados = self.lista_fornecedores.selectedItems()
                for item in itens_selecionados:
                    id_fornecedor = item.data(Qt.UserRole)
                    url_assoc = f"http://127.0.0.1:5000/api/produtos/{produto_salvo_id}/fornecedores"
                    requests.post(url_assoc, headers=headers, json={'id_fornecedor': id_fornecedor})
            
            QMessageBox.information(self, "Sucesso", "Produto salvo com sucesso!")
            super().accept() # Fecha o diálogo com sucesso
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Não foi possível salvar o produto: {e}")


# ==============================================================================
# JANELA DE DIÁLOGO PARA FORMULÁRIO DE FORNECEDOR
# ==============================================================================
class FormularioProdutoDialog(QDialog):
    def __init__(self, parent=None, produto_id=None):
        super().__init__(parent)
        self.produto_id = produto_id
        self.setWindowTitle("Adicionar Novo Produto" if self.produto_id is None else "Editar Produto")
        self.setMinimumSize(450, 600)
        self.layout = QFormLayout(self)

        # Campos de texto
        self.input_codigo = QLineEdit()
        self.input_nome = QLineEdit()
        self.input_descricao = QLineEdit()
        self.input_preco = QLineEdit()
        self.input_preco.setValidator(QDoubleValidator(0.00, 999999.99, 2))
        self.input_codigoB = QLineEdit()
        self.input_codigoC = QLineEdit()

        # Listas de seleção
        self.lista_fornecedores = QListWidget()
        self.lista_fornecedores.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.lista_fornecedores.setMaximumHeight(100) # Define uma altura máxima para a lista

        self.lista_naturezas = QListWidget()
        self.lista_naturezas.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.lista_naturezas.setMaximumHeight(100) # Define uma altura máxima para a lista

        # Adiciona os campos ao layout
        self.layout.addRow("Código:", self.input_codigo)
        self.layout.addRow("Nome:", self.input_nome)
        self.layout.addRow("Descrição:", self.input_descricao)
        self.layout.addRow("Preço:", self.input_preco)
        self.layout.addRow("Código B:", self.input_codigoB)
        self.layout.addRow("Código C:", self.input_codigoC)
        self.layout.addRow("Fornecedores:", self.lista_fornecedores)
        self.layout.addRow("Naturezas:", self.lista_naturezas)

        self.botoes = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.botoes.accepted.connect(self.accept)
        self.botoes.rejected.connect(self.reject)
        self.layout.addWidget(self.botoes)

        self.carregar_listas_de_apoio()
        if self.produto_id:
            self.carregar_dados_produto()

    def carregar_listas_de_apoio(self):
        """Busca as listas de fornecedores e naturezas para preencher as opções."""
        global access_token
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            # Carrega Fornecedores
            url_forn = "http://127.0.0.1:5000/api/fornecedores"
            response_forn = requests.get(url_forn, headers=headers)
            if response_forn.status_code == 200:
                for forn in response_forn.json():
                    item = QListWidgetItem(forn['nome'])
                    item.setData(Qt.UserRole, forn['id'])
                    self.lista_fornecedores.addItem(item)
            
            # Carrega Naturezas
            url_nat = "http://127.0.0.1:5000/api/naturezas"
            response_nat = requests.get(url_nat, headers=headers)
            if response_nat.status_code == 200:
                for nat in response_nat.json():
                    item = QListWidgetItem(nat['nome'])
                    item.setData(Qt.UserRole, nat['id'])
                    self.lista_naturezas.addItem(item)
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Erro de Conexão", f"Erro ao carregar listas de apoio: {e}")

    def carregar_dados_produto(self):
        """No modo de edição, busca os dados do produto, incluindo suas associações."""
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
                self.input_codigoB.setText(dados.get('codigoB', ''))
                self.input_codigoC.setText(dados.get('codigoC', ''))

                # Marca os fornecedores já associados
                ids_fornecedores_associados = {f['id'] for f in dados.get('fornecedores', [])}
                for i in range(self.lista_fornecedores.count()):
                    item = self.lista_fornecedores.item(i)
                    if item.data(Qt.UserRole) in ids_fornecedores_associados:
                        item.setSelected(True)

                # Marca as naturezas já associadas
                ids_naturezas_associadas = {n['id'] for n in dados.get('naturezas', [])}
                for i in range(self.lista_naturezas.count()):
                    item = self.lista_naturezas.item(i)
                    if item.data(Qt.UserRole) in ids_naturezas_associadas:
                        item.setSelected(True)
            else:
                QMessageBox.warning(self, "Erro", "Não foi possível carregar os dados do produto.")
                self.close()
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Erro de Conexão", f"Erro ao carregar dados: {e}")
            self.close()

    def accept(self):
        """Salva o produto e depois atualiza as suas associações."""
        global access_token
        headers = {'Authorization': f'Bearer {access_token}'}
        dados_produto = {
            "codigo": self.input_codigo.text(), "nome": self.input_nome.text(),
            "descricao": self.input_descricao.text(), "preco": self.input_preco.text().replace(',', '.'),
            "codigoB": self.input_codigoB.text(), "codigoC": self.input_codigoC.text()
        }
        
        produto_salvo_id = None
        try:
            if self.produto_id is None: # Modo Adicionar
                response = requests.post("http://127.0.0.1:5000/api/produtos", headers=headers, json=dados_produto)
                if response.status_code == 201:
                    produto_salvo_id = response.json().get('id_produto_criado')
                else: raise Exception(response.json().get('erro', 'Erro desconhecido'))
            else: # Modo Editar
                response = requests.put(f"http://127.0.0.1:5000/api/produtos/{self.produto_id}", headers=headers, json=dados_produto)
                if response.status_code == 200:
                    produto_salvo_id = self.produto_id
                else: raise Exception(response.json().get('erro', 'Erro desconhecido'))

            if produto_salvo_id:
                # TODO: No modo de edição, primeiro limpar as associações antigas
                # Associa os fornecedores selecionados
                for item in self.lista_fornecedores.selectedItems():
                    url = f"http://127.0.0.1:5000/api/produtos/{produto_salvo_id}/fornecedores"
                    requests.post(url, headers=headers, json={'id_fornecedor': item.data(Qt.UserRole)})
                
                # Associa as naturezas selecionadas
                for item in self.lista_naturezas.selectedItems():
                    url = f"http://127.0.0.1:5000/api/produtos/{produto_salvo_id}/naturezas"
                    requests.post(url, headers=headers, json={'id_natureza': item.data(Qt.UserRole)})
            
            QMessageBox.information(self, "Sucesso", "Produto salvo com sucesso!")
            super().accept()
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Não foi possível salvar o produto: {e}")

class ProdutosWidget(QWidget):
    """Tela para gerir (CRUD) os produtos."""
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
        self.btn_excluir.clicked.connect(self.excluir_produto_selecionado)
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

    def excluir_produto_selecionado(self):
        linha_selecionada = self.tabela_produtos.currentRow()
        if linha_selecionada < 0:
            QMessageBox.warning(self, "Seleção", "Por favor, selecione um produto na tabela para excluir.")
            return

        item_id = self.tabela_produtos.item(linha_selecionada, 0)
        produto_id = item_id.data(Qt.UserRole)
        nome_produto = self.tabela_produtos.item(linha_selecionada, 1).text()

        resposta = QMessageBox.question(self, "Confirmar Exclusão", f"Tem a certeza de que deseja excluir o produto '{nome_produto}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if resposta == QMessageBox.StandardButton.Yes:
            global access_token
            url = f"http://127.0.0.1:5000/api/produtos/{produto_id}"
            headers = {'Authorization': f'Bearer {access_token}'}
            try:
                response = requests.delete(url, headers=headers)
                if response.status_code == 200:
                    QMessageBox.information(self, "Sucesso", "Produto excluído com sucesso!")
                    self.carregar_produtos()
                else:
                    erro = response.json().get('erro', 'Erro desconhecido.')
                    QMessageBox.warning(self, "Erro", f"Não foi possível excluir o produto: {erro}")
            except requests.exceptions.RequestException as e:
                QMessageBox.critical(self, "Erro de Conexão", f"Não foi possível conectar ao servidor: {e}")

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

class EstoqueWidget(QWidget):
    """Tela para visualizar os saldos de estoque."""
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
# WIDGET DA TELA DE FORNECEDORES
# ==============================================================================
class FornecedoresWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.titulo = QLabel("Gestão de Fornecedores")
        self.titulo.setStyleSheet("font-size: 24px; font-weight: bold;")

        layout_botoes = QHBoxLayout()
        self.btn_adicionar = QPushButton("Adicionar Novo")
        self.btn_editar = QPushButton("Editar Selecionado")
        self.btn_excluir = QPushButton("Excluir Selecionado")
        layout_botoes.addWidget(self.btn_adicionar)
        layout_botoes.addWidget(self.btn_editar)
        layout_botoes.addWidget(self.btn_excluir)
        layout_botoes.addStretch(1)

        self.tabela_fornecedores = QTableWidget()
        self.tabela_fornecedores.setColumnCount(1) # Apenas a coluna Nome
        self.tabela_fornecedores.setHorizontalHeaderLabels(["Nome"])
        self.tabela_fornecedores.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.layout.addWidget(self.titulo)
        self.layout.addLayout(layout_botoes)
        self.layout.addWidget(self.tabela_fornecedores)

        # Conexões
        self.btn_adicionar.clicked.connect(self.abrir_formulario_adicionar)

        self.carregar_fornecedores()

    def carregar_fornecedores(self):
        """Busca os fornecedores na API e preenche a tabela."""
        global access_token
        url = "http://127.0.0.1:5000/api/fornecedores"
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                fornecedores = response.json()
                self.tabela_fornecedores.setRowCount(len(fornecedores))
                for linha, forn in enumerate(fornecedores):
                    # Guarda o ID no item para uso futuro (editar/excluir)
                    item_nome = QTableWidgetItem(forn['nome'])
                    item_nome.setData(Qt.UserRole, forn['id'])
                    self.tabela_fornecedores.setItem(linha, 0, item_nome)
            else:
                QMessageBox.warning(self, "Erro", "Não foi possível carregar os fornecedores.")
        except requests.exceptions.RequestException as e:
            print(f"Erro de Conexão: {e}")

    def abrir_formulario_adicionar(self):
        """Abre o diálogo para adicionar um novo fornecedor."""
        dialog = FormularioFornecedorDialog(self)
        if dialog.exec():
            # Se o formulário foi salvo com sucesso, atualiza a lista
            self.carregar_fornecedores()


# ==============================================================================
# WIDGET DA TELA DE NATUREZAS
# ==============================================================================
class NaturezasWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.titulo = QLabel("Gestão de Naturezas")
        self.titulo.setStyleSheet("font-size: 24px; font-weight: bold;")

        layout_botoes = QHBoxLayout()
        self.btn_adicionar = QPushButton("Adicionar Nova")
        self.btn_editar = QPushButton("Editar Selecionado")
        self.btn_excluir = QPushButton("Excluir Selecionado")
        layout_botoes.addWidget(self.btn_adicionar)
        layout_botoes.addWidget(self.btn_editar)
        layout_botoes.addWidget(self.btn_excluir)
        layout_botoes.addStretch(1)

        self.tabela_naturezas = QTableWidget()
        self.tabela_naturezas.setColumnCount(1)
        self.tabela_naturezas.setHorizontalHeaderLabels(["Nome"])
        self.tabela_naturezas.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.layout.addWidget(self.titulo)
        self.layout.addLayout(layout_botoes)
        self.layout.addWidget(self.tabela_naturezas)

        self.btn_adicionar.clicked.connect(self.abrir_formulario_adicionar)
        self.carregar_naturezas()

    def carregar_naturezas(self):
        global access_token
        url = "http://127.0.0.1:5000/api/naturezas"
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                naturezas = response.json()
                self.tabela_naturezas.setRowCount(len(naturezas))
                for linha, nat in enumerate(naturezas):
                    item_nome = QTableWidgetItem(nat['nome'])
                    item_nome.setData(Qt.UserRole, nat['id'])
                    self.tabela_naturezas.setItem(linha, 0, item_nome)
            else:
                QMessageBox.warning(self, "Erro", "Não foi possível carregar as naturezas.")
        except requests.exceptions.RequestException as e:
            print(f"Erro de Conexão: {e}")

    def abrir_formulario_adicionar(self):
        dialog = FormularioNaturezaDialog(self)
        if dialog.exec():
            self.carregar_naturezas()
# ==============================================================================
# 6. CLASSE DA JANELA PRINCIPAL
# A "moldura" da aplicação que contém a navegação e a área de conteúdo.
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

        # Criação da Barra de Menus
        menu_bar = self.menuBar()
        menu_arquivo = menu_bar.addMenu("&Arquivo")
        acao_sair = QAction("Sair", self)
        acao_sair.triggered.connect(self.close)
        menu_arquivo.addAction(acao_sair)
        menu_cadastros = menu_bar.addMenu("&Cadastros")
        self.acao_produtos = QAction("Produtos...", self)
        menu_cadastros.addAction(self.acao_produtos)

        # Criação do Layout Principal
        widget_central = QWidget()
        self.setCentralWidget(widget_central)
        layout_principal = QHBoxLayout(widget_central)

        # Criação do Painel de Navegação Lateral
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

        # Criação da Área de Conteúdo Dinâmica
        self.stacked_widget = QStackedWidget()
        layout_principal.addWidget(self.stacked_widget)
        self.tela_dashboard = QLabel("Bem-vindo ao Sistema!\n\nSelecione uma opção no menu lateral para começar.")
        self.tela_dashboard.setAlignment(Qt.AlignCenter)
        self.tela_dashboard.setStyleSheet("font-size: 18px; color: #555;")
        self.tela_produtos = ProdutosWidget()
        self.tela_estoque = EstoqueWidget()
        self.tela_fornecedores = FornecedoresWidget()
        self.tela_naturezas = NaturezasWidget()
        self.stacked_widget.addWidget(self.tela_dashboard)
        self.stacked_widget.addWidget(self.tela_produtos)
        self.stacked_widget.addWidget(self.tela_estoque)
        self.stacked_widget.addWidget(self.tela_fornecedores)
        self.stacked_widget.addWidget(self.tela_naturezas)

        # Conexão dos Sinais (Cliques) aos Slots (Funções)
        self.btn_dashboard.clicked.connect(self.mostrar_tela_dashboard)
        self.btn_produtos.clicked.connect(self.mostrar_tela_produtos)
        self.acao_produtos.triggered.connect(self.mostrar_tela_produtos)
        self.btn_estoque.clicked.connect(self.mostrar_tela_estoque)
        self.btn_fornecedores.clicked.connect(self.mostrar_tela_fornecedores)
        self.btn_naturezas.clicked.connect(self.mostrar_tela_naturezas)

        self.statusBar().showMessage("Pronto.")

    def mostrar_tela_dashboard(self):
        self.stacked_widget.setCurrentWidget(self.tela_dashboard)

    def mostrar_tela_produtos(self):
        self.stacked_widget.setCurrentWidget(self.tela_produtos)

    def mostrar_tela_estoque(self):
        self.stacked_widget.setCurrentWidget(self.tela_estoque)
        
    def mostrar_tela_fornecedores(self):
        self.stacked_widget.setCurrentWidget(self.tela_fornecedores)    
        
    def mostrar_tela_naturezas(self):
        self.stacked_widget.setCurrentWidget(self.tela_naturezas)

# ==============================================================================
# 7. BLOCO DE EXECUÇÃO PRINCIPAL
# O ponto de entrada que inicia a aplicação.
# ==============================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    janela_login = JanelaLogin()
    janela_login.show()
    sys.exit(app.exec())
