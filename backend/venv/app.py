from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required
from flask_jwt_extended import JWTManager
from flask_jwt_extended import get_jwt

# Cria a aplicação Flask
app = Flask(__name__)

# --- CONFIGURAÇÃO DO JWT (JSON Web Token) ---
# Escolha uma frase secreta forte e única
app.config["JWT_SECRET_KEY"] = "bolo-de-cenoura-com-chocolate" 
jwt = JWTManager(app)

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
# Certifique-se de que a senha aqui está correta
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:senha123@localhost/estoque_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Cria a instância que fará a ponte com o banco de dados
db = SQLAlchemy(app)


# Tabela de associação para o relacionamento N-N entre Produto e Fornecedor
produto_fornecedor = db.Table('produto_fornecedor',
    db.Column('FK_PRODUTO_Id_produto', db.Integer, db.ForeignKey('produto.Id_produto'), primary_key=True),
    db.Column('FK_FORNECEDOR_id_fornecedor', db.Integer, db.ForeignKey('fornecedor.id_fornecedor'), primary_key=True)
)

produto_natureza = db.Table('produto_natureza',
    db.Column('fk_PRODUTO_Id_produto', db.Integer, db.ForeignKey('produto.Id_produto'), primary_key=True),
    db.Column('fk_NATUREZA_id_natureza', db.Integer, db.ForeignKey('natureza.id_natureza'), primary_key=True)
)





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
    fornecedores = db.relationship('Fornecedor', secondary=produto_fornecedor, back_populates='produtos')
    naturezas = db.relationship('Natureza', secondary=produto_natureza, back_populates='produtos')

    
    
class Fornecedor(db.Model):
    __tablename__ = 'fornecedor'
    id_fornecedor = db.Column(db.Integer, primary_key=True)
    nome = db.Column('Nome', db.String(50), unique=True, nullable=False)
     # Define o relacionamento com Produto
    produtos = db.relationship('Produto', secondary=produto_fornecedor, back_populates='fornecedores')


class Natureza(db.Model):
    __tablename__ = 'natureza'
    id_natureza = db.Column(db.Integer, primary_key=True)
    nome = db.Column('nome', db.String(100), unique=True, nullable=False)
    
    # Define o relacionamento com Produto
    produtos = db.relationship('Produto', secondary=produto_natureza, back_populates='naturezas')
    
    
