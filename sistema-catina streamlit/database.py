"""Camada de dados - SQLite (arquivo cantina.db, sem servidor externo).
Usa ? como parâmetro, separando SQL dos dados.
Cada usuário tem seu próprio estoque (coluna usuario_id).
"""
import hashlib
import os
import sqlite3
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("CANTINA_DB", BASE_DIR / "cantina.db"))
DIAS_ALERTA_VALIDADE = 7
FUSO = ZoneInfo("America/Sao_Paulo")

_COLUNAS_DATA = {"validade", "validade_lote"}
_COLUNAS_DATAHORA = {"data", "criado_em"}
_COLUNAS_DINHEIRO = {"preco", "valor_unit"}


def _agora():
    return datetime.now(FUSO).replace(tzinfo=None, microsecond=0)


def _hoje():
    return _agora().date()


def _converter(coluna, valor):
    """Converte o que o SQLite guarda (texto/número) para os tipos que o app espera."""
    if valor is None:
        return None
    if coluna in _COLUNAS_DATA:
        return date.fromisoformat(str(valor)[:10])
    if coluna in _COLUNAS_DATAHORA:
        return datetime.fromisoformat(str(valor))
    if coluna in _COLUNAS_DINHEIRO:
        return Decimal(str(valor)).quantize(Decimal("0.01"))
    return valor


def _linha_para_dict(cursor, linha):
    return {col[0]: _converter(col[0], valor) for col, valor in zip(cursor.description, linha)}


def conectar():
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory = _linha_para_dict
    con.execute("PRAGMA foreign_keys = ON")
    return con


def _dinheiro(valor):
    """SQLite não aceita Decimal: guarda como número com 2 casas."""
    return float(Decimal(str(valor or 0)).quantize(Decimal("0.01")))


def _data(valor):
    return valor.isoformat() if valor else None


