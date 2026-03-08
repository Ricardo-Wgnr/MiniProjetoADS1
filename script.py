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
repeticoes = 3  # número de repetições por combinação

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
    """Executa iperf TCP e retorna todas as linhas de saída."""
    return run("sudo himage pc4 iperf -c 10.0.4.20 -t 10")

def start_tcp_server():
    popen("sudo himage pc3 iperf -s")

def start_udp_server():
    popen("sudo himage pc2 iperf -s -u")

def start_tcpdump(filename):
    """Inicia tcpdump salvando em arquivo específico"""
    popen(f"sudo himage pc4 tcpdump -i eth0 -w {filename} host 10.0.4.20 and tcp")

def stop_servers():
    for pc in ["pc1", "pc2", "pc3"]:
        run(f"sudo himage {pc} pkill -f iperf")

def stop_tcpdump():
    run("sudo himage pc4 pkill -f tcpdump")

# ===========================
# Função para processar pcap e calcular eficiência
# ===========================
def process_pcap(filename):
    """
    Lê pcap via tcpdump, soma bytes TCP (úteis) e bytes totais (TCP + headers),
    retorna (bytes_tcp, bytes_totais, eficiencia, tcpdump_output)
    """
    tcp_output = run(f"sudo himage pc4 tcpdump -nn -r {filename}")
    
    bytes_tcp = 0
    bytes_totais = 0
    
    for linha in tcp_output.splitlines():
        match_tcp = re.search(r'length (\d+)', linha)
        if match_tcp:
            payload = int(match_tcp.group(1))
            bytes_tcp += payload
            bytes_totais += payload + 54  # 54 bytes = Ethernet+IP+TCP header
    
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
    writer.writerow(["Algoritmo", "BER", "Repeticao", "Bytes_TCP", "Bytes_Totais", "Eficiencia", "Vazao_TCP_Mbps"])
    
    for alg, ber in combinacoes:
        print(f"\n=== Teste: {alg}, BER={ber} ===")
        set_tcp(alg)
        set_ber(ber)
        
        for repeticao in range(1, repeticoes + 1):
            print(f"\n--- Repetição {repeticao} ---")
            
            pcap_file = f"fluxo_{alg}_{ber}_{repeticao}.pcap"
            
            print("Iniciando tcpdump...")
            start_tcpdump(pcap_file)
            time.sleep(3)  # espera tcpdump iniciar
            
            print("Iniciando servidor UDP e carga...")
            start_udp_server()
            time.sleep(3)
            start_udp_load(udp_load)
            
            print("Iniciando servidor TCP...")
            start_tcp_server()
            time.sleep(3)  # espera servidor TCP iniciar
            
            print("Executando carga TCP...")
            saida_iperf = start_tcp_load()
            
            # Salva saída completa do iperf
            f_iperf.write(f"\n=== {alg} BER={ber} Repetição {repeticao} ===\n")
            f_iperf.write(saida_iperf + "\n")
            
            print("Parando captura tcpdump...")
            stop_tcpdump()
            time.sleep(1)
            
            print("Parando servidores...")
            stop_servers()
            
            print("Processando pcap e calculando eficiência...")
            bytes_tcp, bytes_totais, eficiencia, tcpdump_output = process_pcap(pcap_file)
            
            # Salva saída completa do tcpdump
            f_tcpdump.write(f"\n=== {alg} BER={ber} Repetição {repeticao} ===\n")
            f_tcpdump.write(tcpdump_output + "\n")
            
            vazao_tcp = media_vazao_iperf(saida_iperf)
            
            print(f"Bytes TCP: {bytes_tcp}, Bytes Totais: {bytes_totais}, Eficiência: {eficiencia:.4f}, Vazão TCP: {vazao_tcp:.2f} Mbps")
            
            writer.writerow([alg, ber, repeticao, bytes_tcp, bytes_totais, eficiencia, vazao_tcp])

print("\nExperimento finalizado! Resultados salvos em 'resultados.csv', 'iperf.txt' e 'tcpdump.txt'.")