import subprocess
import csv
import time
import re
import math  # Adicionado para formatar a BER elegantemente

# =================================================================
# Parâmetros do experimento (AUTOMAÇÃO TOTAL)
# =================================================================
algoritmos = ["reno", "cubic"]

bers_para_testar = [1e-5, 1e-6]

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

def set_packet_loss(ber):
    """
    Converte a BER em taxa de perda de pacotes (%) e aplica direto no kernel do PC4.
    """
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
        
    print(f"[*] Kernel ajustado: {loss_percent:.4f}% de pacotes perdidos (Simulando BER de {ber_texto})")

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