import streamlit as st
import pandas as pd
import requests
import json
import time
import re
from datetime import datetime
from typing import Dict, List, Optional

st.set_page_config(
    page_title="Google Maps Super Detail Scraper",
    page_icon="🗺️",
    layout="wide"
)

st.title("🗺️ Google Maps Super Detail Scraper")
st.markdown("Scrape data bisnis hingga tingkat **KELURAHAN/DESA** dengan detail lengkap")

# Custom CSS
st.markdown("""
<style>
    .stButton button {
        width: 100%;
        font-weight: bold;
    }
    .detail-box {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 5px solid #007bff;
    }
    .success-box {
        background-color: #d4edda;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 5px solid #28a745;
    }
    .kelurahan-badge {
        background-color: #17a2b8;
        color: white;
        padding: 3px 8px;
        border-radius: 15px;
        font-size: 12px;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'scraped_data' not in st.session_state:
    st.session_state.scraped_data = None
if 'search_performed' not in st.session_state:
    st.session_state.search_performed = False


class SuperDetailGoogleMapsScraper:
    """
    Google Maps Scraper with Kelurahan/Sub-district level detail
    Extracts complete business data with granular location information
    """
    
    def __init__(self):
        self.results = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive'
        })
    
    def parse_location_parts(self, address: str) -> Dict[str, str]:
        """Parse address into granular components: Kelurahan, Kecamatan, Kota, Provinsi"""
        location_parts = {
            'kelurahan': '',
            'kecamatan': '',
            'kota_kabupaten': '',
            'provinsi': '',
            'kode_pos': '',
            'jalan': '',
            'full_address': address
        }
        
        if not address:
            return location_parts
        
        # Indonesian address patterns
        patterns = {
            'kelurahan': r'Kel\.\s+([^,]+)|Kelurahan\s+([^,]+)',
            'kecamatan': r'Kec\.\s+([^,]+)|Kecamatan\s+([^,]+)',
            'kota_kabupaten': r'(?:Kota|Kabupaten)\s+([^,]+)',
            'provinsi': r'Provinsi\s+([^,]+)',
            'kode_pos': r'\b(\d{5})\b'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, address, re.IGNORECASE)
            if match:
                # Get the first non-None group
                for group in match.groups():
                    if group:
                        location_parts[key] = group.strip()
                        break
        
        # Extract jalan/street name
        jalan_match = re.match(r'^([^,]+)', address)
        if jalan_match:
            location_parts['jalan'] = jalan_match.group(1).strip()
        
        return location_parts
    
    def search_by_subdistrict(self, subdistrict: str, city: str, business_type: str = "", max_results: int = 50) -> List[Dict]:
        """
        Search for businesses in a specific sub-district (kelurahan)
        
        Args:
            subdistrict: Nama kelurahan/desa (e.g., "Cacaban")
            city: Nama kota/kabupaten (e.g., "Magelang")
            business_type: Jenis bisnis (optional, e.g., "toko", "warung")
            max_results: Maximum number of results
        """
        places = []
        
        # Build search query with kelurahan precision
        if business_type:
            query = f"{business_type} {subdistrict} {city}"
        else:
            query = f"{subdistrict} {city}"
        
        st.info(f"🔍 Mencari di: **{subdistrict}, {city}**")
        
        # Try multiple search strategies
        search_strategies = [
            # Strategy 1: Direct Google Maps search
            self._search_via_maps_direct,
            # Strategy 2: OpenStreetMap Nominatim (good for Indonesian addresses)
            self._search_via_nominatim,
            # Strategy 3: Google Search with location filter
            self._search_via_google
        ]
        
        for strategy in search_strategies:
            if len(places) >= max_results:
                break
                
            try:
                new_places = strategy(query, max_results - len(places))
                for place in new_places:
                    if place not in places:
                        # Parse location details for each place
                        place['location_parts'] = self.parse_location_parts(place.get('address', ''))
                        place['kelurahan'] = place['location_parts']['kelurahan'] or subdistrict
                        places.append(place)
                
                if len(places) > 0:
                    st.write(f"   ✅ Mendapatkan {len(places)} hasil dari metode ini")
                    
            except Exception as e:
                st.write(f"   ⚠️ Metode ini gagal: {str(e)[:50]}")
                continue
        
        return places[:max_results]
    
    def _search_via_maps_direct(self, query: str, limit: int) -> List[Dict]:
        """Search via direct Google Maps approach"""
        places = []
        
        # Use Google Maps search URL
        search_url = f"https://www.google.com/maps/search/{requests.utils.quote(query)}"
        
        try:
            response = self.session.get(search_url, timeout=15)
            
            if response.status_code == 200:
                # Extract business data from response
                extracted = self._extract_businesses_from_html(response.text, limit)
                places.extend(extracted)
                
        except Exception as e:
            pass
        
        return places
    
    def _search_via_nominatim(self, query: str, limit: int) -> List[Dict]:
        """Search via OpenStreetMap Nominatim (good for Indonesian addresses)"""
        places = []
        
        # Nominatim API for Indonesian locations
        search_url = "https://nominatim.openstreetmap.org/search"
        params = {
            'q': query,
            'format': 'json',
            'limit': limit,
            'addressdetails': 1,
            'countrycodes': 'id',
            'email': 'scraper@example.com'
        }
        
        try:
            response = requests.get(search_url, params=params, headers={
                'User-Agent': 'MapsScraper/1.0'
            })
            
            if response.status_code == 200:
                data = response.json()
                
                for item in data:
                    address = item.get('display_name', '')
                    addr_details = item.get('address', {})
                    
                    place = {
                        'name': item.get('name', ''),
                        'address': address,
                        'latitude': item.get('lat', ''),
                        'longitude': item.get('lon', ''),
                        'category': addr_details.get('shop', addr_details.get('amenity', '')),
                        'phone': '',
                        'website': '',
                        'rating': 0,
                        'reviews': 0,
                        'kelurahan': addr_details.get('village', addr_details.get('suburb', '')),
                        'kecamatan': addr_details.get('county', ''),
                        'kota_kabupaten': addr_details.get('city', addr_details.get('town', '')),
                        'provinsi': addr_details.get('state', ''),
                        'kode_pos': addr_details.get('postcode', '')
                    }
                    
                    if place['name']:
                        places.append(place)
                        
        except Exception as e:
            pass
        
        return places
    
    def _search_via_google(self, query: str, limit: int) -> List[Dict]:
        """Search via Google Search as fallback"""
        places = []
        
        search_url = f"https://www.google.com/search?q={requests.utils.quote(query)}+Google+Maps"
        
        try:
            response = self.session.get(search_url, timeout=15)
            
            if response.status_code == 200:
                # Extract business listings
                business_pattern = r'"name":"([^"]+)".*?"address":"([^"]+)"'
                matches = re.findall(business_pattern, response.text)
                
                for match in matches[:limit]:
                    place = {
                        'name': match[0],
                        'address': match[1],
                        'phone': '',
                        'website': '',
                        'rating': 0,
                        'reviews': 0,
                        'kelurahan': '',
                        'kecamatan': '',
                        'kota_kabupaten': '',
                        'provinsi': ''
                    }
                    places.append(place)
                    
        except Exception as e:
            pass
        
        return places
    
    def _extract_businesses_from_html(self, html: str, limit: int) -> List[Dict]:
        """Extract business data from HTML response"""
        places = []
        
        # Patterns for business data
        patterns = [
            r'"name":"([^"]+?)".*?"address":"([^"]+?)".*?"rating":([\d.]+).*?"user_ratings_total":(\d+)',
            r'"title":"([^"]+?)".*?"snippet":"([^"]+?)"',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html, re.DOTALL)
            
            for match in matches[:limit]:
                if len(match) >= 2:
                    place = {
                        'name': match[0],
                        'address': match[1] if len(match) > 1 else '',
                        'rating': float(match[2]) if len(match) > 2 and match[2] else 0,
                        'reviews': int(match[3]) if len(match) > 3 and match[3] else 0,
                        'phone': '',
                        'website': '',
                        'kelurahan': '',
                        'kecamatan': '',
                        'kota_kabupaten': '',
                        'provinsi': ''
                    }
                    
                    if place['name'] and place not in places:
                        places.append(place)
        
        return places
    
    def enrich_with_contact_info(self, place: Dict) -> Dict:
        """Try to find phone number and website for a business"""
        if not place.get('name'):
            return place
        
        try:
            search_name = place['name']
            search_url = f"https://www.google.com/search?q={requests.utils.quote(search_name)}+contact+phone+website"
            
            response = self.session.get(search_url, timeout=10)
            
            if response.status_code == 200:
                # Phone patterns for Indonesia
                phone_patterns = [
                    r'(\+62\d{8,12})',
                    r'(08\d{8,11})',
                    r'(0[2-9]\d{7,10})',
                    r'(\(\d{3,4}\)\s*\d{3,4}\s*\d{3,4})'
                ]
                
                for pattern in phone_patterns:
                    phones = re.findall(pattern, response.text)
                    if phones:
                        place['phone'] = phones[0]
                        break
                
                # Website pattern
                website_pattern = r'(https?://(?:www\.)?[a-zA-Z0-9-]+\.(?:com|co\.id|id|net|org|sch\.id)[^\s"\']*)'
                websites = re.findall(website_pattern, response.text)
                
                for site in websites:
                    if 'google' not in site.lower() and 'youtube' not in site.lower():
                        place['website'] = site
                        break
        
        except Exception as e:
            pass
        
        return place
    
    def search_multiple_subdistricts(self, subdistricts: List[str], city: str, business_type: str = "", max_per_subdistrict: int = 30) -> List[Dict]:
        """Search multiple sub-districts and combine results"""
        all_places = []
        
        for subdistrict in subdistricts:
            st.write(f"\n📌 Memproses: **{subdistrict}**")
            places = self.search_by_subdistrict(subdistrict, city, business_type, max_per_subdistrict)
            
            # Enrich with contact info
            for i, place in enumerate(places):
                place = self.enrich_with_contact_info(place)
                places[i] = place
                time.sleep(0.3)  # Rate limiting
            
            all_places.extend(places)
            st.write(f"   ✅ Total dari {subdistrict}: {len(places)} bisnis")
            
            time.sleep(1)  # Delay between subdistricts
        
        return all_places


# Sidebar for configuration
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/google-maps.png", width=80)
    st.markdown("## 🎯 Target Pencarian")
    
    search_mode = st.radio(
        "Mode Pencarian",
        ["📍 Single Kelurahan", "🗺️ Multiple Kelurahan"],
        help="Pilih mode pencarian: satu kelurahan atau beberapa sekaligus"
    )
    
    city = st.text_input(
        "Kota/Kabupaten",
        placeholder="Contoh: Magelang, Jakarta Selatan, Bandung",
        help="Masukkan nama kota atau kabupaten"
    )
    
    business_type = st.text_input(
        "Jenis Bisnis (Opsional)",
        placeholder="Contoh: toko, warung makan, salon, klinik",
        help="Kosongkan jika ingin semua jenis bisnis"
    )
    
    if search_mode == "📍 Single Kelurahan":
        subdistrict = st.text_input(
            "Nama Kelurahan/Desa",
            placeholder="Contoh: Cacaban, Tegalrejo, Sinduadi",
            help="Masukkan nama kelurahan yang ingin dicari"
        )
    else:
        subdistricts_input = st.text_area(
            "Daftar Kelurahan/Desa",
            placeholder="pisahkan dengan koma atau enter\nContoh:\nCacaban, Rejowinangun, Kemirirejo",
            help="Masukkan nama kelurahan, pisahkan dengan koma"
        )
        subdistricts = [s.strip() for s in re.split(r'[,\n]', subdistricts_input) if s.strip()]
    
    max_results = st.slider(
        "Maksimal Hasil per Kelurahan",
        min_value=5,
        max_value=100,
        value=30,
        step=5
    )
    
    st.markdown("---")
    st.markdown("### 📋 Contoh Pencarian")
    st.markdown("""
    **Single Kelurahan:**
    - Kota: `Magelang`
    - Kelurahan: `Cacaban`
    - Jenis: `toko`
    
    **Multiple Kelurahan:**
    - Kota: `Magelang`
    - Kelurahan: `Cacaban, Rejowinangun, Kemirirejo`
    - Jenis: `warung makan`
    """)
    
    st.markdown("---")
    st.markdown("### 📊 Data yang Diekstrak")
    st.markdown("""
    - ✅ Nama Bisnis
    - ✅ Alamat Lengkap
    - ✅ **Kelurahan** (otomatis terdeteksi)
    - ✅ **Kecamatan**
    - ✅ **Kota/Kabupaten**
    - ✅ **Provinsi**
    - ✅ Kode Pos
    - ✅ Nomor Telepon
    - ✅ Website
    - ✅ Rating & Jumlah Ulasan
    - ✅ Koordinat (Lat/Long)
    """)

# Main content area
st.markdown("""
<div class="detail-box">
    <h3>🎯 Pencarian Tingkat Kelurahan</h3>
    <p>Tools ini dirancang khusus untuk mencari bisnis hingga tingkat <strong>KELURAHAN/DESA</strong>. 
    Cocok untuk riset bisnis lokal, analisis kompetitor, atau pengumpulan data UMKM per wilayah.</p>
</div>
""", unsafe_allow_html=True)

col1, col2 = st.columns([2, 1])

with col1:
    search_btn = st.button("🚀 MULAI SCRAPING", type="primary", use_container_width=True)

with col2:
    if st.session_state.scraped_data:
        if st.button("🗑️ Clear Results", use_container_width=True):
            st.session_state.scraped_data = None
            st.session_state.search_performed = False
            st.rerun()

# Search execution
if search_btn:
    if not city:
        st.error("❌ Harap masukkan nama Kota/Kabupaten!")
    elif search_mode == "📍 Single Kelurahan" and not subdistrict:
        st.error("❌ Harap masukkan nama Kelurahan!")
    elif search_mode == "🗺️ Multiple Kelurahan" and (not subdistricts_input or not subdistricts):
        st.error("❌ Harap masukkan daftar Kelurahan!")
    else:
        st.session_state.search_performed = True
        
        with st.spinner("🔍 Memproses pencarian..."):
            scraper = SuperDetailGoogleMapsScraper()
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                if search_mode == "📍 Single Kelurahan":
                    status_text.text(f"Mencari di Kelurahan {subdistrict}, {city}...")
                    results = scraper.search_by_subdistrict(subdistrict, city, business_type, max_results)
                    
                    # Enrich with contact info
                    for i, place in enumerate(results):
                        progress = (i + 1) / len(results) if results else 0
                        progress_bar.progress(progress)
                        status_text.text(f"Mengambil detail {i+1}/{len(results)}: {place.get('name', 'Unknown')[:30]}...")
                        place = scraper.enrich_with_contact_info(place)
                        results[i] = place
                        time.sleep(0.3)
                    
                else:  # Multiple kelurahan
                    status_text.text(f"Mencari di {len(subdistricts)} kelurahan di {city}...")
                    results = scraper.search_multiple_subdistricts(subdistricts, city, business_type, max_results)
                    
                    # Update progress for enrichment
                    for i, place in enumerate(results):
                        progress = (i + 1) / len(results) if results else 0
                        progress_bar.progress(progress)
                        status_text.text(f"Mengambil detail {i+1}/{len(results)}: {place.get('name', 'Unknown')[:30]}...")
                        results[i] = place
                        time.sleep(0.2)
                
                st.session_state.scraped_data = results
                
                progress_bar.empty()
                status_text.empty()
                
                if results:
                    st.balloons()
                    st.success(f"✅ Berhasil! Ditemukan {len(results)} bisnis di wilayah yang dicari!")
                    
                    # Show statistics
                    with_phone = sum(1 for p in results if p.get('phone'))
                    with_website = sum(1 for p in results if p.get('website'))
                    st.info(f"📞 Nomor telepon ditemukan: {with_phone}/{len(results)} | 🌐 Website: {with_website}/{len(results)}")
                else:
                    st.warning("Tidak ada hasil ditemukan. Coba dengan kata kunci yang berbeda.")
                    
            except Exception as e:
                st.error(f"Error: {e}")
                st.info("Silakan coba lagi dengan kata kunci yang lebih spesifik")

# Display results
if st.session_state.scraped_data:
    df = pd.DataFrame(st.session_state.scraped_data)
    
    # Flatten location_parts if it exists as a column
    if 'location_parts' in df.columns:
        location_df = pd.json_normalize(df['location_parts'])
        df = df.drop(columns=['location_parts'])
        df = pd.concat([df, location_df], axis=1)
    
    # Fill missing columns
    expected_cols = ['name', 'address', 'phone', 'website', 'rating', 'reviews', 
                     'kelurahan', 'kecamatan', 'kota_kabupaten', 'provinsi', 'kode_pos', 'jalan']
    for col in expected_cols:
        if col not in df.columns:
            df[col] = ''
    
    # Statistics
    total = len(df)
    with_phone = df['phone'].astype(str).str.len().gt(0).sum()
    with_website = df['website'].astype(str).str.len().gt(0).sum()
    has_kelurahan = df['kelurahan'].astype(str).str.len().gt(0).sum()
    
    st.markdown("---")
    st.markdown("## 📊 Statistik Hasil Pencarian")
    
    col_s1, col_s2, col_s3, col_s4, col_s5 = st.columns(5)
    with col_s1:
        st.metric("Total Bisnis", total)
    with col_s2:
        st.metric("Dengan Telepon", f"{with_phone} ({with_phone/total*100:.0f}%)")
    with col_s3:
        st.metric("Dengan Website", f"{with_website} ({with_website/total*100:.0f}%)")
    with col_s4:
        st.metric("Teridentifikasi Kelurahan", f"{has_kelurahan} ({has_kelurahan/total*100:.0f}%)")
    with col_s5:
        if 'rating' in df.columns and df['rating'].max() > 0:
            avg_rating = df['rating'].mean()
            st.metric("Rata-rata Rating", f"{avg_rating:.1f} ⭐")
        else:
            st.metric("Rata-rata Rating", "N/A")
    
    # Filter options
    st.markdown("---")
    st.markdown("## 🔍 Filter Data")
    
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    
    filtered_df = df.copy()
    
    with col_f1:
        filter_website = st.checkbox("🌐 Hanya yang punya Website")
        if filter_website:
            filtered_df = filtered_df[filtered_df['website'].astype(str).str.len() > 0]
    
    with col_f2:
        filter_phone = st.checkbox("📞 Hanya yang punya Telepon")
        if filter_phone:
            filtered_df = filtered_df[filtered_df['phone'].astype(str).str.len() > 0]
    
    with col_f3:
        if 'rating' in df.columns and df['rating'].max() > 0:
            min_rating = st.slider("⭐ Rating Minimum", 0.0, 5.0, 0.0, 0.5)
            if min_rating > 0:
                filtered_df = filtered_df[filtered_df['rating'] >= min_rating]
    
    with col_f4:
        if 'kelurahan' in df.columns:
            kelurahan_list = ['Semua'] + sorted(df['kelurahan'].dropna().unique().tolist())
            selected_kelurahan = st.selectbox("📍 Filter Kelurahan", kelurahan_list)
            if selected_kelurahan != 'Semua':
                filtered_df = filtered_df[filtered_df['kelurahan'] == selected_kelurahan]
    
    if len(filtered_df) != len(df):
        st.info(f"Menampilkan {len(filtered_df)} dari {len(df)} bisnis")
    
    # Display data table
    st.markdown("---")
    st.markdown("## 📋 Data Bisnis (Lengkap)")
    
    # Select columns to display
    display_cols = ['name', 'jalan', 'kelurahan', 'kecamatan', 'kota_kabupaten', 'phone', 'website', 'rating', 'reviews']
    display_cols = [c for c in display_cols if c in filtered_df.columns]
    
    st.dataframe(
        filtered_df[display_cols],
        use_container_width=True,
        column_config={
            "name": "🏢 Nama Bisnis",
            "jalan": "📍 Jalan",
            "kelurahan": "🏘️ Kelurahan",
            "kecamatan": "🗺️ Kecamatan",
            "kota_kabupaten": "🏙️ Kota/Kab",
            "phone": "📞 Telepon",
            "website": "🌐 Website",
            "rating": st.column_config.NumberColumn("⭐ Rating", format="%.1f"),
            "reviews": "📝 Ulasan"
        }
    )
    
    # Export options
    st.markdown("---")
    st.markdown("## 💾 Export Data")
    
    col_d1, col_d2, col_d3 = st.columns(3)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    location_str = subdistrict if search_mode == "📍 Single Kelurahan" else "multiple_kelurahan"
    filename_base = f"google_maps_{location_str}_{city}_{timestamp}"
    
    with col_d1:
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Download CSV",
            data=csv,
            file_name=f"{filename_base}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col_d2:
        try:
            import io
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                filtered_df.to_excel(writer, index=False, sheet_name='Businesses')
            excel_data = output.getvalue()
            st.download_button(
                label="📊 Download Excel",
                data=excel_data,
                file_name=f"{filename_base}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        except:
            st.info("Install openpyxl untuk export Excel")
    
    with col_d3:
        # Show JSON preview
        if st.button("📋 Lihat JSON Preview", use_container_width=True):
            st.json(filtered_df.head(10).to_dict(orient='records'))

elif not st.session_state.search_performed:
    st.markdown("""
    <div class="success-box">
        <h3>📌 Cara Penggunaan:</h3>
        <ol>
            <li>Masukkan nama <strong>Kota/Kabupaten</strong> (contoh: Magelang)</li>
            <li>Pilih mode pencarian:
                <ul>
                    <li><strong>Single Kelurahan</strong> - cari satu kelurahan saja</li>
                    <li><strong>Multiple Kelurahan</strong> - cari beberapa kelurahan sekaligus</li>
                </ul>
            </li>
            <li>Masukkan nama <strong>Kelurahan/Desa</strong> (contoh: Cacaban)</li>
            <li>(Opsional) Masukkan <strong>jenis bisnis</strong> untuk filter lebih spesifik</li>
            <li>Klik <strong>MULAI SCRAPING</strong></li>
            <li>Data akan muncul dengan detail alamat hingga tingkat kelurahan</li>
        </ol>
        <hr>
        <h4>✨ Fitur Unggulan:</h4>
        <ul>
            <li>✅ Deteksi otomatis Kelurahan, Kecamatan, Kota, Provinsi dari alamat</li>
            <li>✅ Pencarian multiple kelurahan sekaligus</li>
            <li>✅ Filter berdasarkan kelurahan, rating, website, telepon</li>
            <li>✅ Export ke CSV/Excel</li>
            <li>✅ Ekstrak nomor telepon dan website dari hasil pencarian Google</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
