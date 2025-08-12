# ==============================================================================
# 1. IMPORTS
# Centraliza todas as bibliotecas necessárias para a aplicação.
# ==============================================================================
import sys
import os
import requests
import traceback

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QMessageBox, QMainWindow, QHBoxLayout, QStackedWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QSizePolicy, QDialog, QFormLayout,
    QDialogButtonBox, QListWidget, QListWidgetItem, QAbstractItemView,
    QComboBox, QFileDialog, QFrame, QDateEdit, QCalendarWidget, QMenu,
    QTextEdit
)
from PySide6.QtGui import (
    QPixmap, QAction, QDoubleValidator, QKeySequence, QIcon
)
from PySide6.QtCore import (
    Qt, QTimer, Signal, QDate, QEvent
)

from config import SERVER_IP

# ==============================================================================
# 2. FUNÇÕES AUXILIARES E VARIÁVEIS GLOBAIS
# ==============================================================================
access_token = None
API_BASE_URL = f"http://{SERVER_IP}:5000"

def resource_path(relative_path):
    """ Retorna o caminho absoluto para o recurso, funcionando tanto no desenvolvimento quanto no .exe do PyInstaller. """
    try:
        # PyInstaller cria uma pasta temporária e armazena o caminho em _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ==============================================================================
# 3. JANELAS DE DIÁLOGO (FORMULÁRIOS)
# ==============================================================================

class FormularioProdutoDialog(QDialog):
    """Janela de formulário para Adicionar ou Editar um Produto."""
    def __init__(self, parent=None, produto_id=None):
        super().__init__(parent)
        self.produto_id = produto_id
        self.setWindowTitle("Adicionar Novo Produto" if self.produto_id is None else "Editar Produto")
        self.setMinimumSize(450, 600)
        self.layout = QFormLayout(self)
    
        # 1. CRIAÇÃO DE TODOS OS COMPONENTES VISUAIS
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
        self.label_status_codigo = QLabel("")
        self.label_status_codigo.setFixedWidth(100)
        self.btn_add_fornecedor = QPushButton("+")
        self.btn_add_fornecedor.setFixedSize(25, 25)
        self.btn_add_fornecedor.setObjectName("btnQuickAdd")
        self.btn_add_natureza = QPushButton("+")
        self.btn_add_natureza.setFixedSize(25, 25)
        self.btn_add_natureza.setObjectName("btnQuickAdd")
        self.botoes = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        
        self.verificacao_timer = QTimer(self)
        self.verificacao_timer.setSingleShot(True)
        self.verificacao_timer.timeout.connect(self.verificar_codigo_produto)
    
        # 2. ORGANIZAÇÃO DO LAYOUT
        layout_codigo = QHBoxLayout()
        layout_codigo.addWidget(self.input_codigo)
        layout_codigo.addWidget(self.label_status_codigo)
        self.layout.addRow("Código:", layout_codigo) 
        self.layout.addRow("Nome:", self.input_nome)
        self.layout.addRow("Descrição:", self.input_descricao)
        self.layout.addRow("Preço:", self.input_preco)
        self.layout.addRow("Código B:", self.input_codigoB)
        self.layout.addRow("Código C:", self.input_codigoC)
        
        layout_forn = QHBoxLayout()
        layout_forn.addWidget(QLabel("Fornecedores:"))
        layout_forn.addWidget(self.btn_add_fornecedor)
        layout_forn.addStretch(1)
        
        layout_nat = QHBoxLayout()
        layout_nat.addWidget(QLabel("Naturezas:"))
        layout_nat.addWidget(self.btn_add_natureza)
        layout_nat.addStretch(1)

        self.layout.addRow(layout_forn)
        self.layout.addRow(self.lista_fornecedores)
        self.layout.addRow(layout_nat)
        self.layout.addRow(self.lista_naturezas)
        self.layout.addWidget(self.botoes)
        
        # 3. CONEXÕES DOS SINAIS
        self.input_codigo.installEventFilter(self)
        self.input_codigo.textChanged.connect(self.iniciar_verificacao_timer)
        self.input_codigoC.returnPressed.connect(self.botoes.button(QDialogButtonBox.StandardButton.Save).click)
        
        self.btn_add_fornecedor.clicked.connect(self.adicionar_rapido_fornecedor)
        self.btn_add_natureza.clicked.connect(self.adicionar_rapido_natureza)
        
        self.botoes.accepted.connect(self.accept)
        self.botoes.rejected.connect(self.reject)
        
        # 4. CARGA INICIAL DE DADOS
        self.carregar_listas_de_apoio()
        if self.produto_id:
            self.carregar_dados_produto()

    def eventFilter(self, source, event):
        if source is self.input_codigo and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                self.input_nome.setFocus()
                return True
        return super().eventFilter(source, event)

    def iniciar_verificacao_timer(self):
        if self.produto_id is None:
            self.label_status_codigo.setText("Verificando...")
            self.verificacao_timer.stop()
            self.verificacao_timer.start(500)

    def verificar_codigo_produto(self):
        codigo = self.input_codigo.text().strip()
        if not codigo:
            self.label_status_codigo.setText("")
            return
        
        global access_token
        url = f"{API_BASE_URL}/api/produtos/codigo/{codigo}"
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 404:
                self.label_status_codigo.setText("✅ Disponível")
                self.label_status_codigo.setStyleSheet("color: #28a745;")
            elif response.status_code == 200:
                self.label_status_codigo.setText("❌ Já existe!")
                self.label_status_codigo.setStyleSheet("color: #dc3545;")
            else:
                self.label_status_codigo.setText("")
        except requests.exceptions.RequestException:
            self.label_status_codigo.setText("⚠️ Erro")
            self.label_status_codigo.setStyleSheet("color: #ffc107;")

    def adicionar_rapido_fornecedor(self):
        dialog = QuickAddDialog(self, "Adicionar Novo Fornecedor", "/api/fornecedores")
        dialog.item_adicionado.connect(self.carregar_listas_de_apoio)
        dialog.exec()

    def adicionar_rapido_natureza(self):
        dialog = QuickAddDialog(self, "Adicionar Nova Natureza", "/api/naturezas")
        dialog.item_adicionado.connect(self.carregar_listas_de_apoio)
        dialog.exec()
        
    def carregar_listas_de_apoio(self):
        self.lista_fornecedores.clear()
        self.lista_naturezas.clear()
        
        global access_token
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            url_forn = f"{API_BASE_URL}/api/fornecedores"
            response_forn = requests.get(url_forn, headers=headers)
            if response_forn.status_code == 200:
                for forn in response_forn.json():
                    item = QListWidgetItem(forn['nome'])
                    item.setData(Qt.UserRole, forn['id'])
                    self.lista_fornecedores.addItem(item)
            
            url_nat = f"{API_BASE_URL}/api/naturezas"
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
        url = f"{API_BASE_URL}/api/produtos/{self.produto_id}"
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
        nome = self.input_nome.text().strip()
        codigo = self.input_codigo.text().strip()
        preco = self.input_preco.text().strip()
        if not nome or not codigo or not preco:
            QMessageBox.warning(self, "Campos Obrigatórios", "Por favor, preencha todos os campos: Código, Nome e Preço.")
            return
        
        global access_token
        headers = {'Authorization': f'Bearer {access_token}'}
        
        dados_produto = {
            "codigo": codigo, "nome": nome, "preco": preco.replace(',', '.'),
            "descricao": self.input_descricao.text(),
            "codigoB": self.input_codigoB.text(), "codigoC": self.input_codigoC.text()
        }
        
        ids_fornecedores_selecionados = [
            self.lista_fornecedores.item(i).data(Qt.UserRole) 
            for i in range(self.lista_fornecedores.count()) 
            if self.lista_fornecedores.item(i).isSelected()
        ]
        
        ids_naturezas_selecionadas = [
            self.lista_naturezas.item(i).data(Qt.UserRole)
            for i in range(self.lista_naturezas.count())
            if self.lista_naturezas.item(i).isSelected()
        ]

        try:
            if self.produto_id is None:
                url_produto = f"{API_BASE_URL}/api/produtos"
                response_produto = requests.post(url_produto, headers=headers, json=dados_produto)
                if response_produto.status_code != 201:
                    raise Exception(response_produto.json().get('erro', 'Erro ao criar produto'))
                
                produto_salvo_id = response_produto.json().get('id_produto_criado')
                dados_produto['fornecedores_ids'] = ids_fornecedores_selecionados
                dados_produto['naturezas_ids'] = ids_naturezas_selecionadas
                url_update = f"{API_BASE_URL}/api/produtos/{produto_salvo_id}"
                response_update = requests.put(url_update, headers=headers, json=dados_produto)

                if response_update.status_code != 200:
                    raise Exception(response_update.json().get('erro', 'Produto criado, mas falha ao salvar associações'))
            else:
                dados_produto['fornecedores_ids'] = ids_fornecedores_selecionados
                dados_produto['naturezas_ids'] = ids_naturezas_selecionadas
                
                url = f"{API_BASE_URL}/api/produtos/{self.produto_id}"
                response = requests.put(url, headers=headers, json=dados_produto)

                if response.status_code != 200:
                    raise Exception(response.json().get('erro', 'Erro ao atualizar produto'))

            QMessageBox.information(self, "Sucesso", "Produto salvo com sucesso!")
            super().accept()
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Não foi possível salvar o produto: {e}")

