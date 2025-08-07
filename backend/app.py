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
from sqlalchemy import case, or_
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func
import csv
import io
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
    """Retorna uma lista de todos os produtos, incluindo os nomes dos seus fornecedores e naturezas."""
    try:
        termo_busca = request.args.get('search')
        # O .options(joinedload(...)) é uma otimização para carregar os dados relacionados
        # de forma mais eficiente, evitando múltiplas consultas ao banco.
        query = Produto.query.options(joinedload(Produto.fornecedores), joinedload(Produto.naturezas))
        
        if termo_busca:
            query = query.filter(
                or_(
                    Produto.nome.ilike(f"%{termo_busca}%"),
                    Produto.codigo.ilike(f"%{termo_busca}%")
                )
            )

        produtos_db = query.all()
        produtos_json = []
        for produto in produtos_db:
            # --- MUDANÇA PRINCIPAL AQUI ---
            # Cria uma string com os nomes dos fornecedores, separados por vírgula
            fornecedores_str = ", ".join([f.nome for f in produto.fornecedores])
            # Cria uma string com os nomes das naturezas
            naturezas_str = ", ".join([n.nome for n in produto.naturezas])

            produtos_json.append({
                'id': produto.id_produto,
                'nome': produto.nome,
                'codigo': produto.codigo.strip(),
                'descricao': produto.descricao,
                'preco': str(produto.preco),
                'codigoB': produto.codigoB,
                'codigoC': produto.codigoC,
                'fornecedores': fornecedores_str, # <-- Novo campo
                'naturezas': naturezas_str      # <-- Novo campo
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
        if not all(field in dados and dados[field] for field in required_fields):
            return jsonify({'erro': 'Campos obrigatórios (nome, codigo, preco) não podem estar vazios.'}), 400
        
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
        
        return jsonify({
            'mensagem': 'Produto adicionado com sucesso!',
            'id_produto_criado': novo_produto.id_produto
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500



@app.route('/api/produtos/importar', methods=['POST'])
@jwt_required()
def importar_produtos_csv():
    """
    Processa um ficheiro CSV para cadastrar produtos em massa.
    Deteta automaticamente se o separador é vírgula ou ponto e vírgula.
    """
    if 'file' not in request.files:
        return jsonify({'erro': 'Nenhum ficheiro enviado.'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'erro': 'Nome de ficheiro vazio.'}), 400

    sucesso_count = 0
    erros = []
    
    try:
        # Lê o conteúdo do ficheiro em memória
        stream_content = file.stream.read().decode("UTF-8")
        stream = io.StringIO(stream_content, newline=None)

        # --- ALTERAÇÃO AQUI: Detetar o delimitador ---
        # Lemos a primeira linha para ver qual separador ela usa
        header = stream.readline()
        stream.seek(0) # Voltamos ao início do ficheiro
        
        # Se a primeira linha contiver um ';', usamos esse como separador. Senão, usamos a vírgula.
        delimiter = ';' if ';' in header else ','
        
        csv_reader = csv.DictReader(stream, delimiter=delimiter)
        # --- FIM DA ALTERAÇÃO ---

        for linha_num, linha in enumerate(csv_reader, start=2):
            try:
                codigo = linha.get('codigo', '').strip()
                nome = linha.get('nome', '').strip()
                preco = linha.get('preco', '').strip()

                if not codigo or not nome or not preco:
                    erros.append(f"Linha {linha_num}: Campos obrigatórios (codigo, nome, preco) em falta.")
                    continue

                produto_existente = Produto.query.filter_by(codigo=codigo).first()
                if produto_existente:
                    erros.append(f"Linha {linha_num}: Código '{codigo}' já existe no sistema.")
                    continue

                novo_produto = Produto(
                    codigo=codigo,
                    nome=nome,
                    preco=preco.replace(',', '.'),
                    descricao=linha.get('descricao', '').strip()
                )

                fornecedores_nomes = [fn.strip() for fn in linha.get('fornecedores_nomes', '').split(',') if fn.strip()]
                if fornecedores_nomes:
                    fornecedores_db = Fornecedor.query.filter(Fornecedor.nome.in_(fornecedores_nomes)).all()
                    novo_produto.fornecedores.extend(fornecedores_db)

                naturezas_nomes = [nn.strip() for nn in linha.get('naturezas_nomes', '').split(',') if nn.strip()]
                if naturezas_nomes:
                    naturezas_db = Natureza.query.filter(Natureza.nome.in_(naturezas_nomes)).all()
                    novo_produto.naturezas.extend(naturezas_db)

                db.session.add(novo_produto)
                sucesso_count += 1

            except Exception as e_interno:
                # Captura erros inesperados por linha (ex: nome de coluna errado)
                erros.append(f"Linha {linha_num}: Erro ao processar - {e_interno}. Verifique os nomes das colunas.")
                # Para não parar a importação inteira, continuamos para a próxima linha
                continue

        db.session.commit()
        
        return jsonify({
            'mensagem': 'Importação concluída!',
            'produtos_importados': sucesso_count,
            'erros': erros
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': f'Ocorreu um erro geral ao processar o ficheiro: {str(e)}'}), 500



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
                'preco': str(produto.preco),
                'codigoB': produto.codigoB,
                'codigoC': produto.codigoC,
                'fornecedores': [{'id': f.id_fornecedor, 'nome': f.nome} for f in produto.fornecedores],
                'naturezas': [{'id': n.id_natureza, 'nome': n.nome} for n in produto.naturezas]
            }
            return jsonify(produto_json), 200
        
        elif request.method == 'PUT':
            dados = request.get_json()
            
            # Atualiza os campos diretos do produto
            produto.nome = dados['nome']
            produto.codigo = dados['codigo']
            produto.descricao = dados.get('descricao')
            produto.preco = dados['preco']
            produto.codigoB = dados.get('codigoB')
            produto.codigoC = dados.get('codigoC')

            # --- LÓGICA DE SINCRONIZAÇÃO DE ASSOCIAÇÕES ---
            if 'fornecedores_ids' in dados:
                produto.fornecedores.clear() # Limpa as associações antigas
                ids_fornecedores = dados['fornecedores_ids']
                if ids_fornecedores:
                    novos_fornecedores = Fornecedor.query.filter(Fornecedor.id_fornecedor.in_(ids_fornecedores)).all()
                    produto.fornecedores = novos_fornecedores # Adiciona as novas

            if 'naturezas_ids' in dados:
                produto.naturezas.clear() # Limpa as associações antigas
                ids_naturezas = dados['naturezas_ids']
                if ids_naturezas:
                    novas_naturezas = Natureza.query.filter(Natureza.id_natureza.in_(ids_naturezas)).all()
                    produto.naturezas = novas_naturezas # Adiciona as novas

            db.session.commit()
            return jsonify({'mensagem': 'Produto atualizado com sucesso!'}), 200
        
        elif request.method == 'DELETE':
            movimentacao_existente = MovimentacaoEstoque.query.filter_by(id_produto=id_produto).first()
            if movimentacao_existente:
                return jsonify({'erro': 'Este produto não pode ser excluído, pois possui um histórico de movimentações no estoque.'}), 400

            db.session.delete(produto)
            db.session.commit()
            return jsonify({'mensagem': 'Produto excluído com sucesso!'}), 200
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500
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
    
    
    
# Dentro do app.py

@app.route('/api/produtos/<int:id_produto>/fornecedores', methods=['POST'])
@jwt_required()
def adicionar_fornecedor_ao_produto(id_produto):
    """Associa um fornecedor existente a um produto existente."""
    try:
        # Pega no ID do fornecedor enviado no corpo do pedido
        dados = request.get_json()
        if 'id_fornecedor' not in dados:
            return jsonify({'erro': 'O ID do fornecedor é obrigatório.'}), 400

        id_fornecedor = dados['id_fornecedor']

        # Encontra o produto e o fornecedor na base de dados
        produto = Produto.query.get_or_404(id_produto)
        fornecedor = Fornecedor.query.get_or_404(id_fornecedor)

        # A "mágica" do SQLAlchemy: basta adicionar o objeto à lista.
        # Ele irá encarregar-se de criar a linha na tabela de junção.
        if fornecedor not in produto.fornecedores:
            produto.fornecedores.append(fornecedor)
            db.session.commit()
            return jsonify({'mensagem': 'Fornecedor associado ao produto com sucesso!'}), 200
        else:
            return jsonify({'mensagem': 'Fornecedor já está associado a este produto.'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500



# Dentro do app.py

@app.route('/api/produtos/<int:id_produto>/naturezas', methods=['POST'])
@jwt_required()
def adicionar_natureza_ao_produto(id_produto):
    """Associa uma natureza existente a um produto existente."""
    try:
        dados = request.get_json()
        if 'id_natureza' not in dados:
            return jsonify({'erro': 'O ID da natureza é obrigatório.'}), 400

        id_natureza = dados['id_natureza']

        produto = Produto.query.get_or_404(id_produto)
        natureza = Natureza.query.get_or_404(id_natureza)

        if natureza not in produto.naturezas:
            produto.naturezas.append(natureza)
            db.session.commit()
            return jsonify({'mensagem': 'Natureza associada ao produto com sucesso!'}), 200
        else:
            return jsonify({'mensagem': 'Natureza já está associada a este produto.'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500
    
    
    
    
# Dentro do app.py

@app.route('/api/produtos/<int:id_produto>/fornecedores/<int:id_fornecedor>', methods=['DELETE'])
@jwt_required()
def remover_fornecedor_do_produto(id_produto, id_fornecedor):
    """Remove a associação entre um fornecedor e um produto."""
    try:
        produto = Produto.query.get_or_404(id_produto)
        fornecedor = Fornecedor.query.get_or_404(id_fornecedor)

        if fornecedor in produto.fornecedores:
            produto.fornecedores.remove(fornecedor)
            db.session.commit()
            return jsonify({'mensagem': 'Associação com fornecedor removida com sucesso!'}), 200
        else:
            return jsonify({'erro': 'Fornecedor não está associado a este produto.'}), 404

    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500

@app.route('/api/produtos/<int:id_produto>/naturezas/<int:id_natureza>', methods=['DELETE'])
@jwt_required()
def remover_natureza_do_produto(id_produto, id_natureza):
    """Remove a associação entre uma natureza e um produto."""
    try:
        produto = Produto.query.get_or_404(id_produto)
        natureza = Natureza.query.get_or_404(id_natureza)

        if natureza in produto.naturezas:
            produto.naturezas.remove(natureza)
            db.session.commit()
            return jsonify({'mensagem': 'Associação com natureza removida com sucesso!'}), 200
        else:
            return jsonify({'erro': 'Natureza não está associada a este produto.'}), 404

    except Exception as e:
        db.session.rollback()
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



@app.route('/api/estoque/saldos', methods=['GET'])
@jwt_required()
def get_saldos_estoque():
    """Calcula e retorna o saldo de estoque para todos os produtos."""
    try:
        produtos = Produto.query.all()
        saldos_json = []
        for produto in produtos:
            saldo_atual = calcular_saldo_produto(produto.id_produto)
            saldos_json.append({
                'id_produto': produto.id_produto,
                # --- CORREÇÃO AQUI ---
                # Lida com a possibilidade de o código ou nome serem nulos no banco de dados
                'codigo': produto.codigo.strip() if produto.codigo else '',
                'nome': produto.nome if produto.nome else 'Produto sem nome',
                'saldo_atual': saldo_atual
            })
        return jsonify(saldos_json), 200
    except Exception as e:
        # Para debug, é útil imprimir o erro no terminal do servidor
        print(f"!!! ERRO em /api/estoque/saldos: {e}")
        # Retorna uma mensagem de erro genérica para o front-end
        return jsonify({'erro': 'Ocorreu um erro interno no servidor ao calcular os saldos.'}), 500

@app.route('/api/movimentacoes', methods=['GET'])
@jwt_required()
def get_todas_movimentacoes():
    """
    Retorna uma lista de todas as movimentações de estoque (entradas e saídas),
    incluindo dados do produto e do usuário associados.
    Suporta filtragem por tipo de movimentação.
    """
    try:
        # Pega o parâmetro de filtro da URL, ex: /api/movimentacoes?tipo=Entrada
        filtro_tipo = request.args.get('tipo')

        # Começa a consulta base, usando joinedload para otimizar a busca dos
        # dados relacionados de Produto e Usuario em uma única viagem ao banco.
        query = MovimentacaoEstoque.query.options(
            joinedload(MovimentacaoEstoque.produto),
            joinedload(MovimentacaoEstoque.usuario)
        ).order_by(MovimentacaoEstoque.data_hora.desc()) # Ordena pelas mais recentes

        # Aplica o filtro se ele foi fornecido na URL
        if filtro_tipo and filtro_tipo in ["Entrada", "Saida"]:
            query = query.filter(MovimentacaoEstoque.tipo == filtro_tipo)

        movimentacoes = query.all()

        resultado_json = []
        for mov in movimentacoes:
            resultado_json.append({
                'id': mov.id_movimentacao,
                'data_hora': mov.data_hora.strftime('%d/%m/%Y %H:%M:%S'),
                'tipo': mov.tipo,
                'quantidade': mov.quantidade,
                'motivo_saida': mov.motivo_saida,
                # Adiciona os dados relacionados para facilitar a exibição no front-end
                'produto_codigo': mov.produto.codigo.strip() if mov.produto else 'N/A',
                'produto_nome': mov.produto.nome if mov.produto else 'Produto Excluído',
                'usuario_nome': mov.usuario.nome if mov.usuario else 'Usuário Excluído'
            })
        
        return jsonify(resultado_json), 200

    except Exception as e:
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
    
    
    
    
# Dentro do app.py, na secção de rotas de Usuários

@app.route('/api/usuario/me', methods=['GET'])
@jwt_required()
def get_usuario_logado():
    """Retorna as informações do usuário logado (dono do token)."""
    # A função get_jwt_identity() devolve o que guardámos como 'identity' (o nosso id_usuario)
    id_usuario_logado = get_jwt_identity()
    
    # Buscamos o usuário na base de dados com esse ID
    usuario = Usuario.query.get(id_usuario_logado)
    
    if not usuario:
        return jsonify({"erro": "Usuário não encontrado"}), 404

    usuario_json = {
        'id': usuario.id_usuario,
        'nome': usuario.nome,
        'login': usuario.login,
        'permissao': usuario.permissao
    }
    return jsonify(usuario_json), 200

# (Por uma questão de brevidade, omiti as rotas de Fornecedores e Naturezas,
# mas elas seguiriam exatamente o mesmo padrão de refinamento.)




# Dentro do seu app.py

# ==============================================================================
# ROTAS DA API PARA FORNECEDORES
# ==============================================================================

@app.route('/api/fornecedores', methods=['GET'])
@jwt_required()
def get_todos_fornecedores():
    """Retorna uma lista de todos os fornecedores."""
    try:
        fornecedores = Fornecedor.query.order_by(Fornecedor.nome).all()
        fornecedores_json = [{'id': f.id_fornecedor, 'nome': f.nome} for f in fornecedores]
        return jsonify(fornecedores_json), 200
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/api/fornecedores', methods=['POST'])
@jwt_required()
def add_novo_fornecedor():
    """Cria um novo fornecedor."""
    try:
        dados = request.get_json()
        if 'nome' not in dados or not dados['nome'].strip():
            return jsonify({'erro': 'O nome do fornecedor é obrigatório.'}), 400

        novo_fornecedor = Fornecedor(nome=dados['nome'])
        db.session.add(novo_fornecedor)
        db.session.commit()
        return jsonify({'mensagem': 'Fornecedor adicionado com sucesso!'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500

@app.route('/api/fornecedores/<int:id_fornecedor>', methods=['GET', 'PUT', 'DELETE'])
@jwt_required()
def fornecedor_por_id_endpoint(id_fornecedor):
    """Lida com operações para um fornecedor específico (ler, editar, apagar)."""
    try:
        fornecedor = Fornecedor.query.get_or_404(id_fornecedor)

        # --- NOVO BLOCO DE CÓDIGO ---
        # Lógica para o método GET (Ler um por ID)
        if request.method == 'GET':
            return jsonify({
                'id': fornecedor.id_fornecedor,
                'nome': fornecedor.nome
            }), 200
        # --- FIM DO NOVO BLOCO ---

        elif request.method == 'PUT':
            dados = request.get_json()
            if 'nome' not in dados or not dados['nome'].strip():
                return jsonify({'erro': 'O nome do fornecedor é obrigatório.'}), 400
            fornecedor.nome = dados['nome']
            db.session.commit()
            return jsonify({'mensagem': 'Fornecedor atualizado com sucesso!'}), 200

        elif request.method == 'DELETE':
            if fornecedor.produtos:
                return jsonify({'erro': 'Este fornecedor não pode ser excluído pois está associado a um ou mais produtos.'}), 400
            
            db.session.delete(fornecedor)
            db.session.commit()
            return jsonify({'mensagem': 'Fornecedor excluído com sucesso!'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500
    
    
    
    
# Dentro do seu app.py

# ==============================================================================
# ROTAS DA API PARA NATUREZAS
# ==============================================================================

@app.route('/api/naturezas', methods=['GET'])
@jwt_required()
def get_todas_naturezas():
    """Retorna uma lista de todas as naturezas."""
    try:
        naturezas = Natureza.query.order_by(Natureza.nome).all()
        naturezas_json = [{'id': n.id_natureza, 'nome': n.nome} for n in naturezas]
        return jsonify(naturezas_json), 200
    except Exception as e:
        return jsonify({'erro': str(e)}), 500

@app.route('/api/naturezas', methods=['POST'])
@jwt_required()
def add_nova_natureza():
    """Cria uma nova natureza."""
    try:
        dados = request.get_json()
        if 'nome' not in dados or not dados['nome'].strip():
            return jsonify({'erro': 'O nome da natureza é obrigatório.'}), 400

        nova_natureza = Natureza(nome=dados['nome'])
        db.session.add(nova_natureza)
        db.session.commit()
        return jsonify({'mensagem': 'Natureza adicionada com sucesso!'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500

@app.route('/api/naturezas/<int:id_natureza>', methods=['GET', 'PUT', 'DELETE'])
@jwt_required()
def natureza_por_id_endpoint(id_natureza):
    """Lida com operações para uma natureza específica (ler, editar, apagar)."""
    try:
        natureza = Natureza.query.get_or_404(id_natureza)

        # --- NOVO BLOCO DE CÓDIGO ---
        # Lógica para o método GET (Ler uma por ID)
        if request.method == 'GET':
            return jsonify({
                'id': natureza.id_natureza,
                'nome': natureza.nome
            }), 200
        # --- FIM DO NOVO BLOCO ---

        elif request.method == 'PUT':
            dados = request.get_json()
            if 'nome' not in dados or not dados['nome'].strip():
                return jsonify({'erro': 'O nome da natureza é obrigatório.'}), 400
            natureza.nome = dados['nome']
            db.session.commit()
            return jsonify({'mensagem': 'Natureza atualizada com sucesso!'}), 200

        elif request.method == 'DELETE':
            if natureza.produtos:
                return jsonify({'erro': 'Esta natureza não pode ser excluída pois está associada a um ou mais produtos.'}), 400
            
            db.session.delete(natureza)
            db.session.commit()
            return jsonify({'mensagem': 'Natureza excluída com sucesso!'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500


# TRECHO PARA SUBSTITUIR a função usuarios_endpoint em app.py

# ==============================================================================
# ROTAS DA API PARA USUÁRIOS
# ==============================================================================

@app.route('/api/usuarios', methods=['GET'])
@jwt_required() # Protege a rota, exigindo um token
def get_todos_usuarios():
    """Retorna uma lista de todos os usuários."""
    try:
        # Verifica se o usuário logado é um Administrador
        claims = get_jwt()
        if claims.get('permissao') != 'Administrador':
            return jsonify({"erro": "Acesso negado: permissão de Administrador necessária."}), 403

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

@app.route('/api/usuarios', methods=['POST'])
@jwt_required() # Protege a rota, exigindo um token
def add_novo_usuario():
    """Cria um novo usuário."""
    try:
        # Verifica se o usuário logado é um Administrador
        claims = get_jwt()
        if claims.get('permissao') != 'Administrador':
            return jsonify({"erro": "Acesso negado: permissão de Administrador necessária."}), 403

        dados = request.get_json()
        if 'login' not in dados or 'senha' not in dados or 'nome' not in dados or 'permissao' not in dados:
            return jsonify({'erro': 'Dados incompletos'}), 400

        novo_usuario = Usuario(
            nome=dados['nome'],
            login=dados['login'],
            permissao=dados['permissao']
        )
        novo_usuario.set_password(dados['senha'])
        
        db.session.add(novo_usuario)
        db.session.commit()
        
        return jsonify({'mensagem': 'Usuário criado com sucesso!'}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500
    
    
@app.route('/api/usuarios/<int:id_usuario>', methods=['GET', 'PUT', 'DELETE'])
@jwt_required()
def usuario_por_id_endpoint(id_usuario):
    """Lida com operações para um usuário específico (ler, editar, desativar)."""
    # Garante que apenas administradores podem mexer nos usuários
    claims = get_jwt()
    if claims.get('permissao') != 'Administrador':
        return jsonify({"erro": "Acesso negado: permissão de Administrador necessária."}), 403
    
    try:
        usuario = Usuario.query.get_or_404(id_usuario)

        # ---- LER UM USUÁRIO (GET) ----
        if request.method == 'GET':
            return jsonify({
                'id': usuario.id_usuario,
                'nome': usuario.nome,
                'login': usuario.login,
                'permissao': usuario.permissao,
                'ativo': usuario.ativo
            }), 200

        # ---- EDITAR UM USUÁRIO (PUT) ----
        elif request.method == 'PUT':
            dados = request.get_json()
            if not dados or 'nome' not in dados or 'login' not in dados or 'permissao' not in dados:
                return jsonify({'erro': 'Dados incompletos para atualização'}), 400

            # Atualiza os dados básicos
            usuario.nome = dados['nome']
            usuario.login = dados['login']
            usuario.permissao = dados['permissao']
            
            # Atualiza a senha APENAS se uma nova for fornecida
            if 'senha' in dados and dados['senha']:
                usuario.set_password(dados['senha'])
            
            db.session.commit()
            return jsonify({'mensagem': 'Usuário atualizado com sucesso!'}), 200

        # ---- DESATIVAR/REATIVAR UM USUÁRIO (DELETE) ----
        elif request.method == 'DELETE':
            # Implementação de Soft Delete
            # Em vez de apagar, apenas mudamos o status 'ativo'
            usuario.ativo = not usuario.ativo # Inverte o status atual
            db.session.commit()
            
            status = "desativado" if not usuario.ativo else "reativado"
            return jsonify({'mensagem': f'Usuário {status} com sucesso!'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'erro': str(e)}), 500
    
    
    
# ==============================================================================
#          ROTAS DA API PARA DASHBOARD E OUTRAS FUNÇÕES
# ==============================================================================



@app.route('/api/dashboard/kpis', methods=['GET'])
@jwt_required()
def get_dashboard_kpis():
    """Calcula e retorna os principais indicadores (KPIs) para o dashboard."""
    try:
        # 1. Total de produtos cadastrados
        total_produtos = db.session.query(func.count(Produto.id_produto)).scalar()

        # 2. Total de fornecedores
        total_fornecedores = db.session.query(func.count(Fornecedor.id_fornecedor)).scalar()

        # 3. Valor total do estoque (mais complexo)
        # Subquery para calcular o saldo de cada produto
        subquery_saldos = db.session.query(
            MovimentacaoEstoque.id_produto,
            func.sum(
                case(
                    (MovimentacaoEstoque.tipo == 'Entrada', MovimentacaoEstoque.quantidade),
                    (MovimentacaoEstoque.tipo == 'Saida', -MovimentacaoEstoque.quantidade)
                )
            ).label('saldo')
        ).group_by(MovimentacaoEstoque.id_produto).subquery()

        # Query principal que multiplica o saldo de cada produto pelo seu preço
        query_valor_total = db.session.query(
            func.sum(Produto.preco * subquery_saldos.c.saldo)
        ).join(
            subquery_saldos, Produto.id_produto == subquery_saldos.c.id_produto
        )
        
        valor_total_estoque = query_valor_total.scalar() or 0

        # Monta o JSON de resposta
        kpis = {
            'total_produtos': total_produtos,
            'total_fornecedores': total_fornecedores,
            'valor_total_estoque': float(valor_total_estoque) # Converte de Decimal para float
        }
        
        return jsonify(kpis), 200

    except Exception as e:
        return jsonify({'erro': str(e)}), 500
    
# ==============================================================================
# Bloco de Execução Principal
# ==============================================================================

import io
import pandas as pd
from flask import send_file
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from datetime import datetime

# --- FUNÇÕES AUXILIARES PARA GERAR ARQUIVOS ---

# Substitua a sua função gerar_inventario_pdf por esta versão corrigida

def gerar_inventario_pdf(dados):
    """Gera um PDF do relatório de inventário atual."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    elementos = []
    styles = getSampleStyleSheet()

    # Título
    titulo = Paragraph("Relatório de Inventário Atual", styles['h1'])
    elementos.append(titulo)
    elementos.append(Spacer(1, 12))

    # Cabeçalhos da tabela
    dados_tabela = [["Código", "Nome", "Saldo", "Preço Unit. (R$)", "Valor Total (R$)"]]
    # Dados
    valor_total_geral = 0
    for item in dados:
        # --- A CORREÇÃO ESTÁ AQUI ---
        # Multiplicamos diretamente, sem converter para float.
        # O objeto Decimal sabe como se multiplicar por um inteiro (saldo).
        valor_total_item = item['saldo_atual'] * item['preco']
        valor_total_geral += valor_total_item
        
        # O resto da formatação para exibição continua igual
        dados_tabela.append([
            item['codigo'],
            item['nome'],
            str(item['saldo_atual']),
            f"{float(item['preco']):.2f}", # Usamos float() aqui apenas para formatar o texto
            f"{float(valor_total_item):.2f}"
        ])
    
    tabela = Table(dados_tabela)
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ]))
    elementos.append(tabela)
    elementos.append(Spacer(1, 12))

    # Sumário
    sumario = Paragraph(f"<b>Valor Total do Estoque:</b> R$ {float(valor_total_geral):.2f}", styles['h3'])
    elementos.append(sumario)

    doc.build(elementos)
    buffer.seek(0)
    return buffer

def gerar_historico_pdf(dados):
    """Gera um PDF do relatório de histórico de movimentações."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter)) # Paisagem para mais colunas
    elementos = []
    styles = getSampleStyleSheet()

    # Título
    titulo = Paragraph("Relatório de Histórico de Movimentações", styles['h1'])
    elementos.append(titulo)
    elementos.append(Spacer(1, 12))
    
    dados_tabela = [["Data/Hora", "Produto", "Tipo", "Qtd.", "Usuário", "Motivo da Saída"]]
    for item in dados:
        dados_tabela.append([
            item['data_hora'],
            f"{item['produto_codigo']} - {item['produto_nome']}",
            item['tipo'],
            str(item['quantidade']),
            item['usuario_nome'],
            item.get('motivo_saida', '')
        ])
        
    tabela = Table(dados_tabela, colWidths=[120, 200, 60, 40, 100, 150]) # Larguras customizadas
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0,0), (-1,-1), 1, colors.black)
    ]))
    elementos.append(tabela)
    doc.build(elementos)
    buffer.seek(0)
    return buffer


# --- ENDPOINTS DA API DE RELATÓRIOS ---

@app.route('/api/relatorios/inventario', methods=['GET'])
@jwt_required()
def relatorio_inventario():
    """Gera e retorna o relatório de inventário em PDF ou XLSX."""
    formato = request.args.get('formato', 'pdf').lower()

    # Lógica para buscar os dados (adaptada do endpoint de saldos)
    produtos = Produto.query.all()
    dados_relatorio = []
    for produto in produtos:
        saldo = calcular_saldo_produto(produto.id_produto)
        dados_relatorio.append({
            'codigo': produto.codigo.strip(),
            'nome': produto.nome,
            'saldo_atual': saldo,
            'preco': produto.preco
        })

    if formato == 'xlsx':
        df = pd.DataFrame(dados_relatorio)
        df['valor_total'] = df['saldo_atual'] * df['preco']
        df = df.rename(columns={'codigo': 'Código', 'nome': 'Nome', 'saldo_atual': 'Saldo', 'preco': 'Preço Unitário (R$)', 'valor_total': 'Valor Total (R$)'})
        
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False, engine='openpyxl')
        buffer.seek(0)
        return send_file(buffer, download_name="relatorio_inventario.xlsx", as_attachment=True)

    else: # PDF como padrão
        pdf_buffer = gerar_inventario_pdf(dados_relatorio)
        return send_file(pdf_buffer, download_name="relatorio_inventario.pdf", as_attachment=True)


@app.route('/api/relatorios/movimentacoes', methods=['GET'])
@jwt_required()
def relatorio_movimentacoes():
    """Gera e retorna o relatório de movimentações filtrado."""
    formato = request.args.get('formato', 'pdf').lower()
    data_inicio_str = request.args.get('data_inicio')
    data_fim_str = request.args.get('data_fim')
    tipo = request.args.get('tipo')

    # Lógica para buscar os dados (a mesma de antes)
    query = MovimentacaoEstoque.query.options(
        joinedload(MovimentacaoEstoque.produto),
        joinedload(MovimentacaoEstoque.usuario)
    ).order_by(MovimentacaoEstoque.data_hora.desc())

    if data_inicio_str:
        query = query.filter(MovimentacaoEstoque.data_hora >= datetime.strptime(data_inicio_str, '%Y-%m-%d'))
    if data_fim_str:
        data_fim = datetime.strptime(data_fim_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        query = query.filter(MovimentacaoEstoque.data_hora <= data_fim)
    if tipo and tipo in ["Entrada", "Saida"]:
        query = query.filter(MovimentacaoEstoque.tipo == tipo)

    movimentacoes = query.all()
    
    # --- CORREÇÃO ESTÁ AQUI ---
    # Montamos os dados do relatório de forma mais segura.
    dados_relatorio = []
    for mov in movimentacoes:
        dados_relatorio.append({
            'data_hora': mov.data_hora.strftime('%d/%m/%Y %H:%M:%S'),
            'produto_codigo': mov.produto.codigo.strip() if mov.produto else 'N/A',
            'produto_nome': mov.produto.nome if mov.produto else 'Produto Excluído',
            'tipo': mov.tipo,
            'quantidade': mov.quantidade,
            'usuario_nome': mov.usuario.nome if mov.usuario else 'Usuário Excluído',
            'motivo_saida': mov.motivo_saida if mov.motivo_saida else '' # Usando a forma correta
        })

    if formato == 'xlsx':
        df = pd.DataFrame(dados_relatorio)
        df = df.rename(columns={
            'data_hora': 'Data/Hora', 'produto_codigo': 'Cód. Produto', 'produto_nome': 'Nome Produto',
            'tipo': 'Tipo', 'quantidade': 'Quantidade', 'usuario_nome': 'Usuário', 'motivo_saida': 'Motivo da Saída'
        })
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False, engine='openpyxl')
        buffer.seek(0)
        return send_file(buffer, download_name="relatorio_movimentacoes.xlsx", as_attachment=True)
        
    else: # PDF
        pdf_buffer = gerar_historico_pdf(dados_relatorio)
        return send_file(pdf_buffer, download_name="relatorio_movimentacoes.pdf", as_attachment=True)
    
if __name__ == '__main__':
    app.run(debug=True)
    
    
# ==============================================================================
# MÓDULO DE RELATÓRIOS (ADICIONE NO FINAL DO SEU app.py)
# ==============================================================================
