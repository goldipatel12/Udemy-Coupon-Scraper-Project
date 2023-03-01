import json
import os
import random
import re
import threading
import requests
import time
import traceback
from decimal import Decimal
from typing import List
from datetime import datetime, timedelta, date
from math import ceil
# import browser_cookie3
import cloudscraper
import requests
from urllib.parse import parse_qs, unquote, urlsplit, urljoin, urlparse
from bs4 import BeautifulSoup as bs
import streamlit as st


class LoginException(Exception):
    """Login Error

    Args:
        Exception (str): Exception Reason
    """

    pass


class Udemy:
    def __init__(self):
        self.client = requests.session()

    def make_cookies(self, client_id: str, access_token: str, csrf_token: str):
        self.cookie_dict = dict(
            client_id=client_id,
            access_token=access_token,
            csrf_token=csrf_token,
        )

    # def fetch_cookies(self):
    #     """Gets cookies from browser
    #     Sets cookies_dict, cookie_jar
    #     """
    #     cookies = browser_cookie3.load(domain_name="www.udemy.com")
    #     self.cookie_dict: dict = requests.utils.dict_from_cookiejar(cookies)
    #     self.cookie_jar = cookies


    def check_course(self, course_id, coupon_id=False):
        """Checks Purchase,Coupon,Price

        Returns:
            purchased (str | False),
            amount (Decimal)),
            coupon_valid (bool),
        """
        url = (
                "https://www.udemy.com/api-2.0/course-landing-components/"
                + course_id
                + "/me/?components=purchase"
        )
        if coupon_id:
            url += f",redeem_coupon&couponCode={coupon_id}"

        r = self.client.get(url).json()
        print(r)

        try:
            amount = r["purchase"]["data"]["list_price"]["amount"]
        except KeyError:
            print(r)
        coupon_valid = False
        if coupon_id:
            if r["redeem_coupon"]["discount_attempts"][0]["status"] == "applied":
                coupon_valid = True

        return Decimal(amount), coupon_valid

    def manual_login(self, email: str, password: str):

        # s = cloudscraper.CloudScraper()

        s = requests.session()
        r = s.get(
            "https://www.udemy.com/join/signup-popup/",
            headers={"User-Agent": "okhttp/4.9.2 UdemyAndroid 8.9.2(499) (phone)"},
        )

        csrf_token = r.cookies["csrftoken"]

        data = {
            "csrfmiddlewaretoken": csrf_token,
            "locale": "en_US",
            "email": email,
            "password": password,
        }

        # ss = requests.session()
        s.cookies.update(r.cookies)
        s.headers.update(
            {
                "Referer": "https://www.udemy.com/join/signup-popup/",
                "User-Agent": "okhttp/4.9.2 UdemyAndroid 8.9.2(499) (phone)",
            }
        )
        # r = s.get("https://www.udemy.com/join/login-popup/?response_type=json")
        s = cloudscraper.create_scraper(sess=s)
        r = s.post(
            "https://www.udemy.com/join/login-popup/?response_type=json",
            data=data,
            allow_redirects=False,
        )
        if r.text.__contains__("returnUrl"):
            self.make_cookies(
                r.cookies["client_id"], r.cookies["access_token"], csrf_token
            )
        else:
            login_error = r.json()["error"]["data"]["formErrors"][0]
            if login_error[0] == "Y":
                raise LoginException("Too many logins per hour try later")
            elif login_error[0] == "T":
                raise LoginException("Email or password incorrect")
            else:
                raise LoginException(login_error)

    def get_session_info(self):
        """Get Session info
        Sets Client Session, currency and name
        """
        headers = {
            "authorization": "Bearer " + self.cookie_dict["access_token"],
            "accept": "application/json, text/plain, */*",
            "x-requested-with": "XMLHttpRequest",
            "x-forwarded-for": str(
                ".".join(map(str, (random.randint(0, 255) for _ in range(4))))
            ),
            "x-udemy-authorization": "Bearer " + self.cookie_dict["access_token"],
            "content-type": "application/json;charset=UTF-8",
            "origin": "https://www.udemy.com",
            "referer": "https://www.udemy.com/",
            "dnt": "1",
        }

        r = requests.get(
            "https://www.udemy.com/api-2.0/contexts/me/?me=True&Config=True",
            headers=headers,
        ).json()
        if r["me"]["is_authenticated"] == False:
            raise LoginException("Login Failed")

        self.currency: str = r["Config"]["price_country"]["currency"]
        self.display_name: str = r["me"]["display_name"]

        s = requests.session()
        s.cookies.update(self.cookie_dict)
        s.headers.update(headers)
        s.keep_alive = False
        self.client = s