class FormularioFornecedorDialog(QDialog):
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
        url = f"{API_BASE_URL}/api/fornecedores/{self.fornecedor_id}"
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
                url = f"{API_BASE_URL}/api/fornecedores"
                response = requests.post(url, headers=headers, json=dados)
                if response.status_code == 201:
                    QMessageBox.information(self, "Sucesso", "Fornecedor adicionado com sucesso!")
                    super().accept()
                else: raise Exception(response.json().get('erro', 'Erro desconhecido'))
            else:
                url = f"{API_BASE_URL}/api/fornecedores/{self.fornecedor_id}"
                response = requests.put(url, headers=headers, json=dados)
                if response.status_code == 200:
                    QMessageBox.information(self, "Sucesso", "Fornecedor atualizado com sucesso!")
                    super().accept()
                else: raise Exception(response.json().get('erro', 'Erro desconhecido'))
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Não foi possível salvar o fornecedor: {e}")

class FormularioNaturezaDialog(QDialog):
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
        url = f"{API_BASE_URL}/api/naturezas/{self.natureza_id}"
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
                url = f"{API_BASE_URL}/api/naturezas"
                response = requests.post(url, headers=headers, json=dados)
                if response.status_code == 201:
                    QMessageBox.information(self, "Sucesso", "Natureza adicionada com sucesso!")
                    super().accept()
                else: raise Exception(response.json().get('erro', 'Erro desconhecido'))
            else:
                url = f"{API_BASE_URL}/api/naturezas/{self.natureza_id}"
                response = requests.put(url, headers=headers, json=dados)
                if response.status_code == 200:
                    QMessageBox.information(self, "Sucesso", "Natureza atualizada com sucesso!")
                    super().accept()
                else: raise Exception(response.json().get('erro', 'Erro desconhecido'))
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Não foi possível salvar a natureza: {e}")

class QuickAddDialog(QDialog):
    item_adicionado = Signal()

    def __init__(self, parent, titulo, endpoint):
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.endpoint = endpoint
        self.setMinimumWidth(300)

        self.layout = QVBoxLayout(self)
        self.form_layout = QFormLayout()
        
        self.input_nome = QLineEdit()
        self.form_layout.addRow("Nome:", self.input_nome)
        
        self.botoes = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        
        self.layout.addLayout(self.form_layout)
        self.layout.addWidget(self.botoes)

        self.botoes.accepted.connect(self.accept)
        self.botoes.rejected.connect(self.reject)

    def accept(self):
        nome = self.input_nome.text().strip()
        if not nome:
            QMessageBox.warning(self, "Erro", "O campo de nome não pode estar vazio.")
            return

        global access_token
        url = f"{API_BASE_URL}{self.endpoint}"
        headers = {'Authorization': f'Bearer {access_token}'}
        dados = {"nome": nome}

        try:
            response = requests.post(url, headers=headers, json=dados)
            if response.status_code == 201:
                QMessageBox.information(self, "Sucesso", "Item adicionado com sucesso!")
                self.item_adicionado.emit()
                super().accept()
            else:
                raise Exception(response.json().get('erro', 'Erro desconhecido'))
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Não foi possível salvar o item: {e}")

class FormularioUsuarioDialog(QDialog):
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
        global access_token
        url = f"{API_BASE_URL}/api/usuarios/{self.usuario_id}"
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
                self.reject()
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Erro de Conexão", f"Erro ao carregar dados: {e}")
            self.reject()

    def accept(self):
        global access_token
        
        if not self.input_nome.text().strip() or not self.input_login.text().strip():
            QMessageBox.warning(self, "Campos Obrigatórios", "Os campos Nome e Login são obrigatórios.")
            return
        
        dados = {
            "nome": self.input_nome.text(),
            "login": self.input_login.text(),
            "permissao": self.input_permissao.currentText()
        }

        if self.input_senha.text():
            dados['senha'] = self.input_senha.text()
        elif self.usuario_id is None:
            QMessageBox.warning(self, "Campo Obrigatório", "A senha é obrigatória para novos usuários.")
            return

        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            if self.usuario_id is None:
                url = f"{API_BASE_URL}/api/usuarios"
                response = requests.post(url, headers=headers, json=dados)
                mensagem_sucesso = "Usuário adicionado com sucesso!"
                status_esperado = 201
            else:
                url = f"{API_BASE_URL}/api/usuarios/{self.usuario_id}"
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

# Em main_ui.py, adicione esta nova classe

class ImportacaoWidget(QWidget):
    """Tela para importação de produtos em massa a partir de um ficheiro CSV."""
    # --- ADIÇÃO 1: Definimos o novo sinal que a classe pode emitir ---
    produtos_importados_sucesso = Signal()

    def __init__(self):
        super().__init__()
        # O resto do seu __init__ continua exatamente igual...
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.caminho_ficheiro = None

        titulo = QLabel("Importação de Produtos em Massa")
        titulo.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 10px;")
        
        instrucoes = QLabel(
            "<b>Instruções:</b><br>"
            "1. Prepare uma planilha com as seguintes colunas obrigatórias: <b>codigo, nome, preco</b>.<br>"
            "2. Colunas opcionais: <b>quantidade</b>, <b>descricao</b>, <b>fornecedores_nomes</b>, <b>naturezas_nomes</b>.<br>"
            "3. Para múltiplos fornecedores ou naturezas, separe os nomes por vírgula (ex: 'Fornecedor A, Fornecedor B').<br>"
            "4. Salve a planilha no formato <b>CSV (Valores separados por vírgulas)</b>.<br>"
        )
        instrucoes.setWordWrap(True)

        layout_selecao = QHBoxLayout()
        self.btn_selecionar = QPushButton("📂 Selecionar Ficheiro CSV...")
        self.label_ficheiro = QLabel("Nenhum ficheiro selecionado.")
        layout_selecao.addWidget(self.btn_selecionar)
        layout_selecao.addWidget(self.label_ficheiro)
        layout_selecao.addStretch(1)

        self.btn_importar = QPushButton("🚀 Iniciar Importação")
        self.btn_importar.setObjectName("btnImportar")
        self.btn_importar.setEnabled(False)

        label_resultados = QLabel("Resultados da Importação:")
        self.text_resultados = QTextEdit()
        self.text_resultados.setReadOnly(True)

        self.layout.addWidget(titulo)
        self.layout.addWidget(instrucoes)
        self.layout.addLayout(layout_selecao)
        self.layout.addWidget(self.btn_importar)
        self.layout.addWidget(label_resultados)
        self.layout.addWidget(self.text_resultados)

        self.btn_selecionar.clicked.connect(self.selecionar_ficheiro)
        self.btn_importar.clicked.connect(self.iniciar_importacao)


    def selecionar_ficheiro(self):
        caminho, _ = QFileDialog.getOpenFileName(self, "Selecionar Ficheiro CSV", "", "Ficheiros CSV (*.csv)")
        if caminho:
            self.caminho_ficheiro = caminho
            self.label_ficheiro.setText(os.path.basename(caminho))
            self.btn_importar.setEnabled(True)
            self.text_resultados.clear()

    def iniciar_importacao(self):
        if not self.caminho_ficheiro:
            return

        self.text_resultados.setText("A importar... Por favor, aguarde.")
        QApplication.processEvents()

        global access_token
        url = f"{API_BASE_URL}/api/produtos/importar"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        try:
            with open(self.caminho_ficheiro, 'rb') as f:
                files = {'file': (os.path.basename(self.caminho_ficheiro), f, 'text/csv')}
                response = requests.post(url, headers=headers, files=files)

            if response.status_code == 200:
                dados = response.json()
                resultado_texto = f"{dados.get('mensagem', '')}\n"
                resultado_texto += f"Produtos importados com sucesso: {dados.get('produtos_importados', 0)}\n\n"
                
                erros = dados.get('erros', [])
                if erros:
                    resultado_texto += "Erros encontrados:\n"
                    resultado_texto += "\n".join(erros)
                
                self.text_resultados.setText(resultado_texto)
                
                # --- ADIÇÃO 2: Emitimos o sinal se a importação teve sucesso ---
                if dados.get('produtos_importados', 0) > 0:
                    self.produtos_importados_sucesso.emit()
            else:
                self.text_resultados.setText(f"Erro na API: {response.text}")

        except Exception as e:
            self.text_resultados.setText(f"Ocorreu um erro crítico: {e}")
        
        self.btn_importar.setEnabled(False)

class ProdutosWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.titulo = QLabel("Gestão de Produtos")
        self.titulo.setStyleSheet("font-size: 24px; font-weight: bold;")
        
        layout_botoes = QHBoxLayout()
        self.btn_adicionar = QPushButton("➕ Adicionar Novo")
        self.btn_editar = QPushButton("✏️ Editar Selecionado")
        self.btn_excluir = QPushButton("🗑️ Excluir Selecionado")
        self.btn_adicionar.setObjectName("btnPositive")
        self.btn_editar.setObjectName("btnNeutral")
        self.btn_excluir.setObjectName("btnNegative")
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
        dialog.carregar_listas_de_apoio()
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
        dialog.carregar_listas_de_apoio()
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
            url = f"{API_BASE_URL}/api/produtos/{produto_id}"
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
        url = f"{API_BASE_URL}/api/produtos"
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

class SaldosWidget(QWidget):
    """Tela para visualizar os saldos de estoque, com pesquisa via API e ordenação local."""
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.dados_exibidos = [] # Guarda os dados atualmente na tabela

        # --- Título ---
        self.titulo = QLabel("Consulta de Saldos de Estoque")
        self.titulo.setStyleSheet("font-size: 24px; font-weight: bold;")

        # --- Layout de Controles ---
        layout_controles = QHBoxLayout()
        
        self.input_pesquisa = QLineEdit()
        self.input_pesquisa.setPlaceholderText("Buscar por Nome ou Códigos (A, B ou C)...")
        
        # --- BOTÕES DE ORDENAÇÃO COM ÍCONES ---
        self.btn_ordenar_nome = QPushButton("🔤 A-Z")
        self.btn_ordenar_nome.setToolTip("Ordenar por Nome do Produto")
        self.btn_ordenar_nome.setObjectName("btnIcon") # Damos um nome para o estilo

        self.btn_ordenar_codigo = QPushButton("🔢 Cód.")
        self.btn_ordenar_codigo.setToolTip("Ordenar por Código Principal")
        self.btn_ordenar_codigo.setObjectName("btnIcon")

        self.btn_recarregar = QPushButton("🔄 Recarregar")
        self.btn_recarregar.setToolTip("Limpar busca e recarregar a lista completa")

        layout_controles.addWidget(self.input_pesquisa)
        layout_controles.addWidget(self.btn_ordenar_nome)
        layout_controles.addWidget(self.btn_ordenar_codigo)
        layout_controles.addWidget(self.btn_recarregar)

        # --- Tabela de Estoque (sem alterações) ---
        self.tabela_estoque = QTableWidget()
        self.tabela_estoque.setColumnCount(6)
        self.tabela_estoque.setHorizontalHeaderLabels([
            "Código Principal", "Nome do Produto", "Saldo Atual", "Preço (R$)", "Código B", "Código C"
        ])
        self.tabela_estoque.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabela_estoque.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela_estoque.setAlternatingRowColors(True)
        header = self.tabela_estoque.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        # --- Adicionando Widgets ao Layout Principal ---
        self.layout.addWidget(self.titulo)
        self.layout.addLayout(layout_controles)
        self.layout.addWidget(self.tabela_estoque)

        # --- Temporizador para a busca ---
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.carregar_dados_estoque)

        # --- Conexões ---
        self.btn_recarregar.clicked.connect(self.recarregar_lista_completa)
        self.input_pesquisa.textChanged.connect(self.iniciar_busca_timer)
        self.btn_ordenar_nome.clicked.connect(self.ordenar_por_nome)
        self.btn_ordenar_codigo.clicked.connect(self.ordenar_por_codigo)

        # --- Carga Inicial ---
        self.carregar_dados_estoque()

    def iniciar_busca_timer(self):
        self.search_timer.stop()
        self.search_timer.start(300)

    def recarregar_lista_completa(self):
        self.input_pesquisa.clear()
        self.carregar_dados_estoque()

    def carregar_dados_estoque(self):
        global access_token
        params = {}
        termo_busca = self.input_pesquisa.text()
        if termo_busca:
            params['search'] = termo_busca

        url = f"{API_BASE_URL}/api/estoque/saldos"
        headers = {'Authorization': f'Bearer {access_token}'}
        
        try:
            response = requests.get(url, headers=headers, params=params)
            if response and response.status_code == 200:
                self.dados_exibidos = response.json() # Guarda os dados recebidos
                self.popular_tabela(self.dados_exibidos)
            else:
                QMessageBox.warning(self, "Erro", "Não foi possível carregar os saldos.")
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Erro de Conexão", f"Não foi possível conectar ao servidor: {e}")

    def popular_tabela(self, dados):
        self.tabela_estoque.setRowCount(0)
        self.tabela_estoque.setRowCount(len(dados))
        
        for linha, item in enumerate(dados):
            self.tabela_estoque.setItem(linha, 0, QTableWidgetItem(item['codigo']))
            self.tabela_estoque.setItem(linha, 1, QTableWidgetItem(item['nome']))
            
            saldo_item = QTableWidgetItem(str(item['saldo_atual']))
            saldo_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabela_estoque.setItem(linha, 2, saldo_item)

            preco_item = QTableWidgetItem(item['preco'])
            preco_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.tabela_estoque.setItem(linha, 3, preco_item)

            self.tabela_estoque.setItem(linha, 4, QTableWidgetItem(item['codigoB']))
            self.tabela_estoque.setItem(linha, 5, QTableWidgetItem(item['codigoC']))

    # --- LÓGICA DE ORDENAÇÃO LOCAL ---
    def ordenar_por_nome(self):
        """Ordena os dados já exibidos por nome e atualiza a tabela."""
        self.dados_exibidos.sort(key=lambda item: item['nome'].lower())
        self.popular_tabela(self.dados_exibidos)

    def ordenar_por_codigo(self):
        """Ordena os dados já exibidos por código e atualiza a tabela."""
        self.dados_exibidos.sort(key=lambda item: item['codigo'])
        self.popular_tabela(self.dados_exibidos)

class HistoricoWidget(QWidget):
    """Sub-tela para visualizar e filtrar o histórico de movimentações."""
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.dados_completos = []

        # --- Layout de Filtros ---
        layout_filtros = QHBoxLayout()
        self.combo_tipo = QComboBox()
        self.combo_tipo.addItems(["Todas", "Entrada", "Saida"]) # Corrigido para "Saida"
        self.combo_tipo.setStyleSheet("font-size: 14px; padding: 5px;")
        
        self.btn_recarregar = QPushButton("Recarregar Histórico")
        
        layout_filtros.addWidget(QLabel("Filtrar por tipo:"))
        layout_filtros.addWidget(self.combo_tipo)
        layout_filtros.addStretch(1)
        layout_filtros.addWidget(self.btn_recarregar)

        # --- Tabela de Histórico (com a nova coluna) ---
        self.tabela_historico = QTableWidget()
        self.tabela_historico.setColumnCount(8) # Aumentado para 8 colunas
        self.tabela_historico.setHorizontalHeaderLabels([
            "Data/Hora", "Cód. Produto", "Nome Produto", "Tipo", "Qtd. Mov.", "Saldo Após", "Usuário", "Motivo da Saída"
        ])
        self.tabela_historico.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabela_historico.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela_historico.setAlternatingRowColors(True)

        self.layout.addLayout(layout_filtros)
        self.layout.addWidget(self.tabela_historico)

        # --- Conexões ---
        self.btn_recarregar.clicked.connect(self.carregar_historico)
        # O filtro agora é aplicado diretamente na chamada da API
        self.combo_tipo.currentIndexChanged.connect(self.carregar_historico)

        # Carga inicial
        self.carregar_historico()

    def carregar_historico(self):
        """Busca o histórico filtrado da API e o exibe na tabela."""
        global access_token
        
        data_fim = QDate.currentDate()
        data_inicio = data_fim.addDays(-90)
        
        params = {
            'data_inicio': data_inicio.toString("yyyy-MM-dd"),
            'data_fim': data_fim.toString("yyyy-MM-dd"),
            'formato': 'json' # <<< ADICIONE ESTA LINHA CRUCIAL
        }
        
        filtro_tipo = self.combo_tipo.currentText()
        if filtro_tipo != "Todas":
            params['tipo'] = filtro_tipo
    
        url = f"{API_BASE_URL}/api/relatorios/movimentacoes"
        headers = {'Authorization': f'Bearer {access_token}'}
    
        try:
            response = requests.get(url, headers=headers, params=params)
            
            if response and response.status_code == 200:
                self.dados_completos = response.json()
                self.popular_tabela(self.dados_completos)
            else:
                mensagem = "Não foi possível carregar o histórico."
                if response:
                    mensagem += f"\n(Erro: {response.status_code})"
                QMessageBox.warning(self, "Erro", mensagem)
    
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Erro de Conexão", f"Não foi possível conectar ao servidor: {e}")
            
    def popular_tabela(self, dados):
        """Preenche a tabela com os dados fornecidos."""
        self.tabela_historico.setRowCount(0)
        self.tabela_historico.setRowCount(len(dados))

        for linha, mov in enumerate(dados):
            self.tabela_historico.setItem(linha, 0, QTableWidgetItem(mov['data_hora']))
            self.tabela_historico.setItem(linha, 1, QTableWidgetItem(mov['produto_codigo']))
            self.tabela_historico.setItem(linha, 2, QTableWidgetItem(mov['produto_nome']))
            self.tabela_historico.setItem(linha, 3, QTableWidgetItem(mov['tipo']))
            self.tabela_historico.setItem(linha, 4, QTableWidgetItem(str(mov['quantidade'])))
            # --- CORREÇÃO: Usa a chave 'saldo_apos' ---
            self.tabela_historico.setItem(linha, 5, QTableWidgetItem(str(mov.get('saldo_apos', ''))))
            self.tabela_historico.setItem(linha, 6, QTableWidgetItem(mov['usuario_nome']))
            self.tabela_historico.setItem(linha, 7, QTableWidgetItem(mov.get('motivo_saida', '')))


class RelatoriosWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        titulo = QLabel("Módulo de Geração de Relatórios")
        titulo.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 10px;")

        form_layout = QFormLayout()
        form_layout.setSpacing(15)

        self.combo_tipo_relatorio = QComboBox()
        self.combo_tipo_relatorio.addItems(["Inventário Atual", "Histórico de Movimentações"])
        self.combo_tipo_relatorio.setStyleSheet("font-size: 16px; padding: 8px;")
        form_layout.addRow("Selecione o Relatório:", self.combo_tipo_relatorio)

        self.label_data_inicio = QLabel("Data de Início:")
        self.input_data_inicio = QDateEdit(self)
        self.input_data_inicio.setCalendarPopup(True)
        self.input_data_inicio.setDate(QDate.currentDate().addMonths(-1))
        self.input_data_inicio.setStyleSheet("font-size: 16px; padding: 8px;")

        self.label_data_fim = QLabel("Data de Fim:")
        self.input_data_fim = QDateEdit(self)
        self.input_data_fim.setCalendarPopup(True)
        self.input_data_fim.setDate(QDate.currentDate())
        self.input_data_fim.setStyleSheet("font-size: 16px; padding: 8px;")
        
        form_layout.addRow(self.label_data_inicio, self.input_data_inicio)
        form_layout.addRow(self.label_data_fim, self.input_data_fim)

        self.label_tipo_mov = QLabel("Tipo de Movimentação:")
        self.combo_tipo_mov = QComboBox()
        self.combo_tipo_mov.addItems(["Todas", "Entrada", "Saida"])
        self.combo_tipo_mov.setStyleSheet("font-size: 16px; padding: 8px;")
        form_layout.addRow(self.label_tipo_mov, self.combo_tipo_mov)

        layout_botoes = QHBoxLayout()
        self.btn_gerar_pdf = QPushButton("Gerar PDF")
        self.btn_gerar_excel = QPushButton("Gerar Excel (XLSX)")
        self.btn_gerar_pdf.setObjectName("btnNegative")
        self.btn_gerar_excel.setObjectName("btnPositive")
        
        layout_botoes.addStretch(1)
        layout_botoes.addWidget(self.btn_gerar_pdf)
        layout_botoes.addWidget(self.btn_gerar_excel)

        self.layout.addWidget(titulo)
        self.layout.addLayout(form_layout)
        self.layout.addLayout(layout_botoes)
        self.layout.addStretch(1)

        self.combo_tipo_relatorio.currentIndexChanged.connect(self.atualizar_visibilidade_filtros)
        self.btn_gerar_pdf.clicked.connect(lambda: self.gerar_relatorio('pdf'))
        self.btn_gerar_excel.clicked.connect(lambda: self.gerar_relatorio('xlsx'))

        self.atualizar_visibilidade_filtros()

    def atualizar_visibilidade_filtros(self):
        relatorio_selecionado = self.combo_tipo_relatorio.currentText()
        is_historico = (relatorio_selecionado == "Histórico de Movimentações")
        
        self.label_data_inicio.setVisible(is_historico)
        self.input_data_inicio.setVisible(is_historico)
        self.label_data_fim.setVisible(is_historico)
        self.input_data_fim.setVisible(is_historico)
        self.label_tipo_mov.setVisible(is_historico)
        self.combo_tipo_mov.setVisible(is_historico)

    def gerar_relatorio(self, formato):
        relatorio_selecionado = self.combo_tipo_relatorio.currentText()
        
        params = {'formato': formato}
        endpoint = ""
        nome_arquivo_base = ""

        if relatorio_selecionado == "Inventário Atual":
            endpoint = f"{API_BASE_URL}/api/relatorios/inventario"
            nome_arquivo_base = "relatorio_inventario"
        else:
            endpoint = f"{API_BASE_URL}/api/relatorios/movimentacoes"
            nome_arquivo_base = "relatorio_movimentacoes"
            
            params['data_inicio'] = self.input_data_inicio.date().toString("yyyy-MM-dd")
            params['data_fim'] = self.input_data_fim.date().toString("yyyy-MM-dd")
            tipo_mov = self.combo_tipo_mov.currentText()
            if tipo_mov != "Todas":
                params['tipo'] = tipo_mov

        extensao = f".{formato}"
        caminho_salvar, _ = QFileDialog.getSaveFileName(self, "Salvar Relatório", f"{nome_arquivo_base}{extensao}", f"Arquivos {formato.upper()} (*{extensao})")

        if not caminho_salvar:
            return

        try:
            global access_token
            headers = {'Authorization': f'Bearer {access_token}'}
            response = requests.get(endpoint, headers=headers, params=params, stream=True)

            if response.status_code == 200:
                with open(caminho_salvar, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                QMessageBox.information(self, "Sucesso", f"Relatório salvo com sucesso em:\n{caminho_salvar}")
            else:
                QMessageBox.warning(self, "Erro", f"A API retornou um erro: {response.status_code}")
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Erro de Conexão", f"Não foi possível gerar o relatório: {e}")

class EstoqueWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,0)

        self.saldos_view = SaldosWidget()
        self.historico_view = HistoricoWidget()

        nav_layout = QHBoxLayout()
        self.btn_ver_saldos = QPushButton("Visualizar Saldos")
        self.btn_ver_historico = QPushButton("Ver Histórico")
        self.btn_ver_saldos.setCheckable(True)
        self.btn_ver_historico.setCheckable(True)
        self.btn_ver_saldos.setChecked(True)

        nav_layout.addWidget(self.btn_ver_saldos)
        nav_layout.addWidget(self.btn_ver_historico)
        nav_layout.addStretch(1)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.saldos_view)
        self.stack.addWidget(self.historico_view)

        self.layout.addLayout(nav_layout)
        self.layout.addWidget(self.stack)

        self.btn_ver_saldos.clicked.connect(self.mostrar_saldos)
        self.btn_ver_historico.clicked.connect(self.mostrar_historico)

    def mostrar_saldos(self):
        self.stack.setCurrentWidget(self.saldos_view)
        self.btn_ver_saldos.setChecked(True)
        self.btn_ver_historico.setChecked(False)
        self.saldos_view.carregar_dados_estoque()

    def mostrar_historico(self):
        self.stack.setCurrentWidget(self.historico_view)
        self.btn_ver_saldos.setChecked(False)
        self.btn_ver_historico.setChecked(True)
        self.historico_view.carregar_historico()
        
class FornecedoresWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.titulo = QLabel("Gestão de Fornecedores")
        self.titulo.setStyleSheet("font-size: 24px; font-weight: bold;")

        layout_botoes = QHBoxLayout()
        self.btn_adicionar = QPushButton("➕ Adicionar Novo")
        self.btn_editar = QPushButton("✏️ Editar Selecionado")
        self.btn_excluir = QPushButton("🗑️ Excluir Selecionado")
        self.btn_adicionar.setObjectName("btnPositive")
        self.btn_editar.setObjectName("btnNeutral")
        self.btn_excluir.setObjectName("btnNegative")
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
        url = f"{API_BASE_URL}/api/fornecedores"
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
            url = f"{API_BASE_URL}/api/fornecedores/{fornecedor_id}"
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
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.titulo = QLabel("Gestão de Naturezas")
        self.titulo.setStyleSheet("font-size: 24px; font-weight: bold;")

        layout_botoes = QHBoxLayout()
        self.btn_adicionar = QPushButton("➕ Adicionar Nova")
        self.btn_editar = QPushButton("✏️ Editar Selecionada")
        self.btn_excluir = QPushButton("🗑️ Excluir Selecionada")
        self.btn_adicionar.setObjectName("btnPositive")
        self.btn_editar.setObjectName("btnNeutral")
        self.btn_excluir.setObjectName("btnNegative")
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
        url = f"{API_BASE_URL}/api/naturezas"
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
            url = f"{API_BASE_URL}/api/naturezas/{natureza_id}"
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

