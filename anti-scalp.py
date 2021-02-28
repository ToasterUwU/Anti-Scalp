import json
import os
import time
import webbrowser
from difflib import SequenceMatcher
from tkinter.ttk import *

import playsound
from selenium import webdriver
from ttkthemes import ThemedTk

tk = ThemedTk(theme="arc")
tk.minsize(width=300, height=150)
tk.title("Anti Scalp")


class Broswer():
    def __init__(self, browser="firefox", max_gets=10, headless=True, options=None):
        self.browser = browser.lower()
        if self.browser not in ("firefox", "chrome"):
            raise ValueError("browser must be 'firefox' or 'chrome'")

        if options:
            options.headless = headless
            self.options = options
        else:
            if browser == "firefox":
                self.options = webdriver.firefox.options.Options()
                self.options.headless = headless
            else:
                self.options = webdriver.chrome.options.Options()
                self.options.headless = headless

        self.new_driver()
        self.max_gets = max_gets
        self.gets = 0

        with open("data/links.json", "r") as f:
            self.links = json.load(f)

        with open("data/selectors.json", "r") as f:
            self.selectors = json.load(f)

    def update_links(self):
        json_data = {}
        for folder in os.listdir("links/"):
            for txt in os.listdir("links/"+folder+"/"):
                with open("links/"+folder+"/"+txt, "r") as f:
                    lines = f.readlines()

                while "\n" in lines:
                    lines.remove("\n")

                lines = [x.replace("\n", "") for x in lines]

                if folder not in json_data:
                    json_data[folder] = {}

                json_data[folder][txt.replace(".txt", "")] = lines

        with open("data/links.json", "w+") as f:
            json.dump(json_data, f, indent=4)

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
            self.get("about:blank", count=False)
            return result

    def get_price(self, url):
        shopname = self.get_shopname(url)
        if shopname in self.selectors:
            self.get(url)
            result = self._price(shopname)
            self.get("about:blank", count=False)
            return result

    def get_buyable_price(self, url:str):
        shopname = self.get_shopname(url)
        if shopname in self.selectors:
            self.get(url)
            if self._buyable(shopname):
                result = self._price(shopname)
                self.get("about:blank", count=False)
                return result

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

b = Broswer()

for region in b.links:
    for product in b.links[region]:
        for url in b.links[region][product]:
            price = b.get_price(url)
            print(price)

# tk.mainloop()
b.close()