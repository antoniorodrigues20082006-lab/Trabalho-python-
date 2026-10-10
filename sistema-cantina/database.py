"""Camada de dados - MySQL / XAMPP.
Usa %s como parâmetro (equivalente ao ? do sqlite), separando SQL dos dados.
Cada usuário tem seu próprio estoque (coluna usuario_id).
"""
import hashlib
import os
import mysql.connector

CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",       # padrão do XAMPP
    "password": "",       # padrão do XAMPP (vazio)
}
DB_NAME = "cantina"
DIAS_ALERTA_VALIDADE = 7


def conectar(com_banco=True):
    cfg = dict(CONFIG)
    cfg.update(use_pure=True,                 # evita crash da extensão C no Windows
               charset="utf8mb4",
               collation="utf8mb4_general_ci",  # compatível com MariaDB do XAMPP
               connection_timeout=5)
    if com_banco:
        cfg["database"] = DB_NAME
    con = mysql.connector.connect(**cfg)
    cur = con.cursor()
    cur.execute("SET SESSION innodb_lock_wait_timeout = 5")  # não fica travado esperando
    cur.close()
    return con


def _coluna_existe(cur, tabela, coluna):
    cur.execute("SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=%s "
                "AND TABLE_NAME=%s AND COLUMN_NAME=%s", (DB_NAME, tabela, coluna))
    return cur.fetchone()[0] > 0


def criar_banco():
    con = conectar(False)
    cur = con.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET utf8mb4")
    cur.execute(f"USE {DB_NAME}")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nome VARCHAR(100) NOT NULL,
            usuario VARCHAR(50) NOT NULL UNIQUE,
            senha_hash CHAR(64) NOT NULL,
            salt CHAR(32) NOT NULL,
            criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS produtos (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nome VARCHAR(100) NOT NULL,
            categoria VARCHAR(50) NOT NULL,
            quantidade INT NOT NULL DEFAULT 0 CHECK (quantidade >= 0),
            estoque_minimo INT NOT NULL DEFAULT 0,
            validade DATE NULL
        )""")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS movimentacoes (
            id INT AUTO_INCREMENT PRIMARY KEY,
            produto_id INT NOT NULL,
            tipo ENUM('entrada','saida') NOT NULL,
            quantidade INT NOT NULL CHECK (quantidade > 0),
            validade_lote DATE NULL,
            observacao VARCHAR(200) NULL,
            data DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (produto_id) REFERENCES produtos(id) ON DELETE RESTRICT
        )""")
    # migrações de versões anteriores
    for tabela, coluna, tipo in [("produtos", "preco", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
                                 ("produtos", "usuario_id", "INT NULL"),
                                 ("movimentacoes", "valor_unit", "DECIMAL(10,2) NOT NULL DEFAULT 0"),
                                 ("movimentacoes", "usuario_id", "INT NULL")]:
        if not _coluna_existe(cur, tabela, coluna):
            cur.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}")
    con.commit()
    con.close()


# ================= USUÁRIOS / LOGIN =================
def _hash(senha, salt):
    return hashlib.pbkdf2_hmac("sha256", senha.encode(), bytes.fromhex(salt), 120_000).hex()


def registrar_usuario(nome, usuario, senha):
    nome, usuario = nome.strip(), usuario.strip().lower()
    if not nome or not usuario or not senha:
        return False, "Preencha todos os campos"
    if len(senha) < 4:
        return False, "A senha deve ter pelo menos 4 caracteres"
    con = conectar()
    try:
        cur = con.cursor()
        cur.execute("SELECT id FROM usuarios WHERE usuario=%s", (usuario,))
        if cur.fetchone():
            return False, "Este usuário já existe"
        salt = os.urandom(16).hex()
        cur.execute("INSERT INTO usuarios(nome,usuario,senha_hash,salt) VALUES(%s,%s,%s,%s)",
                    (nome, usuario, _hash(senha, salt), salt))
        novo_id = cur.lastrowid
        # primeira conta assume produtos antigos (sem dono)
        cur.execute("SELECT COUNT(*) FROM usuarios")
        if cur.fetchone()[0] == 1:
            cur.execute("UPDATE produtos SET usuario_id=%s WHERE usuario_id IS NULL", (novo_id,))
            cur.execute("UPDATE movimentacoes SET usuario_id=%s WHERE usuario_id IS NULL", (novo_id,))
        con.commit()
        return True, "Conta criada com sucesso"
    except Exception as e:
        con.rollback()
        return False, f"Erro ao criar conta: {e}"
    finally:
        con.close()