class EntradaRapidaWidget(QWidget):
    """Tela para registar entradas de estoque de forma rápida por código de produto."""
    estoque_atualizado = Signal()
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.produto_encontrado_id = None

        # --- 1. CRIAÇÃO DE TODOS OS WIDGETS ---
        self.titulo = QLabel("Entrada Rápida de Estoque")
        self.titulo.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 10px;")
        
        self.input_codigo = QLineEdit()
        self.input_codigo.setPlaceholderText("Digite ou leia o código do produto aqui")
        
        self.btn_verificar = QPushButton("Verificar Produto")
        self.btn_verificar.setObjectName("btnNeutral")

        self.label_nome_produto = QLabel("Aguardando verificação...")
        
        self.input_quantidade = QLineEdit()
        self.input_quantidade.setPlaceholderText("0")
        self.input_quantidade.setValidator(QDoubleValidator(0, 99999, 0))
        
        self.btn_registrar = QPushButton("Registar Entrada")
        self.btn_registrar.setObjectName("btnPositive")

        # --- 2. ORGANIZAÇÃO DO LAYOUT ---
        form_layout = QFormLayout()
        form_layout.setSpacing(15)

        layout_codigo = QHBoxLayout()
        layout_codigo.addWidget(self.input_codigo)
        layout_codigo.addWidget(self.btn_verificar)
        form_layout.addRow("Código do Produto:", layout_codigo)
        form_layout.addRow("Produto Encontrado:", self.label_nome_produto)
        form_layout.addRow("Quantidade a Adicionar:", self.input_quantidade)

        self.layout.addWidget(self.titulo)
        self.layout.addLayout(form_layout)
        self.layout.addWidget(self.btn_registrar, 0, Qt.AlignmentFlag.AlignRight)
        self.layout.addStretch(1)

        # --- 3. CONEXÕES DOS SINAIS ---
        self.btn_verificar.clicked.connect(self.verificar_produto)
        self.input_codigo.returnPressed.connect(self.verificar_produto) 
        self.btn_registrar.clicked.connect(self.registrar_entrada)
        self.input_quantidade.returnPressed.connect(self.btn_registrar.click)

        # --- 4. ESTADO INICIAL ---
        self.resetar_formulario()

    def verificar_produto(self):
        codigo_produto = self.input_codigo.text().strip()
        if not codigo_produto:
            QMessageBox.warning(self, "Atenção", "O campo de código não pode estar vazio.")
            return

        global access_token
        url = f"{API_BASE_URL}/api/produtos/codigo/{codigo_produto}"
        headers = {'Authorization': f'Bearer {access_token}'}

        try:
            response = requests.get(url, headers=headers)
            if response and response.status_code == 200:
                dados_produto = response.json()
                self.produto_encontrado_id = dados_produto['id']
                nome = dados_produto['nome']
                self.label_nome_produto.setText(f"{nome}")
                self.label_nome_produto.setStyleSheet("font-size: 16px; font-weight: bold; color: #28a745;")
                self.input_quantidade.setEnabled(True)
                self.btn_registrar.setEnabled(True)
                self.input_quantidade.setFocus()
            else:
                self.label_nome_produto.setText("Produto não encontrado!")
                self.label_nome_produto.setStyleSheet("font-size: 16px; font-weight: bold; color: #dc3545;")
                self.produto_encontrado_id = None
                self.input_quantidade.clear()
                self.input_quantidade.setEnabled(False)
                self.btn_registrar.setEnabled(False)
                self.input_codigo.selectAll()
                self.input_codigo.setFocus()
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Erro de Conexão", f"Não foi possível conectar ao servidor: {e}")

    def registrar_entrada(self):
        quantidade = self.input_quantidade.text()
        if not self.produto_encontrado_id or not quantidade or int(quantidade) <= 0:
            QMessageBox.warning(self, "Dados Inválidos", "Verifique o produto e insira uma quantidade válida maior que zero.")
            return

        global access_token
        url = f"{API_BASE_URL}/api/estoque/entrada"
        headers = {'Authorization': f'Bearer {access_token}'}
        dados = {
            "id_produto": self.produto_encontrado_id,
            "quantidade": int(quantidade)
        }

        try:
            response = requests.post(url, headers=headers, json=dados)
            if response and response.status_code == 201:
                self.estoque_atualizado.emit()
                QMessageBox.information(self, "Sucesso", "Entrada de estoque registada com sucesso!")
                self.resetar_formulario()
            else:
                erro = response.json().get('erro', 'Erro desconhecido.')
                QMessageBox.warning(self, "Erro", f"Não foi possível registar a entrada: {erro}")
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Erro de Conexão", f"Não foi possível conectar ao servidor: {e}")

    def resetar_formulario(self):
        self.produto_encontrado_id = None
        self.input_codigo.clear()
        self.input_quantidade.clear()
        self.label_nome_produto.setText("Aguardando verificação...")
        self.label_nome_produto.setStyleSheet("font-size: 16px; font-weight: bold; color: #555;")
        self.input_quantidade.setEnabled(False)
        self.btn_registrar.setEnabled(False)
        self.input_codigo.setFocus()

class SaidaRapidaWidget(QWidget):
    """Tela para registar saídas de estoque de forma rápida por código de produto."""
    estoque_atualizado = Signal()

    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.produto_encontrado_id = None

        # --- 1. CRIAÇÃO DE TODOS OS WIDGETS ---
        self.titulo = QLabel("Saída Rápida de Estoque")
        self.titulo.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 10px;")
        
        self.input_codigo = QLineEdit()
        self.input_codigo.setPlaceholderText("Digite ou leia o código do produto aqui")
        
        self.btn_verificar = QPushButton("Verificar Produto")
        self.btn_verificar.setObjectName("btnNeutral")

        self.label_nome_produto = QLabel("Aguardando verificação...")
        
        self.input_quantidade = QLineEdit()
        self.input_quantidade.setPlaceholderText("0")
        self.input_quantidade.setValidator(QDoubleValidator(0, 99999, 0))
        
        self.input_motivo = QLineEdit()
        self.input_motivo.setPlaceholderText("Ex: Venda, Perda, Ajuste de inventário")
        
        self.btn_registrar = QPushButton("Registar Saída")
        self.btn_registrar.setObjectName("btnNegative")

        # --- 2. ORGANIZAÇÃO DO LAYOUT ---
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        
        layout_codigo = QHBoxLayout()
        layout_codigo.addWidget(self.input_codigo)
        layout_codigo.addWidget(self.btn_verificar)
        form_layout.addRow("Código do Produto:", layout_codigo)
        form_layout.addRow("Produto Encontrado:", self.label_nome_produto)
        form_layout.addRow("Quantidade a Retirar:", self.input_quantidade)
        form_layout.addRow("Motivo da Saída:", self.input_motivo)

        self.layout.addWidget(self.titulo)
        self.layout.addLayout(form_layout)
        self.layout.addWidget(self.btn_registrar, 0, Qt.AlignmentFlag.AlignRight)
        self.layout.addStretch(1)

        # --- 3. CONEXÕES DOS SINAIS ---
        self.btn_verificar.clicked.connect(self.verificar_produto)
        self.input_codigo.returnPressed.connect(self.verificar_produto)
        self.btn_registrar.clicked.connect(self.registrar_saida)
        self.input_motivo.returnPressed.connect(self.btn_registrar.click)

        # --- 4. ESTADO INICIAL ---
        self.resetar_formulario()

    def verificar_produto(self):
        codigo_produto = self.input_codigo.text().strip()
        if not codigo_produto: return
        global access_token
        url = f"{API_BASE_URL}/api/produtos/codigo/{codigo_produto}"
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(url, headers=headers)
            if response and response.status_code == 200:
                dados_produto = response.json()
                self.produto_encontrado_id = dados_produto['id']
                self.label_nome_produto.setText(dados_produto['nome'])
                self.label_nome_produto.setStyleSheet("font-size: 16px; font-weight: bold; color: #28a745;")
                self.input_quantidade.setEnabled(True)
                self.input_motivo.setEnabled(True)
                self.btn_registrar.setEnabled(True)
                self.input_quantidade.setFocus()
            else:
                self.label_nome_produto.setText("Produto não encontrado!")
                self.label_nome_produto.setStyleSheet("font-size: 16px; font-weight: bold; color: #dc3545;")
                self.produto_encontrado_id = None
                self.input_quantidade.clear()
                self.input_motivo.clear()
                self.input_quantidade.setEnabled(False)
                self.input_motivo.setEnabled(False)
                self.btn_registrar.setEnabled(False)
                self.input_codigo.selectAll()
                self.input_codigo.setFocus()
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Erro de Conexão", f"Não foi possível conectar ao servidor: {e}")

    def registrar_saida(self):
        quantidade = self.input_quantidade.text()
        motivo = self.input_motivo.text().strip()

        if not self.produto_encontrado_id or not quantidade or int(quantidade) <= 0:
            QMessageBox.warning(self, "Dados Inválidos", "Verifique o produto e insira uma quantidade válida.")
            return
        if not motivo:
            QMessageBox.warning(self, "Dados Inválidos", "O campo 'Motivo da Saída' é obrigatório.")
            return

        global access_token
        url = f"{API_BASE_URL}/api/estoque/saida"
        headers = {'Authorization': f'Bearer {access_token}'}
        dados = {
            "id_produto": self.produto_encontrado_id,
            "quantidade": int(quantidade),
            "motivo_saida": motivo
        }

        try:
            response = requests.post(url, headers=headers, json=dados)
            if response and response.status_code == 201:
                self.estoque_atualizado.emit()
                QMessageBox.information(self, "Sucesso", "Saída de estoque registada com sucesso!")
                self.resetar_formulario()
            else:
                erro = response.json().get('erro', 'Erro desconhecido.')
                QMessageBox.warning(self, "Erro", f"Não foi possível registar a saída: {erro}")
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Erro de Conexão", f"Não foi possível conectar ao servidor: {e}")

    def resetar_formulario(self):
        self.produto_encontrado_id = None
        self.input_codigo.clear()
        self.input_quantidade.clear()
        self.input_motivo.clear()
        self.label_nome_produto.setText("Aguardando verificação...")
        self.label_nome_produto.setStyleSheet("font-size: 16px; font-weight: bold; color: #555;")
        self.input_quantidade.setEnabled(False)
        self.input_motivo.setEnabled(False)
        self.btn_registrar.setEnabled(False)
        self.input_codigo.setFocus()


class UsuariosWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.titulo = QLabel("Gestão de Usuários")
        self.titulo.setStyleSheet("font-size: 24px; font-weight: bold;")

        layout_botoes = QHBoxLayout()
        self.btn_adicionar = QPushButton("➕ Adicionar Novo")
        self.btn_editar = QPushButton("✏️ Editar Selecionado")
        self.btn_desativar = QPushButton("🚫 Desativar/Reativar")
        self.btn_adicionar.setObjectName("btnPositive")
        self.btn_editar.setObjectName("btnNeutral")
        self.btn_desativar.setObjectName("btnNegative")
        layout_botoes.addWidget(self.btn_adicionar)
        layout_botoes.addWidget(self.btn_editar)
        layout_botoes.addWidget(self.btn_desativar)
        layout_botoes.addStretch(1)

        self.tabela_usuarios = QTableWidget()
        self.tabela_usuarios.setColumnCount(4)
        self.tabela_usuarios.setHorizontalHeaderLabels(["Nome", "Login", "Permissão", "Status"])
        self.tabela_usuarios.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabela_usuarios.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela_usuarios.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tabela_usuarios.setAlternatingRowColors(True)

        self.layout.addWidget(self.titulo)
        self.layout.addLayout(layout_botoes)
        self.layout.addWidget(self.tabela_usuarios)

        self.btn_adicionar.clicked.connect(self.abrir_formulario_adicionar)
        self.btn_editar.clicked.connect(self.abrir_formulario_editar)
        self.btn_desativar.clicked.connect(self.desativar_usuario_selecionado)

        self.carregar_usuarios()

    def carregar_usuarios(self):
        global access_token
        url = f"{API_BASE_URL}/api/usuarios"
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                usuarios = response.json()
                self.tabela_usuarios.setRowCount(len(usuarios))
                for linha, user in enumerate(usuarios):
                    item_nome = QTableWidgetItem(user['nome'])
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
        dialog = FormularioUsuarioDialog(self)
        if dialog.exec():
            self.carregar_usuarios()
    
    def abrir_formulario_editar(self):
        linha_selecionada = self.tabela_usuarios.currentRow()
        if linha_selecionada < 0:
            QMessageBox.warning(self, "Seleção", "Por favor, selecione um usuário para editar.")
            return
        
        item_id = self.tabela_usuarios.item(linha_selecionada, 0)
        usuario_id = item_id.data(Qt.UserRole)
        
        dialog = FormularioUsuarioDialog(self, usuario_id=usuario_id)
        if dialog.exec():
            self.carregar_usuarios()

    def desativar_usuario_selecionado(self):
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
            url = f"{API_BASE_URL}/api/usuarios/{usuario_id}"
            headers = {'Authorization': f'Bearer {access_token}'}
            try:
                response = requests.delete(url, headers=headers)
                
                if response.status_code == 200:
                    QMessageBox.information(self, "Sucesso", response.json()['mensagem'])
                    self.carregar_usuarios()
                else:
                    mensagem_erro = f"O servidor retornou um erro: {response.status_code}."
                    try:
                        detalhe_erro = response.json().get('erro')
                        if detalhe_erro:
                            mensagem_erro += f"\nDetalhe: {detalhe_erro}"
                    except requests.exceptions.JSONDecodeError:
                        mensagem_erro += f"\nResposta: {response.text}"
                    
                    QMessageBox.warning(self, "Erro", mensagem_erro)
            except requests.exceptions.RequestException as e:
                QMessageBox.critical(self, "Erro de Conexão", f"Não foi possível conectar ao servidor: {e}")

# ==============================================================================
# 5. CLASSE DA JANELA PRINCIPAL
# ==============================================================================

