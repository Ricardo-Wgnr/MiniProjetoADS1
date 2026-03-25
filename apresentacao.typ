#import "@preview/diatypst:0.9.1": *

#set text(size: 1.1em, lang: "pt")
#set figure.caption(position: top)
#set outline(depth: 1)

#show: slides.with(
  title: "Miniprojeto ADS", // Required
  subtitle: "Medição ativa com iperf com apoio de medição passiva(tcpdump)",
  date: "26 de março de 2026",
  authors: ("Igor Budag, Ricardo Wagner"),

  // Optional (for more see docs at https://mdwm.org/diatypst/)
  ratio: 16/9,
  layout: "medium",
  title-color: green.darken(60%),
  toc: true,
  count: "number"
)

#let tecnica_card(corpo) = {
  rect(
    width: 100%, 
    inset: 15pt, 
    radius: 4pt,
    fill: green.lighten(95%),
    stroke: (left: 5pt + green.darken(60%)),
    text(size: 1.1em, corpo)
  )
}

#let param_card(nome, valor, simbolo) = {
  rect(
    width: 100%, inset: 10pt, radius: 4pt,
    fill: green.lighten(95%),
    stroke: (left: 5pt + green.darken(60%)),
    grid(columns: (1fr, auto, 1.5cm), align: horizon,
      text(weight: "medium", nome),
      text(weight: "bold", valor),
      align(right, text(fill: black.lighten(20%), $#simbolo$))
    )
  )
}
= Objetivo

== Objetivo

A proposta desse miniprojeto consiste em analisar uma situação de transmissão tcp com uma carga UDP intensa passando simultaneamente pelo mesmo link (congestionamento). Para análise, foi feito um experimento que terá parâmetros fixados, variáveis de saída e também fatores que serão variados. O experimento deve ser realizado com 8 repetições para cada configuração e deve se fazer todas as combinações possíveis de fatores. No nosso caso 2², já que temos 2 fatores.


== Objetivo

#align(center + horizon)[
  #image("Img_Exp.png")
]

= Variáveis

== Variáveis de Saída

#stack(
  spacing: 10pt,
  tecnica_card([Vazão Média do Fluxo TCP (iperf)]),
  tecnica_card([Eficiência do Fluxo TCP (tshark)])
)

== Variáveis de Entrada (fatores)

#stack(
  spacing: 10pt,
  param_card("Algoritimo TCP", none, "Reno/Cubic"),
  param_card("BER no enlace entre roteadores", none, [$10^(-6)$/$10^(-5)$])
)

== Parâmetros Fixados

#stack(
  spacing: 10pt,
  param_card("Enlace Ethernet", none, "1 [Gbps]"),
  param_card("Janela TCP default", none, "128 [KByte]"),
  param_card("Duração do teste", none, "30 [s]"),
  param_card("Carga UDP", none, "900 [Mbps]"),
  param_card("Número de repetições", none, "32")
)

= Metodologia

== Script utilizado
Neste trabalho, foi utilizado o software IMUNES para a criação da simulação da rede. Além disso, empregamos a linguagem Python para automatizar os processos de coleta e análise de dados. Essas duas funções foram organizadas em códigos distintos: o script.py, responsável pela coleta, e o analise.py, dedicado à análise dos dados.
#show raw: set text(size: 11pt)

#show raw.where(block: true): set text(size: 9pt)

```py
# =================================================================
# Parâmetros do experimento (AUTOMAÇÃO TOTAL)
# =================================================================
algoritmos = ["reno", "cubic"]

bers_para_testar = [1e-5, 1e-6]

udp_load = 900  # Mbps
repeticoes = 8  # Número de repetições por combinação
# =================================================================
```


== script.py

