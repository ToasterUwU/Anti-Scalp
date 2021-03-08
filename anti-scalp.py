import json
import math
import os
import re
import shutil
import sys
import threading
import time
import webbrowser
from difflib import SequenceMatcher
from itertools import cycle
from typing import Callable, Iterable

import playsound
import requests
from bs4 import BeautifulSoup
from PyQt5.QtCore import QRect
from PyQt5.QtWidgets import (QApplication, QCheckBox, QGridLayout, QGroupBox,
                             QLabel, QMessageBox, QPushButton, QWidget)
from selenium import webdriver


class utility():
    def evenly_chunk(items:Iterable, max_chunk_size:int=20):
        chunk_amount = math.ceil(len(items)/max_chunk_size)
        result = [[] for _ in range(chunk_amount)]

        for element, chunk in zip(items, cycle(result)):
            chunk.append(element)
        return result

    def shopname(link:str):
        return link.split("://", 1)[1].split("/", 1)[0].split(".")[1]

    def format_price(price:str):
        price = price.replace("\n", "").replace(",", ".").replace(".–", ".00").replace("\xa0", " ")

        if " " in price:
            chunks = price.split(" ")
            for chunk in chunks:
                floats = re.findall("\d+\.\d+", chunk)
                if floats != []:
                    price = floats[0]
                    break

        return float(price)

class Checker:
    def __init__(self, links:Iterable, return_func:Callable, logging_func:Callable, links_per_instance=20) -> None:
        self.links = links
        self.links_per_instance = links_per_instance
        self.return_func = return_func
        self.logging_func = logging_func
        self.run = False
        self.th_i = 0

    def _get_i(self):
        self.th_i += 1
        return self.th_i

    def stop(self):
        self.run = False

    def log(self, msg:str):
        if self.logging_func:
            self.logging_func(msg)

class Broswer():
    def __init__(self, browser="firefox", max_gets=10, headless=True, bin_path=None, options=None):
        self.browser = browser.lower()
        if self.browser not in ("firefox", "chrome"):
            raise ValueError("browser must be 'firefox' or 'chrome'")

        firefox_failed = False
        chrome_failed = False
        while True:
            if self.browser == "firefox":
                try:
                    self.options = webdriver.firefox.options.Options()
                    self.options.headless = headless
                    if bin_path:
                        self.options.binary_location = bin_path
                    test_driver = webdriver.Firefox(options=self.options)
                except:
                    if not chrome_failed:
                        self.browser = "chrome"
                    else:
                        raise Exception("Neither Firefox or Chrome are installed.")
                else:
                    test_driver.close()
                    break

            else:
                try:
                    self.options = webdriver.chrome.options.Options()
                    self.options.headless = headless
                    if bin_path:
                        self.options.binary_location = bin_path
                    test_driver = webdriver.Chrome(options=self.options)
                except:
                    if not firefox_failed:
                        self.browser = "firefox"
                    else:
                        raise Exception("Neither Firefox or Chrome are installed.")
                else:
                    test_driver.close()
                    break

        if options:
            options.headless = headless
            self.options = options
        else:
            if self.browser == "firefox":
                self.options = webdriver.firefox.options.Options()
                self.options.headless = headless
                if bin_path:
                    self.options.binary_location = bin_path
            else:
                self.options = webdriver.chrome.options.Options()
                self.options.headless = headless
                if bin_path:
                    self.options.binary_location = bin_path

        self.new_driver()
        self.max_gets = max_gets
        self.gets = 0

        with open("selectors.json", "r") as f:
            self.selectors = json.load(f)

    def buyable(self, link):
        shopname = utility.shopname(link)
        if shopname in self.selectors:
            self._get(link)
            result = self._buyable(shopname)
            title = self.driver.title
            self._get("about:blank", count=False)
            return {"result": result, "title": title, "link": link}

    def price(self, link):
        shopname = utility.shopname(link)
        if shopname in self.selectors:
            self._get(link)
            price = self._price(shopname)
            title = self.driver.title
            self._get("about:blank", count=False)
            if price:
                return {"result": price, "title": title, "link": link}

    def buyable_price(self, link:str):
        shopname = utility.shopname(link)
        if shopname in self.selectors:
            self._get(link)
            title = self.driver.title
            if self._buyable(shopname):
                result = self._price(shopname)
                self._get("about:blank", count=False)
                return {"result": result, "title": title, "link": link}

    def new_driver(self):
        if hasattr(self, "driver"):
            if self.driver:
                self.driver.close()

        if self.browser == "firefox":
            profile = webdriver.FirefoxProfile()
            profile.set_preference("permissions.default.image", 2)

            self.driver = webdriver.Firefox(options=self.options, firefox_profile=profile)

        elif self.browser == "chrome":
            chrome_prefs = {}
            chrome_prefs["profile.default_content_settings"] = {"images": 2}
            chrome_prefs["profile.managed_default_content_settings"] = {"images": 2}
            self.options.experimental_options["prefs"] = chrome_prefs

            self.driver = webdriver.Chrome(options=self.options)

    def _get(self, link, count=True):
        if count:
            if self.gets >= self.max_gets:
                self.gets = 0
                self.new_driver()
            self.gets += 1

        self.driver.get(link)
        time.sleep(0.5)

    def _buyable(self, shop):
        selector = self.selectors[shop]["buyable"]
        try:
            self.driver.find_element_by_css_selector(selector)
            return True
        except:
            return False

    def _price(self, shop):
        selector = self.selectors[shop]["price"]
        if "invalid_price" in self.selectors[shop]:
            invalid_price = self.selectors[shop]["invalid_price"]
        else:
            invalid_price = None

        try:
            price = self.driver.find_element_by_css_selector(selector)
            if invalid_price:
                if SequenceMatcher(None, price.text, invalid_price).ratio() >= 0.9:
                    return None
                else:
                    return price.text
            else:
                return price.text
        except:
            return None

    def close(self):
        self.driver.close()

