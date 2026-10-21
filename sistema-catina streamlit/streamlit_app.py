"""Cantina para Streamlit Community Cloud: streamlit run streamlit_app.py."""
import logging
from html import escape
from pathlib import Path
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

import sqlite3

import streamlit as st

st.set_page_config(page_title="Cantina · Estoque", page_icon="📦", layout="wide")

import database as db


@st.cache_resource(show_spinner=False)
def initialize_database():
    db.criar_banco()
    return True


def money(value):
    return f"R$ {Decimal(str(value or 0)):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def brdate(value):
    return value.strftime("%d/%m/%Y") if value else "Sem validade"


def situation(product):
    today = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    if product["validade"] and product["quantidade"] > 0:
        days = (product["validade"] - today).days
        if days < 0:
            return "🔴 Vencido"
        if days <= db.DIAS_ALERTA_VALIDADE:
            return f"🟡 Vence em {days} dia(s)"
    if product["quantidade"] <= product["estoque_minimo"]:
        return "🟡 Estoque baixo"
    return "🟢 Em estoque"


def notify(message, kind="success"):
    st.session_state["notice"] = (kind, message)


def reset_editor():
    st.session_state.pop("editor", None)


def open_editor(kind, pid=None):
    st.session_state["editor"] = {"kind": kind, "pid": pid}
    st.rerun()


def logout():
    st.session_state.clear()
    st.rerun()


def initials(name):
    words = name.split()
    return (words[0][0] + (words[-1][0] if len(words) > 1 else words[0][1:2])).upper() if words else "C"


def html(markup):
    st.markdown(markup, unsafe_allow_html=True)


def apply_style():
    css = Path(__file__).with_name("streamlit_style.css").read_text(encoding="utf-8")
    html("<style>" + css + "</style>")


def authentication():
    register = st.session_state.get("auth_mode") == "register"
    with st.container(key="auth_card"):
        html('<div class="auth-logo"><span class="logo-square">C</span><span>Cantina</span></div>')
        st.subheader("Criar sua conta" if register else "Bem-vindo de volta")
        st.caption("Cada conta tem o próprio estoque e histórico" if register else "Entre para acessar seu estoque")
        if not register:
            with st.form("login_form", clear_on_submit=True, border=False):
                username = st.text_input("Usuário", max_chars=50, key="login_user", placeholder="ex.: maria")
                password = st.text_input("Senha", type="password", max_chars=128, key="login_password", placeholder="••••••")
                submitted = st.form_submit_button("Entrar", type="primary", width="stretch")
            if submitted:
                user = db.autenticar(username, password) if username.strip() and password else None
                if user:
                    st.session_state["user"] = user
                    st.rerun()
                st.error("Usuário ou senha incorretos.")
        else:
            with st.form("register_form", clear_on_submit=True, border=False):
                name = st.text_input("Nome completo", max_chars=100, key="register_name", placeholder="Como você quer ser chamado")
                username = st.text_input("Usuário", max_chars=50, key="register_user", placeholder="ex.: maria")
                password = st.text_input("Nova senha", type="password", max_chars=128, help="Use pelo menos 8 caracteres.", key="register_password")
                confirmation = st.text_input("Confirmar senha", type="password", max_chars=128, key="register_confirmation")
                submitted = st.form_submit_button("Criar conta", type="primary", width="stretch")
            if submitted:
                if not name.strip() or not username.strip():
                    st.error("Preencha seu nome e nome de usuário.")
                elif len(password) < 8:
                    st.error("Use uma senha com pelo menos 8 caracteres.")
                elif password != confirmation:
                    st.error("As senhas não coincidem.")
                else:
                    ok, _ = db.registrar_usuario(name, username, password)
                    if ok:
                        st.session_state["auth_mode"] = "login"
                        notify("Conta criada. Entre para acessar seu estoque.")
                        st.rerun()
                    st.error("Não foi possível criar a conta. Tente outro nome de usuário.")
        with st.container(key="auth_footer"):
            label, link = st.columns([1.2, 1], vertical_alignment="center")
            label.caption("Já tem conta?" if register else "Não tem conta?")
            if link.button("Entrar" if register else "Criar registro", key="toggle_auth"):
                st.session_state["auth_mode"] = "login" if register else "register"
                st.rerun()


