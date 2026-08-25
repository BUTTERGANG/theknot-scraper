"""Embed dashboard data into HTML as standalone file"""
import json

with open('/home/alex/code/BUTTERGANG/theknot-scraper/dashboard_data.json') as f:
    data = json.load(f)

with open('/home/alex/code/BUTTERGANG/theknot-scraper/dashboard.html') as f:
    html = f.read()

data_json = json.dumps(data)
embed_line = 'const EMBEDDED_DATA = %s;\n\n' % data_json

# Replace the fetch attempt with just using embedded data
html = html.replace(
    'return EMBEDDED_DATA || null;',
    'return EMBEDDED_DATA;'
)

# Insert the data before the loadData call
insert_point = html.find('loadData().then')
if insert_point > 0:
    html = html[:insert_point] + embed_line + '\n' + html[insert_point:]

out = '/home/alex/code/BUTTERGANG/theknot-scraper/dashboard_final.html'
with open(out, 'w') as f:
    f.write(html)

print('Dashboard size: %s bytes' % len(html))
print('Data embedded: %s bytes' % len(data_json))
print('Saved: %s' % out)