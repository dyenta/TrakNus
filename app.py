import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client

# -----------------------------------------------------------------------------
# 1. SETUP & KONEKSI
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Sales Dashboard Pro", layout="wide")

# Mengambil secrets
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase = create_client(url, key)
except Exception as e:
    st.error("Gagal koneksi ke Database. Cek file secrets.toml Anda.")
    st.stop()

# Nama Tabel di Supabase
TABLE_NAME = "MASTER"

# -----------------------------------------------------------------------------
# 2. NAVIGASI
# -----------------------------------------------------------------------------
menu = st.sidebar.selectbox("Pilih Menu", ["Dashboard Analisa", "Upload Data Bulanan"])

# -----------------------------------------------------------------------------
# 3. MENU DASHBOARD
# -----------------------------------------------------------------------------
if menu == "Dashboard Analisa":
    st.title("📊 Laporan Pivot Table (Full Custom)")

    # -----------------------------------------------------------
    # A. FILTER TAHUN (SERVER SIDE)
    # -----------------------------------------------------------
    st.sidebar.markdown("---")
    st.sidebar.header("1. Filter Utama")
    
    pilihan_tahun = [2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]
    selected_years = st.sidebar.multiselect(
        "Pilih Tahun:", 
        options=pilihan_tahun, 
        default=[2024]
    )

    if not selected_years:
        st.warning("⚠️ Harap pilih minimal satu tahun.")
        st.stop()

    # -----------------------------------------------------------
    # B. FETCH DATA (Efisien & Aman)
    # -----------------------------------------------------------
    with st.spinner(f"Mengambil data tahun {selected_years}..."):
        try:
            # Ambil kolom spesifik (Huruf Kecil) agar ringan & tidak timeout
            # Pastikan nama kolom di bawah ini ada di Supabase Anda (sesuaikan jika beda)
            columns_to_fetch = "year, month, area, product, amount_in_local_currency, cust_name, material_group, material_type, business_area"

            try:
                # Coba ambil dengan nama kolom lowercase
                response = supabase.table(TABLE_NAME).select(columns_to_fetch).in_("year", selected_years).execute()
            except:
                # Fallback: Jika gagal, coba ambil Amount dengan spasi (nama lama)
                alt_cols = 'year, month, area, product, amount_in_local_currency, cust_name, material_group, material_type, business_area'
                response = supabase.table(TABLE_NAME).select(alt_cols).in_("year", selected_years).execute()
            
            df = pd.DataFrame(response.data)

            # Cek Data Kosong
            if df.empty:
                st.warning("Data tidak ditemukan.")
                st.stop()

        except Exception as e:
            st.error(f"Gagal mengambil data: {e}")
            st.stop()

    # -----------------------------------------------------------
    # C. DATA CLEANING
    # -----------------------------------------------------------
    # 1. Bersihkan Nama Kolom (Huruf kecil & underscore)
    df.columns = [col.lower().replace(" ", "_").replace("-", "_") for col in df.columns]

    # 2. Pastikan kolom Amount jadi angka
    col_amount = 'amount_in_local_currency'
    if col_amount not in df.columns:
        # Cari alternatif otomatis
        cols = [c for c in df.columns if 'amount' in c]
        if cols: col_amount = cols[0]
    
    df[col_amount] = pd.to_numeric(df[col_amount], errors='coerce').fillna(0)

    # -----------------------------------------------------------
    # D. FILTER DETAIL (CLIENT SIDE)
    # -----------------------------------------------------------
    st.sidebar.header("2. Filter Detail")

    # Filter Bulan
    if 'month' in df.columns:
        avail_months = sorted(df['month'].unique())
        sel_months = st.sidebar.multiselect("Pilih Bulan:", avail_months, default=avail_months)
        if sel_months: df = df[df['month'].isin(sel_months)]

    # Filter Area
    if 'area' in df.columns:
        avail_areas = sorted(df['area'].astype(str).unique())
        sel_areas = st.sidebar.multiselect("Pilih Area:", avail_areas, default=avail_areas)
        if sel_areas: df = df[df['area'].isin(sel_areas)]

    # Info Data
    st.success(f"✅ Data Siap: {len(df)} Transaksi")

    # -----------------------------------------------------------
    # E. PIVOT TABLE (ROW & COLUMN BERTUMPUK)
    # -----------------------------------------------------------
    if not df.empty:
        st.subheader("⚙️ Konfigurasi Pivot")
        
        # Daftar kolom yang bisa dijadikan dimensi
        dims = [c for c in df.columns if c not in [col_amount, 'posting_date']]
        
        c1, c2 = st.columns(2)
        with c1:
            # MULTI SELECT UNTUK BARIS (Row)
            rows = st.multiselect(
                "Pilih Baris (Bisa Bertumpuk):", 
                options=dims, 
                default=["area", "product"] # Default 2 level
            )
        with c2:
            # MULTI SELECT UNTUK KOLOM (Column) - INI YANG BARU
            cols = st.multiselect(
                "Pilih Kolom (Bisa Bertumpuk):", 
                options=dims,
                default=["year"] # Default 1 level
            )

        # Validasi Pivot
        if not rows or not cols:
            st.warning("⚠️ Harap pilih minimal satu Baris dan satu Kolom.")
        else:
            try:
                # Membuat Pivot Table Multi-Index
                pivot = pd.pivot_table(
                    df,
                    index=rows,       # List (Bertumpuk)
                    columns=cols,     # List (Bertumpuk)
                    values=col_amount,
                    aggfunc='sum',
                    fill_value=0,
                    margins=True,
                    margins_name="Grand Total"
                )

                # Sorting (Opsional, sort berdasarkan Grand Total Baris)
                # Note: Sorting Multi-Column agak tricky, kita sort row-nya saja
                pivot = pivot.sort_values(by=("Grand Total", ""), ascending=False) if ("Grand Total", "") in pivot.columns else pivot

                # Judul Laporan
                row_text = " > ".join([r.upper() for r in rows])
                col_text = " > ".join([c.upper() for c in cols])
                st.markdown(f"### 📑 Laporan: {row_text} vs {col_text}")

                # TAMPILKAN TABEL
                # Kita gunakan format rupiah sederhana
                st.dataframe(
                    pivot.style.format("Rp {:,.0f}"), 
                    use_container_width=True, 
                    height=600
                )
                
                # DOWNLOAD
                st.download_button(
                    "📥 Download CSV",
                    data=pivot.to_csv().encode('utf-8'),
                    file_name=f'Pivot_{"_".join(rows)}_vs_{"_".join(cols)}.csv',
                    mime='text/csv'
                )

            except Exception as e:
                st.error(f"Gagal membuat pivot: {e}")
                st.info("Tips: Jangan memilih kolom yang sama di Baris dan Kolom sekaligus.")

# -----------------------------------------------------------------------------
# 4. MENU UPLOAD
# -----------------------------------------------------------------------------
elif menu == "Upload Data Bulanan":
    st.title("📂 Update Data Sales")
    st.info("Upload file Excel (transaksi baru) di sini.")

    file_baru = st.file_uploader("Pilih File Excel", type=["xlsx"])

    if file_baru:
        try:
            df_up = pd.read_excel(file_baru)
            st.write(f"Mendeteksi {len(df_up)} baris baru.")
            
            if st.button("Konfirmasi Simpan ke Cloud"):
                with st.spinner("Mengupload..."):
                    # Bersihkan nama kolom sebelum upload
                    df_up.columns = [c.lower().replace(" ", "_").replace("-", "_") for c in df_up.columns]
                    
                    data_dict = df_up.to_dict(orient='records')
                    supabase.table(TABLE_NAME).insert(data_dict).execute()
                    st.success("Berhasil disimpan!")
        
        except Exception as e:
            st.error(f"Error: {e}")