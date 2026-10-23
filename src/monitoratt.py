import json
import os
import sqlite3
import time
from datetime import datetime
from typing import List

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types
import pandas as pd
from pydantic import BaseModel

# ==============================================================================
# CONFIGURAÇÃO DE SEGURANÇA E AMBIENTE (.env)
# ==============================================================================
load_dotenv()

api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    raise ValueError(
        "Erro: Chave de API do Gemini não encontrada!\n"
        "Verifique se o arquivo .env foi criado e se contém GEMINI_API_KEY=sua_chave."
    )

client = genai.Client(api_key=api_key)

caminho_banco = r"C:\Users\Public\data_warehouse_vendas.db"


# ==============================================================================
# HELPER: CONSULTA O ÚLTIMO ID SEQUENCIAL DA FATO
# ==============================================================================
def obter_proximo_id_pedido():
    if not os.path.exists(caminho_banco):
        return 2001

    conn = sqlite3.connect(caminho_banco)
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='fato_vendas_ia'"
        )
        if not cursor.fetchone():
            conn.close()
            return 2001

        cursor.execute("SELECT ID_Pedido FROM fato_vendas_ia")
        rows = cursor.fetchall()

        max_id = 2000
        for (row,) in rows:
            if row and row.startswith("P"):
                try:
                    num = int(row[1:])
                    if num > max_id:
                        max_id = num
                except ValueError:
                    pass
        conn.close()
        return max_id + 1
    except Exception:
        conn.close()
        return 2001


# ==============================================================================
# MODELOS PYDANTIC
# ==============================================================================
class ParametroIA(BaseModel):
    ano: int
    contexto: str
    perfil_con: str
    estrategia: str


class TendenciaModaIA(BaseModel):
    ano: int
    item_tendencia: str
    categoria: str
    plataformas_venda: str
    fonte_trend: str


class VendaTransacionalIA(BaseModel):
    Ano: int
    Plataforma: str
    Pais: str
    Continente: str
    Idade: int
    ID_Pedido: str
    ID_Cliente: str
    Data_Venda: str
    Item_Vendido: str
    Categoria: str
    Valor_Venda_USD: float
    Status_Retorno: str
    Prob_Retorno: float
    Custo_Log_Reverso: float


class MonitoramentoVendasIA(BaseModel):
    parametros: ParametroIA
    tendencias: List[TendenciaModaIA]
    vendas_geradas: List[VendaTransacionalIA]


# ==============================================================================
# GERADOR IA (GEMINI 2.5 FLASH)
# ==============================================================================
def analisar_e_gerar_vendas_ia(fato_atual_2026, quantidade_vendas=10):
    proximo_id = obter_proximo_id_pedido()
    ultimo_id_esperado = proximo_id + quantidade_vendas - 1

    prompt = f"""
    Como um Engenheiro de Dados e Analista de Mercado especialista no varejo de moda global,
    sua tarefa é analisar o fato macroeconômico atual de 2026 e gerar os dados correspondentes:
    
    FATO DE MERCADO:
    "{fato_atual_2026}"
    
    VOCÊ DEVE RETORNAR OS SEGUINTES TRÊS CONJUNTOS DE DADOS:
    
    1. PARAMETROS:
       - ano: 2026
       - contexto: Resumo de 2 a 4 palavras com underlines (Ex: Eficiencia_IA_Conforto_Sofisticado)
       - perfil_con: Perfil do consumidor (Ex: Seletivo_Identitario, GenZ_UltraFast)
       - estrategia: Estratégia recomendada (Ex: Eficiencia_IA_Durabilidade)
    
    2. TENDENCIAS:
       - Gere de 1 a 3 registros de tendências mapeadas para o contexto de 2026.
       - ano: 2026
       - item_tendencia: Itens em alta separados por vírgula
       - categoria: Nome da categoria de tendência
       - plataformas_venda: Principais plataformas separadas por vírgula (Ex: SHEIN, Depop, Vinted, The RealReal)
       - fonte_trend: Fonte da pesquisa (Ex: McKinsey 2026 / Depop Report 2026)
    
    3. VENDAS GERADAS (exatamente {quantidade_vendas} transações):
       - Ano: 2026
       - Plataforma: Marcas reais (Ex: SHEIN, Depop, Vinted, Poshmark, Enjoei, The RealReal, Zara Online)
       - Pais: País do comprador
       - Continente: América Latina, América do Norte, Europa, Ásia
       - Idade: Idade coerente
       - ID_Pedido: Formato sequencial rigoroso de 'P{proximo_id}' até 'P{ultimo_id_esperado}'
       - ID_Cliente: Formato 'C206-XXXX'
       - Data_Venda: Formato texto 'YYYY-MM-DD' em 2026
       - Item_Vendido: Item específico
       - Categoria: Categoria do item
       - Valor_Venda_USD: Valor monetário em USD
       - Status_Retorno: 'Concluido' ou 'Devolvido'
       - Prob_Retorno: Valor decimal entre 0.0 e 1.0
       - Custo_Log_Reverso: Se 'Devolvido', entre 10.00 e 35.00 USD. Se 'Concluido', DEVE SER 0.00.
    """

    print(
        f"🤖 IA processando mercado de 2026 e gerando {quantidade_vendas} transações (IDs P{proximo_id} a P{ultimo_id_esperado})..."
    )

    max_tentativas = 5
    tempo_espera = 4

    for tentativa in range(1, max_tentativas + 1):
        try:
            resposta = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=MonitoramentoVendasIA,
                    temperature=0.3,
                ),
            )
            return json.loads(resposta.text)
        except errors.APIError as e:
            if e.code in [503, 429]:
                if tentativa < max_tentativas:
                    time.sleep(tempo_espera)
                    tempo_espera *= 2
                else:
                    raise e
            else:
                raise e


