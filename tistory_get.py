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

if arg_ct != 2:
	print("\n사용법 : $ python tistory_get.py [시작포스트번호]  [마지막끝포스트번호]\n\n") 
	sys.exit()

base_url = 'cybercafe.tistory.com'

error_count = 0
error_max_count = 50

start = int(args[1])
end = int(args[2])+1

try:
	for index in range(start, end):
		url = 'https://'+base_url+'/'+str(index)
		http = None
		try:	
			post = requests.get(url)
			post.raise_for_status()
		except requests.exceptions.HTTPError as e:
			if post.status_code == 404:
				print('Post를 찾을 수 없습니다.' + str(index) + ' - 404 Not Found')
				time.sleep(3)
				continue
			else:
				print('Post를 찾았습니다. Post 번호 : ' + str(index))

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

		# Get Article
		article = page.find('div', class_='contents_style')

		# Article에서 java 스크립트 태그 선택 및 제거
		script_tags = article.find_all('script')
		for script_tag in script_tags:
			script_tag.decompose()

		# Article에서 adsense 제거
		script_tags = article.find_all('div', id='AdsenseM1')
		for script_tag in script_tags:
			script_tag.decompose()

		# P 태그에서 data-ke-size 제거
		p_tags = article.find_all('p')
		for p_tag in p_tags:
			del p_tag['data-ke-size']		

		# pre 태그에서 불필요한 attribute 삭제
		pre_tags = article.find_all('pre')
		for pre_tag in pre_tags:
			del pre_tag['id']
			del pre_tag['class']
			del pre_tag['data-ke-language']
			del pre_tag['data-ke-type']

		# 이미지 태그 선택
		img_tags = article.find_all('img')

		# 이미지 다운로드
		for img_tag in img_tags:
    		# 이미지 URL
			img_url = img_tag['src']

			# img tag에 data-filename 이라는 속성이 있으면
			if "data-filename" in img_tag.attrs:
				fname = img_tag['data-filename']
				#print(f"data-filename : {fname}")
			else: # 없으면
				fname = os.path.basename(img_url)
				if fname == "img.jpg":
					directory_name = os.path.dirname( img_tag['src'])
					last_dirname = directory_name.split('/')[-1]
					fname = last_dirname

			# 이미지 저장 경로 생성			
			os.makedirs (os.getcwd() + "/tistory/", exist_ok=True)
			img_dir = os.path.join(os.getcwd() + "/tistory/"+str(index))
			os.makedirs (img_dir, exist_ok=True)
			img_path = os.path.join(img_dir, fname)

    		# 이미지 요청
			img_response = requests.get(img_url)

    		# 이미지 파일 저장. 파일명에 ? 가 포함되어 있을경우 파일저장시 파일명이 '로 묶여 저장되는 경우가 있음
			with open(img_path.replace("?", "_"), 'wb') as img_file:
				img_file.write(img_response.content)
				print(f"이미지 다운로드 완료: {fname}")
			
			# img 태그에서 src attribute의 값을 변경
			img_tag['src'] = img_dir + '/' + fname
			# img 태그에서 불필요한 srcset 속성 삭제
			del img_tag['srcset']
			del img_tag['onerror']

		# div 태그 내의 하위 태그에 순차적으로 접근하기
		# 포스트 다시 작성하기
		contents = ""

		# 이미지가 없는 포스트의 경우 새로 생성해야 함
		os.makedirs (os.getcwd() + "/tistory/", exist_ok=True)

		img_alt = ""

		# 포스트 본문 추출. p 태그가 있는지 여부 판단함
		for tag in article.find_all():
			if tag.name == "p":
				# p tag 다음에 figure 태그가 있으면 이미지의 alt 태그로 처리함
				sec_tag = tag.find('figure')
				if sec_tag:  
					img_alt = sec_tag.text.strip()
				else:  # 없으면 그냥 컨텐츠 문장
					# <br> 태그와 텍스트를 추출하여 리스트로 저장
					img_alt = ""
				if tag.parent.get('class') == ['contents_style']:
					contents = contents + "<p>" + tag.text.strip() + "</p>\n"
			elif tag.name == "img":
				# 파일명에 ?가 있을경우 경우에 따라 파일저장 시 _로 대체되기 때문에 처리함. 앞에서 이미지파일 저장시에도 파일명에 ?가 있으면 _로 대체하여 저장함
				contents = contents + "<img src=" + '"/tistory/' + str(index) + "/" + os.path.basename(tag['src'].replace("?", "_")) + '" alt="' + img_alt + '">\n'
			elif tag.name == "div":
				contents = contents + "<p>" + tag.text.strip() + "</p>\n" 
			elif tag.name == "h2":
				contents = contents + "<h2>" + tag.text.strip() + "</h2>\n"
			elif tag.name == "h1":
				contents = contents + "<h1>" + tag.text.strip() + "</h1>\n"
			elif tag.name == "h3":
				exist_p_tag = 1
				contents = contents + "<h3>" + tag.text.strip() + "</h3>\n"
			elif tag.name == "h4":
				exist_p_tag = 1
				contents = contents + "<h4>" + tag.text.strip() + "</h4>\n"
			elif tag.name == "pre":
				exist_p_tag = 1
				sec_tag = tag.find('code') 
				if sec_tag: # pre와 code가 연속으로 오는 코드 태그이면 pre 태그를 회색 박스로 표시하도록 처리
					contents = contents + '<pre style="border:1px;solid:#ccc;padding:10px;background-color:#d9d9d9;"><code>' + tag.text.strip() + "</code></pre>\n"
				else:
					contents = contents + "<pre>" + tag.text.strip() + "</pre>"
			elif tag.name == "ul":  # list 태그(ul) 처리
				exist_p_tag = 1
				contents = contents + "<ul>\n"
				li_tags = tag.find_all('li')
				for li_tag in li_tags:
					contents = contents + "<li>" + li_tag.text.strip() + "</li>\n"
				contents = contents + "</ul>\n"
			elif tag.name == "span" and tag.parent.get('class') == ['contents_style']:
				contents = contents + "<p>" + tag.text.strip() + "</p>\n"

		# 포스트를 저장할 html 파일명 생성
		wfilename = os.getcwd() + "/tistory/" + str(index) + ".html"

		# 포스트의 제목 등과 컨텐츠를 파일에 작성
		with open(wfilename, "w") as file:
			file.write("포스트 제목 : " + title.text.strip() + "\n")
			file.write("포스트 작성일자 : " + wdate.text.strip() + "\n")
			file.write("카테고리 : " + category.text.strip() + "\n")
			file.write("-------------\n")
			file.write(contents)

		time.sleep(3)

except KeyboardInterrupt:
    sys.exit(0)

