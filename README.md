# Trabalho-python-
# 📦 Sistema de Estoque - Cantina Escolar

## 📋 Sobre o Projeto

Este projeto consiste no desenvolvimento de um sistema de gerenciamento de estoque para uma cantina escolar.

O sistema foi desenvolvido com o objetivo de facilitar o controle dos produtos vendidos pela cantina, permitindo registrar entradas, saídas e vendas, além de acompanhar a quantidade disponível em estoque.

A proposta surgiu a partir da identificação de dificuldades no controle manual dos produtos, como desperdícios, falta de produtos e diferenças entre a quantidade registrada e a quantidade realmente existente.

---

## 🎯 Objetivo

O principal objetivo do sistema é oferecer uma forma simples e organizada de controlar o estoque da cantina escolar.

O sistema deverá permitir:

- Cadastrar produtos;
- Controlar a quantidade disponível;
- Registrar entradas de produtos;
- Registrar saídas de produtos;
- Registrar vendas;
- Controlar produtos próximos do vencimento;
- Identificar produtos com estoque baixo;
- Consultar informações do estoque;
- Gerar relatórios;
- Evitar que a quantidade de produtos fique negativa.

---

## 👥 Usuários do Sistema

O sistema terá dois tipos principais de usuários:

### 👤 Responsável pela Cantina

Será responsável pelas operações do dia a dia, podendo:

- Cadastrar produtos;
- Registrar entradas;
- Registrar saídas;
- Registrar vendas;
- Consultar informações do estoque.

### 🏫 Direção da Escola

Terá acesso às informações para acompanhamento e controle, podendo:

- Consultar o estoque;
- Visualizar relatórios;
- Acompanhar as vendas;
- Verificar produtos com estoque baixo;
- Verificar produtos próximos do vencimento.

Essas permissões foram definidas durante o levantamento de requisitos realizado com a responsável pela cantina. :contentReference[oaicite:2]{index=2}

---

## 🛒 Produtos

O sistema poderá trabalhar com diferentes tipos de produtos vendidos na cantina, como:

- Salgados;
- Refrigerantes;
- Sucos;
- Água;
- Doces;
- Biscoitos.

Cada produto terá informações como:

- Nome;
- Código;
- Categoria;
- Preço;
- Quantidade;
- Estoque mínimo;
- Fornecedor.

:contentReference[oaicite:3]{index=3}

---

## 📦 Controle de Estoque

O estoque será atualizado de acordo com as movimentações realizadas.

### Entrada

Quando novos produtos chegarem à cantina, a quantidade recebida será registrada e adicionada ao estoque.

### Saída

A saída poderá ocorrer principalmente por:

- Venda;
- Produto vencido;
- Produto danificado;
- Produto perdido.

As entradas aumentam a quantidade disponível e as saídas diminuem a quantidade.

O sistema não permitirá que o estoque fique com quantidade negativa.

:contentReference[oaicite:4]{index=4}

---

## 💰 Controle de Vendas

O sistema também terá controle das vendas realizadas na cantina.

Quando uma venda for registrada:

1. O produto será selecionado;
2. A quantidade vendida será informada;
3. O sistema registrará a venda;
4. A quantidade será retirada automaticamente do estoque.

Dessa forma, o estoque poderá permanecer atualizado de acordo com as vendas realizadas.

:contentReference[oaicite:5]{index=5}

---

## ⚠️ Alertas

O sistema contará com mecanismos para auxiliar no controle do estoque.

### 🔻 Estoque Baixo

Cada produto terá uma quantidade mínima definida.

Quando a quantidade disponível ficar abaixo desse limite, o sistema deverá apresentar um alerta.

### ⏰ Produtos Próximos do Vencimento

Os produtos poderão ser organizados por lotes e terão suas respectivas datas de validade.

O sistema poderá apresentar um alerta para produtos que estejam próximos do vencimento.

:contentReference[oaicite:6]{index=6}

---

## 📊 Painel do Sistema

O sistema terá um painel principal para facilitar a visualização das informações da cantina.

O protótipo inicial do painel apresenta:

- 👤 Identificação do usuário;
- 📦 Quantidade de produtos;
- ⚠️ Produtos com estoque baixo;
- ⏰ Produtos vencidos ou próximos do vencimento;
- 💰 Valor das vendas;
- 🔎 Campo de pesquisa;
- ➕ Botão para cadastrar um novo produto;
- 📋 Lista de produtos cadastrados.

