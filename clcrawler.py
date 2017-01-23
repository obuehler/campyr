__author__ = 'Owen Buehler'
from BeautifulSoup import BeautifulSoup
import urllib2
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import argparse
from time import sleep

base_url = "https://sfbay.craigslist.org"
re_search_url = base_url + "/search/apa?search_distance=2&postal=94110&min_price=3500&max_price=5000&bedrooms=2&availabilityMode=0"

# parser = argparse.ArgumentParser()
# parser.add_argument("test", help="Test mode disabled")
# args = parser.parse_args()
#
# TEST_MODE = args.test == "test"
TEST_MODE = False
TEST_TOS = ['otb6@cornell.edu']
PROD_TOS = ['jules.pichette@richmond.edu']

DATA_FILE = "test.txt" if TEST_MODE else "data.txt"
EMAIL_SUBJECT = "New Craigslist Listings"


def soup_from_url(url):
    """Make a BeautifulSoup object out of the html located at url"""
    html_doc = urllib2.urlopen(url).read()
    return BeautifulSoup(html_doc)

def get_all_cl_results(url):
    """Returns all of the results divs from a given craigslist search url"""
    soup = soup_from_url(url)
    return soup.findAll("li", {"class": "result-row"})

def get_stylesheets(soup):
    """TODO The plan here is to parse these sheets to artificially inject/combine them into a style div,
    then use a module like Premailer or inlinestyle to inline the css before sending the email"""
    return [link["href"] for link in soup.findAll("link") if "stylesheet" in link.get("rel", [])]


def extract_dict_from_div(div):
    print div
    link_div = div.find("a", {"class": "result-title hdrlnk"})
    price_div = div.find("span", {"class": "result-price"})
    housing_div = div.find("span", {"class": "housing"})
    hood_div = div.find("span", {"class": "result-hood"})
    # Clunky way to assign these safely when they aren't guaranteed to be there
    return {"title": link_div.text if link_div else None,
            "link": base_url+link_div["href"] if link_div else None,
            "price": price_div.text if price_div else None,
            "detail": housing_div.text if housing_div else None,
            "neighborhood": hood_div.text if hood_div else None,
            "raw_div": str(div),
            }

def find_new_listings(url):
    listing_dict = {dict["link"]: dict for dict in map(extract_dict_from_div, get_all_cl_results(url))}
    old_listings = read_from_file()
    to_alert = []
    for listing in listing_dict.keys():
        if not old_listings.get(listing, None):
            old_listings[listing] = listing_dict[listing]
            to_alert.append(listing)
    #print to_alert
    dump_to_file(old_listings)
    return to_alert

def dump_to_file(data):
    with open(DATA_FILE, "w") as f:
        f.write(json.dumps(data))

def read_from_file():
    try:
        with open(DATA_FILE, "r") as f:
            return json.loads(f.read())
    except:
        return {}

def email_results(tos, mime_message):
    """Uses Simple Mail Transfer Protocol to send msg to tos."""
    server = smtplib.SMTP('smtp.gmail.com', 587)  # 587 for TLS, 465 for SSL
    server.ehlo()  # Identify self to server
    server.starttls()
    server.ehlo()  # Identify again on encrypted connection (tls only)
    server.login("buehlerowen@gmail.com", "Shotton1")
    if mime_message:  # Blank messages are bad mmkay
        server.sendmail("buehlerowen@gmail.com", tos, mime_message.as_string())
    server.quit()

def prepare_message(subject, new_listings):
    all_listings = read_from_file()
    new_divs = [remove_nonascii(make_email_div(all_listings[key])) for key in new_listings]
    listings_str = "I found these %i new listings for your search query:\n" % len(new_listings)
    html_format = "<html><head></head><body><h1>%s</h1>%s</body></html>"
    listings_divs = MIMEText(html_format % (listings_str, "<br/><br/>".join(new_divs)), 'html')

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg.attach(listings_divs)
    return msg if new_divs else None

def make_email_div(listing):
    format = "<a href=%s>%s</a><br/>%s - %s"
    return format % (listing["link"], listing["title"], listing["price"], listing["neighborhood"])

def remove_nonascii(text):
    return ''.join([i if ord(i) < 128 else ' ' for i in text])

def scrape_and_email(url):
    new_listings = find_new_listings(url)
    email_results(TEST_TOS if TEST_MODE else TEST_TOS + PROD_TOS, prepare_message(EMAIL_SUBJECT, new_listings))

# TODO make an emailer class, scraper class, result class, etc
scrape_and_email(re_search_url)
# Now send me an email about bikes!
TEST_MODE = True
bike_search_url = base_url + "/search/bia?search_distance=5&postal=94025&min_price=200&max_price=1200"
scrape_and_email(bike_search_url)
