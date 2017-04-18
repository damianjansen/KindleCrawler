#! python
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import sys, getopt, time, signal, codecs, traceback
global psutilavailable

try:
    import psutil
    psutilavailable = True
except ImportError:
    psutilavailable = False
    print "Failed to find psutil - kill chromedriver manually!"

#
# I DO NOT TAKE ANY RESPONSIBILITY FOR MONEY, TIME OR OTHERWISE LOST IN
# THE USE / ABUSE OF THIS SCRIPT
# Requires chrome, chromedriver, psutil
global driver, amazonsite, username, password, amazonUrl, genre, reducedOnly, freeEnded, pageNum, categories, categoryDict, maxPages, memfile, alternateDevice,driverpath
amazonUrl = "https://www.amazon.com"
maxPages = 400
memory = {}
alternateDevice = ''
driverpath = "chromedriver"
# Parse the options from the command line
def parse_options(argv):
    global username, password, amazonsite, amazonUrl, genre, reducedOnly, categories, alternateDevice, memfile,driverpath
    reducedOnly = False
    try:
        opts, args = getopt.getopt(argv,"g:u:p:c:d:rm:e:",[])
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
        elif opt == '-d':
            alternateDevice = arg
        elif opt == '-m':
            memfile = arg
        elif opt == '-c':
            if arg != 'us' and arg != 'au':
                usage()
                sys.exit(2)
            amazonsite = arg
            if arg != 'us':
                amazonUrl = amazonUrl + '.' + arg
        elif opt == "-e":
            driverpath = arg + '/' + driverpath

# Print usage and exit
def usage():
    print 'AmazonFreeBookCrawler.py -g "<all || genre;genre;...>" -u <amazonusername> -p <amazonpassword> -c <amazoncountry(us|au)>'

# Handle Ctrl+C
def signal_handler(signal, frame):
        print('\nCtrl+C pressed, forcefully closing.\n')
        tearDown()
        sys.exit(0)

# Ensure the categories selected by the user exist
def validate_selected_categories(categoryDict):
    driver.get(amazonUrl + "/gp/search/ref=sr_hi_2?rh=n%3A133140011%2Cn%3A%21133141011%2Cn%3A154606011&bbn=154606011")
    driver.find_element_by_id('ref_154606011')
    for genre in categories:
        if genre not in categoryDict:
            safe_print(genre + ' not available. Valid categories:')
            print(categoryDict.keys())
            exit(1)

# Prevent any other chromedrivers from interfering
def kill_chrome_drivers():
    if not psutilavailable:
        return
    PROCNAME = "chromedriver"
    for proc in psutil.process_iter():
        if proc.name == PROCNAME:
            print("Kill " + proc.name + "(" + str(proc.pid) + ")")
            proc.kill()

# Get driver, memory and auth set up
def setUp():
    global memory, memfile
    validate(username != '', 'Username is empty')
    validate(password != '', 'Password is empty')
    if memfile:
        fileread = open(memfile, 'r')
        for line in fileread:
            title = line.split('||')[0]
            url = line.split('||')[1]
            memory[title] = url
        fileread.close()
        print('Found ' + str(len(memory.keys())) + ' books in memory')
    global driver
    chromeOptions = webdriver.ChromeOptions()
    chromeOptions.add_experimental_option("prefs", {'profile.managed_default_content_settings.images': 2})
    driver = webdriver.Chrome(executable_path=driverpath,port=4444,chrome_options=chromeOptions)


# Shut down cleanly
def tearDown():
    driver.close()
    driver.quit()

# Go!
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
        print("Categories " + str(categories))
    validate_selected_categories(availableCategories)
    signInToAmazon()
    for category in categories:
        print("Trawling category " + category)
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
    #WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'nav-your-account'))).click()
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.LINK_TEXT, 'Your Amazon.com'))).click()
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'ap_email'))).send_keys(username)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'ap_password'))).send_keys(password)
    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'signInSubmit'))).click()
    validate('Hello' in WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'nav-link-accountList'))).find_element_by_class_name('nav-line-1').text, 'Amazon sign in failed')

# Get the list of URLs from the pages
def buy_books(baseUrl):
    pageNum = 1
    print "Find links"
    while paginate(pageNum, baseUrl):
        pageNum = pageNum + 1
        if not iterateBooks(getBookLinks()):
            print "Ran out of free books!"
            break
    print 'Category done'

