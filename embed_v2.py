"""Embed data into dashboard v2"""
import json

with open('/home/alex/code/BUTTERGANG/theknot-scraper/dashboard_data.json') as f:
    data = json.load(f)

with open('/home/alex/code/BUTTERGANG/theknot-scraper/dashboard_v2.html') as f:
    html = f.read()

data_json = json.dumps(data)
html = html.replace('EMBEDDED_DATA_PLACEHOLDER', data_json)

out = '/home/alex/code/BUTTERGANG/theknot-scraper/index.html'
with open(out, 'w') as f:
    f.write(html)

print('Final size: %d bytes' % len(html))
print('Saved: %s' % out)