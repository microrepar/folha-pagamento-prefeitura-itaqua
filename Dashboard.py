from pathlib import Path
from typing import List

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st  # pip install streamlit
import streamlit_authenticator as stauth  # pip install streamlit-authenticator
import yaml
from streamlit_extras.metric_cards import style_metric_cards
from streamlit_plotly_events import plotly_events
from yaml.loader import SafeLoader

from utils import formata_valores

# emojis: https://www.webfx.com/tools/emoji-cheat-sheet/
st.set_page_config(page_title="Dashboard Folha", page_icon=":bar_chart:", layout="wide")


config_file = Path(__file__).parent / 'config.yaml'

def get_config():
    with config_file.open('rb') as file:
        config = yaml.load(file, Loader=SafeLoader)
    return config

config = get_config()
authenticator = stauth.Authenticate(
    config['credentials'],              # credentials:      Dict['usernames', Dict['<alias>', Dict['email | name | password', str]]]
    config['cookie']['name'],           # cookie:           str
    config['cookie']['key'],            # cookie:           str
    config['cookie']['expiry_days'],    # cookie:           str
    config['preauthorized'],            # preauthorized:    List[str]
)

def authentication():
    name, authentication_status, username = authenticator.login("Login", "main")

    if authentication_status == False:
        st.error("Username/password is incorrect")

    if authentication_status == None:
        st.warning("Please enter your username and password")

    if authentication_status:    
        # ---- SIDEBAR ----
        authenticator.logout(f"Logout | {name}", "sidebar")

        if username == 'admin' and st.sidebar.checkbox('Authentication Tools'):
            
            try:
                registry = authenticator.register_user('Register user', preauthorization=False)

                if registry:
                    st.success('User registered successfully')
                    with config_file.open('w') as file:
                        yaml.dump(config, file, default_flow_style=False)
            except Exception as e:
                st.error(e)
            
            st.divider()

            st.markdown(f'### Registred Users')
            placeholder_data_editor = st.empty()

            df = pd.DataFrame(config['credentials']['usernames']).T.reset_index()

            editor_config = {
                'name': st.column_config.TextColumn('Name (required)', required=True),
                'password': st.column_config.TextColumn('Password'),
                'index': st.column_config.TextColumn('Username'),
                'email': st.column_config.TextColumn('E-mail (required)'),
            }

            if 'flag_reset' not in st.session_state:
                st.session_state.flag_reset = False


            if st.button('Reset', type='primary'):
                st.session_state.flag_reset = not st.session_state.flag_reset
            
            placeholder_alert_empty = st.empty()
            
            if st.session_state.flag_reset:
                editor_key = 'edited_data1'
                edited_df = placeholder_data_editor.data_editor(df, 
                                                            num_rows="dynamic", 
                                                            use_container_width=True,
                                                            column_config=editor_config,
                                                            disabled=['password', 'index'],
                                                            key=editor_key)                
            else:
                editor_key = 'edited_data'
                edited_df = placeholder_data_editor.data_editor(df, 
                                                            num_rows="dynamic", 
                                                            use_container_width=True,
                                                            column_config=editor_config,
                                                            disabled=['password', 'index'],
                                                            key=editor_key)
            
            
            result_df = edited_df.copy().set_index('index')
            result_df.index.name = None

            config['credentials']['usernames'] = result_df.T.to_dict()

            if st.session_state[editor_key].get('deleted_rows'):  
                
                flag_contem_admin = False
                
                for index in st.session_state[editor_key]['deleted_rows']:
                    username = df.iloc[index]['index']

                    if 'admin' in username:
                        flag_contem_admin = True
                        break

                if not flag_contem_admin:
                    with config_file.open('w') as file:
                        yaml.dump(config, file, default_flow_style=False)                    
                else:
                    placeholder_alert_empty.error('O usuário "admin" não pode ser removido, efetue o reset e exclua qualquer registro de usuário exceto o admin.')
                    st.session_state[editor_key]['deleted_rows'] = []
            
            
            if st.session_state[editor_key].get('edited_rows'):                
                try:
                    with config_file.open('w') as file:
                        yaml.dump(config, file, default_flow_style=False)                    
                    
                    placeholder_alert_empty.success('Atualização aplicada com sucesso')
                    st.session_state[editor_key]['edited_rows'] = {}
                except Exception as error:
                    placeholder_alert_empty.error(str(error), icon='🚨')

            if st.session_state[editor_key].get('added_rows'):
                placeholder_alert_empty.error('Não é permitido a adição de novos registos pelo quadro, por favor use o formulário para adicionar novos usuários.', icon='🚨')
        
        else:
            dash()    

