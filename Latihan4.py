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

# ================== DATA PENGGUNA ==================
USERS = {
    "HarryFitri": "1",
    "AlipKamal": "2",
    "AripCeluih": "3"
}

# ================== FUNGSI TUKAR DMS ==================
def format_dms(decimal_degree):
    d = int(decimal_degree)
    m = int((decimal_degree - d) * 60)
    s = round((((decimal_degree - d) * 60) - m) * 60, 0)
    return f"{d}°{abs(m):02d}'{abs(int(s)):02d}\""

# ================== FUNGSI EKSPORT KE QGIS (GEOJSON) ==================
def create_geojson(df, poly_geom, area):
    features = []
    
    # 1. Layer Polygon (Lot)
    poly_feat = {
        "type": "Feature",
        "geometry": mapping(poly_geom),
        "properties": {
            "Layer": "Lot_Polygon",
            "Luas_m2": round(area, 3),
            "Luas_Ekar": round(area/4046.856, 4),
            "Nama_Lot": "Lot_Survey"
        }
    }
    features.append(poly_feat)
    
    # 2. Layer LineString (Sempadan)
    coords = list(zip(df['E'], df['N']))
    line_geom = LineString(coords + [coords[0]])
    line_feat = {
        "type": "Feature",
        "geometry": mapping(line_geom),
        "properties": {"Layer": "Sempadan_Line"}
    }
    features.append(line_feat)
    
    # 3. Layer Points (Batu Sempadan)
    for _, row in df.iterrows():
        pt_feat = {
            "type": "Feature",
            "geometry": mapping(Point(row['E'], row['N'])),
            "properties": {
                "Layer": "Batu_Sempadan",
                "STN": int(row['STN']),
                "East": row['E'],
                "North": row['N']
            }
        }
        features.append(pt_feat)
        
    return json.dumps({"type": "FeatureCollection", "features": features}, indent=2)

# ================== FUNGSI LOGIN & KEMASKINI ==================
@st.dialog("🔑 Kemaskini Kata Laluan")
def reset_password_dialog():
    st.info("Sila sahkan ID untuk menetapkan semula kata laluan.")
    id_sah = st.text_input("Sahkan ID Pengguna:")
    pass_baru = st.text_input("Kata Laluan Baharu:", type="password")
    pass_sah = st.text_input("Sahkan Kata Laluan Baharu:", type="password")
    
    if st.button("Simpan Kata Laluan", use_container_width=True):
        if id_sah in USERS and pass_baru == pass_sah and pass_baru != "":
            USERS[id_sah] = pass_baru 
            st.success(f"✅ Kata laluan {id_sah} berjaya dikemaskini!")
            st.rerun()
        else:
            st.error("❌ Maklumat tidak sepadan atau ID tidak wujud.")

def check_password():
    if "password_correct" not in st.session_state:
        _, col_mid, _ = st.columns([1, 1.5, 1])
        with col_mid:
            st.markdown("<h2 style='text-align: center;'>🔐 Sistem Survey Lot PUO</h2>", unsafe_allow_html=True)
            user_id = st.text_input("👤 Masukkan ID:", key="user_id")
            password = st.text_input("🔑 Masukkan Kata Laluan:", type="password", key="user_pass")
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("Log Masuk", use_container_width=True):
                if user_id in USERS and USERS[user_id] == password:
                    st.session_state["password_correct"] = True
                    st.session_state["current_user"] = user_id
                    st.rerun()
                else:
                    st.error("😕 ID atau Kata Laluan salah.")
            
            if st.button("❓ Lupa Kata Laluan?", use_container_width=True):
                reset_password_dialog()
        return False
    return True