```py
# ===========================
# Execução Principal
# ===========================
nome_csv = "resultados_finais_completos.csv"
nome_txt = "iperf_logs_completos.txt"

with open(nome_csv, "w", newline='') as csvfile, \
     open(nome_txt, "w") as f_iperf:

    writer = csv.writer(csvfile)
    writer.writerow(["Algoritmo", "BER", "Repeticao", "Bytes_TCP", "Bytes_Totais", "Eficiencia", "Vazao_TCP_Mbps"])
    
    for ber_atual in bers_para_testar:
        # Formata para texto bonito
        ber_texto = f"10^{int(math.log10(ber_atual))}" if ber_atual > 0 else "0"
        
        print(f"\n{'#'*60}")
        print(f"🚀 INICIANDO BATERIA PARA BER = {ber_texto}")
        print(f"{'#'*60}")
        
        # Injeta a perda de pacotes direto no Linux do PC4!
        set_packet_loss(ber_atual)
        
        for alg in algoritmos:
            print(f"\n{'='*40}")
            print(f"=== Teste: {alg} | BER: {ber_texto} ===")
            print(f"{'='*40}")
            
            set_tcp(alg)
            
            for repeticao in range(1, repeticoes + 1):
                print(f"\n--- Repetição {repeticao} ---")
                
                reset_tcp_metrics()
                
                # Mantivemos o número decimal normal pro nome do arquivo não bugar no Linux
                pcap_file = f"fluxo_{alg}_{ber_atual}_{repeticao}.pcap"
                
                print("Iniciando tcpdump...")
                start_tcpdump(pcap_file)
                time.sleep(2)
                
                print("Iniciando servidor UDP e carga...")
                start_udp_server()
                time.sleep(1)
                start_udp_load(udp_load)
                
                print("Iniciando servidor TCP...")
                start_tcp_server()
                time.sleep(1)
                
                print("Executando carga TCP (30 segundos)...")
                saida_iperf = start_tcp_load()
                
                f_iperf.write(f"\n=== {alg} BER={ber_texto} Repetição {repeticao} ===\n")
                f_iperf.write(saida_iperf + "\n")
                
                print("Parando captura tcpdump...")
                stop_tcpdump()
                time.sleep(2)
                
                print("Parando servidores...")
                stop_servers()
                
                print("Processando pcap via tcpdump com Regex...")
                bytes_tcp, bytes_totais, eficiencia, tcpdump_output = process_pcap(pcap_file)
                
                print("Apagando .pcap para liberar memória da máquina virtual...")
                run(f"sudo himage pc4 rm {pcap_file}")
                
                vazao_tcp = media_vazao_iperf(saida_iperf)
                
                print(f">>> Resultados: Bytes Úteis: {bytes_tcp} | Frame Total: {bytes_totais}")
                print(f">>> Eficiência: {eficiencia:.4f} | Vazão TCP: {vazao_tcp:.2f} Mbps")
                
                # O CSV continua recebendo a variável ber_atual (ex: 1e-05) pro script de gráficos funcionar!
                writer.writerow([alg, ber_atual, repeticao, bytes_tcp, bytes_totais, round(eficiencia, 4), vazao_tcp])

print(f"\n🎉 Experimento 100% concluído! Todos os dados estão consolidados no arquivo '{nome_csv}'.")
```


== analise.py
```py
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
```
= Resultados

== Vazão Média
#align(center + horizon)[
  #image("grafico_vazao_tcp_mbps.png")
]
  
== Eficiência

#align(center + horizon)[
  #image("grafico_eficiencia.png")
]

== Tabela Resumo

#table(
  columns: (auto, auto, 1fr, 1fr),
  inset: 10pt,
  align: center + horizon,
  stroke: (x, y) => if y == 0 { (bottom: 1pt + black) } else { (bottom: 0.5pt + gray.lighten(50%)) },
  fill: (x, y) => if y == 0 { gray.lighten(80%) },
  
  [*Algoritmo*], [*BER*], [*Vazão Média (Mbps)*], [*Eficiência Média*],
  
  [Cubic], [$10^(-6)$], [158.88 ± 3.05], [0.9908 ± 0.0007],
  [Cubic], [$10^(-5)$], [4.38 ± 0.33],   [0.9433 ± 0.0012],
  [Reno],  [$10^(-6)$], [154.88 ± 1.44], [0.9939 ± 0.0001],
  [Reno],  [$10^(-5)$], [11.09 ± 1.00],  [0.9584 ± 0.0028],
)

= Conclusão

== Conclusão

Pelos resultados obtidos podemos observar que quando a rede está sem problemas, os algoritmos não tem uma diferença significativa de desempenho, mas quando temos uma BER pior, podemos ver que o Reno é superior em ambas métricas.