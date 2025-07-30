# 1. Importar 'request' junto com os outros
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

# Cria a aplicação Flask
app = Flask(__name__)

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:senha123@localhost/estoque_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Cria a instância que fará a ponte com o banco de dados
db = SQLAlchemy(app)


# --- MAPEAMENTO DAS TABELAS (MODELOS) ---
class Produto(db.Model):
    __tablename__ = 'produto'
    id_produto = db.Column('Id_produto', db.Integer, primary_key=True)
    nome = db.Column('Nome', db.String(100), nullable=False)
    codigo = db.Column('Codigo', db.String(20), unique=True, nullable=False)
    descricao = db.Column('Descricao', db.String(200))
    preco = db.Column('Preco', db.Numeric(10, 2), nullable=False)
    codigoB = db.Column('CodigoB', db.String(20))
    codigoC = db.Column('CodigoC', db.String(20))


# --- ROTAS DA API ---
# 2. Atualizar a rota para aceitar GET e POST
@app.route('/api/produtos', methods=['GET', 'POST'])
def produtos_endpoint(): # Mudei o nome da função para ser mais genérico
    # 3. Adicionar a lógica para diferenciar os métodos
    if request.method == 'GET':
        try:
            produtos_db = Produto.query.all()
            produtos_json = []
            for produto in produtos_db:
                produtos_json.append({
                    'id': produto.id_produto,
                    'nome': produto.nome,
                    'codigo': produto.codigo.strip(), # Adicionado .strip() para remover espaços do tipo CHAR
                    'descricao': produto.descricao,
                    'preco': str(produto.preco)
                })
            return jsonify(produtos_json), 200
        except Exception as e:
            return jsonify({'erro': str(e)}), 500

    if request.method == 'POST':
        try:
            # Pega nos dados JSON enviados no corpo do pedido
            dados = request.get_json()

            # Cria um novo objeto Produto com os dados recebidos
            novo_produto = Produto(
                nome=dados['nome'],
                codigo=dados['codigo'],
                descricao=dados.get('descricao'), # .get() é mais seguro se o campo for opcional
                preco=dados['preco'],
                codigoB=dados.get('codigoB'),
                codigoC=dados.get('codigoC')
            )

            # Adiciona o novo produto à sessão do banco de dados
            db.session.add(novo_produto)
            # Confirma (salva) a transação
            db.session.commit()

            # Retorna uma mensagem de sucesso
            return jsonify({'mensagem': 'Produto adicionado com sucesso!'}), 201 # 201 = Created

        except Exception as e:
            db.session.rollback() # Desfaz a transação em caso de erro
            return jsonify({'erro': str(e)}), 500


# --- Bloco para executar a aplicação ---
if __name__ == '__main__':
    app.run(debug=True)