# Get the links for books from the page
def getBookLinks():
    urls = []
    listtable = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 's-results-list-atf'))).find_elements_by_class_name('s-result-item')
    for element in listtable:
        if 'This item is currently not available.' in element.text:
            print 'Item not available, skip'
            continue
        urls.append(element.find_element_by_class_name('s-access-detail-page').get_attribute('href'))
    return urls

# Get the next page of books
def paginate(pageNum, baseUrl):
    if pageNum < 400:
        driver.get(baseUrl+str(pageNum))
        return True
    return False

# Iterate through the given list of book links
def iterateBooks(listUrls):
    global memory
    print(str(len(listUrls)) + ' books found')
    free_book_found = False
    for url in listUrls:
        book_id = get_book_id(url)
        safe_print(book_id)
        if book_id in memory.keys():
            safe_print(str(book_id) + ' found in memory, skipping')
            free_book_found = True
            continue
        if buyBookIfFree(url):
            free_book_found = True
    return free_book_found


# Search for url identifier
def get_book_id(bookurl):
    tokens = bookurl.split('/')
    if len(tokens) >= 3:
        return tokens[3]
    safe_print('ID not found in ' + bookurl)
    return ''

# Write book title and id to file
def write_known_book(key, value):
    if key != '':
        try:
            with codecs.open(memfile, 'a', 'utf-8') as memorywrite:
                memorywrite.write(unicode(key + '||' + value + '\n'))
            memorywrite.close()
        except:
            print "Failed to write book to file"

# Check if the item is free and not previously purchased, commit
def buyBookIfFree(url):
    driver.get(url)
    mem_id = get_book_id(url)
    booktitle = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'ebooksProductTitle'))).text.strip()
    if reducedOnly and len(driver.find_elements_by_class_name('ebooks-price-savings')) <= 0:
        safe_print('Skip normally free' + booktitle)
        return True
    if alreadyBought():
        write_known_book(mem_id, booktitle)
        safe_print('Already bought ' + booktitle)
        return True
    if not isBookFree():
        safe_print(booktitle + ' is NOT free')
        return False
    safe_print('Buying ' + booktitle)
    driver.implicitly_wait(3)
    if not select_alternate_device(booktitle):
        return True
    try:
        driver.find_element_by_id('one-click-button').click()
    except NoSuchElementException:
        driver.find_element_by_id('mas-buy-button').click()
    write_known_book(mem_id, booktitle)
    safe_print("Bought " + booktitle)
    driver.implicitly_wait(0)
    return True

# Select other device to deliver to, if specified
def select_alternate_device(booktitle):
    if alternateDevice != "":
        if len(driver.find_elements_by_id('buyDropdown')) > 0:
            select = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'buyDropdown'))).find_element_by_tag_name('select')
            options_box = select.find_elements_by_tag_name("option")
            options = []
            for option in options_box:
                options.append(option.text)
            if alternateDevice not in options:
                safe_print(booktitle + ' cannot be delivered to the specified device ' + alternateDevice)
                return False
            Select(select).select_by_visible_text(alternateDevice)
            return True
        else:
            safe_print(booktitle + ' not available to alternate devices')
            return False
    return True

# Check if book is free ($0.00)
def isBookFree():
    alt_price = False
    try:
        kindle_price = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'kindle-price')))
    except TimeoutException:
        print 'Abnormal price display, trying basic'
        alt_price = True
        try:
            kindle_price = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "a-color-price")))
        except TimeoutException:
            print 'No pricing available'
            return False
    if kindle_price.text.strip().startswith('Kindle Price: $0.00') or (alt_price and kindle_price.text.strip().startswith('$0.00')):
        return True
    print 'Book not free ('+kindle_price.text.strip()+')'
    return False

# Check if already purchased
def alreadyBought():
    divs = driver.find_elements_by_id('ebooksInstantOrderUpdate')
    for element in divs:
        if 'You purchased' in element.text:
            return True
    return False

# Print book titles with special characters
def safe_print(msg):
    try:
        print str(unicode(msg.encode('utf-8')))
    except Exception, e:
        print 'Something broke trying to print... ' + e.message

# Validate some condition
def validate(condition, message):
    if not condition:
        print('Script failed for ' + message)
        sys.exit(1)

if __name__ == '__main__':
    main(sys.argv[1:])

