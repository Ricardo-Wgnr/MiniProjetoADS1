#import "@preview/diatypst:0.9.1": *

#set text(size: 1.1em, lang: "pt")
#set figure.caption(position: top)
#set outline(depth: 1)

#show: slides.with(
  title: "Miniprojeto ADS", // Required
  subtitle: "Medição ativa com iperf com apoio de medição passiva(tcpdump)",
  date: "24 de março de 2026",
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
