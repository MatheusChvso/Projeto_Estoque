from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

# Cria a aplicação Flask
app = Flask(__name__)

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
# Certifique-se de que a senha aqui está correta
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:senha123@localhost/estoque_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Cria a instância que fará a ponte com o banco de dados
db = SQLAlchemy(app)


# --- MAPEAMENTO DA TABELA PRODUTO (MODELO) ---
class Produto(db.Model):
    __tablename__ = 'produto'
    id_produto = db.Column('Id_produto', db.Integer, primary_key=True)
    nome = db.Column('Nome', db.String(100), nullable=False)
    codigo = db.Column('Codigo', db.String(20), unique=True, nullable=False)
    descricao = db.Column('Descricao', db.String(200))
    preco = db.Column('Preco', db.Numeric(10, 2), nullable=False)
    codigoB = db.Column('CodigoB', db.String(20))
    codigoC = db.Column('CodigoC', db.String(20))


# --- ROTA PRINCIPAL: /api/produtos (Para listar todos e criar um novo) ---
@app.route('/api/produtos', methods=['GET', 'POST'])
def produtos_endpoint():
    # Se o pedido for GET, retorna a lista de produtos
    if request.method == 'GET':
        try:
            produtos_db = Produto.query.all()
            # LÓGICA CORRIGIDA: Criar a lista produtos_json
            produtos_json = []
            for produto in produtos_db:
                produtos_json.append({
                    'id': produto.id_produto,
                    'nome': produto.nome,
                    'codigo': produto.codigo.strip(),
                    'descricao': produto.descricao,
                    'preco': str(produto.preco)
                })
            return jsonify(produtos_json), 200
        except Exception as e:
            return jsonify({'erro': str(e)}), 500

    # Se o pedido for POST, cria um novo produto
    elif request.method == 'POST':
        try:
            dados = request.get_json()
            novo_produto = Produto(
                nome=dados['nome'],
                codigo=dados['codigo'],
                descricao=dados.get('descricao'),
                preco=dados['preco'],
                codigoB=dados.get('codigoB'),
                codigoC=dados.get('codigoC')
            )
            db.session.add(novo_produto)
            db.session.commit()
            return jsonify({'mensagem': 'Produto adicionado com sucesso!'}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 500

# --- ROTA INDIVIDUAL: /api/produtos/<id> (Para ler, editar e apagar um produto) ---
@app.route('/api/produtos/<int:id_produto>', methods=['GET', 'PUT', 'DELETE'])
def produto_por_id_endpoint(id_produto):
    # Se o pedido for GET, retorna um único produto
    if request.method == 'GET':
        try:
            produto = Produto.query.get_or_404(id_produto)
            produto_json = {
                'id': produto.id_produto,
                'nome': produto.nome,
                'codigo': produto.codigo.strip(),
                'descricao': produto.descricao,
                'preco': str(produto.preco)
            }
            return jsonify(produto_json), 200
        except Exception as e:
            return jsonify({'erro': str(e)}), 500
    
    # Se o pedido for PUT, atualiza um produto
    elif request.method == 'PUT':
        try:
            produto_para_atualizar = Produto.query.get_or_404(id_produto)
            dados = request.get_json()
            produto_para_atualizar.nome = dados['nome']
            produto_para_atualizar.codigo = dados['codigo']
            produto_para_atualizar.descricao = dados.get('descricao')
            produto_para_atualizar.preco = dados['preco']
            produto_para_atualizar.codigoB = dados.get('codigoB')
            produto_para_atualizar.codigoC = dados.get('codigoC')
            db.session.commit()
            return jsonify({'mensagem': 'Produto atualizado com sucesso!'}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 500
    
    # Se o pedido for DELETE, apaga um produto
    elif request.method == 'DELETE':
        try:
            produto_para_excluir = Produto.query.get_or_404(id_produto)
            db.session.delete(produto_para_excluir)
            db.session.commit()
            return jsonify({'mensagem': 'Produto excluído com sucesso!'}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 500


# --- Bloco para executar a aplicação ---
if __name__ == '__main__':
    app.run(debug=True)