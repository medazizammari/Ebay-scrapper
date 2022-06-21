import requests, time, re, schedule
from bs4 import BeautifulSoup
from time import localtime
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
#ebay_links records all the urls in the featured collections inside the list
#product_links. It will be compared later with new_product_links to determine
#which urls are featured and which are no longer featured by comparing the nth
#case to the (n-1) case.
from ebay_links import product_links

#Writes the initial file and the column headers, which are appended to later by
#the actual data. Every time ebay_experiment is called, it creates a new file.
with open("product_data.txt", "w") as initial_file:
   initial_file.write(
   "Time;Featured;Item number;Title;Condition;Trending price($);List price($);" +
   "Discount($);Discount(%);Current price($);Shipping cost($);" +
   "Item location;Estimated delivery;Return policy;Total item ratings;" +
   "Item rating;Total seller reviews;Seller positive feedback(%);" +
   "Hot info;Total watching;Units sold;Percent sold;Units remaining;Inquiries;" +
   "First reason to buy;Second reason to buy;Third reason to buy;Date;URL" + "\n"
   )

#Filled as the scraper identifies links of listings that have already ended.
bad_links = []

#Retries if the page request bounces
s = requests.Session()
retries = Retry(
    total=10000,
    backoff_factor = 0.1,
    status_forcelist=[ 500, 502, 503, 504 ])

s.mount('http://', HTTPAdapter(max_retries=retries))

#NOTES:
#.encode('ascii','replace') replaces any Unicode objects that ASCII does not
#recognize with a ? so that the information can be imported into a text file.