def sidebar(user):
    summary = db.resumo(user["id"])
    with st.sidebar, st.container(key="sidebar_shell"):
        html(f'<div class="profile"><span class="profile-avatar">{escape(initials(user["nome"]))}</span>'
             f'<div><strong>{escape(user["nome"].split()[0].upper())}</strong>'
             f'<small>@{escape(user["usuario"])}</small></div></div>')
        cards = ""
        for symbol, label, value, color in [("▦", "PRODUTOS", str(summary["produtos"]), "purple"),
                                           ("↓", "ESTOQUE BAIXO", str(summary["baixos"]), "teal"),
                                           ("$", "VENDIDO", money(summary["vendido"]), "rose")]:
            cards += f'<div class="sidebar-stat"><span class="stat-symbol {color}">{symbol}</span><div><small>{label}</small><strong>{escape(value)}</strong></div></div>'
        html('<div class="sidebar-stats">' + cards + '</div>')
        labels = {"Visão geral": "⌂     INÍCIO", "Produtos": "▢     PRODUTOS",
                  "Movimentações": "↗     VENDAS", "Minha conta": "⚙     CONFIGURAÇÕES"}
        page = st.radio("Navegação", ["Visão geral", "Produtos", "Movimentações", "Minha conta"],
                        key="page", on_change=reset_editor, label_visibility="collapsed", format_func=labels.get)
        with st.container(key="sidebar_logout"):
            if st.button("Sair da conta", width="stretch", key="logout"):
                logout()
    return page


def catalog(user, overview):
    uid = user["id"]
    search, add = st.columns([8, 1.5], vertical_alignment="center")
    query = search.text_input("Buscar por nome ou categoria", placeholder="⌕   Buscar produto..." if overview else "⌕   Buscar por nome ou categoria...",
                              max_chars=100, key="product_search", label_visibility="collapsed")
    if add.button("+  Novo", type="primary", key="new_product", width="stretch"):
        open_editor("new")
    hour = datetime.now(ZoneInfo("America/Sao_Paulo")).hour
    greeting = "Bom dia" if hour < 12 else "Boa tarde" if hour < 18 else "Boa noite"
    title = greeting + ", " + user["nome"].split()[0] if overview else "Produtos"
    subtitle = "Itens com alerta aparecem primeiro. Use os botões para movimentar." if overview else "Gerencie cadastro, entradas e saídas"
    html(f'<div class="page-heading"><h1>{escape(title)}</h1><p>{subtitle}</p></div>')
    products = db.listar_produtos(uid, query.strip())
    if overview:
        products.sort(key=lambda product: situation(product).startswith("🟢"))
    if not products:
        html('<div class="empty-state"><h3>Nenhum produto encontrado</h3><p>' +
             ('Tente outro termo.' if query else 'Clique em “+ Novo” para cadastrar o primeiro item.') + '</p></div>')
        if not query and st.button("Cadastrar primeiro produto", key="first_product"):
            open_editor("new")
        return
    for product in products:
        status = situation(product)
        normal = status.startswith("🟢")
        color = "danger" if status.startswith("🔴") or "Estoque baixo" in status else "warning"
        badge = '' if normal else f'<span class="status-pill {color}">{escape(status.split(" ", 1)[1])}</span>'
        with st.container(key=f'product_row_{product["id"]}'):
            info, actions, expiry, quantity = st.columns([4.4, 2.8, 1.6, .8], gap="small", vertical_alignment="center")
            with info:
                html(f'<div class="product-info {"" if normal else "alert-" + color}"><span class="product-avatar">{escape(initials(product["nome"]))}</span>'
                     f'<div><h2>{escape(product["nome"].upper())}</h2><p>{escape(product["categoria"])} · {money(product["preco"])} {badge}</p></div></div>')
            with actions:
                entry, sale, edit = st.columns(3, gap="small")
                if entry.button("Entrada", key=f'entry_{product["id"]}', width="stretch"):
                    open_editor("entry", product["id"])
                if sale.button("Saída", key=f'sale_{product["id"]}', width="stretch"):
                    open_editor("sale", product["id"])
                if edit.button("Editar", key=f'edit_{product["id"]}', width="stretch"):
                    open_editor("edit", product["id"])
            with expiry:
                date_label = product["validade"].strftime("%d/%m/%y") if product["validade"] else "--/--/--"
                html(f'<div class="date-chip {color if "Venc" in status else ""}"><span>▣</span> {date_label}</div>')
            with quantity:
                html(f'<div class="quantity-chip {"danger" if product["quantidade"] <= product["estoque_minimo"] else ""}">{product["quantidade"]}</div>')


