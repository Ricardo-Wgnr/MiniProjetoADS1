# MiniProjetoADS1

## Métricas

- Vazão média do fluxo TCP (iperf);
- Eficiência do fluxo TCP (tshark/tcpdump).

## Fatores

- Fator A - Algoritmo TCP
- Fator B - BER no enlace entre roteadores

## Parâmetros fixados

- Enlaces Ethernet 1 Gbps
- Janela TCP default
- Duração do teste: 30 segundos
- Carga UDP: 900 Mbps

## Configurar o venv

```
python3 -m venv .venv
```

## Ativar o venv
```
source .venv/bin/activate
```

## Instalando os pacotes

```
pip install -r requirements.txt
