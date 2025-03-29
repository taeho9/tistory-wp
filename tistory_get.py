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

# 워드프레스로 이사를 위해 백업할 티스토리 블로그 주소
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
				print('◆◆◆ Post를 찾을 수 없습니다. https://' + base_url + "/" + str(index) + ' - 404 Not Found ◆◆◆')
				time.sleep(3)
				continue
			else:
				print('◆◆◆ 알 수 없는 예러가 발생앴습니다. https://' + base_url + "/" + str(index) + " ◆◆◆◆")
				continue

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
		print('◆ Post No : ' + str(index) + ', Title : ' + title.text + "  /" + str(index))
		print('◆ Category : ' + category.text + ', Date : ' + wdate.text.strip())
		print('◆ WordPress Slug : /' + str(index))

		# 다운로드 이미지 파일과 새롭게 생성한 contents에 추가한 <img> 태그의 카운트를 비교하기 위한 변수 초기화
		img_file_count = 0
		img_tag_count = 0

		# Get Article : 지금까지 Post의 컨텐츠가 들어있는 2 종의 DIV 컨텐츠를 찾음.
		if (article := page.find('div', class_='tt_article_useless_p_margin')):
			print("◆ tt_article_useless_p_margin Class의 DIV 태그를 찾았습니다.")
		elif(article := page.find('div', class_='contents_style')):
			print("◆ contents_style class의 DIV 태그를 찾았습니다.")
		elif(article := page.find('div', class_=['tt_article_useless_p_margin','contents_style'])):
			print ("◆ 두 DIV 클래스를 모두 갖는 DIV 태그를 찾았습니다.")
		else:
			print("◆◆◆ Post의 컨텐츠를 담고 있는 DIV 태그를 찾을 수 없습니다. - Contents Div tag Not Found ◆◆◆")
			sys.exit(0)

		# Article에서 java 스크립트 태그 선택 및 제거
		if (script_tags := article.find_all('script')):
			for script_tag in script_tags:
				script_tag.decompose()

		# Article에서 adsense 제거
		if (script_tags := article.find_all('div', id='AdsenseM1')):
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

		# 포스트의 컨텐츠에서 이미지 태그를 모두 찾아 다운로드 받고 img 태그 정리 및 URL 경로 변경 코드 시작
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
				img_file_count = img_file_count + 1     # 이미지 다운로드에 성공하면 카운터 1 증가
				#print(f"- 이미지 다운로드 완료: {fname}")
			
			# img 태그에서 src attribute의 값을 변경
			#img_tag['src'] = img_dir + '/' + fname
			img_tag['src'] = "/tistory/" + str(index) + "/" + fname
			
			# img 태그에서 불필요한 srcset 속성 삭제
			del img_tag['srcset']
			del img_tag['onerror']
		    # 포스트의 컨텐츠에서 이미지 태그를 모두 찾아 다운로드 받고 img 태그 정리 및 URL 경로 변경 코드 끝

		# div 태그 내의 하위 태그에 순차적으로 접근하기
		# 포스트 다시 작성하기
		contents = ""

		# 이미지가 없는 포스트의 경우 새로 생성해야 함. 이미지를 다운로드 받아서 이미 있으면 무시됨 (exist_ok=True)
		os.makedirs (os.getcwd() + "/tistory/", exist_ok=True)

		img_alt = ""

		# 포스트 본문 추출. p 태그가 있는지 여부 판단함
		for tag in article.children:
			if tag.name == "p":
				# p tag 다음에 figure 태그가 있으면 이미지의 alt 태그로 처리함
				if sec_tags := tag.find_all('figure'):
					for sec_tag in (sec_tags):
						# print("- P태그 내부의 figure 찾음")
						img_tag = sec_tag.find('img')
						alt_text = img_tag.get('alt', '')
						#contents = contents + "<img src=" + '"/tistory/' + str(index) + "/" + os.path.basename(img_tag['src'].replace("?", "_")) + '" alt="' + alt_text + '">\n'
						contents = contents + "<figure style='text-align: center;'>\n<img src='" + img_tag['src'].replace("?", "_") + "' alt='" + alt_text + "'>\n"
						if(figure_tag := sec_tag.find('figcaption')):
							caption = figure_tag.text.strip()
							figure_tag.decompose()
						else:
							caption = ""
						contents = contents + "<figcaption>" + caption + "</figcaption>\n</figure>\n"
						img_tag_count = img_tag_count + 1
				elif (sec_tags := tag.find_all('span')):  # figure 없으면 혹시 imageblock span이 있는지 확인
					for sec_tag in sec_tags:
						if sec_tag and sec_tag.get('class') == ['imageblock']:
							#print("- P태그 내부의 imageblock span 찾음")
							image = sec_tag.find('img')
							alt_text = image.get('alt', '')
							#contents = contents + "<img src=" + '"/tistory/' + str(index) + "/" + os.path.basename(image['src'].replace("?", "_")) + '" alt="' + alt_text + '">\n'
							contents = contents + "<figure style='text-align: center;'>\n<img src='" + image['src'].replace("?", "_") + "' alt='" + alt_text + "'>\n"
							contents = contents + "<figcaption>" + sec_tag.text.strip() + "</figcaption>\n</figure>\n"
							if sec_tag:
								sec_tag.clear()
							img_tag_count = img_tag_count + 1
						else: # imageblock span이 없으면 imageblock div 태그가 있는지 확인
							sec_tag = tag.find('div')
							if sec_tag and (sec_tag.get('class') == ['imageblock','center'] or sec_tag.get('class') == ['imageblock']):
								#print("- P태그 내부의 imageblock center 또는 imageblock div 찾음")
								image = sec_tag.find('img')
								alt_text = image.get('alt', '')
								#contents = contents + "<img src=" + '"/tistory/' + str(index) + "/" + os.path.basename(image['src'].replace("?", "_")) + '" alt="' + alt_text + '">\n'
								contents = contents + "<img src='" + image['src'].replace("?", "_") + "' alt='" + alt_text + "'>\n"
								img_tag_count = img_tag_count + 1
							else:
								img_alt = ""
					# 이미지 블록 찾기 끝
				elif (sec_tag := tag.find('img')):
					#print("- P태그 내부의 img tag 찾음")
					alt_text = sec_tag.get('alt', title.text.strip())
					#contents = contents + "<img src=" + '"/tistory/' + str(index) + "/" + os.path.basename(sec_tag['src'].replace("?", "_")) + '" alt="' + alt_text + '">\n'
					contents = contents + "<img src='" + sec_tag['src'].replace("?", "_") + "' alt='" + alt_text + "'>\n"
					img_tag_count = img_tag_count + 1
				# p 태그 다음에 iframe이 오는 유튜브 등 동영상 삽입한 iframe 찾기
				sec_tag = tag.find('iframe')
				if sec_tag:
					contents = contents +"<center>" + sec_tag.prettify() + "</center>"
				# p 태그 내부에 table 태그가 있는지 찾기
				sec_tag = tag.find('table')
				if sec_tag:
					#print("- P 태그 내부의 Table 태그를 찾음")
					contents = contents + "<p>" + sec_tag.prettify() + "</p>\n"
					sec_tag.decompose()  # table tag 제거
				# P 태그에 바로 따라오는 <a> 태그 찾기
				if ( sec_tag:= tag.find('a')):
					contents = contents + "<a href='" + sec_tag['href'] + "'>"+ sec_tag.text.strip() + "</a>"
				# P 태그 내의 남아 있는 텍스트 추출하여 뒤에 추가
				contents = contents + "<p>" + tag.text.strip() + "</p>\n"
			elif tag.name == 'a':
				contents = contents + "<a href='" + tag['href'] + "'>" + tag.text.strip() + "</a>"
				tag.decompose()
			elif tag.name == 'span':
				if tag.get('class') == ['imageblock']:
					#print("* P태그 없는 imageblock span 찾음")
					image = tag.find('img')
					alt_text = image.get('alt', '')
					#contents = contents + "<img src=" + '"/tistory/' + str(index) + "/" + os.path.basename(image['src'].replace("?", "_")) + '" alt="' + alt_text + '">\n'
					contents = contents + "<figure style='text-align: center;'>\n<img src='" + image['src'].replace("?", "_") + "' alt='" + alt_text + "'>\n"
					contents = contents + "<figcaption>" + tag.text.strip() + "</figcaption>\n</figure>\n"
					tag.decompose()
					img_tag_count = img_tag_count + 1
			elif tag.name == "img":
				#print("# 최상위의 img 태그 찾음")
				# 파일명에 ?가 있을경우 경우에 따라 파일저장 시 _로 대체되기 때문에 처리함. 앞에서 이미지파일 저장시에도 파일명에 ?가 있으면 _로 대체하여 저장함
				#contents = contents + "<img src=" + '"/tistory/' + str(index) + "/" + os.path.basename(tag['src'].replace("?", "_")) + '" alt="' + img_alt + '">\n'
				contents = contents + "<img src='" + tag['src'].replace("?", "_") + "' alt='" + alt_text + "'>\n"
				img_tag_count = img_tag_count + 1
			elif tag.name == "figure":
				if (img_tag := tag.find('img')):
					#print("# 최상위의 Figure 태그 내부의 img 태그 찾음")
					alt_text = img_tag.get('alt', '')
					#contents = contents + "<img src=" + '"/tistory/' + str(index) + "/" + os.path.basename(img_tag['src'].replace("?", "_")) + '" alt="' + alt_text + '">\n'
					contents = contents + "<figure style='text-align: center;'>\n<img src='" + img_tag['src'].replace("?", "_") + "' alt='" + alt_text + "'>\n"
					if(figure_tag := sec_tag.find('figcaption')):
						caption = figure_tag.text.strip()
						figure_tag.decompose()
					else:
						caption = ""
					contents = contents + "<figcaption>" + caption + "</figcaption>\n</figure>\n"
					img_tag_count = img_tag_count + 1
				#else:
					#print("# 최상위의 figure 태그를 찾았으나 img 태그가 없습니다.")
			elif tag.name == "strong":
				contents = contents + "<p>" + tag.text.strip() + "</p>\n" 
			elif tag.name == "div":
				if tag.get('class') ==  ['imageblock', 'center'] or tag.get('class') == ['imageblock']:
					#print("# 최상위의 div 태그 내부에서 imageblock center 찾음")
					image = tag.find('img')
					alt_text = image.get('alt', '')
					#contents = contents + "<img src=" + '"/tistory/' + str(index) + "/" + os.path.basename(image['src'].replace("?", "_")) + '" alt="' + alt_text + '">\n' 
					contents = contents + "<img src='" + image['src'].replace("?", "_") + "' alt='" + alt_text + "'>\n"
					tag.decompose()
					img_tag_count = img_tag_count + 1
				elif tag.get('class') == ['txc-textbox']:
					#print("# 최상위 div 태그 내부에서 텍스트 박스 속성을 찾음")
					tag['style'] = "border-style: dashed; border-width: 1px; border-color: rgb(121, 165, 228); background-color: rgb(219, 232, 251); padding: 10px;"
					contents = contents + tag.prettify() 
				elif ((sec_tag := tag.find('span')) and sec_tag.get('class') == ['imageblock']):
					#print("# 최상위 div 태그 내부의 span 태그 내부에서 imageblock 찾음")
					image = tag.find('img')
					alt_text = image.get('alt', '')
					#contents = contents + "<img src=" + '"/tistory/' + str(index) + "/" + os.path.basename(image['src'].replace("?", "_")) + '" alt="' + alt_text + '">\n'
					contents = contents + "<img src='" + image['src'].replace("?", "_") + "' alt='" + alt_text + "'>\n"
					img_tag_count = img_tag_count + 1
				elif (sec_tag := tag.find('figure')) and sec_tag.get('class') == ['imageblock', 'alignCenter']:
					#print("- DIV 태그 내부의 figure 찾음")
					img_tag = sec_tag.find('img')
					alt_text = img_tag.get('alt', '')
					#contents = contents + "<img src=" + '"/tistory/' + str(index) + "/" + os.path.basename(img_tag['src'].replace("?", "_")) + '" alt="' + alt_text + '">\n'
					contents = contents + "<figure style='text-align: center;'>\n<img src='" + img_tag['src'].replace("?", "_") + "' alt='" + alt_text + "'>\n"
					if(figure_tag := sec_tag.find('figcaption')):
						caption = figure_tag.text.strip()
						figure_tag.decompose()
					else:
						caption = ""
					contents = contents + "<figcaption>" + caption + "</figcaption>\n</figure>\n"
					img_tag_count = img_tag_count + 1
				else:
					contents = contents + "<p>" + tag.text.strip() + "</p>\n" 
			elif tag.name == "h2":
				contents = contents + "<h2>" + tag.text.strip() + "</h2>\n"
			elif tag.name == "h1":
				contents = contents + "<h1>" + tag.text.strip() + "</h1>\n"
			elif tag.name == "h3":
				contents = contents + "<h3>" + tag.text.strip() + "</h3>\n"
			elif tag.name == "h4":
				contents = contents + "<h4>" + tag.text.strip() + "</h4>\n"
			elif tag.name == "pre":
				sec_tag = tag.find('code') 
				if sec_tag: # pre와 code가 연속으로 오는 코드 태그이면 pre 태그를 회색 박스로 표시하도록 처리
					#print("# 최상위 Pre 태그의 code 태그를 찾아 style을 변경함")
					contents = contents + '<pre style="border:1px;solid:#ccc;padding:10px;background-color:#d9d9d9;"><code>' + tag.text.strip() + "</code></pre>\n"
				else:
					#print("# 최상위 Pre 태그를 찾음")
					contents = contents + "<pre>" + tag.text.strip() + "</pre>"
			elif tag.name == "ul":  # list 태그(ul) 처리
				#print("# 최상위 UL 태그를 찾음")
				contents = contents + "<ul>\n"
				li_tags = tag.find_all('li')
				for li_tag in li_tags:
					contents = contents + "<li>" + li_tag.text.strip() + "</li>\n"
				contents = contents + "</ul>\n"
			elif tag.name == "ol": # ol 태그 처리
				# print("# 최상위 OL 태그를 찾음")
				contents = contents + "<p>" + tag.prettify() + "</p>\n"
			elif tag.name == "span" and tag.parent.get('class') == ['contents_style']:
				# print("# 최상위 Span 태그를 찾음")
				contents = contents + "<p>" + tag.text.strip() + "</p>\n"
			elif tag.name == "table":
				print("# 최상위의 Table 태그를 찾음. <주의!> 내부에 IMG 태그가 있어도 생성한 IMG 태그의 카운트가 증가하지 않습니다.")
				contents = contents + "<p>" + tag.prettify() + "</p>\n"
			elif tag.name == "blockquote":
				# blockquote가 발견되면 일단 div 태그로 전환
				contents = contents + "<div style='border: 1px solid; border-radius: 5px; padding: 10px; background-color: #eeeeee;'>"
				if (sec_tag := tag.find('a')):   # 두번째 태그가 <a> tag면 처리함
					contents = contents + "<a href='" + sec_tag['href'] + "'>"+ sec_tag.text.strip() + "</a>"
				else: # 아니면 <p> 태그를 찾아 처리함
					if (block_tags := tag.find_all('p')):
						for block_tag in block_tags:
							contents = contents + "<p>" + block_tag.text.strip() + "</p>\n"
					else:
						contents = contents + tag.text.strip()
				#print("# 최상위의 blockquote 태그를 찾아 Div 태그로 변환함")  # 블록의 div 태그 스타일을 바꾸려면 아래 라인의 style 속성을 변경하면 됨
				contents = contents + "</div>\n"
			elif tag.name == "font":
				# print("# 최상위 Font 태그를 찾음")
				contents = contents + "<p>" + tag.text.strip() + "</p>\n"
			elif isinstance(tag, str):  # 텍스트 노드인 경우
				# print("# 최상위 Div 태그에 있는 텍스트 노드를 찾음")
				contents = contents + "<p>" + tag.text.strip() + "</p>\n" 

		# 포스트를 저장할 html 파일명 생성
		wfilename = os.getcwd() + "/tistory/" + str(index) + ".html"

		# 포스트의 제목 등과 컨텐츠를 파일에 작성
		with open(wfilename, "w") as file:
			file.write("포스트 제목     : \n" + title.text.strip() + "   /" + str(index) + "\n")
			file.write("카테고리        : " + category.text.strip() + "\n")
			file.write("포스트 작성일자 : " + wdate.text.strip() + "\n")
			file.write('워드프레스 Slug : /' + str(index) + "\n")
			file.write("-------------\n")
			file.write("다운로드 받은 이미지 개수 : " + str(img_file_count) + "\n")
			file.write("생성한 IMG 태그 개수      : " + str(img_tag_count) + "\n")
			file.write("-------------\n")
			file.write(contents)
		file.close()

		print("다운로드 받은 이미지 개수 : " + str(img_file_count))
		print("생성한 IMG 태그 개수      : " + str(img_tag_count))
		time.sleep(3)
	
except KeyboardInterrupt:
    sys.exit(0)

