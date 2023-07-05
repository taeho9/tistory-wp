from __future__ import unicode_literals

import requests
import time
import dicttoxml
import sys
import urllib
from bs4 import BeautifulSoup

base_url = 'cybercafe.tistory.com'

image_content_url = '/wp-content/uploads/tistory/'

article_data = []

error_count = 0
error_max_count = 50

try:
	for index in range(300, 302):
		http = None

		try:
			url = 'https://'+base_url+'/'+str(index)
			post = requests.get(url)
			post.raise_for_status()

		except requests.exceptions.RequestException as e:
			if e.code == 404:
				print('Post ' + str(index) + ' - Not Found')
				error_count += 1

				if error_count > error_max_count:
					print('Error Count is over the max value. Stopping the crawler')
					break
		
				time.sleep(3)
				continue
			else:
				raise
				error_count = 0

		page = BeautifulSoup(post.content, "html.parser")

		# Check 404 also
		absent_post = page.find('div', {'class': 'absent_post'})

		if absent_post:
			print('Post ' + str(index) + ' - Not Found')
			time.sleep(3)
			continue

		 # Get Title of article
		title = page.find('title')
		category = page.find('a', class_='jb-category-name')
		wdate = page.find('li', class_='jb-article-information-date')
		print('Post No : ' + str(index) + ', Title : ' + title.text)
		print('Category : ' + category.text + ', Date : ' + wdate.text.strip())

		# Get Artical
		article = page.find('div', class_='contents_style')

		# 스크립트 태그 선택 및 제거
		script_tags = article.find_all('script')
		for script_tag in script_tags:
			script_tag.decompose()

		# adsense 제거
		script_tags = article.find_all('div', id='AdsenseM1')
		for script_tag in script_tags:
			script_tag.decompose()

		print(article.prettify())

		time.sleep(3)

except KeyboardInterrupt:
    sys.exit(0)

