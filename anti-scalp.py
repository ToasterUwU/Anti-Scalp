import json
import os
import shutil
import threading
import time
import webbrowser
from difflib import SequenceMatcher
from tkinter import filedialog as fd
from tkinter.ttk import *
from typing import Callable

import playsound
from selenium import webdriver
from ttkthemes import ThemedTk

tk = ThemedTk(theme="arc")
tk.minsize(width=300, height=150)
tk.title("Anti Scalp")


class Broswer():
    def __init__(self, browser="firefox", max_gets=10, headless=True, bin_path=None, options=None):
        self.browser = browser.lower()
        if self.browser not in ("firefox", "chromium"):
            raise ValueError("browser must be 'firefox' or 'chromium'")

        if options:
            options.headless = headless
            self.options = options
        else:
            if browser == "firefox":
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

        with open("data/selectors.json", "r") as f:
            self.selectors = json.load(f)

    def new_driver(self):
        if hasattr(self, "driver"):
            if self.driver:
                self.driver.close()

        if self.browser == "firefox":
            self.driver = webdriver.Firefox(options=self.options)
        elif self.browser == "chrome":
            self.driver = webdriver.Chrome(options=self.options)

    def get(self, url, count=True):
        if count:
            if self.gets >= self.max_gets:
                self.gets = 0
                self.new_driver()
            self.gets += 1

        self.driver.get(url)
        time.sleep(0.5)

    def get_shopname(self, url:str):
        return url.split("://", 1)[1].split("/", 1)[0].split(".")[1]

    def get_buyable(self, url):
        shopname = self.get_shopname(url)
        if shopname in self.selectors:
            self.get(url)
            result = self._buyable(shopname)
            title = self.driver.title
            self.get("about:blank", count=False)
            return {"result": result, "title": title, "url": url}
        else:
            return {"result": None, "title": None, "url": None}

    def get_price(self, url):
        shopname = self.get_shopname(url)
        if shopname in self.selectors:
            self.get(url)
            result = self._price(shopname)
            title = self.driver.title
            self.get("about:blank", count=False)
            return {"result": result, "title": title, "url": url}
        else:
            return {"result": None, "title": None, "url": None}

    def get_buyable_price(self, url:str):
        shopname = self.get_shopname(url)
        if shopname in self.selectors:
            self.get(url)
            title = self.driver.title
            if self._buyable(shopname):
                result = self._price(shopname)
                self.get("about:blank", count=False)
                return {"result": result, "title": title, "url": url}
            else:
                return {"result": None, "title": title, "url": url}

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

class Link_Checker():
    def __init__(self, links:list, return_func:Callable, browser_kwargs:dict={}, links_per_browser=10) -> None:
        self.l_per_b = links_per_browser
        self.links = links
        self.return_func = return_func
        self.b_kwargs = browser_kwargs
        self.run = False

    def start(self):
        def check_links(checker, links):
            b = Broswer(**checker.b_kwargs)
            while checker.run:
                for link in links:
                    if not checker.run:
                        break

                    price = b.get_price(link)
                    if price["result"]:
                        self.return_func(price)

        self.run = True
        for part_links in chunk_list(self.links, self.l_per_b):
            threading.Thread(target=check_links, args=[self, part_links], daemon=True).start()
            time.sleep(1)
            tk.update()
            tk.update_idletasks()

    def stop(self):
        self.run = False

class Link_Getter():
    def __init__(self) -> None:
        self.links = []
        self.regions = []
        self.products = []

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

        with open("data/links.json", "w+") as f:
            json.dump(self.all_links, f, indent=4)

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

    def get_links(self):
        links = []
        for region in self.all_links:
            if region in self.regions:
                for p in self.all_links[region]:
                    if p in self.products:
                        links.extend(self.all_links[region][p])

        return links


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

def chunk_list(data, chunk_size):
    for i in range(0, len(data), chunk_size):
        yield data[i:i+chunk_size]

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
    webbrowser.get().open(data_dict["url"])
    checker.stop()

getter = Link_Getter()
getter.add_region("germany")
getter.add_product("RTX 3060")
checker = Link_Checker(getter.get_links(), return_func=alert)
checker.start()

tk.mainloop()