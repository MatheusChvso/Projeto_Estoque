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
    Qt, QTimer, Signal, QDate, QEvent, QObject
)
import winsound
import threading
from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtCore import QUrl
import threading
import json
import random

import webbrowser
from packaging.version import parse as parse_version

from config import SERVER_IP

# ==============================================================================
# 2. FUNÇÕES AUXILIARES E VARIÁVEIS GLOBAIS
# ==============================================================================
access_token = None
API_BASE_URL = f"http://{SERVER_IP}:5000"
APP_VERSION = "2.2" #27/08/2025

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

def check_for_updates():
    """Contacta a API para verificar se existe uma nova versão da aplicação."""
    print("A verificar atualizações...")
    try:
        global access_token
        headers = {'Authorization': f'Bearer {access_token}'}
        # Usamos a rota que já criámos no app.py
        response = requests.get(f"{API_BASE_URL}/api/versao", headers=headers, timeout=5)

        if response.status_code == 200:
            dados_versao = response.json()
            versao_servidor = dados_versao.get("versao")
            url_download = dados_versao.get("url_download")

            # Compara as versões usando a biblioteca packaging
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
            # --- CORREÇÃO AQUI: Mostra um erro se a API falhar ---
            print(f"Não foi possível verificar a versão. Erro da API: {response.status_code}")
            QMessageBox.warning(None, "Verificação de Versão", f"Não foi possível contactar o servidor de atualizações (Erro: {response.status_code}).")

    except Exception as e:
        # --- CORREÇÃO AQUI: Mostra um erro para qualquer outra falha ---
        print(f"Ocorreu um erro ao verificar atualizações: {e}")
        QMessageBox.critical(None, "Erro na Verificação de Versão", f"Ocorreu um erro inesperado ao tentar verificar por novas versões:\n\n{e}")

# ==============================================================================
# 3. JANELAS DE DIÁLOGO (FORMULÁRIOS)
# ==============================================================================