def job():
    #Scrapes the eBay home page and returns a list of links from the home page's
    #Featured Collections, and every link within each collection.
    #The current date and time.
    from ebay_experiment_v2 import bad_links
    starttime = time.strftime("%H:%M:%S", localtime())
    print starttime + " - I'm starting the iteration" + "\n"
    #Takes the original eBay url and goes from there.
    url1 = 'http://www.ebay.com/'
    ebaysoup = BeautifulSoup(s.get(url1).text, 'html.parser')
    #No_lazy is the class in which all the featured collections are found
    no_lazy = ebaysoup.find_all('div', attrs = {'class':'no-lazy'})
    #The links to the featured collections are appended to this list.
    featured_links = []

    #Returns the link of each Featured Collection displayed on the main page.
    for html_code in no_lazy:
        featured_links.append(html_code.find('a').get('href'))

    new_product_links = []

    #Iterates through the link of each Featured Collection.
    for html_url in featured_links:
        html_soup = BeautifulSoup(s.get(html_url).text, 'html.parser')
        #Iterates through all the URLs found within the HTML code and appends them.
        item_thumb = html_soup.find_all('div', attrs={'class':'itemThumb'})
        for html_code in item_thumb:
            new_product_links.append(html_code.find('a').get('href'))
        #Generates the URL of an lxml ajax request responsible for retrieving some
        #but not all of the product links. These links need to be retrieved by
        #different means and then added to new_product_links.
        editor = html_url[24:]
        slash = editor.index('/')
        editor = editor[:slash]
        col_code = html_url[-12:]
        lxml_url = 'http://www.ebay.com/cln/_ajax/2/%s/%s' % (editor, col_code)
        #Reduces reduncancy between the URLs generated by html and lxml. The
        #number 30 is rather arbitrary.
        limiter = {'itemsPerPage':'30'}
        lxml_soup = BeautifulSoup((s.get(lxml_url, params=limiter).content), 'lxml')
        #Retrieves all the URLs that the xml code is responsible for.
        lxml_links = [a["href"] for a in lxml_soup.select("div.itemThumb div.itemImg.image.lazy-image a[href]")]

        #Merges the lists and turns them into a set to remove redundancies.
        new_product_links = list(set(new_product_links + lxml_links))
        print str(len(new_product_links)) + " links found"

    #Used to create a correspondence between the link and whether it is featured.
    #The links are the key, and their status (featured or not) is its corresponding
    #information.
    linkdict = {}

    for link in product_links:
        #If a link is in both lists, then it continues to be featured.
        if new_product_links.count(link)==1:
            linkdict[link] = "Featured"
            print "Continues to be featured"
        #If a link is in product_links but not new_product_links, then it was
        #previously featured but no longer is.
        else:
            linkdict[link] = "Not featured"
            print "This link is no longer featured"

    for link in new_product_links:
        #Preliminary check to see if the link is still featured.
        if product_links.count(link)==1:
            pass
        else:
            #Does not re-add the link to the dict if it is in bad_links.
            if bad_links.count(link)==1:
                print "Bad link not added"
            else:
                #If it is not in bad_links, then it is newwly featured.
                product_links.append(link)
                linkdict[link] = "Featured"
                print "NEW featured link found and added"

    print "The dictionary has these many links: " + str(len(linkdict))
    print "The list has these many links: " + str(len(product_links))

    #These are all checks to see if the listing has ended already.
    ended1 = re.compile(r'This listing has ended')
    ended2 = re.compile(r'This listing was ended')
    ended3 = re.compile(r'Bidding has ended')

    for key in linkdict:
        soup = BeautifulSoup(s.get(key).text, 'html.parser')
        ended_listing1 = soup.find(text=ended1)
        ended_listing2 = soup.find(text=ended2)
        ended_listing3 = soup.find(text=ended3)

        #The current date and time.
        mydate = time.strftime("%m/%d/%Y", localtime())
        mytime = time.strftime("%H:%M:%S", localtime())

        print mytime
        print key

        #Removes links of ended listings and adds them to bad_links.
        if ended_listing1 or ended_listing2 or ended_listing3:
            product_links.remove(key)
            bad_links.append(key)
            print "Link removed"
            #These two print statements should have an inverse relationship.
            print "The list now has these many links: " + str(len(product_links))
            print "There are now these many bad links: " + str(len(bad_links)) + "\n"
        else:
            #The product title.
            title = soup.find('h1', attrs={'class':'it-ttl'})
            if title:
                #Removes unnecessary information from the title variable
                for i in title('span'):
                   i.extract()
                title = title.get_text().encode('ascii','replace')
            else:
                title = "N/A"

            print title

            if title=="N/A":
                product_links.remove(key)
                bad_links.append(key)
                print "The list now has these many links: " + str(len(product_links))
                print "There are now these many bad links: " + str(len(bad_links)) + "\n"
            else:
                #The product's unique item_number. Could be used as a key value.
                item_number = soup.find('div', attrs={'id':'descItemNumber'})
                if item_number:
                    item_number = item_number.get_text().encode('ascii','replace')
                else:
                    item_number = "N/A"

                #The product's rating, out of five stars.
                item_rating = soup.find('span', attrs={'class':'reviews-seeall-hdn'})
                if item_rating:
                   item_rating = item_rating.get_text().replace(u'\xa0', u' ')[:3].encode('ascii','replace')
                else:
                   item_rating = 'N/A'

                #The total number of ratings the product has received.
                total_ratings = soup.find('a', attrs={'class':"prodreview vi-VR-prodRev"})
                if total_ratings:
                   total_ratings = total_ratings.get_text().replace(u',', u'').replace(u'product', u'')[:-7].strip().encode('ascii','replace')
                else:
                   total_ratings = '0'

                #The seller's eBay username.
                seller_name = soup.find('span', attrs={'class':'mbg-nw'})
                if seller_name:
                   seller_name = seller_name.get_text().encode('ascii','replace')
                else:
                   seller_name = 'N/A'

                #The total number of reviews the seller has received.
                seller_reviews = soup.find('span', attrs={'class':'mbg-l'})
                if seller_reviews:
                   seller_reviews = seller_reviews.find('a').get_text().encode('ascii','replace')
                else:
                   seller_reviews = "N/A"

                #The seller's positive feedback rating, given as a percent.
                seller_feedback = soup.find('div', attrs={'id':'si-fb'})
                if seller_feedback:
                   seller_feedback = seller_feedback.get_text().replace(u'\xa0', u' ')[:-19].encode('ascii','replace')
                else:
                   seller_feedback = "N/A"

                #The information given by eBay next to the "fire" emblem under the title.
                hot_info = soup.find('div', attrs={'id':'vi_notification_new'})
                if hot_info:
                   hot_info = hot_info.get_text().strip().replace(u',', u'').encode('ascii','replace')
                else:
                   hot_info = "N/A"

                #The declared condition of the item.
                condition = soup.find('div', attrs={'class':"u-flL condText  "})
                if condition:
                    #Also removes unnecessary information from the variable.
                    for i in condition('span'):
                        condition = i.extract()
                    condition = condition.get_text().encode('ascii','replace')
                else:
                   condition = "N/A"

                #How many units of the product have already been sold.
                amount_sold = soup.find('span', attrs={'class':["qtyTxt", "vi-bboxrev-dsplblk", "vi-qty-fixAlignment"]})
                if amount_sold:
                   amount_sold = amount_sold.find('a')
                   if amount_sold:
                       amount_sold = amount_sold.get_text().replace(u',', u'')[:-5].encode('ascii','replace')
                   else:
                       amount_sold = "N/A"
                else:
                   amount_sold = "N/A"

                #Scrapes the information in the bottom of the product info box.
                why_to_buy = soup.find('div', attrs={'id':'why2buy'})
                if why_to_buy:
                    #Specifically looks for information following the format:
                    #"More than X% sold"
                    sold_pattern = re.compile(r'More than')
                    percent_sold = why_to_buy.find(text=sold_pattern)
                    if percent_sold:
                        percent_sold = percent_sold.replace(u'More than ',u'').replace(u'% ',u'').replace(u'sold',u'').encode('ascii','replace')
                    else:
                        percent_sold = "N/A"

                    #Appends each piece of information to the list.
                    reasons = []
                    three_reasons = why_to_buy.find_all('span', attrs={'class':'w2b-sgl'})
                    for reason in three_reasons:
                        reason = reason.get_text().encode('ascii','replace')
                        reasons.append(reason)

                    if len(reasons)==1:
                        first_reason = reasons[0]
                        second_reason = "N/A"
                        third_reason = "N/A"
                    elif len(reasons)==2:
                        first_reason = reasons[0]
                        second_reason = reasons[1]
                        third_reason = "N/A"
                    elif len(reasons)==3:
                        first_reason = reasons[0]
                        second_reason = reasons[1]
                        third_reason = reasons[2]
                    else:
                        first_reason = "N/A"
                        second_reason = "N/A"
                        third_reason = "N/A"
                else:
                    percent_sold = "N/A"
                    first_reason = "N/A"
                    second_reason = "N/A"
                    third_reason = "N/A"

                #How many available units of the product are left.
                amount_available = soup.find('span', attrs={'id':'qtySubTxt'})
                if amount_available:
                   amount_available = amount_available.get_text().strip().encode('ascii','replace')
                   if amount_available=="More than 10 available":
                      amount_available = ">10"
                   elif amount_available=="Limited quantity available":
                      amount_available = "Limited quantity"
                   elif amount_available=="Last one":
                      amount_available = "1"
                   else:
                      amount_available = amount_available[:-10].encode('ascii','replace')
                else:
                   amount_available = "N/A"

                #The number of inquiries, if available. Uses regex to search for
                #the information.
                pattern = re.compile(r'inquiries')
                inquiries = soup.find(text=pattern)
                if inquiries:
                   inquiries = inquiries.replace(u',', u'')[:-10].encode('ascii','replace')
                else:
                   inquiries = "N/A"

                #Scrapes the trending price of a kind of product whenever it is provided.
                trending_price = soup.find('div', attrs={'class':'u-flL vi-bbox-posTop2 '})
                if trending_price:
                   for i in trending_price('div'):
                       i.extract()
                   trending_price = trending_price.get_text().strip().replace(u',', u'').encode('ascii','replace')
                   if trending_price[0]=="$":
                       trending_price = trending_price.replace(u'$',u'').strip()
                   elif trending_price[:2]=="US":
                       trending_price = trending_price.replace(u'US ', u'').replace(u'$',u'').strip()
                   elif trending_price[:3]=="GBP" or trending_price[1]=="C" or trending_price[:2]=="AU" or trending_price[:3]=="EUR":
                       trending_price = "Foreign currency"
                   else:
                       trending_price = "Unknown currency"
                else:
                   trending_price = "N/A"

                #The original price of the product.
                list_price = soup.find('span', attrs={'id':['orgPrc', 'mm-saleOrgPrc']})
                if list_price:
                   list_price = list_price.get_text().strip().replace(u'US ', u'').replace(u',', u'').encode('ascii','replace')
                   if list_price=="":
                       list_price = "N/A"
                   elif list_price[:3]=="GBP" or list_price[1]=="C" or list_price[:2]=="AU" or list_price[:3]=="EUR":
                       list_price = 'Foreign currency'
                   else:
                       list_price = list_price.strip().encode('ascii','replace')
                else:
                   list_price = "N/A"

                #The product discount, in both dollar and percent.
                you_save = soup.find('span', attrs={'id':'youSaveSTP'})
                if not you_save:
                   you_save = soup.find('div', attrs={'id':'mm-saleAmtSavedPrc'})
                else:
                   pass
                if you_save:
                   you_save = you_save.get_text().strip().replace(u'\xa0', u' ').replace(u'US ', u'').replace(u',', u'')
                   if you_save=="(% off)":
                       you_save_raw = "N/A"
                       you_save_percent = "N/A"
                   elif you_save[:3]=="GBP" or you_save[1]=="C" or you_save[:2]=="AU" or you_save[:3]=="EUR":
                       you_save_raw = "N/A"
                       you_save_percent = "N/A"
                   else:
                       you_save_raw = you_save[1:-9].strip().encode('ascii','replace')
                       you_save_percent = you_save.replace(you_save_raw, u'').replace(u'$',u'').replace(u'(',u'').replace(u'% off)',u'').strip().encode('ascii','replace')
                else:
                   you_save_raw = "N/A"
                   you_save_percent = "N/A"

                #The product's current price, after discounts.
                #Sometimes the price is given in a foreign currency, in which case
                #the scraper searches for its conversion within the html code.
                now_price = soup.find('span', attrs={'id':'prcIsum'})
                if not now_price:
                   now_price = soup.find('span', attrs={'id':'mm-saleDscPrc'})
                else:
                   pass
                if now_price:
                   now_price = now_price.get_text().replace(u',', u'').encode('ascii','replace')
                   if now_price[:2]=="US":
                       now_price = now_price[4:].encode('ascii','replace')
                   elif now_price[:3]=="GBP":
                       now_price = soup.find('span', attrs={'id':'convbinPrice'})
                       if now_price:
                           for i in now_price('span'):
                              i.extract()
                           now_price = now_price.get_text()[4:].encode('ascii','replace')
                       else:
                           now_price = soup.find('span', attrs={'id':'convbidPrice'})
                           for i in now_price('span'):
                              i.extract()
                           now_price = now_price.get_text()[4:].encode('ascii','replace')
                   elif now_price[1]=="C":
                       now_price = soup.find('span', attrs={'id':'convbinPrice'})
                       if now_price:
                           for i in now_price('span'):
                              i.extract()
                           now_price = now_price.get_text()[4:].encode('ascii','replace')
                       else:
                           now_price = soup.find('span', attrs={'id':'convbidPrice'})
                           for i in now_price('span'):
                              i.extract()
                           now_price = now_price.get_text()[4:].encode('ascii','replace')
                   elif now_price[:2]=="AU":
                       now_price = soup.find('span', attrs={'id':'convbinPrice'})
                       if now_price:
                           for i in now_price('span'):
                              i.extract()
                           now_price = now_price.get_text()[4:].encode('ascii','replace')
                       else:
                           now_price = soup.find('span', attrs={'id':'convbidPrice'})
                           for i in now_price('span'):
                              i.extract()
                           now_price = now_price.get_text()[4:].encode('ascii','replace')
                   elif now_price[:3]=="EUR":
                       now_price = soup.find('span', attrs={'id':'convbinPrice'})
                       if now_price:
                           for i in now_price('span'):
                              i.extract()
                           now_price = now_price.get_text()[4:].encode('ascii','replace')
                       else:
                           now_price = soup.find('span', attrs={'id':'convbidPrice'})
                           for i in now_price('span'):
                              i.extract()
                           now_price = now_price.get_text()[4:].encode('ascii','replace')
                   else:
                       now_price = "Unknown currency"
                else:
                   now_price = "N/A"

                #The product's shipping costs.
                shipping_cost = soup.find('span', attrs={'id':'fshippingCost'})
                if shipping_cost:
                    shipping_cost = shipping_cost.get_text().replace(u',', u'').strip().encode('ascii','replace')
                    if shipping_cost[:3]=="GBP":
                        shipping_cost = soup.find('span', attrs={'id':'convetedPriceId'})
                        shipping_cost = shipping_cost.get_text()[4:]
                    elif shipping_cost[1]=="C":
                        shipping_cost = soup.find('span', attrs={'id':'convetedPriceId'})
                        shipping_cost = shipping_cost.get_text()[4:]
                    elif shipping_cost[:2]=="AU":
                        shipping_cost = soup.find('span', attrs={'id':'convetedPriceId'})
                        shipping_cost = shipping_cost.get_text()[4:]
                    elif shipping_cost[:3]=="EUR":
                        shipping_cost = soup.find('span', attrs={'id':'convetedPriceId'})
                        shipping_cost = shipping_cost.get_text()[4:]
                    elif shipping_cost=="FREE":
                        shipping_cost = "0.00"
                    elif shipping_cost[0]=="$":
                        shipping_cost = shipping_cost.replace(u'$',u'')
                    else:
                        shipping_cost = "Unknown currency"
                else:
                    #Sometimes the shipping cost is not given, and some supplementary
                    #information such as "Local pickup" is given. In this case,
                    #the scraper performs a naive search for the first bit of
                    #information that seems relevant.
                    shipping_cost = soup.find('span', attrs={'id':'shSummary'})
                    if shipping_cost:
                        shipping = []
                        for i in shipping_cost('span'):
                            shipping.append(i.extract())
                        for i in shipping:
                            shipping_cost = i.get_text().strip().encode('ascii','replace')
                            if shipping_cost=="" or shipping_cost=="|":
                                pass
                            else:
                                break
                    else:
                        shipping_cost = "N/A"

                #The total number of buyers watching the product.
                total_watching = soup.find('span', attrs={'class':'vi-buybox-watchcount'})
                if total_watching:
                   total_watching = total_watching.get_text().replace(u',', u'').encode('ascii','replace')
                else:
                   total_watching = "N/A"

                #The seller's location; where the item will be shipped from.
                item_location = soup.find('div', attrs={'class':'iti-eu-bld-gry'})
                if item_location:
                   item_location = item_location.get_text().strip().encode('ascii','replace')
                else:
                   item_location = "N/A"

                #The estimated date at which the product will be delivered to the DFW area.
                delivery_date = soup.find('span', attrs={'class':'vi-acc-del-range'})
                if delivery_date:
                   delivery_date = delivery_date.get_text().replace(u'and', u'-').encode('ascii','replace')
                   #The estimated delivery date is based on my location; is this information
                   #therefore at all relevant to our insights of other buyers//sellers?
                else:
                   delivery_date = "N/A"

                #The return policy offered by the seller.
                return_policy = soup.find('span', attrs={'id':'vi-ret-accrd-txt'})
                if return_policy:
                   return_policy = return_policy.get_text().replace(u'\xa0', u' ').strip().encode('ascii','replace')
                   #Sometimes the return policy is too long, in which case the
                   #scraper abbreviates it to an arbitrary 90 characters.
                   if len(return_policy)>90:
                       return_policy = return_policy[:90] + "..."
                   else:
                       pass
                else:
                   return_policy = "N/A"

                featured = linkdict[key]

                print "\n"

                #After scraping all the data, it is appended to a text file
                #with semicolon delimiters.
                with open("product_data.txt", "a") as continued_file:
                    continued_file.write(
                        mytime + ";" +
                        featured + ";" +
                        item_number + ";" +
                        title + ";" +
                        condition + ";" +
                        trending_price + ";" +
                        list_price + ";" +
                        you_save_raw + ";" +
                        you_save_percent + ";" +
                        now_price + ";" +
                        shipping_cost + ";" +
                        item_location + ";" +
                        delivery_date + ";" +
                        return_policy + ";" +
                        total_ratings + ";" +
                        item_rating + ";" +
                        seller_reviews + ";" +
                        seller_feedback + ";" +
                        hot_info + ";" +
                        total_watching + ";" +
                        amount_sold + ";" +
                        percent_sold + ";" +
                        amount_available + ";" +
                        inquiries + ";" +
                        first_reason + ";" +
                        second_reason + ";" +
                        third_reason + ";" +
                        mydate + ";" +
                        key + "\n"
                        )

    endtime = time.strftime("%H:%M:%S", localtime())
    print endtime + " - I finished the iteration"

#Ensures that the scraper performs its very first iteration immediately, instead
#of waiting 25 minutes to start.
job()

#Reiterates 25 minutes atfer the CONCLUSION of the previous iteration.
schedule.every(25).minutes.do(job)

while True:
   schedule.run_pending()
   time.sleep(30)

"""depth = 30

while depth > 0:
    try:
        job()
        time.sleep(60*20)
    except requests.exceptions.ConnectionError:
        print "Connection lost"
        time.sleep(60)
        depth -= 1
        print "Trying again"
        job()"""