class Usuario(db.Model):
    __tablename__ = 'usuario'
    id_usuario = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    login = db.Column(db.String(100), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    permissao = db.Column(db.String(100), nullable=False) # 'Administrador' ou 'Usuario'
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    # Método para definir a senha (fazendo o hash)
    def set_password(self, senha):
        self.senha_hash = generate_password_hash(senha)

    # Método para verificar a senha
    def check_password(self, senha):
        return check_password_hash(self.senha_hash, senha)
    

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


# ... (código anterior)

# --- ROTAS DA API PARA FORNECEDORES ---
@app.route('/api/fornecedores', methods=['GET', 'POST'])
def fornecedores_endpoint():
    if request.method == 'GET':
        try:
            fornecedores = Fornecedor.query.all()
            fornecedores_json = [{'id': f.id_fornecedor, 'nome': f.nome} for f in fornecedores]
            return jsonify(fornecedores_json), 200
        except Exception as e:
            return jsonify({'erro': str(e)}), 500

    elif request.method == 'POST':
        try:
            dados = request.get_json()
            novo_fornecedor = Fornecedor(nome=dados['nome'])
            db.session.add(novo_fornecedor)
            db.session.commit()
            return jsonify({'mensagem': 'Fornecedor adicionado com sucesso!'}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 500

@app.route('/api/fornecedores/<int:id_fornecedor>', methods=['PUT', 'DELETE'])
def fornecedor_por_id_endpoint(id_fornecedor):
    try:
        fornecedor = Fornecedor.query.get_or_404(id_fornecedor)

        if request.method == 'PUT':
            # ... (a lógica de PUT continua a mesma)
            dados = request.get_json()
            fornecedor.nome = dados['nome']
            db.session.commit()
            return jsonify({'mensagem': 'Fornecedor atualizado com sucesso!'}), 200

        elif request.method == 'DELETE':
            # --- A LÓGICA DO DESAFIO ---
            # Graças ao relacionamento que criámos, podemos verificar se a lista de produtos não está vazia.
            if fornecedor.produtos:
                return jsonify({'erro': 'Este fornecedor não pode ser excluído pois está associado a um ou mais produtos.'}), 400 # 400 = Bad Request

            # Se a lista estiver vazia, podemos apagar com segurança.
            db.session.delete(fornecedor)
            db.session.commit()
            return jsonify({'mensagem': 'Fornecedor excluído com sucesso!'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500


# ... (código anterior)

# --- ROTAS DA API PARA NATUREZAS ---
@app.route('/api/naturezas', methods=['GET', 'POST'])
def naturezas_endpoint():
    if request.method == 'GET':
        try:
            naturezas = Natureza.query.all()
            naturezas_json = [{'id': n.id_natureza, 'nome': n.nome} for n in naturezas]
            return jsonify(naturezas_json), 200
        except Exception as e:
            return jsonify({'erro': str(e)}), 500

    elif request.method == 'POST':
        try:
            dados = request.get_json()
            nova_natureza = Natureza(nome=dados['nome'])
            db.session.add(nova_natureza)
            db.session.commit()
            return jsonify({'mensagem': 'Natureza adicionada com sucesso!'}), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 500

@app.route('/api/naturezas/<int:id_natureza>', methods=['PUT', 'DELETE'])
def natureza_por_id_endpoint(id_natureza):
    try:
        natureza = Natureza.query.get_or_404(id_natureza)

        if request.method == 'PUT':
            dados = request.get_json()
            natureza.nome = dados['nome']
            db.session.commit()
            return jsonify({'mensagem': 'Natureza atualizada com sucesso!'}), 200

        elif request.method == 'DELETE':
            # Verifica se a natureza está em uso antes de excluir
            if natureza.produtos:
                return jsonify({'erro': 'Esta natureza não pode ser excluída pois está associada a um ou mais produtos.'}), 400

            db.session.delete(natureza)
            db.session.commit()
            return jsonify({'mensagem': 'Natureza excluída com sucesso!'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500


# --- ROTAS DA API PARA USUÁRIOS ---
@app.route('/api/usuarios', methods=['GET', 'POST'])
def usuarios_endpoint():
    # Rota para listar todos os usuários (sem a senha, claro)
    if request.method == 'GET':
        try:
            usuarios = Usuario.query.all()
            usuarios_json = []
            for u in usuarios:
                usuarios_json.append({
                    'id': u.id_usuario,
                    'nome': u.nome,
                    'login': u.login,
                    'permissao': u.permissao,
                    'ativo': u.ativo
                })
            return jsonify(usuarios_json), 200
        except Exception as e:
            return jsonify({'erro': str(e)}), 500

    # Rota para cadastrar um novo usuário
    elif request.method == 'POST':
        # Esta linha verifica se há um token JWT válido no pedido.
        # Se não houver, o código abaixo não será executado.
        jwt_required()
        
        # TODO: Adicionar verificação de permissão de Administrador
        try:
            # Pega nas informações extras que guardámos no token
            claims = get_jwt()
            # Verifica se a permissão é de Administrador
            if claims.get('permissao') != 'Administrador':
                return jsonify({"erro": "Acesso negado: permissão de Administrador necessária."}), 403 # 403 = Forbidden

            # Se a verificação passar, o resto do código é executado
            dados = request.get_json()
            
            # Validação básica
            if 'login' not in dados or 'senha' not in dados or 'nome' not in dados or 'permissao' not in dados:
                return jsonify({'erro': 'Dados incompletos'}), 400

            novo_usuario = Usuario(
                nome=dados['nome'],
                login=dados['login'],
                permissao=dados['permissao']
            )
            # Usa o método que criámos para guardar a senha com hash
            novo_usuario.set_password(dados['senha'])
            
            db.session.add(novo_usuario)
            db.session.commit()
            
            return jsonify({'mensagem': 'Usuário criado com sucesso!'}), 201

        except Exception as e:
            db.session.rollback()
            return jsonify({'erro': str(e)}), 500

# ... (depois dos endpoints de Usuários)

# --- ROTA PARA LOGIN ---
@app.route('/api/login', methods=['POST'])
def login_endpoint():
    try:
        # Pega no login e senha enviados no corpo do pedido
        dados = request.get_json()
        login = dados.get('login', None)
        senha = dados.get('senha', None)

        # Busca o usuário no banco de dados pelo login e verifica se ele está ativo
        usuario = Usuario.query.filter_by(login=login, ativo=True).first()

        # Verifica se o usuário existe E se a senha está correta
        if usuario and usuario.check_password(senha):
            # Cria o token de acesso com a identidade do usuário e a sua permissão
            # A identidade pode ser qualquer coisa, mas o ID é uma boa prática.
            # As 'additional_claims' permitem-nos guardar informação extra no token.
            access_token = create_access_token(
                identity=usuario.id_usuario, 
                additional_claims={'permissao': usuario.permissao}
            )
            # Retorna o token para o cliente
            return jsonify(access_token=access_token), 200
        else:
            # Se as credenciais estiverem erradas, retorna um erro de não autorizado
            return jsonify({"erro": "Credenciais inválidas"}), 401

    except Exception as e:
        return jsonify({'erro': str(e)}), 500


# ... (resto do ficheiro)
# --- Bloco para executar a aplicação ---
if __name__ == '__main__':
    app.run(debug=True)