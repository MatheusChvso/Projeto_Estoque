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
    QDialog, QFormLayout, QDialogButtonBox, QListWidget, QListWidgetItem,
    QAbstractItemView
)
from PySide6.QtGui import QPixmap, QAction, QDoubleValidator
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    # ... todos os seus imports existentes
    QComboBox
)

# ==============================================================================
# 2. VARIÁVEIS GLOBAIS
# ==============================================================================
access_token = None

# ==============================================================================
# 3. JANELAS DE DIÁLOGO (FORMULÁRIOS)
# Definidas primeiro para que possam ser chamadas pelas telas principais.
# ==============================================================================

class FormularioProdutoDialog(QDialog):
    """Janela de formulário para Adicionar ou Editar um Produto."""
    def __init__(self, parent=None, produto_id=None):
        super().__init__(parent)
        self.produto_id = produto_id
        self.setWindowTitle("Adicionar Novo Produto" if self.produto_id is None else "Editar Produto")
        self.setMinimumSize(450, 600)
        self.layout = QFormLayout(self)

        self.input_codigo = QLineEdit()
        self.input_nome = QLineEdit()
        self.input_descricao = QLineEdit()
        self.input_preco = QLineEdit()
        self.input_preco.setValidator(QDoubleValidator(0.00, 999999.99, 2))
        self.input_codigoB = QLineEdit()
        self.input_codigoC = QLineEdit()
        self.lista_fornecedores = QListWidget()
        self.lista_fornecedores.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.lista_fornecedores.setMaximumHeight(100)
        self.lista_naturezas = QListWidget()
        self.lista_naturezas.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.lista_naturezas.setMaximumHeight(100)

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
        global access_token
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            url_forn = "http://127.0.0.1:5000/api/fornecedores"
            response_forn = requests.get(url_forn, headers=headers)
            if response_forn.status_code == 200:
                for forn in response_forn.json():
                    item = QListWidgetItem(forn['nome'])
                    item.setData(Qt.UserRole, forn['id'])
                    self.lista_fornecedores.addItem(item)
            
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

                ids_fornecedores_associados = {f['id'] for f in dados.get('fornecedores', [])}
                for i in range(self.lista_fornecedores.count()):
                    item = self.lista_fornecedores.item(i)
                    if item.data(Qt.UserRole) in ids_fornecedores_associados:
                        item.setSelected(True)

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
                for item in self.lista_fornecedores.selectedItems():
                    url = f"http://127.0.0.1:5000/api/produtos/{produto_salvo_id}/fornecedores"
                    requests.post(url, headers=headers, json={'id_fornecedor': item.data(Qt.UserRole)})
                
                for item in self.lista_naturezas.selectedItems():
                    url = f"http://127.0.0.1:5000/api/produtos/{produto_salvo_id}/naturezas"
                    requests.post(url, headers=headers, json={'id_natureza': item.data(Qt.UserRole)})
            
            QMessageBox.information(self, "Sucesso", "Produto salvo com sucesso!")
            super().accept()
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Não foi possível salvar o produto: {e}")

class FormularioFornecedorDialog(QDialog):
    """Janela de formulário para Adicionar ou Editar um Fornecedor."""
    def __init__(self, parent=None, fornecedor_id=None):
        super().__init__(parent)
        self.fornecedor_id = fornecedor_id
        self.setWindowTitle("Adicionar Novo Fornecedor" if self.fornecedor_id is None else "Editar Fornecedor")

        self.layout = QFormLayout(self)
        self.input_nome = QLineEdit()
        self.layout.addRow("Nome:", self.input_nome)

        self.botoes = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.botoes.accepted.connect(self.accept)
        self.botoes.rejected.connect(self.reject)
        self.layout.addWidget(self.botoes)

        if self.fornecedor_id:
            self.carregar_dados_fornecedor()

    def carregar_dados_fornecedor(self):
        global access_token
        url = f"http://127.0.0.1:5000/api/fornecedores/{self.fornecedor_id}"
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                self.input_nome.setText(response.json().get('nome'))
            else:
                QMessageBox.warning(self, "Erro", "Não foi possível carregar dados do fornecedor.")
        except Exception as e:
            QMessageBox.critical(self, "Erro de Conexão", f"Erro ao carregar: {e}")

    def accept(self):
        global access_token
        headers = {'Authorization': f'Bearer {access_token}'}
        dados = {"nome": self.input_nome.text()}
        try:
            if self.fornecedor_id is None:
                response = requests.post("http://127.0.0.1:5000/api/fornecedores", headers=headers, json=dados)
                if response.status_code == 201:
                    QMessageBox.information(self, "Sucesso", "Fornecedor adicionado com sucesso!")
                    super().accept()
                else: raise Exception(response.json().get('erro', 'Erro desconhecido'))
            else:
                url = f"http://127.0.0.1:5000/api/fornecedores/{self.fornecedor_id}"
                response = requests.put(url, headers=headers, json=dados)
                if response.status_code == 200:
                    QMessageBox.information(self, "Sucesso", "Fornecedor atualizado com sucesso!")
                    super().accept()
                else: raise Exception(response.json().get('erro', 'Erro desconhecido'))
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Não foi possível salvar o fornecedor: {e}")