def dash():
    ano_dir               = Path.cwd() / "data" / "processed" / 'ano'
    mes_dir               = Path.cwd() / "data" / "processed" / 'mes'
    cargo_normalizado_dir = Path.cwd() / "data" / "processed" / 'cargo_normalizado'
    parquets_ano          = sorted(ano_dir.glob('*.parquet'))


    @st.cache_data
    def load_data():
        dataframes = [pd.read_parquet(in_file) for in_file in parquets_ano]
        return  pd.concat(dataframes, ignore_index=False)

    # Carga inicial obrigatória
    df = load_data()


    def dataset_multiselector(log=False):
        lista_identificadores = list()
        def func(value=[], reset=False):
            nonlocal lista_identificadores
            if reset:            
                lista_identificadores.clear()
                if log:
                    print(f'{"reset":><10}{log:>^20}-seq:{st.session_state.contador():0>5}: {len(lista_identificadores):0>4}')
                return lista_identificadores.copy()
            if isinstance(value, List):
                lista_identificadores += list(value)
            else:
                lista_identificadores += [value]

            lista_identificadores = list(set(lista_identificadores))
            lista_identificadores = sorted(lista_identificadores)
            if log:
                if value:
                    print(f'{"set":><10}{log:>^20}-seq:{st.session_state.contador():0>5}: {len(lista_identificadores):0>4}')
                else:
                    print(f'{"get":><10}{log:>^20}-seq:{st.session_state.contador():0>5}: {len(lista_identificadores):0>4}')
            return lista_identificadores.copy()
        return func


    def contador(inicio=0, passo=1):
        cont = inicio
        def func(reset=None, end=None):
            nonlocal cont, passo
            if end:
                print()
                return
            if reset:
                cont = 0
                return cont
            cont += passo
            return cont
        return func


    def fig_customize_marker(fig, dataframe, xaxis_values):
        idx_matriculas_selecionadas = [dataframe.loc[dataframe['matricula'] == x].index for x in xaxis_values]
        fig.update_traces(
            marker=dict(size=[14 if i in idx_matriculas_selecionadas else 10 for i in range(len(dataframe))],
                        color=["yellow" if i in idx_matriculas_selecionadas else 'rgba(135, 206, 250, 0.5)' for i in range(len(dataframe))],
                        symbol=["diamond-dot" if i in [idx_matriculas_selecionadas] else 'circle' for i in range(len(dataframe))],
                        line=dict(
                            color=["black" if i in idx_matriculas_selecionadas else "rgba(75,0,130, 0.7)" for i in range(len(dataframe))],
                            width=[2 if i in idx_matriculas_selecionadas else 2 for i in range(len(dataframe))],
                        )
        ))


    def fig_customize_marker_multiplos_cargos(fig, dataframe: pd.DataFrame, xaxis_values):
        idx_matriculas_selecionadas = [dataframe.loc[dataframe['matricula'] == x].index for x in xaxis_values]
        fig.update_traces(
            marker=dict(size=[14 if i in idx_matriculas_selecionadas else 10 for i in range(len(dataframe))],
                        # color=["yellow" if i in idx_matriculas_selecionadas else 'rgba(135, 206, 250, 0.5)' for i in range(len(dataframe))],
                        symbol=["diamond-dot" if i in [idx_matriculas_selecionadas] else 'circle' for i in range(len(dataframe))],
                        line=dict(
                            color=["black" if i in idx_matriculas_selecionadas else "rgba(75,0,130, 0.7)" for i in range(len(dataframe))],
                            width=[2 if i in idx_matriculas_selecionadas else 2 for i in range(len(dataframe))],
                        )
        ))


    def get_maiores_pagamentos_matriculas(dataframe, col, n=10):
        idx_maiores = dataframe.groupby('cargo_normalizado')[col].idxmax()
        return dataframe.loc[idx_maiores, col]


    def formata_label_ano(opcao):
        return opcao[-2:]


    ###################################################################################
    ### VARIAVEIS DE SESSAO
    if 'set_and_get_matriculas' not in st.session_state:
        st.session_state.set_and_get_matriculas = dataset_multiselector()

    if 'flag_modo_selecao_matricula_cargo' not in st.session_state:
        st.session_state.flag_modo_selecao_matricula_cargo = False

    if 'flag_modo_selecao_matricula_multiplos_cargos' not in st.session_state:
        st.session_state.flag_modo_selecao_matricula_multiplos_cargos = False

    if 'flag_cargos_default_top_15' not in st.session_state:
        st.session_state.flag_cargos_default_top_15 = False

    if 'get_and_set_ultimos_cargos_selecionados' not in st.session_state:
        st.session_state.get_and_set_ultimos_cargos_selecionados = dataset_multiselector()

    if 'contador' not in st.session_state:
        st.session_state.contador = contador()

    if 'flag_cargos_field_on_change' not in st.session_state:
        st.session_state.flag_cargos_field_on_change = False

    if 'cbox_matricula' not in st.session_state:
        st.session_state.cbox_matricula = True

    if 'labels_matricula_nome_cargo' not in st.session_state:
        filtro_duplicados = df.duplicated(subset=['matricula'])
        df_nome_matricula = (df[~filtro_duplicados][['matricula', 'nome', 'cargo']]
                            .sort_values('matricula').copy())
        st.session_state.labels_matricula_nome_cargo = {str(m) :f"{m} | {n} | {c}"
                                                        for n, m, c in zip(df_nome_matricula['nome'],
                                                                        df_nome_matricula['matricula'],
                                                                        df_nome_matricula['cargo'])}

    if 'alterna_multselect_matriculas' not in st.session_state:
        st.session_state.alterna_multselect_matriculas = False

    if 'alterna_multselect_cargos' not in st.session_state:
        st.session_state.alterna_multselect_cargos = False

    if 'lista_matriculas_add' not in st.session_state:
        st.session_state.lista_matriculas_add = []

    if 'txt_matriculas_add' not in st.session_state:
        st.session_state.txt_matriculas_add = ''

    if 'info_base_app' not in st.session_state:
        ANOS                      = list(df['ano'].sort_values().unique())
        PRIMEIRO_ANO              = int(min(ANOS))
        ULTIMO_ANO                = int(max(ANOS))
        QTDE_TODOS_CARGOS         = len(df['cargo_normalizado'].sort_values().unique())
        ULTIMO_MES_DERRADEIRO_ANO = df[df['ano'] == str(ULTIMO_ANO)]['mes'].unique()[-1]
        LISTA_TODAS_MATRICULAS    = list(df['matricula'].unique())
        LISTA_NOME_TODOS_CARGOS   = list(df['cargo_normalizado'].sort_values().unique())
        MESES                     = df['mes'].unique()
        QTDE_COMPETENCIAS         = df['comp'].unique()
        
        st.session_state.info_base_app = {
            'ANOS'                      : ANOS,
            'PRIMEIRO_ANO'              : PRIMEIRO_ANO,
            'ULTIMO_ANO'                : ULTIMO_ANO,
            'QTDE_TODOS_CARGOS'         : QTDE_TODOS_CARGOS,
            'ULTIMO_MES_DERRADEIRO_ANO' : ULTIMO_MES_DERRADEIRO_ANO,
            'LISTA_TODAS_MATRICULAS'    : LISTA_TODAS_MATRICULAS,
            'LISTA_NOME_TODOS_CARGOS'   : LISTA_NOME_TODOS_CARGOS,
            'MESES'                     : MESES,
            'QTDE_COMPETENCIAS'         : QTDE_COMPETENCIAS,
        }


    ANOS                      = st.session_state.info_base_app.get('ANOS')
    PRIMEIRO_ANO              = st.session_state.info_base_app.get('PRIMEIRO_ANO')
    ULTIMO_ANO                = st.session_state.info_base_app.get('ULTIMO_ANO')
    QTDE_TODOS_CARGOS         = st.session_state.info_base_app.get('QTDE_TODOS_CARGOS')
    ULTIMO_MES_DERRADEIRO_ANO = st.session_state.info_base_app.get('ULTIMO_MES_DERRADEIRO_ANO')
    LISTA_TODAS_MATRICULAS    = st.session_state.info_base_app.get('LISTA_TODAS_MATRICULAS')
    LISTA_NOME_TODOS_CARGOS   = st.session_state.info_base_app.get('LISTA_NOME_TODOS_CARGOS')
    MESES                     = st.session_state.info_base_app.get('MESES')
    MESES_STR                 = ['JAN', 'FEV', 'MAR', 'ABR', 'MAI', 'JUN', 'JUL', 'AGO', 
                                'SET', 'OUT', 'NOV', 'DEZ']
    QTDE_COMPETENCIAS       = st.session_state.info_base_app.get('QTDE_COMPETENCIAS')



    ###################################################################################
    st.sidebar.title('**PAINEL**')
    ###################################################################################
    ## PERIODO ANO
    with st.sidebar.expander('**PERÍODO - ANOS**', expanded=True):
        ano_inicial, ano_final = PRIMEIRO_ANO, ULTIMO_ANO
        radio_choice_ano = st.radio('Como deseja analisar os dados?',
                        ('Por período', 'Ano a ano'))

        todos_anos = False
        if f'POR PERÍODO' in radio_choice_ano.upper():
            ano = ''
            todos_anos = st.checkbox('Todos os anos', value=True)
            if todos_anos:
                ano = ULTIMO_ANO
            else:
                choice_anos = st.select_slider('Anos:', options=ANOS, value=(ANOS[-4 ], ANOS[-1]), format_func=formata_label_ano)
                ano_inicial, ano = int(choice_anos[0]), int(choice_anos[-1])

        else:
            ano_inicial = ano = int(st.selectbox('Selecione o ano:', 
                                                ANOS, 
                                                index=len(ANOS)-1))

        anos = [str(a) for a in range(ano_inicial, ano + 1)]

        # Verfica se nas outras opções foram selecionados todos os anos
        todos_anos = True if len(anos) == len(ANOS) else False

    st.sidebar.markdown(f'Período selecionado {len(anos)} ano(s)')


    st.sidebar.divider()
    ###################################################################################
    ## PERIODO MESES
    with st.sidebar.expander('**PERÍODO - MESES**', expanded=True):
        meses = MESES
        lista_meses = list(sorted(df[df['ano'].isin(anos)]['mes'].unique()))
        radio_choice_mes = st.radio('Quais meses?',(f"Todos os meses", 'Por seleção', 'Mês a mês'))
        if 'seleção'.upper() in radio_choice_mes.upper():
            meses = lista_meses
            lista_meses = [f'{m}-{MESES_STR[int(m)-1]}' for m in lista_meses]
            meses = st.multiselect('Selecione o(s) mês(es):', lista_meses, lista_meses[-1])
            if meses:
                meses = [m.split('-')[0] for m in meses]
            else:
                st.error('Selecione no mínimo 1 mês para que sejam '
                                    'apresentados resultados.', icon="🚨")

        if 'Mês a mês' in radio_choice_mes:
            meses = st.selectbox('Selecione o mês:', lista_meses, index=lista_meses.index(lista_meses[-1]))
            meses = [meses.split('-')[0]]

    st.sidebar.markdown(f'Período selecionado {len(meses)} mês(es)')

    st.sidebar.divider()


    # st.session_state.contador(end=True)
    ###################################################################################
    ## CARGOS
    flag_aviso_para_ativar_todas_matriculas = False
    is_1ano_1mes_selecionado =  len(anos) == 1 == len(meses)

    #################CONFIG_CARGOS#############################
    placeholder_checkbox_todos_cargos      = st.sidebar.empty()
    placeholder_slider_qtde_top_pagamentos = st.sidebar.empty()
    placeholder_btn_top_pagamentos         = st.sidebar.empty()
    placeholder_btn_reset_cargos           = st.sidebar.empty()
    placeholder_expander_cargos            = st.sidebar.empty()
    placeholder_label_cargos_selecionados  = st.sidebar.empty()
    #################CONFIG_CARGOS#############################

    todos_cargos = placeholder_checkbox_todos_cargos.checkbox('Todos os cargos', value=True)
    cargos = LISTA_NOME_TODOS_CARGOS

    qtde_cargos_top_pag = 5
    limite_max_top_pagamentos = QTDE_TODOS_CARGOS//3
    if not todos_cargos:
        if is_1ano_1mes_selecionado:
            qtde_cargos_top_pag = placeholder_slider_qtde_top_pagamentos.slider('Qtde. de cargos top pagamentos:', 5, limite_max_top_pagamentos)
            btn_top15_pagamentos =  placeholder_btn_top_pagamentos.button(
                f'Top {qtde_cargos_top_pag} - maiores pagamentos', 
                use_container_width=True,
                type='primary', 
                disabled= not is_1ano_1mes_selecionado, 
                # help='Selecione apenas 1 ano e 1 mês para ativar',
            )
        else:
            btn_top15_pagamentos =  placeholder_btn_top_pagamentos.button(
                f'Top {qtde_cargos_top_pag} - maiores pagamentos', 
                use_container_width=True,
                type='primary', 
                disabled= not is_1ano_1mes_selecionado, 
                help='Selecione apenas 1 ano e 1 mês para ativar',
            )


        with placeholder_expander_cargos.expander('**CARGOS**', expanded=True):
            placeholder_campo_cargos = st.empty()
            placeholder_aviso_cargos = st.empty()
        
        btn_reset_cargos_selecionados = placeholder_btn_reset_cargos.button('Reset Cargos Selecionados', 
                                                        use_container_width=True,
                                                        disabled=todos_cargos,
                                                        type='primary')
        if btn_reset_cargos_selecionados:
            st.session_state.get_and_set_ultimos_cargos_selecionados(reset=True)
    else:
        btn_top15_pagamentos = False
        btn_reset_cargos_selecionados = False


    def on_change_cargos():
        st.session_state.flag_cargos_field_on_change = True


    def componente_selecao_cargos(*, cargos_selecionados):
        st.session_state.get_and_set_ultimos_cargos_selecionados(reset=True)        
        result_selecao = placeholder_campo_cargos.multiselect('Selecione o(s) Cargo(s):', 
                                                            LISTA_NOME_TODOS_CARGOS, 
                                                            default=cargos_selecionados, 
                                                            on_change=on_change_cargos)
        return  st.session_state.get_and_set_ultimos_cargos_selecionados(result_selecao)


    if btn_top15_pagamentos:
        if todos_cargos:
            st.sidebar.error('Você precisa desmarcar a caixa **Todos Cargos**.', icon="🚨")
        else:
            st.session_state.flag_cargos_default_top_15 = True

    # Inicio do fluxo para adição ou remoção dos cargos
    if not todos_cargos:

        cargos = st.session_state.get_and_set_ultimos_cargos_selecionados()   
        
        cargos_matriculas_selecionadas = list(df[df['matricula']
            .isin(st.session_state.set_and_get_matriculas())]['cargo_normalizado'].unique())
        
        # Verifica se todos os cargos estão adicionados no multiselec pela quantidade
        if (len(cargos) == QTDE_TODOS_CARGOS):
            st.session_state.get_and_set_ultimos_cargos_selecionados(reset=True)
            cargos = []

        if not btn_reset_cargos_selecionados:
            cargos = st.session_state.get_and_set_ultimos_cargos_selecionados(cargos_matriculas_selecionadas)

        if st.session_state.flag_cargos_default_top_15:
            st.session_state.flag_cargos_default_top_15 = False        
            top_pagamento_cargos_matriculas = (df[df['ano'].isin(anos) & df['mes'].isin(meses)]
                                            .groupby('cargo_normalizado')
                                            .apply(get_maiores_pagamentos_matriculas, 'valor_bruto'))
            
            top_matriculas = list(df[df['ano'].isin(anos) & df['mes'].isin(meses)]
                                .loc[top_pagamento_cargos_matriculas.sort_values(ascending=False)
                                    .nlargest(qtde_cargos_top_pag).index.get_level_values(1).tolist()]['matricula'])
            top_cargos = list(df[df['ano'].isin(anos) & df['mes'].isin(meses)]
                            .loc[top_pagamento_cargos_matriculas.sort_values(ascending=False)
                                .nlargest(qtde_cargos_top_pag).index.get_level_values(1).tolist()]['cargo_normalizado'])

            cargos = componente_selecao_cargos(cargos_selecionados=st.session_state.get_and_set_ultimos_cargos_selecionados(top_cargos))
            st.session_state.set_and_get_matriculas(list(top_matriculas))
            # print(f'>>>>>>>>>({2:.>20})>>>>>>>>>', st.session_state.contador(), f'cargos: {len(cargos)}')
        else:
            cargos = componente_selecao_cargos(cargos_selecionados=cargos)
            # print(f'>>>>>>>>>({3:.>20})>>>>>>>>>', st.session_state.contador(), f'cargos: {len(cargos)}')

        if len(cargos) < 1:
            st.session_state.set_and_get_matriculas(reset=True)
            placeholder_aviso_cargos.error('Selecione no mínimo 1 cargo para que sejam apresentados resultados.', icon="🚨")
        else:
            flag_aviso_para_ativar_todas_matriculas = True

        if st.session_state.flag_cargos_field_on_change:
            st.session_state.flag_cargos_field_on_change = False
            # print('>>>>>>>>>>>>re_run>>>>>>>>>>>')
            st.experimental_rerun()

        # Recupera uma lista dos cargos que foram removidos da selecao de matriculas memorizadas
        cargos_non_selecionado = list()
        for cargo in cargos_matriculas_selecionadas:
            if cargo not in cargos:
                cargos_non_selecionado.append(cargo)

        if cargos_non_selecionado:
            # Recupera uma lista das matriculas memorizadas de cargos que forma removidos da selecao
            matriculas_fora_selecao = []
            for cargo in cargos_non_selecionado:
                matriculas_fora_selecao += list(df[df['cargo_normalizado'] == cargo]['matricula'])

            # Cria uma nova lista de matriculas memorizadas que ainda tem os seus respectivos cargos selecionados
            novo_cache_matriculas = []
            for matricula in st.session_state.set_and_get_matriculas():
                if matricula not in matriculas_fora_selecao:
                    novo_cache_matriculas.append(matricula)
            st.session_state.set_and_get_matriculas(reset=True)
            # Adiciona o nova lista de matriculas memorizadas
            st.session_state.set_and_get_matriculas(novo_cache_matriculas, )


    # # Adiciona a ultima selecao de cargos no cache
    st.session_state.get_and_set_ultimos_cargos_selecionados(reset=True)
    st.session_state.get_and_set_ultimos_cargos_selecionados(cargos)


    placeholder_label_cargos_selecionados.markdown(f'{len(cargos)} cargos selecionados')


    st.sidebar.divider()

    # st.session_state.contador(end=True)
    ###################################################################################
    # Efetua a cópia do dataframe e realiza o primeiro filtro de cargos
    df_result = df.copy()
    df_result = df_result[df_result['cargo_normalizado'].isin(cargos)
                        & df_result['ano'].isin(anos)
                        & df_result['mes'].isin(meses)]
    ###################################################################################

    # st.session_state.contador(end=True)
    ###################################################################################
    ## MATRICULAS
    # lista_memorizada = st.session_state.set_and_get_matriculas()
    # matriculas = lista_memorizada if lista_memorizada \
    #                               else df_result[df_result['ano'].isin(anos)
    #                                     & df_result['mes'].isin(meses)]['matricula'].unique()
    matriculas = df_result[df_result['ano'].isin(anos)
                                        & df_result['mes'].isin(meses)]['matricula'].unique()
                            

    #################CONFIG_MATRICULAS########################
    placeholder_todas_matriculas          = st.sidebar.empty()
    placeholder_multselec_matriculas       = st.sidebar.empty()
    placeholder_btn_memo_matriculas       = st.sidebar.empty()
    placeholder_btn_reset_memo_matriculas = st.sidebar.empty()
    placeholder_matriculas_selecionadas   = st.sidebar.empty()
    placeholder_matriculas_memorizadas    = st.sidebar.empty()
    #################CONFIG_MATRICULAS########################

    # Alterado a manutencao do estado de checkbox todas as matriculas devido a limitação do uso 
    # do objeto empty que sempre cria um novo espaço com um novo checkbox alterando o ultimo 
    # estado do componente pelo argumento default setado no parametro value
    def on_change_todas_matriculas():
        st.session_state.cbox_matricula = not st.session_state.cbox_matricula

    todas_matriculas = placeholder_todas_matriculas.checkbox('Todas as matrículas', 
                                                            value=st.session_state.cbox_matricula, 
                                                            on_change=on_change_todas_matriculas)



    if st.session_state.set_and_get_matriculas():
        if placeholder_btn_reset_memo_matriculas.button('Reset Matrculas Memorizadas',type='secondary', use_container_width=True):
            st.session_state.set_and_get_matriculas(reset=True)
            st.experimental_rerun()

    if not todas_matriculas:
        with placeholder_multselec_matriculas.expander('**MATRÍCULAS**', expanded=True):
            placeholder_multiselect_matricula = st.empty()
            # btn_add_lista_matriculas = st.button('Adicionar lista de matrículas', use_container_width=True)    
            placeholder_text_lista_matricula = st.empty()    
            placeholder_matriculas_alert = st.empty()

        matriculas = []
        
        filtro_duplicados = df_result.duplicated(subset=['matricula'])
        df_matricula = (df_result[~filtro_duplicados]['matricula'].sort_values().copy())

        lista_nomes_matriculas = [st.session_state.labels_matricula_nome_cargo.get(m) for m in df_matricula]
        
        lista_memorizada = st.session_state.set_and_get_matriculas()
        default_matriculas = [st.session_state.labels_matricula_nome_cargo.get(m) for m in lista_memorizada if m in list(df_result['matricula'])]
        default_matriculas += st.session_state.lista_matriculas_add


        # if btn_add_lista_matriculas:
        #     st.session_state.txt_matriculas_add = placeholder_text_lista_matricula.text_area('Insirá matrículas separadas por vírgula ou espaço', 
        #                                                      placeholder='Exemplo: 00123, 00285, 00111')
        # else:
        
        if st.session_state.alterna_multselect_matriculas:
            matriculas = placeholder_multiselect_matricula.multiselect('Selecione a(s) matricula(s):', lista_nomes_matriculas,
                                        default=default_matriculas, key='matric1')
        else:
            matriculas = placeholder_multiselect_matricula.multiselect('Selecione a(s) matricula(s):', lista_nomes_matriculas,
                                        default=default_matriculas, key='matric2')
        
        if matriculas:
            matriculas = [m.split(' | ')[0] for m in matriculas]

        
        btn_memo_matriculas =  placeholder_btn_memo_matriculas.button(
            f'Memorizar matrículas selecionadas', 
            type='primary', use_container_width=True,
            disabled= todas_matriculas or not matriculas
            or (len(matriculas) == len(st.session_state.set_and_get_matriculas())
                and not set(matriculas) - set(st.session_state.set_and_get_matriculas()))
        )

        if btn_memo_matriculas:
            st.session_state.set_and_get_matriculas(matriculas)
            st.session_state.alterna_multselect_matriculas = not st.session_state.alterna_multselect_matriculas
            st.experimental_rerun()
        
        if cargos:    
            if not matriculas:
                placeholder_matriculas_alert.error('Selecione no mínimo 1 matrícula para que sejam '
                                    'apresentados resultados.', icon="🚨")
                if flag_aviso_para_ativar_todas_matriculas:
                    flag_aviso_para_ativar_todas_matriculas = False
                    placeholder_matriculas_alert.error('Selecione alguma ou todas as matrículas para que sejam apresentados gráficos.', icon="🚨")
        else:
            placeholder_matriculas_alert.error('Selecione no mínimo 1 cargo para exibir as matrículas', icon="🚨")


    st.sidebar.divider()

    ###################################################################################
    qtde_cargos_normalizados_filtrados = len(df_result['cargo_normalizado'].unique())

    # st.session_state.contador(end=True)
    ###################################################################################
    ## Aplica fitros de ano, mes e matriculas selecionados
    df_result = df_result[df_result['matricula'].isin(matriculas)]

    ###################################################################################
    ## Graficos
    ### Tabela folha de pagamento por ano e por matricula
    def get_fig_line_valor_bruto_anual(dataframe: pd.DataFrame):
        valor_bruto_anual = dataframe.groupby('ano')[['valor_bruto']].sum().reset_index()
        valor_bruto_anual['Tipo Pagamento'] = 'Bruto'

        fig_line_valor_bruto_anual = px.line(valor_bruto_anual,
                                            x='ano',
                                            y='valor_bruto',
                                            markers=True,
                                            range_y=(0, valor_bruto_anual.max()),
                                            color='Tipo Pagamento',
                                            line_dash='Tipo Pagamento',
                                            title='Valor Total de Pagamento Anual')

        fig_line_valor_bruto_anual.update_layout(yaxis_title='Pagamento',
                                                xaxis_title='Ano')
        return fig_line_valor_bruto_anual


    ### Tabela folha de pagamento por ano e por matricula
    def get_fig_bar_valor_bruto_anual(dataframe: pd.DataFrame):
        valor_bruto_anual = dataframe.groupby('ano')[['valor_bruto']].sum().reset_index()
        valor_bruto_anual['Tipo Pagamento'] = 'Bruto'
        fig_bar_valor_bruto_anual = px.bar(valor_bruto_anual,
                                    x='ano',
                                    y='valor_bruto',
                                    text_auto=True,
                                    title='Valor Total de Pagamento Anual')

        fig_bar_valor_bruto_anual.update_layout(yaxis_title='Pagamento',
                                            xaxis_title='Ano')
        return fig_bar_valor_bruto_anual


    def get_fig_qtde_matriculas_mensal(dataframe: pd.DataFrame):
        filtro_comp_matricula_duplicado = dataframe.duplicated(subset=['comp', 'matricula'])
        qtde_matriculas_mensal = dataframe[~filtro_comp_matricula_duplicado].groupby(['comp', ])[['matricula']].count().reset_index()
        qtde_matriculas_mensal['Tipo'] = 'Matriculas'

        fig_qtde_matriculas_mensal = px.line(qtde_matriculas_mensal,
                                    x='comp',
                                    y='matricula',
                                    markers=True,
                                    range_y=(0, qtde_matriculas_mensal.max()),
                                    color='Tipo',
                                    line_dash='Tipo',
                                    title='Qtde Total de Matriculas Mensal')

        fig_qtde_matriculas_mensal.update_layout(yaxis_title='Qtde Matricula',
                                                xaxis_title='Competencia')
        return fig_qtde_matriculas_mensal


    ### Tabela folha de pagamento mensal
    def get_fig_valor_bruto_mensal(dataframe: pd.DataFrame):
        valor_bruto_mensal = dataframe.groupby(['comp'])[['valor_bruto']].sum().reset_index()
        valor_bruto_mensal['Tipo Pagamento'] = 'Bruto'
        fig_valor_bruto_mensal = px.line(valor_bruto_mensal,
                                    x='comp',
                                    y='valor_bruto',
                                    markers=True,
                                    range_y=(0, valor_bruto_mensal.max()),
                                    color='Tipo Pagamento',
                                    line_dash='Tipo Pagamento',
                                    title='Valor Total de Pagamento Mensal')

        fig_valor_bruto_mensal.update_layout(yaxis_title='Pagamento',
                                            xaxis_title='Mês')
        return fig_valor_bruto_mensal


    ### Grafico folha de pagamento mensal por nome
    def get_fig_valor_bruto_mensal_por_nome(dataframe: pd.DataFrame):
        df_fig = load_data()
        df_fig = df_fig[df_fig['matricula'].isin(dataframe['matricula'])].loc[:, ['matricula', 'nome', 'cargo', 'comp', 'valor_bruto' ]]

        fig_valor_bruto_mensal_por_nome = px.line(df_fig,
                                            x='comp',
                                            y='valor_bruto',
                                            markers=True,
                                            range_y=(0, df_fig.max()),
                                            color='nome',
                                            #  line_dash='nome',
                                            labels={'matricula': 'RGF', 'valor_bruto': 'Pagamento'},
                                            hover_name='nome',
                                            hover_data=['cargo', 'matricula'],
                                            title=f'Valor pagamento mensal por nome desde {df["competencia"].unique()[0]}')

        fig_valor_bruto_mensal_por_nome.update_layout(yaxis_title='Pagamento',
                                                xaxis_title='Competência')

        fig_valor_bruto_mensal_por_nome.update_traces(
        hovertemplate=("<b>RGF: %{customdata[1]}</b><br>"
                    "Nome: %{hovertext}<br>"
                    "Cargo: %{customdata[0]}<br>"
                    "Competência: %{x}<br>"
                    "Pagamento: R$%{y:,.2f}"),
        )
        return fig_valor_bruto_mensal_por_nome


    ### Grafico folha de pagamento mensal por matricula
    def get_fig_valor_bruto_mensal_por_matricula(dataframe: pd.DataFrame):
        df_fig = load_data()
        df_fig = df_fig[df_fig['matricula'].isin(dataframe['matricula'])].loc[:, ['matricula', 'nome', 'cargo', 'comp', 'valor_bruto' ]]

        fig_valor_bruto_mensal_por_matricula = px.line(df_fig,
                                            x='comp',
                                            y='valor_bruto',
                                            markers=True,
                                            range_y=(0, df_fig.max()),
                                            color='matricula',
                                            #  line_dash='nome',
                                            labels={'matricula': 'RGF', 'valor_bruto': 'Pagamento'},
                                            hover_name='nome',
                                            hover_data=['cargo', 'matricula'],
                                            title=f'Valor pagamento mensal por matrícula desde {df["competencia"].unique()[0]}')

        fig_valor_bruto_mensal_por_matricula.update_layout(yaxis_title='Pagamento',
                                                xaxis_title='Competência')

        fig_valor_bruto_mensal_por_matricula.update_traces(
        hovertemplate=("<b>RGF: %{customdata[1]}</b><br>"
                    "Nome: %{hovertext}<br>"
                    "Cargo: %{customdata[0]}<br>"
                    "Competência: %{x}<br>"
                    "Pagamento: R$%{y:,.2f}"),
        )
        return fig_valor_bruto_mensal_por_matricula


    ### Grafico folha de pagamento mensal por nome a partir do dataframe resultado
    def get_fig_valor_bruto_mensal_por_nome_df_result(dataframe: pd.DataFrame):
        df_fig = dataframe
        fig_valor_bruto_mensal_por_matricula = px.line(df_fig,
                                            x='comp',
                                            y='valor_bruto',
                                            markers=True,
                                            range_y=(0, df_fig[['valor_bruto']].max()),                                        
                                            color='nome',
                                            #  line_dash='nome',
                                            labels={'matricula': 'RGF', 'valor_bruto': 'Pagamento'},
                                            hover_name='nome',
                                            hover_data=['cargo', 'matricula'],
                                            title='Valor pagamento mensal por nome')

        fig_valor_bruto_mensal_por_matricula.update_layout(yaxis_title='Pagamento',
                                                xaxis_title='Competência')

        fig_valor_bruto_mensal_por_matricula.update_traces(
        hovertemplate=("<b>RGF: %{customdata[1]}</b><br>"
                    "Nome: %{hovertext}<br>"
                    "Cargo: %{customdata[0]}<br>"
                    "Competência: %{x}<br>"
                    "Pagamento: R$%{y:,.2f}"),
        )
        return fig_valor_bruto_mensal_por_matricula


    ### Grafico folha de pagamento mensal por matricula a partir do dataframe resultado
    def get_fig_valor_bruto_mensal_por_matricula_df_result(dataframe: pd.DataFrame):
        df_fig = dataframe
        fig_valor_bruto_mensal_por_matricula = px.line(df_fig,
                                            x='comp',
                                            y='valor_bruto',
                                            markers=True,
                                            range_y=(0, df_fig[['valor_bruto']].max()),
                                            color='matricula',
                                            #  line_dash='nome',
                                            labels={'matricula': 'RGF', 'valor_bruto': 'Pagamento'},
                                            hover_name='nome',
                                            hover_data=['cargo', 'matricula'],
                                            title='Valor pagamento mensal por matrícula')

        fig_valor_bruto_mensal_por_matricula.update_layout(yaxis_title='Pagamento',
                                                xaxis_title='Competência')

        fig_valor_bruto_mensal_por_matricula.update_traces(
        hovertemplate=("<b>RGF: %{customdata[1]}</b><br>"
                    "Nome: %{hovertext}<br>"
                    "Cargo: %{customdata[0]}<br>"
                    "Competência: %{x}<br>"
                    "Pagamento: R$%{y:,.2f}"),
        )
        return fig_valor_bruto_mensal_por_matricula


    ### Tabela qtde top 10 maiores pagamentos por cargo
    def get_fig_total_pagamento_por_cargo(dataframe: pd.DataFrame):
        total_pagamento_por_cargo = (dataframe.groupby('cargo_normalizado')[['valor_bruto']]
                                    .sum()
                                    .reset_index()
                                    .sort_values('valor_bruto', ascending=False))
        fig_total_pagamento_por_cargo = px.bar(total_pagamento_por_cargo.head(10),
                                                x='valor_bruto',
                                                y='cargo_normalizado',
                                                text_auto=True,
                                                orientation='h',
                                                color='cargo_normalizado',
                                                labels={'cargo_normalizado': 'Cargos'},
                                                title='Top 10 Maiores Pagamentos por Cargo')
        fig_total_pagamento_por_cargo.update_layout(yaxis_title='',
                                                    yaxis=dict(showticklabels=False),
                                                    xaxis_title='Pagamento Valor Bruto')
        return fig_total_pagamento_por_cargo


    ### Tabela total de pagamento por cargo
    def get_fig_top10_media_pagamento_por_cargo(dataframe: pd.DataFrame):
        top10_media_pagamento_por_cargo = (dataframe.groupby('cargo_normalizado')[['valor_bruto']]
                                    .agg(['sum', 'mean'])
                                    .reset_index())
        top10_media_pagamento_por_cargo.columns = ['cargo', 'sum', 'mean']
        top10_media_pagamento_por_cargo = top10_media_pagamento_por_cargo.sort_values( 'mean', ascending=False).head(10)

        fig_top10_media_pagamento_por_cargo = px.bar(top10_media_pagamento_por_cargo,
                                                y='mean',
                                                x='cargo',
                                                text_auto=True,
                                                orientation='v',
                                                color='cargo',
                                                title='Top 10 Maiores Média de Pagamentos por Cargo no período selecionado')
        fig_top10_media_pagamento_por_cargo.update_layout(yaxis_title='',
                                                        xaxis_title='Total de Pagamentos',
                                                        xaxis=dict(showticklabels=False))
        return fig_top10_media_pagamento_por_cargo


    def get_fig_qtde_matriculas_mensal_cargo(dataframe: pd.DataFrame):
        filtro_comp_matricula_duplicado = dataframe.duplicated(subset=['comp', 'matricula'])
        qtde_matriculas_mensal_cargo = dataframe[~filtro_comp_matricula_duplicado].groupby(['comp', 'cargo_normalizado'])[['matricula']].count().reset_index()
        qtde_matriculas_mensal_cargo['Cargos'] = qtde_matriculas_mensal_cargo['cargo_normalizado']

        fig_qtde_matriculas_mensal_cargo = px.line(qtde_matriculas_mensal_cargo,
                                                x='comp',
                                                y='matricula',
                                                markers=True,
                                                range_y=(0, qtde_matriculas_mensal_cargo.max()),
                                                color='Cargos',
                                                line_dash='Cargos',
                                                title='Qtde Matriculas por Cargo no período selecionado')

        fig_qtde_matriculas_mensal_cargo.update_layout(yaxis_title='Qtde Matriculas',
                                                xaxis_title='Competencia')
        return fig_qtde_matriculas_mensal_cargo


    ### Tabela qtde top 10 maiores pagamentos por cargo
    def get_fig_qtde_matr_cargos_top10_maior_pag(dataframe: pd.DataFrame):
        total_pagamento_por_cargo = (dataframe.groupby('cargo_normalizado')[['valor_bruto']]
                                    .sum()
                                    .reset_index()
                                    .sort_values('valor_bruto', ascending=False))

        filtro_cargo_matricula_duplicado = dataframe.duplicated(subset=['cargo_normalizado', 'matricula'])
        cargos_top10_maior_pagamento = total_pagamento_por_cargo['cargo_normalizado'].head(10)
        qtde_matriculas_top10_maior_pag_cargo = (dataframe[~filtro_cargo_matricula_duplicado]
                                                .groupby(['cargo_normalizado', ])[['matricula']]
                                                .count().reset_index())
        qtde_matriculas_top10_maior_pag_cargo = (qtde_matriculas_top10_maior_pag_cargo[qtde_matriculas_top10_maior_pag_cargo['cargo_normalizado'].isin(cargos_top10_maior_pagamento)]
                                                ).sort_values('matricula', ascending=False)

        fig_qtde_matr_cargos_top10_maior_pag = px.bar(qtde_matriculas_top10_maior_pag_cargo,
                                                x='matricula',
                                                y='cargo_normalizado',
                                                text_auto=True,
                                                color='cargo_normalizado',
                                                orientation='h',
                                                labels={'cargo_normalizado': 'Cargos'},
                                                title='Qtde Matriculas dos Cargos Top 10 Maiores Pagamentos')

        fig_qtde_matr_cargos_top10_maior_pag.update_layout(yaxis_title='',
                                                        xaxis_title='Pagamento Valor Bruto',
                                                        yaxis=dict(showticklabels=False))
        return fig_qtde_matr_cargos_top10_maior_pag


    ##################################GRAFICO DE DISPERSAO APENAS UM CARGO##################################################
    def get_fig_valor_bruto_por_matricula(dataframe: pd.DataFrame):
        valor_bruto_por_matricula_mes = dataframe.copy()
        valor_bruto_por_matricula_mes['matric'] = valor_bruto_por_matricula_mes['matric'].astype('float64')
        valor_bruto_por_matricula_mes['valor_bruto'] = valor_bruto_por_matricula_mes['valor_bruto'].astype('float64')
        valor_bruto_por_matricula_mes = valor_bruto_por_matricula_mes.sort_values('matric').reset_index()
        # st.write(valor_bruto_por_matricula_mes)
        fig_valor_bruto_por_matricula = px.scatter(valor_bruto_por_matricula_mes,
                                                x="matric",
                                                y="valor_bruto",
                                                trendline='ols',
                                                trendline_color_override="red",
                                                labels={'matric': 'RGF', 'valor_bruto': 'Pagamento'},
                                                hover_name='nome',
                                                hover_data=['cargo'],
                                                title=f'Pagamento Valor Bruto por Matricula no mês - {MESES_STR[int(meses[-1])-1]}/{ano_final} ({len(matriculas)} matrículas)')
        range_valores_bruto = []
        range_matriculas = []
        if not valor_bruto_por_matricula_mes.empty:
            valor_maximo = int(max(valor_bruto_por_matricula_mes['valor_bruto'])) + 1000
            if valor_maximo <= 6000:
                passo_valor = 500
            elif valor_maximo <= 10000:
                passo_valor = 2000
            elif valor_maximo <= 20000:
                passo_valor = 3000
            else:
                passo_valor = 4000
            range_valores_bruto = [v for v in range(1000, valor_maximo, passo_valor)]


            maior_matricula = int(max(valor_bruto_por_matricula_mes['matric'])) + 1500
            if maior_matricula <= 6000:
                passo_matricula = 500
            elif maior_matricula <= 11000:
                passo_matricula = 2000
            elif maior_matricula <= 21000:
                passo_matricula = 3000
            elif maior_matricula <= 30000:
                passo_matricula = 4000
            else:
                passo_matricula = 10000

            range_matriculas = [v for v in range(0, maior_matricula + 1000, passo_matricula)]

        fig_valor_bruto_por_matricula.update_layout(xaxis_title='Matrícula',
                                                    xaxis=dict(
                                                        tickvals=range_matriculas,
                                                        ticktext=[f'{v}' for v in range_matriculas],
                                                        showticklabels=True,
                                                        tickangle=45,
                                                    ),
                                                    yaxis=dict(
                                                        tickvals=range_valores_bruto,
                                                        ticktext=[formata_valores(v, 'R$') for v in range_valores_bruto],
                                                        showticklabels=True,
                                                        tickangle=-45,
                                                    ),
                                                    hoverlabel=dict(
                                                        bgcolor="white",
                                                        font_size=12,
                                                        font_family="Rockwell"
                                                    ),
                                                    clickmode='event+select',
                                                    font=dict(
                                                        family="Arial",
                                                        size=14,
                                                        color="RebeccaPurple"
                                                    ),)

        fig_valor_bruto_por_matricula.update_traces(
            hovertemplate=("<b>RGF: %{x:5.0f}</b><br>"
                        "Nome: %{hovertext}<br>"
                        "Cago: %{customdata[0]}<br>"
                        "Pagamento: R$%{y:,.2f}"),
            marker=dict(
                    color='rgba(135, 206, 250, 0.5)',
                    size=10,
                    symbol='circle',
                    line=dict(
                        color="rgba(75,0,130, 0.7)",
                        width=2
                    )
                ),
        )
        return fig_valor_bruto_por_matricula

    ##################################GRAFICO DE DISPERSAO VARIOS CARGOS##################################################
    def get_fig_pg_bruto_por_matricula_mes_varios_cargos(dataframe: pd.DataFrame):
        pg_bruto_por_matricula_mes_varios_cargos = dataframe.copy()
        pg_bruto_por_matricula_mes_varios_cargos['matric'] = pg_bruto_por_matricula_mes_varios_cargos['matric'].astype('float64')
        pg_bruto_por_matricula_mes_varios_cargos['valor_bruto'] = pg_bruto_por_matricula_mes_varios_cargos['valor_bruto'].astype('float64')
        pg_bruto_por_matricula_mes_varios_cargos = pg_bruto_por_matricula_mes_varios_cargos.sort_values('matric').reset_index()
        # st.write(pg_bruto_por_matricula_mes_varios_cargos)
        fig_pg_bruto_por_matricula_mes_varios_cargos = px.scatter(pg_bruto_por_matricula_mes_varios_cargos,
                                                x="matric",
                                                y="valor_bruto",
                                                #    trendline='ols',
                                                #    trendline_color_override="red",
                                                labels={'matric': 'RGF', 'valor_bruto': 'Pagamento'},
                                                hover_name='nome',
                                                hover_data=['cargo'],
                                                color='cargo_normalizado',
                                                title=f'Pagamento valor bruto matrícula/mês vários cargos - {MESES_STR[int(meses[-1])-1]} ({qtde_cargos_normalizados_filtrados} cargos)')
        range_valores_bruto = []
        range_matriculas = []

        if not pg_bruto_por_matricula_mes_varios_cargos.empty:
            valor_maximo = int(max(pg_bruto_por_matricula_mes_varios_cargos['valor_bruto'])) + 1000
            if valor_maximo <= 6000:
                passo_valor = 500
            elif valor_maximo <= 10000:
                passo_valor = 2000
            elif valor_maximo <= 20000:
                passo_valor = 3000
            elif valor_maximo <= 30000:
                passo_valor = 5000
            else:
                passo_valor = 10000
            range_valores_bruto = [v for v in range(passo_valor, valor_maximo + passo_valor, passo_valor)]


            maior_matricula = int(max(pg_bruto_por_matricula_mes_varios_cargos['matric'])) + 1500
            if maior_matricula <= 6000:
                passo_matricula = 500

            elif maior_matricula <= 11000:
                passo_matricula = 2000

            elif maior_matricula <= 21000:
                passo_matricula = 3000
            
            elif maior_matricula <= 30000:
                passo_matricula = 4000
            else:
                passo_matricula = 10000
            

            range_matriculas = [v for v in range(0, maior_matricula + 1000, passo_matricula)]

        fig_pg_bruto_por_matricula_mes_varios_cargos.update_layout(xaxis_title='Matrícula',
                                                                xaxis=dict(
                                                                    tickvals=range_matriculas,
                                                                    ticktext=[f'{v}' for v in range_matriculas],
                                                                    showticklabels=True,
                                                                    tickangle=45,
                                                                ),
                                                                yaxis=dict(
                                                                    tickvals=range_valores_bruto,
                                                                    ticktext=[formata_valores(v, 'R$') for v in range_valores_bruto],
                                                                    showticklabels=True,
                                                                    tickangle=-45,
                                                                ),
                                                                hoverlabel=dict(
                                                                    bgcolor="white",
                                                                    font_size=12,
                                                                    font_family="Rockwell"
                                                                ),
                                                                clickmode='event+select',
                                                                font=dict(
                                                                    family="Arial",
                                                                    size=14,
                                                                    color="RebeccaPurple"
                                                                ),)

        fig_pg_bruto_por_matricula_mes_varios_cargos.update_traces(hoverinfo='skip',
            hovertemplate=("<b>RGF: %{x:5.0f}</b><br>"
                        "Nome: %{hovertext}<br>"
                        "Cargo: %{customdata[0]}<br>"
                        "Pagamento: R$%{y:,.2f}"),
            # customdata=[pg_bruto_por_matricula_mes_varios_cargos['cargo_normalizado']],
            # showlegend=False,
            marker=dict(
                    # color='rgba(135, 206, 250, 0.5)',
                    size=10,
                    symbol='circle',
                    line=dict(
                        color="rgba(75,0,130, 0.8)",
                        width=2
                    )
                ),
        )
        
        return fig_pg_bruto_por_matricula_mes_varios_cargos

    ##########################BODY###################################
    ## Page Body
    # st.title('DASHBOARD FOLHA DE PAGAMENTO 💰')
    st.markdown(
        f"""
        <div style='text-align:center;'>
            <h1>FOLHA DE PAGAMENTO ITAQUÁ 💰</h1>
            <h3>Pagamentos desde {df['competencia'].unique()[0]}</h3>
            <p>Fonte: <a href="https://transparencia.itaquaquecetuba.sp.gov.br/tdaportalclient.aspx?418" target="blank">
                            Portal da Transparência (Recursos Humanos)</a>. Último acesso em: 31/08/2023
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.divider()


    if not df_result.empty:
        col1, col2, col3 = st.columns(3)
        with col1:
            qtde_pagamentos = df_result.shape[0]
            st.metric('Valor total de pagamentos',
                    formata_valores(df_result['valor_bruto'].sum(), 'R$'))
            st.metric('Média simples por pagamento',
                    formata_valores(df_result['valor_bruto']
                                    .sum()/qtde_pagamentos, 'R$'))

        with col2:
            qtde_anos = len(df_result['competencia'].unique())//12
            qtde_meses = len(df_result['competencia'].unique())%12
            st.metric('Quantidade de pagamentos', formata_valores(qtde_pagamentos))
            st.metric('Total competências', f"{qtde_anos} ano(s) {qtde_meses} mês(es)")

        with col3:
            qtde_matriculas = len(df_result['matricula'].unique())
            qtde_cargos = len(df_result['cargo'].unique())
            st.metric('Quantidade de matrículas', qtde_matriculas)
            st.metric(f'Cargos - período selecionado', qtde_cargos)
        style_metric_cards()

        st.divider()

        # Primeiro conjunto de visualizações
        if (radio_choice_ano == 'Ano a ano' or len(anos) == 1) and len(meses) > 1 :
            # print('>>>>>>>>>>>>>fig1')
            if len(matriculas) > 1:
                col1, col2 = st.columns(2)
                with col1:
                    st.plotly_chart(get_fig_valor_bruto_mensal(df_result), use_container_width=True)

                with col2:
                    st.plotly_chart(get_fig_qtde_matriculas_mensal(df_result), use_container_width=True)
            else:
                st.plotly_chart(get_fig_valor_bruto_mensal(df_result), use_container_width=True)

            if len(matriculas) <= limite_max_top_pagamentos:
                st.plotly_chart(get_fig_valor_bruto_mensal_por_nome_df_result(df_result), use_container_width=True)
                st.plotly_chart(get_fig_valor_bruto_mensal_por_matricula_df_result(df_result), use_container_width=True)

            if qtde_cargos_normalizados_filtrados > 1:
                col1, col2 = st.columns(2)
                with col1:
                    st.plotly_chart(get_fig_total_pagamento_por_cargo(df_result), use_container_width=True)
                with col2:
                    st.plotly_chart(get_fig_qtde_matr_cargos_top10_maior_pag(df_result), use_container_width=True)
                st.plotly_chart(get_fig_top10_media_pagamento_por_cargo(df_result), use_container_width=True)

            if 1 < qtde_cargos_normalizados_filtrados <= qtde_cargos_top_pag :
                st.plotly_chart(get_fig_qtde_matriculas_mensal_cargo(df_result), use_container_width=True)

            # TODO: fazer comparativo de totais por mês caso tenha mais de um rgf selecionado

        elif todos_anos:
            # print('>>>>>>>>>>>>>fig2')
            st.plotly_chart(get_fig_bar_valor_bruto_anual(df_result), use_container_width=True)
            st.plotly_chart(get_fig_valor_bruto_mensal(df_result), use_container_width=True)
            
            if len(matriculas) <= limite_max_top_pagamentos:
                st.plotly_chart(get_fig_valor_bruto_mensal_por_matricula_df_result(df_result), use_container_width=True)
                st.plotly_chart(get_fig_valor_bruto_mensal_por_nome_df_result(df_result), use_container_width=True)
            
            if len(matriculas) > 1:
                st.plotly_chart(get_fig_qtde_matriculas_mensal(df_result), use_container_width=True)

            if qtde_cargos_normalizados_filtrados > 1:
                col1, col2 = st.columns(2)
                with col1:
                    st.plotly_chart(get_fig_total_pagamento_por_cargo(df_result), use_container_width=True)
                with col2:
                    st.plotly_chart(get_fig_qtde_matr_cargos_top10_maior_pag(df_result), use_container_width=True)
                st.divider()

                st.plotly_chart(get_fig_top10_media_pagamento_por_cargo(df_result), use_container_width=True)

            if 1 < qtde_cargos_normalizados_filtrados <= qtde_cargos_top_pag:
                st.plotly_chart(get_fig_qtde_matriculas_mensal_cargo(df_result), use_container_width=True)

        elif len(anos) > 1:
            # print('>>>>>>>>>>>>>fig3')
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(get_fig_bar_valor_bruto_anual(df_result), use_container_width=True)
            with col2:
                st.plotly_chart(get_fig_valor_bruto_mensal(df_result), use_container_width=True)
            
            if len(matriculas) > 1:
                st.plotly_chart(get_fig_qtde_matriculas_mensal(df_result), use_container_width=True)
            
            if len(matriculas) <= limite_max_top_pagamentos:
                st.plotly_chart(get_fig_valor_bruto_mensal_por_nome_df_result(df_result), use_container_width=True)

            if 1 < qtde_cargos_normalizados_filtrados <= qtde_cargos_top_pag:
                st.plotly_chart(get_fig_qtde_matriculas_mensal_cargo(df_result), use_container_width=True)

            if qtde_cargos_normalizados_filtrados > 1:
                col1, col2 = st.columns(2)
                with col1:
                    st.plotly_chart(get_fig_total_pagamento_por_cargo(df_result), use_container_width=True)
                with col2:
                    st.plotly_chart(get_fig_qtde_matr_cargos_top10_maior_pag(df_result), use_container_width=True)
                st.plotly_chart(get_fig_top10_media_pagamento_por_cargo(df_result), use_container_width=True)


        elif qtde_cargos_normalizados_filtrados == 1 and len(matriculas) > 1:        # Plotar boxplot e scatter
            # print('>>>>>>>>>>>>>fig4')
            matricula_selecionada = []
            if st.session_state.flag_modo_selecao_matricula_cargo:
                # st.plotly_chart(get_fig_valor_bruto_por_matricula(df_result), use_container_width=True)
                st.info(':blue[Agora selecione as **matrículas** nos pontos do gráfico para maiores detalhes.]', icon='ℹ️')

                selected_points = plotly_events(get_fig_valor_bruto_por_matricula(df_result))

                if selected_points:
                    # selected_points
                    x = selected_points[0].get('x')
                    matricula_selecionada.append(f'{x:0>5}')
                    st.markdown(f':red[Última matrícula selecionada: **{matricula_selecionada[-1]}**]')

                col1, col2, *_ = st.columns(2)
                with col1:
                    voltar =  st.button('Voltar', type='primary', use_container_width=True)
                with col2:
                    reset = st.button('Reset', type='primary', use_container_width=True)

                if reset:
                    st.multiselect('Matrículas Selecionadas', LISTA_TODAS_MATRICULAS, disabled=True,
                                default=st.session_state.set_and_get_matriculas(reset=True))
                else:
                    st.multiselect('Matrículas Selecionadas', LISTA_TODAS_MATRICULAS, disabled=True,
                                default=st.session_state.set_and_get_matriculas(matricula_selecionada, ))

                if voltar:
                    st.session_state.flag_modo_selecao_matricula_cargo = not st.session_state.flag_modo_selecao_matricula_cargo
                    st.experimental_rerun()
            else:
                # TODO: Desligado a customizacao do marker para o scatter devido a complexidade adicionada para manter.
                # fig_customize_marker(get_fig_valor_bruto_por_matricula(df_result), valor_bruto_por_matricula_mes, st.session_state.set_and_get_matriculas())

                st.plotly_chart(get_fig_valor_bruto_por_matricula(df_result), use_container_width=True)
                col1, col2 = st.columns(2)
                with col1:
                    btn_seleciona_matriculas = st.button('Clique aqui e memorize as matrículas', type='primary', use_container_width=True)
                with col2:
                    btn_reset = st.button('Reset', type='primary', use_container_width=True)

                if btn_reset:
                    st.session_state.set_and_get_matriculas(reset=True)

                if btn_seleciona_matriculas:
                    st.session_state.flag_modo_selecao_matricula_cargo = not st.session_state.flag_modo_selecao_matricula_cargo
                    st.experimental_rerun()
                st.multiselect('Matrículas Selecionadas', LISTA_TODAS_MATRICULAS, disabled=True,
                                default=st.session_state.set_and_get_matriculas(matricula_selecionada, ))

            # TODO: implementar a plotagem dos gráficos boxplot para exibição de outliers

            # TODO: implementar a plotagem dos gráficos comparativos entre matriculas distintas
            if len(matriculas) <= limite_max_top_pagamentos:
                st.plotly_chart(get_fig_valor_bruto_mensal_por_nome(df_result), use_container_width=True)
                st.plotly_chart(get_fig_valor_bruto_mensal_por_matricula(df_result), use_container_width=True)


        elif qtde_cargos_normalizados_filtrados > 1 or st.session_state.set_and_get_matriculas():
            # print('>>>>>>>>>>>>>fig5')
            if 1 < qtde_cargos_normalizados_filtrados <= limite_max_top_pagamentos+10:
                matricula_selecionada = []
                if st.session_state.flag_modo_selecao_matricula_multiplos_cargos:
                    st.info(':blue[Agora selecione as **matrículas** nos pontos do gráfico para maiores detalhes.]', icon='ℹ️')
                    
                    # # TODO: implementar quando descobrir uma forma de marcar pontos do graficom com mais de um grupo de legenda
                    # fig_customize_marker_multiplos_cargos(get_fig_pg_bruto_por_matricula_mes_varios_cargos(df_result), pg_bruto_por_matricula_mes_varios_cargos, st.session_state.set_and_get_matriculas())

                    selected_points = plotly_events(get_fig_pg_bruto_por_matricula_mes_varios_cargos(df_result))

                    if selected_points:
                        # selected_points
                        x = selected_points[0].get('x')
                        matricula_selecionada.append(f'{x:0>5}')
                        st.markdown(f':red[Última matrícula selecionada: **{matricula_selecionada[-1]}**]')                    

                    col1, col2, *_ = st.columns(2)
                    with col1:
                        voltar =  st.button('Voltar', type='primary', use_container_width=True)
                    with col2:
                        reset = st.button('Reset', type='primary', use_container_width=True)

                    if reset:
                        st.multiselect('Matrículas Memorizadas', LISTA_TODAS_MATRICULAS, disabled=True,
                                    default=st.session_state.set_and_get_matriculas(reset=True))
                        st.experimental_rerun()
                    else:
                        st.multiselect('Matrículas Memorizadas', LISTA_TODAS_MATRICULAS, disabled=True,
                                    default=st.session_state.set_and_get_matriculas(matricula_selecionada, ))                    

                    if voltar:
                        st.session_state.flag_modo_selecao_matricula_multiplos_cargos = not st.session_state.flag_modo_selecao_matricula_multiplos_cargos
                        st.experimental_rerun()
                else:
                    # # TODO: implementar quando descobrir uma forma de marcar pontos do graficom com mais de um grupo de legenda
                    # fig_customize_marker_multiplos_cargos(get_fig_pg_bruto_por_matricula_mes_varios_cargos(df_result), pg_bruto_por_matricula_mes_varios_cargos, st.session_state.set_and_get_matriculas())

                    st.plotly_chart(get_fig_pg_bruto_por_matricula_mes_varios_cargos(df_result), use_container_width=True)

                    col1, col2 = st.columns(2)
                    with col1:
                        btn_seleciona_matriculas = st.button('Clique aqui e memorize as matrículas', type='primary', use_container_width=True)
                    with col2:
                        btn_reset = st.button('Reset', type='primary', use_container_width=True)

                    if btn_reset:
                        st.session_state.set_and_get_matriculas(reset=True)
                        st.experimental_rerun()

                    if btn_seleciona_matriculas:
                        st.session_state.flag_modo_selecao_matricula_multiplos_cargos = not st.session_state.flag_modo_selecao_matricula_multiplos_cargos
                        st.experimental_rerun()
                    st.multiselect('Matrículas Memorizadas', LISTA_TODAS_MATRICULAS, disabled=True,
                                    default=st.session_state.set_and_get_matriculas(matricula_selecionada, ))
                
            if len(matriculas) <= limite_max_top_pagamentos:
                st.plotly_chart(get_fig_valor_bruto_mensal_por_nome(df_result), use_container_width=True)
                st.plotly_chart(get_fig_valor_bruto_mensal_por_matricula(df_result), use_container_width=True)

            if todos_cargos and todas_matriculas:            
                col1, col2 = st.columns(2)
                with col1:
                    st.plotly_chart(get_fig_total_pagamento_por_cargo(df_result), use_container_width=True)
                with col2:
                    st.plotly_chart(get_fig_qtde_matr_cargos_top10_maior_pag(df_result), use_container_width=True)
                st.plotly_chart(get_fig_top10_media_pagamento_por_cargo(df_result), use_container_width=True)

        else:
            st.info(f"""ATENÇÃO! NÃO HÁ GRÁFICOS PARA APRESENTAR COM ESTA CONFIGURAÇÃO DE ANOS, MESES, CARGOS E MATRICULAS SELECIONADOS""", icon='ℹ️')


        if False:
            col1, col2 = st.columns(2)
            with col1:
                ...
            with col2:
                ...
    else:
        st.info(f"""ATENÇÃO! NÃO HÁ GRÁFICOS PARA APRESENTAR COM ESTA CONFIGURAÇÃO DE ANOS, MESES, CARGOS E MATRICULAS SELECIONADOS""", icon='ℹ️')


    placeholder_matriculas_selecionadas.markdown(f'Matrículas Selecionadas: ✅{len(matriculas):0>4}')
    placeholder_matriculas_memorizadas.markdown(f'Matrículas Memorizadas: 🧠{len(st.session_state.set_and_get_matriculas()):0>4}')

    # st.dataframe(df_result)

if __name__ == '__main__':
    authentication()
