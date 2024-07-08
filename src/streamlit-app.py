import time
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import simplejson as json
import streamlit as st
from kafka import KafkaConsumer
from streamlit_autorefresh import st_autorefresh

# Função para criar um consumidor Kafka
def create_kafka_consumer(topic_name):
    # Configurar um consumidor Kafka com o tópico e as configurações especificadas
    consumer = KafkaConsumer(
        topic_name,
        bootstrap_servers='localhost:9092',
        auto_offset_reset='earliest',
        value_deserializer=lambda x: json.loads(x.decode('utf-8')))
    return consumer

# Função para buscar dados do Kafka
def fetch_data_from_kafka(consumer):
    # Poll Kafka consumer for messages within a timeout period
    messages = consumer.poll(timeout_ms=1000)
    data = []

    for topic_partition, message in messages.items():
        for msg in message:
            data.append(msg.value)

    return data

# Função para plotar um gráfico de barras colorido para a contagem de votos por candidato
def plot_colored_bar_chart(results):
    data_type = results['candidate_name']
    colors = plt.cm.viridis(np.linspace(0, 1, len(data_type)))
    
    fig, ax = plt.subplots()
    
    for i, (candidate, total_votes) in enumerate(zip(data_type, results['total_votes'])):
        ax.bar(candidate, total_votes, color=colors[i])
        ax.annotate(str(total_votes), (candidate, total_votes), ha='center', va='bottom', fontsize=12, color='black')

    ax.set_xlabel('Candidato')
    ax.set_ylabel('Total de Votos')
    ax.set_title('Contagem de Votos por Candidato')
    ax.set_xticks(data_type)
    ax.tick_params(axis='x', rotation=90)
    
    return fig

# Função para plotar um gráfico de donut para a distribuição de votos
def plot_donut_chart(data: pd.DataFrame, title='Donut Chart', type='candidate'):
    if type == 'candidate':
        labels = list(data['candidate_name'])

    sizes = list(data['total_votes'])
    fig, ax = plt.subplots()
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=140, wedgeprops=dict(width=0.3))
    ax.axis('equal')
    
    # Add a white circle at the center to create a donut effect
    centre_circle = plt.Circle((0,0),0.70,fc='white')
    ax.add_patch(centre_circle)

    plt.title(title)
    return fig

# Função para atualizar dados exibidos no painel
def update_data():
    while True:
        # Espaço reservado para exibir a última hora de atualização
        last_refresh = st.empty()
        last_refresh.text(f"Última atualização em: {time.strftime('%Y-%m-%d %H:%M:%S')}")

        votes_consumer = create_kafka_consumer("votes_topic")
        votes_data = fetch_data_from_kafka(votes_consumer)
        votes_df = pd.DataFrame(votes_data)
        
        total_votes_all_candidates = votes_df.groupby('candidate_id')['vote'].count().sum()

        st.markdown("""---""")
        st.subheader(f"Total de Votos: {total_votes_all_candidates}")

        # Identificar o candidato líder
        leading_candidate = votes_df.groupby('candidate_id')['vote'].count().idxmax()

        # Exibir informações do candidato líder
        st.markdown("""---""")
        st.header('Candidato Líder')
        col1, col2 = st.columns(2)
        with col1:
            st.image(votes_df.loc[votes_df['candidate_id'] == leading_candidate, 'photo_url'].iloc[0], width=200)
        with col2:
            st.header(votes_df.loc[votes_df['candidate_id'] == leading_candidate, 'candidate_name'].iloc[0])
            st.subheader("Total de Votos: {}".format(votes_df.groupby('candidate_id')['vote'].count().max()))

        # Exibir estatísticas e visualizações
        st.markdown("""---""")
        st.header('Estatísticas')
        results = votes_df.groupby(['candidate_name']).size().reset_index(name='total_votes')
        results = results.reset_index(drop=True)
        col1, col2 = st.columns(2)

        # Exibir gráfico de barras e gráfico de donut
        with col1:
            bar_fig = plot_colored_bar_chart(results)
            st.pyplot(bar_fig)

        with col2:
            donut_fig = plot_donut_chart(results, title='Distribuição de Votos')
            st.pyplot(donut_fig)

        # Exibir tabela com estatísticas do candidato
        st.table(results)

        time.sleep(10)  # Intervalo de atualização

# Layout da barra lateral
def sidebar():
    # Inicializar a última hora de atualização se não estiver presente no estado da sessão
    if st.session_state.get('last_update') is None:
        st.session_state['last_update'] = time.time()

    # Slider para controlar o intervalo de atualização
    refresh_interval = st.sidebar.slider("Intervalo de atualização (segundos)", 5, 60, 10)
    st_autorefresh(interval=refresh_interval * 1000, key="auto")

    # Botão para atualizar manualmente os dados
    if st.sidebar.button('Atualizar Dados'):
        update_data()

# Título do painel Streamlit
st.title('Painel de Eleições em Tempo Real')

# Exibir barra lateral
sidebar()

# Atualizar e exibir dados no painel
update_data()
