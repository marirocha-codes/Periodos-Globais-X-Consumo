import os
import sqlite3
import pandas as pd
from datetime import datetime

# Caminho para o banco de dados relacional
caminho_banco = r"C:\Users\Public\data_warehouse_vendas.db"

def gerar_tabela_mestre_completa():
    """
    Consolida o histórico real (1000 registros) com as simulações da IA (10 registros)
    em uma única tabela mestre denormalizada física no SQLite.
    Insere automaticamente o contexto geográfico (País/Continente) e cadastra a origem
    do dado para evitar valores nulos (nulls) ou relações perdidas no Power BI.
    """
    if not os.path.exists(caminho_banco):
        print(f"❌ Erro: O arquivo do banco de dados não existe em: {caminho_banco}")
        print("Certifique-se de executar o script de reconstrução primeiro para inicializar o DW.")
        return

    print("🔌 Conectando ao Banco de Dados SQLite...")
    conn = sqlite3.connect(caminho_banco)
    
    try:
        print("📖 Lendo tabelas do Data Warehouse...")
        df_fato_historica = pd.read_sql_query("SELECT * FROM fato_vendas", conn)
        df_dim_cliente = pd.read_sql_query("SELECT * FROM dim_cliente", conn)
        df_dim_plataforma = pd.read_sql_query("SELECT * FROM dim_plataforma", conn)
        
        # Leitura de fato da IA do banco de dados, e aviso
        try:
            df_fato_ia = pd.read_sql_query("SELECT * FROM fato_vendas_ia", conn)
            tem_fato_ia = True
            print(f"🤖 Encontrada tabela de IA 'fato_vendas_ia' com {len(df_fato_ia)} registros.")
        except Exception:
            tem_fato_ia = False
            print("⚠️ Nota: Tabela transacional 'fato_vendas_ia' não encontrada no banco. Consolidando apenas a estrutura principal...")

        print("🧩 Cruzando dados históricos (unindo Fato + Cliente + Plataforma) para criar a estrutura Master...")
        
        #  Join do histórico com as dimensões de cliente para trazer País, Continente e Idade
        df_historico_rico = df_fato_historica.merge(
            df_dim_cliente[["ID_Cliente", "Pais", "Continente", "Idade"]],
            on="ID_Cliente",
            how="left"
        )
        
        # Join com a plataforma para trazer o Item Vendido e Categoria
        df_historico_rico = df_historico_rico.merge(
            df_dim_plataforma[["Plataforma", "Item_Vendido", "Categoria"]],
            on="Plataforma",
            how="left"
        )

        # Padroniza o metadado de inserção do histórico
        df_historico_rico["inserido_em"] = "Carga Histórica"
        df_historico_rico["Origem_Dado"] = "Histórico Real"

        if tem_fato_ia:
            # Garante que as colunas da Fato IA estejam no mesmo formato e ordem
            # A Fato IA já possui País, Continente e Idade de forma nativa por vir denormalizada
            df_ia_alinhada = df_fato_ia.copy()
            df_ia_alinhada["Origem_Dado"] = "Simulado por IA"
            
            # Caso a coluna de data de inserção não exista, cria uma marcação
            if "inserido_em" not in df_ia_alinhada.columns:
                df_ia_alinhada["inserido_em"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            else:
                # Substituição de possíveis nulos na inserção da IA pela data atual
                df_ia_alinhada["inserido_em"] = df_ia_alinhada["inserido_em"].fillna(
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
        else:
            df_ia_alinhada = pd.DataFrame(columns=df_historico_rico.columns)

        print("🔗 Unificando o histórico consolidado de vendas com as projeções de 2026 da IA...")
        
        # Lista exata das 16 colunas finais que farão parte do Schema Unificado Master
        colunas_final = [
            "Ano", "Plataforma", "Pais", "Continente", "Idade", "ID_Pedido", "ID_Cliente",
            "Data_Venda", "Item_Vendido", "Categoria", "Valor_Venda_USD", "Status_Retorno",
            "Prob_Retorno", "Custo_Log_Reverso", "Origem_Dado", "inserido_em"
        ]

        # Garantia de que ambos os DataFrames possuam as mesmas colunas para a união
        df_historico_rico = df_historico_rico[colunas_final]
        if tem_fato_ia:
            df_ia_alinhada = df_ia_alinhada[colunas_final]

        # Reordenação cronologicamente pela Data de Venda
        df_mestre_final = pd.concat([df_historico_rico, df_ia_alinhada], ignore_index=True)
        df_mestre_final["Data_Venda"] = pd.to_datetime(df_mestre_final["Data_Venda"])
        df_mestre_final = df_mestre_final.sort_values(by="Data_Venda").reset_index(drop=True)
        
        # Conversão a data de volta para string formato ISO para o SQLite salvar corretamente
        df_mestre_final["Data_Venda"] = df_mestre_final["Data_Venda"].dt.strftime("%Y-%m-%d")

        print(f"💾 Salvando nova tabela física 'fato_vendas_mestre_completa' com {len(df_mestre_final)} registros...")
        
        df_mestre_final.to_sql(
            "fato_vendas_mestre_completa", 
            conn, 
            if_exists="replace", 
            index=False
        )
        
        print("\n" + "="*80)
        print("🎉 SUCESSO! A TABELA MESTRE CONSOLIDADA FOI CRIADA.")
        print(f"📍 Local absoluto: {os.path.abspath(caminho_banco)}")
        print("🗂️  Tabela disponível: 'fato_vendas_mestre_completa' (16 Colunas alinhadas)")
        print(f"📊 Volume Financeiro Totalizado: USD {df_mestre_final['Valor_Venda_USD'].sum():,.2f}")
        print("="*80)

    except Exception as e:
        print(f"❌ Ocorreu um erro durante a consolidação da tabela: {e}")
    finally:
        conn.close()
        print("🔌 Conexão com o banco de dados finalizada com segurança.")

if __name__ == "__main__":
    print("="*80)
    print("🚀 INICIANDO CONSTRUÇÃO DA TABELA MESTRE DENORMALIZADA (FATO COMPLETA)...")
    print("="*80)
    gerar_tabela_mestre_completa()
    print("="*80)