class FormularioNaturezaDialog(QDialog):
    """Janela de formulário para Adicionar ou Editar uma Natureza."""
    def __init__(self, parent=None, natureza_id=None):
        super().__init__(parent)
        self.natureza_id = natureza_id
        self.setWindowTitle("Adicionar Nova Natureza" if self.natureza_id is None else "Editar Natureza")

        self.layout = QFormLayout(self)
        self.input_nome = QLineEdit()
        self.layout.addRow("Nome:", self.input_nome)

        self.botoes = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.botoes.accepted.connect(self.accept)
        self.botoes.rejected.connect(self.reject)
        self.layout.addWidget(self.botoes)

        if self.natureza_id:
            self.carregar_dados_natureza()

    def carregar_dados_natureza(self):
        global access_token
        url = f"http://127.0.0.1:5000/api/naturezas/{self.natureza_id}"
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                self.input_nome.setText(response.json().get('nome'))
            else:
                QMessageBox.warning(self, "Erro", "Não foi possível carregar dados da natureza.")
        except Exception as e:
            QMessageBox.critical(self, "Erro de Conexão", f"Erro ao carregar: {e}")

    def accept(self):
        global access_token
        headers = {'Authorization': f'Bearer {access_token}'}
        dados = {"nome": self.input_nome.text()}
        try:
            if self.natureza_id is None:
                response = requests.post("http://127.0.0.1:5000/api/naturezas", headers=headers, json=dados)
                if response.status_code == 201:
                    QMessageBox.information(self, "Sucesso", "Natureza adicionada com sucesso!")
                    super().accept()
                else: raise Exception(response.json().get('erro', 'Erro desconhecido'))
            else:
                url = f"http://127.0.0.1:5000/api/naturezas/{self.natureza_id}"
                response = requests.put(url, headers=headers, json=dados)
                if response.status_code == 200:
                    QMessageBox.information(self, "Sucesso", "Natureza atualizada com sucesso!")
                    super().accept()
                else: raise Exception(response.json().get('erro', 'Erro desconhecido'))
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Não foi possível salvar a natureza: {e}")



# TRECHO 1: ADICIONAR esta nova classe ao main_ui.py

