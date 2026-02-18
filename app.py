from flask import Flask, render_template, request, jsonify, send_file
import feedparser
import requests
import os
import json
from datetime import datetime
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.colors import HexColor
import re

app = Flask(__name__)

DEFAULT_FEEDS = [
    {"name": "Hacker News", "url": "https://news.ycombinator.com/rss", "category": "Tech"},
    {"name": "Cal Newport", "url": "https://calnewport.com/feed/", "category": "Productivity"},
    {"name": "Gear Patrol", "url": "https://www.gearpatrol.com/feed/", "category": "Gear"},
    {"name": "Wired", "url": "https://www.wired.com/feed/rss", "category": "Tech"},
    {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index", "category": "Tech"},
]

def fetch_articles(feeds, max_per_feed=5):
    articles = []
    for feed in feeds:
        try:
            parsed = feedparser.parse(feed["url"])
            for entry in parsed.entries[:max_per_feed]:
                articles.append({
                    "title": entry.get("title", "No title"),
                    "summary": re.sub('<[^<]+?>', '', entry.get("summary", entry.get("description", "")))[:500],
                    "url": entry.get("link", ""),
                    "source": feed["name"],
                    "category": feed["category"],
                    "published": entry.get("published", "")
                })
        except Exception as e:
            print(f"Error fetching {feed['name']}: {e}")
    return articles

def generate_pdf(articles, title="Daily Digest"):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
        rightMargin=0.75*inch, leftMargin=0.75*inch,
        topMargin=0.75*inch, bottomMargin=0.75*inch)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('T', parent=styles['Title'], fontSize=24, textColor=HexColor('#1a1a1a'), spaceAfter=6)
    date_style = ParagraphStyle('D', parent=styles['Normal'], fontSize=11, textColor=HexColor('#666666'), spaceAfter=20)
    heading_style = ParagraphStyle('H', parent=styles['Heading2'], fontSize=13, textColor=HexColor('#1a1a1a'), spaceBefore=14, spaceAfter=4)
    meta_style = ParagraphStyle('M', parent=styles['Normal'], fontSize=9, textColor=HexColor('#888888'), spaceAfter=6)
    body_style = ParagraphStyle('B', parent=styles['Normal'], fontSize=10, textColor=HexColor('#333333'), leading=14, spaceAfter=10)
    cat_style = ParagraphStyle('C', parent=styles['Normal'], fontSize=9, textColor=HexColor('#ffffff'), backColor=HexColor('#333333'), spaceBefore=16, spaceAfter=8, borderPadding=(4,6,4,6))

    story.append(Paragraph(title, title_style))
    story.append(Paragraph(datetime.now().strftime("%A, %B %d, %Y"), date_style))
    story.append(HRFlowable(width="100%", thickness=1, color=HexColor('#cccccc')))
    story.append(Spacer(1, 12))

    current_category = None
    for article in articles:
        if article['category'] != current_category:
            current_category = article['category']
            story.append(Paragraph(f"  {current_category.upper()}  ", cat_style))
        story.append(Paragraph(article['title'], heading_style))
        story.append(Paragraph(f"{article['source']} - {article['published'][:16] if article['published'] else ''}", meta_style))
        if article['summary']:
            story.append(Paragraph(article['summary'][:400], body_style))
        story.append(HRFlowable(width="100%", thickness=0.5, color=HexColor('#eeeeee')))

    doc.build(story)
    buffer.seek(0)
    return buffer

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/fetch', methods=['POST'])
def fetch():
    feeds = request.json.get('feeds', DEFAULT_FEEDS)
    return jsonify(fetch_articles(feeds))

@app.route('/api/generate', methods=['POST'])
def generate():
    data = request.json
    pdf = generate_pdf(data.get('articles', []), data.get('title', 'Daily Digest'))
    return send_file(pdf, mimetype='application/pdf', as_attachment=True,
        download_name=f"digest-{datetime.now().strftime('%Y-%m-%d')}.pdf")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
