# %% [markdown]
# ## folha de pagamento
# 
# Evolução história dos vencimentos dos servidores
# 
# ### Data Sources
# - file1 : Description of where this file came from
# 
# ### Changes
# - 07-01-2023 : Started project

# %%
import contextlib
import subprocess
import time
import webbrowser
from datetime import datetime
from pathlib import Path
from random import randint
from threading import Thread
import pyautogui

from rpapy.core.activities import click_vision, wait_element_vision, write_text_vision
from rpapy.core.localizador import ImageNotDisappearError, ImageNotFoundError

# %% [markdown]
# ### Functions Variables Define

# %%
# Navegadores web
CHROME = 'chrome'
EDGE = 'edge'
FIREFOX = 'firefox'
OPERA = 'opera'

NAVEGADORES = {
    CHROME: r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    EDGE: r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    FIREFOX: r"C:\Program Files\Mozilla Firefox\firefox.exe",
    OPERA: r"C:\Users\codigo100cera\AppData\Local\Programs\Opera GX\opera.exe"    
}

BROWSER_WSL = {
    CHROME: "google-chrome",
    EDGE: "google-chrome",
    FIREFOX: "firefox",
    OPERA: "opera" 
}
for nome, navegador_path in NAVEGADORES.items():
    webbrowser.register(nome, None,webbrowser.BackgroundBrowser(navegador_path))

def open_page(browser_name, mes_competencia, ano_competencia, *, wsl=None):

    url = f'http://portaldatransparencia.pmmc.com.br/index.php/rh_verbas/index/{mes_competencia:0>2}/{ano_competencia}/'

    if wsl:
        # Formata a url para ser executada no terminal bash do linux
        url_preenchida = url_preenchida.replace('\n', '%0A').replace(' ', '%20').replace('&', '\&')
        comando = f"bash -c '"+BROWSER_WSL.get(browser_name, 'google-chrome')+f" {url_preenchida}'"
        print(comando)
        t = Thread(target=subprocess.call, args=(comando,))
        t.start()
    else:
        browser = webbrowser.get(browser_name)
        browser.open_new_tab(url)

# %% [markdown]
# ### File Downloads

# %%
destino = 'D:\\05-WORKSPACES\\PythonProjects\\folha_de_pagamento\\data\\raw{enter}'
in_files_csv = (Path.cwd() / 'data' / 'raw').glob('*.csv')
folhas_baixadas = [f.name.lower() for f in in_files_csv]

for ano in range(2009, 2024):
    for mes in range(1, 13):
        if ano == 2009 and mes < 5: continue
        if ano == 2023 and mes > 6: break

        if f'{ano}-{mes:0>2}.csv' in folhas_baixadas: continue

        open_page(CHROME, mes, ano, wsl=False)

        print('Baixando o arquivo', f'{ano}-{mes:0>2}.csv')
        for _ in range(10):
            with contextlib.suppress(ImageNotFoundError):
                # esperar carregar a pagina
                wait_element_vision('label_matricula', max_wait=2)
                break
            with contextlib.suppress(ImageNotFoundError):
                # esperar carregar a pagina
                wait_element_vision('label_matricula2', max_wait=2)
                break        
        
        # efetuar um clique no botão para baixar o arquivo
        click_vision('btn_download_file', max_wait=5, interval=2)

        # preencher o campo nome do arquivo .csv
        write_text_vision('campo_nome_arquivo', backend='uia', text='{VK_CONTROL down}a{DELETE}{VK_CONTROL up}{VK_SHIFT up}'+f'{ano}-{mes:0>2}.csv'+'{ENTER}', move_x=50, after=5)

        # clicar no botão fechar do browser
        click_vision('btn_fechar_browser', max_wait=10)

        pyautogui.sleep(3)


# %%



