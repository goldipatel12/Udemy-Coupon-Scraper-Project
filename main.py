from src import *
import streamlit as st
import datetime
import pandas as pd
import time
import json


def main():
    st.title("Udemy Scraper Project")
    with st.sidebar:
        st.title("Udemy Scraper Project")
        with st.form(key='my_form'):
            site_to_scrape = st.multiselect("Select Websites To Scrape (Select Multiple):", constants.COUPON_WEBSITES)
            days_delta = st.slider("Do Not Collect Coupons More Than These Many Days Old", 1, 365, 20, 1)
            max_course_count = st.slider("Maximum Number Of Courses To Scrape", 1, 1000, 20, 1)
            max_retries_count = st.slider("Maximum Number Of Retries Per Request", 1, 50, 4, 1)
            submit_button = st.form_submit_button(label='Scrape Udemy Coupon')

    if submit_button and not site_to_scrape:
        st.error('Please Select At-least One Website To Scrape 🚨')

    if submit_button and site_to_scrape:
        scraped_data = scrape.scraper(site_to_scrape, max_course_count, days_delta, max_retries_count)
        df = pd.DataFrame.from_dict(scraped_data)
        if not df.empty:
            tmp_download_link = export.export_csv(df)
            st.markdown(tmp_download_link, unsafe_allow_html=True)
            st.json(df.to_json(orient="records"))
            st.snow()
    # validate = st.sidebar.checkbox("Check Data Availability")
    # if validate:
    #     data = page.total_page(cityname, property_type, bhk)
    #     st.sidebar.write(data)
    # add_scrapebutton = st.sidebar.checkbox("Start Scraping")
    # if add_scrapebutton:
    #     scraped_data = scrape.mb_scraper(data, cityname, property_type,bhk)
    #     cleandata = cleaner.data_cleaner(scraped_data, data)
    #     df = pd.DataFrame(cleandata, columns=constants.COLUMNS)
    #     if not df.empty:
    #         tmp_download_link = export.export_csv(df)
    #         st.markdown(tmp_download_link, unsafe_allow_html=True)
    #         st.json(df.to_json(orient="records"))


if __name__ == "__main__":
    main()