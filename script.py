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
    saida[0] = run(cmd)
    cmd = "tshark -r fluxo.pcap -T fields -e frame.len | awk '{s+=$1} END {print s}'"
    saida[1] = run(cmd)
    return saida

# for alg, ber in combinacoes:

#     print("setup iniciado")
#     set_tcp(alg)
#     set_ber(ber)

#     for repeticao in range(1,9):        

#         print("start tcpdump")
#         start_tcpdump()
#         time.sleep(2)
        
#         print("start udp server")
#         start_udp_server()
#         time.sleep(1)
#         print("start udp load")
#         start_udp_load(udp_load)

#         print("start tcp server")
#         start_tcp_server()
#         time.sleep(1)
#         print("start tcp load")
#         saida = start_tcp_load()

#         # experimento
#             # vazao media: coletar saida iperf receptor tcp
#             # eficiencia: capturar com tcpdump, iniciar alguns segundos antes do iperf e terminar depois
#             # extrair daddos bytes uteis x total com tshark
#             # salvar csv
#             # resetar memoria tcp

# testes

set_tcp(algoritmos[0])
set_ber(bers[0])

for repeticao in range(1,3):        
    print("start tcpdump")
    start_tcpdump()
    time.sleep(2)
    
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
    saida_tshark = output_tshark()
    stop_servers()

    with open("iperf.txt", "a") as f:
        f.write(saida_iperf)

    with open("tshark.txt", "a") as f:
        f.write(saida_tshark)