# ==============================================================================
# ATUALIZAÇÃO ATÔMICA DAS TABELAS NO SQLITE
# ==============================================================================
def atualizar_data_warehouse(dados_ia):
    conn = sqlite3.connect(caminho_banco)
    cursor = conn.cursor()
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 1. PARAMETROS_IA (Garante a recriação limpa com novas colunas)
    cursor.execute("DROP TABLE IF EXISTS parametros_ia")
    cursor.execute("""
        CREATE TABLE parametros_ia (
            ano INTEGER PRIMARY KEY,
            contexto TEXT,
            perfil_con TEXT,
            estrategia TEXT,
            ultima_atualizacao TEXT
        )
    """)

    p = dados_ia["parametros"]
    cursor.execute(
        """
        INSERT INTO parametros_ia (ano, contexto, perfil_con, estrategia, ultima_atualizacao)
        VALUES (?, ?, ?, ?, ?)
    """,
        (p["ano"], p["contexto"], p["perfil_con"], p["estrategia"], agora),
    )

    # 2. TENDENCIAS_MODA_IA
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tendencias_moda_ia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ano INTEGER,
            item_tendencia TEXT,
            categoria TEXT,
            plataformas_venda TEXT,
            fonte_trend TEXT,
            ultima_atualizacao TEXT
        )
    """)

    for t in dados_ia["tendencias"]:
        cursor.execute(
            """
            INSERT INTO tendencias_moda_ia (ano, item_tendencia, categoria, plataformas_venda, fonte_trend, ultima_atualizacao)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                t["ano"],
                t["item_tendencia"],
                t["categoria"],
                t["plataformas_venda"],
                t["fonte_trend"],
                agora,
            ),
        )

    # 3. FATO_VENDAS_IA
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fato_vendas_ia (
            Ano INTEGER,
            Plataforma TEXT,
            Pais TEXT,
            Continente TEXT,
            Idade INTEGER,
            ID_Pedido TEXT PRIMARY KEY,
            ID_Cliente TEXT,
            Data_Venda TEXT,
            Item_Vendido TEXT,
            Categoria TEXT,
            Valor_Venda_USD REAL,
            Status_Retorno TEXT,
            Prob_Retorno REAL,
            Custo_Log_Reverso REAL,
            inserido_em TEXT
        )
    """)

    for venda in dados_ia["vendas_geradas"]:
        cursor.execute(
            """
            INSERT INTO fato_vendas_ia (
                Ano, Plataforma, Pais, Continente, Idade, ID_Pedido, ID_Cliente,
                Data_Venda, Item_Vendido, Categoria, Valor_Venda_USD,
                Status_Retorno, Prob_Retorno, Custo_Log_Reverso, inserido_em
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ID_Pedido) DO UPDATE SET
                Plataforma = excluded.Plataforma,
                Pais = excluded.Pais,
                Continente = excluded.Continente,
                Idade = excluded.Idade,
                ID_Cliente = excluded.ID_Cliente,
                Data_Venda = excluded.Data_Venda,
                Item_Vendido = excluded.Item_Vendido,
                Categoria = excluded.Categoria,
                Valor_Venda_USD = excluded.Valor_Venda_USD,
                Status_Retorno = excluded.Status_Retorno,
                Prob_Retorno = excluded.Prob_Retorno,
                Custo_Log_Reverso = excluded.Custo_Log_Reverso,
                inserido_em = excluded.inserido_em
        """,
            (
                venda["Ano"],
                venda["Plataforma"],
                venda["Pais"],
                venda["Continente"],
                venda["Idade"],
                venda["ID_Pedido"],
                venda["ID_Cliente"],
                venda["Data_Venda"],
                venda["Item_Vendido"],
                venda["Categoria"],
                venda["Valor_Venda_USD"],
                venda["Status_Retorno"],
                venda["Prob_Retorno"],
                venda["Custo_Log_Reverso"],
                agora,
            ),
        )

    # 4. DIM_PLATAFORMA (Consolida plataformas da Fato Vendas + Tendências)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dim_plataforma (
            nome_plataforma TEXT PRIMARY KEY
        )
    """)

    # Insere plataformas únicas da fato_vendas_ia
    cursor.execute("""
        INSERT OR IGNORE INTO dim_plataforma (Plataforma)
        SELECT DISTINCT Plataforma FROM fato_vendas_ia WHERE Plataforma IS NOT NULL;
    """)

    # Insere plataformas das tendencias_moda_ia tratando a string separada por vírgula
    cursor.execute("""
        INSERT OR IGNORE INTO dim_plataforma (Plataforma)
        SELECT DISTINCT TRIM(value) 
        FROM tendencias_moda_ia, json_each('["' || REPLACE(plataformas_venda, ',', '","') || '"]')
        WHERE TRIM(value) IS NOT NULL AND TRIM(value) != '';
    """)

    conn.commit()
    conn.close()

    print("\n" + "=" * 80)
    print("✅ DATA WAREHOUSE ATUALIZADO COM SUCESSO!")
    print(f"📍 Banco: {caminho_banco}")
    print(f"🕒 Timestamp do Lote: {agora}")
    print("=" * 80)


if __name__ == "__main__":
    fato_mercado_2026 = (
        "McKinsey aponta que em 2026 o consumo de moda é focado em 'Elegance Meets Ease' "
        "(conforto sofisticado), eficiência por IA e dinâmica forte de Ultra Fast Fashion "
        "concorrendo com plataformas de resale."
    )

    resultado = analisar_e_gerar_vendas_ia(
        fato_mercado_2026, quantidade_vendas=10
    )
    atualizar_data_warehouse(resultado)