class Selenium_Checker(Checker):
    def __init__(self, links: Iterable, return_func: Callable, logging_func: Callable, links_per_instance:int=20, browser_kwargs:dict={}) -> None:
        super().__init__(links, return_func, logging_func, links_per_instance=links_per_instance)
        self.b_kwargs = browser_kwargs

    def start(self):
        def check_links(links:list):
            b = Broswer(**self.b_kwargs)
            number = self._get_i()
            while self.run:
                if links == []:
                    break

                for link in links:
                    if not self.run:
                        break

                    shopname = utility.shopname(link)
                    if shopname in b.selectors:

                        try:
                            data_dict = b.buyable_price(link)
                        except:
                            continue

                        if data_dict:
                            self.return_func(data_dict)

                    else:
                        links.remove(link)
                        self.log(f"BROWSER-{number}: Removed a {shopname} link. This shop isnt supported. Please add the configuration for {shopname}.")

                if len(links) != 0:
                    self.log(f"BROWSER-{number}: Finished full cycle of {len(links)} links. Re-checking now.")

            b.close()
            if links == []:
                self.log(f"BROWSER-{number}: Closing, no links left.")
            else:
                self.log(f"BROWSER-{number}: Closing.")

        self.run = True
        def start_ths():
            for part_links in utility.evenly_chunk(self.links, self.links_per_instance):
                threading.Thread(name="Browser-Thread", target=check_links, args=[part_links], daemon=True).start()
                time.sleep(5)
        threading.Thread(name="Browser-Starter", target=start_ths, daemon=True).start()

class Requester():
    def __init__(self) -> None:
        with open("selectors.json", "r") as f:
            self.selectors = json.load(f)

    def buyable(self, link):
        shopname = utility.shopname(link)
        if shopname in self.selectors:
            bs, title = self._get(link)
            buyable = self._buyable(bs, shopname)
            return {"result": buyable, "title": title, "link": link}

    def price(self, link):
        shopname = utility.shopname(link)
        if shopname in self.selectors:
            bs, title = self._get(link)
            price = self._price(bs, shopname)
            if price:
                return {"result": price, "title": title, "link": link}

    def buyable_price(self, link):
        shopname = utility.shopname(link)
        if shopname in self.selectors:
            bs, title = self._get(link)
            if self._buyable(bs, shopname):
                price = self._price(bs, shopname)
                return {"result": price, "title": title, "link": link}

    def _get(self, link):
        headers = {'User-Agent': 'Chrome/89.0.4389'} #Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36
        html = requests.get(link, headers=headers)
        bs = BeautifulSoup(html.text, features="html.parser")
        try:
            title = bs.select_one("title").get_text()
        except:
            raise Exception(f"Bot access not allowed on {utility.shopname(link)}")

        return bs, title

    def _buyable(self, bs:BeautifulSoup, shop:str):
        selector = self.selectors[shop]["buyable"]

        element = bs.select_one(selector)
        if element:
            return True
        else:
            return False

    def _price(self, bs:BeautifulSoup, shop:str):
        selector = self.selectors[shop]["price"]

        if "invalid_price" in self.selectors[shop]:
            invalid_price = self.selectors[shop]["invalid_price"]
        else:
            invalid_price = None

        try:
            price = bs.select_one(selector)
            if invalid_price:
                if SequenceMatcher(None, price.get_text(), invalid_price).ratio() >= 0.9:
                    return None

            return price.get_text()
        except:
            return None