def autenticar(usuario, senha):
    con = conectar()
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT * FROM usuarios WHERE usuario=%s", (usuario.strip().lower(),))
    u = cur.fetchone()
    con.close()
    if not u or _hash(senha, u["salt"]) != u["senha_hash"]:
        return None
    return {"id": u["id"], "nome": u["nome"], "usuario": u["usuario"]}


def alterar_senha(uid, atual, nova):
    con = conectar()
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT * FROM usuarios WHERE id=%s", (uid,))
    u = cur.fetchone()
    if _hash(atual, u["salt"]) != u["senha_hash"]:
        con.close()
        return False, "Senha atual incorreta"
    if len(nova) < 4:
        con.close()
        return False, "A nova senha deve ter pelo menos 4 caracteres"
    salt = os.urandom(16).hex()
    cur.execute("UPDATE usuarios SET senha_hash=%s, salt=%s WHERE id=%s", (_hash(nova, salt), salt, uid))
    con.commit()
    con.close()
    return True, "Senha alterada"


# ================= CREATE =================
def cadastrar_produto(uid, nome, categoria, estoque_minimo, validade=None, preco=0):
    con = conectar()
    cur = con.cursor()
    cur.execute("INSERT INTO produtos(usuario_id,nome,categoria,quantidade,estoque_minimo,validade,preco) "
                "VALUES(%s,%s,%s,0,%s,%s,%s)", (uid, nome, categoria, estoque_minimo, validade, preco))
    con.commit()
    con.close()
    return True, "Produto cadastrado"


def registrar_entrada(uid, produto_id, quantidade, validade_lote=None, obs=""):
    if quantidade <= 0:
        return False, "Quantidade deve ser maior que zero"
    con = conectar()
    try:
        cur = con.cursor()
        cur.execute("SELECT validade FROM produtos WHERE id=%s AND usuario_id=%s FOR UPDATE",
                    (produto_id, uid))
        row = cur.fetchone()
        if not row:
            return False, "Produto não encontrado"
        cur.execute("UPDATE produtos SET quantidade=quantidade+%s WHERE id=%s", (quantidade, produto_id))
        if validade_lote and (row[0] is None or validade_lote < row[0]):
            cur.execute("UPDATE produtos SET validade=%s WHERE id=%s", (validade_lote, produto_id))
        cur.execute("INSERT INTO movimentacoes(usuario_id,produto_id,tipo,quantidade,validade_lote,observacao) "
                    "VALUES(%s,%s,'entrada',%s,%s,%s)", (uid, produto_id, quantidade, validade_lote, obs))
        con.commit()
        return True, "Entrada registrada"
    except Exception as e:
        con.rollback()
        return False, str(e)
    finally:
        con.close()


# ================= UPDATE =================
def registrar_saida(uid, produto_id, quantidade, obs=""):
    if quantidade <= 0:
        return False, "Quantidade deve ser maior que zero"
    con = conectar()
    try:
        cur = con.cursor()
        cur.execute("SELECT quantidade, preco FROM produtos WHERE id=%s AND usuario_id=%s FOR UPDATE",
                    (produto_id, uid))
        atual = cur.fetchone()
        if not atual or atual[0] < quantidade:
            con.rollback()
            return False, "Estoque insuficiente"
        cur.execute("UPDATE produtos SET quantidade=quantidade-%s WHERE id=%s", (quantidade, produto_id))
        cur.execute("INSERT INTO movimentacoes(usuario_id,produto_id,tipo,quantidade,observacao,valor_unit) "
                    "VALUES(%s,%s,'saida',%s,%s,%s)", (uid, produto_id, quantidade, obs, atual[1]))
        con.commit()
        return True, "Saída registrada"
    except Exception as e:
        con.rollback()
        return False, str(e)
    finally:
        con.close()


