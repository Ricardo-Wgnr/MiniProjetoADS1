import itertools
import subprocess
import csv
import time
import re

# ===========================
# Parâmetros do experimento
# ===========================
algoritmos = ["reno", "cubic"]
bers = [1e-6, 1e-5]
udp_load = 900  # Mbps
repeticoes = 8  # Número de repetições por combinação (conforme roteiro)

combinacoes = list(itertools.product(algoritmos, bers))

# ===========================
# Funções utilitárias
# ===========================
def run(cmd):
    """Executa comando e retorna stdout."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

def popen(cmd):
    """Executa comando em background."""
    subprocess.Popen(cmd, shell=True)

def set_tcp(alg):
    run(f"sudo himage pc4 sysctl -w net.ipv4.tcp_congestion_control={alg}")

def set_ber(value):
    run(f"sudo vlink -BER {int(1/value)} router1:router2")

def start_udp_load(value):
    popen(f"sudo himage pc1 iperf -c 10.0.3.20 -u -t 40 -b{value}M")

def start_tcp_load():
    """Executa iperf TCP por 30 segundos (conforme roteiro)"""
    return run("sudo himage pc4 iperf -c 10.0.4.20 -t 30")

def start_tcp_server():
    popen("sudo himage pc3 iperf -s")

def start_udp_server():
    popen("sudo himage pc2 iperf -s -u")

def start_tcpdump(filename):
    """Inicia tcpdump salvando em arquivo específico. Captura APENAS tcp do nosso host."""
    popen(f"sudo himage pc4 tcpdump -i eth0 -w {filename} host 10.0.4.20 and tcp")

def stop_servers():
    for pc in ["pc1", "pc2", "pc3"]:
        run(f"sudo himage {pc} pkill -f iperf")

def stop_tcpdump():
    run("sudo himage pc4 pkill -f tcpdump")

def reset_tcp_metrics():
    """Limpa a memória de métricas do TCP no emissor e receptor para não viciar a próxima rodada"""
    run("sudo himage pc4 sysctl -w net.ipv4.tcp_no_metrics_save=1")
    run("sudo himage pc3 sysctl -w net.ipv4.tcp_no_metrics_save=1")

# ===========================
# Função para processar pcap e calcular eficiência
# ===========================
def process_pcap(filename):
    """
    Lê pcap via tcpdump com a flag -e (para ler tamanho do frame L2), 
    soma bytes TCP (úteis) e bytes totais (frame L2 completo),
    retorna (bytes_tcp, bytes_totais, eficiencia, tcpdump_output)
    """
    # Usando -e para expor o cabeçalho Ethernet e pegar o length total da camada 2
    tcp_output = run(f"sudo himage pc4 tcpdump -nne -r {filename}")
    
    bytes_tcp = 0
    bytes_totais = 0
    
    for linha in tcp_output.splitlines():
        # Captura o primeiro length (Frame Total) e o último length (Payload TCP) da linha
        match = re.search(r'length\s+(\d+):.*length\s+(\d+)', linha)
        
        if match:
            tamanho_frame = int(match.group(1))
            tamanho_payload = int(match.group(2))
            
            bytes_tcp += tamanho_payload
            bytes_totais += tamanho_frame
    
    eficiencia = bytes_tcp / bytes_totais if bytes_totais > 0 else 0
    return bytes_tcp, bytes_totais, eficiencia, tcp_output

# ===========================
# Função para extrair média de vazão TCP do iperf
# ===========================
def media_vazao_iperf(saida_iperf):
    """
    Calcula média de todas as linhas de vazão do iperf.
    Retorna valor em Mbps.
    """
    vazoes = []
    for linha in saida_iperf.splitlines():
        match = re.search(r'([\d\.]+)\s*Mbits/sec', linha)
        if match:
            vazoes.append(float(match.group(1)))
    return sum(vazoes)/len(vazoes) if vazoes else 0.0

# ===========================
# Experimento principal
# ===========================
with open("resultados.csv", "w", newline='') as csvfile, \
     open("iperf.txt", "w") as f_iperf, \
     open("tcpdump.txt", "w") as f_tcpdump:

    writer = csv.writer(csvfile)
    # Cabeçalho formatado
    writer.writerow(["Algoritmo", "BER", "Repeticao", "Bytes_TCP", "Bytes_Totais", "Eficiencia", "Vazao_TCP_Mbps"])
    
    for alg, ber in combinacoes:
        print(f"\n{'='*40}")
        print(f"=== Teste: {alg}, BER={ber} ===")
        print(f"{'='*40}")
        
        set_tcp(alg)
        set_ber(ber)
        
        for repeticao in range(1, repeticoes + 1):
            print(f"\n--- Repetição {repeticao} ---")
            
            # Resetando métricas antes de iniciar
            reset_tcp_metrics()
            
            pcap_file = f"fluxo_{alg}_{ber}_{repeticao}.pcap"
            
            print("Iniciando tcpdump...")
            start_tcpdump(pcap_file)
            time.sleep(2)  # espera tcpdump iniciar
            
            print("Iniciando servidor UDP e carga...")
            start_udp_server()
            time.sleep(1)
            start_udp_load(udp_load)
            
            print("Iniciando servidor TCP...")
            start_tcp_server()
            time.sleep(1)  # espera servidor TCP iniciar
            
            print("Executando carga TCP (30 segundos)...")
            saida_iperf = start_tcp_load()
            
            # Salva saída completa do iperf
            f_iperf.write(f"\n=== {alg} BER={ber} Repetição {repeticao} ===\n")
            f_iperf.write(saida_iperf + "\n")
            
            print("Parando captura tcpdump...")
            stop_tcpdump()
            time.sleep(2) # Dar tempo para o arquivo ser salvo no disco do emulador
            
            print("Parando servidores...")
            stop_servers()
            
            print("Processando pcap e calculando eficiência...")
            bytes_tcp, bytes_totais, eficiencia, tcpdump_output = process_pcap(pcap_file)
            
            # Salva saída completa do tcpdump
            f_tcpdump.write(f"\n=== {alg} BER={ber} Repetição {repeticao} ===\n")
            f_tcpdump.write(tcpdump_output + "\n")
            
            vazao_tcp = media_vazao_iperf(saida_iperf)
            
            print(f">>> Resultados: Bytes Úteis: {bytes_tcp} | Frame Total: {bytes_totais}")
            print(f">>> Eficiência: {eficiencia:.4f} | Vazão TCP: {vazao_tcp:.2f} Mbps")
            
            writer.writerow([alg, ber, repeticao, bytes_tcp, bytes_totais, round(eficiencia, 4), vazao_tcp])

print("\n🚀 Experimento finalizado com sucesso! Resultados salvos em 'resultados.csv', 'iperf.txt' e 'tcpdump.txt'.")