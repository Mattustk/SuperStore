"""
Projeto Star Schema com SuperStore
Autor: Guilherme Coradini
Descrição: Modelagem dimensional de dados de vendas para análise em Power BI.
"""

import pyodbc
import pandas as pd

# ==========================================
# 1. CONEXÃO COM SQL SERVER
# ==========================================
server = '___________'  
database = '_____'     

conn_str = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={server};"
    f"DATABASE={database};"
    f"Trusted_Connection=yes;"
)

conn = pyodbc.connect(conn_str)
df = pd.read_sql("SELECT * FROM SuperStore", conn)



# ==========================================
# 2. TRATAMENTO DE TIPOS
# ==========================================

# Conversão para Datetime
df['Ship Date'] = pd.to_datetime(df['Ship Date'])
df['Order Date'] = pd.to_datetime(df['Order Date'])

# O "coerce" serve para: se tiver uma letra no meio do número, ele não trava o código, só ignora.
df['Sales'] = pd.to_numeric(df, errors='coerce')
df['Quantity'] = pd.to_numeric(df, errors='coerce')
df['Discount'] = pd.to_numeric(df, errors='coerce')
df['Profit'] = pd.to_numeric(df, errors='coerce')

# ==========================================
# 3. LIMPEZA DOS DADOS
# ==========================================
df = df.drop(columns=['Row ID'])  # Coluna inútil
df = df.drop_duplicates(subset=['Order ID', 'Product ID'])  # Remove duplicatas pela granularidade correta
df = df.dropna(subset=['Order ID', 'Customer ID', 'Product ID', 'Sales'])  # Remove nulos nas colunas críticas

# ==========================================
# 4. CRIAÇÃO DAS DIMENSÕES (COM SURROGATE KEYS)
# ==========================================
# Dimensão Envio
ship_dim = df[["Ship Date", "Ship Mode"]].drop_duplicates().reset_index(drop=True)
ship_dim['sk_shipping'] = range(1, 1 + len(ship_dim))

# Dimensão Cliente
customer_dim = df[["Customer ID", "Customer Name", "Segment"]].drop_duplicates().reset_index(drop=True)
customer_dim['sk_customer'] = range(1, 1 + len(customer_dim))

# Dimensão Produto
product_dim = df[["Product ID", "Product Name", "Category", "Sub-Category"]].drop_duplicates().reset_index(drop=True)
product_dim['sk_product'] = range(1, 1 + len(product_dim))

# Dimensão Região
region_dim = df[["Postal Code", "Country", "State", "City", "Region"]].drop_duplicates().reset_index(drop=True)
region_dim['sk_region'] = range(1, 1 + len(region_dim))

# ==========================================
# 5. CRIAÇÃO DA TABELA FATO
# ==========================================
fact_sales = df[['Customer ID', 'Product ID', 'Postal Code', 'Ship Date', 'Ship Mode', 
                 'Sales', 'Quantity', 'Discount', 'Profit']]

# ==========================================
# 6. MERGES (TRAZ AS SURROGATE KEYS PARA A FATO)
# ==========================================
fact_sales = fact_sales.merge(customer_dim[['Customer ID', 'sk_customer']], on='Customer ID', how='left')
fact_sales = fact_sales.merge(product_dim[['Product ID', 'sk_product']], on='Product ID', how='left')
fact_sales = fact_sales.merge(region_dim[['Postal Code', 'sk_region']], on='Postal Code', how='left')
fact_sales = fact_sales.merge(ship_dim[['Ship Date', 'Ship Mode', 'sk_shipping']], on=['Ship Date', 'Ship Mode'], how='left')

# ==========================================
# 7. VALIDAÇÃO DOS MERGES (GARANTE INTEGRIDADE REFERENCIAL)
# ==========================================
assert fact_sales['sk_customer'].isna().sum() == 0, "❌ Erro: Customer ID sem correspondência!" # Se algum valor dentro da "sk_customer" for invalido ira aparecer esse erro
assert fact_sales['sk_product'].isna().sum() == 0, "❌ Erro: Product ID sem correspondência!" # Se algum valor dentro da "sk_product" for invalido ira aparecer esse erro
assert fact_sales['sk_region'].isna().sum() == 0, "❌ Erro: Postal Code sem correspondência!" # Se algum valor dentro da "sk_region" for invalido ira aparecer esse erro
assert fact_sales['sk_shipping'].isna().sum() == 0, "❌ Erro: Ship Date/Mode sem correspondência!" # Se algum valor dentro da "sk_shipping" for invalido ira aparecer esse erro


# ==========================================
# 8. LIMPEZA FINAL DA FATO
# ==========================================
# Remove colunas originais (agora substituídas pelas SKs)
fact_sales = fact_sales.drop(columns=['Customer ID', 'Product ID', 'Postal Code', 'Ship Date', 'Ship Mode'])

# Ordena colunas no padrão profissional
fact_sales = fact_sales[['sk_customer', 'sk_product', 'sk_region', 'sk_shipping', 
                         'Sales', 'Quantity', 'Discount', 'Profit']]

# ==========================================
# 9. EXPORTAÇÃO PARA CSV (FORMATADO PARA POWER BI BRASIL)
# ==========================================
# Adicionado decimal=',' para o Power BI não quebrar as casas decimais
customer_dim.to_csv('dim_cliente.csv', index=False)
product_dim.to_csv('dim_produto.csv', index=False)
region_dim.to_csv('dim_regiao.csv', index=False)
ship_dim.to_csv('dim_envio.csv', index=False)
fact_sales.to_csv('fato_vendas.csv', index=False, decimal=',')

# Fecha conexão
conn.close()
