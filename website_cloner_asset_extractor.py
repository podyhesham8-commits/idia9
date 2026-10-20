import os
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import requests


def scrape_website(target_url, log_callback, finish_callback):
  try:
    log_callback(f"[*] جاري الاتصال بالموقع: {target_url}\n")

    # تنظيف وتجهيز المجلد لحفظ الملفات
    parsed_url = urlparse(target_url)
    domain_name = parsed_url.netloc.replace(":", "_")
    output_dir = os.path.join("Downloaded_Sites", domain_name)

    if not os.path.exists(output_dir):
      os.makedirs(output_dir)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
            " like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }

    response = requests.get(target_url, headers=headers, timeout=15)
    if response.status_code != 200:
      log_callback(f"[!] خطأ في الوصول للموقع. كود الاستجابة: {response.status_code}\n")
      finish_callback()
      return

    soup = BeautifulSoup(response.text, "html.parser")

    # حفظ الصفحة الرئيسية
    index_path = os.path.join(output_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
      f.write(response.text)
    log_callback("[+] تم حفظ الصفحة الرئيسية (index.html)\n")

    # تجميع كل الروابط والملفات (صور، js، css، روابط فرعية)
    assets = set()

    # جلب الصور
    for img in soup.find_all("img"):
      src = img.get("src")
      if src:
        assets.add(urljoin(target_url, src))

    # جلب ملفات الـ CSS
    for link in soup.find_all("link"):
      href = link.get("href")
      if href:
        assets.add(urljoin(target_url, href))

    # جلب ملفات الـ JS
    for script in soup.find_all("script"):
      src = script.get("src")
      if src:
        assets.add(urljoin(target_url, src))

    # جلب الروابط الفرعية الداخلية (Sub-links)
    sub_links = set()
    for a in soup.find_all("a"):
      href = a.get("href")
      if href:
        full_url = urljoin(target_url, href)
        # التأكد إن الرابط يتبع نفس النطاق (Domain) عشان ما يطلعش لموقع تاني
        if urlparse(full_url).netloc == parsed_url.netloc:
          sub_links.add(full_url)

    log_callback(
        f"[*] تم العثور على {len(assets)} ملف (صور/أكواد) و {len(sub_links)}"
        " رابط فرعي.\n"
    )

    # تحميل الأصول (Assets)
    for asset_url in assets:
      try:
        file_data = requests.get(asset_url, headers=headers, timeout=10)
        if file_data.status_code == 200:
          # استخراج مسار الملف المحلي
          parsed_asset = urlparse(asset_url)
          asset_path = parsed_asset.lstrip("/")
          # تنظيف المسار
          local_file_path = os.path.join(
              output_dir, os.path.basename(parsed_asset.path)
          )
          if len(parsed_asset.path) > 1:
            # حفظ الملف
            with open(local_file_path, "wb") as f:
              f.write(file_data.content)
            log_callback(f"[تحميل] {os.path.basename(parsed_asset.path)}\n")
      except Exception as e:
        pass

    # زيارة وتحميل محتوى الروابط الفرعية أيضاً
    for sub_url in sub_links:
      try:
        log_callback(f"[*] جاري سحب الرابط الفرعي: {sub_url}\n")
        sub_res = requests.get(sub_url, headers=headers, timeout=10)
        if sub_res.status_code == 200:
          # حفظ الصفحة الفرعية كملف HTML داخل المجلد
          sub_name = (
              urlparse(sub_url).path.strip("/").replace("/", "_")
              or "sub_page"
          )
          if not sub_name.endswith(".html"):
            sub_name += ".html"
          sub_file_path = os.path.join(output_dir, sub_name)
          with open(sub_file_path, "w", encoding="utf-8") as f:
            f.write(sub_res.text)
      except Exception as e:
        pass

    log_callback(f"\n[✔] اكتمل التحميل بنجاح! تم حفظ الملفات في مجلد: {output_dir}\n")

  except Exception as e:
    log_callback(f"[x] حدث خطأ غير متوقع: {str.str(e)}\n")

  finish_callback()


class ScraperApp:

  def __init__(self, root):
    self.root = root
    self.root.title("Pody Web Ripper Pro")
    self.root.geometry("650x500")
    self.root.config(bg="#1e1e1e")

    # العنوان
    title_label = tk.Label(
        root,
        text="Web Site & Assets Downloader",
        font=("Arial", 16, "bold"),
        bg="#1e1e1e",
        fg="#00ffcc",
    )
    title_label.pack(pady=10)

    # إدخال الرابط
    url_frame = tk.Frame(root, bg="#1e1e1e")
    url_frame.pack(pady=5, fill=tk.X, padx=20)

    tk.Label(
        url_frame,
        text="رابط الموقع:",
        font=("Arial", 11),
        bg="#1e1e1e",
        fg="white",
    ).pack(side=tk.LEFT, padx=5)

    self.url_entry = tk.Entry(
        url_frame,
        font=("Arial", 11),
        bg="#2d2d2d",
        fg="white",
        insertbackground="white",
    )
    self.url_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

    # زر البدء
    self.start_btn = tk.Button(
        root,
        text="بدء السحب والتحميل",
        font=("Arial", 12, "bold"),
        bg="#00aa55",
        fg="white",
        command=self.start_scraping,
    )
    self.start_btn.pack(pady=10)

    # صندوق المخرجات (Logs)
    self.log_area = scrolledtext.ScrolledText(
        root, font=("Consolas", 10), bg="#121212", fg="#00ff00"
    )
    self.log_area.pack(expand=True, fill=tk.BOTH, padx=20, pady=10)

  def log(self, message):
    self.log_area.insert(tk.END, message)
    self.log_area.see(tk.END)

  def start_scraping(self):
    url = self.url_entry.get().strip()
    if not url:
      messagebox.showerror("خطأ", "برجاء إدخال رابط صحيح!")
      return

    if not url.startswith("http"):
      url = "https://" + url

    self.start_btn.config(state=tk.DISABLED)
    self.log_area.delete(1.0, tk.END)

    # تشغيل المهمة في Thread منفصل عشان البرنامج ما يهنقش
    threading.Thread(
        target=scrape_website,
        args=(url, self.log, self.enable_btn),
        daemon=True,
    ).start()

  def enable_btn(self):
    self.start_btn.config(state=tk.NORMAL)


if __name__ == "__main__":
  root = tk.Tk()
  app = ScraperApp(root)
  root.mainloop()