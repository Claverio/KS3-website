import os, re

filepath = '/Users/stevenchristian/Documents/claverio/P2P/koperasi-ks3/landing/cms/templates/cms/product.html'
with open(filepath, 'r') as f:
    content = f.read()

def replacer_url(m):
    return "url({% static 'cms/images/" + m.group(1) + "' %})"

content = re.sub(r"url\(['\"]?images/([^)'\"]+)['\"]?\)", replacer_url, content)

def replacer_src(m):
    return 'src="{% static \'cms/images/' + m.group(1) + '\' %}"'

content = re.sub(r'src=[\'"]images/([^\\\'"]+)[\'"]', replacer_src, content)

def replacer_href(m):
    return 'href="{% static \'cms/images/' + m.group(1) + '\' %}"'

content = re.sub(r'href=[\'"]images/([^\\\'"]+)[\'"]', replacer_href, content)

lines = content.split('\n')
split_idx = 0
for i, line in enumerate(lines):
    if '<!-- start section -->' in line:
        split_idx = i
        break

hero_lines = ['{% load static %}'] + lines[:split_idx]
content_lines = ['{% load static %}'] + lines[split_idx:]

with open('/Users/stevenchristian/Documents/claverio/P2P/koperasi-ks3/landing/cms/templates/cms/section/product_page_title.html', 'w') as f:
    f.write('\n'.join(hero_lines))

with open('/Users/stevenchristian/Documents/claverio/P2P/koperasi-ks3/landing/cms/templates/cms/section/product_content.html', 'w') as f:
    f.write('\n'.join(content_lines))

os.remove(filepath)
print('Done splitting product.html')