def editar_produto(uid, produto_id, nome, categoria, estoque_minimo, validade=None, preco=0):
    con = conectar()
    cur = con.cursor()
    cur.execute("UPDATE produtos SET nome=%s,categoria=%s,estoque_minimo=%s,validade=%s,preco=%s "
                "WHERE id=%s AND usuario_id=%s",
                (nome, categoria, estoque_minimo, validade, preco, produto_id, uid))
    con.commit()
    con.close()
    return True, "Produto atualizado"


# ================= DELETE =================
def excluir_produto(uid, produto_id):
    con = conectar()
    cur = con.cursor()
    cur.execute("SELECT COUNT(*) FROM movimentacoes WHERE produto_id=%s", (produto_id,))
    if cur.fetchone()[0] > 0:
        con.close()
        return False, "Produto possui histórico de movimentações e não pode ser excluído"
    cur.execute("DELETE FROM produtos WHERE id=%s AND usuario_id=%s", (produto_id, uid))
    con.commit()
    con.close()
    return True, "Produto excluído"


# ================= READ =================
def _consulta(sql, params):
    con = conectar()
    cur = con.cursor(dictionary=True)
    cur.execute(sql, params)
    d = cur.fetchall()
    con.close()
    return d


def listar_produtos(uid, busca=""):
    like = f"%{busca}%"
    return _consulta("SELECT * FROM produtos WHERE usuario_id=%s AND (nome LIKE %s OR categoria LIKE %s) "
                     "ORDER BY nome", (uid, like, like))


def obter_produto(uid, produto_id):
    r = _consulta("SELECT * FROM produtos WHERE id=%s AND usuario_id=%s", (produto_id, uid))
    return r[0] if r else None


def listar_movimentacoes(uid, busca=""):
    like = f"%{busca}%"
    return _consulta("""
        SELECT m.id, p.nome, m.tipo, m.quantidade, m.validade_lote, m.observacao, m.data, m.valor_unit
        FROM movimentacoes m JOIN produtos p ON p.id = m.produto_id
        WHERE p.usuario_id=%s AND (p.nome LIKE %s OR m.tipo LIKE %s)
        ORDER BY m.data DESC""", (uid, like, like))


def itens_baixos(uid):
    return _consulta("SELECT * FROM produtos WHERE usuario_id=%s AND quantidade <= estoque_minimo "
                     "ORDER BY quantidade", (uid,))


def proximos_vencimento(uid, dias=DIAS_ALERTA_VALIDADE):
    return _consulta("SELECT *, DATEDIFF(validade, CURDATE()) AS dias FROM produtos "
                     "WHERE usuario_id=%s AND validade IS NOT NULL AND quantidade > 0 "
                     "AND validade <= DATE_ADD(CURDATE(), INTERVAL %s DAY) ORDER BY validade", (uid, dias))


def resumo(uid):
    con = conectar()
    cur = con.cursor()
    cur.execute("SELECT COUNT(*), COALESCE(SUM(quantidade),0) FROM produtos WHERE usuario_id=%s", (uid,))
    total, unidades = cur.fetchone()
    cur.execute("SELECT COALESCE(SUM(m.quantidade*m.valor_unit),0) FROM movimentacoes m "
                "JOIN produtos p ON p.id=m.produto_id WHERE p.usuario_id=%s AND m.tipo='saida'", (uid,))
    vendido = float(cur.fetchone()[0])
    con.close()
    return {"produtos": total, "unidades": int(unidades), "vendido": vendido,
            "baixos": len(itens_baixos(uid)), "vencendo": len(proximos_vencimento(uid))}
