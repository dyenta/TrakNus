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
    st.title("📊 Laporan Pivot Table Sales")

    # A. FETCH DATA
    with st.spinner("Sedang memuat data..."):
        try:
            # Ambil semua data
            response = supabase.table(TABLE_NAME).select("*").execute()
            df = pd.DataFrame(response.data)
        except Exception as e:
            st.error(f"Error koneksi: {e}")
            st.stop()

    # B. DATA CLEANING
    if df.empty:
        st.warning("Belum ada data.")
    else:
        # 1. Standarisasi nama kolom (Huruf kecil & underscore)
        df.columns = [col.lower().replace(" ", "_").replace("-", "_") for col in df.columns]

        # 2. Pastikan kolom angka berformat numerik
        col_amount = 'amount_in_local_currency' # Sesuaikan nama kolom amount Anda
        if col_amount in df.columns:
            df[col_amount] = pd.to_numeric(df[col_amount], errors='coerce').fillna(0)

        # -----------------------------------------------------------
        # C. PENGATURAN PIVOT TABLE (INTERAKTIF)
        # -----------------------------------------------------------
        st.subheader("⚙️ Konfigurasi Tabel")
        
        # Pilihan untuk Baris dan Kolom Pivot
        c1, c2, c3 = st.columns(3)
        with c1:
            # Mau dikelompokkan berdasarkan apa barisnya? (Area / Product / Customer)
            row_option = st.selectbox("Pilih Baris (Rows):", ["area", "product", "cust_name"], index=0)
        with c2:
            # Mau dikelompokkan berdasarkan apa kolomnya? (Month / Year)
            col_option = st.selectbox("Pilih Kolom (Columns):", ["year", "month", "material_group"], index=0)
        with c3:
            # Filter Tahun (Agar tabel tidak kepanjangan)
            if 'year' in df.columns:
                years = sorted(df['year'].unique())
                selected_year = st.selectbox("Filter Tahun:", years, index=len(years)-1) # Default tahun terakhir
                df_filtered = df[df['year'] == selected_year]
            else:
                df_filtered = df

        st.markdown("---")

        # -----------------------------------------------------------
        # D. MEMBUAT PIVOT TABLE
        # -----------------------------------------------------------
        if col_amount in df_filtered.columns and row_option in df_filtered.columns:
            
            # Membuat Pivot Table Pandas
            pivot_table = pd.pivot_table(
                df_filtered,
                index=[row_option],          # Baris
                columns=[col_option],        # Kolom
                values=col_amount,           # Nilai yang dihitung
                aggfunc='sum',               # Dijumlahkan (Sum)
                fill_value=0,                # Jika kosong isi 0
                margins=True,                # Tampilkan Grand Total
                margins_name="Grand Total"
            )

            # Sorting: Urutkan dari penjualan tertinggi (berdasarkan Grand Total)
            pivot_table = pivot_table.sort_values(by="Grand Total", ascending=False)

            # Tampilkan Judul
            st.subheader(f"Laporan Penjualan: {row_option.upper()} vs {col_option.upper()}")
            
            # TAMPILKAN TABEL DENGAN FORMAT (Highlight & Rupiah)
            st.dataframe(
                pivot_table.style.background_gradient(cmap="Blues", axis=None).format("Rp {:,.0f}"),
                use_container_width=True,
                height=500
            )
            
            # Download Button (Fitur Wajib Dashboard Sales)
            st.download_button(
                label="📥 Download Pivot ke Excel",
                data=pivot_table.to_csv().encode('utf-8'),
                file_name='pivot_sales_report.csv',
                mime='text/csv',
            )
            
        else:
            st.error("Kolom yang dipilih tidak ditemukan di database.")
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