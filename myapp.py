import streamlit as st
import pandas as pd
from datetime import datetime
import requests


def get_top_machines():

    pd.set_option('display.max_columns', 8)
    pd.set_option('max_seq_item', None)
    pd.set_option('display.width', 200)

    headers = {
        'authority': 'b0.p.awsstatic.com',
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'no-cache',
        'origin': 'https://c0.b0.p.awsstatic.com',
        'pragma': 'no-cache',
        'referer': 'https://c0.b0.p.awsstatic.com/',
        'sec-ch-ua': '"Brave";v="117", "Not;A=Brand";v="8", "Chromium";v="117"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'sec-gpc': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36',
    }

    now = int(datetime.now().timestamp() * 1000)
    params = {
        'timestamp': now
    }

    session = requests.Session()
    session.headers.update(headers)

    df = pd.DataFrame()

    for z in [
        'US East (N. Virginia)',
        'US East (Ohio)',
        'US West (N. California)',
        'US West (Oregon)',
        'Canada (Central)',
    ]:
        z_encoded = z.replace(' ', '%20')
        st.write(f'Getting data for {z}')
        url = f'https://b0.p.awsstatic.com/pricing/2.0/meteredUnitMaps/ec2/USD/current/ec2-ondemand-without-sec-sel/{z_encoded}/Linux/index.json'
        response = session.get(url, params=params, headers=headers)
        response_json = response.json()

        for instance_name, instance_dict in response_json['regions'][z].items():
            server_info = {
                'instance_name': instance_name,
                'price': instance_dict['price'],
                'memory': instance_dict['Memory'],
                'vCPU': instance_dict['vCPU'],
                'Instance Type': instance_dict['Instance Type'],
                'location': instance_dict['Location'],
            }
            server_info_df = pd.DataFrame([server_info])
            df = pd.concat([df, server_info_df], ignore_index=True)

    df["Memory_"] = df["memory"].str.extract('(\d+)').astype(float)
    df["vCPU"] = df["vCPU"].astype(float)
    df["price"] = df["price"].astype(float)


    df = df[(df["vCPU"] >= vCPU_min) & (df["Memory_"] >= memory_min) & (df["price"] < price_max)]

    df["Price-Cpu Ratio"] = df["vCPU"] / df["price"]
    df["Price-Memory Ratio"] = df["Memory_"] / df["price"]
    df["Monthly Estimation"] = df["price"] * 24 * 31

    df["RPS-Memory"] = df["Memory_"] * 10
    df["RPS-Network"] = df["Price-Memory Ratio"] * 1000

    df["Request-Per-Second"] = df[["RPS-Memory", "RPS-Network"]].min(axis=1)
    df["RPS-Capacity"] = df["Request-Per-Second"] * (1 / 0.1)

    df["Score"] = (
            (cpu_weight * df["Price-Cpu Ratio"]) / 100 +
            (memory_weight * df["Price-Memory Ratio"]) / 100 +
            (price_weight * df["price"]) / 100 +
            (rps_weight * df["RPS-Capacity"]) / 100
    )

    df = df.sort_values(by="Score", ascending=False)
    df.reset_index(drop=True, inplace=True)

    df = df[["Instance Type", "price", "Monthly Estimation", "memory", "vCPU", "location", "Score"]]

    top_machines = df.head(50)
    return top_machines


st.title("EC2 Machine Selector")

st.markdown("This app helps you select the best EC2 machine for your needs based on your preferences.")
st.markdown("You can adjust the weights and filters to refine your selection.")

st.sidebar.header("Weights")
st.sidebar.markdown("This weights represent the importance of each metric for you. The higher the weight, the more important the metric is.")
cpu_weight = st.sidebar.slider("CPU Weight", 0.0, 1.0, 0.4, 0.1)
memory_weight = st.sidebar.slider("Memory Weight", 0.0, 1.0, 0.3, 0.1)
price_weight = st.sidebar.slider("Price Weight", 0.0, 1.0, 0.5, 0.1)
rps_weight = st.sidebar.slider("RPS Weight", 0.0, 1.0, 0.6, 0.1)

st.sidebar.header("Filters")
st.sidebar.markdown("Adjust the filters to refine your selection.")
vCPU_min = st.sidebar.slider("Minimum vCPU", 0, 128, 16, 2)
memory_min = st.sidebar.slider("Minimum Memory", 0, 512, 64, 2)
price_max = st.sidebar.slider("Maximum Hour Price", 0.0, 10.0, 0.9, 0.1)

if st.sidebar.button("Fetch Top Machines"):
    t_machines = get_top_machines()
    st.write("Top Machines:")
    st.table(t_machines)
