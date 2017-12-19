import logging
import json
import csv
import sys
import pdb
import re

def macys_reviews(text):
    for s in re.findall('<span class="m_[\w]+-BVRRReviewText[^>]+>([^>]+)</span', text):
        yield { "retailer" : "macys", "review" : s.replace("&#39;","'") }

def bloomingdales_reviews(text):
    for s in re.findall('<span class="m_[\w]+-BVRRReviewText[^>]+>([^>]+)</span', text):
        yield { "retailer" : "bloomingdales", "review" : s.replace("&#39;","'") }

def nordstrom_reviews(text):
    for s in re.findall('<span class="m_[\w\-]+-BVRRReviewText[^>]+>([^>]+)</span', text):
        yield { "retailer" : "nordstrom", "review" : s.replace("&#39;","'") }

def ulta_reviews(text):
    for s in re.findall('<p class="m_[\w\-]+-pr-comments[^>]+>([^<]+)</p', text):
        yield { "retailer" : "ulta", "review" : s.replace("&#39;","'") }

def sephora_reviews(text):
    for s in re.findall('<div class="m_[\w\-]+x526xf[^>]+>([^>]+)</div', text):
        yield { "retailer" : "sephora", "review" : s.replace("&#39;","'") }

def reviews_from_file(extractor, filename):
    with open(filename, "r") as f:
        lines = []
        while 1:
            line = f.readline()
            if not line: break
            lines.append(line)
        for review in extractor("".join(lines)):
            yield review


writer = csv.DictWriter(sys.stdout, fieldnames=["retailer","review"])
writer.writeheader()
for r in reviews_from_file(sephora_reviews, "../tests/sephora_reviews.txt"):
    writer.writerow(r)
for r in reviews_from_file(macys_reviews, "../tests/macys_reviews_part1.txt"):
    writer.writerow(r)
for r in reviews_from_file(macys_reviews, "../tests/macys_reviews_part2.txt"):
    writer.writerow(r)
for r in reviews_from_file(bloomingdales_reviews, "../tests/bloomingdales_reviews.txt"):
    writer.writerow(r)
for r in reviews_from_file(nordstrom_reviews, "../tests/nordstrom_reviews.txt"):
    writer.writerow(r)
for r in reviews_from_file(ulta_reviews, "../tests/ulta_reviews1.txt"):
    writer.writerow(r)
for r in reviews_from_file(ulta_reviews, "../tests/ulta_reviews2.txt"):
    writer.writerow(r)
for r in reviews_from_file(ulta_reviews, "../tests/ulta_reviews3.txt"):
    writer.writerow(r)
for r in reviews_from_file(ulta_reviews, "../tests/ulta_reviews4.txt"):
    writer.writerow(r)
for r in reviews_from_file(ulta_reviews, "../tests/ulta_reviews5.txt"):
    writer.writerow(r)
for r in reviews_from_file(ulta_reviews, "../tests/ulta_reviews6.txt"):
    writer.writerow(r)
for r in reviews_from_file(ulta_reviews, "../tests/ulta_reviews7.txt"):
    writer.writerow(r)
for r in reviews_from_file(ulta_reviews, "../tests/ulta_reviews8.txt"):
    writer.writerow(r)
for r in reviews_from_file(ulta_reviews, "../tests/ulta_reviews9.txt"):
    writer.writerow(r)
for r in reviews_from_file(ulta_reviews, "../tests/ulta_reviews10.txt"):
    writer.writerow(r)
