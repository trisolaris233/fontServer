# coding: utf-8

import os
import re
import json
import datetime
import requests
import sqlite3

from urllib import parse
from bs4 import BeautifulSoup

from flask import Flask, flash, request, redirect, url_for
from flask import request
from flask import render_template
from werkzeug.utils import secure_filename


# 一般用户代理
GENERAL_HEADERS = {
    'Host': 'www.ztxz.cn',
    'Referer': "http://www.ztxz.cn/search?search=%s" % parse.quote('sunshine+ice'),
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36'
}
DATABASE_NAME = os.path.join(os.path.dirname(__file__), "../fonts.db")
UPLOAD_FOLDER = "../fonts"
PREVIEW_HOST = "http://www.ztxz.cn"
PREVIEW_API_URL = "http://www.ztxz.cn/search"
ALLOWED_EXTENSIONS = set(['ttf', 'otf', 'woff', 'svg', 'woff2'])
reg_url_pic = re.compile(r'https?://.*?(jpg|png|gif)')
reg_url_font = re.compile(r'https?://.*?(ttf|otf|woff|svg|woff2)')


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SECRET_KEY'] = os.urandom(24)


class font(object):
    def __init__(
        self,
        name=None,
        url=None, 
        preview=None
    ):
        self.name = name
        self.url = url
        self.preview = preview

# 上传字体
def upload_font(fontname, preview_pic=None, **kwargs):
    pass

# 判断图片url正确
def chk_valid_pic_url(pic_url):
    return reg_url_pic.match(pic_url) != None

# 判断字体url正确
def chk_valid_font_url(font_url):
    return '.' in font_url and \
           font_url.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 插入字体
def insert_font(fontname, fonturl, preview_pic=None):
    conn = sqlite3.connect(DATABASE_NAME)
    if not chk_valid_font_url(fonturl):
        return (False, "Invalid url of font")

    try:
        insert_table_cmd = '''
        INSERT INTO LOCALFONTS(
            fontname, fonturl, preview
        ) VALUES(?, ?, ?)
        '''
        conn.execute(insert_table_cmd, (fontname, fonturl, preview_pic))
    except sqlite3.Error as e:
        return (False, "Failed in inserting data into the database - %s" % e.args[0])
    conn.commit()
    conn.close()
    return (True, "Successfully")

# 获取后缀名
def get_extension(filename):
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else None

# 获取字体预览
def search_for_font_preview(fontname):
    response = requests.get("%s?search=%s" % (PREVIEW_API_URL, parse.quote(fontname)), headers=GENERAL_HEADERS)
    text = response.text

    soup = BeautifulSoup(text, 'html.parser')
    res = soup.find_all("img", attrs={"data-toggle":"tooltip", "data-placement":"top"})


    if len(res) > 0:
        content = requests.get("%s%s" % (PREVIEW_HOST, res[0].attrs['src']), headers=GENERAL_HEADERS).content
        extension = get_extension(res[0].attrs['src'])
        preview_path = "scripts/static/preview/" + str(int(datetime.datetime.now().timestamp())) + "." + extension
        ofstream = open(preview_path, "wb+")
        ofstream.write(content)

        return (True,'/static/preview/' + str(int(datetime.datetime.now().timestamp())) + "." + extension)
    return (False, "Cannot find preview matched")
    


# 初始化
def init():
    conn = sqlite3.connect(DATABASE_NAME)
    try:
        create_table_cmd = '''
        CREATE TABLE IF NOT EXISTS LOCALFONTS(
            id INTEGER PRIMARY KEY NOT NULL,
            fontname TEXT NOT NULL,
            preview TEXT,
            fonturl TEXT NOT NULL
        );
        '''
        conn.execute(create_table_cmd)
    except sqlite3.Error as e:
        return (False, "Failed in creating tables - %s" % e.args[0])
    conn.commit()
    conn.close()
    return (True, "Successfully")

# 从数据库中读取字体
def read_fonts(pagesize = -1):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()
    rlist = []

    c.execute("SELECT * FROM LOCALFONTS;")
    if pagesize < 0:
        tmplist = c.fetchall()
    else:
        tmplist = c.fetchmany(pagesize)
    # print(type(tmplist))
    for line in tmplist:
        # print(type(line))
        # print(line)
        rlist.append(font(line[1], line[3], line[2]))
    return rlist

# 在本地查找名为fontname的字体
def find_font_by_name(fontname):
    conn = sqlite3.connect(DATABASE_NAME)
    c = conn.cursor()

    c.execute("SELECT * FROM LOCALFONTS WHERE fontname='%s'" % fontname)
    row = c.fetchone()

    if not row:
        return False
    return (True, font(row[1], row[3], row[2]))

    
# 上传页
@app.route('/contribute', methods=['GET', 'POST'])
def contribute():
    if request.method == 'POST':
        if 'file' not in request.files:
            return render_template('contribute.html', error="No file")
        if 'filename' not in request.form:
            return render_template('contribute.html', error="You are ought to input the name of the font you contribute.")
        enable_preview = request.form.getlist('enable_preview')[0]

        f = request.files['file']
        new_file_name = request.form['filename']

        if f.filename == '':
            return render_template('contribute.html', error="No file was selected")
        if new_file_name == '':
            return render_template('contribute.html', error="Invalid filename")
            
        

        if chk_valid_font_url(f.filename):
            origin_filename = f.filename
            basepath = os.path.dirname(__file__)
            second_path = 'static/fonts/%s.%s' % (new_file_name, get_extension(origin_filename))
            upload_path = os.path.join(basepath, second_path)
            print(upload_path)
            if os.path.exists(upload_path):
                return render_template('contribute.html', error="The font that has the same name has been here! Do you want to change one?")
            
            preview = None
            preview_src = None

            # 如果启用了预览
            # 则获取预览图像地址
            if enable_preview != '':
                preview = search_for_font_preview(new_file_name)
                print(preview)
                if preview[0]:
                    preview_src = preview[1]

            # 插入数据库
            res = insert_font(new_file_name, "/static/fonts/%s.%s" % (new_file_name, get_extension(origin_filename)), preview_src)
            if res[0]:
                # 保存到本地
                print(upload_path)
                f.save(upload_path)
                return render_template('contribute.html', success="thank you for your contribution!")
            else:
                return render_template('contribute.html', error=res[1])
            
            
            # flash("thank you for your contributing!")
            
            # return redirect(url_for('contribute'))
        else:
            return render_template('contribute.html', error="invalid file")
    else:

        return render_template('contribute.html')


@app.route('/fonts/<fontname>/')
def fontpage(fontname):
    f = find_font_by_name(fontname)
    if f[0]:
        print(f[1].preview)
        return render_template('font.html', fobj=f[1], contributor="offical")
    return render_template('404.html')



@app.route('/')
def index():
    res = read_fonts(-1)
    return render_template('index.html', fonts=res)

init()
# if __name__ == "__main__":
#     # 初始化数据库
#     init()
#     app.run(host='0.0.0.0', port=2333)

#     print(init()[1])
#     print(insert_font("consolas4", "https://lose7.org/uploads/1.png")[1])