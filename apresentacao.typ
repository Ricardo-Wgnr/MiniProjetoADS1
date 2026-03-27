#import "@preview/diatypst:0.9.1": *
#import "@preview/mmdr:0.2.1": mermaid

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

A proposta desse miniprojeto consiste em analisar uma situação de transmissão TCP com uma carga UDP intensa passando simultaneamente pelo mesmo link (congestionamento), verificando qual algoritmo TCP (Reno ou Cubic) se sai melhor. Para análise, foi feito um experimento que terá parâmetros fixados, variáveis de saída e também fatores que serão variados. O experimento deve ser realizado com 8 repetições para cada configuração e deve se fazer todas as combinações possíveis de fatores. No nosso caso 2², já que temos 2 fatores.


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

== Metodologia

Neste trabalho, foi utilizado o software IMUNES para a criação da simulação da rede. Além disso, empregamos a linguagem Python para automatizar os processos de coleta e análise de dados. Essas duas funções foram organizadas em códigos distintos: o script.py, responsável pela coleta, e o analise.py, dedicado à análise dos dados.

== Loop Principal

#align(center + horizon)[

#image("Diagrama1.png")
]

== Cálculo da eficiência e set da BER

- Tentamos utilizar o comando tshark disponibilizado para o cálculo da eficiência e vlink para alterar a BER, mas não obtivemos resultados satisfatórios.

- No caso da BER, ela não alterava, então buscamos inserir uma perda em porcentagem equivalente a essa BER.

- Já para o cálculo da eficiencia, fizemos uma busca utilizando regex no próprio pcap.

- Vamos mostrar os trechos de código a seguir:

== Set da BER

#show raw: set text(size: 8pt)

```py
def set_packet_loss(ber):
    # Converte a BER em taxa de perda de pacotes (%) e aplica direto no kernel do PC4.
    if ber == 0:
        loss_percent = 0.0
        ber_texto = "0"
    else:
        prob_sucesso_pacote = (1 - ber) ** 12000
        prob_perda_pacote = 1 - prob_sucesso_pacote
        loss_percent = prob_perda_pacote * 100
        ber_texto = f"10^{int(math.log10(ber))}" # Transforma 1e-05 em 10^-5

    # 1. Apaga qualquer regra de controle de tráfego antiga na interface eth0 do PC4
    run("sudo himage pc4 tc qdisc del dev eth0 root 2>/dev/null")
    
    # 2. Aplica a nova regra de perda de pacotes
    if loss_percent > 0:
        run(f"sudo himage pc4 tc qdisc add dev eth0 root netem loss {loss_percent:.4f}%")
```

== Cálculo da eficiencia

```py
def process_pcap(filename):
    tcp_output = run(f"sudo himage pc4 tcpdump -nne -r {filename}")

    bytes_tcp = 0
    bytes_totais = 0
    
    for linha in tcp_output.splitlines():
        match = re.search(r'length\s+(\d+):.*length\s+(\d+)', linha)
        if match:
            tamanho_frame = int(match.group(1))
            tamanho_payload = int(match.group(2))
            
            bytes_tcp += tamanho_payload
            bytes_totais += tamanho_frame
    
    eficiencia = bytes_tcp / bytes_totais if bytes_totais > 0 else 0
    return bytes_tcp, bytes_totais, eficiencia, tcp_output
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