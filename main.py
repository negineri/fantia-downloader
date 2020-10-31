import argparse
import requests
import re
import json
import os
import time
import random
import sys
from bs4 import BeautifulSoup


def download_photo_gallery(post_path, post_content, requests_meta):
    regex_ext = re.compile(r'[^\.]+$')
    regex_url = re.compile(r'^[^\?]+')
    if post_content['comment'] is not None:
        file_path = post_path + '/comment.txt'
        with open(file_path, mode='w') as f:
            f.write(post_content['comment'])
    for index, post_content_photo in enumerate(post_content['post_content_photos']):
        try:
            res = requests.get(requests_meta['url_scheme'] + requests_meta['site_domain'] +
                               post_content_photo['show_original_uri'], cookies=requests_meta['cookies'])
        except requests.exceptions.RequestException as err:
            print(err)
            return False
        page_bs = BeautifulSoup(res.text, 'html.parser')
        img_url = page_bs.select_one('img').get('src')
        try:
            img = requests.get(img_url, cookies=requests_meta['cookies'])
        except requests.exceptions.RequestException as err:
            print(err)
            return False
        file_path = post_path + '/' + \
            format(index + 1, '03') + '.' + \
            regex_ext.search(regex_url.search(img_url).group()).group()
        with open(file_path, mode='wb') as f:
            f.write(img.content)


def download_file(post_path, post_content, requests_meta):
    if post_content['comment'] is not None:
        file_path = post_path + '/comment.txt'
        with open(file_path, mode='w') as f:
            f.write(post_content['comment'])
    file_url = requests_meta['url_scheme'] + \
        requests_meta['site_domain']+post_content['download_uri']
    try:
        file_data = requests.get(file_url, cookies=requests_meta['cookies'])
    except requests.exceptions.RequestException as err:
        print(err)
        return False
    file_path = post_path + '/' + post_content['filename']
    with open(file_path, mode='wb') as f:
        f.write(file_data.content)


def download_text(post_path, post_content, requests_meta):
    if post_content['comment'] is not None:
        file_path = post_path + '/comment.txt'
        with open(file_path, mode='w') as f:
            f.write(post_content['comment'])


def download_product(post_path, post_content, requests_meta):
    if post_content['comment'] is not None:
        file_path = post_path + '/comment.txt'
        with open(file_path, mode='w') as f:
            f.write(post_content['comment'])
    file_path = post_path + '/url.txt'
    with open(file_path, mode='w') as f:
        f.write(post_content['product']['uri'])


def download_post(dir_path, post_id, requests_meta):
    os.makedirs(dir_path, exist_ok=True)
    post_url = requests_meta['url_scheme'] + \
        requests_meta['site_domain'] + '/api/v1/posts/' + post_id
    regex_ext = re.compile(r'[^\.]+$')
    try:
        res = requests.get(post_url, cookies=requests_meta['cookies'])
    except requests.exceptions.RequestException as err:
        print(err)
        return False
    post_data = json.loads(res.text)

    file_path = dir_path + '/comment.txt'
    if not os.path.isfile(file_path):
        with open(file_path, mode='w') as f:
            f.write(post_data['post']['comment'])

    if post_data['post']['thumb'] is not None:
        file_path = dir_path + '/thumb.' + \
            regex_ext.search(post_data['post']['thumb']['original']).group()
        if not os.path.isfile(file_path):
            try:
                img = requests.get(post_data['post']['thumb']['original'],
                                   cookies=requests_meta['cookies'])
            except requests.exceptions.RequestException as err:
                print(err)
                return False
            with open(file_path, mode='wb') as f:
                f.write(img.content)

    for post_content in post_data['post']['post_contents']:
        if post_content['visible_status'] != 'visible':
            continue
        title = post_content['title'] or ''
        post_path = dir_path + '/' + \
            str(post_content['id']) + '_' + title
        if os.path.isdir(post_path):
            continue
        else:
            os.makedirs(post_path)
        if post_content['category'] == 'photo_gallery':
            download_photo_gallery(post_path, post_content, requests_meta)
        elif post_content['category'] == 'file':
            download_file(post_path, post_content, requests_meta)
        elif post_content['category'] == 'text':
            download_text(post_path, post_content, requests_meta)
        elif post_content['category'] == 'product':
            download_product(post_path, post_content, requests_meta)
        else:
            print(post_id + ' unknown category\n')
            sys.exit()

    time.sleep(random.random())


def get_posts(user_id, requests_meta):
    savedata_dir = './data'
    page_num = 1
    while True:
        if page_num == 1:
            posts_url = requests_meta['url_scheme'] + \
                requests_meta['site_domain'] + \
                '/fanclubs/'+str(user_id)+'/posts'
        else:
            posts_url = requests_meta['url_scheme'] + \
                requests_meta['site_domain'] + '/fanclubs/' + \
                str(user_id)+'/posts?page='+str(page_num)
        try:
            res = requests.get(posts_url, cookies=requests_meta['cookies'])
        except requests.exceptions.RequestException as err:
            print(err)
            return
        page_bs = BeautifulSoup(res.text, 'html.parser')
        post_links = page_bs.select('div.post')
        for post_link in post_links:
            post_title = post_link.select_one('.post-title').string
            post_date = post_link.select_one('.post-date > .mr-5')
            if post_date is None:
                post_date = post_link.select_one('.post-date').string
            else:
                post_date = post_date.string
            trans_table = str.maketrans('', '', '- :')
            post_date = post_date.translate(trans_table)

            post_href = post_link.select_one('a.link-block').get('href')
            post_id = re.search(r'\d+$', post_href).group()
            dir_name = post_id + '_' + post_title + '_' + post_date
            dir_path = savedata_dir + '/' + user_id + '/' + dir_name
            download_post(dir_path, post_id, requests_meta)
        if len(post_links) != 20:
            break
        page_num += 1


parser = argparse.ArgumentParser(description='fantia data downloader')
parser.add_argument('-i', '--id', help='target fanclub id')
parser.add_argument('-s', '--session', help='_session_id')
args = parser.parse_args()
if args.id is None:
    user_id = input('target fanclub id?\n')
else:
    user_id = args.id
if args.session is None:
    session_id = input('your _session_id?\n')
else:
    session_id = args.session

cookies = {'_session_id': session_id}

print('i='+user_id)
print('s='+session_id)

requests_meta = {
    'site_domain': 'fantia.jp',
    'url_scheme': 'https://',
    'cookies': cookies
}

get_posts(user_id, requests_meta)
