# ==============================================================================
# IMPORTS DAS BIBLIOTECAS
# ==============================================================================
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
    get_jwt,
    JWTManager
)
from datetime import datetime
from sqlalchemy import case

# ==============================================================================
# CONFIGURAÇÃO INICIAL
# ==============================================================================

# Cria a aplicação Flask
app = Flask(__name__)

# --- CONFIGURAÇÃO DO JWT (JSON Web Token) ---
# Em produção, esta chave deve ser guardada de forma segura (ex: variável de ambiente)
app.config["JWT_SECRET_KEY"] = "minha-chave-super-secreta-para-o-projeto-de-estoque"
jwt = JWTManager(app)

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:senha123@localhost/estoque_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Cria a instância do SQLAlchemy
db = SQLAlchemy(app)


# ==============================================================================
# TABELAS DE ASSOCIAÇÃO (Muitos-para-Muitos)
# ==============================================================================

produto_fornecedor = db.Table('produto_fornecedor',
    db.Column('FK_PRODUTO_Id_produto', db.Integer, db.ForeignKey('produto.Id_produto'), primary_key=True),
    db.Column('FK_FORNECEDOR_id_fornecedor', db.Integer, db.ForeignKey('fornecedor.id_fornecedor'), primary_key=True)
)

produto_natureza = db.Table('produto_natureza',
    db.Column('fk_PRODUTO_Id_produto', db.Integer, db.ForeignKey('produto.Id_produto'), primary_key=True),
    db.Column('fk_NATUREZA_id_natureza', db.Integer, db.ForeignKey('natureza.id_natureza'), primary_key=True)
)


# ==============================================================================
# MODELOS DO BANCO DE DADOS (ENTITIES)
# ==============================================================================

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
    produtos = db.relationship('Produto', secondary=produto_fornecedor, back_populates='fornecedores')

class Natureza(db.Model):
    __tablename__ = 'natureza'
    id_natureza = db.Column(db.Integer, primary_key=True)
    nome = db.Column('nome', db.String(100), unique=True, nullable=False)
    produtos = db.relationship('Produto', secondary=produto_natureza, back_populates='naturezas')

class MovimentacaoEstoque(db.Model):
    __tablename__ = 'mov_estoque'
    id_movimentacao = db.Column(db.Integer, primary_key=True)
    id_produto = db.Column(db.Integer, db.ForeignKey('produto.Id_produto'), nullable=False)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id_usuario'), nullable=False)
    data_hora = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    quantidade = db.Column(db.Integer, nullable=False)
    tipo = db.Column(db.Enum("Entrada", "Saida"), nullable=False)
    motivo_saida = db.Column(db.String(200))
    
    produto = db.relationship('Produto')
    usuario = db.relationship('Usuario')

