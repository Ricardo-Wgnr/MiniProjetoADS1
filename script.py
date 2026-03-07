import itertools
import subprocess
import csv
from datetime import datetime
import re
import time

algoritmos = ["reno", "cubic"]
bers = [1e-6, 1e-5]
udp_load = 900

combinacoes = list(itertools.product(algoritmos, bers))

def run(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout

def popen(cmd):
    subprocess.Popen(cmd, shell=True)

def set_tcp(alg):
    cmd = f"sudo himage pc4 sysctl -w net.ipv4.tcp_congestion_control={alg}"
    run(cmd)
    
def set_ber(value):
    cmd = f"sudo vlink -BER {int(1/value)} router1:router2"
    run(cmd)

def start_udp_load(value):
    cmd = f"sudo himage pc1 iperf -c 10.0.3.20 -u -t 40 -b{value}M"
    return popen(cmd)
    

def start_tcp_load():
    cmd = f"sudo himage pc4 iperf -c 10.0.4.20 -t 30"
    saida = run(cmd)
    return saida

def start_tcp_server():
    cmd = "sudo himage pc3 iperf -s"
    popen(cmd)

def start_udp_server():
    cmd = "sudo himage pc2 iperf -s -u"
    popen(cmd)

def start_tcpdump():
    cmd = "sudo himage pc4 tcpdump -i eth0 -w fluxo.pcap host 10.0.4.20 and tcp"
    popen(cmd)

def stop_servers():
    cmd = "sudo himage pc2 pkill -f iperf"
    run(cmd)
    cmd = "sudo himage pc3 pkill -f iperf"
    run(cmd)
    cmd = "sudo himage pc1 pkill -f iperf"
    run(cmd)

def output_tshark():
    cmd = "sudo himage pc4 tshark -r fluxo.pcap -T fields -e tcp.len | awk '{s+=$1} END {print s}'"
    saida = []
    saida.append(run(cmd))
    cmd = "sudo himage pc4 tshark -r fluxo.pcap -T fields -e frame.len | awk '{s+=$1} END {print s}'"
    saida.append(run(cmd))
    return saida

def stop_tcpdump():
    cmd = "sudo himage pc4 pkill -f tcpdump"
    run(cmd)

def reset_tcp_metrics():
    run("sudo himage pc4 sysctl -w net.ipv4.tcp_no_metrics_save=1")
    run("sudo himage pc3 sysctl -w net.ipv4.tcp_no_metrics_save=1")

set_tcp(algoritmos[0])
set_ber(bers[0])

set_tcp(algoritmos[0])
set_ber(bers[0])

nome_arquivo_csv = "resultados_iperf.csv"

with open(nome_arquivo_csv, "w", newline='') as f:

    writer = csv.writer(f)
    writer.writerow(["exp_id", "repeticao", "algoritmoTcp", "ber", "udp_load", "vazao_mbps", "bytes_mbytes", "duracao_sec"])

for alg, ber in combinacoes:

    print("setup iniciado")
    set_tcp(alg)
    set_ber(ber)

    for repeticao in range(1, 9):   

        print(f"\n--- Iniciando repetição {repeticao} ---")
        reset_tcp_metrics()

        print("start udp server")
        start_udp_server()
        time.sleep(1)

        print("start udp load")
        start_udp_load(udp_load)

        print("start tcp server")
        start_tcp_server()
        time.sleep(1)

        print("start tcp load")
        saida_iperf = start_tcp_load()

        stop_servers()

        vazao_mbps = 0.0
        bytes_mbytes = 0.0
        duracao_sec = 0.0

        padrao = r'(\d+\.\d+)-\s*(\d+\.\d+)\s+sec\s+(\d+(?:\.\d+)?)\s+MBytes\s+(\d+(?:\.\d+)?)\s+Mbits/sec'
        match = re.search(padrao, saida_iperf)

        if match:
            duracao_sec = float(match.group(2)) - float(match.group(1))
            bytes_mbytes = float(match.group(3))
            vazao_mbps = float(match.group(4))

        exp_id = f"TCP_{alg}_BER_{ber}"

        linha_csv = [exp_id, repeticao, alg, ber, udp_load, vazao_mbps, bytes_mbytes, duracao_sec]

        with open(nome_arquivo_csv, "a", newline='') as f:
            writer = csv.writer(f)
            writer.writerow(linha_csv)

        print(f"Repetição {repeticao} salva! Vazão: {vazao_mbps} Mbits/sec")


