import streamlit as st
import pandas as pd
import requests
import re
import json
import time
from datetime import datetime
from bs4 import BeautifulSoup

st.set_page_config(
    page_title="Google Maps Scraper",
    page_icon="🗺️",
    layout="wide"
)

st.title("🗺️ Google Maps Business Scraper - REAL DATA")
st.markdown("Extract REAL business data from Google Maps")

# Custom CSS
st.markdown("""
<style>
    .stButton button {
        width: 100%;
        font-weight: bold;
    }
    .real-data {
        background-color: #d4edda;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 5px solid #28a745;
    }
    .warning {
        background-color: #fff3cd;
        padding: 15px;
        border-radius: 10px;
        margin: 10px 0;
        border-left: 5px solid #ffc107;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'scraped_data' not in st.session_state:
    st.session_state.scraped_data = None
if 'search_performed' not in st.session_state:
    st.session_state.search_performed = False

class RealGoogleMapsScraper:
    """Real Google Maps Scraper - Extracts actual data"""
    
    def __init__(self):
        self.results = []
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
    
    def search_google_maps(self, query, max_results=50):
        """Search Google Maps for businesses"""
        places = []
        
        try:
            # Encode query for URL
            encoded_query = requests.utils.quote(query)
            
            # Try multiple sources for real data
            places = self._search_via_serpapi_simulation(query, max_results)
            
            if not places:
                places = self._search_via_direct_google(query, max_results)
            
            if not places:
                places = self._search_via_opencage(query, max_results)
            
            # Enrich with real contact data
            for i, place in enumerate(places):
                yield i + 1, len(places), place
                
                # Try to find real phone number and website
                place = self._find_real_contact(place)
                places[i] = place
                
                time.sleep(0.5)  # Rate limiting
        
        except Exception as e:
            st.error(f"Search error: {e}")
        
        self.results = places
        return places
    
    def _search_via_serpapi_simulation(self, query, max_results):
        """Simulate Google Maps search using available endpoints"""
        places = []
        
        # Use Google Maps search URL directly
        search_url = f"https://www.google.com/maps/search/{requests.utils.quote(query)}"
        
        try:
            response = self.session.get(search_url, timeout=15)
            
            if response.status_code == 200:
                # Extract business data from response
                places = self._extract_business_data(response.text, max_results)
                
        except Exception as e:
            st.warning(f"Direct search limited: {e}")
        
        return places
    
    def _search_via_direct_google(self, query, max_results):
        """Search via Google search as fallback"""
        places = []
        
        search_url = f"https://www.google.com/search?q={requests.utils.quote(query)}+Google+Maps"
        
        try:
            response = self.session.get(search_url, timeout=15)
            
            if response.status_code == 200:
                places = self._extract_from_google_search(response.text, max_results)
                
        except Exception as e:
            st.warning(f"Google search fallback: {e}")
        
        return places
    
    def _search_via_opencage(self, query, max_results):
        """Use OpenCage geocoding as last resort"""
        places = []
        
        # OpenCage free tier - limited but gives real data
        try:
            # Using publicly available data
            search_url = f"https://nominatim.openstreetmap.org/search?q={requests.utils.quote(query)}&format=json&limit={max_results}&addressdetails=1"
            
            response = requests.get(search_url, headers={'User-Agent': 'MapsScraper/1.0'})
            
            if response.status_code == 200:
                data = response.json()
                
                for item in data:
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
                    
                    # Extract from address details
                    addr = item.get('address', {})
                    if addr.get('phone'):
                        place['phone'] = addr.get('phone')
                    if addr.get('website'):
                        place['website'] = addr.get('website')
                    
                    if place['name']:
                        places.append(place)
                        
        except Exception as e:
            st.warning(f"OpenCage search limited: {e}")
        
        return places
    
    def _extract_business_data(self, html, max_results):
        """Extract business data from HTML"""
        places = []
        
        # Pattern for business data in Google Maps
        patterns = [
            r'"name":"([^"]+?)".*?"address":"([^"]+?)".*?"rating":([\d.]+).*?"user_ratings_total":(\d+)',
            r'"title":"([^"]+?)".*?"address":"([^"]+?)"',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html, re.DOTALL)
            
            for match in matches[:max_results]:
                if len(match) >= 2:
                    place = {
                        'name': match[0],
                        'address': match[1] if len(match) > 1 else '',
                        'rating': float(match[2]) if len(match) > 2 and match[2] else 0,
                        'reviews': int(match[3]) if len(match) > 3 and match[3] else 0,
                        'phone': '',
                        'website': '',
                        'category': '',
                        'latitude': '',
                        'longitude': ''
                    }
                    
                    if place['name'] and place['name'] not in [p['name'] for p in places]:
                        places.append(place)
        
        return places
    
    def _extract_from_google_search(self, html, max_results):
        """Extract business data from Google search results"""
        places = []
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find business listings in search results
        business_patterns = [
            r'localResult.*?"name":"([^"]+)".*?"address":"([^"]+)"',
            r'"name":"([^"]+)".*?"formattedAddress":"([^"]+)"',
        ]
        
        for pattern in business_patterns:
            matches = re.findall(pattern, html)
            
            for match in matches[:max_results]:
                place = {
                    'name': match[0],
                    'address': match[1] if len(match) > 1 else '',
                    'phone': '',
                    'website': '',
                    'rating': 0,
                    'reviews': 0,
                    'category': '',
                    'latitude': '',
                    'longitude': ''
                }
                
                if place['name']:
                    places.append(place)
        
        return places
    
    def _find_real_contact(self, place):
        """Find real phone number and website for a business"""
        if not place.get('name'):
            return place
        
        try:
            # Search for business contact info
            search_name = place['name']
            search_url = f"https://www.google.com/search?q={requests.utils.quote(search_name)}+contact+phone"
            
            response = self.session.get(search_url, timeout=10)
            
            if response.status_code == 200:
                # Extract phone numbers - Indonesian format
                phone_patterns = [
                    r'(\+62\d{8,12})',  # +62xxxxxxxx
                    r'(08\d{8,11})',     # 08xxxxxxxx
                    r'(0[2-9]\d{7,10})', # Landline
                    r'(\d{4}[\s-]?\d{4}[\s-]?\d{4})', # 4-4-4 format
                ]
                
                for pattern in phone_patterns:
                    phones = re.findall(pattern, response.text)
                    if phones:
                        place['phone'] = phones[0]
                        break
                
                # Extract websites
                website_pattern = r'(https?://(?:www\.)?[a-zA-Z0-9-]+\.(?:com|co\.id|id|net|org|sch\.id)[^\s"\']*)'
                websites = re.findall(website_pattern, response.text)
                
                for site in websites:
                    if 'google' not in site.lower() and 'youtube' not in site.lower():
                        place['website'] = site
                        break
                
                # Extract rating if available
                rating_pattern = r'ratingValue["\']?\s*:\s*["\']?([\d.]+)'
                ratings = re.findall(rating_pattern, response.text)
                if ratings:
                    try:
                        place['rating'] = float(ratings[0])
                    except:
                        pass
                
                # Extract review count
                review_pattern = r'reviewCount["\']?\s*:\s*["\']?(\d+)'
                reviews = re.findall(review_pattern, response.text)
                if reviews:
                    try:
                        place['reviews'] = int(reviews[0])
                    except:
                        pass
        
        except Exception as e:
            pass  # Silently fail, keep whatever data we have
        
        return place
    
    def get_real_place_details(self, place_id):
        """Get detailed info for a specific place ID"""
        # This would use Google Places API - requires API key
        # For now, return basic info
        return {}

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/google-maps.png", width=80)
    st.markdown("## 🔧 Settings")
    
    search_query = st.text_input(
        "Search Query",
        placeholder="e.g., restaurant Jakarta, hotel Bandung",
        help="Enter what you want to search for"
    )
    
    max_results = st.slider(
        "Maximum Results",
        min_value=5,
        max_value=100,
        value=30,
        step=5
    )
    
    st.markdown("---")
    st.markdown("### ⚠️ Important Notes")
    st.markdown("""
    **About Real Data:**
    - Phone numbers and websites are extracted from public Google search results
    - Some businesses may not have complete contact info
    - For best results, be specific with your search query
    - Rate limiting applied to avoid being blocked
    """)
    
    st.markdown("---")
    st.markdown("### 📝 Search Tips")
    st.markdown("""
    ✅ **Good queries:**
    - `restaurant SCBD Jakarta`
    - `hotel near Malioboro`
    - `cafe with wifi Bandung`
    
    ❌ **Avoid:**
    - Too generic queries
    - Special characters
    """)

# Main content
st.markdown('<div class="real-data">', unsafe_allow_html=True)
st.markdown("**✅ REAL DATA MODE ACTIVE** - Extracting actual business information from Google")
st.markdown('</div>', unsafe_allow_html=True)

col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("### 🎯 Search Configuration")
    search_btn = st.button("🔍 START REAL SCRAPING", type="primary", use_container_width=True)

with col2:
    if st.session_state.scraped_data is not None:
        if st.button("🗑️ Clear Results", use_container_width=True):
            st.session_state.scraped_data = None
            st.session_state.search_performed = False
            st.rerun()

# Search logic
if search_btn and search_query:
    st.session_state.search_performed = True
    
    with st.spinner(f"🔍 Scraping REAL data for '{search_query}'..."):
        scraper = RealGoogleMapsScraper()
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            results = []
            results_gen = scraper.search_google_maps(search_query, max_results)
            
            for i, total, place in results_gen:
                progress = i / total if total > 0 else 0
                progress_bar.progress(progress)
                status_text.text(f"Scraping {i}/{total} businesses... Found phone: {place.get('phone', 'No phone yet')}")
                results.append(place)
            
            st.session_state.scraped_data = results
            
            progress_bar.empty()
            status_text.empty()
            
            if results:
                st.success(f"✅ Successfully extracted {len(results)} businesses with REAL data!")
                
                # Show sample of found phones
                phones_found = sum(1 for p in results if p.get('phone'))
                websites_found = sum(1 for p in results if p.get('website'))
                st.info(f"📞 Found phone numbers: {phones_found}/{len(results)} | 🌐 Found websites: {websites_found}/{len(results)}")
            else:
                st.warning("No results found. Try a different search query.")
                
        except Exception as e:
            st.error(f"Scraping error: {e}")
            st.info("Try using a more specific search query or check your internet connection")

# Display results
if st.session_state.scraped_data:
    df = pd.DataFrame(st.session_state.scraped_data)
    
    # Statistics
    total = len(df)
    with_website = df['website'].astype(str).str.len().gt(0).sum() if 'website' in df.columns else 0
    with_phone = df['phone'].astype(str).str.len().gt(0).sum() if 'phone' in df.columns else 0
    
    st.markdown("---")
    st.markdown("### 📊 Real Data Statistics")
    
    col_s1, col_s2, col_s3, col_s4 = st.columns(4)
    with col_s1:
        st.metric("Total Businesses", total)
    with col_s2:
        st.metric("With Phone Number", f"{with_phone} ({with_phone/total*100:.0f}%)")
    with col_s3:
        st.metric("With Website", f"{with_website} ({with_website/total*100:.0f}%)")
    with col_s4:
        avg_rating = df['rating'].mean() if 'rating' in df.columns else 0
        st.metric("Avg Rating", f"{avg_rating:.1f} ⭐" if avg_rating > 0 else "N/A")
    
    # Filter options
    st.markdown("---")
    st.markdown("### 🔍 Filter Data")
    
    col_f1, col_f2, col_f3 = st.columns(3)
    
    filtered_df = df.copy()
    
    with col_f1:
        filter_website = st.checkbox("🌐 Only with Website")
        if filter_website:
            filtered_df = filtered_df[filtered_df['website'].astype(str).str.len() > 0]
    
    with col_f2:
        filter_phone = st.checkbox("📞 Only with Phone Number")
        if filter_phone:
            filtered_df = filtered_df[filtered_df['phone'].astype(str).str.len() > 0]
    
    with col_f3:
        if 'rating' in df.columns and df['rating'].max() > 0:
            min_rating = st.slider("⭐ Minimum Rating", 0.0, 5.0, 0.0, 0.5)
            if min_rating > 0:
                filtered_df = filtered_df[filtered_df['rating'] >= min_rating]
    
    if len(filtered_df) != len(df):
        st.info(f"Showing {len(filtered_df)} out of {len(df)} businesses")
    
    # Display data table
    st.markdown("---")
    st.markdown("### 📋 Business Data (REAL)")
    
    # Reorder columns for better display
    display_cols = ['name', 'address', 'phone', 'website', 'rating', 'reviews', 'category']
    display_cols = [c for c in display_cols if c in filtered_df.columns]
    
    st.dataframe(
        filtered_df[display_cols],
        use_container_width=True,
        column_config={
            "name": "Business Name",
            "address": "Address",
            "phone": st.column_config.TextColumn("📞 Phone Number"),
            "website": st.column_config.LinkColumn("🌐 Website"),
            "rating": st.column_config.NumberColumn("⭐ Rating", format="%.1f"),
            "reviews": "📝 Reviews",
            "category": "Category"
        }
    )
    
    # Download options
    st.markdown("---")
    st.markdown("### 💾 Export Data")
    
    col_d1, col_d2 = st.columns(2)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename_base = f"google_maps_real_{search_query.replace(' ', '_')}_{timestamp}"
    
    with col_d1:
        csv = filtered_df.to_csv(index=False)
        st.download_button(
            label="📥 Download as CSV",
            data=csv,
            file_name=f"{filename_base}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col_d2:
        # Create Excel file
        try:
            import io
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                filtered_df.to_excel(writer, index=False, sheet_name='Businesses')
            excel_data = output.getvalue()
            st.download_button(
                label="📊 Download as Excel",
                data=excel_data,
                file_name=f"{filename_base}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        except:
            pass

elif not st.session_state.search_performed:
    st.markdown("""
    <div class="warning">
        <h3>📌 About Real Data Mode:</h3>
        <p>This tool extracts REAL business information from Google search results including:</p>
        <ul>
            <li>✅ Business names and addresses</li>
            <li>✅ Phone numbers (when available publicly)</li>
            <li>✅ Websites (when listed)</li>
            <li>✅ Ratings and review counts (when available)</li>
        </ul>
        <p><strong>Note:</strong> Some businesses may not have complete contact info publicly listed. 
        For better results, use specific search queries like "restaurant Senayan City Jakarta" instead of just "restaurant".</p>
    </div>
    """, unsafe_allow_html=True)
