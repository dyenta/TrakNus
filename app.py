import streamlit as st
import pandas as pd
from supabase import create_client
import plotly.express as px

# 1. Koneksi ke Database (Gunakan Secrets untuk keamanan nanti)
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase = create_client(url, key)

st.set_page_config(page_title="Sales Dashboard Pro", layout="wide")

# Menu Navigasi
menu = st.sidebar.selectbox("Pilih Menu", ["Dashboard Analisa", "Upload Data Bulanan"])

if menu == "Dashboard Analisa":
    st.title("📊 Real-time Sales Analytics")
    
    # Ambil data agregat saja (agar ringan)
    # Contoh: Total sales per area
    response = supabase.table("sales_data").select("Area, Amount in Local Currency").execute()
    df = pd.DataFrame(response.data)
    
    # Visualisasi
    fig = px.bar(df.groupby("Area").sum().reset_index(), x="Area", y="Amount in Local Currency")
    st.plotly_chart(fig, use_container_width=True)

elif menu == "Upload Data Bulanan":
    st.title("📂 Update Data Sales")
    st.write("Upload file Excel bulanan Anda di sini untuk menambah database.")
    
    file_baru = st.file_uploader("Pilih File Excel", type=["xlsx"])
    
    if file_baru:
        df_update = pd.read_excel(file_baru)
        st.write(f"Mendeteksi {len(df_update)} baris data baru.")
        
        if st.button("Konfirmasi Simpan ke Cloud"):
            # Proses kirim ke Supabase
            data_dict = df_update.to_dict(orient='records')
            supabase.table("sales_data").insert(data_dict).execute()
            st.success("Data Berhasil Ditambahkan!")