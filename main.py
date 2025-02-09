import requests
import plotly.express as px
from io import StringIO
import logging
import streamlit as st
import pandas as pd

# Configure logging for cloud environment
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

@st.cache_data(ttl=3600)  # Cache for 1 hour
def fetch_and_process_data():
    """Fetch and process data from IS Yatirim"""
    url = "https://www.isyatirim.com.tr/tr-tr/analiz/hisse/Sayfalar/Temel-Degerler-Ve-Oranlar.aspx#page-1"
    
    try:
        logging.info("Fetching data from IS Yatirim...")
        response = requests.get(url)
        response.raise_for_status()
        html_content = response.text
        
        # Process sector data
        tables = pd.read_html(StringIO(html_content))
        sector_table = tables[2]
        sector_df = pd.DataFrame({
            "Hisse": sector_table["Kod"],
            "Sektör": sector_table["Sektör"],
            "Piyasa Değeri (mn $)": sector_table["Piyasa Değeri (mn $)"]
        })
        
        # Process return data
        return_table = tables[6]
        try:
            return_df = pd.DataFrame({
                "Hisse": return_table["Kod"],
                "Getiri (%)": return_table["Günlük Getiri (%)"]/100
            })
        except TypeError:
            return_table["Günlük Getiri (%)"] = pd.to_numeric(
                return_table["Günlük Getiri (%)"].str.replace('%', '').str.replace(',', '.'),
                errors='coerce'
            )
            return_df = pd.DataFrame({
                "Hisse": return_table["Kod"],
                "Getiri (%)": return_table["Günlük Getiri (%)"]/100
            })
        
        # Merge and process data
        df = pd.merge(sector_df, return_df, on="Hisse")
        df["Piyasa Değeri (mn $)"] = df["Piyasa Değeri (mn $)"].str.replace('.', '').str.replace(',', '.').astype('float64')
        
        color_ranges = [-10, -5, -0.01, 0, 0.01, 5, 10]
        color_labels = ["red", "indianred", "lightpink", "lightgreen", "lime", "green"]
        df["Renk"] = pd.cut(df["Getiri (%)"], bins=color_ranges, labels=color_labels)
        
        return df
        
    except Exception as e:
        logging.error(f"Error in data processing: {e}")
        st.error(f"Veri çekme işlemi sırasında hata oluştu: {e}")
        return None

def create_treemap(df):
    """Create treemap visualization"""
    try:
        # Create visualization
        color_map = {
            "(?)": "#262931",
            "red": "red",
            "indianred": "indianred",
            "lightpink": "lightpink",
            "lightgreen": "lightgreen",
            "lime": "lime",
            "green": "green"
        }
        
        fig = px.treemap(
            df,
            path=[px.Constant("Borsa İstanbul"), "Sektör", "Hisse"],
            values="Piyasa Değeri (mn $)",
            color="Renk",
            custom_data=["Getiri (%)", "Sektör"],
            color_discrete_map=color_map
        )

        fig.update_traces(
            hovertemplate="<br>".join([
                "Hisse: %{label}",
                "Piyasa Değeri (mn $): %{value}",
                "Getiri: %{customdata[0]}",
                "Sektör: %{customdata[1]}"
            ])
        )
        fig.data[0].texttemplate = "<b>%{label}</b><br>%{customdata[0]} %"
        
        return fig
        
    except Exception as e:
        logging.error(f"Error in visualization creation: {e}")
        st.error(f"Görselleştirme oluşturulurken hata oluştu: {e}")
        return None

def main():
    """Main function for Streamlit app"""
    st.set_page_config(
        page_title="Borsa İstanbul Treemap",
        page_icon="📈",
        layout="wide"
    )
    
    st.title("Borsa İstanbul Hisse Senedi Treemap")
    st.markdown("""
    Bu uygulama, Borsa İstanbul'daki hisse senetlerinin günlük performansını ve piyasa değerlerini görselleştirir.
    - 🟢 Yeşil tonları: Pozitif getiri
    - 🔴 Kırmızı tonları: Negatif getiri
    - Kutu boyutları: Piyasa değeri
    """)
    
    # Add a refresh button
    if st.button("🔄 Verileri Güncelle"):
        st.cache_data.clear()
        st.experimental_rerun()
    
    # Show loading spinner while fetching data
    with st.spinner('Veriler yükleniyor...'):
        df = fetch_and_process_data()
    
    if df is not None:
        # Create and display treemap
        fig = create_treemap(df)
        if fig is not None:
            st.plotly_chart(fig, use_container_width=True)
            
            # Display summary statistics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Toplam Hisse Sayısı", len(df))
            with col2:
                positive_return = len(df[df["Getiri (%)"] > 0])
                st.metric("Yükselen Hisse Sayısı", positive_return)
            with col3:
                negative_return = len(df[df["Getiri (%)"] < 0])
                st.metric("Düşen Hisse Sayısı", negative_return)
            
            # Display raw data in expandable section
            with st.expander("Ham Veriyi Göster"):
                st.dataframe(df.sort_values("Piyasa Değeri (mn $)", ascending=False))

if __name__ == "__main__":
    main()