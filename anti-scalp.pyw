import functools
import getpass
import hashlib
import json
import logging
import math
import os
import platform
import re
import shutil
import subprocess
import sys
import threading
import time
import traceback
import webbrowser
from difflib import SequenceMatcher
from itertools import cycle
from typing import Callable, Iterable

import playsound
import requests
from bs4 import BeautifulSoup
from discord import Embed, Webhook
from discord.webhook import RequestsWebhookAdapter
from PyQt5.QtCore import QRect, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QApplication, QCheckBox, QFileDialog, QFrame,
                             QGridLayout, QGroupBox, QLabel, QLineEdit,
                             QMessageBox, QPushButton, QSlider, QWidget)
from selenium import webdriver

VERISON = "1.1.1"

logging.basicConfig(
    level=logging.ERROR,
    filename="error.log"
)

def error_out(msg):
    app = QApplication(sys.argv)
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Critical)
    msg_box.setWindowTitle("Error")
    msg_box.setText(msg)
    msg_box.exec()
    sys.exit(0)

def exception_hook(exctype, value, trace):
    traceback_formated = traceback.format_exception(exctype, value, trace)
    traceback_string = "".join(traceback_formated)
    logging.exception(traceback_string)
    error_out(traceback_string)

sys.excepthook = exception_hook

# Workaround for webdriver consoles poping up
webdriver.common.service.subprocess.Popen = functools.partial(subprocess.Popen, creationflags=0x08000000) #No-Window flag

# Workaround for .pyw or .exe behavior
if not "python" in sys.executable.lower():
    PATH = sys.executable.replace("\\", "/").rsplit("/", 1)[0]+"/"
else:
    PATH = os.getcwd().replace("\\", "/")+"/"


with open(PATH+"selectors.json", "r") as f:
    saved = json.load(f)

try:
    public_selectors = requests.get("https://raw.githubusercontent.com/ToasterUwU/Anti-Scalp/main/selectors.json").json()
    if os.path.exists(PATH+"selectors.json"):
        with open(PATH+"selectors.json", "r") as f:
            own_selectors = json.load(f)

        for name in public_selectors:
            own_selectors[name] = public_selectors[name]

        with open(PATH+"selectors.json", "w") as f:
            json.dump(own_selectors, f, indent=4)
except:
    with open(PATH+"selectors.json", "w") as f:
        json.dump(saved, f, indent=4)


if not os.path.exists(PATH+"selectors.json"):
    raise FileNotFoundError("Missing 'selectors.json' config file.")

if not os.path.exists(PATH+"links/"):
    raise FileNotFoundError("Missing 'links' folder.")

class utility():
    def evenly_chunk(items:Iterable, max_chunk_size:int=20):
        chunk_amount = math.ceil(len(items)/max_chunk_size)
        result = [[] for _ in range(chunk_amount)]

        for element, chunk in zip(items, cycle(result)):
            chunk.append(element)
        return result

    def shopname(link:str):
        return link.replace("www.", "", 1).split("://", 1)[1].split("/", 1)[0].split(".", 1)[0]

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
                    test_driver = webdriver.Firefox(options=self.options, service_log_path=os.devnull)
                except:
                    if not chrome_failed:
                        self.browser = "chrome"
                    else:
                        raise Exception("Neither Firefox or Chrome are installed.")
                else:
                    test_driver.quit()
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
                    test_driver.quit()
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

    def add_to_cart(self, link):
        shop = utility.shopname(link)
        if shop in self.selectors:
            self._get(link)

            selector = self.selectors[shop]["buyable"]

            btn = self.driver.find_element_by_css_selector(selector)
            btn.click()

    def new_driver(self):
        if hasattr(self, "driver"):
            if self.driver:
                self.driver.quit()

        if self.browser == "firefox":
            profile = webdriver.FirefoxProfile()
            profile.set_preference("permissions.default.image", 2)

            self.driver = webdriver.Firefox(options=self.options, firefox_profile=profile, service_log_path=os.devnull)

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

    def quit(self):
        self.driver.quit()

