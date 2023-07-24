import requests
import time
import dicttoxml
import sys
import os
import urllib
from datetime import datetime
from bs4 import BeautifulSoup
from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods.posts import NewPost

# 명령행에서 아규먼트 읽음
args = sys.argv
arg_ct = len(args) - 1

if arg_ct != 1:
	print("\n사용법 : $ python tistory_get.py [포스트번호]\n\n") 
	sys.exit()

base_url = 'cybercafe.tistory.com'

error_count = 0
error_max_count = 50

start = int(args[1])

try:
	url = 'https://'+base_url+'/'+str(start)
	http = None
	try:	
		post = requests.get(url)
		post.raise_for_status()
	except requests.exceptions.HTTPError as e:
		if post.status_code == 404:
			print('Post를 찾을 수 없습니다.' + str(index) + ' - 404 Not Found')
			time.sleep(3)
		else:
			print('Post를 찾았습니다. Post 번호 : ' + str(index))

	page = BeautifulSoup(post.content, "html.parser")

	# Check 404 also
	post = page.find('div', {'class': 'absent_post'})

	if post:
		print('Post ' + str(index) + ' - Not Found')
		time.sleep(3) 

	# Get Title of article
	title = page.find('title')
	category = page.find('a', class_='jb-category-name')
	wdate = page.find('li', class_='jb-article-information-date')
	print('Post No : ' + str(start) + ', Title : ' + title.text)
	print('Category : ' + category.text + ', Date : ' + wdate.text.strip())

	# Get Article
	contents_div = page.find('div', class_='contents_style')

	# Article에서 java 스크립트 태그 선택 및 제거
	script_tags = contents_div.find_all('script')
	for script_tag in script_tags:
		script_tag.decompose()

	# Article에서 adsense 제거
	script_tags = contents_div.find_all('div', id='AdsenseM1')
	for script_tag in script_tags:
		script_tag.decompose()

	with open("tags.txt", "w") as file:
		# 모든 태그에 순차적으로 접근
		for tag in contents_div.children:
			if tag.name == 'p':
				file.write(tag.name + " | " + tag.text + "\n====\n")
			elif tag.name == 'span' and tag.get('class') == ['imageblock']:
				image = tag.find('img')
				image_url = image['src']
				alt_text = image.get('alt', '')
				file.write(image.name + " | " + image_url + "| " + alt_text + "\n====\n")
			elif tag.name == "strong":
				file.write(tag.name + " | " + tag.text.strip() + "\n====\n")	
			elif isinstance(tag, str):  # 텍스트 노드인 경우
				file.write("텍스트 노드 | " + tag.strip()  + "\n====\n")
		file.close()

except KeyboardInterrupt:
    sys.exit(0)