class Request_Checker(Checker):
    def start(self):
        def check_links(links:list):
            r = Requester()
            number = self._get_i()
            while self.run:
                if links == []:
                    break

                for link in links:
                    if not self.run:
                        break

                    shopname = utility.shopname(link)
                    if shopname in r.selectors:
                        try:
                            data_dict = r.buyable_price(link)
                        except:
                            links.remove(link)
                            self.log(f"{shopname} doesnt allow bot access. Use Selenium instead of Requests.")
                            continue

                        if data_dict:
                            self.return_func(data_dict)

                    else:
                        links.remove(link)
                        self.log(f"REQUESTS-{number}: Removed a {shopname} link. This shop isnt supported. Please add the configuration for {shopname}.")

                if len(links) != 0:
                    self.log(f"REQUESTS-{number}: Finished full cycle of {len(links)} links. Re-checking now.")

            if links == []:
                self.log(f"REQUESTS-{number}: Closing, no links left.")
            else:
                self.log(f"REQUESTS-{number}: Closing.")

        self.run = True
        for part_links in utility.evenly_chunk(self.links, self.links_per_instance):
            threading.Thread(name="Requester-Thread", target=check_links, args=[part_links], daemon=True).start()

class Link_Getter():
    def __init__(self) -> None:
        self.links = []
        self.regions = []
        self.products = []
        with open("selectors.json", "r") as f:
            self.selectors = json.load(f)

        self.all_links = {}
        for folder in os.listdir("links/"):
            for txt in os.listdir("links/"+folder+"/"):
                with open("links/"+folder+"/"+txt, "r") as f:
                    lines = f.readlines()

                while "\n" in lines:
                    lines.remove("\n")

                lines = [x.replace("\n", "") for x in lines]

                folder = folder.lower()
                if folder not in self.all_links:
                    self.all_links[folder] = {}

                self.all_links[folder][txt.replace(".txt", "").lower()] = lines

    def add_region(self, region:str):
        region = region.lower()

        if region not in self.all_links:
            raise KeyError(f"ERROR: {region.capitalize()} isnt in the saved Regions.")

        elif region not in self.regions:
            self.regions.append(region)

    def add_product(self, product:str):
        product = product.lower()

        all_products = self.all_products()

        if product not in all_products:
            raise KeyError(f"ERROR: {product} isnt in the saved Products.")

        elif product not in self.products:
            self.products.append(product)

    def rm_region(self, region:str):
        region = region.lower()
        while region in self.regions:
            self.regions.remove(region)

    def rm_product(self, product:str):
        product = product.lower()
        while product in self.products:
            self.products.remove(product)

    def clear_regions(self):
        self.regions = []

    def clear_products(self):
        self.products = []

    def clear_all(self):
        self.products = []
        self.regions = []

    def all_regions(self):
        return [x for x in self.all_links]

    def all_products(self):
        all_products = []
        for region in self.all_links:
            for p in self.all_links[region]:
                if p not in all_products:
                    all_products.append(p)
        return all_products

    def get_all_links(self):
        links = []
        for region in self.all_links:
            if region in self.regions:
                for p in self.all_links[region]:
                    if p in self.products:
                        links.extend(self.all_links[region][p])

        return links

    def get_selenium_links(self):
        banned_shops = []
        for shop in self.selectors:
            if self.selectors[shop]["requests"] == True:
                banned_shops.append(shop)

        links = self.get_all_links()

        new_links = []
        for link in links:
            shop = utility.shopname(link)
            if shop not in banned_shops:
                new_links.append(link)

        return new_links

    def get_requests_links(self):
        banned_shops = []
        for shop in self.selectors:
            if self.selectors[shop]["requests"] == False:
                banned_shops.append(shop)

        links = self.get_all_links()

        new_links = []
        for link in links:
            shop = utility.shopname(link)
            if shop not in banned_shops:
                new_links.append(link)

        return new_links