def get_course_id(url: str):
    # url="https://www.udemy.com/course/microsoft-az-102-practice-test?couponCode=04718D908CFD4CBE19BB"
    r = requests.get(url)
    soup = bs(r.content, "html.parser")
    try:
        course_id = (
            soup.find("meta", {"itemprop": "image"})["content"]
            .split("/")[5]
            .split("_")[0]
        )
    except IndexError:
        course_id = ""
    return course_id


def extract_course_coupon(url: str) -> bool or str:
    """Get coupon code from url
    Returns:
       False | Coupon code
    """
    query = urlsplit(url).query
    params = parse_qs(query)
    try:
        params = {k: v[0] for k, v in params.items()}
        return params["couponCode"]
    except KeyError:
        return False


def extract_url_without_query_params(url: str) -> str:
    """Get url without the query params
    Returns:
       False | url without query params
    """
    return urljoin(url, urlparse(url).path)


# def scraper(site_to_scrape: list, max_course_count: int, creation_date: int, max_retries_count: int) -> List[dict]:
def scraper(site_to_scrape: list, max_course_count: int, days_delta: int, max_retries_count: int) -> List[dict]:
    st.markdown("""
            <style>
            #MainMenu{visibility: hidden;}
            footer{visibility: hidden;}
            </style>""", unsafe_allow_html=True)
    st.info(f"Starting Script with the following settings:    \n>>Website to Scrape: {site_to_scrape}   \n>>Maximum Course Count: {max_course_count}   \n>>Maximum Course Count: {days_delta}   \n>>Maximum Retries Count: {max_retries_count}")
    data = []
    course_count = 0

    attempt = 0
    cred_list = [{"email": "goldipatel12@gmail.com", "password": "Goldi@123"},
                 {"email": "dmuddeshya@gmail.com", "password": "Uddeshya@pwd"},
                 {"email": "uddeshya.us@gmail.com", "password": "Uddeshya@2023"},
                 {"email": "Poojasinghsengar.1001@gmail.com", "password": "Uddeshya@2023"},
                 {"email": "Sengar101998@gmail.com", "password": "Uddeshya@2023"}]

    udemy = Udemy()
    login_error = True
    while login_error:
        try:
            # email = "goldipatel12@gmail.com"
            # password = "Goldi@123"
            email = cred_list[attempt]['email']
            password = cred_list[attempt]['password']
            print("Trying to login")
            udemy.manual_login(email, password)
            print(0)
            udemy.get_session_info()
            login_error = False
        except LoginException as e:
            print(str(e))
            attempt = attempt + 1

    last_coupon_date = date.today() - timedelta(days=days_delta)

    for site in site_to_scrape:
        print(site)
        if site == "Real Discount":
            # st.warning("Started Scraping: https://www.real.discount/")
            rd_big_all = []
            data_dict = {}
            r = {}

            headers = {
                "User-Agent": "PostmanRuntime/7.30.0",
                "Host": "www.real.discount",
                "Connection": "Keep-Alive",
            }

            # Pagination Request
            try:
                pagination_r = requests.get(
                    "https://www.real.discount/api-web/all-courses/?store=Udemy&page=1&per_page=40&orderby=date&free=1&editorschoices=0",
                    headers=headers,
                    timeout=5,
                ).json()
            except requests.exceptions.ConnectTimeout:
                pagination_r = requests.get(
                    "https://www.real.discount/api-web/all-courses/?store=Udemy&page=1&per_page=40&orderby=date&free=1&editorschoices=0",
                    headers=headers,
                    timeout=5,
                ).json()

            data_per_page = 100
            if pagination_r:
                entry_count = int(pagination_r["count"])
                total_pages = (entry_count//data_per_page) + 1

            else:
                total_pages = 7
            st.warning(f"Started Scraping: https://www.real.discount/    \n>> Total Page Count {total_pages}")
            for page_no in range(1, total_pages+1):
                if course_count >= max_course_count:
                    break
                try:
                    st.warning(f"Scraping Page: {page_no}/{total_pages} of https://www.real.discount/ for courses")
                    for i in range(max_retries_count):
                        try:
                            try:
                                r = requests.get(
                                    f"https://www.real.discount/api-web/all-courses/?store=Udemy&page={page_no}&per_page={data_per_page}&orderby=date&free=1&editorschoices=0",
                                    headers=headers,
                                    timeout=5,
                                ).json()
                            except requests.exceptions.ConnectTimeout:
                                r = requests.get(
                                    f"https://www.real.discount/api-web/all-courses/?store=Udemy&page={page_no}&per_page={data_per_page}&orderby=date&free=1&editorschoices=0",
                                    headers=headers,
                                    timeout=5,
                                ).json()
                            break
                        except Exception:
                            continue
                    print(r)
                    if r:
                        rd_big_all.extend(r["results"])

                        rd_length = len(rd_big_all)
                        for index, item in enumerate(rd_big_all):
                            print("000000000000")
                            print(item)
                            print(course_count)
                            print(max_course_count)
                            if item["type"] == "Normal":
                                if course_count < max_course_count:
                                    rd_progress = index
                                    course_title = item["name"]
                                    link = item["url"]
                                    expiration_date = item["sale_end"]
                                    start_date_str = item["sale_start"].rstrip()
                                    date_obj = datetime.strptime(start_date_str, '%a, %d %b %Y %H:%M:%S %Z').date()
                                    if last_coupon_date <= date_obj:
                                        if link.startswith("https://click.linksynergy.com"):
                                            try:
                                                link = link.split("murl=")[1]
                                            except:
                                                continue

                                        course_link = extract_url_without_query_params(link)
                                        coupon_code = extract_course_coupon(link)

                                        data_dict["course_title"] = course_title
                                        data_dict["course_link"] = course_link
                                        data_dict["coupon_code"] = coupon_code
                                        data_dict["expiration_date"] = expiration_date

                                        st.success('Successfully fetched course, details:')
                                        st.json(data_dict)

                                        course_id = get_course_id(link)
                                        st.warning('Validating above coupon code On Udemy')
                                        amount, coupon_valid = udemy.check_course(course_id=course_id, coupon_id=coupon_code)
                                        print("------")

                                        if coupon_valid:
                                            st.success('Successfully validated course coupon code on Udemy, Enqueuing Course!')
                                            data.append(data_dict)
                                            data_dict = {}
                                            course_count = course_count + 1
                                        else:
                                            st.error('Invalid coupon code, not Enqueuing course!')

                except:
                    rd_error = traceback.format_exc()
                    rd_length = -1
                    rd_done = True
                    print(rd_error)
        elif site == "999 Course Sale":
            st.warning("Started Scraping: https://999coursesale.com")
            cs_big_all = []
            data_dict = {}
            r = {}
            try:
                head = {
                    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36 Edg/92.0.902.84",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                }
                for i in range(max_retries_count):
                    try:
                        try:
                            r = requests.get(
                                "https://999coursesale.com/freebie-courses-list.php?pd12=free-v5-ret-orig-2-udemy-ans-no&orig_utm_content=&orig_utm_medium=&orig_utm_campaign=&utm_source=nonzu&_redir=",
                                headers=head
                            )
                        except requests.exceptions.ConnectTimeout:
                            r = requests.get(
                                "https://999coursesale.com/freebie-courses-list.php?pd12=free-v5-ret-orig-2-udemy-ans-no&orig_utm_content=&orig_utm_medium=&orig_utm_campaign=&utm_source=nonzu&_redir=",
                                headers=head
                            )
                        break
                    except Exception:
                        continue

                # print(r)
                if r:
                    soup = bs(r.content, "html.parser")
                    # print(r.content)
                    cs_small_all = soup.find_all("div", {"class": "mt-3 text-center"})
                    cs_big_all.extend(cs_small_all)
                    cs_length = len(cs_big_all)
                    for index, item in enumerate(cs_big_all):
                        cs_progress = index
                        a_tag = item.select("a")[0]
                        onclick_fn = str(a_tag.get('onclick'))
                        # print(onclick_fn)
                        sep = "'"
                        onclick_list = onclick_fn.split(sep)
                        course_link = onclick_list[1]
                        coupon_code = onclick_list[3]
                        print(course_link)
                        print(coupon_code)
                        course_title = a_tag.find("h3", {"class": "heading"}).string
                        print("2222222")
                        print(course_title)
                        expiration_date = item.find("span", {"class": "text2"}).string
                        print(expiration_date)
                        course_id = get_course_id(course_link)
                        amount, coupon_valid = udemy.check_course(course_id=course_id, coupon_id=coupon_code)

                        if coupon_valid:
                            data_dict["course_title"] = course_title
                            data_dict["course_link"] = course_link
                            data_dict["coupon_code"] = coupon_code
                            data_dict["expiration_date"] = expiration_date
                            data.append(data_dict)
                            data_dict = {}
                            course_count = course_count + 1

            except:
                cs_error = traceback.format_exc()
                cs_length = -1
                cs_done = True

        elif site == "Course King":
            ck_big_all = []
            data_dict = {}
            r = {}
            try:
                head = {
                    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36 Edg/92.0.902.84",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                }
                for i in range(max_retries_count):
                    try:
                        try:
                            r = requests.get(
                                "https://courseking.org/freebie-courses-list.php?orig_utm_content=&orig_utm_medium=&orig_utm_campaign=&utm_source=nonzu&_redir=",
                                headers=head
                                )
                        except requests.exceptions.ConnectTimeout:
                            r = requests.get(
                                "https://courseking.org/freebie-courses-list.php?orig_utm_content=&orig_utm_medium=&orig_utm_campaign=&utm_source=nonzu&_redir=",
                                headers=head
                            )
                        break
                    except Exception:
                        continue

                # print(r)
                if r:
                    soup = bs(r.content, "html.parser")
                    # print(r.content)
                    ck_small_all = soup.find_all("div", {"class": "mt-3 text-center"})
                    ck_big_all.extend(ck_small_all)
                    ck_length = len(ck_big_all)
                    for index, item in enumerate(ck_big_all):
                        cs_progress = index
                        a_tag = item.select("a")[0]
                        onclick_fn = str(a_tag.get('onclick'))
                        # print(onclick_fn)
                        sep = "'"
                        onclick_list = onclick_fn.split(sep)
                        course_link = onclick_list[1]
                        coupon_code = onclick_list[3]
                        print(course_link)
                        print(coupon_code)
                        course_title = a_tag.find("h3", {"class": "heading"}).string
                        print("2222222")
                        print(course_title)
                        expiration_date = item.find("span", {"class": "text2"}).string
                        print(expiration_date)
                        course_id = get_course_id(course_link)
                        amount, coupon_valid = udemy.check_course(course_id=course_id, coupon_id=coupon_code)

                        if coupon_valid:
                            data_dict["course_title"] = course_title
                            data_dict["course_link"] = course_link
                            data_dict["coupon_code"] = coupon_code
                            data_dict["expiration_date"] = expiration_date
                            data.append(data_dict)
                            data_dict = {}
                            course_count = course_count + 1

            except:
                ck_error = traceback.format_exc()
                ck_length = -1
                ck_done = True

    return data


# if __name__ == "__main__":
#     print(scraper(site_to_scrape=["Real Discount"], max_course_count=20, max_retries_count=2))