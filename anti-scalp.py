import json
import math
import os
import re
import shutil
import threading
import time
import webbrowser
from difflib import SequenceMatcher
from itertools import cycle
from tkinter import filedialog as fd
from tkinter.ttk import *
from typing import Callable, Iterable

import playsound
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from ttkthemes import ThemedTk

tk = ThemedTk(theme="arc")
tk.minsize(width=300, height=150)
tk.title("Anti Scalp")


class utility():
    def evenly_chunk(items:Iterable, max_chunk_size:int=20):
        chunk_amount = math.ceil(len(items)/20)
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
        def check_links(checker:Selenium_Checker, links:list):
            b = Broswer(**checker.b_kwargs)
            number = checker._get_i()
            while checker.run:
                if links == []:
                    break

                for link in links:
                    if not checker.run:
                        break

                    shopname = utility.shopname(link)
                    if shopname in checker.selectors:

                        data_dict = b.buyable_price(link)
                        checker.return_func(data_dict)

                    else:
                        links.remove(link)
                        checker.log(f"BROWSER-{number}: Removed a {shopname} link. This shop isnt supported. Please add the configuration for {shopname}.")

                if len(links) != 0:
                    checker.log(f"BROWSER-{number}: Finished full cycle of {len(links)} links. Re-checking now.")

            b.close()
            checker.log(f"BROWSER-{number}: Closing, no links left.")

        self.run = True
        for part_links in utility.evenly_chunk(self.links, self.links_per_instance):
            threading.Thread(name="Browser-Thread", target=check_links, args=[self, part_links], daemon=True).start()
            time.sleep(5)
            tk.update()
            tk.update_idletasks()

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
        def check_links(checker:Request_Checker, links:list):
            r = Requester()
            while checker.run:
                for link in links:
                    shopname = utility.shopname(link)
                    if shopname in r.selectors:
                        try:
                            data_dict = r.buyable_price(link)
                        except:
                            links.remove(link)
                            checker.log(f"{shopname} doesnt allow bot access. Use Selenium instead of Requests.")
                            continue

                        if data_dict:
                            checker.return_func(data_dict)

                    else:
                        links.remove(link)
                        checker.log(f"REQUESTS: Removed a {shopname} link. This shop isnt supported. Please add the configuration for {shopname}.")

                if len(links) != 0:
                    checker.log(f"REQUESTS: Finished full cycle of {len(links)} links. Re-checking now.")

        self.run = True
        for part_links in utility.evenly_chunk(self.links, self.links_per_instance):
            threading.Thread(name="Browser-Thread", target=check_links, args=[self, part_links], daemon=True).start()

class Requests_Checker():
    def __init__(self, links:Iterable, return_func:Callable, logging_func:Callable) -> None:
        self.links = links
        self.return_func = return_func
        self.logging_func = logging_func
        self.run = False

        with open("selectors.json", "r") as f:
            self.selectors = json.load(f)

    def start(self):
        def check_links(checker:Requests_Checker, links:list):
            if len(links) >= 30:
                wait = 2*len(links)
            else:
                wait = 60/len(links)

            while checker.run:
                for link in links:
                    shopname = utility.shopname(link)
                    if shopname in checker.selectors:
                        bs, title = checker.get(link)
                        if not bs:
                            links.remove(link)
                            checker.log(f"{utility.shopname(link)} doesnt allow bot access. Use Selenium instead of Requests.")
                            continue

                        if checker.buyable(bs, shopname):
                            result = checker.price(bs, shopname)
                            if result:
                                checker.return_func({"result": result, "title": title, "link": link, "unsupported": False})
                    else:
                        links.remove(link)
                        checker.log(f"REQUESTS: Removed a {utility.shopname(link)} link. This shop isnt supported. Please add the configuration for {utility.shopname(link)}.")

                    time.sleep(wait)

                if len(links) != 0:
                    checker.log(f"REQUESTS: Finished full cycle of {len(links)} links. Re-checking now.")

        self.run = True
        threading.Thread(name="Requests-Thread", target=check_links, args=[self, self.links], daemon=True).start()

    def stop(self):
        self.run = False

    def log(self, msg:str):
        if self.logging_func:
            self.logging_func(msg)

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

    def get_shopname(self, link:str):
        return link.split("://", 1)[1].split("/", 1)[0].split(".")[1]

    def add_region(self, region:str):
        region = region.lower()

        if region not in self.all_links:
            raise KeyError(f"ERROR: {region.capitalize()} isnt in the saved Regions.")

        elif region not in self.regions:
            self.regions.append(region)

    def add_product(self, product:str):
        product = product.lower()

        all_products = []
        for region in self.all_links:
            for p in self.all_links[region]:
                if p not in all_products:
                    all_products.append(p)

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


def play_alert():
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

def alert(data_dict:dict):
    print(f"FOUND {data_dict['title']} -> {data_dict['result']}")
    play_alert()
    webbrowser.open(data_dict["link"])
    req_checker.stop()
    sel_checker.stop()


getter = Link_Getter()
getter.add_region("Germany")
getter.add_product("RTX 3060")
getter.add_product("RTX 3060 TI")

r = Requester()
b = Broswer()

for link in getter.get_requests_links():
    data = r.price(link)
    if data:
        print(utility.format_price(data["result"]))

for link in getter.get_selenium_links():
    data = b.price(link)
    if data:
        print(utility.format_price(data["result"]))

req_checker = Request_Checker(getter.get_requests_links(), return_func=alert, logging_func=lambda msg: print(msg))
req_checker.start()

sel_checker = Selenium_Checker(getter.get_selenium_links(), return_func=alert, logging_func=lambda msg: print(msg))
sel_checker.start()

tk.mainloop()