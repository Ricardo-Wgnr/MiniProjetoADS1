import itertools

algoritmos = ["reno", "cubic"]
bers = [1e-6, 1e-5]
udp_load = [800, 900]

combinacoes = list(itertools.product(algoritmos, bers, udp_load))

# print(combinacoes)
# print(len(combinacoes))

for alg, ber, load in combinacoes:
    for repeticao in range(1,9):
        # experimento
        # salvar csv
        pass
