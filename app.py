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
    st.title("📊 Laporan Pivot Table Sales (Multi-Tahun)")

    # -----------------------------------------------------------
    # A. FILTER TAHUN (MULTIPLE SELECT)
    # -----------------------------------------------------------
    # Daftar tahun yang tersedia
    pilihan_tahun = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
    
    st.sidebar.markdown("---")
    st.sidebar.header("Filter Utama")
    
    # Ganti selectbox jadi multiselect
    # Default kita pilih tahun terakhir agar tidak kosong saat pertama buka
    selected_years = st.sidebar.multiselect(
        "Pilih Tahun Data (Bisa lebih dari satu):", 
        options=pilihan_tahun, 
        default=[2024] 
    )

    # Validasi: Jika user menghapus semua pilihan
    if not selected_years:
        st.warning("⚠️ Silakan pilih minimal satu tahun di Sidebar sebelah kiri.")
        st.stop() # Hentikan program sampai user memilih tahun

    # -----------------------------------------------------------
    # B. FETCH DATA (MENGGUNAKAN LOGIKA "IN")
    # -----------------------------------------------------------
    with st.spinner(f"Sedang mengambil data tahun {selected_years}..."):
        try:
            # LOGIKA QUERY BARU: Menggunakan .in_() untuk banyak nilai
            # Artinya: "Ambil data DIMANA Tahun ADA DI DALAM list [2023, 2024]"
            
            try:
                # Coba cari kolom 'Year' (Huruf Besar)
                response = supabase.table(TABLE_NAME).select("*").in_("Year", selected_years).execute()
            except:
                # Jika error, coba cari kolom 'year' (Huruf Kecil)
                response = supabase.table(TABLE_NAME).select("*").in_("year", selected_years).execute()
            
            df = pd.DataFrame(response.data)

        except Exception as e:
            st.error(f"Gagal mengambil data: {e}")
            st.stop()

    # -----------------------------------------------------------
    # C. DATA CLEANING & PIVOT
    # -----------------------------------------------------------
    if df.empty:
        st.warning(f"Data untuk tahun {selected_years} tidak ditemukan di database.")
    else:
        st.success(f"✅ Data dimuat: {len(df)} baris (Tahun: {', '.join(map(str, selected_years))})")
        
        # 1. Bersihkan Nama Kolom (Huruf kecil & underscore)
        df.columns = [col.lower().replace(" ", "_").replace("-", "_") for col in df.columns]

        # 2. Pastikan kolom Amount jadi angka
        col_amount = 'amount_in_local_currency'
        if col_amount not in df.columns:
            cols = [c for c in df.columns if 'amount' in c]
            if cols: col_amount = cols[0]

        df[col_amount] = pd.to_numeric(df[col_amount], errors='coerce').fillna(0)

        # -----------------------------------------------------------
        # D. PENGATURAN PIVOT
        # -----------------------------------------------------------
        st.subheader("⚙️ Atur Tampilan Pivot")
        c1, c2 = st.columns(2)
        with c1:
            # Baris: Biasanya Area atau Produk
            row_option = st.selectbox("Baris (Rows):", ["area", "product", "cust_name", "material_group"], index=0)
        with c2:
            # Kolom: Tambahkan 'year' agar bisa membandingkan antar tahun
            # Default kita ubah jadi 'year' jika user memilih lebih dari 1 tahun
            default_col = 0 if len(selected_years) == 1 else 2 # Index 2 asumsinya adalah 'year' (jika ada di list)
            
            pilihan_kolom = ["month", "material_type", "year", "business_area"]
            col_option = st.selectbox("Kolom (Columns):", pilihan_kolom, index=0)

        # -----------------------------------------------------------
        # E. RENDER PIVOT TABLE
        # -----------------------------------------------------------
        if col_amount in df.columns and row_option in df.columns:
            
            # Cek apakah kolom pivot tersedia
            if col_option not in df.columns:
                st.warning(f"Kolom '{col_option}' tidak ditemukan di data (Mungkin karena data tahun tertentu kosong).")
            else:
                pivot = pd.pivot_table(
                    df,
                    index=[row_option],
                    columns=[col_option],
                    values=col_amount,
                    aggfunc='sum',
                    fill_value=0,
                    margins=True,
                    margins_name="Grand Total"
                )
                
                # Sort berdasarkan Grand Total terbesar
                pivot = pivot.sort_values(by="Grand Total", ascending=False)

                st.subheader(f"Pivot: {row_option.upper()} vs {col_option.upper()}")
                
                # Tampilkan Tabel
                st.dataframe(
                    pivot.style.format("Rp {:,.0f}"), 
                    use_container_width=True, 
                    height=500
                )
                
                # Tombol Download
                st.download_button(
                    "📥 Download CSV",
                    data=pivot.to_csv().encode('utf-8'),
                    file_name=f'Sales_Pivot_{row_option}_vs_{col_option}.csv',
                    mime='text/csv'
                )
        else:
            st.error(f"Kolom {row_option} atau {col_amount} tidak ditemukan setelah cleaning.")
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