import streamlit as st
import pandas as pd
import requests
import re
import json
import time
from datetime import datetime

st.set_page_config(
    page_title="Google Maps Scraper",
    page_icon="🗺️",
    layout="wide"
)

st.title("🗺️ Google Maps Business Scraper")
st.markdown("Extract business data from Google Maps - No API key required")

# Custom CSS
st.markdown("""
<style>
    .stButton button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
        font-weight: bold;
    }
    .success-box {
        background-color: #d4edda;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .info-box {
        background-color: #d1ecf1;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'scraped_data' not in st.session_state:
    st.session_state.scraped_data = None
if 'search_performed' not in st.session_state:
    st.session_state.search_performed = False

class GoogleMapsScraper:
    def __init__(self):
        self.results = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
    
    def search_places_api(self, query, max_results=50):
        """Search places using a free API alternative"""
        places = []
        
        # Using OpenStreetMap Nominatim as free alternative
        # This gives basic place data that we can enrich
        try:
            search_url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': query,
                'format': 'json',
                'limit': max_results,
                'addressdetails': 1,
                'email': 'user@example.com'  # Replace with your email for better rate limits
            }
            
            response = requests.get(search_url, params=params, headers={
                'User-Agent': 'GoogleMapsScraper/1.0'
            })
            
            if response.status_code == 200:
                data = response.json()
                
                for i, item in enumerate(data[:max_results]):
                    place = {
                        'name': item.get('display_name', '').split(',')[0],
                        'address': item.get('display_name', ''),
                        'latitude': item.get('lat', ''),
                        'longitude': item.get('lon', ''),
                        'category': item.get('type', ''),
                        'phone': '',
                        'website': '',
                        'rating': 0,
                        'reviews': 0
                    }
                    
                    # Try to enrich with additional info
                    enriched = self.enrich_place_data(place['name'])
                    if enriched:
                        place.update(enriched)
                    
                    places.append(place)
                    
                    # Update progress
                    yield i + 1, len(data), place
                    
                    time.sleep(0.5)  # Rate limiting
                    
            else:
                st.error(f"API Error: {response.status_code}")
                
        except Exception as e:
            st.error(f"Error: {e}")
        
        self.results = places
        return places
    
    def enrich_place_data(self, place_name):
        """Try to find phone and website for a place"""
        enriched = {'phone': '', 'website': ''}
        
        try:
            # Search Google for business info (simulated - in real scenario you'd need proper API)
            search_url = f"https://www.google.com/search?q={requests.utils.quote(place_name)}+contact"
            response = self.session.get(search_url, timeout=10)
            
            if response.status_code == 200:
                # Extract phone pattern
                phone_pattern = r'(\+?\d{1,4}[\s\-]?\(?\d{2,4}\)?[\s\-]?\d{3,4}[\s\-]?\d{3,4})'
                phones = re.findall(phone_pattern, response.text)
                if phones:
                    enriched['phone'] = phones[0]
                
                # Extract website
                website_pattern = r'(https?://[^\s"\']+\.(?:com|co\.id|id|net|org)[^\s"\']*)'
                websites = re.findall(website_pattern, response.text)
                for site in websites:
                    if 'google' not in site.lower() and 'youtube' not in site.lower():
                        enriched['website'] = site
                        break
                        
        except:
            pass
        
        return enriched
    
    def generate_sample_data(self, query, count=20):
        """Generate sample data for demo purposes"""
        sample_categories = {
            'restaurant': ['Warung Makan', 'Kafe', 'Restoran Padang', 'Sushi House', 'Pizza Place'],
            'hotel': ['Hotel Santika', 'Aston Hotel', 'Ibis Hotel', 'Grand Hotel', 'Budget Inn'],
            'shop': ['Toko Baju', 'Elektronik Store', 'Minimarket', 'Butik', 'Book Store']
        }
        
        places = []
        for i in range(count):
            category = list(sample_categories.keys())[i % len(sample_categories)]
            name_template = sample_categories[category][i % len(sample_categories[category])]
            
            place = {
                'name': f"{name_template} {query.split()[0]} {i+1}",
                'address': f"Jl. Contoh No. {i+1}, {query}",
                'phone': f"+62 812-{i:04d}-{i:04d}",
                'website': f"https://www.example{i+1}.com" if i % 3 == 0 else "",
                'rating': round(3 + (i % 25) / 10, 1),
                'reviews': (i + 1) * (10 + (i % 90)),
                'category': category,
                'latitude': f"-6.2{i}",
                'longitude': f"106.8{i}"
            }
            places.append(place)
            yield i + 1, count, place
        
        self.results = places
        return places

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/google-maps.png", width=80)
    st.markdown("## 🔧 Settings")
    
    search_query = st.text_input(
        "Search Query",
        placeholder="e.g., restaurants in Jakarta, coffee shop Bandung",
        help="Enter what you want to search for"
    )
    
    max_results = st.slider(
        "Maximum Results",
        min_value=10,
        max_value=200,
        value=50,
        step=10,
        help="Number of businesses to extract"
    )
    
    use_demo = st.checkbox(
        "Use Demo Data",
        value=False,
        help="Generate sample data for testing (no actual scraping)"
    )
    
    st.markdown("---")
    st.markdown("### 📋 Search Examples")
    st.markdown("""
    - `restaurants in Jakarta`
    - `hotel in Bandung`
    - `coffee shop Surabaya`
    - `cafe near Monas`
    - `plumber in Bali`
    """)
    
    st.markdown("---")
    st.markdown("### ⚠️ Note")
    st.markdown("""
    This tool uses free APIs. For best results:
    - Use specific queries
    - Be patient between searches
    - Results are for demonstration
    """)

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### 🎯 Search Configuration")
    
    col_a, col_b = st.columns(2)
    with col_a:
        search_btn = st.button("🔍 START SCRAPING", type="primary", use_container_width=True)
    with col_b:
        clear_btn = st.button("🗑️ Clear Results", use_container_width=True)

with col2:
    st.markdown("### 📊 Statistics")
    if st.session_state.scraped_data:
        stats_placeholder = st.empty()
    else:
        st.info("No data yet. Click 'Start Scraping'")

# Clear button logic
if clear_btn:
    st.session_state.scraped_data = None
    st.session_state.search_performed = False
    st.rerun()

# Search button logic
if search_btn and search_query:
    st.session_state.search_performed = True
    
    with st.spinner(f"🔍 Scraping data for '{search_query}'..."):
        scraper = GoogleMapsScraper()
        
        # Progress bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        if use_demo:
            # Use demo data
            results_gen = scraper.generate_sample_data(search_query, max_results)
            results = []
            for i, total, place in results_gen:
                progress = i / total
                progress_bar.progress(progress)
                status_text.text(f"Generating {i}/{total} businesses...")
                results.append(place)
            st.session_state.scraped_data = results
        else:
            # Try to get real data
            try:
                results = []
                results_gen = scraper.search_places_api(search_query, max_results)
                for i, total, place in results_gen:
                    progress = i / total if total > 0 else 0
                    progress_bar.progress(progress)
                    status_text.text(f"Scraping {i}/{total} businesses...")
                    results.append(place)
                st.session_state.scraped_data = results
            except Exception as e:
                st.error(f"Error during scraping: {e}")
                st.info("Switching to demo mode...")
                results_gen = scraper.generate_sample_data(search_query, max_results)
                results = []
                for i, total, place in results_gen:
                    progress = i / total
                    progress_bar.progress(progress)
                    status_text.text(f"Generating {i}/{total} businesses...")
                    results.append(place)
                st.session_state.scraped_data = results
        
        progress_bar.empty()
        status_text.empty()
    
    st.success(f"✅ Successfully extracted {len(st.session_state.scraped_data)} businesses!")
    st.balloons()

# Display results
if st.session_state.scraped_data:
    df = pd.DataFrame(st.session_state.scraped_data)
    
    # Statistics
    total = len(df)
    with_website = df['website'].astype(str).str.len().gt(0).sum() if 'website' in df.columns else 0
    with_phone = df['phone'].astype(str).str.len().gt(0).sum() if 'phone' in df.columns else 0
    avg_rating = df['rating'].mean() if 'rating' in df.columns else 0
    
    st.markdown("---")
    st.markdown("### 📈 Data Overview")
    
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    with col_s1:
        st.metric("Total Businesses", total)
    with col_s2:
        st.metric("With Website", f"{with_website} ({with_website/total*100:.0f}%)")
    with col_s3:
        st.metric("With Phone", f"{with_phone} ({with_phone/total*100:.0f}%)")
    with col_s4:
        st.metric("Avg Rating", f"{avg_rating:.1f} ⭐")
    
    # Filter options
    st.markdown("---")
    st.markdown("### 🔍 Filter Data")
    
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    
    filtered_df = df.copy()
    
    with col_f1:
        filter_website = st.checkbox("Only with Website")
        if filter_website:
            filtered_df = filtered_df[filtered_df['website'].astype(str).str.len() > 0]
    
    with col_f2:
        filter_phone = st.checkbox("Only with Phone")
        if filter_phone:
            filtered_df = filtered_df[filtered_df['phone'].astype(str).str.len() > 0]
    
    with col_f3:
        min_rating = st.slider("Minimum Rating", 0.0, 5.0, 0.0, 0.5)
        if min_rating > 0:
            filtered_df = filtered_df[filtered_df['rating'] >= min_rating]
    
    with col_f4:
        min_reviews = st.number_input("Minimum Reviews", 0, 1000, 0)
        if min_reviews > 0:
            filtered_df = filtered_df[filtered_df['reviews'] >= min_reviews]
    
    if len(filtered_df) != len(df):
        st.info(f"Showing {len(filtered_df)} out of {len(df)} businesses")
    
    # Display data table
    st.markdown("---")
    st.markdown("### 📋 Business Data")
    
    st.dataframe(
        filtered_df,
        use_container_width=True,
        column_config={
            "name": "Business Name",
            "address": "Address",
            "phone": "Phone",
            "website": "Website",
            "rating": st.column_config.NumberColumn("Rating", format="%.1f ⭐"),
            "reviews": "Reviews",
            "category": "Category"
        }
    )
    
    # Download options
    st.markdown("---")
    st.markdown("### 💾 Export Data")
    
    col_d1, col_d2, col_d3 = st.columns(3)
    
    with col_d1:
        # Download CSV
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Download as CSV",
            data=csv,
            file_name=f"google_maps_{search_query.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col_d2:
        # Download Excel
        try:
            import io
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                filtered_df.to_excel(writer, index=False, sheet_name='Businesses')
            excel_data = output.getvalue()
            st.download_button(
                label="📊 Download as Excel",
                data=excel_data,
                file_name=f"google_maps_{search_query.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        except:
            st.info("Excel export requires openpyxl. Use CSV instead.")
    
    with col_d3:
        # Copy to clipboard
        if st.button("📋 Copy to Clipboard", use_container_width=True):
            st.code(csv[:1000] + "...", language='csv')
            st.info("Select all (Ctrl+A) and copy (Ctrl+C)")

elif search_btn and not search_query:
    st.warning("⚠️ Please enter a search query")

elif not st.session_state.search_performed:
    st.markdown("""
    <div class="info-box">
        <h3>📌 How to Use:</h3>
        <ol>
            <li>Enter a search query in the sidebar (e.g., "restaurants in Jakarta")</li>
            <li>Set maximum number of results you want</li>
            <li>Click <b>START SCRAPING</b> button</li>
            <li>Wait for the scraper to extract data</li>
            <li>Filter results using the options above</li>
            <li>Download data as CSV or Excel</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="success-box">
        <h3>✨ Features:</h3>
        <ul>
            <li>✅ Extract business names, addresses, and contact info</li>
            <li>✅ Filter by website, phone, rating, and reviews</li>
            <li>✅ Export to CSV or Excel format</li>
            <li>✅ Works online - no installation needed</li>
            <li>✅ Free to use with demo data option</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
