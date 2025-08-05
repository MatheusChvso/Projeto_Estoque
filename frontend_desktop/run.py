# run.py - O nosso lançador de aplicação

import sys
import os
import threading
from waitress import serve
from PySide6.QtWidgets import QApplication

# --- Configuração de Caminho ---
# Adiciona a pasta 'backend' ao caminho do Python para que possamos importar o 'app'
# Isso garante que o script funcione tanto no desenvolvimento quanto no .exe
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, backend_path)

# --- Imports do Nosso Projeto ---
from app import app  # Importa a instância do Flask do nosso backend
from main_ui import JanelaLogin, QIcon # Importa a janela de login e QIcon

# --- Função para Rodar o Servidor ---
def run_server():
    """Inicia o servidor Flask usando Waitress em uma porta específica."""
    print("Iniciando servidor Flask em segundo plano...")
    # Usamos o Waitress em vez do app.run() para um ambiente mais estável
    serve(app, host='127.0.0.1', port=5000)

# --- Bloco de Execução Principal ---
if __name__ == "__main__":
    # 1. Inicia o servidor em uma thread separada
    # A flag 'daemon=True' garante que a thread do servidor fechará junto com a aplicação
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # 2. Inicia a aplicação PySide6 (front-end)
    print("Iniciando a interface gráfica...")
    app_qt = QApplication(sys.argv)
    
    # Aplica o estilo (o mesmo código do main_ui.py)
    try:
        with open("style.qss", "r", encoding="utf-8") as f:
            app_qt.setStyleSheet(f.read())
    except FileNotFoundError:
        print("AVISO: Arquivo de estilo (style.qss) não encontrado.")
    

    
    janela_login = JanelaLogin()
    janela_login.show()
    
    sys.exit(app_qt.exec())