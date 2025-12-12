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

if menu == "Dashboard Analisa":
    st.title("📊 Laporan Pivot Table Sales (Multi-Filter)")

    # -----------------------------------------------------------
    # A. FILTER UTAMA (DATABASE LEVEL)
    # -----------------------------------------------------------
    st.sidebar.markdown("---")
    st.sidebar.header("1. Filter Wajib")
    
    # Filter Tahun (Tetap ambil dari server agar ringan)
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
    # B. FETCH DATA DARI SUPABASE
    # -----------------------------------------------------------
    with st.spinner(f"Mengambil data tahun {selected_years}..."):
        try:
            # Menggunakan .in_() untuk mengambil banyak tahun sekaligus
            try:
                response = supabase.table(TABLE_NAME).select("*").in_("Year", selected_years).execute()
            except:
                response = supabase.table(TABLE_NAME).select("*").in_("year", selected_years).execute()
            
            df = pd.DataFrame(response.data)

        except Exception as e:
            st.error(f"Gagal mengambil data: {e}")
            st.stop()

    # -----------------------------------------------------------
    # C. DATA CLEANING & PREPARATION
    # -----------------------------------------------------------
    if df.empty:
        st.warning("Data tidak ditemukan untuk tahun tersebut.")
    else:
        # 1. Bersihkan Nama Kolom (Huruf kecil & underscore)
        df.columns = [col.lower().replace(" ", "_").replace("-", "_") for col in df.columns]

        # 2. Format Kolom Angka (Amount)
        col_amount = 'amount_in_local_currency'
        if col_amount not in df.columns:
            cols = [c for c in df.columns if 'amount' in c]
            if cols: col_amount = cols[0]
        
        df[col_amount] = pd.to_numeric(df[col_amount], errors='coerce').fillna(0)

        # -----------------------------------------------------------
        # D. FILTER TAMBAHAN (CLIENT SIDE - PANDAS)
        # -----------------------------------------------------------
        st.sidebar.header("2. Filter Detail")

        # --- Filter Bulan ---
        # Ambil daftar bulan yang tersedia di data yang sudah ditarik
        if 'month' in df.columns:
            available_months = sorted(df['month'].unique())
            selected_months = st.sidebar.multiselect(
                "Pilih Bulan:",
                options=available_months,
                default=available_months # Default terpilih semua
            )
            
            # Terapkan Filter Bulan
            if selected_months:
                df = df[df['month'].isin(selected_months)]

        # --- Filter Area ---
        # Ambil daftar area yang tersedia di data
        if 'area' in df.columns:
            available_areas = sorted(df['area'].astype(str).unique())
            selected_areas = st.sidebar.multiselect(
                "Pilih Area:",
                options=available_areas,
                default=available_areas # Default terpilih semua
            )

            # Terapkan Filter Area
            if selected_areas:
                df = df[df['area'].isin(selected_areas)]

        # Tampilkan Info Data setelah difilter
        st.success(f"✅ Menampilkan {len(df)} transaksi.")

        # -----------------------------------------------------------
        # E. PENGATURAN & RENDER PIVOT
        # -----------------------------------------------------------
        if not df.empty:
            st.subheader("⚙️ Atur Tampilan Pivot")
            c1, c2 = st.columns(2)
            with c1:
                # Opsi Baris
                row_options = [c for c in df.columns if c in ["area", "product", "cust_name", "material_group", "sales_office"]]
                # Tambahkan fallback jika kolom tidak ditemukan
                if not row_options: row_options = df.columns.tolist()
                
                row_val = st.selectbox("Baris (Rows):", row_options, index=0)

            with c2:
                # Opsi Kolom
                col_options = ["month", "year", "material_type", "business_area"]
                col_val = st.selectbox("Kolom (Columns):", col_options, index=0)

            # Validasi Kolom Pivot
            if row_val in df.columns and col_val in df.columns and col_amount in df.columns:
                
                # Buat Pivot Table
                pivot = pd.pivot_table(
                    df,
                    index=[row_val],
                    columns=[col_val],
                    values=col_amount,
                    aggfunc='sum',
                    fill_value=0,
                    margins=True,
                    margins_name="Grand Total"
                )
                
                # Sorting descending berdasarkan Grand Total
                pivot = pivot.sort_values(by="Grand Total", ascending=False)

                st.markdown(f"### Pivot: {row_val.upper()} vs {col_val.upper()}")
                
                # Tampilkan Tabel
                st.dataframe(
                    pivot.style.format("Rp {:,.0f}"), 
                    use_container_width=True, 
                    height=500
                )
                
                # Download Button
                st.download_button(
                    "📥 Download CSV",
                    data=pivot.to_csv().encode('utf-8'),
                    file_name=f'Sales_Filter_Result.csv',
                    mime='text/csv'
                )
            else:
                st.warning("Kolom yang dipilih tidak tersedia di data hasil filter.")
        else:
            st.warning("Data kosong setelah difilter. Coba kurangi filter area/bulan.")
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