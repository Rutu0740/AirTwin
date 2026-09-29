from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import time

options = Options()
options.add_argument('--headless')
driver = webdriver.Chrome(options=options)
driver.get('http://127.0.0.1:8000/overview/')

time.sleep(2) # Wait for Leaflet to initialize

try:
    map_h = driver.execute_script("return document.getElementById('map') ? document.getElementById('map').offsetHeight : -1")
    map_inner = driver.execute_script("return document.getElementById('map') ? document.getElementById('map').innerHTML : ''")
    tiles = driver.execute_script("return document.querySelectorAll('.leaflet-tile').length")
    has_map = driver.execute_script("return window.map !== undefined")

    print(f"Map Height: {map_h}")
    print(f"window.map defined: {has_map}")
    print(f"Tile elements count: {tiles}")
    print(f"Inner HTML length: {len(map_inner)}")
except Exception as e:
    print(f"Error: {e}")
driver.quit()
