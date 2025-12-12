import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client

# -----------------------------------------------------------------------------
# 1. SETUP & KONEKSI
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Sales Dashboard Pro", layout="wide")

# Mengambil secrets (Pastikan file .streamlit/secrets.toml sudah benar)
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except Exception as e:
    st.error("Gagal koneksi ke Database. Cek file secrets.toml Anda.")
    st.stop()

# Nama Tabel di Supabase Anda (Sesuai kode terakhir Anda)
TABLE_NAME = "MASTER"

# -----------------------------------------------------------------------------
# 2. NAVIGASI
# -----------------------------------------------------------------------------
menu = st.sidebar.selectbox("Pilih Menu", ["Dashboard Analisa", "Upload Data Bulanan"])

# -----------------------------------------------------------------------------
# 3. MENU 1: DASHBOARD ANALISA
# -----------------------------------------------------------------------------
if menu == "Dashboard Analisa":
    st.title("📊 Real-time Sales Analytics")

    # A. FETCH DATA
    # Mengambil data dari Supabase
    with st.spinner("Sedang memuat data dari cloud..."):
        try:
            # Kita ambil semua kolom
            response = supabase.table(TABLE_NAME).select("*").execute()
            df = pd.DataFrame(response.data)
        except Exception as e:
            st.error(f"Terjadi kesalahan saat mengambil data: {e}")
            st.stop()

    # B. DATA CLEANING (PENTING: Mencegah Error KeyError)
    if df.empty:
        st.warning("Data kosong. Silakan upload data terlebih dahulu.")
    else:
        # Ubah semua nama kolom jadi huruf kecil & ganti spasi dengan underscore
        # Contoh: "Amount in Local Currency" -> "amount_in_local_currency"
        df.columns = [col.lower().replace(" ", "_").replace("-", "_") for col in df.columns]

        # Tentukan kolom target (sesuaikan dengan hasil cleaning di atas)
        # Kita cari kolom yang mengandung kata 'amount' dan 'area'
        col_amount = 'amount_in_local_currency' # Default target
        col_area = 'area'                       # Default target

        # Cek apakah kolom benar-benar ada
        if col_amount not in df.columns:
            # Coba cari alternatif jika nama kolomnya beda
            cols_found = [c for c in df.columns if 'amount' in c]
            if cols_found: col_amount = cols_found[0]
        
        # C. KPI METRICS
        if col_amount in df.columns:
            total_sales = df[col_amount].sum()
            total_trx = len(df)
            
            c1, c2 = st.columns(2)
            c1.metric("Total Revenue", f"Rp {total_sales:,.0f}")
            c2.metric("Total Transaksi", f"{total_trx} Baris")
            
            st.markdown("---")

            # D. VISUALISASI
            # Pastikan kolom Area ada
            if col_area in df.columns:
                # Grouping Data
                df_grouped = df.groupby(col_area)[col_amount].sum().reset_index()
                
                # Plot Bar Chart
                st.subheader("Performa Penjualan per Area")
                # Perhatikan: x dan y menggunakan nama variabel yang sudah pasti benar
                fig = px.bar(df_grouped, x=col_area, y=col_amount, 
                             color=col_area, title="Total Sales by Area")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.error(f"Kolom '{col_area}' tidak ditemukan. Nama kolom yang ada: {df.columns.tolist()}")
        else:
            st.error(f"Kolom Amount tidak ditemukan. Nama kolom yang ada: {df.columns.tolist()}")

# -----------------------------------------------------------------------------
# 4. MENU 2: UPLOAD DATA
# -----------------------------------------------------------------------------
elif menu == "Upload Data Bulanan":
    st.title("📂 Update Data Sales")
    st.info("Fitur ini akan menambahkan data baru ke database tanpa menghapus data lama.")

    file_baru = st.file_uploader("Pilih File Excel", type=["xlsx"])

    if file_baru:
        try:
            df_update = pd.read_excel(file_baru)
            st.write(f"✅ Berhasil membaca {len(df_update)} baris data baru.")
            
            # Preview Data
            st.dataframe(df_update.head())

            if st.button("Konfirmasi Simpan ke Cloud"):
                with st.spinner("Sedang mengupload ke Supabase..."):
                    
                    # 1. Bersihkan nama kolom Excel agar cocok dengan Database
                    # (Agar "Amount in Local Currency" di Excel masuk ke "amount_in_local_currency" di DB)
                    df_update.columns = [c.lower().replace(" ", "_").replace("-", "_") for c in df_update.columns]
                    
                    # 2. Konversi ke Dictionary
                    data_dict = df_update.to_dict(orient='records')

                    # 3. Insert ke Supabase
                    supabase.table(TABLE_NAME).insert(data_dict).execute()
                    
                    st.success("🎉 Data Berhasil Ditambahkan! Silakan cek di menu Dashboard.")
        
        except Exception as e:
            st.error(f"Gagal memproses file: {e}")
            st.warning("Pastikan nama kolom di Excel sama dengan yang ada di Database.")