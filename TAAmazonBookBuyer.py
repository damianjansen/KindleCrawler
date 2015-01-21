#! python
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import sys, getopt
import psutil

#
# I DO NOT TAKE ANY RESPONSIBILITY FOR MONEY, TIME OR OTHERWISE LOST IN
# THE USE / ABUSE OF THIS SCRIPT
# Requires chrome, chromedriver, psutil
global ozbargainurl, amazonsite, amazonuser, amazonpass, amazonloginbase
amazonloginbase = "https://www.amazon.com"

global driver

def parseOptions(argv):
    global ozbargainurl, amazonuser, amazonpass, amazonsite, amazonloginbase
    try:
        opts, args = getopt.getopt(argv,"d:u:p:c:",[])
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-d':
            ozbargainurl = "https://www.ozbargain.com.au/node/" + arg
        elif opt == '-u':
            amazonuser = arg
        elif opt == '-p':
            amazonpass = arg
        elif opt == '-c':
            if arg != 'us' and arg != 'au':
                usage()
                sys.exit(2)
            amazonsite = arg
            if arg != 'us':
                amazonloginbase = amazonloginbase + '.' + arg

def usage():
    print 'TAAmazonBookBuyer.py -d <dealID> -u <amazonusername> -p <amazonpassword> -c <amazoncountry(us|au)>'

# Prevent any other chromedrivers from interfering
def killChromeDrivers():
    PROCNAME = "chromedriver"
    for proc in psutil.process_iter():
        if proc.name == PROCNAME:
            print("Kill " + proc.name + "(" + str(proc.pid) + ")")
            proc.kill()

def setUp():
    validate(amazonuser != '', 'Username is empty')
    validate(amazonpass != '', 'Password is empty')
    validate(ozbargainurl != '', 'Deal URL is empty')
    global driver
    driver = webdriver.Chrome()

def tearDown():
    driver.close()

def main(argv):
    killChromeDrivers()
    parseOptions(argv)
    setUp()
    signInToAmazon()
    print('Access ' + ozbargainurl)
    driver.get(ozbargainurl)
    iterateBooks(getUrls())
    tearDown()

# Sign in to Amazon and check
def signInToAmazon():
    print('Log in to ' + amazonloginbase)
    driver.get(amazonloginbase)
    driver.find_element_by_id('nav-your-account').click()
    driver.find_element_by_id('ap_email').send_keys(amazonuser)
    driver.find_element_by_id('ap_password').send_keys(amazonpass)
    driver.find_element_by_id('signInSubmit-input').click()
    validate(WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'nav-signin-text'))).text != 'Sign in', 'Amazon sign in failed')

# Get the list of URLs from the deal
def getUrls():
    urls = []
    for element in driver.find_elements_by_link_text(amazonsite):
        urls.append(element.get_attribute('href'))
    return urls

# Iterate through the given list of book links
def iterateBooks(listUrls):
    print(str(len(listUrls)) + ' books found')
    for url in listUrls:
        buyBookIfFree(url)

# Check if the item is free and not previously purchased, commit
def buyBookIfFree(url):
    driver.get(url)
    booktitle = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'btAsinTitle'))).text.strip()
    if alreadyBought():
        print 'Already bought ' + booktitle
        return
    if not isBookFree():
        print booktitle + ' is NOT free'
        return
    print 'Buying ' + booktitle
    driver.find_element_by_id('buyButton').click()

# Check if book is free
def isBookFree():
    priceLarge = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'priceLarge')))
    if priceLarge.text.strip() != '$0.00':
        return False
    return True

# Check if already purchased
def alreadyBought():
    divs = driver.find_elements_by_class_name('iou_div')
    for element in divs:
        if 'You purchased' in element.text:
            return True
    return False

def validate(condition, message):
    if not condition:
        print('Script failed for ' + message)
        sys.exit(1)

if __name__ == '__main__':
    main(sys.argv[1:])

