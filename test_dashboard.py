import plotly.express as px
import pandas as pd
import streamlit as st

# Dados do exemplo
df = px.data.iris()

# Identificar o índice do ponto (7.9, 3.8)
indice_ponto_alterado = df[(df["sepal_length"] == 7.9) & (df["sepal_width"] == 3.8)].index

# Modificar o estilo do ponto (7.9, 3.8) diretamente no DataFrame
df[ 'custom_symbol'] = 'circle'
df[ 'custom_size'] = 10
df.loc[indice_ponto_alterado, 'custom_symbol'] = 'diamond-dot'
df.loc[indice_ponto_alterado, 'custom_size'] = 18

# df

# Plotar o gráfico de dispersão com todos os pontos usando o Plotly Express
fig = px.scatter(df, x="sepal_length", y="sepal_width", color="species", title="Automatic Labels Based on Data Frame Column Names")

# # Atualizar o estilo apenas do ponto (7.9, 3.8) usando update_traces()
# fig.update_traces(marker=dict(symbol=df['custom_symbol'], size=df['custom_size']))

# Exibir o gráfico usando o Streamlit
st.plotly_chart(fig)
