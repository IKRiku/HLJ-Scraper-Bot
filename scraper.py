import requests
from bs4 import BeautifulSoup
import json
import os
import time

# --- CONFIGURATION ---
WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")
DATA_FILE = "stock.json"

# HLJ Search URLs for different grades (adjust parameters as needed based on HLJ's actual URL structure)
URLS = {
    "HG": "https://www.hlj.com/search/?q=*&productFilter=category%3AGundam%20%26%20Sci-Fi%3A%3AGunpla%3A%3AHigh%20Grade",
    "RG": "https://www.hlj.com/search/?q=*&productFilter=category%3AGundam%20%26%20Sci-Fi%3A%3AGunpla%3A%3AReal%20Grade",
    "MG": "https://www.hlj.com/search/?q=*&productFilter=category%3AGundam%20%26%20Sci-Fi%3A%3AGunpla%3A%3AMaster%20Grade",
    "PG": "https://www.hlj.com/search/?q=*&productFilter=category%3AGundam%20%26%20Sci-Fi%3A%3AGunpla%3A%3APerfect%20Grade",
    "EG": "https://www.hlj.com/search/?q=*&productFilter=category%3AGundam%20%26%20Sci-Fi%3A%3AGunpla%3A%3AEntry%20Grade"
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

def load_previous_stock():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def send_discord_alert(item, status, color):
    if not WEBHOOK_URL:
        return
    
    embed = {
        "title": f"[{item['grade']}] {item['name']}",
        "url": item['url'],
        "color": color,
        "description": f"**Status:** {status}",
        "thumbnail": {"url": item['image']}
    }
    
    requests.post(WEBHOOK_URL, json={"embeds": [embed]})
    time.sleep(1) # Prevent Discord rate-limiting

def scrape_hlj():
    current_stock = {}
    
    for grade, url in URLS.items():
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. The main container from your first screenshot
        products = soup.find_all("div", class_="search-widget-block") 
        
        for p in products:
            try:
                # 2. Extract Link & Image (from item-img-wrapper)
                link_tag = p.find("a", class_="item-img-wrapper")
                if not link_tag:
                    continue # Skip if this block isn't a real product
                    
                item_url = "https://www.hlj.com" + link_tag['href']
                
                img_tag = link_tag.find("img")
                image = img_tag['src'] if img_tag else ""
                
                # 3. Extract Name
                name_tag = p.find(class_="product-item-name")
                name = name_tag.text.strip() if name_tag else "Unknown Gunpla"
                
                # 4. Check Stock Status 
                # Your screenshot shows available items use the "release green" class
                stock_div = p.find("div", class_="stock")
                is_in_stock = False
                
                if stock_div and stock_div.find("div", class_="release green"):
                    is_in_stock = True
                
                # 5. Save to current_stock if available
                if is_in_stock:
                    current_stock[item_url] = {
                        "name": name,
                        "url": item_url,
                        "image": image,
                        "grade": grade,
                        "status": "In Stock"
                    }
            except Exception as e:
                print(f"Error parsing an item: {e}")
                continue 
                
    return current_stock
def main():
    old_stock = load_previous_stock()
    new_stock = scrape_hlj()
    
    # 1. Check for New Restocks
    for url, item in new_stock.items():
        if url not in old_stock:
            print(f"RESTOCK: {item['name']}")
            send_discord_alert(item, "✅ IN STOCK", 3066993) # Green
            
    # 2. Check for Out of Stock
    for url, item in old_stock.items():
        if url not in new_stock:
            print(f"OUT OF STOCK: {item['name']}")
            send_discord_alert(item, "❌ OUT OF STOCK", 15158332) # Red
            
    # 3. Save new state
    with open(DATA_FILE, "w") as f:
        json.dump(new_stock, f, indent=4)

if __name__ == "__main__":
    main()
