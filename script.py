import itertools
import subprocess
import csv
from datetime import datetime
import re
import time

algoritmos = ["reno", "cubic"]
bers = [1e-6, 1e-5]
udp_load = [800, 900]

combinacoes = list(itertools.product(algoritmos, bers, udp_load))

def run(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout

def popen(cmd):
    return subprocess.Popen(cmd, shell=True)

def set_tcp(alg):
    cmd = f"sudo himage pc1 sysctl -w net.ipv4.tcp_congestion_control={alg}"
    run(cmd)
    
def set_ber(value):
    cmd = f"vlink -BER {int(1/value)} router1:router2"
    run(cmd)

def start_udp_load(value):
    cmd = f"sudo himage pc3 iperf -c 10.0.4.20 -u -t 40 -b{value}M"
    return popen(cmd)
    

def start_tcp_load():
    cmd = f"himage pc1 iperf -c 10.0.2.20 -t 30 -i 5"
    saida = run(cmd)
    return saida

def start_tcp_server():
    cmd = "himage pc2 iperf -s"
    popen(cmd)

def start_udp_server():
    cmd = "himage pc4 iperf -s -u"
    popen(cmd)

def start_tcpdump():
    cmd = "himage pc1 tcpdump -i eth0 -w fluxo.pcap host 10.0.2.20 and tcp"
    popen(cmd)

for alg, ber, load in combinacoes:

    print("setup iniciado")
    set_tcp(alg)
    set_ber(ber)
    print("setup feito")

    for repeticao in range(1,9):        

        print("start tcpdump")
        tcpdump = start_tcpdump()
        time.sleep(2)
        print("feito")
        
        print("start udp server")
        udp_server = start_udp_server()
        print("feito")
        time.sleep(1)
        print("start udp load")
        udp_load = start_udp_load(load)
        print("feito")

        print("start tcp server")
        tcp_server = start_tcp_server()
        print("feito")
        time.sleep(1)
        print("start tcp load")
        saida = start_tcp_load()
        print("feito")
        tcpdump.terminate()
        tcp_server.terminate()
        udp_server.terminate()
        udp_load.terminate()

        # experimento
            # vazao media: coletar saida iperf receptor tcp
            # eficiencia: capturar com tcpdump, iniciar alguns segundos antes do iperf e terminar depois
            # extrair daddos bytes uteis x total com tshark
            # salvar csv
            # resetar memoria tcp
