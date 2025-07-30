# Importa as bibliotecas que acabamos de instalar
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy

# Cria a aplicação Flask
app = Flask(__name__)

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
# Substitua 'SuaSenhaForteAqui' pela senha que você definiu para o root do MySQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:senha123@localhost/estoque_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Cria a instância que fará a ponte com o banco de dados
db = SQLAlchemy(app)



# --- MAPEAMENTO DAS TABELAS (MODELOS) ---
# Esta classe espelha a tabela PRODUTO no banco de dados
class Produto(db.Model):
    __tablename__ = 'produto'  # Garante que o nome da tabela seja 'produto'
    id_produto = db.Column('Id_produto', db.Integer, primary_key=True) # Mapeia para a coluna 'Id_produto'
    nome = db.Column('Nome', db.String(100), nullable=False)
    codigo = db.Column('Codigo', db.String(20), unique=True, nullable=False) # Usei String em vez de Char
    descricao = db.Column('Descricao', db.String(200))
    preco = db.Column('Preco', db.Numeric(10, 2), nullable=False)
    codigoB = db.Column('CodigoB', db.String(20))
    codigoC = db.Column('CodigoC', db.String(20))

# ... (código da rota de teste e do if __name__...)

# --- ROTAS DA API ---
@app.route('/api/produtos', methods=['GET'])
def get_produtos():
    try:
        # Usa o SQLAlchemy para buscar todos os registos da tabela Produto
        produtos_db = Produto.query.all()

        # Converte a lista de objetos Produto para uma lista de dicionários (formato JSON)
        produtos_json = []
        for produto in produtos_db:
            produtos_json.append({
                'id': produto.id_produto,
                'nome': produto.nome,
                'codigo': produto.codigo,
                'descricao': produto.descricao,
                'preco': str(produto.preco) # Convertemos decimal para string para o JSON
            })

        # Retorna a lista em formato JSON com uma resposta HTTP 200 (OK)
        return jsonify(produtos_json), 200

    except Exception as e:
        # Se der algum erro, retorna uma mensagem de erro
        return jsonify({'erro': str(e)}), 500


# ... (código do if __name__...)

# --- Bloco para executar a aplicação ---
if __name__ == '__main__':
    # O debug=True faz com que o servidor reinicie automaticamente sempre que você salvar uma alteração
    app.run(debug=True)