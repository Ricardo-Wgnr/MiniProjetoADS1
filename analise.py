import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import scipy.stats as stats

# ==========================================================
# 1. Carregamento dos Dados
# ==========================================================
arquivo_alvo = 'resultados_finais_completos.csv'

try:
    df = pd.read_csv(arquivo_alvo)
    print(f"📥 Arquivo '{arquivo_alvo}' carregado com sucesso!")
except FileNotFoundError:
    print(f"❌ Erro: O arquivo '{arquivo_alvo}' não foi encontrado na pasta.")
    exit()

# Ordena os dados pela coluna BER para o eixo X do gráfico ficar na ordem crescente
df = df.sort_values(by='BER')

# ==========================================================
# 2. Função para calcular o Intervalo de Confiança (95%)
# ==========================================================
def confidence_interval(data, confidence=0.95):
    n = len(data)
    m = np.mean(data)
    std_err = stats.sem(data)
    h = std_err * stats.t.ppf((1 + confidence) / 2, n - 1)
    return h

# ==========================================================
# 3. Análise e Geração de Tabelas e Gráficos
# ==========================================================
variaveis_de_saida = ['Vazao_TCP_Mbps', 'Eficiencia']

for var in variaveis_de_saida:
    print(f"\n{'='*50}")
    print(f"ANÁLISE ESTATÍSTICA: {var}")
    print(f"{'='*50}")
    
    # Agrupa por Algoritmo e BER e calcula as métricas
    resumo = df.groupby(['Algoritmo', 'BER'])[var].agg(
        Média=np.mean,
        Desvio_Padrão=np.std,
        IC_95=confidence_interval
    ).reset_index()
    
    # [NOVIDADE]: Cria uma cópia só para a tabela de texto ficar bonita no terminal
    resumo_tabela = resumo.copy()
    resumo_tabela['BER'] = resumo_tabela['BER'].apply(lambda x: f"10^{int(np.log10(x))}")
    print(resumo_tabela.to_string(index=False))
    
    algoritmos = resumo['Algoritmo'].unique()
    bers = resumo['BER'].unique()
    
    x = np.arange(len(bers))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(8, 6))
    
    for i, alg in enumerate(algoritmos):
        dados_alg = resumo[resumo['Algoritmo'] == alg]
        medias = dados_alg['Média'].values
        erros = dados_alg['IC_95'].values
        
        posicao = x - width/2 if i == 0 else x + width/2
        
        ax.bar(posicao, medias, width, yerr=erros, label=alg.capitalize(), 
               capsize=8, alpha=0.8, edgecolor='black')

    min_val = (resumo['Média'] - resumo['IC_95']).min()
    max_val = (resumo['Média'] + resumo['IC_95']).max()
    margem = (max_val - min_val) * 0.5 
    
    ax.set_ylim(max(0, min_val - margem), max_val + margem)

    # Configuração de Títulos e Eixos
    ax.set_xlabel('Taxa de Erro de Bit (BER)', fontsize=12)
    ax.set_ylabel(f'{var}', fontsize=12)
    ax.set_title(f'Efeito Principal: Algoritmo e BER na {var}\n(Intervalo de Confiança de 95%)', fontsize=14)
    ax.set_xticks(x)
    
    # [NOVIDADE]: Renderiza a BER como notação matemática real no eixo X do gráfico (ex: 10^{-5})
    rotulos_ber = [f'$10^{{{int(np.log10(ber))}}}$' for ber in bers]
    ax.set_xticklabels(rotulos_ber, fontsize=14)
    
    ax.legend(title="Algoritmo TCP", loc='best')
    
    ax.yaxis.grid(True, linestyle='--', alpha=0.7)
    ax.set_axisbelow(True)
    
    plt.tight_layout()
    nome_arquivo = f'grafico_{var.lower()}.png'
    plt.savefig(nome_arquivo, dpi=300)
    print(f"[OK] Gráfico gerado e salvo como: {nome_arquivo}")

print("\n🎉 Todos os gráficos e análises foram atualizados com sucesso!")