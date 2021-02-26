from tkinter.ttk import *
from typing import Union

from selenium import webdriver
from ttkthemes import ThemedTk

tk = ThemedTk(theme="arc")
tk.minsize(width=300, height=150)
tk.title("Anti Scalp")

f = Frame(tk)
f.grid()

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

    def new_driver(self):
        if hasattr(self, "driver"):
            if self.driver:
                self.driver.close()

        if self.browser == "firefox":
            self.driver = webdriver.Firefox(options=self.options)
        elif self.browser == "chrome":
            self.driver = webdriver.Chrome(options=self.options)

    def get(self, url):
        if self.gets >= self.max_gets:
            self.gets = 0
            self.new_driver()

        self.driver.get(url)
        self.gets += 1

    def get_amazon_price(self, link:str) -> Union[str, None]:
        self.get(link)
        try:
            self.driver.find_element_by_id("add-to-cart-button")
            try:
                price = self.driver.find_element_by_id("price_inside_buybox")
                return price.text
            except:
                return None
        except:
            return None

    def close(self):
        self.driver.close()

b = Broswer()

tk.mainloop()
b.close()