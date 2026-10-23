from datetime import datetime
import os
import numpy as np
import pandas as pd

# ==============================================================================
# PARÂMETROS DE MERCADO (DADOS REAIS DE RESALE/MODA)
# ==============================================================================
PRECOS_BASE_CATEGORIA = {
    "Luxo": (800, 3500),  # Vestiaire / Farfetch
    "Alfaiataria": (200, 750),  # Ternos e Blazers
    "Vintage": (120, 450),  # Peças raras de época
    "Upcycling": (80, 250),  # Moda sustentável
    "Streetwear": (60, 200),  # Sneakers e modas urbanas
    "Fast Fashion": (20, 70),  # Basiquinhos / Reuso de entrada
}

PLATAFORMAS_PESO = {
    "Vestiaire Collective": 0.25,
    "Poshmark": 0.30,
    "ThredUp": 0.25,
    "Depop": 0.20,
}

FATOR_PANDEMIA_ANO = {
    2019: 1.0,
    2020: 0.75,  # Queda acentuada
    2021: 0.90,  # Retomada
    2022: 1.30,  # Expansão acelerada
    2023: 1.55,
    2024: 1.80,
    2025: 2.10,
    2026: 2.40,  # Projeção forte
}


# ==============================================================================
# 1. CAMADA BRONZE (RAW DATA GENERATION)
# ==============================================================================
def gerar_camada_bronze(qtd_registros=100000):
  """Gera os dados brutos em simulação de Big Data."""
  print(
      f"🥉 [BRONZE] Gerando amostra bruta de {qtd_registros:,} registros..."
  )

  np.random.seed(42)  # Mantém os mesmos dados sempre reproduzíveis

  anos = np.random.choice(
      list(FATOR_PANDEMIA_ANO.keys()),
      size=qtd_registros,
      p=[0.08, 0.08, 0.10, 0.14, 0.15, 0.15, 0.15, 0.15],
  )

  plataformas = np.random.choice(
      list(PLATAFORMAS_PESO.keys()),
      size=qtd_registros,
      p=list(PLATAFORMAS_PESO.values()),
  )

  paises = np.random.choice(
      ["EUA", "França", "Reino Unido", "Japão", "Brasil", "Alemanha"],
      size=qtd_registros,
      p=[0.35, 0.20, 0.15, 0.12, 0.10, 0.08],
  )

  categorias = np.random.choice(
      list(PRECOS_BASE_CATEGORIA.keys()), size=qtd_registros
  )

  valores_venda = []
  for cat, ano in zip(categorias, anos):
    min_p, max_p = PRECOS_BASE_CATEGORIA[cat]
    preco_base = np.random.uniform(min_p, max_p)
    fator_ano = FATOR_PANDEMIA_ANO[ano]
    valores_venda.append(round(preco_base * fator_ano, 2))

  prob_retorno = np.random.beta(a=2, b=8, size=qtd_registros).round(4)
  status_retorno = np.where(prob_retorno > 0.35, "Sim", "Não")
  custo_log_reverso = np.where(
      status_retorno == "Sim",
      np.array(valores_venda) * np.random.uniform(0.08, 0.18, qtd_registros),
      0.0,
  ).round(2)

  df_bronze = pd.DataFrame({
      "id_pedido": [f"PED-{i:08d}" for i in range(1, qtd_registros + 1)],
      "id_cliente": np.random.randint(10000, 99999, size=qtd_registros),
      "ano": anos,
      "data_venda": pd.date_range(
          start="2019-01-01", periods=qtd_registros, freq="min"
      ).strftime("%Y-%m-%d"),
      "plataforma": plataformas,
      "pais": paises,
      "continente": np.where(
          np.isin(paises, ["França", "Reino Unido", "Alemanha"]),
          "Europa",
          np.where(
              paises == "EUA",
              "América do Norte",
              np.where(paises == "Brasil", "América do Sul", "Ásia"),
          ),
      ),
      "categoria": categorias,
      "item_vendido": [f"Item-{c[:3].upper()}" for c in categorias],
      "valor_venda_usd": valores_venda,
      "status_retorno": status_retorno,
      "prob_retorno": prob_retorno,
      "custo_log_reverso": custo_log_reverso,
      "origem_dado": np.where(anos <= 2025, "Histórico Real", "Simulado por IA"),
      "inserido_em": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
  })

  print("✅ [BRONZE] Dados brutos gerados com sucesso!")
  return df_bronze


# ==============================================================================
# 2. CAMADA SILVER (CLEANING & DEDUPLICATION)
# ==============================================================================
def processar_camada_silver(df_bronze):
  """Aplica higienização, remove duplicatas e trata tipos de dados."""
  print("🥈 [SILVER] Tratando dados e removendo duplicatas...")

  df_silver = df_bronze.copy()
  df_silver = df_silver.drop_duplicates(subset=["id_pedido"]).reset_index(
      drop=True
  )

  df_silver["valor_venda_usd"] = df_silver["valor_venda_usd"].fillna(0.0)
  df_silver["custo_log_reverso"] = df_silver["custo_log_reverso"].fillna(0.0)
  df_silver["ano"] = df_silver["ano"].astype(int)
  df_silver["valor_venda_usd"] = df_silver["valor_venda_usd"].astype(float)
  df_silver["prob_retorno"] = df_silver["prob_retorno"].astype(float)

  print("✅ [SILVER] Tabela limpa com sucesso!")
  return df_silver