def product_editor(uid, product):
    st.title("Editar produto" if product else "Novo produto")
    if not product:
        st.caption("O estoque começa em zero. Registre uma entrada depois do cadastro.")
    suffix = str(product["id"]) if product else "new"
    with st.form("product_form_" + suffix):
        name = st.text_input("Nome do produto", value=product["nome"] if product else "", max_chars=100, key="product_name_" + suffix)
        category = st.text_input("Categoria", value=product["categoria"] if product else "", max_chars=50, key="product_category_" + suffix)
        left, right = st.columns(2)
        price_text = left.text_input("Preço de venda (R$)", value=str(product["preco"]) if product else "0,00", max_chars=20, key="product_price_" + suffix)
        minimum = right.number_input("Estoque mínimo", min_value=0, max_value=2147483647,
                                     value=product["estoque_minimo"] if product else 0, step=1, key="product_minimum_" + suffix)
        expiry = st.date_input("Validade (opcional)", value=product["validade"] if product else None,
                               min_value=date(1900, 1, 1), max_value=date(2200, 12, 31), format="DD/MM/YYYY", key="product_expiry_" + suffix)
        submitted = st.form_submit_button("Salvar produto", type="primary")
    if submitted:
        try:
            price = Decimal(price_text.replace(",", "."))
            if not price.is_finite() or price < 0 or price > Decimal("99999999.99") or price != price.quantize(Decimal("0.01")):
                raise ValueError
            if not name.strip() or not category.strip():
                raise ValueError
        except (ValueError, InvalidOperation):
            st.error("Preencha nome e categoria. Use preço positivo com até duas casas decimais.")
            return
        if product:
            db.editar_produto(uid, product["id"], name.strip(), category.strip(), minimum, expiry, price)
        else:
            db.cadastrar_produto(uid, name.strip(), category.strip(), minimum, expiry, price)
        reset_editor()
        notify("Produto salvo.")
        st.rerun()
    if product:
        st.divider()
        st.caption("Produtos com movimentações são preservados no histórico.")
        if st.button("Excluir produto", key="delete_product"):
            open_editor("delete", product["id"])


def movement_editor(uid, product, kind):
    entry = kind == "entry"
    st.title("Registrar entrada" if entry else "Registrar saída")
    st.subheader(product["nome"])
    st.caption(f'{product["quantidade"]} unidade(s) em estoque · Preço: {money(product["preco"])}')
    with st.form(f'movement_{kind}_{product["id"]}'):
        quantity = st.number_input("Quantidade", min_value=1, max_value=2147483647, value=1, step=1, key="movement_quantity")
        expiry = st.date_input("Validade do lote (opcional)", value=None, min_value=date(1900, 1, 1), max_value=date(2200, 12, 31),
                               format="DD/MM/YYYY", key="movement_expiry") if entry else None
        note = st.text_area("Observação (opcional)", max_chars=200, key="movement_note")
        submitted = st.form_submit_button("Confirmar entrada" if entry else "Confirmar saída", type="primary")
    if submitted:
        # Releia a propriedade e o saldo antes de qualquer gravação.
        current = db.obter_produto(uid, product["id"])
        if not current:
            st.error("Produto não encontrado nesta conta.")
            return
        if entry and current["quantidade"] + quantity > 2147483647:
            st.error("Quantidade acima do limite permitido.")
            return
        if not entry and current["quantidade"] < quantity:
            st.error("Estoque insuficiente para essa saída.")
            return
        if entry:
            ok, _ = db.registrar_entrada(uid, product["id"], quantity, expiry, note)
        else:
            ok, _ = db.registrar_saida(uid, product["id"], quantity, note)
        if not ok:
            st.error("Não foi possível registrar. Confira o estoque e tente novamente.")
            return
        reset_editor()
        notify("Entrada registrada." if entry else "Saída registrada.")
        st.rerun()


def editor(uid, state):
    if st.button("← Voltar ao estoque", key="cancel_editor"):
        reset_editor()
        st.rerun()
    kind = state["kind"]
    product = db.obter_produto(uid, state["pid"]) if kind != "new" else None
    if kind != "new" and not product:
        st.error("Produto não encontrado nesta conta.")
        return
    if kind in {"new", "edit"}:
        product_editor(uid, product)
    elif kind in {"entry", "sale"}:
        movement_editor(uid, product, kind)
    elif kind == "delete":
        st.title("Excluir produto")
        st.write(product["nome"])
        with st.form("delete_form"):
            confirm = st.checkbox("Confirmo a exclusão deste produto", key="delete_confirm")
            submitted = st.form_submit_button("Confirmar exclusão", type="primary")
        if submitted:
            if not confirm:
                st.error("Marque a confirmação para excluir.")
                return
            ok, _ = db.excluir_produto(uid, product["id"])
            if ok:
                reset_editor()
                notify("Produto excluído.")
                st.rerun()
            st.error("Produto com movimentações não pode ser excluído.")