class JanelaPrincipal(QMainWindow):
    logoff_requested = Signal()

    def __init__(self):
        super().__init__()
        
        # --- BLOCO DE DEPURAÇÃO PARA APANHAR ERROS SILENCIOSOS ---
        try:
            self.setWindowTitle("Sistema de Gestão de Estoque")
            self.resize(1280, 720)
        
            self.dados_usuario = {}
        
            # --- ÁREA DE CONTEÚDO ---
            self.stacked_widget = QStackedWidget()
            self.stacked_widget.setObjectName("mainContentArea")
            
            self.tela_dashboard = DashboardWidget()
            self.tela_produtos = ProdutosWidget()
            self.tela_estoque = EstoqueWidget()
            self.tela_entrada_rapida = EntradaRapidaWidget()
            self.tela_saida_rapida = SaidaRapidaWidget()
            self.tela_relatorios = RelatoriosWidget()
            self.tela_fornecedores = FornecedoresWidget()
            self.tela_naturezas = NaturezasWidget()
            self.tela_usuarios = None
            self.tela_importacao = ImportacaoWidget()

            self.stacked_widget.addWidget(self.tela_dashboard)
            self.stacked_widget.addWidget(self.tela_produtos)
            self.stacked_widget.addWidget(self.tela_estoque)
            self.stacked_widget.addWidget(self.tela_entrada_rapida)
            self.stacked_widget.addWidget(self.tela_saida_rapida)
            self.stacked_widget.addWidget(self.tela_relatorios)
            self.stacked_widget.addWidget(self.tela_fornecedores)
            self.stacked_widget.addWidget(self.tela_naturezas)
            self.stacked_widget.addWidget(self.tela_importacao)
        
            # --- BARRA DE MENUS ---
            menu_bar = self.menuBar()
            
            menu_arquivo = menu_bar.addMenu("&Arquivo")
            acao_dashboard = QAction("Dashboard", self)
            acao_dashboard.setShortcut("Ctrl+D")
            acao_dashboard.triggered.connect(self.mostrar_tela_dashboard)
            menu_arquivo.addAction(acao_dashboard)
            menu_arquivo.addSeparator()
            acao_logoff = QAction("Fazer Logoff", self)
            acao_logoff.triggered.connect(self.logoff_requested.emit)
            menu_arquivo.addAction(acao_logoff)
            acao_sair = QAction("Sair", self)
            acao_sair.setShortcut(QKeySequence.Quit)
            acao_sair.triggered.connect(self.close)
            menu_arquivo.addAction(acao_sair)

            self.menu_cadastros = menu_bar.addMenu("&Cadastros")
            self.acao_produtos = QAction("Produtos...", self)
            self.acao_produtos.setShortcut("Ctrl+P")
            self.acao_produtos.triggered.connect(self.mostrar_tela_produtos)
            self.menu_cadastros.addAction(self.acao_produtos)
            self.acao_fornecedores = QAction("Fornecedores...", self)
            self.acao_fornecedores.setShortcut("Ctrl+F")
            self.acao_fornecedores.triggered.connect(self.mostrar_tela_fornecedores)
            self.menu_cadastros.addAction(self.acao_fornecedores)
            self.acao_naturezas = QAction("Naturezas...", self)
            self.acao_naturezas.triggered.connect(self.mostrar_tela_naturezas)
            self.menu_cadastros.addAction(self.acao_naturezas)
            self.menu_cadastros.addSeparator()
            acao_importar = QAction("Importar Produtos de CSV...", self)
            acao_importar.triggered.connect(self.mostrar_tela_importacao)
            self.menu_cadastros.addAction(acao_importar)
            self.menu_cadastros.addSeparator()
            self.acao_usuarios = QAction("Usuários...", self)
            self.acao_usuarios.triggered.connect(self.mostrar_tela_usuarios)

            menu_operacoes = menu_bar.addMenu("&Operações")
            acao_entrada = QAction("Entrada Rápida de Estoque...", self)
            acao_entrada.setShortcut("Ctrl+E")
            acao_entrada.triggered.connect(self.mostrar_tela_entrada_rapida)
            menu_operacoes.addAction(acao_entrada)
            acao_saida = QAction("Saída Rápida de Estoque...", self)
            acao_saida.setShortcut("Ctrl+S")
            acao_saida.triggered.connect(self.mostrar_tela_saida_rapida)
            menu_operacoes.addAction(acao_saida)
            menu_operacoes.addSeparator()
            acao_saldos = QAction("Consultar Saldos...", self)
            acao_saldos.triggered.connect(self.mostrar_tela_estoque)
            menu_operacoes.addAction(acao_saldos)
            acao_historico = QAction("Ver Histórico de Movimentações...", self)
            acao_historico.triggered.connect(lambda: (self.mostrar_tela_estoque(), self.tela_estoque.mostrar_historico()))
            menu_operacoes.addAction(acao_historico)

            menu_relatorios = menu_bar.addMenu("&Relatórios")
            acao_gerar_relatorio = QAction("Gerar Relatório...", self)
            acao_gerar_relatorio.triggered.connect(self.mostrar_tela_relatorios)
            menu_relatorios.addAction(acao_gerar_relatorio)

            menu_ajuda = menu_bar.addMenu("&Ajuda")
            acao_sobre = QAction("Sobre...", self)
            acao_sobre.triggered.connect(self.mostrar_dialogo_sobre)
            menu_ajuda.addAction(acao_sobre)

            # --- LAYOUT GERAL ---
            widget_central = QWidget()
            self.setCentralWidget(widget_central)
            layout_principal = QHBoxLayout(widget_central)

            # --- PAINEL LATERAL ---
            painel_lateral = QWidget()
            painel_lateral.setObjectName("painelLateral")
            painel_lateral.setFixedWidth(220)
            self.layout_painel_lateral = QVBoxLayout(painel_lateral)
            self.layout_painel_lateral.setAlignment(Qt.AlignTop)

            self.btn_dashboard = QPushButton("🏠 Dashboard")
            self.btn_produtos = QPushButton("📦 Produtos")
            self.btn_estoque = QPushButton("📊 Estoque")
            self.btn_entrada_rapida = QPushButton("➡️ Entrada Rápida")
            self.btn_saida_rapida = QPushButton("⬅️ Saída Rápida")
            self.btn_relatorios = QPushButton("📄 Relatórios")
            self.btn_fornecedores = QPushButton("🚚 Fornecedores")
            self.btn_naturezas = QPushButton("🌿 Naturezas")
            self.btn_usuarios = QPushButton("👥 Usuários")
            self.btn_logoff = QPushButton("🚪 Fazer Logoff")
            self.btn_logoff.setObjectName("btnLogoff")

            self.layout_painel_lateral.addWidget(self.btn_dashboard)
            self.layout_painel_lateral.addWidget(self.btn_produtos)
            self.layout_painel_lateral.addWidget(self.btn_estoque)
            self.layout_painel_lateral.addWidget(self.btn_entrada_rapida)
            self.layout_painel_lateral.addWidget(self.btn_saida_rapida)
            self.layout_painel_lateral.addWidget(self.btn_relatorios)
            self.layout_painel_lateral.addWidget(self.btn_fornecedores)
            self.layout_painel_lateral.addWidget(self.btn_naturezas)
            self.layout_painel_lateral.addStretch(1)
            self.layout_painel_lateral.addWidget(self.btn_logoff)
            
            layout_principal.addWidget(painel_lateral)
            layout_principal.addWidget(self.stacked_widget)

            # --- CONEXÕES ---
            self.btn_dashboard.clicked.connect(self.mostrar_tela_dashboard)
            self.btn_produtos.clicked.connect(self.mostrar_tela_produtos)
            self.btn_estoque.clicked.connect(self.mostrar_tela_estoque)
            self.btn_entrada_rapida.clicked.connect(self.mostrar_tela_entrada_rapida)
            self.btn_saida_rapida.clicked.connect(self.mostrar_tela_saida_rapida)
            self.btn_relatorios.clicked.connect(self.mostrar_tela_relatorios)
            self.btn_fornecedores.clicked.connect(self.mostrar_tela_fornecedores)
            self.btn_naturezas.clicked.connect(self.mostrar_tela_naturezas)
            self.btn_logoff.clicked.connect(self.logoff_requested.emit)
            
            self.tela_dashboard.ir_para_produtos.connect(self.mostrar_tela_produtos)
            self.tela_dashboard.ir_para_fornecedores.connect(self.mostrar_tela_fornecedores)
            self.tela_dashboard.ir_para_entrada_rapida.connect(self.mostrar_tela_entrada_rapida)
            self.tela_dashboard.ir_para_saida_rapida.connect(self.mostrar_tela_saida_rapida)
            self.tela_entrada_rapida.estoque_atualizado.connect(self.tela_estoque.saldos_view.carregar_dados_estoque)
            self.tela_saida_rapida.estoque_atualizado.connect(self.tela_estoque.saldos_view.carregar_dados_estoque)
            self.tela_importacao.produtos_importados_sucesso.connect(self.tela_produtos.carregar_produtos)

            self.statusBar().showMessage("Pronto.")

        except Exception as e:
            # Se qualquer erro acontecer durante a inicialização, ele será apanhado aqui
            error_log_path = os.path.join(os.path.expanduser("~"), "Desktop", "crash_log.txt")
            with open(error_log_path, "w", encoding="utf-8") as f:
                f.write(f"Ocorreu um erro crítico ao iniciar a janela principal:\n\n")
                f.write(f"{e}\n\n")
                f.write(traceback.format_exc())
            QMessageBox.critical(self, "Erro de Inicialização", f"Ocorreu um erro crítico. Verifique o ficheiro 'crash_log.txt' no seu Ambiente de Trabalho.")
            sys.exit(1)

    # O resto da sua classe JanelaPrincipal continua aqui...
    # (carregar_dados_usuario, mostrar_tela_*, etc.)
    def carregar_dados_usuario(self, dados_usuario):
        self.dados_usuario = dados_usuario
        
        nome_usuario = self.dados_usuario.get('nome', 'N/A')
        permissao_usuario = self.dados_usuario.get('permissao', 'N/A')
        self.statusBar().showMessage(f"Usuário: {nome_usuario} | Permissão: {permissao_usuario}")
    
        if self.dados_usuario.get('permissao') == 'Administrador':
            if self.tela_usuarios is None:
                self.tela_usuarios = UsuariosWidget()
                self.stacked_widget.addWidget(self.tela_usuarios)
            
            self.layout_painel_lateral.insertWidget(self.layout_painel_lateral.count() - 1, self.btn_usuarios)
            self.btn_usuarios.clicked.connect(self.mostrar_tela_usuarios)
            self.menu_cadastros.addAction(self.acao_usuarios)
        else:
            self.btn_usuarios.hide()
            
    def mostrar_tela_usuarios(self):
        if self.tela_usuarios:
            self.stacked_widget.setCurrentWidget(self.tela_usuarios)

    def mostrar_tela_dashboard(self):
        self.tela_dashboard.carregar_dados_dashboard()
        self.stacked_widget.setCurrentWidget(self.tela_dashboard)
        
    def mostrar_tela_entrada_rapida(self):
        self.tela_entrada_rapida.resetar_formulario()
        self.stacked_widget.setCurrentWidget(self.tela_entrada_rapida)
        
    def mostrar_tela_saida_rapida(self):
        self.tela_saida_rapida.resetar_formulario()
        self.stacked_widget.setCurrentWidget(self.tela_saida_rapida)

    def mostrar_tela_produtos(self):
        self.stacked_widget.setCurrentWidget(self.tela_produtos)
        
    def mostrar_tela_relatorios(self):
        self.stacked_widget.setCurrentWidget(self.tela_relatorios)

    def mostrar_tela_estoque(self):
        self.tela_estoque.mostrar_saldos() 
        self.stacked_widget.setCurrentWidget(self.tela_estoque)
        
    def mostrar_tela_fornecedores(self):     
        self.stacked_widget.setCurrentWidget(self.tela_fornecedores)
        
    def mostrar_tela_naturezas(self):
        self.stacked_widget.setCurrentWidget(self.tela_naturezas)
        
    def mostrar_dialogo_sobre(self):
        QMessageBox.about(self, 
            "Sobre o Sistema de Gestão de Estoque",
            """
            <b>Sistema de Gestão de Estoque v1.0</b>
            <p>Desenvolvido como parte de um projeto de demonstração.</p>
            <p><b>Tecnologias:</b> Python, PySide6, Flask, SQLAlchemy.</p>
            <p>Agradecimentos especiais pela colaboração e testes.</p>
            """
        )
    
    def mostrar_tela_importacao(self):
        """Mostra a tela de importação de produtos."""
        self.stacked_widget.setCurrentWidget(self.tela_importacao)