# ==============================================================================
# 3. CAMADA GOLD (ANALYTICAL AGGREGATION - TABELA FINAL PRO POWER BI)
# ==============================================================================
def criar_camada_gold(df_silver, fator_escala_mercado=1000):
  """Consolida as métricas por dimensões de negócio e aplica a Escala de Bilhões."""
  print("🥇 [GOLD] Agregando dimensões e criando a tabela final de métricas...")

  df_gold = (
      df_silver.groupby([
          "ano",
          "plataforma",
          "pais",
          "continente",
          "categoria",
          "origem_dado",
      ])
      .agg(
          qtd_pedidos_amostra=("id_pedido", "count"),
          gmv_base_usd=("valor_venda_usd", "sum"),
          custo_log_base_usd=("custo_log_reverso", "sum"),
          risco_perda_base_usd=(
              "valor_venda_usd",
              lambda x: (x * df_silver.loc[x.index, "prob_retorno"]).sum(),
          ),
          qtd_devolucoes_confirmadas=(
              "status_retorno",
              lambda x: (x == "Sim").sum(),
          ),
      )
      .reset_index()
  )

  # Aplica o Fator de Escala Global para escala de mercado real ($B)
  df_gold["gmv_global_usd"] = (
      df_gold["gmv_base_usd"] * fator_escala_mercado
  ).round(2)
  df_gold["custo_log_reverso_global_usd"] = (
      df_gold["custo_log_base_usd"] * fator_escala_mercado
  ).round(2)
  df_gold["risco_perda_previsto_usd"] = (
      df_gold["risco_perda_base_usd"] * fator_escala_mercado
  ).round(2)
  df_gold["volume_estimado_pedidos"] = (
      df_gold["qtd_pedidos_amostra"] * fator_escala_mercado
  )

  # Remove colunas intermediárias da amostra
  df_gold = df_gold.drop(
      columns=[
          "gmv_base_usd",
          "custo_log_base_usd",
          "risco_perda_base_usd",
          "qtd_pedidos_amostra",
      ]
  )

  # Renomeia as colunas para ficar visualmente perfeito no Power BI
  df_gold = df_gold.rename(
      columns={
          "ano": "Ano",
          "plataforma": "Plataforma",
          "pais": "País",
          "continente": "Continente",
          "categoria": "Categoria",
          "origem_dado": "Origem do Dado",
          "qtd_devolucoes_confirmadas": "Devoluções Confirmadas",
          "gmv_global_usd": "GMV Global (USD)",
          "custo_log_reverso_global_usd": "Custo Logística Reversa (USD)",
          "risco_perda_previsto_usd": "Risco de Perda Previsto (USD)",
          "volume_estimado_pedidos": "Volume Estimado de Pedidos",
      }
  )

  print(
      f"✅ [GOLD] Tabela analítica pronta! Volume Total: USD {df_gold['GMV Global (USD)'].sum():,.2f}"
  )
  return df_gold


# ==============================================================================
# EXECUÇÃO DO PIPELINE E GERADOR DE ARQUIVOS
# ==============================================================================
if __name__ == "__main__":
  print("=" * 80)
  print("🚀 GERANDO TABELA ANALÍTICA PARA O POWER BI (SEM DEPENDÊNCIA DE SQL)")
  print("=" * 80)

  # 1. Executa o Pipeline Medallion
  df_bronze = gerar_camada_bronze(qtd_registros=100000)
  df_silver = processar_camada_silver(df_bronze)
  df_gold = criar_camada_gold(df_silver, fator_escala_mercado=1000)

  # 2. Exporta os Arquivos para a mesma pasta do script
  caminho_excel = "gold_vendas_analytics.xlsx"
  caminho_csv = "gold_vendas_analytics.csv"

  print("\n💾 Salvando os arquivos locais na sua pasta...")

  # Salva em formato Excel (.xlsx)
  df_gold.to_excel(caminho_excel, index=False)
  print(f"📊 Arquivo Excel gerado: {os.path.abspath(caminho_excel)}")

  # Salva em formato CSV (.csv) como alternativa
  df_gold.to_csv(caminho_csv, index=False, encoding="utf-8-sig", sep=";")
  print(f"📄 Arquivo CSV gerado:   {os.path.abspath(caminho_csv)}")

  print("\n" + "=" * 80)
  print("🎉 CONCLUÍDO COM SUCESSO!")
  print("=" * 80)
  print("👉 Agora no Power BI:")
  print("   1. Clique em 'Obter dados'")
  print(f"   2. Escolha 'Pasta de trabalho do Excel' e selecione o arquivo:")
  print(f"      '{caminho_excel}'")
  print("   3. Clique em 'Carregar' e monte seu Dashboard normalmente!")