class FormularioUsuarioDialog(QDialog):
    """Janela de formulário para Adicionar ou Editar um Usuário."""
    def __init__(self, parent=None, usuario_id=None):
        super().__init__(parent)
        self.usuario_id = usuario_id
        self.setWindowTitle("Adicionar Novo Usuário" if self.usuario_id is None else "Editar Usuário")
        self.setMinimumWidth(350)

        self.layout = QFormLayout(self)
        self.input_nome = QLineEdit()
        self.input_login = QLineEdit()
        self.input_senha = QLineEdit()
        self.input_senha.setPlaceholderText("Deixe em branco para não alterar")
        self.input_permissao = QComboBox()
        self.input_permissao.addItems(["Usuario", "Administrador"])

        self.layout.addRow("Nome:", self.input_nome)
        self.layout.addRow("Login:", self.input_login)
        self.layout.addRow("Nova Senha:", self.input_senha)
        self.layout.addRow("Permissão:", self.input_permissao)

        self.botoes = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.botoes.accepted.connect(self.accept)
        self.botoes.rejected.connect(self.reject)
        self.layout.addWidget(self.botoes)

        if self.usuario_id:
            self.carregar_dados_usuario()

    def carregar_dados_usuario(self):
        """Busca os dados de um usuário específico na API para preencher o formulário."""
        global access_token
        url = f"http://127.0.0.1:5000/api/usuarios/{self.usuario_id}"
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                dados = response.json()
                self.input_nome.setText(dados.get('nome', ''))
                self.input_login.setText(dados.get('login', ''))
                self.input_permissao.setCurrentText(dados.get('permissao', 'Usuario'))
            else:
                QMessageBox.warning(self, "Erro", "Não foi possível carregar os dados do usuário.")
                self.reject() # Fecha o diálogo se não conseguir carregar
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Erro de Conexão", f"Erro ao carregar dados: {e}")
            self.reject()

    def accept(self):
        """Envia os dados para a API para criar ou editar um usuário."""
        global access_token
        headers = {'Authorization': f'Bearer {access_token}'}
        
        dados = {
            "nome": self.input_nome.text(),
            "login": self.input_login.text(),
            "permissao": self.input_permissao.currentText()
        }

        # Adiciona a senha ao dicionário SOMENTE se o campo não estiver vazio
        if self.input_senha.text():
            dados['senha'] = self.input_senha.text()

        try:
            if self.usuario_id is None: # Modo Adicionar
                url = "http://127.0.0.1:5000/api/usuarios"
                response = requests.post(url, headers=headers, json=dados)
                mensagem_sucesso = "Usuário adicionado com sucesso!"
                status_esperado = 201
            else: # Modo Editar
                url = f"http://127.0.0.1:5000/api/usuarios/{self.usuario_id}"
                response = requests.put(url, headers=headers, json=dados)
                mensagem_sucesso = "Usuário atualizado com sucesso!"
                status_esperado = 200
            
            if response.status_code == status_esperado:
                QMessageBox.information(self, "Sucesso", mensagem_sucesso)
                super().accept()
            else:
                raise Exception(response.json().get('erro', 'Erro desconhecido'))

        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Não foi possível salvar o usuário: {e}")
# ==============================================================================
# 4. WIDGETS DE CONTEÚDO (AS "TELAS" PRINCIPAIS)
# ==============================================================================

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
        self.tabela_produtos.setColumnCount(8)
        self.tabela_produtos.setHorizontalHeaderLabels(["Código", "Nome", "Descrição", "Preço", "Código B", "Código C", "Fornecedores", "Naturezas"])
        self.tabela_produtos.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabela_produtos.setAlternatingRowColors(True)
        header = self.tabela_produtos.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)

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
                    self.tabela_produtos.setItem(linha, 4, QTableWidgetItem(produto.get('codigoB', '')))
                    self.tabela_produtos.setItem(linha, 5, QTableWidgetItem(produto.get('codigoC', '')))
                    self.tabela_produtos.setItem(linha, 6, QTableWidgetItem(produto.get('fornecedores', '')))
                    self.tabela_produtos.setItem(linha, 7, QTableWidgetItem(produto.get('naturezas', '')))
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
        self.tabela_estoque.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
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