class InteractiveKPICard(QFrame):
    """Um cartão de KPI clicável que emite um sinal."""
    clicked = Signal()

    def __init__(self, titulo, valor_inicial="--", icone="●"):
        super().__init__()
        self.setObjectName("kpiCard")
        self.setCursor(Qt.PointingHandCursor)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(5)

        top_layout = QHBoxLayout()
        self.label_icone = QLabel(icone)
        self.label_icone.setObjectName("kpiIcon")
        self.label_titulo = QLabel(titulo)
        self.label_titulo.setObjectName("kpiTitle")
        top_layout.addWidget(self.label_icone)
        top_layout.addWidget(self.label_titulo)
        top_layout.addStretch(1)

        self.label_valor = QLabel(valor_inicial)
        self.label_valor.setObjectName("kpiValue")

        self.layout.addLayout(top_layout)
        self.layout.addWidget(self.label_valor)

    def set_valor(self, novo_valor):
        self.label_valor.setText(str(novo_valor))

    def mouseReleaseEvent(self, event):
        """Emite o sinal 'clicked' quando o cartão é clicado."""
        self.clicked.emit()
        super().mouseReleaseEvent(event)

class DashboardWidget(QWidget):
    """Tela principal do dashboard com um design profissional e minimalista."""
    # Sinais para navegar para outras telas
    ir_para_produtos = Signal()
    ir_para_fornecedores = Signal()
    ir_para_entrada_rapida = Signal()
    ir_para_saida_rapida = Signal()

    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.layout.setContentsMargins(30, 20, 30, 20)
        self.layout.setSpacing(20)

        # --- CABEÇALHO: Logo e Mensagem de Boas-vindas ---
        header_layout = QHBoxLayout()
        self.label_logo = QLabel()
        logo_pixmap = QPixmap(resource_path("logo.png"))
        logo_redimensionada = logo_pixmap.scaled(150, 90, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.label_logo.setPixmap(logo_redimensionada)
        
        self.label_boas_vindas = QLabel("Bem-vindo de volta!")
        self.label_boas_vindas.setObjectName("welcomeMessage")

        header_layout.addWidget(self.label_logo)
        header_layout.addWidget(self.label_boas_vindas)
        header_layout.addStretch(1)

        # --- KPIs INTERATIVOS ---
        kpi_layout = QHBoxLayout()
        self.card_produtos = InteractiveKPICard("Produtos", icone="📦")
        self.card_fornecedores = InteractiveKPICard("Fornecedores", icone="🚚")
        self.card_valor_estoque = InteractiveKPICard("Valor do Estoque (R$)", icone="💰")
        kpi_layout.addWidget(self.card_produtos)
        kpi_layout.addWidget(self.card_fornecedores)
        kpi_layout.addWidget(self.card_valor_estoque)

        # --- BOTÕES DE AÇÃO PRINCIPAIS ---
        action_layout = QHBoxLayout()
        self.btn_atalho_entrada = QPushButton("➡️\n\nNova Entrada")
        self.btn_atalho_entrada.setObjectName("btnDashboardAction")
        self.btn_atalho_saida = QPushButton("⬅️\n\nNova Saída")
        self.btn_atalho_saida.setObjectName("btnDashboardAction")
        action_layout.addWidget(self.btn_atalho_entrada)
        action_layout.addWidget(self.btn_atalho_saida)

        # Adicionando tudo ao layout principal
        self.layout.addLayout(header_layout)
        self.layout.addWidget(QLabel("Resumo do Sistema")) # Um título simples
        self.layout.addLayout(kpi_layout)
        self.layout.addWidget(QLabel("Operações Comuns"))
        self.layout.addLayout(action_layout)
        self.layout.addStretch(1)

        # --- Conexões ---
        self.card_produtos.clicked.connect(self.ir_para_produtos.emit)
        self.card_fornecedores.clicked.connect(self.ir_para_fornecedores.emit)
        self.btn_atalho_entrada.clicked.connect(self.ir_para_entrada_rapida.emit)
        self.btn_atalho_saida.clicked.connect(self.ir_para_saida_rapida.emit)

    def carregar_dados_dashboard(self):
        self.carregar_kpis()

    def carregar_kpis(self):
        global access_token
        url = f"{API_BASE_URL}/api/dashboard/kpis"
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(url, headers=headers, timeout=5)
            if response and response.status_code == 200:
                dados = response.json()
                self.card_produtos.set_valor(dados.get('total_produtos', 0))
                self.card_fornecedores.set_valor(dados.get('total_fornecedores', 0))
                valor_formatado = f"R$ {dados.get('valor_total_estoque', 0):.2f}".replace('.', ',')
                self.card_valor_estoque.set_valor(valor_formatado)
        except requests.exceptions.RequestException:
            print("Erro ao carregar KPIs do dashboard.")

        
# ==============================================================================
# 6. CLASSE DA JANELA DE LOGIN
# ==============================================================================

class AppManager:
    """Classe para gerir o ciclo de vida das janelas da aplicação."""
    def __init__(self):
        self.login_window = None
        self.main_window = None

    def start(self):
        """Inicia a aplicação mostrando a janela de login."""
        self.show_login_window()

    def show_login_window(self):
        """Cria e exibe a janela de login."""
        self.login_window = JanelaLogin()
        self.login_window.login_successful.connect(self.show_main_window)
        self.login_window.show()

    def show_main_window(self, user_data):
        """Cria e exibe a janela principal após um login bem-sucedido."""
        self.main_window = JanelaPrincipal()
        self.main_window.carregar_dados_usuario(user_data)
        self.main_window.show()
        self.main_window.mostrar_tela_dashboard()
        self.main_window.logoff_requested.connect(self.handle_logoff)
        self.login_window.close()

    def handle_logoff(self):
        """Fecha a janela principal e volta para a tela de login."""
        if self.main_window:
            self.main_window.close()
        self.show_login_window()


class JanelaLogin(QWidget):
    login_successful = Signal(dict) # Sinal que carrega os dados do utilizador

    def __init__(self):
        super().__init__()
        # ... (o resto do seu __init__ continua igual)
        self.setWindowTitle("Meu Sistema de Gestão - Login")
        self.resize(300, 350)
        self.janela_principal = None

        layout = QVBoxLayout()
        logo_pixmap = QPixmap(resource_path("logo.png"))
        logo_redimensionada = logo_pixmap.scaled(250, 150, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
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
        self.input_senha.returnPressed.connect(self.botao_login.click)

    def fazer_login(self):
        global access_token
        login = self.input_login.text()
        senha = self.input_senha.text()

        if not login or not senha:
            QMessageBox.warning(self, "Erro de Entrada", "Os campos de login e senha não podem estar vazios.")
            return

        url = f"{API_BASE_URL}/api/login"
        dados = {"login": login, "senha": senha}

        try:
            response = requests.post(url, json=dados)
            if response.status_code == 200:
                access_token = response.json()['access_token']
                print("Login bem-sucedido! Token guardado.")
                
                headers = {'Authorization': f'Bearer {access_token}'}
                url_me = f"{API_BASE_URL}/api/usuario/me"
                response_me = requests.get(url_me, headers=headers)
                
                if response_me.status_code == 200:
                    dados_usuario_logado = response_me.json()
                else:
                    dados_usuario_logado = {'nome': 'Desconhecido', 'permissao': 'Usuario'}
                
                # --- A MUDANÇA ESTÁ AQUI ---
                # Em vez de criar a janela, apenas emitimos o sinal de sucesso
                self.login_successful.emit(dados_usuario_logado)
                self.close()
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

    try:
        with open(resource_path("style.qss"), "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        print("AVISO: Arquivo de estilo (style.qss) não encontrado.")
    
    # Cria o gestor e inicia a aplicação
    manager = AppManager()
    manager.start()
    
    sys.exit(app.exec())