# ================== MAIN APP (SELEPAS LOGIN) ==================
if check_password():
    current_user = st.session_state.get("current_user", "User")
    
    st.sidebar.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #00B4DB, #0083B0); padding: 20px; border-radius: 15px; text-align: center; margin-bottom: 20px;">
            <img src="https://cdn-icons-png.flaticon.com/512/3135/3135715.png" width="80" style="border-radius: 50%; border: 3px solid white;">
            <h3 style="color: white; margin-top: 10px; font-family: sans-serif;">Hai, {current_user}!</h3>
            <p style="color: #e0e0e0; font-size: 0.8em; margin-bottom: 0px;">Surveyor Berdaftar</p>
        </div>
        """, unsafe_allow_html=True
    )
    
    if st.sidebar.button("🚪 Log Keluar", use_container_width=True):
        del st.session_state["password_correct"]
        del st.session_state["current_user"]
        st.rerun()

    # --- HEADER ---
    col_logo, col_text = st.columns([1.2, 4])
    with col_logo:
        if os.path.exists("Poli_Logo.png"):
            st.image("Poli_Logo.png", width=180)
        else:
            st.warning("⚠️ Logo tidak dijumpai.")

    with col_text:
        st.markdown("""
            <style>
                .main-title { font-family: 'Arial Black', sans-serif; font-size: 55px; font-weight: 900; margin-bottom: -15px; line-height: 1; letter-spacing: -2px; }
                .sub-title { font-size: 20px; color: #555; margin-top: 0px; }
            </style>
            <div>
                <h1 class="main-title">SISTEM SURVEY LOT</h1>
                <p class="sub-title">Politeknik Ungku Omar | Jabatan Kejuruteraan Awam</p>
            </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<hr style='border: 1px solid #eee; margin-top: 0px;'>", unsafe_allow_html=True)

    # --- SIDEBAR SETTINGS ---
    st.sidebar.header("⚙️ Tetapan Paparan")
    uploaded_file = st.sidebar.file_uploader("Upload fail CSV", type=["csv"])

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        if all(col in df.columns for col in ['STN', 'E', 'N']):
            # CRS: RSO Malaya (EPSG:4390) ke WGS84 (EPSG:4326)
            transformer = Transformer.from_crs("EPSG:4390", "EPSG:4326", always_xy=True)
            df['lon'], df['lat'] = transformer.transform(df['E'].values, df['N'].values)
            
            coords_en = list(zip(df['E'], df['N']))
            coords_ll = list(zip(df['lon'], df['lat']))
            poly_geom = Polygon(coords_en)
            poly_ll = Polygon(coords_ll) 
            centroid_ll = poly_ll.centroid
            area = poly_geom.area

            # --- EKSPORT GEOJSON ---
            st.sidebar.markdown("---")
            st.sidebar.subheader("💾 Eksport Data QGIS")
            geojson_data = create_geojson(df, poly_geom, area)
            st.sidebar.download_button(
                label="📥 Download GeoJSON untuk QGIS",
                data=geojson_data,
                file_name=f"Lot_Survey_{current_user}.geojson",
                mime="application/json",
                use_container_width=True
            )

            # --- MOD PETA ---
            st.sidebar.markdown("---")
            st.sidebar.subheader("🌍 Mod Peta Interaktif")
            show_interactive_map = st.sidebar.toggle("On/Off Peta Satelit", value=True)
            map_provider = st.sidebar.radio("Pilih Jenis Peta:", ["Satelit (Hybrid)", "Standard Map"], disabled=not show_interactive_map)

            st.sidebar.markdown("---")
            st.sidebar.subheader("🎨 Pilihan Warna")
            poly_color = st.sidebar.color_picker("Warna Kawasan (Poligon)", "#6036AF") 
            line_color = st.sidebar.color_picker("Warna Garisan Sempadan", "#FFFF00") 
            poly_opacity = st.sidebar.slider("Kelegapan Kawasan", 0.0, 1.0, 0.3)

            # --- RINGKASAN ---
            st.markdown("### 📊 Ringkasan Lot")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Luas (m²)", f"{area:.2f}")
            col2.metric("Luas (Ekar)", f"{area/4046.856:.4f}")
            col3.metric("Bilangan Stesen", len(df))
            col4.metric("Status", "Tutup" if poly_geom.is_valid else "Ralat")

            st.markdown("---")
            st.subheader("📐 Paparan Pelan Ukur")

            # --- GAYA LABEL ---
            label_size_stn = st.sidebar.slider("Saiz Bulatan Stesen", 15, 30, 22) 
            label_size_data = st.sidebar.slider("Saiz Bearing/Jarak", 5, 12, 7)
            label_size_luas = st.sidebar.slider("Saiz Tulisan LUAS", 8, 30, 14) 
            show_bearing_label = st.sidebar.checkbox("Papar Label Bearing & Jarak", value=True)
            show_luas_label = st.sidebar.checkbox("Papar Label LUAS", value=True)

            if show_interactive_map:
                google_map_url = 'https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}' if map_provider == "Satelit (Hybrid)" else 'https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}'
                m = folium.Map(location=[df['lat'].mean(), df['lon'].mean()], zoom_start=20, max_zoom=22, tiles=google_map_url, attr='Google')
                
                # 1. TOOLTIP LOT (HOVER)
                lot_info = f"<div style='font-family: Arial;'><b>INFO LOT</b><br>Luas: {area:.2f} m²<br>Ekar: {area/4046.856:.4f}</div>"
                folium.Polygon(
                    locations=[[r['lat'], r['lon']] for _, r in df.iterrows()],
                    color=line_color, weight=3, fill=True, fill_color=poly_color, fill_opacity=poly_opacity,
                    tooltip=folium.Tooltip(lot_info)
                ).add_to(m)

                if show_luas_label:
                    folium.Marker(
                        [centroid_ll.y, centroid_ll.x],
                        icon=folium.DivIcon(html=f'''<div style="font-size: {label_size_luas}pt; color: white; text-shadow: 2px 2px 4px black; font-weight: bold; width: 200px; text-align: center; margin-left: -100px; pointer-events: none;">{area:.2f} m²</div>''')
                    ).add_to(m)
                
                for i in range(len(df)):
                    p1, p2 = df.iloc[i], df.iloc[(i + 1) % len(df)]
                    dE, dN = p2['E'] - p1['E'], p2['N'] - p1['N']
                    dist, bear = np.sqrt(dE**2 + dN**2), (np.degrees(np.arctan2(dE, dN)) + 360) % 360
                    
                    if show_bearing_label:
                        mid_lat, mid_lon = (p1['lat'] + p2['lat']) / 2, (p1['lon'] + p2['lon']) / 2
                        folium.Marker(
                            [mid_lat, mid_lon],
                            icon=folium.DivIcon(html=f'''<div style="text-align: center; width: 150px; margin-left: -75px; pointer-events: none;">
                                <div style="font-size: {label_size_data}pt; color: white; text-shadow: 2px 2px 3px black; font-weight: bold;">
                                {format_dms(bear)}<br>{dist:.2f}m</div></div>''')
                        ).add_to(m)

                    # 2. TOOLTIP BATU (HOVER KOORDINAT)
                    stn_info = f"<div style='font-family: Arial;'><b>STN {int(p1['STN'])}</b><br>E: {p1['E']:.3f}<br>N: {p1['N']:.3f}</div>"
                    folium.Marker(
                        [p1['lat'], p1['lon']],
                        tooltip=folium.Tooltip(stn_info),
                        icon=folium.DivIcon(html=f'''<div style="background-color: white; border: 2px solid red; border-radius: 50%; width: {label_size_stn}px; height: {label_size_stn}px; display: flex; align-items: center; justify-content: center; font-size: {label_size_stn*0.6}px; font-weight: bold; color: black; margin-left: -{label_size_stn/2}px; margin-top: -{label_size_stn/2}px; box-shadow: 1px 1px 3px black;">{int(p1["STN"])}</div>''')
                    ).add_to(m)

                folium_static(m, width=900, height=550)

            else:
                # --- MATPLOTLIB ---
                fig, ax = plt.subplots(figsize=(10, 8))
                ax.fill(*(poly_geom.exterior.xy), color=poly_color, alpha=poly_opacity)
                ax.plot(*(poly_geom.exterior.xy), color=line_color, linewidth=2)
                for _, row in df.iterrows():
                    ax.scatter(row['E'], row['N'], color='red')
                ax.set_aspect('equal')
                st.pyplot(fig)

            st.markdown("---")
            st.subheader("📋 Jadual Data Koordinat")
            st.dataframe(df[['STN', 'E', 'N', 'lat', 'lon']], use_container_width=True)

        else: st.error("❌ Kolum STN, E, N tak jumpa!")