class FornecedoresWidget(QWidget):
    """Tela para gerir (CRUD) os fornecedores."""
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
        self.tabela_fornecedores.setColumnCount(1)
        self.tabela_fornecedores.setHorizontalHeaderLabels(["Nome"])
        self.tabela_fornecedores.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabela_fornecedores.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.layout.addWidget(self.titulo)
        self.layout.addLayout(layout_botoes)
        self.layout.addWidget(self.tabela_fornecedores)

        self.btn_adicionar.clicked.connect(self.abrir_formulario_adicionar)
        self.btn_editar.clicked.connect(self.abrir_formulario_editar)
        self.btn_excluir.clicked.connect(self.excluir_fornecedor_selecionado)

        self.carregar_fornecedores()

    def carregar_fornecedores(self):
        global access_token
        url = "http://127.0.0.1:5000/api/fornecedores"
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                fornecedores = response.json()
                self.tabela_fornecedores.setRowCount(len(fornecedores))
                for linha, forn in enumerate(fornecedores):
                    item_nome = QTableWidgetItem(forn['nome'])
                    item_nome.setData(Qt.UserRole, forn['id'])
                    self.tabela_fornecedores.setItem(linha, 0, item_nome)
            else:
                QMessageBox.warning(self, "Erro", "Não foi possível carregar os fornecedores.")
        except requests.exceptions.RequestException as e:
            print(f"Erro de Conexão: {e}")

    def abrir_formulario_adicionar(self):
        dialog = FormularioFornecedorDialog(self)
        if dialog.exec():
            self.carregar_fornecedores()

    def abrir_formulario_editar(self):
        linha_selecionada = self.tabela_fornecedores.currentRow()
        if linha_selecionada < 0:
            QMessageBox.warning(self, "Seleção", "Por favor, selecione um fornecedor para editar.")
            return
        item = self.tabela_fornecedores.item(linha_selecionada, 0)
        fornecedor_id = item.data(Qt.UserRole)
        dialog = FormularioFornecedorDialog(self, fornecedor_id=fornecedor_id)
        if dialog.exec():
            self.carregar_fornecedores()

    def excluir_fornecedor_selecionado(self):
        linha_selecionada = self.tabela_fornecedores.currentRow()
        if linha_selecionada < 0:
            QMessageBox.warning(self, "Seleção", "Por favor, selecione um fornecedor para excluir.")
            return
        item = self.tabela_fornecedores.item(linha_selecionada, 0)
        fornecedor_id = item.data(Qt.UserRole)
        nome_fornecedor = item.text()
        resposta = QMessageBox.question(self, "Confirmar Exclusão", f"Tem a certeza de que deseja excluir o fornecedor '{nome_fornecedor}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if resposta == QMessageBox.StandardButton.Yes:
            global access_token
            url = f"http://127.0.0.1:5000/api/fornecedores/{fornecedor_id}"
            headers = {'Authorization': f'Bearer {access_token}'}
            try:
                response = requests.delete(url, headers=headers)
                if response.status_code == 200:
                    QMessageBox.information(self, "Sucesso", "Fornecedor excluído com sucesso!")
                    self.carregar_fornecedores()
                else:
                    QMessageBox.warning(self, "Erro", f"Não foi possível excluir: {response.json().get('erro')}")
            except requests.exceptions.RequestException as e:
                QMessageBox.critical(self, "Erro de Conexão", f"Não foi possível conectar ao servidor: {e}")

class NaturezasWidget(QWidget):
    """Tela para gerir (CRUD) as naturezas."""
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
        self.tabela_naturezas.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabela_naturezas.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.layout.addWidget(self.titulo)
        self.layout.addLayout(layout_botoes)
        self.layout.addWidget(self.tabela_naturezas)

        self.btn_adicionar.clicked.connect(self.abrir_formulario_adicionar)
        self.btn_editar.clicked.connect(self.abrir_formulario_editar)
        self.btn_excluir.clicked.connect(self.excluir_natureza_selecionada)

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

    def abrir_formulario_editar(self):
        linha_selecionada = self.tabela_naturezas.currentRow()
        if linha_selecionada < 0:
            QMessageBox.warning(self, "Seleção", "Por favor, selecione uma natureza para editar.")
            return
        item = self.tabela_naturezas.item(linha_selecionada, 0)
        natureza_id = item.data(Qt.UserRole)
        dialog = FormularioNaturezaDialog(self, natureza_id=natureza_id)
        if dialog.exec():
            self.carregar_naturezas()

    def excluir_natureza_selecionada(self):
        linha_selecionada = self.tabela_naturezas.currentRow()
        if linha_selecionada < 0:
            QMessageBox.warning(self, "Seleção", "Por favor, selecione uma natureza para excluir.")
            return
        item = self.tabela_naturezas.item(linha_selecionada, 0)
        natureza_id = item.data(Qt.UserRole)
        nome_natureza = item.text()
        resposta = QMessageBox.question(self, "Confirmar Exclusão", f"Tem a certeza de que deseja excluir a natureza '{nome_natureza}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if resposta == QMessageBox.StandardButton.Yes:
            global access_token
            url = f"http://127.0.0.1:5000/api/naturezas/{natureza_id}"
            headers = {'Authorization': f'Bearer {access_token}'}
            try:
                response = requests.delete(url, headers=headers)
                if response.status_code == 200:
                    QMessageBox.information(self, "Sucesso", "Natureza excluída com sucesso!")
                    self.carregar_naturezas()
                else:
                    QMessageBox.warning(self, "Erro", f"Não foi possível excluir: {response.json().get('erro')}")
            except requests.exceptions.RequestException as e:
                QMessageBox.critical(self, "Erro de Conexão", f"Não foi possível conectar ao servidor: {e}")



# TRECHO 2: ADICIONAR esta nova classe ao main_ui.py

class UsuariosWidget(QWidget):
    """Tela para gerir (CRUD) os usuários."""
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.titulo = QLabel("Gestão de Usuários")
        self.titulo.setStyleSheet("font-size: 24px; font-weight: bold;")

        layout_botoes = QHBoxLayout()
        self.btn_adicionar = QPushButton("Adicionar Novo")
        self.btn_editar = QPushButton("Editar Selecionado")
        self.btn_desativar = QPushButton("Desativar/Reativar") # Texto mais claro
        layout_botoes.addWidget(self.btn_adicionar)
        layout_botoes.addWidget(self.btn_editar)
        layout_botoes.addWidget(self.btn_desativar)
        layout_botoes.addStretch(1)

        self.tabela_usuarios = QTableWidget()
        self.tabela_usuarios.setColumnCount(4)
        self.tabela_usuarios.setHorizontalHeaderLabels(["Nome", "Login", "Permissão", "Status"])
        self.tabela_usuarios.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabela_usuarios.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows) # Melhor para selecionar
        self.tabela_usuarios.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabela_usuarios.setAlternatingRowColors(True)

        self.layout.addWidget(self.titulo)
        self.layout.addLayout(layout_botoes)
        self.layout.addWidget(self.tabela_usuarios)

        # Conexões
        self.btn_adicionar.clicked.connect(self.abrir_formulario_adicionar)
        self.btn_editar.clicked.connect(self.abrir_formulario_editar)
        self.btn_desativar.clicked.connect(self.desativar_usuario_selecionado)

        self.carregar_usuarios()

    def carregar_usuarios(self):
        global access_token
        url = "http://127.0.0.1:5000/api/usuarios"
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                usuarios = response.json()
                self.tabela_usuarios.setRowCount(len(usuarios))
                for linha, user in enumerate(usuarios):
                    item_nome = QTableWidgetItem(user['nome'])
                    # Guardamos o ID no primeiro item da linha para fácil acesso
                    item_nome.setData(Qt.UserRole, user['id'])
                    
                    status = "Ativo" if user['ativo'] else "Inativo"
                    
                    self.tabela_usuarios.setItem(linha, 0, item_nome)
                    self.tabela_usuarios.setItem(linha, 1, QTableWidgetItem(user['login']))
                    self.tabela_usuarios.setItem(linha, 2, QTableWidgetItem(user['permissao']))
                    self.tabela_usuarios.setItem(linha, 3, QTableWidgetItem(status))
            else:
                QMessageBox.warning(self, "Erro", "Não foi possível carregar os usuários.")
        except requests.exceptions.RequestException as e:
            print(f"Erro de Conexão: {e}")

    def abrir_formulario_adicionar(self):
        """Abre o diálogo para adicionar um novo usuário."""
        dialog = FormularioUsuarioDialog(self)
        if dialog.exec():
            self.carregar_usuarios()
    
    def abrir_formulario_editar(self):
        """Abre o diálogo para editar o usuário selecionado."""
        linha_selecionada = self.tabela_usuarios.currentRow()
        if linha_selecionada < 0:
            QMessageBox.warning(self, "Seleção", "Por favor, selecione um usuário para editar.")
            return
        
        # Pega o item da primeira coluna (onde guardamos o ID)
        item_id = self.tabela_usuarios.item(linha_selecionada, 0)
        usuario_id = item_id.data(Qt.UserRole)
        
        dialog = FormularioUsuarioDialog(self, usuario_id=usuario_id)
        if dialog.exec():
            self.carregar_usuarios()

    def desativar_usuario_selecionado(self):
        """Envia um pedido para desativar (soft delete) o usuário selecionado."""
        linha_selecionada = self.tabela_usuarios.currentRow()
        if linha_selecionada < 0:
            QMessageBox.warning(self, "Seleção", "Por favor, selecione um usuário.")
            return
        
        item_id = self.tabela_usuarios.item(linha_selecionada, 0)
        usuario_id = item_id.data(Qt.UserRole)
        nome_usuario = self.tabela_usuarios.item(linha_selecionada, 0).text()
        status_atual = self.tabela_usuarios.item(linha_selecionada, 3).text()

        acao = "desativar" if status_atual == "Ativo" else "reativar"
        
        resposta = QMessageBox.question(self, f"Confirmar Ação",
                                        f"Tem certeza que deseja {acao} o usuário '{nome_usuario}'?",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if resposta == QMessageBox.StandardButton.Yes:
            global access_token
            # --- DEBUG: Adicione esta linha para ver o ID no terminal ---
            print(f"Tentando {acao} usuário com ID: {usuario_id}")
            
            url = f"http://127.0.0.1:5000/api/usuarios/{usuario_id}"
            headers = {'Authorization': f'Bearer {access_token}'}
            try:
                response = requests.delete(url, headers=headers)
                
                # Resposta de sucesso
                if response.status_code == 200:
                    QMessageBox.information(self, "Sucesso", response.json()['mensagem'])
                    self.carregar_usuarios()
                # Resposta de erro (mas controlada)
                else:
                    mensagem_erro = f"O servidor retornou um erro: {response.status_code}."
                    try:
                        # Tenta obter a mensagem de erro específica do JSON
                        detalhe_erro = response.json().get('erro')
                        if detalhe_erro:
                            mensagem_erro += f"\nDetalhe: {detalhe_erro}"
                    except requests.exceptions.JSONDecodeError:
                        # Se não for JSON, apenas mostra o texto bruto da resposta
                        mensagem_erro += f"\nResposta: {response.text}"
                    
                    QMessageBox.warning(self, "Erro", mensagem_erro)

            except requests.exceptions.RequestException as e:
                QMessageBox.critical(self, "Erro de Conexão", f"Não foi possível conectar ao servidor: {e}")
# ==============================================================================
# 5. CLASSE DA JANELA PRINCIPAL
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

        # Inicializa com dados vazios
        self.dados_usuario = {}

        # --- BARRA DE MENUS ---
        menu_bar = self.menuBar()
        menu_arquivo = menu_bar.addMenu("&Arquivo")
        acao_sair = QAction("Sair", self)
        acao_sair.triggered.connect(self.close)
        menu_arquivo.addAction(acao_sair)
        menu_cadastros = menu_bar.addMenu("&Cadastros")
        self.acao_produtos = QAction("Produtos...", self)
        menu_cadastros.addAction(self.acao_produtos)

        # --- LAYOUT GERAL E WIDGET CENTRAL ---
        widget_central = QWidget()
        self.setCentralWidget(widget_central)
        layout_principal = QHBoxLayout(widget_central)

        # --- PAINEL DE NAVEGAÇÃO LATERAL ---
        painel_lateral = QWidget()
        painel_lateral.setObjectName("painelLateral")
        painel_lateral.setFixedWidth(200)
        self.layout_painel_lateral = QVBoxLayout(painel_lateral) # Tornando o layout um atributo
        self.layout_painel_lateral.setAlignment(Qt.AlignTop)

        self.btn_dashboard = QPushButton("Dashboard")
        self.btn_produtos = QPushButton("Produtos")
        self.btn_estoque = QPushButton("Estoque")
        self.btn_fornecedores = QPushButton("Fornecedores")
        self.btn_naturezas = QPushButton("Naturezas")
        self.btn_usuarios = QPushButton("Usuários")

        self.layout_painel_lateral.addWidget(self.btn_dashboard)
        self.layout_painel_lateral.addWidget(self.btn_produtos)
        self.layout_painel_lateral.addWidget(self.btn_estoque)
        self.layout_painel_lateral.addWidget(self.btn_fornecedores)
        self.layout_painel_lateral.addWidget(self.btn_naturezas)
        # O botão de usuários será adicionado depois, na função de carregar dados
        
        self.layout_painel_lateral.addStretch(1)
        layout_principal.addWidget(painel_lateral)

        # --- ÁREA DE CONTEÚDO ---
        self.stacked_widget = QStackedWidget()
        layout_principal.addWidget(self.stacked_widget)
        self.tela_dashboard = QLabel("Bem-vindo ao Sistema!\n\nSelecione uma opção no menu lateral para começar.")
        self.tela_dashboard.setAlignment(Qt.AlignCenter)
        self.tela_dashboard.setStyleSheet("font-size: 18px; color: #555;")
        self.tela_produtos = ProdutosWidget()
        self.tela_estoque = EstoqueWidget()
        self.tela_fornecedores = FornecedoresWidget()
        self.tela_naturezas = NaturezasWidget()
        self.tela_usuarios = UsuariosWidget()
        # A tela de usuários será criada depois
        
        self.stacked_widget.addWidget(self.tela_dashboard)
        self.stacked_widget.addWidget(self.tela_produtos)
        self.stacked_widget.addWidget(self.tela_estoque)
        self.stacked_widget.addWidget(self.tela_fornecedores)
        self.stacked_widget.addWidget(self.tela_naturezas)
        self.stacked_widget.addWidget(self.tela_usuarios)

        # --- CONEXÕES ---
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
        # Primeiro, manda a tela de estoque recarregar os seus dados
        self.tela_estoque.carregar_dados_estoque()
        # Depois, exibe a tela já atualizada
        self.stacked_widget.setCurrentWidget(self.tela_estoque)
        
    def mostrar_tela_fornecedores(self):
        self.stacked_widget.setCurrentWidget(self.tela_fornecedores)
        
    def mostrar_tela_naturezas(self):
        self.stacked_widget.setCurrentWidget(self.tela_naturezas)
        
    def carregar_dados_usuario(self, dados_usuario):
        """Recebe os dados do usuário logado e ajusta a UI de acordo com as permissões."""
        self.dados_usuario = dados_usuario
        
        # Atualiza a barra de status
        nome_usuario = self.dados_usuario.get('nome', 'N/A')
        permissao_usuario = self.dados_usuario.get('permissao', 'N/A')
        self.statusBar().showMessage(f"Usuário: {nome_usuario} | Permissão: {permissao_usuario}")

        # Lógica para mostrar/esconder o botão de usuários
        if self.dados_usuario.get('permissao') == 'Administrador':
            # Insere o botão na penúltima posição do layout lateral
            self.layout_painel_lateral.insertWidget(self.layout_painel_lateral.count() - 1, self.btn_usuarios)
            self.btn_usuarios.clicked.connect(self.mostrar_tela_usuarios)
            # TODO: Criar e adicionar a tela de usuários ao stacked_widget
        else:
            self.btn_usuarios.hide()
            
    def mostrar_tela_usuarios(self):
        self.stacked_widget.setCurrentWidget(self.tela_usuarios)

# ==============================================================================
# 6. CLASSE DA JANELA DE LOGIN (Movida para o final para resolver NameError)
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
                
                # Busca os dados do usuário logado
                headers = {'Authorization': f'Bearer {access_token}'}
                url_me = "http://127.0.0.1:5000/api/usuario/me"
                response_me = requests.get(url_me, headers=headers)
                
                if response_me.status_code == 200:
                    dados_usuario_logado = response_me.json()
                else:
                    dados_usuario_logado = {'nome': 'Desconhecido', 'permissao': 'Usuario'}
                
                self.close()
                
                # Cria a janela principal primeiro
                self.janela_principal = JanelaPrincipal()
                # DEPOIS, carrega os dados do usuário nela
                self.janela_principal.carregar_dados_usuario(dados_usuario_logado)
                # E só então a exibe
                self.janela_principal.show()
            else:
                erro_msg = response.json().get('erro', 'Ocorreu um erro desconhecido.')
                QMessageBox.warning(self, "Erro de Login", f"Falha no login: {erro_msg}")
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Erro de Conexão", f"Não foi possível conectar ao servidor: {e}")

# ==============================================================================
# 7. BLOCO DE EXECUÇÃO PRINCIPAL
# ==============================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    janela_login = JanelaLogin()
    janela_login.show()
    sys.exit(app.exec())