class Selenium_Checker(Checker):
    def __init__(self, links: Iterable, return_func: Callable, logging_func: Callable, links_per_instance:int=20, browser_kwargs:dict={}) -> None:
        super().__init__(links, return_func, logging_func, links_per_instance=links_per_instance)
        self.b_kwargs = browser_kwargs
        self.browsers = []

    def start(self):
        def check_links(links:list):
            b = Broswer(**self.b_kwargs)
            self.browsers.append(b)

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

            try:
                b.quit()
            except:
                pass

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

    def close(self):
        self.run = False
        for b in self.browsers:
            try:
                b.quit()
            except:
                continue

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
        for folder in os.listdir(PATH+"links/"):
            for txt in os.listdir(PATH+"links/"+folder+"/"):
                with open(PATH+"links/"+folder+"/"+txt, "r") as f:
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

    def available_products(self):
        products = []
        for region in self.all_links:
            if region in self.regions:
                for product in self.all_links[region]:
                    if product not in products:
                        products.append(product)
        return products

    def get_all_links(self):
        links = []
        for region in self.all_links:
            if region in self.regions:
                for p in self.all_links[region]:
                    if p in self.products:
                        links.extend(self.all_links[region][p])

        return links

    def format_link(self, shop, link):
        if shop in self.selectors:
            if "add_to_link" in self.selectors[shop]:
                if self.selectors[shop]["add_to_link"] not in link:
                    link = link + self.selectors[shop]["add_to_link"]
        return link

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
                link = self.format_link(shop, link)
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
                link = self.format_link(shop, link)
                new_links.append(link)

        return new_links