def movements(uid):
    query = st.text_input("Buscar produto, entrada ou saída", placeholder="⌕   Buscar movimentação...", max_chars=100,
                          key="movement_search", label_visibility="collapsed")
    html('<div class="page-heading"><h1>Vendas e movimentações</h1><p>Histórico de entradas e saídas do seu estoque</p></div>')
    records = db.listar_movimentacoes(uid, query.strip())
    if not records:
        html('<div class="empty-state"><h3>Sem movimentações</h3><p>Entradas e saídas registradas aparecem aqui.</p></div>')
        return
    for row in records:
        entry = row["tipo"] == "entrada"
        color = "teal" if entry else "rose"
        details = ["Entrada" if entry else "Saída", row["data"].strftime("%d/%m/%Y  %H:%M")]
        if row["validade_lote"]:
            details.append("lote vence " + brdate(row["validade_lote"]))
        if row["observacao"]:
            details.append(row["observacao"])
        total = '' if entry else money(row["quantidade"] * row["valor_unit"])
        html(f'<div class="movement-row"><span class="movement-icon {color}">{"↓" if entry else "↑"}</span>'
             f'<div class="movement-info"><h2>{escape(row["nome"].upper())}</h2><p>{escape(" · ".join(details))}</p></div>'
             f'<span class="movement-total">{total}</span><strong class="movement-quantity {color}">{"+" if entry else "−"}{row["quantidade"]}</strong></div>')


def account(user):
    html('<div class="page-heading"><h1>Configurações</h1><p>Conta, alertas e conexão</p></div>')
    html(f'<div class="account-card"><h2>Minha conta</h2><p>{escape(user["nome"])} · @{escape(user["usuario"])}</p></div>')
    with st.expander("Alterar senha"), st.form("password_form", clear_on_submit=True, border=False):
        st.subheader("Alterar senha")
        current = st.text_input("Senha atual", type="password", max_chars=128, key="current_password")
        password = st.text_input("Nova senha", type="password", max_chars=128, key="new_password")
        confirmation = st.text_input("Confirmar nova senha", type="password", max_chars=128, key="new_password_confirmation")
        submitted = st.form_submit_button("Salvar nova senha", type="primary")
    if submitted:
        if len(password) < 8:
            st.error("Use uma senha com pelo menos 8 caracteres.")
        elif password != confirmation:
            st.error("As senhas não coincidem.")
        else:
            ok, _ = db.alterar_senha(user["id"], current, password)
            if ok:
                st.session_state.clear()
                notify("Senha alterada. Entre novamente.")
                st.rerun()
            st.error("Não foi possível alterar. Confira a senha atual.")
    for title, items, color in [("Abaixo do estoque mínimo", db.itens_baixos(user["id"]), "rose"),
                                 (f"Vencendo em até {db.DIAS_ALERTA_VALIDADE} dias", db.proximos_vencimento(user["id"]), "amber")]:
        rows = ''
        for product in items:
            detail = f'{product["quantidade"]} de {product["estoque_minimo"]} un.' if color == "rose" else brdate(product["validade"])
            rows += f'<div class="alert-item"><span>{escape(product["nome"])}</span><strong>{escape(detail)}</strong></div>'
        html(f'<div class="account-card"><h2 class="text-{color}">{title} ({len(items)})</h2>' +
             (rows or '<p>Nenhum item — tudo certo.</p>') + '</div>')
    html('<div class="account-card"><h2>Banco de dados</h2><p>SQLite · arquivo local · conectado</p></div>')


def main():
    apply_style()
    with st.spinner("Conectando ao banco da cantina…"):
        initialize_database()
    notice = st.session_state.pop("notice", None)
    if notice:
        getattr(st, notice[0])(notice[1])
    user = st.session_state.get("user")
    if not user:
        authentication()
        return
    page = sidebar(user)
    state = st.session_state.get("editor")
    if state:
        editor(user["id"], state)
    elif page in {"Visão geral", "Produtos"}:
        catalog(user, page == "Visão geral")
    elif page == "Movimentações":
        movements(user["id"])
    else:
        account(user)


def show_connection_error(error):
    # Não exiba a exceção original: mensagens do driver podem conter detalhes internos.
    logging.getLogger(__name__).error("Falha ao abrir a Cantina: tipo=%s", type(error).__name__)
    if isinstance(error, FileNotFoundError) and Path(error.filename or "").name == "streamlit_style.css":
        message = "Falta streamlit_style.css. Envie esse arquivo ao GitHub, ao lado de streamlit_app.py."
    else:
        message = "Não foi possível abrir o banco de dados SQLite (cantina.db). Reinicie o app e tente novamente."
    st.error(message)


if __name__ == "__main__":
    try:
        main()
    except (sqlite3.Error, OSError) as error:
        show_connection_error(error)
        if st.button("Tentar novamente", key="retry_database"):
            st.rerun()