class Usuario(db.Model):
    __tablename__ = 'usuario'
    id_usuario = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    login = db.Column(db.String(100), unique=True, nullable=False)
    senha_hash = db.Column(db.String(255), nullable=False)
    permissao = db.Column(db.String(100), nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    def set_password(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def check_password(self, senha):
        return check_password_hash(self.senha_hash, senha)


# ==============================================================================
# FUNÇÕES AUXILIARES (HELPERS)
# ==============================================================================

def calcular_saldo_produto(id_produto):
    """Calcula o saldo de estoque de um produto somando as entradas e subtraindo as saídas."""
    saldo = db.session.query(
        db.func.sum(
            case(
                (MovimentacaoEstoque.tipo == 'Entrada', MovimentacaoEstoque.quantidade),
                (MovimentacaoEstoque.tipo == 'Saida', -MovimentacaoEstoque.quantidade)
            )
        )
    ).filter(MovimentacaoEstoque.id_produto == id_produto).scalar() or 0
    return saldo


# ==============================================================================
# ROTAS DA API (ENDPOINTS)
# ==============================================================================

# --- ROTAS DE PRODUTOS ---

@app.route('/api/produtos', methods=['GET'])
@jwt_required()
def get_todos_produtos():
    """Retorna uma lista de todos os produtos."""
    try:
        produtos_db = Produto.query.all()
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

@app.route('/api/produtos', methods=['POST'])
@jwt_required()
def add_novo_produto():
    """Cria um novo produto no sistema."""
    try:
        dados = request.get_json()
        required_fields = ['nome', 'codigo', 'preco']
        if not all(field in dados for field in required_fields):
            return jsonify({'erro': 'Campos obrigatórios em falta: nome, codigo, preco'}), 400

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

@app.route('/api/produtos/<int:id_produto>', methods=['GET', 'PUT', 'DELETE'])
@jwt_required()
def produto_por_id_endpoint(id_produto):
    """Lida com operações para um produto específico (ler, editar, apagar)."""
    try:
        produto = Produto.query.get_or_404(id_produto)

        if request.method == 'GET':
            produto_json = {
                'id': produto.id_produto,
                'nome': produto.nome,
                'codigo': produto.codigo.strip(),
                'descricao': produto.descricao,
                'preco': str(produto.preco)
            }
            return jsonify(produto_json), 200
        
        elif request.method == 'PUT':
            dados = request.get_json()
            if 'nome' not in dados or 'codigo' not in dados or 'preco' not in dados:
                return jsonify({'erro': 'Campos obrigatórios em falta: nome, codigo, preco'}), 400
            
            produto.nome = dados['nome']
            produto.codigo = dados['codigo']
            produto.descricao = dados.get('descricao')
            produto.preco = dados['preco']
            produto.codigoB = dados.get('codigoB')
            produto.codigoC = dados.get('codigoC')
            db.session.commit()
            return jsonify({'mensagem': 'Produto atualizado com sucesso!'}), 200
        
        elif request.method == 'DELETE':
            db.session.delete(produto)
            db.session.commit()
            return jsonify({'mensagem': 'Produto excluído com sucesso!'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500

# Adicione aqui as outras rotas (Fornecedores, Naturezas, Estoque, Usuários, Login)
# seguindo o mesmo padrão de organização e refinamento.
# ... (código anterior)

# --- ROTA PARA BUSCAR UM PRODUTO PELO CÓDIGO ---
@app.route('/api/produtos/codigo/<string:codigo>', methods=['GET'])
@jwt_required()
def get_produto_por_codigo(codigo):
    """Busca um produto específico pelo seu campo 'Codigo'."""
    try:
        # O .strip() é importante caso o campo no banco seja CHAR, para remover espaços
        produto = Produto.query.filter_by(codigo=codigo.strip()).first()
        
        if produto:
            # Se encontrou o produto, retorna os seus dados
            produto_json = {
                'id': produto.id_produto,
                'nome': produto.nome,
                'codigo': produto.codigo.strip(),
                'descricao': produto.descricao,
                'preco': str(produto.preco)
            }
            return jsonify(produto_json), 200
        else:
            # Se não encontrou, retorna um erro 404 (Not Found)
            return jsonify({'erro': 'Produto com este código não encontrado.'}), 404
            
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

# ... (resto do ficheiro)
# --- ROTAS DE ESTOQUE ---

@app.route('/api/produtos/<int:id_produto>/estoque', methods=['GET'])
@jwt_required()
def get_saldo_estoque(id_produto):
    """Calcula e retorna o saldo atual de um produto."""
    try:
        # Chama a função auxiliar para evitar código duplicado
        saldo_calculado = calcular_saldo_produto(id_produto)
        return jsonify({'id_produto': id_produto, 'saldo_atual': saldo_calculado}), 200
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/api/estoque/entrada', methods=['POST'])
@jwt_required()
def registrar_entrada():
    """Registra uma nova entrada de estoque para um produto."""
    try:
        dados = request.get_json()
        if 'id_produto' not in dados or 'quantidade' not in dados:
            return jsonify({'erro': 'Campos obrigatórios em falta: id_produto, quantidade'}), 400

        id_usuario_logado = get_jwt_identity()
        nova_entrada = MovimentacaoEstoque(
            id_produto=dados['id_produto'],
            quantidade=dados['quantidade'],
            id_usuario=id_usuario_logado,
            tipo='Entrada'
        )
        db.session.add(nova_entrada)
        db.session.commit()
        return jsonify({'mensagem': 'Entrada de estoque registada com sucesso!'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500

@app.route('/api/estoque/saida', methods=['POST'])
@jwt_required()
def registrar_saida():
    """Registra uma nova saída de estoque para um produto."""
    try:
        dados = request.get_json()
        required_fields = ['id_produto', 'quantidade', 'motivo_saida']
        if not all(field in dados and dados[field] for field in required_fields):
            return jsonify({'erro': 'Campos obrigatórios em falta: id_produto, quantidade, motivo_saida'}), 400

        id_produto = dados['id_produto']
        quantidade_saida = dados['quantidade']
        
        saldo_atual = calcular_saldo_produto(id_produto)
        if saldo_atual < quantidade_saida:
            return jsonify({'erro': f'Estoque insuficiente. Saldo atual: {saldo_atual}'}), 400

        id_usuario_logado = get_jwt_identity()
        nova_saida = MovimentacaoEstoque(
            id_produto=id_produto,
            quantidade=quantidade_saida,
            id_usuario=id_usuario_logado,
            tipo='Saida',
            motivo_saida=dados.get('motivo_saida')
        )
        db.session.add(nova_saida)
        db.session.commit()
        return jsonify({'mensagem': 'Saída de estoque registada com sucesso!'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500

# --- ROTAS DE LOGIN E USUÁRIOS ---

@app.route('/api/login', methods=['POST'])
def login_endpoint():
    """Autentica um usuário e retorna um token de acesso."""
    try:
        dados = request.get_json()
        if not dados or 'login' not in dados or 'senha' not in dados:
            return jsonify({'erro': 'Campos de login e senha são obrigatórios'}), 400

        login = dados.get('login')
        senha = dados.get('senha')

        usuario = Usuario.query.filter_by(login=login, ativo=True).first()

        if usuario and usuario.check_password(senha):
            access_token = create_access_token(
                identity=str(usuario.id_usuario),
                additional_claims={'permissao': usuario.permissao}
            )
            return jsonify(access_token=access_token), 200
        else:
            return jsonify({"erro": "Credenciais inválidas"}), 401
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

# (Por uma questão de brevidade, omiti as rotas de Fornecedores e Naturezas,
# mas elas seguiriam exatamente o mesmo padrão de refinamento.)

# ==============================================================================
# Bloco de Execução Principal
# ==============================================================================
if __name__ == '__main__':
    app.run(debug=True)