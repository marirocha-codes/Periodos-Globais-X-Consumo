# Periodos-Globais-X-Consumo
# Analytics Engineering & BI

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![SQLite](https://img.shields.io/badge/SQLite-Database-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Power BI](https://img.shields.io/badge/Power_BI-Dashboard-F2C811?style=for-the-badge&logo=powerbi&logoColor=black)](https://powerbi.microsoft.com/)
[![Gemini AI](https://img.shields.io/badge/Gemini_AI-API-8E75B2?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)

---

## 📌 Sobre o Projeto

Este projeto tem como objetivo monitorar e analisar como fenômenos socioeconômicos globais influenciam diretamente o comportamento do consumidor e as tomadas de decisão no mercado de moda.

A solução abrange desde a construção do pipeline automatizado de dados (arquitetura Medallion em SQLite) até a geração de relatórios de mercado e inteligência preditiva com **Google Gemini AI**.

👉 **Para ler a análise completa de mercado e visualizações de dados, acesse o [Relatório de Análise (REPORT.md)](REPORT.md).**

---

##  Arquitetura da Solução

1. **Ingestão & ETL (Python):** Geração e tratamento de dados brutos calibrados com benchmarks reais do setor.
2. **Data Warehouse (SQLite):** Organização em pipeline estruturado (camadas Bronze, Silver e Gold / `dim_cliente`).
3. **Dashboards (Power BI):** Modelagem dimensional e visuais interativos segmentados por perfil, categoria, país e faixa etária.
4. **Previsões Dinâmicas (Gemini AI):** Integração com a API do Gemini para análises preditivas em tempo real.

---

##  Como Executar o Projeto Localmente:

### 1. Pré-requisitos:
* Python 3.10+ instalado
* Chave de API do Google Gemini ([Obtenha aqui](https://aistudio.google.com/))

### 2. Configuração do Ambiente
Clone este repositório e instale as seguintes dependências:


```bash
git clone [https://github.com/seu-usuario/seu-repositorio.git](https://github.com/seu-usuario/seu-repositorio.git)
cd seu-repositorio
pip install -r requirements.txt
```

###3. Configure sua Chave de API (Gemini)

Crie um arquivo chamado .env na raiz do projeto e adicione a sua chave da API do Gemini:
GEMINI_API_KEY=sua_chave_aqui

###3. Execução do Pipeline
Para alimentar o banco de dados e gerar as previsões dinâmicas, execute o comando:

Bash
python main.py