class FormularioProdutoDialog(QDialog):
    """Janela de formulário para Adicionar ou Editar um Produto."""
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
        
        self.carregar_dados_iniciais()

    def carregar_dados_iniciais(self):
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
            if response_forn and response_forn.status_code == 200:
                for forn in response_forn.json():
                    item = QListWidgetItem(forn['nome'])
                    item.setData(Qt.UserRole, forn['id'])
                    self.lista_fornecedores.addItem(item)
            
            url_nat = f"{API_BASE_URL}/api/naturezas"
            response_nat = requests.get(url_nat, headers=headers)
            if response_nat and response_nat.status_code == 200:
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
            if response and response.status_code == 200:
                dados = response.json()
                self.input_codigo.setText(dados.get('codigo', ''))
                self.input_nome.setText(dados.get('nome', ''))
                self.input_descricao.setText(dados.get('descricao', ''))
                self.input_preco.setText(str(dados.get('preco', '0.00')))
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
        
        if not nome or not codigo:
            QMessageBox.warning(self, "Campos Obrigatórios", "Por favor, preencha os campos: Código e Nome.")
            return
        
        global access_token
        headers = {'Authorization': f'Bearer {access_token}'}
        
        preco_str = self.input_preco.text().strip().replace(',', '.')
        
        dados_produto = {
            "codigo": codigo, 
            "nome": nome, 
            "preco": preco_str if preco_str else "0.00",
            "descricao": self.input_descricao.text(),
            "codigoB": self.input_codigoB.text(), 
            "codigoC": self.input_codigoC.text()
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
                if not response_produto or response_produto.status_code != 201:
                    raise Exception(response_produto.json().get('erro', 'Erro ao criar produto'))
                
                produto_salvo_id = response_produto.json().get('id_produto_criado')
                dados_produto['fornecedores_ids'] = ids_fornecedores_selecionados
                dados_produto['naturezas_ids'] = ids_naturezas_selecionadas
                url_update = f"{API_BASE_URL}/api/produtos/{produto_salvo_id}"
                response_update = requests.put(url_update, headers=headers, json=dados_produto)

                if not response_update or response_update.status_code != 200:
                    raise Exception(response_update.json().get('erro', 'Produto criado, mas falha ao salvar associações'))
                super().accept()
            else:
                dados_produto['fornecedores_ids'] = ids_fornecedores_selecionados
                dados_produto['naturezas_ids'] = ids_naturezas_selecionadas
                
                url = f"{API_BASE_URL}/api/produtos/{self.produto_id}"
                response = requests.put(url, headers=headers, json=dados_produto)

                if not response or response.status_code != 200:
                    raise Exception(response.json().get('erro', 'Erro ao atualizar produto'))

                dados_atualizados = response.json()
                self.produto_atualizado.emit(self.row, dados_atualizados)
                QMessageBox.information(self, "Sucesso", "Produto atualizado com sucesso!")
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
                if self.endpoint == "/api/fornecedores":
                    signal_handler.fornecedores_atualizados.emit()
                elif self.endpoint == "/api/naturezas":
                    signal_handler.naturezas_atualizadas.emit()
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

class MudarSenhaDialog(QDialog):
    """Janela de formulário para o utilizador alterar a sua própria senha."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Alterar Minha Senha")
        self.setMinimumWidth(350)

        self.layout = QFormLayout(self)
        self.layout.setSpacing(15)

        # --- Campos de Entrada ---
        self.input_senha_atual = QLineEdit()
        self.input_senha_atual.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.input_nova_senha = QLineEdit()
        self.input_nova_senha.setEchoMode(QLineEdit.EchoMode.Password)
        
        self.input_confirmacao = QLineEdit()
        self.input_confirmacao.setEchoMode(QLineEdit.EchoMode.Password)

        self.layout.addRow("Senha Atual:", self.input_senha_atual)
        self.layout.addRow("Nova Senha:", self.input_nova_senha)
        self.layout.addRow("Confirmar Nova Senha:", self.input_confirmacao)

        # --- Botões ---
        self.botoes = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.layout.addWidget(self.botoes)

        # --- Conexões ---
        self.botoes.accepted.connect(self.accept)
        self.botoes.rejected.connect(self.reject)
        # Permite submeter com Enter no último campo
        self.input_confirmacao.returnPressed.connect(self.accept)

    def accept(self):
        """Valida os dados e envia o pedido à API."""
        senha_atual = self.input_senha_atual.text()
        nova_senha = self.input_nova_senha.text()
        confirmacao = self.input_confirmacao.text()

        # Validação no front-end
        if not senha_atual or not nova_senha or not confirmacao:
            QMessageBox.warning(self, "Campos Vazios", "Todos os campos são obrigatórios.")
            return

        if nova_senha != confirmacao:
            QMessageBox.warning(self, "Erro", "A nova senha e a confirmação não correspondem.")
            return
            
        global access_token
        url = f"{API_BASE_URL}/api/usuario/mudar-senha"
        headers = {'Authorization': f'Bearer {access_token}'}
        dados = {
            "senha_atual": senha_atual,
            "nova_senha": nova_senha,
            "confirmacao_nova_senha": confirmacao
        }

        try:
            response = requests.post(url, headers=headers, json=dados)
            if response and response.status_code == 200:
                QMessageBox.information(self, "Sucesso", "Senha alterada com sucesso!")
                super().accept() # Fecha o diálogo
            else:
                erro = response.json().get('erro', 'Ocorreu um erro desconhecido.')
                QMessageBox.warning(self, "Falha na Alteração", erro)

        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Erro de Conexão", f"Não foi possível conectar ao servidor: {e}")

class QuantidadeDialog(QDialog):
    """Diálogo para adicionar ou remover uma quantidade de estoque."""
    estoque_modificado = Signal(int) # Sinal que emite o novo saldo

    def __init__(self, parent, produto_id, produto_nome, operacao):
        super().__init__(parent)
        self.produto_id = produto_id
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

        dados = {
            "id_produto": self.produto_id,
            "quantidade": int(quantidade_str)
        }
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
                # Após o sucesso, busca o novo saldo e emite o sinal
                saldo_response = requests.get(f"{API_BASE_URL}/api/estoque/saldos?search={self.produto_id}", headers=headers)
                if saldo_response and saldo_response.status_code == 200:
                    novo_saldo = saldo_response.json()[0]['saldo_atual']
                    self.estoque_modificado.emit(novo_saldo)
                super().accept()
            else:
                QMessageBox.warning(self, "Erro na API", response.json().get('erro', 'Ocorreu um erro.'))
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Erro de Conexão", str(e))
# ==============================================================================
# 4. WIDGETS DE CONTEÚDO (AS "TELAS" PRINCIPAIS)
# ==============================================================================



# Em main_ui.py, substitua a sua classe InventarioWidget por esta

class InventarioWidget(QWidget):
    """A nova tela unificada para visualização e gestão do inventário."""
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.dados_exibidos = []
        self.sort_qtd_desc = True

        # --- Título ---
        self.titulo = QLabel("Inventário Completo")
        self.titulo.setStyleSheet("font-size: 24px; font-weight: bold;")

        # --- Layout de Controles ---
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
        
        # --- NOVO BOTÃO DE ETIQUETAS ---
        self.btn_gerar_etiquetas = QPushButton("🖨️ Gerar Etiquetas")
        self.btn_gerar_etiquetas.setObjectName("btnPrint") # Nome para o estilo

        controles_layout_2.addWidget(self.btn_adicionar)
        controles_layout_2.addWidget(self.btn_editar)
        controles_layout_2.addWidget(self.btn_excluir)
        controles_layout_2.addWidget(self.btn_gerar_etiquetas) # Adicionado ao layout
        controles_layout_2.addStretch(1)

        # Botões de Ordenação
        self.btn_ordenar_nome = QPushButton("🔤 A-Z")
        self.btn_ordenar_nome.setToolTip("Ordenar por Nome do Produto")
        self.btn_ordenar_nome.setObjectName("btnIcon")
        self.btn_ordenar_qtd = QPushButton("📦 Qtd.")
        self.btn_ordenar_qtd.setToolTip("Ordenar por Saldo em Estoque")
        self.btn_ordenar_qtd.setObjectName("btnIcon")
        
        controles_layout_2.addWidget(self.btn_ordenar_nome)
        controles_layout_2.addWidget(self.btn_ordenar_qtd)

        # --- Tabela de Inventário ---
        self.tabela_inventario = QTableWidget()
        # --- ALTERAÇÃO: Permite a seleção de múltiplas linhas ---
        self.tabela_inventario.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tabela_inventario.setColumnCount(7)
        self.tabela_inventario.setHorizontalHeaderLabels([
            "Código", "Nome do Produto", "Descrição", "Saldo", "Preço (R$)", "Código B", "Código C"
        ])
        self.tabela_inventario.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabela_inventario.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tabela_inventario.setAlternatingRowColors(True)
        self.tabela_inventario.setWordWrap(True)

        header = self.tabela_inventario.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)

        # --- Adicionando Widgets ao Layout Principal ---
        self.layout.addWidget(self.titulo)
        self.layout.addLayout(controles_layout_1)
        self.layout.addLayout(controles_layout_2)
        self.layout.addWidget(self.tabela_inventario)

        # --- Temporizador para a busca ---
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.carregar_dados_inventario)

        # --- Conexões ---
        self.input_pesquisa.textChanged.connect(self.iniciar_busca_timer)
        self.btn_adicionar.clicked.connect(self.abrir_formulario_adicionar)
        self.btn_editar.clicked.connect(self.abrir_formulario_editar)
        self.btn_excluir.clicked.connect(self.excluir_produto_selecionado)
        self.btn_gerar_etiquetas.clicked.connect(self.gerar_etiquetas_selecionadas) # Nova conexão
        self.btn_ordenar_nome.clicked.connect(self.ordenar_por_nome)
        self.btn_ordenar_qtd.clicked.connect(self.ordenar_por_quantidade)

        # --- Carga Inicial ---
        self.carregar_dados_inventario()

    # --- NOVO MÉTODO PARA GERAR ETIQUETAS ---
    def gerar_etiquetas_selecionadas(self):
        # Pega os índices das linhas selecionadas
        selected_rows = self.tabela_inventario.selectionModel().selectedRows()
        
        if not selected_rows:
            QMessageBox.warning(self, "Seleção", "Por favor, selecione um ou mais produtos na tabela para gerar as etiquetas.")
            return

        # Extrai os IDs dos produtos das linhas selecionadas
        product_ids = []
        for index in selected_rows:
            item = self.tabela_inventario.item(index.row(), 0)
            if item and item.data(Qt.UserRole):
                product_ids.append(item.data(Qt.UserRole))

        if not product_ids:
            QMessageBox.warning(self, "Erro", "Não foi possível obter os IDs dos produtos selecionados.")
            return

        # Abre a janela para o utilizador escolher onde salvar
        caminho_salvar, _ = QFileDialog.getSaveFileName(self, "Salvar Ficheiro de Etiquetas", "etiquetas.pdf", "Ficheiros PDF (*.pdf)")

        if not caminho_salvar:
            return # Utilizador cancelou

        global access_token
        url = f"{API_BASE_URL}/api/produtos/etiquetas"
        headers = {'Authorization': f'Bearer {access_token}'}
        dados = {'product_ids': product_ids}

        try:
            # Mostra uma mensagem de "Aguarde"
            msg_box = QMessageBox(QMessageBox.Icon.Information, "Aguarde", "A gerar o ficheiro de etiquetas...", buttons=QMessageBox.StandardButton.NoButton, parent=self)
            msg_box.show()
            QApplication.processEvents()

            response = requests.post(url, headers=headers, json=dados, stream=True)
            
            msg_box.close() # Fecha a mensagem de "Aguarde"

            if response and response.status_code == 200:
                with open(caminho_salvar, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                QMessageBox.information(self, "Sucesso", f"Ficheiro de etiquetas salvo com sucesso em:\n{caminho_salvar}")
            else:
                erro = response.json().get('erro', 'Erro desconhecido.')
                QMessageBox.warning(self, "Erro na API", f"Não foi possível gerar as etiquetas: {erro}")

        except requests.exceptions.RequestException as e:
            msg_box.close()
            QMessageBox.critical(self, "Erro de Conexão", f"Não foi possível conectar ao servidor: {e}")

    # O resto dos seus métodos (iniciar_busca_timer, carregar_dados_inventario, etc.) continua aqui
    def iniciar_busca_timer(self):
        self.search_timer.stop()
        self.search_timer.start(300)

    def carregar_dados_inventario(self):
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
                self.dados_exibidos = response.json()
                self.popular_tabela(self.dados_exibidos)
            else:
                QMessageBox.warning(self, "Erro", "Não foi possível carregar os dados do inventário.")
        except requests.exceptions.RequestException as e:
            QMessageBox.critical(self, "Erro de Conexão", f"Não foi possível conectar ao servidor: {e}")

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
            url = f"{API_BASE_URL}/api/produtos/{produto_id}"
            headers = {'Authorization': f'Bearer {access_token}'}
            try:
                response = requests.delete(url, headers=headers)
                if response and response.status_code == 200:
                    QMessageBox.information(self, "Sucesso", "Produto excluído com sucesso!")
                    self.carregar_dados_inventario()
                else:
                    erro = response.json().get('erro', 'Erro desconhecido.')
                    QMessageBox.warning(self, "Erro", f"Não foi possível excluir o produto: {erro}")
            except requests.exceptions.RequestException as e:
                QMessageBox.critical(self, "Erro de Conexão", f"Não foi possível conectar ao servidor: {e}")

class GestaoEstoqueWidget(QWidget):
    """Widget contêiner que gerencia as visualizações de Inventário e Histórico."""
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,0)

        # --- Sub-Widgets (as "telas" internas) ---
        self.inventario_view = InventarioWidget()
        self.historico_view = HistoricoWidget()

        # --- Botões de Navegação ---
        nav_layout = QHBoxLayout()
        self.btn_ver_inventario = QPushButton("Visão Geral do Inventário")
        self.btn_ver_historico = QPushButton("Ver Histórico de Movimentações")
        self.btn_ver_inventario.setCheckable(True)
        self.btn_ver_historico.setCheckable(True)
        self.btn_ver_inventario.setChecked(True)

        nav_layout.addWidget(self.btn_ver_inventario)
        nav_layout.addWidget(self.btn_ver_historico)
        nav_layout.addStretch(1)

        # --- Stacked Widget para alternar as telas ---
        self.stack = QStackedWidget()
        self.stack.addWidget(self.inventario_view)
        self.stack.addWidget(self.historico_view)

        self.layout.addLayout(nav_layout)
        self.layout.addWidget(self.stack)

        # --- Conexões ---
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
        self.tabela_produtos.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
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

        dialog = FormularioProdutoDialog(self, produto_id=produto_id, row=linha_selecionada)
        dialog.produto_atualizado.connect(self.atualizar_linha_produto)
        dialog.exec()

    def atualizar_linha_produto(self, linha, dados_produto):
        item_codigo = QTableWidgetItem(dados_produto['codigo'])
        item_codigo.setData(Qt.UserRole, dados_produto['id'])
        self.tabela_produtos.setItem(linha, 0, item_codigo)

        self.tabela_produtos.setItem(linha, 1, QTableWidgetItem(dados_produto['nome']))
        self.tabela_produtos.setItem(linha, 2, QTableWidgetItem(dados_produto['descricao']))
        self.tabela_produtos.setItem(linha, 3, QTableWidgetItem(dados_produto['preco']))
        self.tabela_produtos.setItem(linha, 4, QTableWidgetItem(dados_produto.get('codigoB', '')))
        self.tabela_produtos.setItem(linha, 5, QTableWidgetItem(dados_produto.get('codigoC', '')))
        self.tabela_produtos.setItem(linha, 6, QTableWidgetItem(dados_produto.get('fornecedores', '')))
        self.tabela_produtos.setItem(linha, 7, QTableWidgetItem(dados_produto.get('naturezas', '')))

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
                if response and response.status_code == 200:
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
            if response and response.status_code == 200:
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
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)
        self.dados_exibidos = []

        self.titulo = QLabel("Consulta de Saldos de Estoque")
        self.titulo.setStyleSheet("font-size: 24px; font-weight: bold;")

        layout_controles = QHBoxLayout()
        
        self.input_pesquisa = QLineEdit()
        self.input_pesquisa.setPlaceholderText("Buscar por Nome ou Códigos (A, B ou C)...")
        
        self.btn_ordenar_nome = QPushButton("🔤 A-Z")
        self.btn_ordenar_nome.setToolTip("Ordenar por Nome do Produto")
        self.btn_ordenar_nome.setObjectName("btnIcon")

        self.btn_ordenar_codigo = QPushButton("🔢 Cód.")
        self.btn_ordenar_codigo.setToolTip("Ordenar por Código Principal")
        self.btn_ordenar_codigo.setObjectName("btnIcon")

        self.btn_recarregar = QPushButton("🔄 Recarregar")
        self.btn_recarregar.setToolTip("Limpar busca e recarregar a lista completa")

        layout_controles.addWidget(self.input_pesquisa)
        layout_controles.addWidget(self.btn_ordenar_nome)
        layout_controles.addWidget(self.btn_ordenar_codigo)
        layout_controles.addWidget(self.btn_recarregar)

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
        
        self.layout.addWidget(self.titulo)
        self.layout.addLayout(layout_controles)
        self.layout.addWidget(self.tabela_estoque)

        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.carregar_dados_estoque)

        self.btn_recarregar.clicked.connect(self.recarregar_lista_completa)
        self.input_pesquisa.textChanged.connect(self.iniciar_busca_timer)
        self.btn_ordenar_nome.clicked.connect(self.ordenar_por_nome)
        self.btn_ordenar_codigo.clicked.connect(self.ordenar_por_codigo)

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
                self.dados_exibidos = response.json()
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

    def ordenar_por_nome(self):
        self.dados_exibidos.sort(key=lambda item: item['nome'].lower())
        self.popular_tabela(self.dados_exibidos)

    def ordenar_por_codigo(self):
        self.dados_exibidos.sort(key=lambda item: item['codigo'])
        self.popular_tabela(self.dados_exibidos)

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
        self.tabela_historico.setHorizontalHeaderLabels([
            "Data/Hora", "Cód. Produto", "Nome Produto", "Tipo", "Qtd. Mov.", "Saldo Após", "Usuário", "Motivo da Saída"
        ])
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
        
        params = {
            'data_inicio': data_inicio.toString("yyyy-MM-dd"),
            'data_fim': data_fim.toString("yyyy-MM-dd"),
            'formato': 'json'
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

        self.label_nome_produto = QLabel("Aguardando verificação...")
        
        self.input_quantidade = QLineEdit()
        self.input_quantidade.setPlaceholderText("0")
        self.input_quantidade.setValidator(QDoubleValidator(0, 99999, 0))
        
        self.btn_registrar = QPushButton("Registar Entrada")
        self.btn_registrar.setObjectName("btnPositive")

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

class TerminalWidget(QWidget):
    """Tela de consulta rápida otimizada para leitor de código de barras."""
    def __init__(self):
        super().__init__()
        self.setObjectName("terminalWidget")
        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.barcode_buffer = ""
        self.barcode_timer = QTimer(self)
        self.barcode_timer.setSingleShot(True)
        self.barcode_timer.setInterval(200) # Tempo de espera entre os caracteres
        self.barcode_timer.timeout.connect(self.processar_codigo)
        
        self.produto_atual = None

        # --- Painel Principal ---
        main_panel = QFrame()
        main_panel.setObjectName("terminalMainPanel")
        main_panel_layout = QVBoxLayout(main_panel)
        main_panel_layout.setSpacing(20)

        # Secção Superior: Nome e Quantidade
        top_section_layout = QHBoxLayout()
        self.label_nome = QLabel("Passe um código de barras no leitor...")
        self.label_nome.setObjectName("terminalProductName")
        self.label_nome.setWordWrap(True)
        
        self.label_qtd_box = QFrame()
        self.label_qtd_box.setObjectName("terminalQuantityBox")
        qtd_layout = QVBoxLayout(self.label_qtd_box)
        self.label_qtd_valor = QLabel("--")
        self.label_qtd_valor.setObjectName("terminalQuantityValue")
        qtd_layout.addWidget(self.label_qtd_valor)
        
        top_section_layout.addWidget(self.label_nome, 4) # Proporção 4
        top_section_layout.addWidget(self.label_qtd_box, 1) # Proporção 1

        # Botões de Ação
        action_buttons_layout = QHBoxLayout()
        self.btn_remover = QPushButton("➖")
        self.btn_remover.setObjectName("btnTerminalRemove")
        self.btn_adicionar = QPushButton("➕")
        self.btn_adicionar.setObjectName("btnTerminalAdd")
        action_buttons_layout.addStretch(1)
        action_buttons_layout.addWidget(self.btn_remover)
        action_buttons_layout.addWidget(self.btn_adicionar)
        action_buttons_layout.addStretch(1)

        main_panel_layout.addLayout(top_section_layout)
        main_panel_layout.addLayout(action_buttons_layout)

        # --- Painel Inferior: Descrição e Código ---
        bottom_panel = QFrame()
        bottom_panel.setObjectName("terminalBottomPanel")
        bottom_panel_layout = QVBoxLayout(bottom_panel)
        self.label_descricao = QLabel("Descrição do produto aparecerá aqui.")
        self.label_descricao.setObjectName("terminalDescription")
        self.label_codigo = QLabel("Código: --")
        self.label_codigo.setObjectName("terminalCode")
        bottom_panel_layout.addWidget(self.label_descricao)
        bottom_panel_layout.addWidget(self.label_codigo)

        self.layout.addWidget(main_panel, 2) # Proporção 2
        self.layout.addWidget(bottom_panel, 1) # Proporção 1

        # Conexões
        self.btn_adicionar.clicked.connect(lambda: self.abrir_dialogo_quantidade("Entrada"))
        self.btn_remover.clicked.connect(lambda: self.abrir_dialogo_quantidade("Saida"))
        
        self.resetar_tela()

    def keyPressEvent(self, event):
        """Captura os eventos de teclado para ler o código de barras."""
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
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
        
        dialog = QuantidadeDialog(self, self.produto_atual['id_produto'], self.produto_atual['nome'], operacao)
        dialog.estoque_modificado.connect(self.atualizar_quantidade_em_tempo_real)
        dialog.exec()

    def atualizar_quantidade_em_tempo_real(self, novo_saldo):
        """Atualiza o saldo na tela após uma operação bem-sucedida."""
        if self.produto_atual:
            self.produto_atual['saldo_atual'] = novo_saldo
            self.label_qtd_valor.setText(str(novo_saldo))

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
            self.tela_gestao_estoque = GestaoEstoqueWidget() # <-- NOVA TELA UNIFICADA
            self.tela_entrada_rapida = EntradaRapidaWidget()
            self.tela_saida_rapida = SaidaRapidaWidget()
            self.tela_relatorios = RelatoriosWidget()
            self.tela_fornecedores = FornecedoresWidget()
            self.tela_naturezas = NaturezasWidget()
            self.tela_usuarios = None
            self.tela_importacao = ImportacaoWidget()
            self.tela_terminal = TerminalWidget()

            self.stacked_widget.addWidget(self.tela_dashboard)
            self.stacked_widget.addWidget(self.tela_gestao_estoque) # <-- ADICIONADA
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
            self.acao_produtos = QAction("Inventário...", self) # Texto do menu atualizado
            self.acao_produtos.setShortcut("Ctrl+P")
            self.acao_produtos.triggered.connect(self.mostrar_tela_gestao_estoque) # Conecta à nova tela
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
            acao_saldos = QAction("Consultar Inventário...", self) # Texto atualizado
            acao_saldos.triggered.connect(self.mostrar_tela_gestao_estoque) # Conecta à nova tela
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
            self.btn_inventario = QPushButton("📦 Inventário") # <-- NOVO BOTÃO
            self.btn_entrada_rapida = QPushButton("➡️ Entrada Rápida")
            self.btn_saida_rapida = QPushButton("⬅️ Saída Rápida")
            self.btn_relatorios = QPushButton("📄 Relatórios")
            self.btn_fornecedores = QPushButton("🚚 Fornecedores")
            self.btn_naturezas = QPushButton("🌿 Naturezas")
            self.btn_terminal = QPushButton("🛰️ Terminal")
            self.btn_usuarios = QPushButton("👥 Usuários")
            self.btn_logoff = QPushButton("🚪 Fazer Logoff")
            self.btn_logoff.setObjectName("btnLogoff")

            self.layout_painel_lateral.addWidget(self.btn_dashboard)
            self.layout_painel_lateral.addWidget(self.btn_inventario) # <-- ADICIONADO
            self.layout_painel_lateral.addWidget(self.btn_entrada_rapida)
            self.layout_painel_lateral.addWidget(self.btn_saida_rapida)
            self.layout_painel_lateral.addWidget(self.btn_relatorios)
            self.layout_painel_lateral.addWidget(self.btn_fornecedores)
            self.layout_painel_lateral.addWidget(self.btn_naturezas)
            self.layout_painel_lateral.addWidget(self.btn_terminal)
            self.layout_painel_lateral.addStretch(1)
            self.layout_painel_lateral.addWidget(self.btn_logoff)
            
            layout_principal.addWidget(painel_lateral)
            layout_principal.addWidget(self.stacked_widget)

            # --- CONEXÕES ---
            self.btn_dashboard.clicked.connect(self.mostrar_tela_dashboard)
            self.btn_inventario.clicked.connect(self.mostrar_tela_gestao_estoque) # <-- CONEXÃO ATUALIZADA
            self.btn_entrada_rapida.clicked.connect(self.mostrar_tela_entrada_rapida)
            self.btn_saida_rapida.clicked.connect(self.mostrar_tela_saida_rapida)
            self.btn_relatorios.clicked.connect(self.mostrar_tela_relatorios)
            self.btn_fornecedores.clicked.connect(self.mostrar_tela_fornecedores)
            self.btn_naturezas.clicked.connect(self.mostrar_tela_naturezas)
            self.btn_terminal.clicked.connect(self.mostrar_tela_terminal)
            self.btn_logoff.clicked.connect(self.logoff_requested.emit)
            
            # Conexões de sinais entre widgets
            self.tela_dashboard.ir_para_produtos.connect(self.mostrar_tela_gestao_estoque) # <-- CONEXÃO ATUALIZADA
            self.tela_dashboard.ir_para_fornecedores.connect(self.mostrar_tela_fornecedores)
            self.tela_dashboard.ir_para_entrada_rapida.connect(self.mostrar_tela_entrada_rapida)
            self.tela_dashboard.ir_para_saida_rapida.connect(self.mostrar_tela_saida_rapida)
            self.tela_dashboard.ir_para_terminal.connect(self.mostrar_tela_terminal) 
            self.tela_entrada_rapida.estoque_atualizado.connect(self.tela_gestao_estoque.inventario_view.carregar_dados_inventario)
            self.tela_saida_rapida.estoque_atualizado.connect(self.tela_gestao_estoque.inventario_view.carregar_dados_inventario)
            self.tela_importacao.produtos_importados_sucesso.connect(self.tela_gestao_estoque.inventario_view.carregar_dados_inventario)
            signal_handler.fornecedores_atualizados.connect(self.tela_fornecedores.carregar_fornecedores)
            signal_handler.naturezas_atualizadas.connect(self.tela_naturezas.carregar_naturezas)

            self.statusBar().showMessage("Pronto.")

        except Exception as e:
            error_log_path = os.path.join(os.path.expanduser("~"), "Desktop", "crash_log.txt")
            with open(error_log_path, "w", encoding="utf-8") as f:
                f.write(f"Ocorreu um erro crítico ao iniciar a janela principal:\n\n")
                f.write(f"{e}\n\n")
                f.write(traceback.format_exc())
            QMessageBox.critical(self, "Erro de Inicialização", f"Ocorreu um erro crítico. Verifique o ficheiro 'crash_log.txt' no seu Ambiente de Trabalho.")
            sys.exit(1)


        except Exception as e:
            error_log_path = os.path.join(os.path.expanduser("~"), "Desktop", "crash_log.txt")
            with open(error_log_path, "w", encoding="utf-8") as f:
                f.write(f"Ocorreu um erro crítico ao iniciar a janela principal:\n\n")
                f.write(f"{e}\n\n")
                f.write(traceback.format_exc())
            QMessageBox.critical(self, "Erro de Inicialização", f"Ocorreu um erro crítico. Verifique o ficheiro 'crash_log.txt' no seu Ambiente de Trabalho.")
            sys.exit(1)

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
        # Passa o nome do utilizador logado para o método de carregamento do dashboard
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
       """Exibe a nossa nova caixa de diálogo 'Sobre' personalizada."""
       dialog = SobreDialog(self)
       dialog.exec()

    
    def mostrar_tela_importacao(self):
        self.stacked_widget.setCurrentWidget(self.tela_importacao)
        
    def mostrar_tela_gestao_estoque(self):
        """Mostra a nova tela unificada de gestão de estoque."""
        self.stacked_widget.setCurrentWidget(self.tela_gestao_estoque)
        # Garante que a aplicação abre sempre na aba de inventário por defeito
        self.tela_gestao_estoque.mostrar_inventario()
        
    def abrir_dialogo_mudar_senha(self):
        """Abre a janela de diálogo para alteração de senha."""
        dialog = MudarSenhaDialog(self)
        dialog.exec()

    def mostrar_tela_terminal(self):
        """Mostra a tela do terminal e garante que ela tem o foco do teclado."""
        self.stacked_widget.setCurrentWidget(self.tela_terminal)
        self.tela_terminal.setFocus() # Essencial para capturar os eventos de teclado

class SobreDialog(QDialog):
    """Uma janela 'Sobre' personalizada com um easter egg que toca um ficheiro de áudio."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sobre o Sistema")
        self.setMinimumWidth(400)
        self.click_count = 0

        # --- Prepara o leitor de som ---
        self.sound_effect = QSoundEffect()

        self.layout = QVBoxLayout(self)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.setSpacing(15)

        # --- Logo Clicável ---
        self.logo_label = QLabel()
        logo_pixmap = QPixmap(resource_path("logo2.png"))
        logo_redimensionada = logo_pixmap.scaled(150, 90, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.logo_label.setPixmap(logo_redimensionada)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_label.setToolTip("Hmmm, o que será que acontece se clicar aqui várias vezes?")
        self.logo_label.installEventFilter(self)

        # --- Texto Informativo ---
        info_text = QLabel(
            """
            <b>Sistema de Gestão de Estoque v2.0</b>
            <p>Versão 26-08-2025</p>
            <p>Desenvolvido por Matheus com Google Gemini :D.</p>
            <p>Desenvolvido para controle de estoque na Szm.</p>
            <p><b>Tecnologias:</b> Python, PySide6, Flask, SQLAlchemy.</p>
            <p>Agradecimentos especiais a Mathias pela colaboração e testes.</p>
            
            """
        )
        info_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_text.setWordWrap(True)

        # --- Botão OK ---
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)

        # Adicionando tudo ao layout
        self.layout.addWidget(self.logo_label)
        self.layout.addWidget(info_text)
        self.layout.addWidget(self.ok_button, 0, Qt.AlignmentFlag.AlignCenter)

    def eventFilter(self, source, event):
        """Filtro que interceta os eventos antes de eles chegarem ao seu destino."""
        if source is self.logo_label and event.type() == QEvent.Type.MouseButtonPress:
            self.click_count += 1
            print(f"Logo clicada {self.click_count} vezes.")
            
            if self.click_count == 10:
                print("Easter Egg Ativado!")
                self.tocar_musica() # Chama diretamente, sem thread
                self.click_count = 0
            
            return True
        
        return super().eventFilter(source, event)

    def tocar_musica(self):
        """Toca um ficheiro de áudio como easter egg."""
        try:
            # Usa QSoundEffect para tocar o áudio sem bloquear a UI.
            # Usamos resource_path para encontrar o ficheiro, e QUrl.fromLocalFile para o carregar.
            self.sound_effect.setSource(QUrl.fromLocalFile(resource_path("easter_egg.wav")))
            self.sound_effect.setVolume(0.8) # Volume a 80%
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
    """Tela principal do dashboard com um design profissional e minimalista."""
    # Sinais para navegar para outras telas
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

        # --- CORREÇÃO: Curiosidades agora estão embutidas diretamente no código ---
        self.lista_curiosidades = [
    "A Cidade do Vaticano é o menor país do mundo.",
    "O mel nunca se estraga. Arqueólogos encontraram potes de mel em túmulos egípcios com mais de 3000 anos e ainda comestíveis.",
    "As formigas descansam cerca de 8 minutos num período de 12 horas.",
    "O olho de um avestruz é maior do que o seu cérebro.",
    "Os polvos têm três corações e o seu sangue é azul.",
    "A Grande Muralha da China não é visível da Lua a olho nu.",
    "O som não se propaga no vácuo.",
    "O Brasil é o país com a maior biodiversidade do mundo.",
    "As borboletas sentem o sabor com os seus pés.",
    "Um raio pode atingir uma temperatura cinco vezes superior à da superfície do Sol.",
    "O seu coração bate cerca de 100.000 vezes por dia.",
    "A preguiça pode levar até um mês para digerir uma única folha.",
    "O Oceano Pacífico é o maior e mais profundo oceano do mundo.",
    "A Torre Eiffel pode ser 15 cm mais alta durante o verão devido à expansão térmica do ferro.",
    "Os camelos têm três pálpebras para se protegerem da areia do deserto.",
    "A Antártida é o maior deserto do mundo.",
    "O ornitorrinco é um dos poucos mamíferos que põem ovos.",
    "As vacas têm melhores amigas e ficam stressadas quando são separadas.",
    "O recorde de voo de uma galinha é de 13 segundos.",
    "A pele de um urso polar é preta por baixo do seu pelo branco.",
    "O Sol é tão grande que caberiam aproximadamente 1.3 milhões de planetas Terra dentro dele.",
    "As impressões digitais de um coala são indistinguíveis das de um humano.",
    "O Japão tem mais de 6.800 ilhas.",
    "Os flamingos são cor-de-rosa por causa dos pigmentos dos camarões e algas que comem.",
    "O cérebro humano gera cerca de 23 watts de energia quando está acordado, o suficiente para acender uma lâmpada pequena.",
    "As lontras do mar dão as mãos enquanto dormem para não se afastarem.",
    "A Mona Lisa não tem sobrancelhas.",
    "O isqueiro foi inventado antes do fósforo.",
    "O esqueleto humano é composto por 206 ossos.",
    "As girafas não têm cordas vocais.",
    "O Monte Evereste cresce cerca de 4 milímetros por ano.",
    "A água quente congela mais rápido do que a água fria, um fenómeno conhecido como efeito Mpemba.",
    "As formigas não têm pulmões.",
    "O caracol pode dormir por até três anos.",
    "O chocolate já foi usado como moeda pelos Astecas.",
    "A Austrália é mais larga do que a Lua.",
    "O som de um chicote a estalar é, na verdade, um pequeno boom sónico.",
    "O coração de uma baleia azul é tão grande que um humano poderia nadar através das suas artérias.",
    "As abelhas conseguem reconhecer rostos humanos.",
    "A Islândia é o único país sem mosquitos.",
    "O primeiro telemóvel pesava mais de 1 kg.",
    "O cabelo humano cresce, em média, 15 centímetros por ano.",
    "As estrelas-do-mar não têm cérebro.",
    "O Egito é o país com mais pirâmides no mundo, não o México.",
    "Os cavalos-marinhos são os únicos animais em que o macho dá à luz.",
    "Apenas 5% do oceano foi explorado.",
    "O nome completo da Barbie é Barbara Millicent Roberts.",
    "O pneu de um carro de Fórmula 1 gira cerca de 50 vezes por segundo a alta velocidade.",
    "O corpo humano tem mais de 96.000 quilómetros de vasos sanguíneos.",
    "As cabras têm sotaques.",
    "O maior engarrafamento do mundo durou 12 dias.",
    "A Rússia é maior em área de superfície do que Plutão.",
    "O nome original do Pac-Man era Puck-Man.",
    "As bananas são bagas, mas os morangos não são.",
    "O músculo mais forte do corpo humano é a língua.",
    "O grito de um pavão pode ser ouvido a mais de um quilómetro de distância.",
    "A Lua está a afastar-se da Terra a uma taxa de 3.8 cm por ano.",
    "O suor dos hipopótamos é cor-de-rosa.",
    "O primeiro produto a ter um código de barras foi um pacote de pastilhas elásticas.",
    "Os golfinhos dão nomes uns aos outros.",
    "O olho humano consegue distinguir cerca de 10 milhões de cores diferentes.",
    "O som de um pato não faz eco, e ninguém sabe porquê.",
    "O nome original do Google era Backrub.",
    "As unhas das mãos crescem mais rápido do que as unhas dos pés.",
    "O cérebro de um elefante pesa cerca de 5 kg.",
    "A Estátua da Liberdade era originalmente da cor do cobre.",
    "O medo de espaços vazios chama-se cenofobia.",
    "Os ratos multiplicam-se tão rapidamente que, em 18 meses, dois ratos podem ter mais de um milhão de descendentes.",
    "O primeiro email foi enviado em 1971.",
    "As aranhas são aracnídeos, não insetos.",
    "O coração de um camarão está na sua cabeça.",
    "O nome do Bluetooth vem de um rei viking do século X, Harald Bluetooth.",
    "O recorde mundial para o maior número de flexões sem parar é de 10.507.",
    "O deserto do Saara já foi uma floresta tropical exuberante.",
    "Os tubarões existem há mais tempo do que as árvores.",
    "O nome completo do Pato Donald é Donald Fauntleroy Duck.",
    "A Coca-Cola seria verde se não fossem adicionados corantes.",
    "O corpo humano produz 25 milhões de novas células a cada segundo.",
    "Os pinguins propõem casamento oferecendo uma pedra à sua parceira.",
    "O primeiro filme a usar efeitos gerados por computador foi 'Westworld' em 1973.",
    "O planeta Vénus gira na direção oposta à da maioria dos outros planetas.",
    "O espirro viaja a cerca de 160 km/h.",
    "As corujas não conseguem mover os seus olhos.",
    "O nome 'LEGO' vem da frase dinamarquesa 'leg godt', que significa 'brincar bem'.",
    "O maior floco de neve já registado tinha 38 cm de diâmetro.",
    "A pele é o maior órgão do corpo humano.",
    "O nome original da Nike era Blue Ribbon Sports.",
    "Os gatos não conseguem sentir o sabor doce.",
    "O crânio humano é composto por 22 ossos.",
    "O primeiro despertador só conseguia tocar às 4 da manhã.",
    "O koala dorme cerca de 22 horas por dia.",
    "A palavra 'abacate' vem da palavra asteca para 'testículo'.",
    "O som viaja quatro vezes mais rápido na água do que no ar.",
    "O nome original do Twitter era 'twttr'.",
    "O cérebro humano encolhe à medida que envelhecemos.",
    "A probabilidade de ser atingido por um raio é maior do que a de ganhar na lotaria.",
    "O nome 'Wendy' foi inventado para o livro 'Peter Pan'.",
    "As formigas conseguem levantar 50 vezes o seu próprio peso.",
    "O primeiro romance escrito numa máquina de escrever foi 'As Aventuras de Tom Sawyer'.",
    "O nome do estado do Alasca vem de uma palavra aleúte que significa 'grande terra'.",
    "Os gatos têm cinco dedos nas patas dianteiras e quatro nas traseiras.",
    "O nome 'robô' vem da palavra checa 'robota', que significa 'trabalho forçado'.",
    "O primeiro vídeo do YouTube foi carregado em 23 de abril de 2005.",
    "A palavra 'nerd' foi usada pela primeira vez no livro de Dr. Seuss 'If I Ran the Zoo'.",
    "O coração humano para por um milissegundo quando espirramos.",
    "O nome original da Pepsi era 'Brad's Drink'.",
    "Os elefantes são os únicos mamíferos que não conseguem saltar.",
    "O nome 'jeans' vem da cidade de Génova, em Itália.",
    "O primeiro tweet foi enviado em 21 de março de 2006.",
    "A palavra 'quarentena' vem da palavra italiana 'quaranta giorni', que significa '40 dias'.",
    "O nome 'sanduíche' vem de John Montagu, o 4º Conde de Sandwich.",
    "O primeiro website foi criado em 1991.",
    "A palavra 'assassino' vem da palavra árabe 'hashishin'.",
    "O nome 'gorila' vem de uma palavra grega que significa 'tribo de mulheres peludas'.",
    "O primeiro telemóvel com câmara foi lançado no Japão em 2000.",
    "A palavra 'músculo' vem da palavra latina 'musculus', que significa 'ratinho'.",
    "O nome 'helicóptero' vem das palavras gregas 'helix' (espiral) e 'pteron' (asa).",
    "O primeiro videojogo foi criado em 1958.",
    "A palavra 'escola' vem da palavra grega 'skhole', que significa 'lazer'.",
    "O nome 'pânico' vem do deus grego Pan.",
    "O primeiro livro impresso foi a Bíblia de Gutenberg, em 1455.",
    "A palavra 'álcool' vem da palavra árabe 'al-kuhl'.",
    "O nome 'malária' vem da palavra italiana 'mala aria', que significa 'mau ar'.",
    "O primeiro filme a cores foi 'The World, the Flesh and the Devil', de 1914.",
    "A palavra 'salário' vem da palavra latina 'salarium', que se refere ao sal que era dado aos soldados romanos.",
    "O nome 'canário' vem das Ilhas Canárias, e não o contrário.",
    "O primeiro carro foi inventado em 1886 por Karl Benz.",
    "A palavra 'trivial' vem do latim 'trivium', que era o ponto de encontro de três estradas.",
    "O nome 'vulcão' vem do deus romano do fogo, Vulcano.",
    "O primeiro avião foi inventado em 1903 pelos irmãos Wright.",
    "A palavra 'ginásio' vem da palavra grega 'gymnasion', que significa 'lugar para se exercitar nu'.",
    "O nome 'eco' vem da ninfa grega Eco.",
    "O primeiro computador foi o ENIAC, em 1946.",
    "A palavra 'calendário' vem da palavra latina 'kalendarium', que era o livro de contas dos romanos.",
    "O nome 'narcisismo' vem da figura mitológica grega Narciso.",
    "O primeiro satélite artificial foi o Sputnik 1, lançado em 1957.",
    "A palavra 'biblioteca' vem da palavra grega 'bibliotheke', que significa 'caixa de livros'.",
    "O nome 'hipocondria' vem da palavra grega 'hypokhondrion', que se refere à área do abdómen abaixo das costelas.",
    "O primeiro homem no espaço foi Yuri Gagarin, em 1961.",
    "A palavra 'sarcasmo' vem da palavra grega 'sarkazein', que significa 'rasgar a carne'.",
    "O nome 'pijama' vem da palavra persa 'payjama', que significa 'vestimenta para as pernas'.",
    "O primeiro homem na Lua foi Neil Armstrong, em 1969.",
        ]

        # --- CARTÃO DE BOAS-VINDAS ---
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

        # --- TÍTULOS DE SECÇÃO ---
        kpi_title = QLabel("Resumo do Sistema")
        kpi_title.setObjectName("dashboardSectionTitle")
        action_title = QLabel("Operações Comuns")
        action_title.setObjectName("dashboardSectionTitle")

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
        self.btn_atalho_terminal = QPushButton("🛰️\n\nTerminal de Consulta")
        self.btn_atalho_terminal.setObjectName("btnDashboardAction")
        action_layout.addWidget(self.btn_atalho_entrada)
        action_layout.addWidget(self.btn_atalho_saida)
        action_layout.addWidget(self.btn_atalho_terminal)

        # Adicionando tudo ao layout principal
        self.layout.addWidget(welcome_card)
        self.layout.addWidget(kpi_title)
        self.layout.addLayout(kpi_layout)
        self.layout.addWidget(action_title)
        self.layout.addLayout(action_layout)
        self.layout.addStretch(1)

        # --- Conexões ---
        self.card_produtos.clicked.connect(self.ir_para_produtos.emit)
        self.card_fornecedores.clicked.connect(self.ir_para_fornecedores.emit)
        self.btn_atalho_entrada.clicked.connect(self.ir_para_entrada_rapida.emit)
        self.btn_atalho_saida.clicked.connect(self.ir_para_saida_rapida.emit)
        self.btn_atalho_terminal.clicked.connect(self.ir_para_terminal.emit)

    def atualizar_mensagem_boas_vindas(self, nome_utilizador):
        """Atualiza a mensagem de boas-vindas com o nome do utilizador e uma curiosidade."""
        primeiro_nome = nome_utilizador.split(" ")[0]
        curiosidade = random.choice(self.lista_curiosidades)
        
        self.label_boas_vindas.setText(f"Bem-vindo(a), {primeiro_nome}!")
        self.label_curiosidade.setText(f"<i>Você sabia que... {curiosidade}</i>")

    def carregar_dados_dashboard(self, nome_utilizador):
        self.atualizar_mensagem_boas_vindas(nome_utilizador)
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

class JanelaLogin(QWidget):
    login_successful = Signal(dict)

    def __init__(self):
        super().__init__()
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
    
    manager = AppManager()
    manager.start()
    
    sys.exit(app.exec())
