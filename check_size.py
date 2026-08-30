"""Check dataset size for export planning"""
import psycopg2

conn = psycopg2.connect(host='localhost', port=54329, user='postgres', password='devpass', dbname='wedding_vendors')
cur = conn.cursor()

cur.execute("SELECT pg_size_pretty(pg_database_size('wedding_vendors'))")
print('DB size:', cur.fetchone()[0])

cur.execute("SELECT COUNT(*) FROM vendors")
print('Vendors:', cur.fetchone()[0])
cur.execute("SELECT COUNT(*) FROM vendor_reviews")
print('Reviews:', cur.fetchone()[0])
cur.execute("SELECT SUM(LENGTH(review_text))/1024/1024 FROM vendor_reviews")
print('Review text total MB:', round(cur.fetchone()[0] or 0, 1))

cur.close(); conn.close()