O painel foi pensado para apresentar as principais informações de forma rápida, permitindo que o responsável pela cantina acompanhe a situação do estoque sem precisar acessar várias telas.

---

## 📑 Relatórios

O sistema deverá disponibilizar relatórios relacionados ao funcionamento da cantina, incluindo:

- Relatório do estoque atual;
- Produtos com estoque baixo;
- Produtos próximos do vencimento;
- Entradas de produtos;
- Saídas de produtos;
- Vendas realizadas.

:contentReference[oaicite:7]{index=7}

---

## 🗄️ Banco de Dados

Inicialmente, o sistema utilizará o **SQLite** para armazenamento dos dados.

As informações armazenadas poderão incluir:

- Produtos;
- Categorias;
- Estoque;
- Entradas;
- Saídas;
- Vendas;
- Lotes e validade;
- Usuários.

O uso de um banco de dados permitirá manter as informações organizadas e facilitar futuras consultas.

:contentReference[oaicite:8]{index=8}

---

## 💾 Backup

Para evitar a perda das informações, será realizada periodicamente uma cópia do banco de dados.

O backup terá como objetivo preservar os registros da cantina caso ocorra algum problema com os dados originais.

:contentReference[oaicite:9]{index=9}

---

## 🛠️ Tecnologias

As tecnologias previstas para o desenvolvimento do projeto são:

- **Python** - linguagem principal;
- **SQLite** - banco de dados;
- **Git** - controle de versão;
- **GitHub** - armazenamento e acompanhamento do projeto.

---

## 📌 Regras do Sistema

O sistema deverá seguir algumas regras principais:

1. Todo produto deverá possuir informações básicas para seu cadastro.
2. Toda entrada deverá aumentar a quantidade disponível.
3. Toda saída deverá diminuir a quantidade disponível.
4. Uma venda deverá gerar uma saída do produto.
5. O estoque nunca poderá ficar negativo.
6. Cada produto poderá possuir uma quantidade mínima.
7. Produtos abaixo do estoque mínimo deverão gerar um alerta.
8. Os produtos poderão ser organizados por lotes.
9. Os lotes poderão possuir datas de validade.
10. Produtos próximos do vencimento poderão gerar alertas.
11. As movimentações deverão ser registradas no sistema.

---

## 📅 Levantamento de Requisitos(OBS: Entrevista feita com IA)

O levantamento dos requisitos foi realizado por meio de uma entrevista com a responsável pela cantina da **Escola Novo Futuro (ENF)**.

**Responsável pela cantina:** Sara Ribeiro de Souza  
**Responsável pela entrevista:** Antonio Rodrigues da Silva Neto  
**Data:** 23/09/2026

:contentReference[oaicite:10]{index=10}

link do formulário: https://github.com/antoniorodrigues20082006-lab/Trabalho-python-/blob/main/Formulario_Cantina_Estoque.pdf
---

## 🚀 Situação do Projeto

O projeto encontra-se em fase de desenvolvimento.

### Etapas

- [x] Levantamento de requisitos
- [x] Identificação dos usuários
- [x] Definição das principais funcionalidades
- [x] Criação do protótipo inicial do painel
- [ ] Modelagem do banco de dados
- [ ] Desenvolvimento do sistema
- [ ] Implementação do controle de estoque
- [ ] Implementação das vendas
- [ ] Implementação dos alertas
- [ ] Implementação dos relatórios
- [ ] Testes
- [ ] Documentação final

---

## 📷 Protótipo do Painel

O primeiro protótipo foi desenvolvido para representar visualmente a tela principal do sistema, com informações resumidas do estoque, produtos cadastrados, alertas e vendas.

A interface poderá ser aprimorada durante o desenvolvimento, mantendo como objetivo principal a facilidade de uso e a visualização rápida das informações.

link do protótipo: https://github.com/antoniorodrigues20082006-lab/Trabalho-python-/blob/main/Prot%C3%B3tipo%20no%20papel.jpeg

---

## 🎓 Finalidade Acadêmica

Este projeto está sendo desenvolvido como atividade acadêmica do curso de **Ciência da Computação**, tendo como finalidade aplicar conhecimentos de programação, banco de dados, levantamento de requisitos, modelagem de sistemas e desenvolvimento de interfaces.

---

## 👨‍💻 Autor

**Antonio Rodrigues da Silva Neto**

Projeto acadêmico - Sistema de Estoque para Cantina Escolar.