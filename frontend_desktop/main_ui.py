# ==============================================================================
# 1. IMPORTS
# ==============================================================================
import sys
import os
import requests
import traceback
import json
import random
import webbrowser
import winsound
import threading

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout,
    QMessageBox, QMainWindow, QHBoxLayout, QStackedWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QSizePolicy, QDialog, QFormLayout,
    QDialogButtonBox, QListWidget, QListWidgetItem, QAbstractItemView,
    QComboBox, QFileDialog, QFrame, QDateEdit, QCalendarWidget, QMenu,
    QTextEdit, QTabWidget, QProgressBar, QSpinBox, QCheckBox, QGroupBox,
    QGridLayout, QScrollArea, QLineEdit, QInputDialog  , QRadioButton, QButtonGroup
)
from PySide6.QtGui import (
    QPixmap, QAction, QDoubleValidator, QKeySequence, QIcon
)
from PySide6.QtCore import (
    Qt, QTimer, Signal, QDate, QEvent, QObject, QThread, QUrl, QSettings # Adicione QSettings
)
from PySide6.QtMultimedia import QSoundEffect
from packaging.version import parse as parse_version

from config import SERVER_IP

# ==============================================================================
# 2. FUNÇÕES AUXILIARES E VARIÁVEIS GLOBAIS
# ==============================================================================
access_token = None
API_BASE_URL = f"http://{SERVER_IP}:5000"
APP_VERSION = "2.5"
# --- ADICIONE ESTAS LINHAS DE DEPURACAO AQUI ---
print("--- INICIANDO APLICAÇÃO ---")
print(f"--- IP DO SERVIDOR CARREGADO DE CONFIG.PY: '{SERVER_IP}' ---")
print("--------------------------")
# --- FIM DAS LINHAS DE DEPURACAO ---
class SignalHandler(QObject):
    """Um gestor central para sinais globais da aplicação."""
    fornecedores_atualizados = Signal()
    naturezas_atualizadas = Signal()

signal_handler = SignalHandler()

def resource_path(relative_path):
    """ Retorna o caminho absoluto para o recurso, funcionando tanto no desenvolvimento quanto no .exe do PyInstaller. """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def show_connection_error_message(parent):
    """Exibe uma mensagem de erro de conexão padronizada e amigável."""
    QMessageBox.critical(parent,
        "Erro de Conexão",
        "Impossível conectar ao servidor.\n\n"
        "Por favor, verifique os seguintes pontos:\n"
        "1. O computador servidor está ligado e a aplicação está a ser executada.\n"
        "2. O seu computador tem uma ligação à rede (internet ou local).\n"
        "3. O endereço IP no ficheiro 'config.py' está correto."
    )
    
CURRENT_THEME = 'light' # Variável global para saber o tema atual

def load_stylesheet(theme_name):
    """Carrega e retorna o conteúdo do ficheiro QSS para um tema específico."""
    global CURRENT_THEME
    filename = "style.qss" if theme_name == "light" else "style_dark.qss"
    try:
        with open(resource_path(filename), "r", encoding="utf-8") as f:
            CURRENT_THEME = theme_name
            return f.read()
    except FileNotFoundError:
        print(f"AVISO: Arquivo de estilo ({filename}) não encontrado.")
        return ""    

def check_for_updates():
    """Contacta a API para verificar se existe uma nova versão da aplicação."""
    print("A verificar atualizações...")
    try:
        global access_token
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(f"{API_BASE_URL}/api/versao", headers=headers, timeout=5)

        if response.status_code == 200:
            dados_versao = response.json()
            versao_servidor = dados_versao.get("versao")
            url_download = dados_versao.get("url_download")

            if versao_servidor and parse_version(versao_servidor) > parse_version(APP_VERSION):
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Information)
                msg_box.setWindowTitle("Nova Versão Disponível!")
                msg_box.setText(f"Uma nova versão ({versao_servidor}) do sistema está disponível.")
                msg_box.setInformativeText("Deseja ir para a página de download agora?")
                msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                msg_box.setDefaultButton(QMessageBox.StandardButton.Yes)
                
                ret = msg_box.exec()
                if ret == QMessageBox.StandardButton.Yes:
                    webbrowser.open(url_download)
            else:
                print("A sua aplicação está atualizada.")
        else:
            print(f"Não foi possível verificar a versão. Erro da API: {response.status_code}")
            QMessageBox.warning(None, "Verificação de Versão", f"Não foi possível contactar o servidor de atualizações (Erro: {response.status_code}).")

    except requests.exceptions.RequestException:
        show_connection_error_message(None)
    except Exception as e:
        print(f"Ocorreu um erro ao verificar atualizações: {e}")
        QMessageBox.critical(None, "Erro na Verificação de Versão", f"Ocorreu um erro inesperado ao tentar verificar por novas versões:\n\n{e}")

# ==============================================================================
# 3. JANELAS DE DIÁLOGO E WORKERS
# ==============================================================================

class ApiWorker(QObject):
    """
    Um 'trabalhador' genérico que executa uma requisição de API em uma QThread separada
    para não congelar a interface.
    """
    # Sinal que será emitido com o resultado: (status_code, dados_json)
    finished = Signal(int, object)

    def __init__(self, method, endpoint, params=None, json_data=None, files=None, form_data=None):
        super().__init__()
        self.method = method
        self.endpoint = endpoint
        self.params = params
        self.json_data = json_data
        self.files = files
        self.form_data = form_data

    def run(self):
        # --- PRINT DE DEPURACAO 1 ---
        print(f"--- FRONTEND DEBUG: ApiWorker.run iniciado para o endpoint: {self.endpoint} ---")

        global access_token, API_BASE_URL
        headers = {'Authorization': f'Bearer {access_token}'}
        url = f"{API_BASE_URL}{self.endpoint}"

        # --- PRINT DE DEPURACAO 2 ---
        print(f"--- FRONTEND DEBUG: A fazer chamada {self.method.upper()} para a URL: {url} ---")

        try:
            response = requests.request(
                self.method, url, headers=headers, params=self.params, 
                files=self.files,  data=self.form_data, timeout=15
            )
            # --- PRINT DE DEPURACAO 3 ---
            print(f"--- FRONTEND DEBUG: Resposta recebida com status: {response.status_code} ---")

            data = response.json() if response.content else {}
            self.finished.emit(response.status_code, data)

        except requests.exceptions.RequestException as e:
            # --- PRINT DE DEPURACAO 4 ---
            print(f"--- FRONTEND DEBUG: EXCEÇÃO! Erro de conexão: {e} ---")
            self.finished.emit(-1, {"erro": f"Erro de conexão: {e}"})
        except Exception as e:
            # --- PRINT DE DEPURACAO 5 ---
            print(f"--- FRONTEND DEBUG: EXCEÇÃO! Erro inesperado: {e} ---")
            self.finished.emit(-2, {"erro": f"Erro inesperado: {e}"})

class FormDataLoader(QObject):
    finished = Signal(dict)
    def __init__(self, produto_id):
        super().__init__()
        self.produto_id = produto_id
    def run(self):
        results = {'status': 'success'}
        try:
            global access_token
            headers = {'Authorization': f'Bearer {access_token}'}
            timeout = 10
            params = {}
            if self.produto_id:
                params['produto_id'] = self.produto_id
            response = requests.get(f"{API_BASE_URL}/api/formularios/produto_data", headers=headers, params=params, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            results['fornecedores'] = data.get('fornecedores', [])
            results['naturezas'] = data.get('naturezas', [])
            if data.get('produto'):
                results['produto'] = data['produto']
        except requests.exceptions.RequestException:
            results['status'] = 'error'
            results['message'] = "connection_error"
        except Exception as e:
            results['status'] = 'error'
            results['message'] = f"Ocorreu um erro inesperado: {e}"
        self.finished.emit(results)

class FormularioProdutoDialog(QDialog):
    produto_atualizado = Signal(int, dict)
    def __init__(self, parent=None, produto_id=None, row=None):
        super().__init__(parent)
        self.produto_id = produto_id
        self.row = row
        self.setWindowTitle("Adicionar Novo Produto" if self.produto_id is None else "Editar Produto")
        self.setMinimumSize(450, 600)
        self.layout = QFormLayout(self)
        self.dados_produto_carregados = None
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
        self.input_codigo.installEventFilter(self)
        self.input_codigo.textChanged.connect(self.iniciar_verificacao_timer)
        self.input_codigoC.returnPressed.connect(self.botoes.button(QDialogButtonBox.StandardButton.Save).click)
        self.btn_add_fornecedor.clicked.connect(self.adicionar_rapido_fornecedor)
        self.btn_add_natureza.clicked.connect(self.adicionar_rapido_natureza)
        self.botoes.accepted.connect(self.accept)
        self.botoes.rejected.connect(self.reject)
        self.iniciar_carregamento_assincrono()
    def iniciar_carregamento_assincrono(self):
        self.definir_estado_carregamento(True)
        self.thread = QThread()
        self.worker = FormDataLoader(self.produto_id)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.preencher_dados_formulario)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()
    def definir_estado_carregamento(self, a_carregar):
        for widget in self.findChildren(QWidget):
            if isinstance(widget, (QLineEdit, QListWidget, QPushButton)):
                widget.setEnabled(not a_carregar)
        if a_carregar:
            self.loading_label = QLabel("A carregar dados do servidor...")
            self.layout.addRow(self.loading_label)
        else:
            if hasattr(self, 'loading_label'):
                self.loading_label.hide()
                self.loading_label.deleteLater()
    def preencher_dados_formulario(self, resultados):
        self.definir_estado_carregamento(False)
        if resultados['status'] == 'error':
            if resultados['message'] == 'connection_error':
                show_connection_error_message(self)
            else:
                QMessageBox.critical(self, "Erro de Carregamento", resultados['message'])
            self.reject()
            return
        for forn in resultados.get('fornecedores', []):
            item = QListWidgetItem(forn['nome'])
            item.setData(Qt.UserRole, forn['id'])
            self.lista_fornecedores.addItem(item)
        for nat in resultados.get('naturezas', []):
            item = QListWidgetItem(nat['nome'])
            item.setData(Qt.UserRole, nat['id'])
            self.lista_naturezas.addItem(item)
        if 'produto' in resultados:
            self.dados_produto_carregados = resultados['produto']
            dados = self.dados_produto_carregados
            self.input_codigo.setText(dados.get('codigo', ''))
            self.input_nome.setText(dados.get('nome', ''))
            self.input_descricao.setText(dados.get('descricao', ''))
            self.input_preco.setText(str(dados.get('preco', '0.00')))
            self.input_codigoB.setText(dados.get('codigoB', ''))
            self.input_codigoC.setText(dados.get('codigoC', ''))
            self.selecionar_itens_nas_listas(dados)
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
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(f"{API_BASE_URL}/api/produtos/codigo/{codigo}", headers=headers)
            if response and response.status_code == 404:
                self.label_status_codigo.setText("✅ Disponível")
                self.label_status_codigo.setStyleSheet("color: #28a745;")
            elif response and response.status_code == 200:
                self.label_status_codigo.setText("❌ Já existe!")
                self.label_status_codigo.setStyleSheet("color: #dc3545;")
            else:
                self.label_status_codigo.setText("")
        except requests.exceptions.RequestException:
            self.label_status_codigo.setText("⚠️ Erro")
            self.label_status_codigo.setStyleSheet("color: #ffc107;")
    def adicionar_rapido_fornecedor(self):
        dialog = QuickAddDialog(self, "Adicionar Novo Fornecedor", "/api/fornecedores")
        dialog.item_adicionado.connect(self.carregar_listas_de_apoio_refreshed)
        dialog.exec()
    def adicionar_rapido_natureza(self):
        dialog = QuickAddDialog(self, "Adicionar Nova Natureza", "/api/naturezas")
        dialog.item_adicionado.connect(self.carregar_listas_de_apoio_refreshed)
        dialog.exec()
    def carregar_listas_de_apoio_refreshed(self):
        self.carregar_listas_de_apoio()
        if self.dados_produto_carregados:
            self.selecionar_itens_nas_listas(self.dados_produto_carregados)
    def carregar_listas_de_apoio(self):
        self.lista_fornecedores.clear()
        self.lista_naturezas.clear()
        global access_token
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response_forn = requests.get(f"{API_BASE_URL}/api/fornecedores", headers=headers)
            if response_forn and response_forn.status_code == 200:
                for forn in response_forn.json():
                    item = QListWidgetItem(forn['nome'])
                    item.setData(Qt.UserRole, forn['id'])
                    self.lista_fornecedores.addItem(item)
            response_nat = requests.get(f"{API_BASE_URL}/api/naturezas", headers=headers)
            if response_nat and response_nat.status_code == 200:
                for nat in response_nat.json():
                    item = QListWidgetItem(nat['nome'])
                    item.setData(Qt.UserRole, nat['id'])
                    self.lista_naturezas.addItem(item)
        except requests.exceptions.RequestException:
            show_connection_error_message(self)
    def selecionar_itens_nas_listas(self, dados_produto):
        ids_fornecedores_associados = {f['id'] for f in dados_produto.get('fornecedores', [])}
        for i in range(self.lista_fornecedores.count()):
            item = self.lista_fornecedores.item(i)
            if item.data(Qt.UserRole) in ids_fornecedores_associados:
                item.setSelected(True)
        ids_naturezas_associadas = {n['id'] for n in dados_produto.get('naturezas', [])}
        for i in range(self.lista_naturezas.count()):
            item = self.lista_naturezas.item(i)
            if item.data(Qt.UserRole) in ids_naturezas_associadas:
                item.setSelected(True)
    def accept(self):
        nome = self.input_nome.text().strip()
        codigo = self.input_codigo.text().strip()
        if not nome or not codigo:
            QMessageBox.warning(self, "Campos Obrigatórios", "Por favor, preencha os campos: Código e Nome.")
            return
        global access_token
        headers = {'Authorization': f'Bearer {access_token}'}
        preco_str = self.input_preco.text().strip().replace(',', '.')
        dados_produto = {
            "codigo": codigo, "nome": nome, "preco": preco_str if preco_str else "0.00",
            "descricao": self.input_descricao.text(),
            "codigoB": self.input_codigoB.text(), "codigoC": self.input_codigoC.text()
        }
        ids_fornecedores_selecionados = [self.lista_fornecedores.item(i).data(Qt.UserRole) for i in range(self.lista_fornecedores.count()) if self.lista_fornecedores.item(i).isSelected()]
        ids_naturezas_selecionadas = [self.lista_naturezas.item(i).data(Qt.UserRole) for i in range(self.lista_naturezas.count()) if self.lista_naturezas.item(i).isSelected()]
        try:
            if self.produto_id is None:
                response_produto = requests.post(f"{API_BASE_URL}/api/produtos", headers=headers, json=dados_produto)
                if not response_produto or response_produto.status_code != 201:
                    raise Exception(response_produto.json().get('erro', 'Erro ao criar produto'))
                produto_salvo_id = response_produto.json().get('id_produto_criado')
                dados_produto['fornecedores_ids'] = ids_fornecedores_selecionados
                dados_produto['naturezas_ids'] = ids_naturezas_selecionadas
                response_update = requests.put(f"{API_BASE_URL}/api/produtos/{produto_salvo_id}", headers=headers, json=dados_produto)
                if not response_update or response_update.status_code != 200:
                    raise Exception(response_update.json().get('erro', 'Produto criado, mas falha ao salvar associações'))
                super().accept()
            else:
                dados_produto['fornecedores_ids'] = ids_fornecedores_selecionados
                dados_produto['naturezas_ids'] = ids_naturezas_selecionadas
                response = requests.put(f"{API_BASE_URL}/api/produtos/{self.produto_id}", headers=headers, json=dados_produto)
                if not response or response.status_code != 200:
                    raise Exception(response.json().get('erro', 'Erro ao atualizar produto'))
                dados_atualizados = response.json()
                self.produto_atualizado.emit(self.row, dados_atualizados)
                QMessageBox.information(self, "Sucesso", "Produto atualizado com sucesso!")
                super().accept()
        except requests.exceptions.RequestException:
            show_connection_error_message(self)
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
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(f"{API_BASE_URL}/api/fornecedores/{self.fornecedor_id}", headers=headers)
            if response.status_code == 200:
                self.input_nome.setText(response.json().get('nome'))
            else:
                QMessageBox.warning(self, "Erro", "Não foi possível carregar dados do fornecedor.")
        except requests.exceptions.RequestException:
            show_connection_error_message(self)
    def accept(self):
        global access_token
        headers = {'Authorization': f'Bearer {access_token}'}
        dados = {"nome": self.input_nome.text()}
        try:
            if self.fornecedor_id is None:
                response = requests.post(f"{API_BASE_URL}/api/fornecedores", headers=headers, json=dados)
                if response.status_code == 201:
                    QMessageBox.information(self, "Sucesso", "Fornecedor adicionado com sucesso!")
                    super().accept()
                else: raise Exception(response.json().get('erro', 'Erro desconhecido'))
            else:
                response = requests.put(f"{API_BASE_URL}/api/fornecedores/{self.fornecedor_id}", headers=headers, json=dados)
                if response.status_code == 200:
                    QMessageBox.information(self, "Sucesso", "Fornecedor atualizado com sucesso!")
                    super().accept()
                else: raise Exception(response.json().get('erro', 'Erro desconhecido'))
        except requests.exceptions.RequestException:
            show_connection_error_message(self)
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
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(f"{API_BASE_URL}/api/naturezas/{self.natureza_id}", headers=headers)
            if response.status_code == 200:
                self.input_nome.setText(response.json().get('nome'))
            else:
                QMessageBox.warning(self, "Erro", "Não foi possível carregar dados da natureza.")
        except requests.exceptions.RequestException:
            show_connection_error_message(self)
    def accept(self):
        global access_token
        headers = {'Authorization': f'Bearer {access_token}'}
        dados = {"nome": self.input_nome.text()}
        try:
            if self.natureza_id is None:
                response = requests.post(f"{API_BASE_URL}/api/naturezas", headers=headers, json=dados)
                if response.status_code == 201:
                    QMessageBox.information(self, "Sucesso", "Natureza adicionada com sucesso!")
                    super().accept()
                else: raise Exception(response.json().get('erro', 'Erro desconhecido'))
            else:
                response = requests.put(f"{API_BASE_URL}/api/naturezas/{self.natureza_id}", headers=headers, json=dados)
                if response.status_code == 200:
                    QMessageBox.information(self, "Sucesso", "Natureza atualizada com sucesso!")
                    super().accept()
                else: raise Exception(response.json().get('erro', 'Erro desconhecido'))
        except requests.exceptions.RequestException:
            show_connection_error_message(self)
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
        headers = {'Authorization': f'Bearer {access_token}'}
        dados = {"nome": nome}
        try:
            response = requests.post(f"{API_BASE_URL}{self.endpoint}", headers=headers, json=dados)
            if response.status_code == 201:
                QMessageBox.information(self, "Sucesso", "Item adicionado com sucesso!")
                self.item_adicionado.emit()
                if self.endpoint == "/api/fornecedores":
                    signal_handler.fornecedores_atualizados.emit()
                elif self.endpoint == "/api/naturezas":
                    signal_handler.naturezas_atualizadas.emit()
                super().accept()
            else:
                raise Exception(response.json().get('erro', 'Erro desconhecido'))
        except requests.exceptions.RequestException:
            show_connection_error_message(self)
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
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(f"{API_BASE_URL}/api/usuarios/{self.usuario_id}", headers=headers)
            if response.status_code == 200:
                dados = response.json()
                self.input_nome.setText(dados.get('nome', ''))
                self.input_login.setText(dados.get('login', ''))
                self.input_permissao.setCurrentText(dados.get('permissao', 'Usuario'))
            else:
                QMessageBox.warning(self, "Erro", "Não foi possível carregar os dados do usuário.")
                self.reject()
        except requests.exceptions.RequestException:
            show_connection_error_message(self)
            self.reject()
    def accept(self):
        global access_token
        if not self.input_nome.text().strip() or not self.input_login.text().strip():
            QMessageBox.warning(self, "Campos Obrigatórios", "Os campos Nome e Login são obrigatórios.")
            return
        dados = {"nome": self.input_nome.text(), "login": self.input_login.text(), "permissao": self.input_permissao.currentText()}
        if self.input_senha.text():
            dados['senha'] = self.input_senha.text()
        elif self.usuario_id is None:
            QMessageBox.warning(self, "Campo Obrigatório", "A senha é obrigatória para novos usuários.")
            return
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            if self.usuario_id is None:
                response = requests.post(f"{API_BASE_URL}/api/usuarios", headers=headers, json=dados)
                mensagem_sucesso = "Usuário adicionado com sucesso!"
                status_esperado = 201
            else:
                response = requests.put(f"{API_BASE_URL}/api/usuarios/{self.usuario_id}", headers=headers, json=dados)
                mensagem_sucesso = "Usuário atualizado com sucesso!"
                status_esperado = 200
            if response.status_code == status_esperado:
                QMessageBox.information(self, "Sucesso", mensagem_sucesso)
                super().accept()
            else:
                raise Exception(response.json().get('erro', 'Erro desconhecido'))
        except requests.exceptions.RequestException:
            show_connection_error_message(self)
        except Exception as e:
            QMessageBox.warning(self, "Erro", f"Não foi possível salvar o usuário: {e}")

class MudarSenhaDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Alterar Minha Senha")
        self.setMinimumWidth(350)
        self.layout = QFormLayout(self)
        self.layout.setSpacing(15)
        self.input_senha_atual = QLineEdit()
        self.input_senha_atual.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_nova_senha = QLineEdit()
        self.input_nova_senha.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_confirmacao = QLineEdit()
        self.input_confirmacao.setEchoMode(QLineEdit.EchoMode.Password)
        self.layout.addRow("Senha Atual:", self.input_senha_atual)
        self.layout.addRow("Nova Senha:", self.input_nova_senha)
        self.layout.addRow("Confirmar Nova Senha:", self.input_confirmacao)
        self.botoes = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.layout.addWidget(self.botoes)
        self.botoes.accepted.connect(self.accept)
        self.botoes.rejected.connect(self.reject)
        self.input_confirmacao.returnPressed.connect(self.accept)
    def accept(self):
        senha_atual = self.input_senha_atual.text()
        nova_senha = self.input_nova_senha.text()
        confirmacao = self.input_confirmacao.text()
        if not senha_atual or not nova_senha or not confirmacao:
            QMessageBox.warning(self, "Campos Vazios", "Todos os campos são obrigatórios.")
            return
        if nova_senha != confirmacao:
            QMessageBox.warning(self, "Erro", "A nova senha e a confirmação não correspondem.")
            return
        global access_token
        headers = {'Authorization': f'Bearer {access_token}'}
        dados = {"senha_atual": senha_atual, "nova_senha": nova_senha, "confirmacao_nova_senha": confirmacao}
        try:
            response = requests.post(f"{API_BASE_URL}/api/usuario/mudar-senha", headers=headers, json=dados)
            if response and response.status_code == 200:
                QMessageBox.information(self, "Sucesso", "Senha alterada com sucesso!")
                super().accept()
            else:
                erro = response.json().get('erro', 'Ocorreu um erro desconhecido.')
                QMessageBox.warning(self, "Falha na Alteração", erro)
        except requests.exceptions.RequestException:
            show_connection_error_message(self)

class QuantidadeDialog(QDialog):
    estoque_modificado = Signal(str)
    def __init__(self, parent, produto_id, produto_nome, produto_codigo, operacao):
        super().__init__(parent)
        self.produto_id = produto_id
        self.produto_codigo = produto_codigo
        self.operacao = operacao
        acao_texto = "Adicionar" if operacao == "Entrada" else "Remover"
        self.setWindowTitle(f"{acao_texto} Estoque")
        self.setMinimumWidth(350)
        self.layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        self.label_produto = QLabel(f"<b>Produto:</b> {produto_nome}")
        self.input_quantidade = QLineEdit()
        self.input_quantidade.setValidator(QDoubleValidator(0, 99999, 0))
        self.input_motivo = QLineEdit()
        form_layout.addRow(self.label_produto)
        form_layout.addRow("Quantidade:", self.input_quantidade)
        if self.operacao == "Saida":
            form_layout.addRow("Motivo da Saída:", self.input_motivo)
        self.botoes = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.layout.addLayout(form_layout)
        self.layout.addWidget(self.botoes)
        self.botoes.accepted.connect(self.accept)
        self.botoes.rejected.connect(self.reject)
        self.input_quantidade.setFocus()
    def accept(self):
        quantidade_str = self.input_quantidade.text()
        if not quantidade_str or int(quantidade_str) <= 0:
            QMessageBox.warning(self, "Erro", "Por favor, insira uma quantidade válida maior que zero.")
            return
        dados = { "id_produto": self.produto_id, "quantidade": int(quantidade_str) }
        endpoint = "/api/estoque/entrada"
        if self.operacao == "Saida":
            motivo = self.input_motivo.text().strip()
            if not motivo:
                QMessageBox.warning(self, "Erro", "O motivo é obrigatório para saídas de estoque.")
                return
            dados["motivo_saida"] = motivo
            endpoint = "/api/estoque/saida"
        global access_token
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.post(f"{API_BASE_URL}{endpoint}", headers=headers, json=dados)
            if response and response.status_code == 201:
                self.estoque_modificado.emit(self.produto_codigo)
                super().accept()
            else:
                QMessageBox.warning(self, "Erro na API", response.json().get('erro', 'Ocorreu um erro.'))
        except requests.exceptions.RequestException:
            show_connection_error_message(self)

# ==============================================================================
# 4. WIDGETS DE CONTEÚDO (AS "TELAS" PRINCIPAIS)
# ==============================================================================