def criar_banco():
    con = conectar()
    con.executescript("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            usuario TEXT NOT NULL UNIQUE,
            senha_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER REFERENCES usuarios(id),
            nome TEXT NOT NULL,
            categoria TEXT NOT NULL,
            quantidade INTEGER NOT NULL DEFAULT 0 CHECK (quantidade >= 0),
            estoque_minimo INTEGER NOT NULL DEFAULT 0,
            validade TEXT NULL,
            preco REAL NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS movimentacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER REFERENCES usuarios(id),
            produto_id INTEGER NOT NULL REFERENCES produtos(id) ON DELETE RESTRICT,
            tipo TEXT NOT NULL CHECK (tipo IN ('entrada','saida')),
            quantidade INTEGER NOT NULL CHECK (quantidade > 0),
            validade_lote TEXT NULL,
            observacao TEXT NULL,
            data TEXT NOT NULL,
            valor_unit REAL NOT NULL DEFAULT 0
        );
    """)
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
        cur.execute("SELECT id FROM usuarios WHERE usuario=?", (usuario,))
        if cur.fetchone():
            return False, "Este usuário já existe"
        salt = os.urandom(16).hex()
        cur.execute("INSERT INTO usuarios(nome,usuario,senha_hash,salt,criado_em) VALUES(?,?,?,?,?)",
                    (nome, usuario, _hash(senha, salt), salt, _agora().isoformat(sep=" ")))
        novo_id = cur.lastrowid
        # primeira conta assume produtos antigos (sem dono)
        cur.execute("SELECT COUNT(*) AS n FROM usuarios")
        if cur.fetchone()["n"] == 1:
            cur.execute("UPDATE produtos SET usuario_id=? WHERE usuario_id IS NULL", (novo_id,))
            cur.execute("UPDATE movimentacoes SET usuario_id=? WHERE usuario_id IS NULL", (novo_id,))
        con.commit()
        return True, "Conta criada com sucesso"
    except Exception as e:
        con.rollback()
        return False, f"Erro ao criar conta: {e}"
    finally:
        con.close()


def autenticar(usuario, senha):
    con = conectar()
    u = con.execute("SELECT * FROM usuarios WHERE usuario=?", (usuario.strip().lower(),)).fetchone()
    con.close()
    if not u or _hash(senha, u["salt"]) != u["senha_hash"]:
        return None
    return {"id": u["id"], "nome": u["nome"], "usuario": u["usuario"]}


def alterar_senha(uid, atual, nova):
    con = conectar()
    u = con.execute("SELECT * FROM usuarios WHERE id=?", (uid,)).fetchone()
    if not u or _hash(atual, u["salt"]) != u["senha_hash"]:
        con.close()
        return False, "Senha atual incorreta"
    if len(nova) < 4:
        con.close()
        return False, "A nova senha deve ter pelo menos 4 caracteres"
    salt = os.urandom(16).hex()
    con.execute("UPDATE usuarios SET senha_hash=?, salt=? WHERE id=?", (_hash(nova, salt), salt, uid))
    con.commit()
    con.close()
    return True, "Senha alterada"


# ================= CREATE =================
def cadastrar_produto(uid, nome, categoria, estoque_minimo, validade=None, preco=0):
    con = conectar()
    con.execute("INSERT INTO produtos(usuario_id,nome,categoria,quantidade,estoque_minimo,validade,preco) "
                "VALUES(?,?,?,0,?,?,?)",
                (uid, nome, categoria, estoque_minimo, _data(validade), _dinheiro(preco)))
    con.commit()
    con.close()
    return True, "Produto cadastrado"


def registrar_entrada(uid, produto_id, quantidade, validade_lote=None, obs=""):
    if quantidade <= 0:
        return False, "Quantidade deve ser maior que zero"
    con = conectar()
    try:
        con.execute("BEGIN IMMEDIATE")  # trava escrita: evita duas movimentações ao mesmo tempo
        row = con.execute("SELECT validade FROM produtos WHERE id=? AND usuario_id=?",
                          (produto_id, uid)).fetchone()
        if not row:
            con.rollback()
            return False, "Produto não encontrado"
        con.execute("UPDATE produtos SET quantidade=quantidade+? WHERE id=?", (quantidade, produto_id))
        if validade_lote and (row["validade"] is None or validade_lote < row["validade"]):
            con.execute("UPDATE produtos SET validade=? WHERE id=?", (_data(validade_lote), produto_id))
        con.execute("INSERT INTO movimentacoes(usuario_id,produto_id,tipo,quantidade,validade_lote,observacao,data) "
                    "VALUES(?,?,'entrada',?,?,?,?)",
                    (uid, produto_id, quantidade, _data(validade_lote), obs, _agora().isoformat(sep=" ")))
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
        con.execute("BEGIN IMMEDIATE")
        atual = con.execute("SELECT quantidade, preco FROM produtos WHERE id=? AND usuario_id=?",
                            (produto_id, uid)).fetchone()
        if not atual or atual["quantidade"] < quantidade:
            con.rollback()
            return False, "Estoque insuficiente"
        con.execute("UPDATE produtos SET quantidade=quantidade-? WHERE id=?", (quantidade, produto_id))
        con.execute("INSERT INTO movimentacoes(usuario_id,produto_id,tipo,quantidade,observacao,valor_unit,data) "
                    "VALUES(?,?,'saida',?,?,?,?)",
                    (uid, produto_id, quantidade, obs, _dinheiro(atual["preco"]), _agora().isoformat(sep=" ")))
        con.commit()
        return True, "Saída registrada"
    except Exception as e:
        con.rollback()
        return False, str(e)
    finally:
        con.close()


def editar_produto(uid, produto_id, nome, categoria, estoque_minimo, validade=None, preco=0):
    con = conectar()
    con.execute("UPDATE produtos SET nome=?,categoria=?,estoque_minimo=?,validade=?,preco=? "
                "WHERE id=? AND usuario_id=?",
                (nome, categoria, estoque_minimo, _data(validade), _dinheiro(preco), produto_id, uid))
    con.commit()
    con.close()
    return True, "Produto atualizado"


# ================= DELETE =================
def excluir_produto(uid, produto_id):
    con = conectar()
    n = con.execute("SELECT COUNT(*) AS n FROM movimentacoes WHERE produto_id=?", (produto_id,)).fetchone()["n"]
    if n > 0:
        con.close()
        return False, "Produto possui histórico de movimentações e não pode ser excluído"
    con.execute("DELETE FROM produtos WHERE id=? AND usuario_id=?", (produto_id, uid))
    con.commit()
    con.close()
    return True, "Produto excluído"


# ================= READ =================
def _consulta(sql, params):
    con = conectar()
    d = con.execute(sql, params).fetchall()
    con.close()
    return d


def listar_produtos(uid, busca=""):
    like = f"%{busca}%"
    return _consulta("SELECT * FROM produtos WHERE usuario_id=? AND (nome LIKE ? OR categoria LIKE ?) "
                     "ORDER BY nome", (uid, like, like))


def obter_produto(uid, produto_id):
    r = _consulta("SELECT * FROM produtos WHERE id=? AND usuario_id=?", (produto_id, uid))
    return r[0] if r else None


def listar_movimentacoes(uid, busca=""):
    like = f"%{busca}%"
    return _consulta("""
        SELECT m.id, p.nome, m.tipo, m.quantidade, m.validade_lote, m.observacao, m.data, m.valor_unit
        FROM movimentacoes m JOIN produtos p ON p.id = m.produto_id
        WHERE p.usuario_id=? AND (p.nome LIKE ? OR m.tipo LIKE ?)
        ORDER BY m.data DESC, m.id DESC""", (uid, like, like))


def itens_baixos(uid):
    return _consulta("SELECT * FROM produtos WHERE usuario_id=? AND quantidade <= estoque_minimo "
                     "ORDER BY quantidade", (uid,))


def proximos_vencimento(uid, dias=DIAS_ALERTA_VALIDADE):
    hoje = _hoje().isoformat()
    return _consulta("SELECT *, CAST(julianday(validade) - julianday(?) AS INTEGER) AS dias FROM produtos "
                     "WHERE usuario_id=? AND validade IS NOT NULL AND quantidade > 0 "
                     "AND validade <= date(?, '+' || ? || ' days') ORDER BY validade",
                     (hoje, uid, hoje, int(dias)))


def resumo(uid):
    con = conectar()
    r = con.execute("SELECT COUNT(*) AS total, COALESCE(SUM(quantidade),0) AS unidades "
                    "FROM produtos WHERE usuario_id=?", (uid,)).fetchone()
    vendido = con.execute("SELECT COALESCE(SUM(m.quantidade*m.valor_unit),0) AS v FROM movimentacoes m "
                          "JOIN produtos p ON p.id=m.produto_id WHERE p.usuario_id=? AND m.tipo='saida'",
                          (uid,)).fetchone()["v"]
    con.close()
    return {"produtos": r["total"], "unidades": int(r["unidades"]), "vendido": float(vendido),
            "baixos": len(itens_baixos(uid)), "vencendo": len(proximos_vencimento(uid))}
