from typing import Sequence


def formata_valores(valor, prefixo=''):
    for unidade in ['', 'mil', 'milhões']:
        if valor < 1000:
            return f'{prefixo} {valor:.2f} {unidade}'
        valor /= 1000
    return f'{prefixo} {valor:.2f} bilhões'


    