class GUI():
    def __init__(self) -> None:
        self.getter = Link_Getter()

        self.app = QApplication(sys.argv)
        self.msgs = []

    def mainloop(self):
        self.app.exec()

    def play_sound(self):
        mp3_exists = os.path.exists("alert.mp3")
        wav_exists = os.path.exists("alert.wav")
        if not mp3_exists and not wav_exists:
            playsound.playsound("standard_alert.mp3", block=False)
        else:
            if mp3_exists:
                playsound.playsound("alert.mp3", block=False)
            else:
                playsound.playsound("alert.wav", block=False)

    def change_sound():
        filename = fd.askopenfilename(filetypes=[("Sounds", "*.mp3 *.wav")])
        shutil.copy2(filename, "sound."+filename.rsplit(".", 1)[1])

    def reset_sound():
        if os.path.exists("sound.mp3"):
            os.remove("sound.mp3")
        if os.path.exists("sound.wav"):
            os.remove("sound.wav")

    def log(self, msg):
        self.msgs = self.msgs[-9:]
        self.msgs.append(msg)
        self.log_box.setText("\n".join(self.msgs))

    def alert(self, data_dict:dict):
        self.msg_box_var.set(self.msg_box_var.get()+"\n"+f"FOUND {data_dict['title']} -> {data_dict['result']}")
        print(f"FOUND {data_dict['title']} -> {data_dict['result']}")
        self.play_alert()
        webbrowser.open(data_dict["link"])
        self.req_checker.stop()
        self.sel_checker.stop()

    def update_regions(self, garbage):
        self.getter.clear_regions()
        for name, box in self.region_check_boxes.items():
            if box.isChecked():
                self.getter.add_region(name)

    def update_products(self, garbage):
        self.getter.clear_products()
        for name, box in self.product_check_boxes.items():
            if box.isChecked():
                self.getter.add_product(name)

    def btn_function(self):
        if self.start_stop_btn.text() == "Stop":
            self.start_stop_btn.setText("Start")

            self.req_checker.stop()
            self.sel_checker.stop()

        else:
            if self.getter.regions == []:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Critical)
                msg.setWindowTitle("Missing Regions")
                msg.setText("Please select at least one region.")
                msg.exec()
                return

            elif self.getter.products == []:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Critical)
                msg.setWindowTitle("Missing Products")
                msg.setText("Please select at least one product.")
                msg.exec()
                return

            self.start_stop_btn.setText("Stop")

            self.req_checker = Request_Checker(self.getter.get_requests_links(), return_func=gui.alert, logging_func=gui.log)
            self.req_checker.start()

            self.sel_checker = Selenium_Checker(self.getter.get_selenium_links(), return_func=gui.alert, logging_func=gui.log)
            self.sel_checker.start()

    def main_window(self):
        self.main = QWidget()
        self.main.setWindowTitle("Anti Scalp")
        self.main_layout = QGridLayout()

        regions = self.getter.all_regions()
        self.region_box = QGroupBox("Regions")
        self.region_grid = QGridLayout()
        self.region_box.setLayout(self.region_grid)

        row = 0
        self.region_check_boxes = {}
        for r in regions:
            self.region_check_boxes[r] = QCheckBox(text=r.capitalize())
            self.region_check_boxes[r].stateChanged.connect(self.update_regions)
            self.region_grid.addWidget(self.region_check_boxes[r], row, 0)
            self.region_check_boxes[r].show()
            row += 1

        self.main_layout.addWidget(self.region_box, 0, 0)

        self.log_box = QLabel(text="Welcome.\n\nPlease select at least one region\nand one product. After that, press start.")
        self.log_box.setGeometry(QRect(0, 0, 250, 100))
        self.main_layout.addWidget(self.log_box, 0, 1)

        products = self.getter.all_products()
        self.product_box = QGroupBox("Products")
        self.product_grid = QGridLayout()
        self.product_box.setLayout(self.product_grid)

        row = 0
        self.product_check_boxes = {}
        for p in products:
            self.product_check_boxes[p] = QCheckBox(text=p.upper())
            self.product_check_boxes[p].stateChanged.connect(self.update_products)
            self.product_grid.addWidget(self.product_check_boxes[p], row, 0)
            row += 1

        self.main_layout.addWidget(self.product_box, 0, 2)

        self.start_stop_btn = QPushButton(text="Start")
        self.start_stop_btn.clicked.connect(self.btn_function)
        self.main_layout.addWidget(self.start_stop_btn, 1, 1)

        self.main.setLayout(self.main_layout)
        self.main.show()

gui = GUI()

gui.main_window()
gui.mainloop()