import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from shapely.geometry import Polygon, Point, LineString, mapping
import json
import os
import folium 
from streamlit_folium import folium_static 
from pyproj import Transformer

# ================== FUNGSI TUKAR DMS ==================
def format_dms(decimal_degree):
    d = int(decimal_degree)
    m = int((decimal_degree - d) * 60)
    s = round((((decimal_degree - d) * 60) - m) * 60, 0)
    return f"{d}°{abs(m):02d}'{abs(int(s)):02d}\""

# ================== FUNGSI LOGIN & KEMASKINI ==================
@st.dialog("🔑 Kemaskini Kata Laluan")
def reset_password_dialog():
    st.info("Sila sahkan ID untuk menetapkan semula kata laluan.")
    id_sah = st.text_input("Sahkan ID Pengguna:")
    pass_baru = st.text_input("Kata Laluan Baharu:", type="password")
    pass_sah = st.text_input("Sahkan Kata Laluan Baharu:", type="password")
    
    if st.button("Simpan Kata Laluan", use_container_width=True):
        if id_sah == "HarryFitri" and pass_baru == pass_sah and pass_baru != "":
            st.success("✅ Kata laluan berjaya dikemaskini!")
            st.rerun()
        else:
            st.error("❌ Maklumat tidak sepadan atau kosong.")

def check_password():
    if "password_correct" not in st.session_state:
        _, col_mid, _ = st.columns([1, 1.5, 1])
        with col_mid:
            st.markdown("<h2 style='text-align: center;'>🔐 Sistem Survey Lot PUO</h2>", unsafe_allow_html=True)
            user_id = st.text_input("👤 Masukkan ID:", key="user_id")
            password = st.text_input("🔑 Masukkan Kata Laluan:", type="password", key="user_pass")
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("Log Masuk", use_container_width=True):
                if user_id == "HarryFitri" and password == "1":
                    st.session_state["password_correct"] = True
                    st.rerun()
                else:
                    st.error("😕 ID atau Kata Laluan salah.")
            
            if st.button("❓ Lupa Kata Laluan?", use_container_width=True):
                reset_password_dialog()
        return False
    return True

