# run.py - O nosso lançador de aplicação (Versão Final)

import sys
import os
import threading
from waitress import serve
from PySide6.QtWidgets import QApplication

# --- Configuração de Caminho ---
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, backend_path)

# --- Imports do Nosso Projeto ---
from app import app
from main_ui import JanelaLogin, resource_path # Importamos a função resource_path

# --- Função para Rodar o Servidor ---
def run_server():
    """Inicia o servidor Flask usando Waitress em uma porta específica."""
    print("Iniciando servidor Flask em segundo plano...")
    serve(app, host='0.0.0.0', port=5000)

# --- Bloco de Execução Principal ---
if __name__ == "__main__":
    # 1. Inicia o servidor em uma thread separada
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # 2. Inicia a aplicação PySide6 (front-end)
    print("Iniciando a interface gráfica...")
    app_qt = QApplication(sys.argv)
    
    # --- CORREÇÃO AQUI: Usamos resource_path para carregar o estilo ---
    try:
        # Agora o .exe saberá onde encontrar o style.qss
        with open(resource_path("style.qss"), "r", encoding="utf-8") as f:
            app_qt.setStyleSheet(f.read())
    except FileNotFoundError:
        print("AVISO: Arquivo de estilo (style.qss) não encontrado.")
    
    janela_login = JanelaLogin()
    janela_login.show()
    
    sys.exit(app_qt.exec())
