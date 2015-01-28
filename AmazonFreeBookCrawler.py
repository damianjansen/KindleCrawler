#! python
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import sys, getopt, time, signal
import psutil

#
# I DO NOT TAKE ANY RESPONSIBILITY FOR MONEY, TIME OR OTHERWISE LOST IN
# THE USE / ABUSE OF THIS SCRIPT
# Requires chrome, chromedriver, psutil
global driver, amazonsite, username, password, amazonUrl, genre, reducedOnly, freeEnded, pageNum, categories, categoryDict, maxPages
amazonUrl = "https://www.amazon.com"
maxPages = 400

def parse_options(argv):
    global username, password, amazonsite, amazonUrl, genre, reducedOnly, categories
    reducedOnly = False
    try:
        opts, args = getopt.getopt(argv,"g:u:p:c:r",[])
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-g':
            categories = arg.split(';')
        elif opt == '-u':
            username = arg
        elif opt == '-p':
            password = arg
        elif opt == '-r':
            reducedOnly = True
        elif opt == '-c':
            if arg != 'us' and arg != 'au':
                usage()
                sys.exit(2)
            amazonsite = arg
            if arg != 'us':
                amazonUrl = amazonUrl + '.' + arg

def usage():
    print 'AmazonFreeBookCrawler.py -g "<all || genre;genre;...>" -u <amazonusername> -p <amazonpassword> -c <amazoncountry(us|au)>'

def signal_handler(signal, frame):
        print('\nCtrl+C pressed, forcefully closing.\n')
        tearDown()
        sys.exit(0)

def validate_selected_categories(categoryDict):
    driver.get(amazonUrl + "/gp/search/ref=sr_hi_2?rh=n%3A133140011%2Cn%3A%21133141011%2Cn%3A154606011&bbn=154606011")
    driver.find_element_by_id('ref_154606011')
    for genre in categories:
        if genre not in categoryDict:
            print(genre + ' not available. Valid categories:')
            print(categoryDict.keys())
            exit(1)

# Prevent any other chromedrivers from interfering
def kill_chrome_drivers():
    PROCNAME = "chromedriver"
    for proc in psutil.process_iter():
        if proc.name == PROCNAME:
            print("Kill " + proc.name + "(" + str(proc.pid) + ")")
            proc.kill()

def setUp():
    validate(username != '', 'Username is empty')
    validate(password != '', 'Password is empty')
    global driver
    driver = webdriver.Chrome()

def tearDown():
    driver.close()
    driver.quit()

def main(argv):
    global categories
    signal.signal(signal.SIGINT, signal_handler)
    kill_chrome_drivers()
    parse_options(argv)
    setUp()
    availableCategories = getCategories()
    if categories[0] == "all":
        categories = availableCategories.keys()
        print("Selecting all categories")
    validate_selected_categories(availableCategories)
    signInToAmazon()
    for category in categories:
        print(availableCategories.get(category))
        buy_books(availableCategories.get(category)+'&page=')
    tearDown()

# Get the available categories from the site
def getCategories():
    catarray = {}
    driver.get("http://www.amazon.com/gp/search/ref=sr_hi_2?rh=n%3A133140011%2Cn%3A%21133141011%2Cn%3A154606011&bbn=154606011&sort=price-asc-rank")
    listitems = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'ref_154606011'))).find_elements_by_tag_name('li')
    for listitem in listitems:
        if len(listitem.find_elements_by_class_name('refinementLink')) > 0:
            name = listitem.find_element_by_class_name('refinementLink').text
            link = listitem.find_element_by_tag_name('a').get_attribute('href')
            catarray[name] = link
    return catarray

# Sign in to Amazon and check
def signInToAmazon():
    print('Log in to ' + amazonUrl)
    driver.get(amazonUrl)
    driver.find_element_by_id('nav-your-account').click()
    driver.find_element_by_id('ap_email').send_keys(username)
    driver.find_element_by_id('ap_password').send_keys(password)
    driver.find_element_by_id('signInSubmit-input').click()
    validate(WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'nav-signin-text'))).text != 'Sign in', 'Amazon sign in failed')

# Get the list of URLs from the pages
def buy_books(baseUrl):
    pageNum = 1
    print "Find links"
    while paginate(pageNum, baseUrl):
        pageNum = pageNum + 1
        iterateBooks(getBookLinks())

# Get the links for books from the page
def getBookLinks():
    urls = []
    listtable = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 's-results-list-atf'))).find_elements_by_class_name('s-result-item')
    for element in listtable:
        urls.append(element.find_element_by_class_name('s-access-detail-page').get_attribute('href'))
    return urls

def paginate(pageNum, baseUrl):
    # Make this better by checking for non-free books
    if pageNum < 400:
        driver.get(baseUrl+str(pageNum))
        return True
    return False

# Iterate through the given list of book links
def iterateBooks(listUrls):
    print(str(len(listUrls)) + ' books found')
    for url in listUrls:
        buyBookIfFree(url)

# Check if the item is free and not previously purchased, commit
def buyBookIfFree(url):
    driver.get(url)
    booktitle = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'btAsinTitle'))).text.strip()
    if reducedOnly and len(driver.find_elements_by_class_name('listPrice')) <= 0:
        print 'Skip normally free' + booktitle
        return
    if alreadyBought():
        print 'Already bought ' + booktitle
        return
    if not isBookFree():
        print booktitle + ' is NOT free'
        return
    print 'Buying ' + booktitle
    time.sleep(1)
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'buyButton')))
    time.sleep(1)
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'buyButton'))).click()

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