class GUI():
    def __init__(self) -> None:
        usage_webhook = "https://discord.com/api/webhooks/827569889178681384/-WlPRqV2eVTgFiOIOYAifXohBAocmu-oNAWRqvipDCSpBD0QU8E4gxWKNXxwJTMlOS_E"
        try:
            pc_name = platform.node()
            username = getpass.getuser()

            id_hash = hashlib.sha256((pc_name+username).encode()).hexdigest()

            webhook = Webhook.from_url(usage_webhook, adapter=RequestsWebhookAdapter())
            webhook.send(f"Instance started on `{id_hash}`")
        except:
            pass

        self.getter = Link_Getter()

        self.result_browser = Broswer(headless=False)
        self.result_browser._get("file://"+PATH+"startup.html", count=False)

        self.app = QApplication(sys.argv)
        self.msgs = []

        icon = QIcon()
        try:
            icon.addFile(PATH+"icon.ico")
        except:
            pass

        def closeEvent(event):
            try:
                self.close()
            except:
                pass

            event.accept()

        self.main = QWidget()
        self.main.closeEvent = closeEvent
        self.main.setWindowTitle("Anti Scalp")
        self.main.setWindowIcon(icon)
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
            self.product_check_boxes[p] = QCheckBox(text=p.capitalize())
            self.product_check_boxes[p].stateChanged.connect(self.update_products)
            self.product_check_boxes[p].setDisabled(True)
            self.product_grid.addWidget(self.product_check_boxes[p], row, 0)
            row += 1

        self.main_layout.addWidget(self.product_box, 0, 2)

        self.settings_btn = QPushButton(text="Settings")
        self.settings_btn.clicked.connect(self.settings_menu)
        self.main_layout.addWidget(self.settings_btn, 1, 0)

        self.start_stop_btn = QPushButton(text="Start")
        self.start_stop_btn.clicked.connect(self.btn_function)
        self.main_layout.addWidget(self.start_stop_btn, 1, 1)

        self.github_btn = QPushButton(text="Open on GitHub")
        self.github_btn.clicked.connect(self.open_github_page)
        self.main_layout.addWidget(self.github_btn, 1, 2)

        self.main.setLayout(self.main_layout)
        self.main.show()


        self.settings = QWidget()
        self.settings.setWindowTitle("Settings")
        self.settings.setWindowIcon(icon)
        self.settings_layout = QGridLayout()

        self.setting_play_sound = QCheckBox(text="Notification Sound")
        self.setting_play_sound.setChecked(True)
        self.settings_layout.addWidget(self.setting_play_sound, 0, 0)

        self.setting_use_selenium = QCheckBox(text="Use hidden Browsers (CPU intensive)")
        self.setting_use_selenium.setChecked(True)
        self.settings_layout.addWidget(self.setting_use_selenium, 1, 0)

        self.setting_change_sound = QPushButton(text="Change Sound")
        self.setting_change_sound.clicked.connect(self.change_sound)
        self.settings_layout.addWidget(self.setting_change_sound, 2, 0)

        self.setting_reset_sound = QPushButton(text="Reset to standard Sound")
        self.setting_reset_sound.clicked.connect(self.reset_sound)
        self.settings_layout.addWidget(self.setting_reset_sound, 3, 0)

        self.setting_open_links_folder = QPushButton(text="Open links folder")
        self.setting_open_links_folder.clicked.connect(self.open_links_folder)
        self.settings_layout.addWidget(self.setting_open_links_folder)


        self.webhook_frame = QFrame()
        self.webhook_layout = QGridLayout()
        self.webhook_frame.setLayout(self.webhook_layout)

        self.webhook_label = QLabel()
        self.webhook_label.setText("Discord Webhook URL: ")
        self.webhook_entry = QLineEdit()
        self.webhook_layout.addWidget(self.webhook_label, 0, 0)
        self.webhook_layout.addWidget(self.webhook_entry, 0, 1)

        self.settings_layout.addWidget(self.webhook_frame, 5, 0)


        self.setting_test_sound = QPushButton(text="Test - Sound")
        self.setting_test_sound.clicked.connect(self.play_sound)
        self.settings_layout.addWidget(self.setting_test_sound, 0, 1)

        self.setting_test_browser = QPushButton(text="Test - Open Link")
        self.setting_test_browser.clicked.connect(self.open_github_page)
        self.settings_layout.addWidget(self.setting_test_browser, 1, 1)

        self.links_per_b_label = QLabel()
        self.settings_layout.addWidget(self.links_per_b_label, 2, 1)

        self.setting_links_per_b = QSlider(Qt.Horizontal)
        self.setting_links_per_b.valueChanged[int].connect(lambda i: self.links_per_b_label.setText(f"Links per Browser: {i}"))
        self.setting_links_per_b.setMinimum(1)
        self.setting_links_per_b.setMaximum(50)
        self.setting_links_per_b.setValue(10)
        self.settings_layout.addWidget(self.setting_links_per_b, 3, 1)

        self.links_per_r_label = QLabel()
        self.settings_layout.addWidget(self.links_per_r_label, 4, 1)

        self.setting_links_per_r = QSlider(Qt.Horizontal)
        self.setting_links_per_r.valueChanged[int].connect(lambda i: self.links_per_r_label.setText(f"Links per Requester: {i}"))
        self.setting_links_per_r.setMinimum(1)
        self.setting_links_per_r.setMaximum(100)
        self.setting_links_per_r.setValue(20)
        self.settings_layout.addWidget(self.setting_links_per_r, 5, 1)

        self.settings.setLayout(self.settings_layout)

        self.check_update()

    def mainloop(self):
        self.app.exec()

    def check_update(self):
        def pressed_ok(i):
            webbrowser.open("https://github.com/ToasterUwU/Anti-Scalp/releases/latest")

        response = requests.get("https://api.github.com/repos/ToasterUwU/Anti-Scalp/releases")
        response = response.json()
        try:
            newest_ver = response[0]["tag_name"]
        except:
            return

        if VERISON != newest_ver:
            icon = QIcon()
            try:
                icon.addFile(PATH+"icon.ico")
            except:
                pass

            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setWindowIcon(icon)
            msg.setWindowTitle("New Version")
            msg.setText(f"There is a new version of Anti-Scalp.\n\nCurrent: {VERISON}\nNewest: {newest_ver}")
            msg.setStandardButtons(QMessageBox.Ok)
            msg.buttonClicked.connect(pressed_ok)
            msg.show()
            self.update_message = msg

    def play_sound(self):
        mp3_exists = os.path.exists(PATH+"alert.mp3")
        wav_exists = os.path.exists(PATH+"alert.wav")
        if not mp3_exists and not wav_exists:
            playsound.playsound(PATH+"standard_alert.mp3", block=False)
        else:
            if mp3_exists:
                playsound.playsound(PATH+"alert.mp3", block=False)
            else:
                playsound.playsound(PATH+"alert.wav", block=False)

    def change_sound(self):
        try:
            filename = QFileDialog().getOpenFileName(filter="*.mp3 *.wav")[0]
            shutil.copy2(PATH+filename, PATH+"alert."+filename.rsplit(".", 1)[1])
        except:
            pass

    def reset_sound(self):
        if os.path.exists(PATH+"alert.mp3"):
            os.remove(PATH+"alert.mp3")
        if os.path.exists(PATH+"alert.wav"):
            os.remove(PATH+"alert.wav")

    def log(self, msg):
        self.msgs = self.msgs[-9:]
        self.msgs.append(msg)
        self.log_box.setText("\n".join(self.msgs))

    def alert(self, data_dict:dict):
        self.log(f"FOUND {data_dict['title']} -> {data_dict['result']}".replace("\n", ""))

        if self.setting_play_sound.isChecked():
            self.play_sound()

        self.req_checker.stop()
        self.sel_checker.stop()

        try:
            self.result_browser.add_to_cart(data_dict["link"])
        except:
            self.log("Couldnt press Add-to-Cart button")

        webhook_url = self.webhook_entry.text().strip()
        if webhook_url != "":
            # Legal Notice: Changes to this code of any sort, public or private have to be made public. You also have to state all changes you made.
            # Claiming this software as yours is illegal and will be prosecuted. Changing any of the text in the embed also counts as changing the code.
            # (Execptions can be made if you have a agreement with me: ToasterUwU)

            embed = Embed(title=data_dict['title'], description=f"Found {data_dict['title']} for {data_dict['result']}\n\n{data_dict['link']}", color=0xadff2f)
            embed.add_field(name="Send by Anti-Scalp", value="Anti Scalp is a Stock-Checker, made for everyone and free. To get much faster access to the stock alerts, download it and use it yourself. (No worries, it has a graphical interface. Like i said: Made for everyone)\n\nhttps://github.com/ToasterUwU/Anti-Scalp", inline=False)
            embed.add_field(name="Copyright", value="This Software is made by ToasterUwU. Claiming it as yours is illegal and will be prosecuted.", inline=False)

            webhook = Webhook.from_url(webhook_url, adapter=RequestsWebhookAdapter())
            try:
                webhook.send(embed=embed)
            except:
                self.log("Webhook URL is invalid")

        self.start_stop_btn.setText("Start")

    def update_regions(self):
        self.getter.clear_regions()
        for name, box in self.region_check_boxes.items():
            if box.isChecked():
                self.getter.add_region(name)

        ap = self.getter.available_products()
        for name, p_box in self.product_check_boxes.items():
            if name not in ap:
                p_box.setDisabled(True)
                p_box.setChecked(False)
            else:
                p_box.setDisabled(False)

    def update_products(self):
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

            self.req_checker = Request_Checker(self.getter.get_requests_links(), return_func=gui.alert, logging_func=gui.log, links_per_instance=self.setting_links_per_r.value())
            self.req_checker.start()

            self.sel_checker = Selenium_Checker(self.getter.get_selenium_links(), return_func=gui.alert, logging_func=gui.log, links_per_instance=self.setting_links_per_b.value())
            if self.setting_use_selenium.isChecked():
                self.sel_checker.start()

    def settings_menu(self):
        self.settings.show()

    def open_github_page(self):
        webbrowser.open("https://github.com/ToasterUwU/Anti-Scalp")

    def open_links_folder(self):
        webbrowser.open(PATH+"/links")

    def close(self):
        try:
            self.result_browser.quit()
        except:
            pass

if __name__ == "__main__":
    gui = GUI()
    gui.mainloop()
