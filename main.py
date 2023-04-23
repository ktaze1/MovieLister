import json
import time

from bs4 import BeautifulSoup

import concurrent.futures
from concurrent.futures import ThreadPoolExecutor

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

def get_film_links(url):
    film_links = []
    try:
        driver.get(url)
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, "really-lazy-load")))
    except TimeoutException:
        print(f"Timed out waiting for page to load: {url}")
        return film_links

    # Scroll down until there are no more new films loaded
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    ul_tag = soup.find('ul', {'class': 'poster-list -p150 -grid -constrained clear'})
    if ul_tag:
        li_tags = ul_tag.find_all('li', {'class': 'tooltip poster-container'})
        for li in li_tags:
            link = li.find(lambda tag: tag.name == 'div' and all(cls in tag['class'] for cls in ['react-component', 'poster', 'film-poster']))
            if link:
                film_links.append('http://letterboxd.com' + link['data-film-link'])
    return film_links

def get_film_data(film_url):
    driver.get(film_url)
    try:
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, 'featured-film-header')))
    except TimeoutException:
        print(f"Timed out waiting for film data to load: {film_url}")
        return {}
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    film_data = {}
    section = soup.find('section', {'id': 'featured-film-header'})
    if section:
        film_data['name'] = section.find('h1', {'class': 'headline-1 js-widont prettify'}).text.strip()
        film_data['release_date'] = section.find('small', {'class': 'number'}).text.strip()
        em_tag = section.find('em')
        if em_tag:
            film_data['original_name'] = em_tag.text.strip()
        else:
            film_data['original_name'] = None
    return film_data

def main(initial_urls):
    director_film_data = {}
    with ThreadPoolExecutor() as executor:
        film_links_futures = [(initial_url.split('/')[-2], executor.submit(get_film_links, initial_url)) for initial_url in initial_urls]
        for director, future in film_links_futures:
            try:
                film_links = future.result()
            except Exception as e:
                print(f"Error fetching film links for {director}: {str(e)}")
                continue

        director_film_data[director] = []
        film_data_futures = [executor.submit(get_film_data, film_link) for film_link in film_links]
        for film_data_future in concurrent.futures.as_completed(film_data_futures):
            try:
                director_film_data[director].append(film_data_future.result())
            except Exception as e:
                print(f"Error fetching film data: {str(e)}")
                continue
    return director_film_data


if __name__ == '__main__':

    driver = webdriver.ChromiumEdge()

    initial_url = ['https://letterboxd.com/director/ingmar-bergman/']
    result = main(initial_url)

    with open('films.json', 'w', encoding='utf-8') as outfile:
        json.dump(result, outfile, indent=2, ensure_ascii=False)

    driver.quit()
