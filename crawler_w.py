import sys
import pandas as pd
import numpy as np
import json
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options  
from selenium.common.exceptions import WebDriverException
import time

def index_marks(nrows, chunk_size):
    return range(1 * chunk_size, (nrows // chunk_size + 1) * chunk_size, chunk_size)

def split(dfm, chunk_size):
    indices = index_marks(dfm.shape[0], chunk_size)
    return np.split(dfm, indices)
    
def phone_str(phone):
    num_l = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0']
    p = ''
    for i in range(len(phone)):
        if phone[i] in num_l:
             p = p+phone[i]
    return p

def crawler(group, outfile):
    data = pd.read_csv("data_mean.csv", dtype = {'ZIPCODE':str, 'PHONE':str, 'CAMIS':str})
    
    chunks = split(data, 250)
    chunks_reidx = []
    for i in range(len(chunks)):
        chunks_reidx.append(chunks[i].reset_index())
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    
    browser = webdriver.Chrome(chrome_options=chrome_options, executable_path='./chromedriver.exe')
    result = []
    df = chunks_reidx[group]
    
    for i in range(len(df)):
        dba = df.DBA[i]
        zip_code = df.ZIPCODE[i]
        CAMIS = df.CAMIS[i]
        url = 'https://www.yelp.com/search?find_desc='+ dba +'&find_loc='+ zip_code  

        try:
            browser.get(url)
            time.sleep(3)
            review_c = browser.find_element_by_xpath('//div[@data-key="1"]//a[@class="biz-name js-analytics-click"]')
            time.sleep(0.5)
            browser.execute_script('arguments[0].click();',review_c)

            time.sleep(2)

            drop_c = browser.find_element_by_xpath('//span[@data-dropdown-initial-text="Yelp Sort"]')
            drop_c.location_once_scrolled_into_view
            time.sleep(0.5)
            browser.execute_script('arguments[0].click();',drop_c)
            time.sleep(0.5)
            newest = browser.find_element_by_xpath('//a[@data-review-feed-label="Newest First"]')
            browser.execute_script('arguments[0].click();',newest)
            time.sleep(2)

            soup = BeautifulSoup(browser.page_source, 'lxml')

            name = soup.find('h1').text.strip()

            phone = soup.find('span', class_='biz-phone').text.strip()
            phone = phone_str(phone)

            latitude = json.loads(soup.find("div", class_="lightbox-map hidden").attrs['data-map-state'])['center']['latitude']

            longitude = json.loads(soup.find("div", class_="lightbox-map hidden").attrs['data-map-state'])['center']['longitude']

            address = soup.find('div', class_='map-box-address u-space-l4').address.text.strip()

            review = soup.find_all('div', class_='review-content')
            rev = []
            for j in range(len(review)):
                r = {
                    "date": review[j].span.text.strip()[0:10],
                    "star": float(review[j].div.div.div.attrs['title'].split(' ')[0]),
                    "review": review[j].p.text
                }
                rev.append(r)
            
        except Exception:
            print ('error', name)
            pass

        while True:
            if len(rev)>50:
                break
            else:
                try:
                    next = browser.find_element_by_xpath("//*[text()='Next']")
                    next.location_once_scrolled_into_view
                    time.sleep(0.5)
                    browser.execute_script('arguments[0].click();',next)
                    time.sleep(2)

                    soup = BeautifulSoup(browser.page_source, 'lxml')
                    review = soup.find_all('div', class_='review-content')
                    for j in range(len(review)):
                        r = {
                            "date": review[j].span.text.strip()[0:10],
                            "star": float(review[j].div.div.div.attrs['title'].split(' ')[0]),
                            "review": review[j].p.text
                        }
                        rev.append(r)

                except WebDriverException:
                    break
        try:
            price = soup.find('span', class_="business-attribute price-range").text
        except Exception:
            price = 'NA'
            pass
        
        res = {
            "name" : name,
            "phone": phone,
            "address": address,
            "latitude": latitude,
            "longitude": longitude,
            "price": price,
            "CAMIS": CAMIS,
            "review": rev
        }
        result.append(res)
        if i % 10 == 0:
            print(i)
        if i % 10 == 0:
            with open(fileout, 'w') as outfile:
                json.dump(result, outfile)

    browser.quit()
    
    with open(fileout, 'w') as outfile:
        json.dump(result, outfile)
    print('Finish')
    
if __name__ == '__main__':
    filenames = sys.argv
    
    group = int(filenames[1])
    fileout = filenames [2]

    crawler(group, fileout)