# ================== MAIN APP (SELEPAS LOGIN) ==================
if check_password():
    
    # --- 👤 PROFIL PENGGUNA ---
    st.sidebar.markdown(
        """
        <div style="background: linear-gradient(135deg, #00B4DB, #0083B0); padding: 20px; border-radius: 15px; text-align: center; margin-bottom: 20px;">
            <img src="https://cdn-icons-png.flaticon.com/512/3135/3135715.png" width="80" style="border-radius: 50%; border: 3px solid white;">
            <h3 style="color: white; margin-top: 10px; font-family: sans-serif;">Hai, HarryFitri!</h3>
            <p style="color: #e0e0e0; font-size: 0.8em; margin-bottom: 0px;">Surveyor Berdaftar</p>
        </div>
        """, unsafe_allow_html=True
    )

    # --- HEADER ---
    col_logo, col_text = st.columns([1.2, 4])
    with col_logo:
        if os.path.exists("Poli_Logo.png"):
            st.image("Poli_Logo.png", width=180)
        else:
            st.warning("⚠️ Logo 'Poli_Logo.png' tidak dijumpai.")

    with col_text:
        st.markdown("""
            <style>
                .main-title { font-family: 'Arial Black', Gadget, sans-serif; font-size: 55px; font-weight: 900; margin-bottom: -15px; line-height: 1; letter-spacing: -2px; }
                .sub-title { font-size: 20px; color: #555; margin-top: 0px; }
            </style>
            <div>
                <h1 class="main-title">SISTEM SURVEY LOT</h1>
                <p class="sub-title">Politeknik Ungku Omar | Jabatan Kejuruteraan Awam</p>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<hr style='border: 1px solid #eee; margin-top: 0px;'>", unsafe_allow_html=True)

    # ================== SIDEBAR SETTINGS ==================
    st.sidebar.header("⚙️ Tetapan Paparan")
    uploaded_file = st.sidebar.file_uploader("Upload fail CSV", type=["csv"])

    st.sidebar.markdown("---")
    st.sidebar.subheader("🌍 Mod Peta Interaktif")
    show_interactive_map = st.sidebar.toggle("On/Off Peta Satelit", value=False)
    map_provider = st.sidebar.radio("Pilih Jenis Peta:", ["Satelit (Hybrid)", "Standard Map"], disabled=not show_interactive_map)

    st.sidebar.markdown("---")
    st.sidebar.subheader("🎨 Pilihan Warna")
    poly_color = st.sidebar.color_picker("Warna Kawasan (Poligon)", "#6036AF") 
    line_color = st.sidebar.color_picker("Warna Garisan Sempadan", "#FFFF00") 
    poly_opacity = st.sidebar.slider("Kelegapan Kawasan", 0.0, 1.0, 0.3)

    st.sidebar.markdown("---")
    plot_theme = st.sidebar.selectbox("Tema Warna Pelan Matplotlib", ["Light Mode", "Dark Mode", "Blueprint"])
    show_bg_grid = st.sidebar.checkbox("Papar Grid Latar", value=True)
    grid_interval = st.sidebar.slider("Jarak Selang Grid", 5, 50, 10)

    st.sidebar.markdown("---")
    st.sidebar.subheader("🖋️ Gaya Label")
    show_luas_label = st.sidebar.checkbox("Papar Label LUAS (Tengah Lot)", value=True)
    show_bearing_label = st.sidebar.checkbox("Papar Label Bearing & Jarak", value=True) # <--- FEATURE ON/OFF BEARING
    label_size_stn = st.sidebar.slider("Saiz Bulatan Stesen", 15, 30, 22) 
    label_size_data = st.sidebar.slider("Saiz Bearing/Jarak", 5, 12, 7)
    label_size_luas = st.sidebar.slider("Saiz Tulisan LUAS", 8, 30, 14) 

    # ================== BACA & PROSES DATA ==================
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            
            if all(col in df.columns for col in ['STN', 'E', 'N']):
                # Transformasi ke WGS84
                transformer = Transformer.from_crs("EPSG:4390", "EPSG:4326", always_xy=True)
                df['lon'], df['lat'] = transformer.transform(df['E'].values, df['N'].values)
                
                coords_en = list(zip(df['E'], df['N']))
                coords_ll = list(zip(df['lon'], df['lat']))
                poly_geom = Polygon(coords_en)
                poly_ll = Polygon(coords_ll) 
                centroid_ll = poly_ll.centroid # Untuk letak label luas di tengah peta
                area = poly_geom.area

                # ================== VISUALIZATION ==================
                st.markdown("### 📊 Ringkasan Lot")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Luas (m²)", f"{area:.2f}")
                col2.metric("Luas (Ekar)", f"{area/4046.856:.4f}")
                col3.metric("Bilangan Stesen", len(df))
                col4.metric("Status", "Tutup" if poly_geom.is_valid else "Ralat")

                st.markdown("---")
                st.subheader("📐 Paparan Pelan Ukur")

                if show_interactive_map:
                    # --- MOD PETA INTERAKTIF (FOLIUM) ---
                    google_map_url = 'https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}' if map_provider == "Satelit (Hybrid)" else 'https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}'
                    m = folium.Map(location=[df['lat'].mean(), df['lon'].mean()], zoom_start=20, max_zoom=22, tiles=google_map_url, attr='Google')
                    
                    # 1. POLIGON LOT
                    lot_info = f"<b>LOT INFO</b><br>Luas: {area:.2f} m²<br>Ekar: {area/4046.856:.4f}"
                    folium.Polygon(
                        locations=[[r['lat'], r['lon']] for _, r in df.iterrows()],
                        color=line_color,
                        weight=3,
                        fill=True,
                        fill_color=poly_color,
                        fill_opacity=poly_opacity,
                        tooltip=folium.Tooltip(lot_info)
                    ).add_to(m)

                    # 2. LABEL LUAS DI TENGAH LOT (Floating Label)
                    if show_luas_label:
                        folium.Marker(
                            [centroid_ll.y, centroid_ll.x],
                            icon=folium.DivIcon(html=f'''<div style="font-size: {label_size_luas}pt; color: white; text-shadow: 2px 2px 4px black; font-weight: bold; width: 200px; text-align: center; margin-left: -100px;">{area:.2f} m²</div>''')
                        ).add_to(m)
                    
                    for i in range(len(df)):
                        p1, p2 = df.iloc[i], df.iloc[(i + 1) % len(df)]
                        dE, dN = p2['E'] - p1['E'], p2['N'] - p1['N']
                        dist, bear = np.sqrt(dE**2 + dN**2), (np.degrees(np.arctan2(dE, dN)) + 360) % 360
                        
                        # 3. LABEL BEARING & JARAK (On/Off Control)
                        if show_bearing_label:
                            mid_lat, mid_lon = (p1['lat'] + p2['lat']) / 2, (p1['lon'] + p2['lon']) / 2
                            angle = -np.degrees(np.arctan2(p2['lat'] - p1['lat'], p2['lon'] - p1['lon']))
                            if angle > 90: angle -= 180
                            elif angle < -90: angle += 180
                            
                            folium.Marker(
                                [mid_lat, mid_lon],
                                icon=folium.DivIcon(html=f'''<div style="transform: rotate({angle}deg); text-align: center; width: 150px; margin-left: -75px;">
                                    <div style="font-size: {label_size_data}pt; color: white; text-shadow: 2px 2px 3px black; font-weight: bold;">
                                    {format_dms(bear)}<br>{dist:.2f}m</div></div>''')
                            ).add_to(m)

                        # 4. BATU SEMPADAN (Hover info koordinat)
                        stn_info = f"<b>STN {int(p1['STN'])}</b><br>E: {p1['E']:.3f}<br>N: {p1['N']:.3f}"
                        folium.Marker(
                            [p1['lat'], p1['lon']],
                            tooltip=folium.Tooltip(stn_info),
                            icon=folium.DivIcon(html=f'''<div style="background-color: white; border: 2px solid red; border-radius: 50%; width: {label_size_stn}px; height: {label_size_stn}px; display: flex; align-items: center; justify-content: center; font-size: {label_size_stn*0.6}px; font-weight: bold; color: black; margin-left: -{label_size_stn/2}px; margin-top: -{label_size_stn/2}px; box-shadow: 1px 1px 3px black;">{int(p1["STN"])}</div>''')
                        ).add_to(m)

                    folium_static(m, width=900, height=550)

                else:
                    # --- MOD MATPLOTLIB (Static) ---
                    # (Dikekalkan untuk paparan blueprint/light/dark)
                    fig, ax = plt.subplots(figsize=(10, 8))
                    if plot_theme == "Dark Mode": bg_color, grid_color = "#121212", "#555555"
                    elif plot_theme == "Blueprint": bg_color, grid_color = "#003366", "#004080"
                    else: bg_color, grid_color = "#ffffff", "#aaaaaa"
                    
                    fig.patch.set_facecolor(bg_color); ax.set_facecolor(bg_color)
                    line_geom = LineString(coords_en + [coords_en[0]])
                    ax.plot(*(line_geom.xy), linewidth=2, color=line_color, zorder=4)
                    ax.fill(*(poly_geom.exterior.xy), color=poly_color, alpha=poly_opacity)

                    if show_luas_label:
                        ax.text(poly_geom.centroid.x, poly_geom.centroid.y, f"{area:.2f} m²", fontsize=label_size_luas, fontweight='bold', color='darkgreen', ha='center', bbox=dict(boxstyle='round,pad=0.3', fc='white', alpha=0.9, ec='green'), zorder=10)

                    if show_bearing_label:
                        for i in range(len(df)):
                            p1, p2 = df.iloc[i], df.iloc[(i + 1) % len(df)]
                            dE, dN = p2['E'] - p1['E'], p2['N'] - p1['N']
                            dist, bear = np.sqrt(dE**2 + dN**2), (np.degrees(np.arctan2(dE, dN)) + 360) % 360
                            txt_angle = np.degrees(np.arctan2(dN, dE))
                            if txt_angle > 90: txt_angle -= 180
                            elif txt_angle < -90: txt_angle += 180
                            ax.text((p1['E']+p2['E'])/2, (p1['N']+p2['N'])/2, f"{format_dms(bear)}\n{dist:.2f}m", fontsize=label_size_data, color='brown', fontweight='bold', ha='center', rotation=txt_angle)

                    for _, row in df.iterrows():
                        ax.scatter(row['E'], row['N'], color='white', edgecolor='red', s=300, zorder=5)
                        ax.text(row['E'], row['N'], str(int(row['STN'])), fontsize=label_size_stn/2, color='black', fontweight='bold', ha='center', va='center', zorder=6)
                    
                    ax.set_aspect("equal")
                    if not show_bg_grid: ax.axis('off')
                    else: ax.grid(True, color=grid_color, linestyle='--')
                    st.pyplot(fig)

                st.markdown("---")
                st.subheader("📋 Jadual Data Koordinat")
                st.dataframe(df[['STN', 'E', 'N', 'lat', 'lon']], use_container_width=True)

            else: st.error("❌ Kolum STN, E, N tak jumpa!")
        except Exception as e: st.error(f"❌ Ralat: {e}")
