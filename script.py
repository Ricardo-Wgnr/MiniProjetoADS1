import subprocess
import csv
import time
import re

# =================================================================
# Parâmetros do experimento (AJUSTE AQUI ANTES DE CADA RODADA!)
# =================================================================
algoritmos = ["reno", "cubic"]

# MUDE ESTA VARIÁVEL PARA COMBINAR COM O QUE VOCÊ COLOCOU NO IMUNES
BER_ATUAL = 1e-6

udp_load = 900  # Mbps
repeticoes = 8  # Número de repetições por combinação
# =================================================================

def run(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

def popen(cmd):
    subprocess.Popen(cmd, shell=True)

def set_tcp(alg):
    run(f"sudo himage pc4 sysctl -w net.ipv4.tcp_congestion_control={alg}")

def start_udp_load(value):
    popen(f"sudo himage pc1 iperf -c 10.0.3.20 -u -t 40 -b {value}M")

def start_tcp_load():
    return run("sudo himage pc4 iperf -c 10.0.4.20 -t 30")

def start_tcp_server():
    popen("sudo himage pc3 iperf -s")

def start_udp_server():
    popen("sudo himage pc2 iperf -s -u")

def start_tcpdump(filename):
    popen(f"sudo himage pc4 tcpdump -i eth0 -w {filename} host 10.0.4.20 and tcp")

def stop_servers():
    for pc in ["pc1", "pc2", "pc3"]:
        run(f"sudo himage {pc} pkill -f iperf")

def stop_tcpdump():
    run("sudo himage pc4 pkill -f tcpdump")

def reset_tcp_metrics():
    run("sudo himage pc4 sysctl -w net.ipv4.tcp_no_metrics_save=1")
    run("sudo himage pc3 sysctl -w net.ipv4.tcp_no_metrics_save=1")

# ===========================
# Função original de processamento (Regex)
# ===========================
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

def media_vazao_iperf(saida_iperf):
    vazoes = []
    for linha in saida_iperf.splitlines():
        match = re.search(r'([\d\.]+)\s*Mbits/sec', linha)
        if match:
            vazoes.append(float(match.group(1)))
    return sum(vazoes)/len(vazoes) if vazoes else 0.0

# Nomes de arquivos dinâmicos
nome_csv = f"resultados_BER_{BER_ATUAL}.csv"
nome_txt = f"iperf_BER_{BER_ATUAL}.txt"

with open(nome_csv, "w", newline='') as csvfile, \
     open(nome_txt, "w") as f_iperf:

    writer = csv.writer(csvfile)
    writer.writerow(["Algoritmo", "BER", "Repeticao", "Bytes_TCP", "Bytes_Totais", "Eficiencia", "Vazao_TCP_Mbps"])
    
    for alg in algoritmos:
        print(f"\n{'='*40}")
        print(f"=== Teste: {alg}, BER travada em: {BER_ATUAL} ===")
        print(f"{'='*40}")
        
        set_tcp(alg)
        
        for repeticao in range(1, repeticoes + 1):
            print(f"\n--- Repetição {repeticao} ---")
            
            reset_tcp_metrics()
            
            pcap_file = f"fluxo_{alg}_{BER_ATUAL}_{repeticao}.pcap"
            
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
            
            f_iperf.write(f"\n=== {alg} BER={BER_ATUAL} Repetição {repeticao} ===\n")
            f_iperf.write(saida_iperf + "\n")
            
            print("Parando captura tcpdump...")
            stop_tcpdump()
            time.sleep(2)
            
            print("Parando servidores...")
            stop_servers()
            
            print("Processando pcap via tcpdump com Regex...")
            bytes_tcp, bytes_totais, eficiencia, tcpdump_output = process_pcap(pcap_file)
            
            # Limpeza de memória (A solução para o travamento do IMUNES!)
            print("Apagando .pcap para liberar memória da máquina virtual...")
            run(f"sudo himage pc4 rm {pcap_file}")
            
            vazao_tcp = media_vazao_iperf(saida_iperf)
            
            print(f">>> Resultados: Bytes Úteis: {bytes_tcp} | Frame Total: {bytes_totais}")
            print(f">>> Eficiência: {eficiencia:.4f} | Vazão TCP: {vazao_tcp:.2f} Mbps")
            
            writer.writerow([alg, BER_ATUAL, repeticao, bytes_tcp, bytes_totais, round(eficiencia, 4), vazao_tcp])

print(f"\n🚀 Rodada concluída com sucesso! Os dados estão salvos em '{nome_csv}'.")