class ImportacaoWidget(QWidget):
    produtos_importados_sucesso = Signal()
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.caminho_ficheiro = None
        titulo = QLabel("Importação de Produtos em Massa")
        titulo.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 10px;")
        instrucoes = QLabel(
            "<b>Instruções:</b><br>"
            "1. Prepare uma planilha com as seguintes colunas obrigatórias: <b>codigo, nome</b>.<br>"
            "2. Colunas opcionais: <b>preco, quantidade</b>, <b>descricao</b>, <b>fornecedores_nomes</b>, <b>naturezas_nomes</b>.<br>"
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
        self.btn_importar.setObjectName("btnPositive")
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
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            with open(self.caminho_ficheiro, 'rb') as f:
                files = {'file': (os.path.basename(self.caminho_ficheiro), f, 'text/csv')}
                response = requests.post(f"{API_BASE_URL}/api/produtos/importar", headers=headers, files=files)
            if response.status_code == 200:
                dados = response.json()
                resultado_texto = f"{dados.get('mensagem', '')}\n"
                resultado_texto += f"Produtos importados com sucesso: {dados.get('produtos_importados', 0)}\n\n"
                erros = dados.get('erros', [])
                if erros:
                    resultado_texto += "Erros encontrados:\n"
                    resultado_texto += "\n".join(erros)
                self.text_resultados.setText(resultado_texto)
                if dados.get('produtos_importados', 0) > 0:
                    self.produtos_importados_sucesso.emit()
            else:
                self.text_resultados.setText(f"Erro na API: {response.text}")
        except requests.exceptions.RequestException:
            show_connection_error_message(self)
        except Exception as e:
            self.text_resultados.setText(f"Ocorreu um erro crítico: {e}")
        self.btn_importar.setEnabled(False)

class InventarioWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.dados_exibidos = []
        self.sort_qtd_desc = True
        self.titulo = QLabel("Inventário Completo")
        self.titulo.setStyleSheet("font-size: 24px; font-weight: bold;")
        controles_layout_1 = QHBoxLayout()
        self.input_pesquisa = QLineEdit()
        self.input_pesquisa.setPlaceholderText("Buscar por Nome ou Códigos (A, B ou C)...")
        controles_layout_1.addWidget(self.input_pesquisa)
        controles_layout_2 = QHBoxLayout()
        self.btn_adicionar = QPushButton("➕ Adicionar Novo")
        self.btn_adicionar.setObjectName("btnPositive")
        self.btn_editar = QPushButton("✏️ Editar Selecionado")
        self.btn_editar.setObjectName("btnNeutral")
        self.btn_excluir = QPushButton("🗑️ Excluir Selecionado")
        self.btn_excluir.setObjectName("btnNegative")
        self.btn_gerar_etiquetas = QPushButton("🖨️ Gerar Etiquetas")
        self.btn_gerar_etiquetas.setObjectName("btnPrint")
        controles_layout_2.addWidget(self.btn_adicionar)
        controles_layout_2.addWidget(self.btn_editar)
        controles_layout_2.addWidget(self.btn_excluir)
        controles_layout_2.addWidget(self.btn_gerar_etiquetas)
        controles_layout_2.addStretch(1)
        self.btn_ordenar_nome = QPushButton("🔤 A-Z")
        self.btn_ordenar_nome.setToolTip("Ordenar por Nome do Produto")
        self.btn_ordenar_nome.setObjectName("btnIcon")
        self.btn_ordenar_qtd = QPushButton("📦 Qtd.")
        self.btn_ordenar_qtd.setToolTip("Ordenar por Saldo em Estoque")
        self.btn_ordenar_qtd.setObjectName("btnIcon")
        controles_layout_2.addWidget(self.btn_ordenar_nome)
        controles_layout_2.addWidget(self.btn_ordenar_qtd)
        self.tabela_inventario = QTableWidget()
        self.tabela_inventario.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tabela_inventario.setColumnCount(7)
        self.tabela_inventario.setHorizontalHeaderLabels(["Código", "Nome do Produto", "Descrição", "Saldo", "Preço (R$)", "Código B", "Código C"])
        self.tabela_inventario.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabela_inventario.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela_inventario.setAlternatingRowColors(True)
        self.tabela_inventario.setWordWrap(True)
        header = self.tabela_inventario.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.layout.addWidget(self.titulo)
        self.layout.addLayout(controles_layout_1)
        self.layout.addLayout(controles_layout_2)
        self.layout.addWidget(self.tabela_inventario)
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.carregar_dados_inventario)
        self.input_pesquisa.textChanged.connect(self.iniciar_busca_timer)
        self.btn_adicionar.clicked.connect(self.abrir_formulario_adicionar)
        self.btn_editar.clicked.connect(self.abrir_formulario_editar)
        self.btn_excluir.clicked.connect(self.excluir_produto_selecionado)
        self.btn_gerar_etiquetas.clicked.connect(self.gerar_etiquetas_selecionadas)
        self.btn_ordenar_nome.clicked.connect(self.ordenar_por_nome)
        self.btn_ordenar_qtd.clicked.connect(self.ordenar_por_quantidade)
        self.carregar_dados_inventario()
    def iniciar_busca_timer(self):
        self.search_timer.stop()
        self.search_timer.start(300)
    def carregar_dados_inventario(self):
        global access_token
        params = {}
        termo_busca = self.input_pesquisa.text()
        if termo_busca:
            params['search'] = termo_busca
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(f"{API_BASE_URL}/api/estoque/saldos", headers=headers, params=params)
            if response and response.status_code == 200:
                self.dados_exibidos = response.json()
                self.popular_tabela(self.dados_exibidos)
            else:
                QMessageBox.warning(self, "Erro", "Não foi possível carregar os dados do inventário.")
        except requests.exceptions.RequestException:
            show_connection_error_message(self)
    def popular_tabela(self, dados):
        self.tabela_inventario.setRowCount(0)
        self.tabela_inventario.setRowCount(len(dados))
        for linha, item in enumerate(dados):
            item_codigo = QTableWidgetItem(item['codigo'])
            item_codigo.setData(Qt.UserRole, item['id_produto'])
            self.tabela_inventario.setItem(linha, 0, item_codigo)
            self.tabela_inventario.setItem(linha, 1, QTableWidgetItem(item['nome']))
            self.tabela_inventario.setItem(linha, 2, QTableWidgetItem(item.get('descricao', '')))
            saldo_item = QTableWidgetItem(str(item['saldo_atual']))
            saldo_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.tabela_inventario.setItem(linha, 3, saldo_item)
            preco_item = QTableWidgetItem(str(item.get('preco', '0.00')))
            preco_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.tabela_inventario.setItem(linha, 4, preco_item)
            self.tabela_inventario.setItem(linha, 5, QTableWidgetItem(item['codigoB']))
            self.tabela_inventario.setItem(linha, 6, QTableWidgetItem(item['codigoC']))
        self.tabela_inventario.resizeRowsToContents()
    def ordenar_por_nome(self):
        self.dados_exibidos.sort(key=lambda item: item['nome'].lower())
        self.popular_tabela(self.dados_exibidos)
    def ordenar_por_quantidade(self):
        self.dados_exibidos.sort(key=lambda item: int(item['saldo_atual']), reverse=self.sort_qtd_desc)
        self.sort_qtd_desc = not self.sort_qtd_desc
        self.popular_tabela(self.dados_exibidos)
    def abrir_formulario_adicionar(self):
        dialog = FormularioProdutoDialog(self)
        if dialog.exec():
            self.carregar_dados_inventario()
    def abrir_formulario_editar(self):
        linha_selecionada = self.tabela_inventario.currentRow()
        if linha_selecionada < 0:
            QMessageBox.warning(self, "Seleção", "Por favor, selecione um produto para editar.")
            return
        item = self.tabela_inventario.item(linha_selecionada, 0)
        produto_id = item.data(Qt.UserRole)
        dialog = FormularioProdutoDialog(self, produto_id=produto_id, row=linha_selecionada)
        dialog.produto_atualizado.connect(self.atualizar_linha_produto)
        dialog.exec()
    def atualizar_linha_produto(self, linha, dados_produto):
        saldo_antigo = self.tabela_inventario.item(linha, 3).text()
        item_codigo = QTableWidgetItem(dados_produto['codigo'])
        item_codigo.setData(Qt.UserRole, dados_produto['id'])
        self.tabela_inventario.setItem(linha, 0, item_codigo)
        self.tabela_inventario.setItem(linha, 1, QTableWidgetItem(dados_produto['nome']))
        self.tabela_inventario.setItem(linha, 2, QTableWidgetItem(dados_produto['descricao']))
        saldo_item = QTableWidgetItem(saldo_antigo)
        saldo_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tabela_inventario.setItem(linha, 3, saldo_item)
        preco_item = QTableWidgetItem(dados_produto['preco'])
        preco_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.tabela_inventario.setItem(linha, 4, preco_item)
        self.tabela_inventario.setItem(linha, 5, QTableWidgetItem(dados_produto.get('codigoB', '')))
        self.tabela_inventario.setItem(linha, 6, QTableWidgetItem(dados_produto.get('codigoC', '')))
        self.tabela_inventario.resizeRowToContents(linha)
    def excluir_produto_selecionado(self):
        linha_selecionada = self.tabela_inventario.currentRow()
        if linha_selecionada < 0:
            QMessageBox.warning(self, "Seleção", "Por favor, selecione um produto para excluir.")
            return
        item_id = self.tabela_inventario.item(linha_selecionada, 0)
        produto_id = item_id.data(Qt.UserRole)
        nome_produto = self.tabela_inventario.item(linha_selecionada, 1).text()
        resposta = QMessageBox.question(self, "Confirmar Exclusão", f"Tem a certeza de que deseja excluir o produto '{nome_produto}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if resposta == QMessageBox.StandardButton.Yes:
            global access_token
            headers = {'Authorization': f'Bearer {access_token}'}
            try:
                response = requests.delete(f"{API_BASE_URL}/api/produtos/{produto_id}", headers=headers)
                if response and response.status_code == 200:
                    QMessageBox.information(self, "Sucesso", "Produto excluído com sucesso!")
                    self.carregar_dados_inventario()
                else:
                    erro = response.json().get('erro', 'Erro desconhecido.')
                    QMessageBox.warning(self, "Erro", f"Não foi possível excluir o produto: {erro}")
            except requests.exceptions.RequestException:
                show_connection_error_message(self)
    def gerar_etiquetas_selecionadas(self):
        selected_rows = self.tabela_inventario.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Seleção", "Por favor, selecione um ou mais produtos na tabela para gerar as etiquetas.")
            return
        product_ids = []
        for index in selected_rows:
            item = self.tabela_inventario.item(index.row(), 0)
            if item and item.data(Qt.UserRole):
                product_ids.append(item.data(Qt.UserRole))
        if not product_ids:
            QMessageBox.warning(self, "Erro", "Não foi possível obter os IDs dos produtos selecionados.")
            return
        caminho_salvar, _ = QFileDialog.getSaveFileName(self, "Salvar Ficheiro de Etiquetas", "etiquetas.pdf", "Ficheiros PDF (*.pdf)")
        if not caminho_salvar:
            return
        global access_token
        headers = {'Authorization': f'Bearer {access_token}'}
        dados = {'product_ids': product_ids}
        try:
            msg_box = QMessageBox(QMessageBox.Icon.Information, "Aguarde", "A gerar o ficheiro de etiquetas...", buttons=QMessageBox.StandardButton.NoButton, parent=self)
            msg_box.show()
            QApplication.processEvents()
            response = requests.post(f"{API_BASE_URL}/api/produtos/etiquetas", headers=headers, json=dados, stream=True)
            msg_box.close()
            if response and response.status_code == 200:
                with open(caminho_salvar, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                QMessageBox.information(self, "Sucesso", f"Ficheiro de etiquetas salvo com sucesso em:\n{caminho_salvar}")
            else:
                erro = response.json().get('erro', 'Erro desconhecido.')
                QMessageBox.warning(self, "Erro na API", f"Não foi possível gerar as etiquetas: {erro}")
        except requests.exceptions.RequestException:
            msg_box.close()
            show_connection_error_message(self)

class GestaoEstoqueWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,0)
        self.inventario_view = InventarioWidget()
        self.historico_view = HistoricoWidget()
        nav_layout = QHBoxLayout()
        self.btn_ver_inventario = QPushButton("Visão Geral do Inventário")
        self.btn_ver_historico = QPushButton("Ver Histórico de Movimentações")
        self.btn_ver_inventario.setCheckable(True)
        self.btn_ver_historico.setCheckable(True)
        self.btn_ver_inventario.setChecked(True)
        nav_layout.addWidget(self.btn_ver_inventario)
        nav_layout.addWidget(self.btn_ver_historico)
        nav_layout.addStretch(1)
        self.stack = QStackedWidget()
        self.stack.addWidget(self.inventario_view)
        self.stack.addWidget(self.historico_view)
        self.layout.addLayout(nav_layout)
        self.layout.addWidget(self.stack)
        self.btn_ver_inventario.clicked.connect(self.mostrar_inventario)
        self.btn_ver_historico.clicked.connect(self.mostrar_historico)
    def mostrar_inventario(self):
        self.stack.setCurrentWidget(self.inventario_view)
        self.btn_ver_inventario.setChecked(True)
        self.btn_ver_historico.setChecked(False)
        self.inventario_view.carregar_dados_inventario()
    def mostrar_historico(self):
        self.stack.setCurrentWidget(self.historico_view)
        self.btn_ver_inventario.setChecked(False)
        self.btn_ver_historico.setChecked(True)
        self.historico_view.carregar_historico()

class HistoricoWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.dados_completos = []
        layout_filtros = QHBoxLayout()
        self.combo_tipo = QComboBox()
        self.combo_tipo.addItems(["Todas", "Entrada", "Saida"])
        self.combo_tipo.setStyleSheet("font-size: 14px; padding: 5px;")
        self.btn_recarregar = QPushButton("Recarregar Histórico")
        layout_filtros.addWidget(QLabel("Filtrar por tipo:"))
        layout_filtros.addWidget(self.combo_tipo)
        layout_filtros.addStretch(1)
        layout_filtros.addWidget(self.btn_recarregar)
        self.tabela_historico = QTableWidget()
        self.tabela_historico.setColumnCount(8)
        self.tabela_historico.setHorizontalHeaderLabels(["Data/Hora", "Cód. Produto", "Nome Produto", "Tipo", "Qtd. Mov.", "Saldo Após", "Usuário", "Motivo da Saída"])
        self.tabela_historico.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabela_historico.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela_historico.setAlternatingRowColors(True)
        self.layout.addLayout(layout_filtros)
        self.layout.addWidget(self.tabela_historico)
        self.btn_recarregar.clicked.connect(self.carregar_historico)
        self.combo_tipo.currentIndexChanged.connect(self.carregar_historico)
        self.carregar_historico()
    def carregar_historico(self):
        global access_token
        data_fim = QDate.currentDate()
        data_inicio = data_fim.addDays(-90)
        params = {'data_inicio': data_inicio.toString("yyyy-MM-dd"), 'data_fim': data_fim.toString("yyyy-MM-dd"), 'formato': 'json'}
        filtro_tipo = self.combo_tipo.currentText()
        if filtro_tipo != "Todas":
            params['tipo'] = filtro_tipo
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(f"{API_BASE_URL}/api/relatorios/movimentacoes", headers=headers, params=params)
            if response and response.status_code == 200:
                self.dados_completos = response.json()
                self.popular_tabela(self.dados_completos)
            else:
                mensagem = "Não foi possível carregar o histórico."
                if response:
                    mensagem += f"\n(Erro: {response.status_code})"
                QMessageBox.warning(self, "Erro", mensagem)
        except requests.exceptions.RequestException:
            show_connection_error_message(self)
    def popular_tabela(self, dados):
        self.tabela_historico.setRowCount(0)
        self.tabela_historico.setRowCount(len(dados))
        for linha, mov in enumerate(dados):
            self.tabela_historico.setItem(linha, 0, QTableWidgetItem(mov['data_hora']))
            self.tabela_historico.setItem(linha, 1, QTableWidgetItem(mov['produto_codigo']))
            self.tabela_historico.setItem(linha, 2, QTableWidgetItem(mov['produto_nome']))
            self.tabela_historico.setItem(linha, 3, QTableWidgetItem(mov['tipo']))
            self.tabela_historico.setItem(linha, 4, QTableWidgetItem(str(mov['quantidade'])))
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
        self.btn_gerar_pdf.setObjectName("btnNegative")
        self.btn_gerar_excel = QPushButton("Gerar Excel (XLSX)")
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
        except requests.exceptions.RequestException:
            show_connection_error_message(self)

class FornecedoresWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.titulo = QLabel("Gestão de Fornecedores")
        self.titulo.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout_botoes = QHBoxLayout()
        self.btn_adicionar = QPushButton("➕ Adicionar Novo")
        self.btn_adicionar.setObjectName("btnPositive")
        self.btn_editar = QPushButton("✏️ Editar Selecionado")
        self.btn_editar.setObjectName("btnNeutral")
        self.btn_excluir = QPushButton("🗑️ Excluir Selecionado")
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
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(f"{API_BASE_URL}/api/fornecedores", headers=headers)
            if response.status_code == 200:
                fornecedores = response.json()
                self.tabela_fornecedores.setRowCount(len(fornecedores))
                for linha, forn in enumerate(fornecedores):
                    item_nome = QTableWidgetItem(forn['nome'])
                    item_nome.setData(Qt.UserRole, forn['id'])
                    self.tabela_fornecedores.setItem(linha, 0, item_nome)
            else:
                QMessageBox.warning(self, "Erro", "Não foi possível carregar os fornecedores.")
        except requests.exceptions.RequestException:
            show_connection_error_message(self)
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
            headers = {'Authorization': f'Bearer {access_token}'}
            try:
                response = requests.delete(f"{API_BASE_URL}/api/fornecedores/{fornecedor_id}", headers=headers)
                if response.status_code == 200:
                    QMessageBox.information(self, "Sucesso", "Fornecedor excluído com sucesso!")
                    self.carregar_fornecedores()
                else:
                    QMessageBox.warning(self, "Erro", f"Não foi possível excluir: {response.json().get('erro')}")
            except requests.exceptions.RequestException:
                show_connection_error_message(self)

class NaturezasWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.titulo = QLabel("Gestão de Naturezas")
        self.titulo.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout_botoes = QHBoxLayout()
        self.btn_adicionar = QPushButton("➕ Adicionar Nova")
        self.btn_adicionar.setObjectName("btnPositive")
        self.btn_editar = QPushButton("✏️ Editar Selecionada")
        self.btn_editar.setObjectName("btnNeutral")
        self.btn_excluir = QPushButton("🗑️ Excluir Selecionada")
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
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(f"{API_BASE_URL}/api/naturezas", headers=headers)
            if response.status_code == 200:
                naturezas = response.json()
                self.tabela_naturezas.setRowCount(len(naturezas))
                for linha, nat in enumerate(naturezas):
                    item_nome = QTableWidgetItem(nat['nome'])
                    item_nome.setData(Qt.UserRole, nat['id'])
                    self.tabela_naturezas.setItem(linha, 0, item_nome)
            else:
                QMessageBox.warning(self, "Erro", "Não foi possível carregar as naturezas.")
        except requests.exceptions.RequestException:
            show_connection_error_message(self)
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
            headers = {'Authorization': f'Bearer {access_token}'}
            try:
                response = requests.delete(f"{API_BASE_URL}/api/naturezas/{natureza_id}", headers=headers)
                if response.status_code == 200:
                    QMessageBox.information(self, "Sucesso", "Natureza excluída com sucesso!")
                    self.carregar_naturezas()
                else:
                    QMessageBox.warning(self, "Erro", f"Não foi possível excluir: {response.json().get('erro')}")
            except requests.exceptions.RequestException:
                show_connection_error_message(self)

class EntradaRapidaWidget(QWidget):
    estoque_atualizado = Signal()
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.produto_encontrado_id = None
        self.titulo = QLabel("Entrada Rápida de Estoque")
        self.titulo.setStyleSheet("font-size: 24px; font-weight: bold; margin-bottom: 10px;")
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        self.input_codigo = QLineEdit()
        self.input_codigo.setPlaceholderText("Digite ou leia o código do produto aqui")
        self.btn_verificar = QPushButton("Verificar Produto")
        self.btn_verificar.setObjectName("btnNeutral")
        layout_codigo = QHBoxLayout()
        layout_codigo.addWidget(self.input_codigo)
        layout_codigo.addWidget(self.btn_verificar)
        form_layout.addRow("Código do Produto:", layout_codigo)
        self.label_nome_produto = QLabel("Aguardando verificação...")
        form_layout.addRow("Produto Encontrado:", self.label_nome_produto)
        self.input_quantidade = QLineEdit()
        self.input_quantidade.setPlaceholderText("0")
        self.input_quantidade.setValidator(QDoubleValidator(0, 99999, 0))
        form_layout.addRow("Quantidade a Adicionar:", self.input_quantidade)
        self.btn_registrar = QPushButton("Registar Entrada")
        self.btn_registrar.setObjectName("btnPositive")
        self.layout.addWidget(self.titulo)
        self.layout.addLayout(form_layout)
        self.layout.addWidget(self.btn_registrar, 0, Qt.AlignmentFlag.AlignRight)
        self.layout.addStretch(1)
        self.btn_verificar.clicked.connect(self.verificar_produto)
        self.input_codigo.returnPressed.connect(self.verificar_produto) 
        self.btn_registrar.clicked.connect(self.registrar_entrada)
        self.input_quantidade.returnPressed.connect(self.btn_registrar.click)
        self.resetar_formulario()
    def verificar_produto(self):
        codigo_produto = self.input_codigo.text().strip()
        if not codigo_produto:
            QMessageBox.warning(self, "Atenção", "O campo de código não pode estar vazio.")
            return
        global access_token
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(f"{API_BASE_URL}/api/produtos/codigo/{codigo_produto}", headers=headers)
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
        except requests.exceptions.RequestException:
            show_connection_error_message(self)
    def registrar_entrada(self):
        quantidade = self.input_quantidade.text()
        if not self.produto_encontrado_id or not quantidade or int(quantidade) <= 0:
            QMessageBox.warning(self, "Dados Inválidos", "Verifique o produto e insira uma quantidade válida maior que zero.")
            return
        global access_token
        headers = {'Authorization': f'Bearer {access_token}'}
        dados = {"id_produto": self.produto_encontrado_id, "quantidade": int(quantidade)}
        try:
            response = requests.post(f"{API_BASE_URL}/api/estoque/entrada", headers=headers, json=dados)
            if response and response.status_code == 201:
                self.estoque_atualizado.emit()
                QMessageBox.information(self, "Sucesso", "Entrada de estoque registada com sucesso!")
                self.resetar_formulario()
            else:
                erro = response.json().get('erro', 'Erro desconhecido.')
                QMessageBox.warning(self, "Erro", f"Não foi possível registar a entrada: {erro}")
        except requests.exceptions.RequestException:
            show_connection_error_message(self)
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
    estoque_atualizado = Signal()
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.produto_encontrado_id = None
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
        self.btn_verificar.clicked.connect(self.verificar_produto)
        self.input_codigo.returnPressed.connect(self.verificar_produto)
        self.btn_registrar.clicked.connect(self.registrar_saida)
        self.input_motivo.returnPressed.connect(self.btn_registrar.click)
        self.resetar_formulario()
    def verificar_produto(self):
        codigo_produto = self.input_codigo.text().strip()
        if not codigo_produto: return
        global access_token
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(f"{API_BASE_URL}/api/produtos/codigo/{codigo_produto}", headers=headers)
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
        except requests.exceptions.RequestException:
            show_connection_error_message(self)
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
        headers = {'Authorization': f'Bearer {access_token}'}
        dados = {"id_produto": self.produto_encontrado_id, "quantidade": int(quantidade), "motivo_saida": motivo}
        try:
            response = requests.post(f"{API_BASE_URL}/api/estoque/saida", headers=headers, json=dados)
            if response and response.status_code == 201:
                self.estoque_atualizado.emit()
                QMessageBox.information(self, "Sucesso", "Saída de estoque registada com sucesso!")
                self.resetar_formulario()
            else:
                erro = response.json().get('erro', 'Erro desconhecido.')
                QMessageBox.warning(self, "Erro", f"Não foi possível registar a saída: {erro}")
        except requests.exceptions.RequestException:
            show_connection_error_message(self)
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
        self.btn_adicionar.setObjectName("btnPositive")
        self.btn_editar = QPushButton("✏️ Editar Selecionado")
        self.btn_editar.setObjectName("btnNeutral")
        self.btn_desativar = QPushButton("🚫 Desativar/Reativar")
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
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(f"{API_BASE_URL}/api/usuarios", headers=headers)
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
        except requests.exceptions.RequestException:
            show_connection_error_message(self)
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
        resposta = QMessageBox.question(self, f"Confirmar Ação", f"Tem certeza que deseja {acao} o usuário '{nome_usuario}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if resposta == QMessageBox.StandardButton.Yes:
            global access_token
            headers = {'Authorization': f'Bearer {access_token}'}
            try:
                response = requests.delete(f"{API_BASE_URL}/api/usuarios/{usuario_id}", headers=headers)
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
            except requests.exceptions.RequestException:
                show_connection_error_message(self)

# No seu ficheiro main_ui.py, substitua as suas classes TerminalWidget e JanelaPrincipal por estas:

class TerminalWidget(QWidget):
    """Tela de consulta rápida com design profissional e funcionalidade de adição."""
    # Sinais para comunicar com a JanelaPrincipal
    ir_para_novo_produto = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("terminalWidget")
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.layout.setContentsMargins(20, 10, 20, 20)

        # --- ATRIBUTOS ---
        self.barcode_buffer = ""
        self.barcode_timer = QTimer(self)
        self.barcode_timer.setSingleShot(True)
        self.barcode_timer.setInterval(200)
        self.produto_atual = None

        # --- 1. CRIAÇÃO DE TODOS OS WIDGETS PRIMEIRO ---
        logo_label = QLabel()
        logo_pixmap = QPixmap(resource_path("logo.png"))
        logo_redimensionada = logo_pixmap.scaled(200, 80, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        logo_label.setPixmap(logo_redimensionada)
        
        titulo = QLabel("SUPER TERMINAL")
        titulo.setObjectName("terminalHeaderTitle")
        
        self.btn_novo_produto = QPushButton("➕ Novo Produto")
        self.btn_novo_produto.setObjectName("btnTerminalNewProduct")

        main_panel = QFrame()
        main_panel.setObjectName("terminalMainPanel")
        
        self.label_nome = QLabel("Passe um código de barras no leitor...")
        self.label_nome.setObjectName("terminalProductName")
        self.label_nome.setWordWrap(True)
        
        self.label_qtd_box = QFrame()
        self.label_qtd_box.setObjectName("terminalQuantityBox")
        self.label_qtd_valor = QLabel("--")
        self.label_qtd_valor.setObjectName("terminalQuantityValue")
        
        bottom_panel = QFrame()
        bottom_panel.setObjectName("terminalBottomPanel")
        
        self.label_descricao = QLabel("Descrição do produto aparecerá aqui.")
        self.label_descricao.setObjectName("terminalDescription")
        self.label_codigo = QLabel("Código: --")
        self.label_codigo.setObjectName("terminalCode")
        
        self.btn_remover = QPushButton("➖")
        self.btn_remover.setObjectName("btnTerminalRemove")
        self.btn_adicionar = QPushButton("➕")
        self.btn_adicionar.setObjectName("btnTerminalAdd")

        # --- 2. ORGANIZAÇÃO DO LAYOUT ---
        header_layout = QHBoxLayout()
        header_layout.addWidget(logo_label)
        header_layout.addStretch(1)
        header_layout.addWidget(titulo)
        header_layout.addStretch(1)
        header_layout.addWidget(self.btn_novo_produto)

        main_panel_layout = QHBoxLayout(main_panel)
        main_panel_layout.setSpacing(0)
        main_panel_layout.addWidget(self.label_nome, 3)
        qtd_layout = QVBoxLayout(self.label_qtd_box)
        qtd_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        qtd_layout.addWidget(self.label_qtd_valor)
        main_panel_layout.addWidget(self.label_qtd_box, 1)

        bottom_panel_layout = QHBoxLayout(bottom_panel)
        info_layout = QVBoxLayout()
        info_layout.addWidget(self.label_descricao)
        info_layout.addWidget(self.label_codigo)
        bottom_panel_layout.addLayout(info_layout, 3)
        action_buttons_layout = QHBoxLayout()
        action_buttons_layout.addStretch(1)
        action_buttons_layout.addWidget(self.btn_remover)
        action_buttons_layout.addWidget(self.btn_adicionar)
        bottom_panel_layout.addLayout(action_buttons_layout, 1)

        self.layout.addLayout(header_layout)
        self.layout.addWidget(main_panel, 1)
        self.layout.addWidget(bottom_panel, 1)
        
        # --- 3. CONEXÕES DOS SINAIS ---
        self.barcode_timer.timeout.connect(self.processar_codigo)
        self.btn_adicionar.clicked.connect(lambda: self.abrir_dialogo_quantidade("Entrada"))
        self.btn_remover.clicked.connect(lambda: self.abrir_dialogo_quantidade("Saida"))
        self.btn_novo_produto.clicked.connect(self.ir_para_novo_produto.emit)
        
        self.resetar_tela()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            self.barcode_timer.stop()
            self.processar_codigo()
        else:
            self.barcode_buffer += event.text()
            self.barcode_timer.start()

    def processar_codigo(self):
        codigo = self.barcode_buffer.strip()
        self.barcode_buffer = ""
        if not codigo:
            return

        self.label_nome.setText("A procurar...")
        QApplication.processEvents()

        global access_token
        url = f"{API_BASE_URL}/api/estoque/saldos?search={codigo}"
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(url, headers=headers)
            if response and response.status_code == 200:
                resultados = response.json()
                if resultados:
                    self.produto_atual = resultados[0]
                    self.atualizar_display()
                else:
                    self.produto_nao_encontrado()
            else:
                self.produto_nao_encontrado()
        except requests.exceptions.RequestException:
            self.produto_nao_encontrado("Erro de conexão.")

    def atualizar_display(self):
        self.label_nome.setText(self.produto_atual.get('nome', 'N/A'))
        self.label_qtd_valor.setText(str(self.produto_atual.get('saldo_atual', '--')))
        self.label_descricao.setText(self.produto_atual.get('descricao', 'Sem descrição.'))
        self.label_codigo.setText(f"Código: {self.produto_atual.get('codigo', '--')}")
        self.btn_adicionar.setEnabled(True)
        self.btn_remover.setEnabled(True)

    def produto_nao_encontrado(self, msg="Produto não encontrado."):
        self.produto_atual = None
        self.label_nome.setText(msg)
        self.resetar_tela(manter_msg=True)

    def resetar_tela(self, manter_msg=False):
        if not manter_msg:
            self.label_nome.setText("Passe um código de barras no leitor...")
        self.label_qtd_valor.setText("--")
        self.label_descricao.setText("Descrição do produto aparecerá aqui.")
        self.label_codigo.setText("Código: --")
        self.btn_adicionar.setEnabled(False)
        self.btn_remover.setEnabled(False)

    def abrir_dialogo_quantidade(self, operacao):
        if not self.produto_atual:
            return
        
        dialog = QuantidadeDialog(self,
                                  self.produto_atual['id_produto'],
                                  self.produto_atual['nome'],
                                  self.produto_atual['codigo'],
                                  operacao)
        dialog.estoque_modificado.connect(self.reprocessar_codigo_apos_modificacao)
        dialog.exec()

    def reprocessar_codigo_apos_modificacao(self, codigo):
        self.barcode_buffer = codigo
        self.processar_codigo()

# ==============================================================================
# CLASSES DE DOCUMENTOS 
#===============================================================================
class DocumentacaoWidget(QWidget):
    """
    Widget principal que gere toda a funcionalidade de geração de documentação,
    incluindo o formulário de abas e a tela de anexos.
    """
    def __init__(self, servico_id):
        super().__init__()
        self.servico_id = servico_id
        self.dados_formulario_capturados = {} # Atributo para guardar o JSON entre as telas

        # --- 1. Layouts Principais ---
        self.layout_principal = QHBoxLayout(self)
        self.stacked_widget_interno = QStackedWidget() # Para alternar entre formulário e anexos

        # --- 2. Criação da Tela de Formulário ---
        self.widget_formulario = QWidget()
        layout_formulario = QVBoxLayout(self.widget_formulario)
        
        self.tab_widget = QTabWidget()
        
        # Chamada aos métodos para criar o conteúdo de cada aba
        self.tab_widget.addTab(self._criar_aba_identificacao(), "1. Identificação")
        self.tab_widget.addTab(self._criar_aba_escopo(), "2. Escopo")
        self.tab_widget.addTab(self._criar_aba_lista_documentos(), "3. Lista de Docs")
        self.tab_widget.addTab(self._criar_aba_diagramas(), "4. Diagramas")
        self.tab_widget.addTab(self._criar_aba_lista_instrumentos(), "5. Dispositivos & Instrumentos")
        self.tab_widget.addTab(self._criar_aba_programacao(), "7. Programação")
        self.tab_widget.addTab(self._criar_aba_testes(), "8. Testes")
        self.tab_widget.addTab(self._criar_aba_operacao(), "9. Operação")
        self.tab_widget.addTab(self._criar_aba_treinamento(), "10. Treinamento")
        self.tab_widget.addTab(self._criar_aba_as_built(), "11. As Built")
        self.tab_widget.addTab(self._criar_aba_anexos(), "12. Anexos")
        
        self.btn_proximo = QPushButton("Próximo -> Para Anexos")
        self.btn_proximo.setObjectName("btnPositive")
        self.btn_proximo.clicked.connect(self.avancar_para_anexos)
        
        layout_formulario.addWidget(self.tab_widget)
        layout_formulario.addWidget(self.btn_proximo, 0, Qt.AlignmentFlag.AlignRight)

        # --- 3. Criação da Tela de Anexos ---
        self.widget_anexos = AnexosWidget()
        self.widget_anexos.voltar_solicitado.connect(self.voltar_para_formulario)
        self.widget_anexos.gerar_documento_solicitado.connect(self.iniciar_geracao_documento)

        # --- 4. Adicionar as "Telas" ao StackedWidget ---
        self.stacked_widget_interno.addWidget(self.widget_formulario)
        self.stacked_widget_interno.addWidget(self.widget_anexos)

        # --- 5. Criação da Lista de Histórico (Lado Direito) ---
        self.lista_historico = QListWidget()
        self.lista_historico.itemClicked.connect(self.on_historico_item_clicado)


        # --- NOVO CÓDIGO AQUI ---
        self.btn_excluir_historico = QPushButton("🗑️ Excluir Selecionado")
        self.btn_excluir_historico.setObjectName("btnNegative") # Estilo vermelho
        self.btn_excluir_historico.clicked.connect(self.on_excluir_historico_clicado)
        
        # Criamos um layout vertical para o lado direito
        layout_direita = QVBoxLayout()
        layout_direita.addWidget(self.lista_historico)
        layout_direita.addWidget(self.btn_excluir_historico)
        # --- FIM DO NOVO CÓDIGO ---
        # --- 6. Montagem Final do Layout ---
        self.layout_principal.addWidget(self.stacked_widget_interno, 2)
        self.layout_principal.addLayout(layout_direita, 1)

        # --- 7. Carregamento Inicial dos Dados ---
        self.carregar_historico()

    # ==============================================================================
    # MÉTODOS AUXILIARES PARA CRIAR CADA ABA
    # ==============================================================================
    def _criar_aba_identificacao(self):
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setSpacing(15)
        self.input_nome_projeto = QLineEdit()
        self.input_cliente = QLineEdit()
        self.input_local_instalacao = QLineEdit()
        self.input_empresa_responsavel = QLineEdit()
        self.input_data_versao = QLineEdit()
        self.input_num_contrato = QLineEdit()
        layout.addRow("Nome do projeto:", self.input_nome_projeto)
        layout.addRow("Cliente:", self.input_cliente)
        layout.addRow("Local de instalação:", self.input_local_instalacao)
        layout.addRow("Empresa responsável:", self.input_empresa_responsavel)
        layout.addRow("Data e versão do documento:", self.input_data_versao)
        layout.addRow("Número de contrato/ordem de serviço:", self.input_num_contrato)
        return widget

    def _criar_aba_escopo(self):
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setSpacing(15)
        self.text_objetivos = QTextEdit()
        self.text_limites = QTextEdit()
        self.text_premissas = QTextEdit()
        self.text_interfaces = QTextEdit()
        layout.addRow("Objetivos do projeto:", self.text_objetivos)
        layout.addRow("Limites de fornecimento:", self.text_limites)
        layout.addRow("Premissas e restrições técnicas:", self.text_premissas)
        layout.addRow("Interfaces com outras disciplinas:", self.text_interfaces)
        return widget

    def _criar_aba_lista_documentos(self):
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.tabela_documentos_projeto = QTableWidget()
        self.tabela_documentos_projeto.setColumnCount(6)
        self.tabela_documentos_projeto.setHorizontalHeaderLabels(["Título", "Código/Nº", "Revisão", "Data", "Autor", "Status"])
        self.tabela_documentos_projeto.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # --- Lógica dos Botões ---
        def adicionar_linha_documento():
            linha = self.tabela_documentos_projeto.rowCount()
            self.tabela_documentos_projeto.insertRow(linha)
    
        def remover_linha_documento():
            linha_selecionada = self.tabela_documentos_projeto.currentRow()
            if linha_selecionada >= 0:
                self.tabela_documentos_projeto.removeRow(linha_selecionada)
    
        layout_botoes = QHBoxLayout()
        self.btn_add_doc = QPushButton("➕ Adicionar Documento")
        self.btn_rem_doc = QPushButton("➖ Remover Selecionado")
        self.btn_add_doc.clicked.connect(adicionar_linha_documento)
        self.btn_rem_doc.clicked.connect(remover_linha_documento)
        layout_botoes.addStretch(1)
        layout_botoes.addWidget(self.btn_add_doc)
        layout_botoes.addWidget(self.btn_rem_doc)
    
        layout.addWidget(self.tabela_documentos_projeto)
        layout.addLayout(layout_botoes)
        return widget

    def _criar_aba_diagramas(self):
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setSpacing(15)
        self.text_diagramas_notas = QTextEdit()
        self.text_diagramas_notas.setPlaceholderText("Descreva os diagramas principais do projeto, como P&ID, unifilares elétricos, diagramas de malha, rede, etc.")
        layout.addRow("Descrição e Notas sobre os Diagramas:", self.text_diagramas_notas)
        return widget

    def _criar_aba_lista_instrumentos(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.tabela_instrumentos = QTableWidget()
        self.tabela_instrumentos.setColumnCount(6)
        self.tabela_instrumentos.setHorizontalHeaderLabels(["Tag", "Descrição", "Fabricante/Modelo", "Faixa", "Sinal", "Localização"])
        self.tabela_instrumentos.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # --- Lógica dos Botões ---
        def adicionar_linha_instrumento():
            linha = self.tabela_instrumentos.rowCount()
            self.tabela_instrumentos.insertRow(linha)
    
        def remover_linha_instrumento():
            linha_selecionada = self.tabela_instrumentos.currentRow()
            if linha_selecionada >= 0:
                self.tabela_instrumentos.removeRow(linha_selecionada)
    
        layout_botoes = QHBoxLayout()
        self.btn_add_instrumento = QPushButton("➕ Adicionar Instrumento")
        self.btn_rem_instrumento = QPushButton("➖ Remover Selecionado")
        self.btn_add_instrumento.clicked.connect(adicionar_linha_instrumento)
        self.btn_rem_instrumento.clicked.connect(remover_linha_instrumento)
        layout_botoes.addStretch(1)
        layout_botoes.addWidget(self.btn_add_instrumento)
        layout_botoes.addWidget(self.btn_rem_instrumento)
    
        layout.addWidget(self.tabela_instrumentos)
        layout.addLayout(layout_botoes)
        return widget

    def _criar_aba_programacao(self):
        
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.tabela_programacao = QTableWidget()
        self.tabela_programacao.setColumnCount(2)
        self.tabela_programacao.setHorizontalHeaderLabels(["Ficheiro (Backup/Print do Programa)", "Descrição Funcional/Comentários"])
        self.tabela_programacao.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tabela_programacao.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        # --- Lógica dos Botões ---
        def adicionar_linha_programa():
            linha = self.tabela_programacao.rowCount()
            self.tabela_programacao.insertRow(linha)
    
        def remover_linha_programa():
            linha_selecionada = self.tabela_programacao.currentRow()
            if linha_selecionada >= 0:
                self.tabela_programacao.removeRow(linha_selecionada)
    
        layout_botoes = QHBoxLayout()
        self.btn_add_programa = QPushButton("➕ Adicionar Programa")
        self.btn_rem_programa = QPushButton("➖ Remover Selecionado")
        self.btn_add_programa.clicked.connect(adicionar_linha_programa)
        self.btn_rem_programa.clicked.connect(remover_linha_programa)
        layout_botoes.addStretch(1)
        layout_botoes.addWidget(self.btn_add_programa)
        layout_botoes.addWidget(self.btn_rem_programa)
        
        layout.addWidget(self.tabela_programacao)
        layout.addLayout(layout_botoes)
        return widget

    def _criar_aba_testes(self):
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setSpacing(15)
        self.text_procedimentos_testes = QTextEdit()
        self.text_relatorios_testes = QTextEdit()
        self.text_nao_conformidades = QTextEdit()
        layout.addRow("Procedimentos (FAT/SAT) e Checklists:", self.text_procedimentos_testes)
        layout.addRow("Relatórios de testes com resultados:", self.text_relatorios_testes)
        layout.addRow("Registro de não conformidades:", self.text_nao_conformidades)
        return widget

    def _criar_aba_operacao(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.radio_texto_manual = QRadioButton("Escrever Manualmente")
        self.radio_pdf_manual = QRadioButton("Anexar PDF do Manual de Operação")
        layout_escolha = QHBoxLayout()
        layout_escolha.addWidget(self.radio_texto_manual)
        layout_escolha.addWidget(self.radio_pdf_manual)
        layout_escolha.addStretch(1)
        self.text_manual_operacao = QTextEdit()
        self.widget_selecao_pdf = QWidget()
        layout_pdf = QHBoxLayout(self.widget_selecao_pdf)
        self.input_caminho_pdf_manual = QLineEdit()
        self.input_caminho_pdf_manual.setReadOnly(True)
        self.btn_procurar_pdf_manual = QPushButton("Procurar...")
        layout_pdf.addWidget(self.input_caminho_pdf_manual)
        layout_pdf.addWidget(self.btn_procurar_pdf_manual)
        self.radio_texto_manual.toggled.connect(self.text_manual_operacao.setVisible)
        self.radio_pdf_manual.toggled.connect(self.widget_selecao_pdf.setVisible)
        self.radio_texto_manual.setChecked(True)
        self.widget_selecao_pdf.hide()
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        self.text_procedimentos_manutencao = QTextEdit()
        self.text_sobressalentes = QTextEdit()
        form_layout.addRow("Procedimentos de calibração/manutenção:", self.text_procedimentos_manutencao)
        form_layout.addRow("Lista de sobressalentes recomendados:", self.text_sobressalentes)
        layout.addLayout(layout_escolha)
        layout.addWidget(self.text_manual_operacao)
        layout.addWidget(self.widget_selecao_pdf)
        layout.addLayout(form_layout)
        return widget

    def _criar_aba_treinamento(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        form_layout = QFormLayout()
        self.text_programa_treinamento = QTextEdit()
        form_layout.addRow("Programa e conteúdo aplicado:", self.text_programa_treinamento)
        
        self.tabela_participantes = QTableWidget()
        self.tabela_participantes.setColumnCount(2)
        self.tabela_participantes.setHorizontalHeaderLabels(["Nome do Participante", "Certificado (Sim/Não)"])
        self.tabela_participantes.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        # --- Lógica dos Botões ---
        def adicionar_linha_participante():
            linha = self.tabela_participantes.rowCount()
            self.tabela_participantes.insertRow(linha)
    
        def remover_linha_participante():
            linha_selecionada = self.tabela_participantes.currentRow()
            if linha_selecionada >= 0:
                self.tabela_participantes.removeRow(linha_selecionada)
    
        layout_botoes = QHBoxLayout()
        self.btn_add_participante = QPushButton("➕ Adicionar Participante")
        self.btn_rem_participante = QPushButton("➖ Remover Selecionado")
        self.btn_add_participante.clicked.connect(adicionar_linha_participante)
        self.btn_rem_participante.clicked.connect(remover_linha_participante)
        layout_botoes.addStretch(1)
        layout_botoes.addWidget(self.btn_add_participante)
        layout_botoes.addWidget(self.btn_rem_participante)
    
        layout.addLayout(form_layout)
        layout.addWidget(QLabel("Lista de Participantes:"))
        layout.addWidget(self.tabela_participantes)
        layout.addLayout(layout_botoes)
        return widget

    def _criar_aba_as_built(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.tabela_as_built = QTableWidget()
        self.tabela_as_built.setColumnCount(2)
        self.tabela_as_built.setHorizontalHeaderLabels(["Documento 'As Built' (PDF)", "Notas / Detalhes da Atualização"])
        self.tabela_as_built.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tabela_as_built.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        # --- Lógica dos Botões ---
        def adicionar_linha_as_built():
            linha = self.tabela_as_built.rowCount()
            self.tabela_as_built.insertRow(linha)
    
        def remover_linha_as_built():
            linha_selecionada = self.tabela_as_built.currentRow()
            if linha_selecionada >= 0:
                self.tabela_as_built.removeRow(linha_selecionada)
    
        layout_botoes = QHBoxLayout()
        self.btn_add_as_built = QPushButton("➕ Adicionar Documento")
        self.btn_rem_as_built = QPushButton("➖ Remover Selecionado")
        self.btn_add_as_built.clicked.connect(adicionar_linha_as_built)
        self.btn_rem_as_built.clicked.connect(remover_linha_as_built)
        layout_botoes.addStretch(1)
        layout_botoes.addWidget(self.btn_add_as_built)
        layout_botoes.addWidget(self.btn_rem_as_built)
        
        layout.addWidget(self.tabela_as_built)
        layout.addLayout(layout_botoes)
        return widget

    def _criar_aba_anexos(self):
        widget = QWidget()
        layout = QFormLayout(widget)
        self.text_anexos = QTextEdit()
        self.text_anexos.setPlaceholderText("Liste aqui os documentos anexos principais, como Datasheets, Manuais, Licenças, Certificados, ARTs, etc. A etapa de upload dos ficheiros será a seguir.")
        layout.addRow("Lista e Descrição dos Anexos:", self.text_anexos)
        return widget


# Em main_ui.py, adicione este método à classe DocumentacaoWidget

    def on_excluir_historico_clicado(self):
        """
        Chamado ao clicar no botão para excluir um item do histórico.
        """
        # 1. Pega no item atualmente selecionado na lista
        item_selecionado = self.lista_historico.currentItem()
        
        if not item_selecionado:
            QMessageBox.warning(self, "Seleção", "Por favor, selecione um item do histórico para excluir.")
            return
    
        documento_id = item_selecionado.data(Qt.UserRole)
        texto_item = item_selecionado.text()
    
        # 2. Pede confirmação ao utilizador
        resposta = QMessageBox.question(self, "Confirmar Exclusão", 
            f"Tem a certeza de que deseja excluir permanentemente o seguinte documento?\n\n<b>{texto_item}</b>\n\nEsta ação não pode ser desfeita.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    
        if resposta == QMessageBox.StandardButton.No:
            return
    
        # 3. Inicia a chamada à API DELETE em background
        self.thread_exclusao = QThread()
        self.worker_exclusao = ApiWorker("delete", f"/api/documentos/{documento_id}")
        self.worker_exclusao.moveToThread(self.thread_exclusao)
        
        self.thread_exclusao.started.connect(self.worker_exclusao.run)
        self.worker_exclusao.finished.connect(self.on_exclusao_finalizada)
        
        # Padrão de limpeza robusto
        self.worker_exclusao.finished.connect(self.thread_exclusao.quit)
        self.worker_exclusao.finished.connect(self.worker_exclusao.deleteLater)
        self.thread_exclusao.finished.connect(self.thread_exclusao.deleteLater)
        
        self.thread_exclusao.start()
    
    def on_exclusao_finalizada(self, status_code, data):
        """Callback que é executado após a tentativa de exclusão na API."""
        if status_code == 200:
            QMessageBox.information(self, "Sucesso", data.get('mensagem', 'Item excluído com sucesso!'))
            # Recarrega a lista para mostrar que o item desapareceu
            self.carregar_historico()
        else:
            erro = data.get('erro', 'Ocorreu um erro desconhecido.')
            QMessageBox.critical(self, "Falha na Exclusão", f"Não foi possível excluir o item:\n\n{erro}")
        # ==============================================================================
        # MÉTODOS DE LÓGICA E NAVEGAÇÃO
        # ==============================================================================
    
    def _capturar_dados_do_formulario(self):
        """Método auxiliar que lê os dados de todas as abas e retorna um dicionário."""
        dados_finais = {}
        
        # Aba 1
        dados_finais['identificacao_projeto'] = { "nome_projeto": self.input_nome_projeto.text(), "cliente": self.input_cliente.text(), "local_instalacao": self.input_local_instalacao.text(), "empresa_responsavel": self.input_empresa_responsavel.text(), "data_versao": self.input_data_versao.text(), "num_contrato": self.input_num_contrato.text() }
        # Aba 2
        dados_finais['escopo_premissas'] = { "objetivos": self.text_objetivos.toPlainText(), "limites_fornecimento": self.text_limites.toPlainText(), "premissas": self.text_premissas.toPlainText(), "interfaces": self.text_interfaces.toPlainText() }
        # Aba 3
        lista_docs_data = []
        for linha in range(self.tabela_documentos_projeto.rowCount()):
            lista_docs_data.append({ "titulo": self.tabela_documentos_projeto.item(linha, 0).text() if self.tabela_documentos_projeto.item(linha, 0) else "", "codigo": self.tabela_documentos_projeto.item(linha, 1).text() if self.tabela_documentos_projeto.item(linha, 1) else "", "revisao": self.tabela_documentos_projeto.item(linha, 2).text() if self.tabela_documentos_projeto.item(linha, 2) else "", "data": self.tabela_documentos_projeto.item(linha, 3).text() if self.tabela_documentos_projeto.item(linha, 3) else "", "autor": self.tabela_documentos_projeto.item(linha, 4).text() if self.tabela_documentos_projeto.item(linha, 4) else "", "status": self.tabela_documentos_projeto.item(linha, 5).text() if self.tabela_documentos_projeto.item(linha, 5) else "" })
        dados_finais['lista_documentos_projeto'] = lista_docs_data
        # Aba 4
        dados_finais['diagramas_desenhos'] = {"notas": self.text_diagramas_notas.toPlainText()}
        # Aba 5
        lista_instrumentos_data = []
        for linha in range(self.tabela_instrumentos.rowCount()):
            lista_instrumentos_data.append({ "tag": self.tabela_instrumentos.item(linha, 0).text() if self.tabela_instrumentos.item(linha, 0) else "", "descricao": self.tabela_instrumentos.item(linha, 1).text() if self.tabela_instrumentos.item(linha, 1) else "", "fabricante_modelo": self.tabela_instrumentos.item(linha, 2).text() if self.tabela_instrumentos.item(linha, 2) else "", "faixa": self.tabela_instrumentos.item(linha, 3).text() if self.tabela_instrumentos.item(linha, 3) else "", "sinal": self.tabela_instrumentos.item(linha, 4).text() if self.tabela_instrumentos.item(linha, 4) else "", "localizacao": self.tabela_instrumentos.item(linha, 5).text() if self.tabela_instrumentos.item(linha, 5) else "" })
        dados_finais['lista_instrumentos'] = lista_instrumentos_data
        # Aba 7
        lista_programas_data = []
        for linha in range(self.tabela_programacao.rowCount()):
            lista_programas_data.append({ "ficheiro": self.tabela_programacao.item(linha, 0).text() if self.tabela_programacao.item(linha, 0) else "", "descricao": self.tabela_programacao.item(linha, 1).text() if self.tabela_programacao.item(linha, 1) else "" })
        dados_finais['programacao_logica'] = lista_programas_data
        # Aba 8
        dados_finais['testes_comissionamento'] = { "procedimentos": self.text_procedimentos_testes.toPlainText(), "relatorios": self.text_relatorios_testes.toPlainText(), "nao_conformidades": self.text_nao_conformidades.toPlainText() }
        # Aba 9
        dados_operacao = { "procedimentos_manutencao": self.text_procedimentos_manutencao.toPlainText(), "sobressalentes": self.text_sobressalentes.toPlainText() }
        if self.radio_texto_manual.isChecked():
            dados_operacao["manual_tipo"] = "texto"
            dados_operacao["manual_conteudo"] = self.text_manual_operacao.toPlainText()
        else:
            dados_operacao["manual_tipo"] = "pdf"
            dados_operacao["manual_conteudo"] = self.input_caminho_pdf_manual.text()
        dados_finais['operacao_manutencao'] = dados_operacao
        # Aba 10
        lista_participantes_data = []
        for linha in range(self.tabela_participantes.rowCount()):
            lista_participantes_data.append({ "nome": self.tabela_participantes.item(linha, 0).text() if self.tabela_participantes.item(linha, 0) else "", "certificado": self.tabela_participantes.item(linha, 1).text() if self.tabela_participantes.item(linha, 1) else "" })
        dados_finais['treinamento'] = { "programa": self.text_programa_treinamento.toPlainText(), "participantes": lista_participantes_data }
        # Aba 11
        lista_as_built_data = []
        for linha in range(self.tabela_as_built.rowCount()):
            lista_as_built_data.append({ "documento": self.tabela_as_built.item(linha, 0).text() if self.tabela_as_built.item(linha, 0) else "", "notas": self.tabela_as_built.item(linha, 1).text() if self.tabela_as_built.item(linha, 1) else "" })
        dados_finais['documentos_as_built'] = lista_as_built_data
        # Aba 12
        dados_finais['anexos'] = {"descricao": self.text_anexos.toPlainText()}
        return dados_finais

    def avancar_para_anexos(self):
        """Lê os dados do formulário, guarda-os e muda para a tela de anexos."""
        try:
            self.dados_formulario_capturados = self._capturar_dados_do_formulario()
            print("--- DADOS CAPTURADOS ---")
            print(json.dumps(self.dados_formulario_capturados, indent=4, ensure_ascii=False))
            self.stacked_widget_interno.setCurrentWidget(self.widget_anexos)
        except Exception as e:
            QMessageBox.critical(self, "Erro ao Capturar Dados", f"Ocorreu um erro ao ler os dados do formulário: {e}")
            traceback.print_exc()

    def voltar_para_formulario(self):
        """Muda a visualização de volta para o formulário de abas."""
        self.stacked_widget_interno.setCurrentWidget(self.widget_formulario)

    def iniciar_geracao_documento(self, lista_ficheiros_anexos):
        """
        O passo final! Junta tudo e inicia a chamada à API com o novo worker especializado.
        """
        msg_box = QMessageBox(QMessageBox.Icon.Information, "Aguarde", "A gerar o documento no servidor...", buttons=QMessageBox.StandardButton.NoButton, parent=self)
        msg_box.show()
        QApplication.processEvents()
    
        dados_formulario_json_str = json.dumps(self.dados_formulario_capturados)
        
        files_to_upload = []
        for path in lista_ficheiros_anexos:
            try:
                files_to_upload.append(
                    ('anexos', (os.path.basename(path), open(path, 'rb'), 'application/pdf'))
                )
            except Exception as e:
                msg_box.close()
                QMessageBox.critical(self, "Erro de Ficheiro", f"Não foi possível ler o ficheiro: {os.path.basename(path)}\n\n{e}")
                return
    
        # Usamos o novo worker especializado em vez do ApiWorker genérico
        self.thread_geracao = QThread()
        self.worker_geracao = GeracaoDocumentoWorker(
            servico_id=self.servico_id,
            form_data={'dados_formulario': dados_formulario_json_str},
            files_to_upload=files_to_upload
        )
        self.thread_geracao.started.connect(self.worker_geracao.run)
        self.worker_geracao.finished.connect(
            lambda s, d: self.on_geracao_finalizada(s, d, msg_box, files_to_upload)
    )
        self.worker_geracao.finished.connect(self.thread_geracao.quit)
        self.worker_geracao.finished.connect(self.worker_geracao.deleteLater)
        self.thread_geracao.finished.connect(self.thread_geracao.deleteLater)
        self.thread_geracao.start()

    # ==============================================================================
    # MÉTODOS DE CALLBACK (Respostas da API)
    # ==============================================================================
    def on_geracao_finalizada(self, status_code, data, msg_box, files_opened):
        """Callback que é executado quando o back-end termina de gerar o documento."""
        msg_box.close()
    
        # Importante: Fecha todos os ficheiros que foram abertos para o upload
        for _, file_tuple in files_opened:
            file_tuple[1].close()
    
        if status_code == 201:
            QMessageBox.information(self, "Sucesso!", "Documento gerado com sucesso!")
            
            # A SOLUÇÃO ESTÁ AQUI:
            # Usamos um QTimer.singleShot para agendar as próximas ações em vez de as chamar diretamente.
            # Isto garante que a thread anterior terminou completamente antes de iniciarmos novas operações.
            QTimer.singleShot(0, self.carregar_historico)
            QTimer.singleShot(0, self.voltar_para_formulario)
            
        else:
            erro = data.get('erro', 'Ocorreu um erro desconhecido no servidor.')
            QMessageBox.critical(self, "Falha na Geração", f"Não foi possível gerar o documento:\n\n{erro}")


    def carregar_historico(self):
        """Inicia a chamada à API em uma thread para buscar o histórico."""
        self.lista_historico.clear()
        self.lista_historico.addItem("A carregar histórico do servidor...")
        
        self.thread_historico = QThread()
        self.worker_historico = ApiWorker("get", f"/api/servicos/{self.servico_id}/documentos")
        self.worker_historico.moveToThread(self.thread_historico)
        
        # Conexões Corrigidas:
        self.thread_historico.started.connect(self.worker_historico.run)
        self.worker_historico.finished.connect(self.on_carregamento_historico_finished) # O nosso callback
        
        # Padrão de limpeza robusto:
        self.worker_historico.finished.connect(self.thread_historico.quit) # 1. Pede à thread para parar
        self.worker_historico.finished.connect(self.worker_historico.deleteLater) # 2. Agenda o worker para ser apagado PELA SUA PRÓPRIA THREAD
        self.thread_historico.finished.connect(self.thread_historico.deleteLater) # 3. Agenda a thread para ser apagada SÓ DEPOIS de terminar
        
        self.thread_historico.start()

    def on_carregamento_historico_finished(self, status_code, data):
        self.lista_historico.clear()
        if status_code == 200:
            if not data:
                self.lista_historico.addItem("Nenhum documento gerado para este serviço.")
                return
            for doc in data:
                texto_item = f"{doc['data_criacao']} - por {doc['nome_usuario']} - v{doc['versao']}"
                item = QListWidgetItem(texto_item)
                item.setData(Qt.UserRole, doc['id'])
                self.lista_historico.addItem(item)
        else:
            self.lista_historico.addItem("Erro ao carregar histórico.")
            erro = data.get("erro", "Erro desconhecido")
            QMessageBox.warning(self, "Erro de API", f"Não foi possível buscar o histórico: {erro}")

    def on_historico_item_clicado(self, item):
       """Este método é chamado sempre que um item na lista de histórico é clicado."""
       documento_id = item.data(Qt.UserRole)
       if documento_id is None:
           return
           
       print(f"Item clicado! ID do documento: {documento_id}. A buscar detalhes na API...")
       
       self.thread_detalhes = QThread()
       self.worker_detalhes = ApiWorker("get", f"/api/documentos/{documento_id}")
       self.worker_detalhes.moveToThread(self.thread_detalhes)
       
       # Conexões Corrigidas:
       self.thread_detalhes.started.connect(self.worker_detalhes.run)
       self.worker_detalhes.finished.connect(self.on_detalhes_documento_recebidos)
       
       # Padrão de limpeza robusto:
       self.worker_detalhes.finished.connect(self.thread_detalhes.quit)
       self.worker_detalhes.finished.connect(self.worker_detalhes.deleteLater)
       self.thread_detalhes.finished.connect(self.thread_detalhes.deleteLater)
       
       self.thread_detalhes.start()

    def on_detalhes_documento_recebidos(self, status_code, data):
        if status_code == 200:
            dados_identificacao = data.get('identificacao_projeto', {})
            self.input_nome_projeto.setText(dados_identificacao.get('nome_projeto', ''))
            self.input_cliente.setText(dados_identificacao.get('cliente', ''))
            self.input_local_instalacao.setText(dados_identificacao.get('local_instalacao', ''))
            self.input_empresa_responsavel.setText(dados_identificacao.get('empresa_responsavel', ''))
            self.input_data_versao.setText(dados_identificacao.get('data_versao', ''))
            self.input_num_contrato.setText(dados_identificacao.get('num_contrato', ''))
            dados_escopo = data.get('escopo_premissas', {})
            self.text_objetivos.setPlainText(dados_escopo.get('objetivos', ''))
            self.text_limites.setPlainText(dados_escopo.get('limites_fornecimento', ''))
            self.text_premissas.setPlainText(dados_escopo.get('premissas', ''))
            self.text_interfaces.setPlainText(dados_escopo.get('interfaces', ''))
            lista_docs = data.get('lista_documentos_projeto', [])
            self.tabela_documentos_projeto.setRowCount(0)
            for doc in lista_docs:
                linha = self.tabela_documentos_projeto.rowCount()
                self.tabela_documentos_projeto.insertRow(linha)
                self.tabela_documentos_projeto.setItem(linha, 0, QTableWidgetItem(doc.get('titulo', '')))
                self.tabela_documentos_projeto.setItem(linha, 1, QTableWidgetItem(doc.get('codigo', '')))
                self.tabela_documentos_projeto.setItem(linha, 2, QTableWidgetItem(doc.get('revisao', '')))
                self.tabela_documentos_projeto.setItem(linha, 3, QTableWidgetItem(doc.get('data', '')))
                self.tabela_documentos_projeto.setItem(linha, 4, QTableWidgetItem(doc.get('autor', '')))
                self.tabela_documentos_projeto.setItem(linha, 5, QTableWidgetItem(doc.get('status', '')))
            dados_diagramas = data.get('diagramas_desenhos', {})
            self.text_diagramas_notas.setPlainText(dados_diagramas.get('notas', ''))
            lista_instrumentos = data.get('lista_instrumentos', [])
            self.tabela_instrumentos.setRowCount(0)
            for inst in lista_instrumentos:
                linha = self.tabela_instrumentos.rowCount()
                self.tabela_instrumentos.insertRow(linha)
                self.tabela_instrumentos.setItem(linha, 0, QTableWidgetItem(inst.get('tag', '')))
                self.tabela_instrumentos.setItem(linha, 1, QTableWidgetItem(inst.get('descricao', '')))
                self.tabela_instrumentos.setItem(linha, 2, QTableWidgetItem(inst.get('fabricante_modelo', '')))
                self.tabela_instrumentos.setItem(linha, 3, QTableWidgetItem(inst.get('faixa', '')))
                self.tabela_instrumentos.setItem(linha, 4, QTableWidgetItem(inst.get('sinal', '')))
                self.tabela_instrumentos.setItem(linha, 5, QTableWidgetItem(inst.get('localizacao', '')))
            dados_programacao = data.get('programacao_logica', {})
            # Lógica para preencher tabela de programação aqui...
            dados_testes = data.get('testes_comissionamento', {})
            self.text_procedimentos_testes.setPlainText(dados_testes.get('procedimentos', ''))
            self.text_relatorios_testes.setPlainText(dados_testes.get('relatorios', ''))
            self.text_nao_conformidades.setPlainText(dados_testes.get('nao_conformidades', ''))
            dados_operacao = data.get('operacao_manutencao', {})
            self.text_procedimentos_manutencao.setPlainText(dados_operacao.get('procedimentos_manutencao', ''))
            self.text_sobressalentes.setPlainText(dados_operacao.get('sobressalentes', ''))
            if dados_operacao.get('manual_tipo') == 'pdf':
                self.radio_pdf_manual.setChecked(True)
                self.input_caminho_pdf_manual.setText(dados_operacao.get('manual_conteudo', ''))
            else:
                self.radio_texto_manual.setChecked(True)
                self.text_manual_operacao.setPlainText(dados_operacao.get('manual_conteudo', ''))
            dados_treinamento = data.get('treinamento', {})
            self.text_programa_treinamento.setPlainText(dados_treinamento.get('programa', ''))
            lista_participantes = dados_treinamento.get('participantes', [])
            self.tabela_participantes.setRowCount(0)
            for p in lista_participantes:
                linha = self.tabela_participantes.rowCount()
                self.tabela_participantes.insertRow(linha)
                self.tabela_participantes.setItem(linha, 0, QTableWidgetItem(p.get('nome', '')))
                self.tabela_participantes.setItem(linha, 1, QTableWidgetItem(p.get('certificado', '')))
            dados_as_built = data.get('documentos_as_built', {})
            # Lógica para preencher tabela as_built aqui...
            dados_anexos = data.get('anexos', {})
            self.text_anexos.setPlainText(dados_anexos.get('descricao', ''))
            QMessageBox.information(self, "Sucesso", "Dados do documento carregados no formulário!")
        else:
            QMessageBox.critical(self, "Erro de API", "Não foi possível carregar os detalhes deste documento.")

class DropArea(QLabel):
    """Um QLabel personalizado que aceita ficheiros arrastados e soltos."""
    filesDropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setText("\nArraste e solte os ficheiros PDF dos Anexos aqui\n(até 5 ficheiros)")
        self.setStyleSheet("""
            DropArea {
                border: 2px dashed #888888;
                border-radius: 8px;
                font-size: 18px;
                color: #555555;
            }
            DropArea:hover {
                border-color: #0078d7;
                background-color: #f0f8ff;
            }
        """)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = [url.toLocalFile() for url in event.mimeData().urls()]
        pdf_files = [url for url in urls if url.lower().endswith('.pdf')]
        if pdf_files:
            self.filesDropped.emit(pdf_files)


class GeracaoDocumentoWorker(QObject):  
    """Um worker especializado apenas para a tarefa de gerar o documento final."""
    finished = Signal(int, dict)

    def __init__(self, servico_id, form_data, files_to_upload):
        super().__init__()
        self.servico_id = servico_id
        self.form_data = form_data
        self.files_to_upload = files_to_upload

    def run(self):
        global access_token, API_BASE_URL
        headers = {'Authorization': f'Bearer {access_token}'}
        url = f"{API_BASE_URL}/api/servicos/{self.servico_id}/documentos"

        try:
            # Esta é a chamada requests mais direta e explícita possível
            response = requests.post(
                url, 
                headers=headers, 
                data=self.form_data, 
                files=self.files_to_upload, 
                timeout=60 # Timeout maior para uploads
            )
            data = response.json() if response.content else {}
            self.finished.emit(response.status_code, data)
        except Exception as e:
            traceback.print_exc() # Imprime o erro detalhado no terminal
            self.finished.emit(-2, {"erro": str(e)})

class AnexosWidget(QWidget):
    """A tela para fazer o upload dos ficheiros de anexo."""
    # Sinais para comunicar com o widget principal (DocumentacaoWidget)
    voltar_solicitado = Signal()
    gerar_documento_solicitado = Signal(list) # Emite a lista final de caminhos de ficheiros

    def __init__(self):
        super().__init__()
        self.caminhos_ficheiros = []
        
        layout = QVBoxLayout(self)
        
        # Área de Drag-and-Drop
        self.drop_area = DropArea()
        self.drop_area.filesDropped.connect(self.adicionar_ficheiros)
        
        # Lista para exibir os ficheiros adicionados
        self.lista_ficheiros = QListWidget()
        
        # Botões de Ação
        layout_botoes = QHBoxLayout()
        btn_voltar = QPushButton("< Voltar ao Formulário")
        btn_gerar = QPushButton("🚀 Gerar Documento Final")
        btn_gerar.setObjectName("btnPositive")

        btn_voltar.clicked.connect(self.voltar_solicitado.emit)
        btn_gerar.clicked.connect(self.on_gerar_clicado)

        layout_botoes.addWidget(btn_voltar)
        layout_botoes.addStretch(1)
        layout_botoes.addWidget(btn_gerar)
        
        layout.addWidget(self.drop_area, 1) # Ocupa mais espaço
        layout.addWidget(QLabel("Ficheiros Anexados:"))
        layout.addWidget(self.lista_ficheiros, 1)
        layout.addLayout(layout_botoes)

    def adicionar_ficheiros(self, novos_ficheiros):
        for ficheiro in novos_ficheiros:
            if ficheiro not in self.caminhos_ficheiros:
                self.caminhos_ficheiros.append(ficheiro)
                item = QListWidgetItem(f"📄 {os.path.basename(ficheiro)}")
                item.setData(Qt.UserRole, ficheiro) # Guarda o caminho completo
                self.lista_ficheiros.addItem(item)
        
    def on_gerar_clicado(self):
        # Emite o sinal com a lista de caminhos de ficheiros para o widget pai processar
        self.gerar_documento_solicitado.emit(self.caminhos_ficheiros)


    
# ==============================================================================
# 5. CLASSE DA JANELA PRINCIPAL
# ==============================================================================

class JanelaPrincipal(QMainWindow):
    logoff_requested = Signal()

    def __init__(self):
        super().__init__()
        
        try:
            self.setWindowTitle("Sistema de Gestão de Estoque")
            self.resize(1280, 720)
        
            self.dados_usuario = {}
        
            # --- ÁREA DE CONTEÚDO ---
            self.stacked_widget = QStackedWidget()
            self.stacked_widget.setObjectName("mainContentArea")
            
            self.tela_dashboard = DashboardWidget()
            self.tela_gestao_estoque = GestaoEstoqueWidget()
            self.tela_entrada_rapida = EntradaRapidaWidget()
            self.tela_saida_rapida = SaidaRapidaWidget()
            self.tela_relatorios = RelatoriosWidget()
            self.tela_fornecedores = FornecedoresWidget()
            self.tela_naturezas = NaturezasWidget()
            self.tela_usuarios = None
            self.tela_importacao = ImportacaoWidget()
            self.tela_terminal = TerminalWidget()
            self.tela_documentacao_servico_1 = None
    
            self.stacked_widget.addWidget(self.tela_dashboard)
            self.stacked_widget.addWidget(self.tela_gestao_estoque)
            self.stacked_widget.addWidget(self.tela_entrada_rapida)
            self.stacked_widget.addWidget(self.tela_saida_rapida)
            self.stacked_widget.addWidget(self.tela_relatorios)
            self.stacked_widget.addWidget(self.tela_fornecedores)
            self.stacked_widget.addWidget(self.tela_naturezas)
            self.stacked_widget.addWidget(self.tela_importacao)
            self.stacked_widget.addWidget(self.tela_terminal)
        
            # --- BARRA DE MENUS ---
            menu_bar = self.menuBar()
            
            menu_arquivo = menu_bar.addMenu("&Arquivo")
            acao_dashboard = QAction("Dashboard", self)
            acao_dashboard.setShortcut("Ctrl+D")
            acao_dashboard.triggered.connect(self.mostrar_tela_dashboard)
            menu_arquivo.addAction(acao_dashboard)
            menu_arquivo.addSeparator()
            # --- NOVO CÓDIGO AQUI ---
            self.acao_trocar_tema = QAction("Mudar para Tema Escuro", self)
            self.acao_trocar_tema.triggered.connect(self.trocar_tema)
            menu_arquivo.addAction(self.acao_trocar_tema)
            # --- FIM DO NOVO CÓDIGO ---
            self.acao_mudar_senha = QAction("Alterar Minha Senha...", self)
            self.acao_mudar_senha.triggered.connect(self.abrir_dialogo_mudar_senha)
            menu_arquivo.addAction(self.acao_mudar_senha)
            menu_arquivo.addSeparator()
            acao_logoff = QAction("Fazer Logoff", self)
            acao_logoff.triggered.connect(self.logoff_requested.emit)
            menu_arquivo.addAction(acao_logoff)
            acao_sair = QAction("Sair", self)
            acao_sair.setShortcut(QKeySequence.Quit)
            acao_sair.triggered.connect(self.close)
            menu_arquivo.addAction(acao_sair)
    
            self.menu_cadastros = menu_bar.addMenu("&Cadastros")
            self.acao_produtos = QAction("Inventário...", self)
            self.acao_produtos.setShortcut("Ctrl+P")
            self.acao_produtos.triggered.connect(self.mostrar_tela_gestao_estoque)
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
            menu_operacoes.addSeparator() # Adiciona uma linha a separar
            acao_doc_teste = QAction("Documentação (Pedro Emo)", self)
            acao_doc_teste.triggered.connect(self.mostrar_tela_documentacao_teste)
            menu_operacoes.addAction(acao_doc_teste)
            acao_saida = QAction("Saída Rápida de Estoque...", self)
            acao_saida.setShortcut("Ctrl+S")
            acao_saida.triggered.connect(self.mostrar_tela_saida_rapida)
            menu_operacoes.addAction(acao_saida)
            menu_operacoes.addSeparator()
            acao_saldos = QAction("Consultar Inventário...", self)
            acao_saldos.triggered.connect(self.mostrar_tela_gestao_estoque)
            menu_operacoes.addAction(acao_saldos)
            acao_historico = QAction("Ver Histórico de Movimentações...", self)
            acao_historico.triggered.connect(lambda: (self.mostrar_tela_gestao_estoque(), self.tela_gestao_estoque.mostrar_historico()))
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
            self.btn_inventario = QPushButton("📦 Inventário")
            self.btn_terminal = QPushButton("🛰️ Terminal")
            self.btn_entrada_rapida = QPushButton("➡️ Entrada Rápida")
            self.btn_saida_rapida = QPushButton("⬅️ Saída Rápida")
            self.btn_relatorios = QPushButton("📄 Relatórios")
            self.btn_fornecedores = QPushButton("🚚 Fornecedores")
            self.btn_naturezas = QPushButton("🌿 Naturezas")
            self.btn_usuarios = QPushButton("👥 Usuários")
            self.btn_logoff = QPushButton("🚪 Fazer Logoff")
            self.btn_logoff.setObjectName("btnLogoff")
    
            self.layout_painel_lateral.addWidget(self.btn_dashboard)
            self.layout_painel_lateral.addWidget(self.btn_inventario)
            self.layout_painel_lateral.addWidget(self.btn_terminal)
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
            self.btn_inventario.clicked.connect(self.mostrar_tela_gestao_estoque)
            self.btn_terminal.clicked.connect(self.mostrar_tela_terminal)
            self.btn_entrada_rapida.clicked.connect(self.mostrar_tela_entrada_rapida)
            self.btn_saida_rapida.clicked.connect(self.mostrar_tela_saida_rapida)
            self.btn_relatorios.clicked.connect(self.mostrar_tela_relatorios)
            self.btn_fornecedores.clicked.connect(self.mostrar_tela_fornecedores)
            self.btn_naturezas.clicked.connect(self.mostrar_tela_naturezas)
            self.btn_logoff.clicked.connect(self.logoff_requested.emit)
            
            self.tela_dashboard.ir_para_produtos.connect(self.mostrar_tela_gestao_estoque)
            self.tela_dashboard.ir_para_fornecedores.connect(self.mostrar_tela_fornecedores)
            self.tela_dashboard.ir_para_terminal.connect(self.mostrar_tela_terminal)
            self.tela_dashboard.ir_para_entrada_rapida.connect(self.mostrar_tela_entrada_rapida)
            self.tela_dashboard.ir_para_saida_rapida.connect(self.mostrar_tela_saida_rapida)
            self.tela_terminal.ir_para_novo_produto.connect(self.abrir_formulario_novo_produto)
            # --- A LINHA ABAIXO FOI REMOVIDA PARA CORRIGIR O ERRO ---
            # self.tela_gestao_estoque.inventario_view.novo_produto_adicionado.connect(self.tela_terminal.reprocessar_codigo_apos_modificacao)
            self.tela_entrada_rapida.estoque_atualizado.connect(self.tela_gestao_estoque.inventario_view.carregar_dados_inventario)
            self.tela_saida_rapida.estoque_atualizado.connect(self.tela_gestao_estoque.inventario_view.carregar_dados_inventario)
            self.tela_importacao.produtos_importados_sucesso.connect(self.tela_gestao_estoque.inventario_view.carregar_dados_inventario)
            signal_handler.fornecedores_atualizados.connect(self.tela_fornecedores.carregar_fornecedores)
            signal_handler.naturezas_atualizadas.connect(self.tela_naturezas.carregar_naturezas)
    
            self.statusBar().showMessage("Pronto.")
    
        except Exception:
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            log_file = os.path.join(desktop, "crash_log.txt")
            with open(log_file, "w", encoding="utf-8") as f:
                f.write("Ocorreu um erro crítico ao iniciar a JanelaPrincipal:\n\n")
                f.write(traceback.format_exc())
            QMessageBox.critical(None, "Erro Crítico", f"A aplicação encontrou um erro fatal ao iniciar. Verifique o ficheiro 'crash_log.txt' no seu Ambiente de Trabalho.")
            sys.exit(1)


    # --- MÉTODO CORRIGIDO E ADICIONADO ---
    def abrir_formulario_novo_produto(self):
        """Muda para a tela de inventário e abre o formulário de novo produto."""
        self.mostrar_tela_gestao_estoque()
        # Chama o método que abre o formulário na tela de inventário
        self.tela_gestao_estoque.inventario_view.abrir_formulario_adicionar()
      
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
        nome_utilizador = self.dados_usuario.get('nome', 'Utilizador')
        self.tela_dashboard.carregar_dados_dashboard(nome_utilizador)
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
        dialog = SobreDialog(self)
        dialog.exec()
    def mostrar_tela_importacao(self):
        self.stacked_widget.setCurrentWidget(self.tela_importacao)
    def mostrar_tela_gestao_estoque(self):
        self.stacked_widget.setCurrentWidget(self.tela_gestao_estoque)
        self.tela_gestao_estoque.mostrar_inventario()
    def abrir_dialogo_mudar_senha(self):
        dialog = MudarSenhaDialog(self)
        dialog.exec()
    def mostrar_tela_terminal(self):
        self.stacked_widget.setCurrentWidget(self.tela_terminal)
        self.tela_terminal.setFocus()
    def trocar_tema(self):
        """Alterna entre o tema claro e escuro."""
        settings = QSettings("SuaEmpresa", "GestaoEstoque")
        
        # Determina o novo tema
        novo_tema = "dark" if CURRENT_THEME == "light" else "light"
        
        # Carrega e aplica o novo estilo
        novo_estilo = load_stylesheet(novo_tema)
        QApplication.instance().setStyleSheet(novo_estilo)
        
        # Atualiza o texto da ação do menu
        texto_acao = "Mudar para Tema Claro" if novo_tema == "dark" else "Mudar para Tema Escuro"
        self.acao_trocar_tema.setText(texto_acao)
        
        # Salva a nova preferência
        settings.setValue("theme", novo_tema)
        print(f"Tema alterado para: {novo_tema}")
    def mostrar_tela_documentacao_teste(self):
        """Cria (se necessário) e exibe a tela de documentação para o serviço de teste."""
        servico_id_teste = 1
        
        # Lógica para criar a tela apenas uma vez e reutilizá-la
        if self.tela_documentacao_servico_1 is None:
            print(f"A criar widget de documentação para o serviço ID: {servico_id_teste}")
            self.tela_documentacao_servico_1 = DocumentacaoWidget(servico_id=servico_id_teste)
            self.stacked_widget.addWidget(self.tela_documentacao_servico_1)
        
        # Define a nova tela como a tela ativa
        self.stacked_widget.setCurrentWidget(self.tela_documentacao_servico_1)

class SobreDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sobre o Sistema")
        self.setMinimumWidth(400)
        self.click_count = 0
        self.sound_effect = QSoundEffect()
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.setSpacing(15)
        self.logo_label = QLabel()
        logo_pixmap = QPixmap(resource_path("logo2.png"))
        logo_redimensionada = logo_pixmap.scaled(150, 90, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.logo_label.setPixmap(logo_redimensionada)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_label.setToolTip("Hmmm, o que será que acontece se clicar aqui várias vezes?")
        self.logo_label.installEventFilter(self)
        info_text = QLabel(
            """
            <b>Sistema de Gestão de Estoque v2.3D</b>
            <p>Versão 11-09-2025 Especial(Gerador de Documento)</p>
            <p>Desenvolvido por Matheus com Google Gemini :D.</p>
            <p>Desenvolvido para controle de estoque na Szm.</p>
            <p><b>Tecnologias:</b> Python, PySide6, Flask, SQLAlchemy.</p>
            <p>Versão Especial com Editor de Documentos</p>
            """
        )
        info_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_text.setWordWrap(True)
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.layout.addWidget(self.logo_label)
        self.layout.addWidget(info_text)
        self.layout.addWidget(self.ok_button, 0, Qt.AlignmentFlag.AlignCenter)
    def eventFilter(self, source, event):
        if source is self.logo_label and event.type() == QEvent.Type.MouseButtonPress:
            self.click_count += 1
            print(f"Logo clicada {self.click_count} vezes.")
            if self.click_count == 10:
                print("Easter Egg Ativado!")
                self.tocar_musica()
                self.click_count = 0
            return True
        return super().eventFilter(source, event)
    def tocar_musica(self):
        try:
            self.sound_effect.setSource(QUrl.fromLocalFile(resource_path("easter_egg.wav")))
            self.sound_effect.setVolume(0.8)
            self.sound_effect.play()
            print("A tocar o ficheiro de áudio easter_egg.wav")
        except Exception as e:
            print(f"Não foi possível tocar o som: {e}")

class InteractiveKPICard(QFrame):
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
        self.clicked.emit()
        super().mouseReleaseEvent(event)

class DashboardWidget(QWidget):
    ir_para_produtos = Signal()
    ir_para_fornecedores = Signal()
    ir_para_entrada_rapida = Signal()
    ir_para_saida_rapida = Signal()
    ir_para_terminal = Signal()
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.layout.setContentsMargins(30, 20, 30, 20)
        self.layout.setSpacing(25)
        self.lista_curiosidades = [
            "A Cidade do Vaticano é o menor país do mundo.",
            "O mel nunca se estraga.",
            "As formigas descansam cerca de 8 minutos a cada 12 horas.",
            "O olho de um avestruz é maior que seu cérebro.",
            "Os polvos têm três corações.",
            "A Grande Muralha da China não é visível da Lua a olho nu.",
            "O som não se propaga no vácuo.",
            "O Brasil tem a maior biodiversidade do mundo.",
            "As borboletas sentem o sabor com os pés.",
            "Um raio é cinco vezes mais quente que a superfície do Sol.",
            "Seu coração bate cerca de 100.000 vezes por dia.",
            "A preguiça pode levar um mês para digerir uma folha.",
            "O Oceano Pacífico é o maior e mais profundo do mundo.",
            "A Torre Eiffel pode ser 15 cm mais alta no verão.",
            "Os camelos têm três pálpebras para se proteger da areia.",
            "As girafas têm a língua azul para evitar queimaduras solares.",
            "O corpo humano tem mais de 600 músculos.",
            "Dedo no cu e gritaria. ~Rogério Skylab, Matador de passarinho."
            
            
        ]
        welcome_card = QFrame()
        welcome_card.setObjectName("welcomeCard")
        welcome_layout = QHBoxLayout(welcome_card)
        logo_label = QLabel()
        logo_pixmap = QPixmap(resource_path("logo.png"))
        logo_redimensionada = logo_pixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        logo_label.setPixmap(logo_redimensionada)
        message_layout = QVBoxLayout()
        self.label_boas_vindas = QLabel("Bem-vindo(a)!")
        self.label_boas_vindas.setObjectName("welcomeMessage")
        self.label_curiosidade = QLabel("Você sabia que...")
        self.label_curiosidade.setObjectName("curiosityMessage")
        self.label_curiosidade.setWordWrap(True)
        message_layout.addWidget(self.label_boas_vindas)
        message_layout.addWidget(self.label_curiosidade)
        welcome_layout.addWidget(logo_label)
        welcome_layout.addLayout(message_layout)
        welcome_layout.addStretch(1)
        kpi_title = QLabel("Resumo do Sistema")
        kpi_title.setObjectName("dashboardSectionTitle")
        action_title = QLabel("Operações Comuns")
        action_title.setObjectName("dashboardSectionTitle")
        kpi_layout = QHBoxLayout()
        self.card_produtos = InteractiveKPICard("Produtos", icone="📦")
        self.card_fornecedores = InteractiveKPICard("Fornecedores", icone="🚚")
        self.card_valor_estoque = InteractiveKPICard("Valor do Estoque (R$)", icone="💰")
        kpi_layout.addWidget(self.card_produtos)
        kpi_layout.addWidget(self.card_fornecedores)
        kpi_layout.addWidget(self.card_valor_estoque)
        action_layout = QHBoxLayout()
        self.btn_atalho_entrada = QPushButton("➡️\n\nNova Entrada")
        self.btn_atalho_entrada.setObjectName("btnDashboardAction")
        self.btn_atalho_saida = QPushButton("⬅️\n\nNova Saída")
        self.btn_atalho_saida.setObjectName("btnDashboardAction")
        self.btn_atalho_terminal = QPushButton("🛰️\n\nTerminal de Consulta")
        self.btn_atalho_terminal.setObjectName("btnDashboardAction")
        action_layout.addWidget(self.btn_atalho_entrada)
        action_layout.addWidget(self.btn_atalho_saida)
        action_layout.addWidget(self.btn_atalho_terminal)
        self.layout.addWidget(welcome_card)
        self.layout.addWidget(kpi_title)
        self.layout.addLayout(kpi_layout)
        self.layout.addWidget(action_title)
        self.layout.addLayout(action_layout)
        self.layout.addStretch(1)
        self.card_produtos.clicked.connect(self.ir_para_produtos.emit)
        self.card_fornecedores.clicked.connect(self.ir_para_fornecedores.emit)
        self.btn_atalho_entrada.clicked.connect(self.ir_para_entrada_rapida.emit)
        self.btn_atalho_saida.clicked.connect(self.ir_para_saida_rapida.emit)
        self.btn_atalho_terminal.clicked.connect(self.ir_para_terminal.emit)
    def atualizar_mensagem_boas_vindas(self, nome_utilizador):
        primeiro_nome = nome_utilizador.split(" ")[0]
        curiosidade = random.choice(self.lista_curiosidades)
        self.label_boas_vindas.setText(f"Bem-vindo(a), {primeiro_nome}!")
        self.label_curiosidade.setText(f"<i>Você sabia que... {curiosidade}</i>")
    def carregar_dados_dashboard(self, nome_utilizador):
        self.atualizar_mensagem_boas_vindas(nome_utilizador)
        self.carregar_kpis()
    def carregar_kpis(self):
        global access_token
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get(f"{API_BASE_URL}/api/dashboard/kpis", headers=headers, timeout=5)
            if response and response.status_code == 200:
                dados = response.json()
                self.card_produtos.set_valor(dados.get('total_produtos', 0))
                self.card_fornecedores.set_valor(dados.get('total_fornecedores', 0))
                valor_formatado = f"R$ {dados.get('valor_total_estoque', 0):.2f}".replace('.', ',')
                self.card_valor_estoque.set_valor(valor_formatado)
        except requests.exceptions.RequestException:
            show_connection_error_message(self)

# ==============================================================================
# 6. CLASSE DA JANELA DE LOGIN
# ==============================================================================

class AppManager:
    def __init__(self):
        self.login_window = None
        self.main_window = None
    def start(self):
        self.show_login_window()
    def show_login_window(self):
        self.login_window = JanelaLogin()
        self.login_window.login_successful.connect(self.show_main_window)
        self.login_window.show()
    def show_main_window(self, user_data):
        self.main_window = JanelaPrincipal()
        self.main_window.carregar_dados_usuario(user_data)
        self.main_window.show()
        self.main_window.mostrar_tela_dashboard()
        self.main_window.logoff_requested.connect(self.handle_logoff)
        self.login_window.close()
        check_for_updates()
    def handle_logoff(self):
        if self.main_window:
            self.main_window.close()
        self.show_login_window()

class JanelaLogin(QMainWindow):
    """Uma tela de login profissional em ecrã completo, inspirada no design moderno."""
    login_successful = Signal(dict)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema de Gestão de Estoque - Acesso")
        # O ícone será definido pelo AppManager ou pelo estilo global

        # --- Estrutura Principal ---
        widget_central = QWidget()
        self.setCentralWidget(widget_central)
        layout_principal = QHBoxLayout(widget_central)
        layout_principal.setContentsMargins(0, 0, 0, 0)
        layout_principal.setSpacing(0)

        # --- PAINEL ESQUERDO (Branding/Visual) ---
        painel_esquerdo = QFrame()
        painel_esquerdo.setObjectName("loginLeftPanel")
        layout_esquerdo = QVBoxLayout(painel_esquerdo)
        layout_esquerdo.setContentsMargins(50, 50, 50, 50)
        layout_esquerdo.setAlignment(Qt.AlignmentFlag.AlignCenter)

        logo_label = QLabel()
        logo_pixmap = QPixmap(resource_path("logo.png"))
        # Usamos um tamanho maior para a logo aqui
        logo_redimensionada = logo_pixmap.scaled(300, 200, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        logo_label.setPixmap(logo_redimensionada)
        
        titulo_branding = QLabel("Sistema de Gestão de Estoque")
        titulo_branding.setObjectName("loginBrandingTitle")
        
        subtitulo_branding = QLabel("Entrada / Saida e Relatórios de Estoque.")
        subtitulo_branding.setObjectName("loginBrandingSubtitle")

        layout_esquerdo.addWidget(logo_label)
        layout_esquerdo.addWidget(titulo_branding)
        layout_esquerdo.addWidget(subtitulo_branding)
        layout_esquerdo.addStretch(1) # Empurra o conteúdo para o centro

        # --- PAINEL DIREITO (Formulário) ---
        painel_direito = QFrame()
        painel_direito.setObjectName("loginRightPanel")
        layout_direito_container = QVBoxLayout(painel_direito)
        layout_direito_container.setAlignment(Qt.AlignmentFlag.AlignCenter)

        form_frame = QFrame()
        form_frame.setObjectName("loginFormFrame")
        form_layout = QVBoxLayout(form_frame)
        form_layout.setSpacing(15)

        titulo_login = QLabel("LOGIN")
        titulo_login.setObjectName("loginTitle")

        self.input_login = QLineEdit()
        self.input_login.setPlaceholderText("O seu login de utilizador")
        self.input_login.setObjectName("loginInput")

        self.input_senha = QLineEdit()
        self.input_senha.setPlaceholderText("••••••••")
        self.input_senha.setEchoMode(QLineEdit.EchoMode.Password)
        self.input_senha.setObjectName("loginInput")

        self.botao_login = QPushButton("Entrar")
        self.botao_login.setObjectName("loginButton")

        form_layout.addWidget(titulo_login)
        form_layout.addWidget(QLabel("Utilizador"))
        form_layout.addWidget(self.input_login)
        form_layout.addWidget(QLabel("Senha"))
        form_layout.addWidget(self.input_senha)
        form_layout.addWidget(self.botao_login)

        layout_direito_container.addWidget(form_frame)

        # Adiciona os painéis ao layout principal
        layout_principal.addWidget(painel_esquerdo, 2) # Proporção 2 (mais largo)
        layout_principal.addWidget(painel_direito, 3) # Proporção 3

        # Conexões
        self.botao_login.clicked.connect(self.fazer_login)
        self.input_senha.returnPressed.connect(self.botao_login.click)

    def showEvent(self, event):
        """Mostra a janela maximizada quando ela é exibida."""
        self.showMaximized()
        super().showEvent(event)

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
            response = requests.post(url, json=dados, timeout=10)
            if response and response.status_code == 200:
                access_token = response.json()['access_token']
                print("Login bem-sucedido! Token guardado.")
                
                headers = {'Authorization': f'Bearer {access_token}'}
                url_me = f"{API_BASE_URL}/api/usuario/me"
                response_me = requests.get(url_me, headers=headers)
                
                dados_usuario_logado = response_me.json() if response_me.status_code == 200 else {'nome': 'Desconhecido', 'permissao': 'Usuario'}
                
                self.login_successful.emit(dados_usuario_logado)
                self.close()
            else:
                erro_msg = response.json().get('erro', 'Credenciais inválidas.')
                QMessageBox.warning(self, "Falha no Login", erro_msg)
        except requests.exceptions.RequestException:
            show_connection_error_message(self)


# ==============================================================================
# 7. BLOCO DE EXECUÇÃO PRINCIPAL
# ==============================================================================
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # --- LÓGICA DE TEMA AQUI ---
    # Define um nome para a sua empresa e aplicação para o QSettings
    settings = QSettings("SuaEmpresa", "GestaoEstoque") 
    
    # Lê o tema salvo, usando 'light' como padrão se nada for encontrado
    saved_theme = settings.value("theme", "light") 
    
    # Carrega o estilo inicial baseado na preferência salva
    initial_stylesheet = load_stylesheet(saved_theme)
    app.setStyleSheet(initial_stylesheet)
    # --- FIM DA LÓGICA DE TEMA ---

    manager = AppManager()
    manager.start()

    # Atualiza o texto do botão de tema na janela principal após ela ser criada
    if manager.main_window:
        texto_acao = "Mudar para Tema Claro" if saved_theme == "dark" else "Mudar para Tema Escuro"
        manager.main_window.acao_trocar_tema.setText(texto_acao)

    sys.exit(app.exec())