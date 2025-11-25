# راهنمای اجرا روی ویندوز

## ✅ کد روی ویندوز اجرا می‌شود!

کد شما **cross-platform** است و روی ویندوز، لینوکس و macOS کار می‌کند.

---

## 📋 پیش‌نیازها

### 1. Java 21+
```powershell
# بررسی نسخه Java
java -version

# اگر نصب نیست، از اینجا دانلود کنید:
# https://adoptium.net/
```

### 2. Maven
```powershell
# بررسی نسخه Maven
mvn -version

# اگر نصب نیست:
# https://maven.apache.org/download.cgi
```

### 3. Python 3.9+
```powershell
# بررسی نسخه Python
python --version

# اگر نصب نیست:
# https://www.python.org/downloads/
```

---

## 🚀 مراحل اجرا

### مرحله 1: راه‌اندازی Python Services

```powershell
# رفتن به پوشه Python services
cd python_services

# نصب dependencies
pip install -r requirements.txt

# راه‌اندازی سرویس (در یک terminal جدا)
python -m python_services
```

**نکته:** سرویس روی `http://localhost:8000` اجرا می‌شود.

---

### مرحله 2: کامپایل و اجرای Desktop App

**گزینه 1: با Maven (توصیه می‌شود)**

```powershell
# رفتن به پوشه desktop-app
cd desktop-app

# کامپایل پروژه
mvn clean compile

# اجرای اپلیکیشن
mvn exec:java -Dexec.mainClass="com.meetingassistant.app.MainApplication"
```

**گزینه 2: با JavaFX Modules (اگر گزینه 1 کار نکرد)**

```powershell
# کامپایل
mvn clean package

# اجرا با module path
java --module-path "C:\path\to\javafx\lib" --add-modules javafx.controls,javafx.fxml -cp "target\classes;target\dependency\*" com.meetingassistant.app.MainApplication
```

---

## ⚠️ مشکلات احتمالی و راه حل

### مشکل 1: JavaFX پیدا نمی‌شود

**خطا:** `Error: JavaFX runtime components are missing`

**راه حل:**
1. JavaFX را دانلود کنید: https://openjfx.io/
2. یا از Java 21+ استفاده کنید که JavaFX را شامل می‌شود

### مشکل 2: میکروفون کار نمی‌کند

**خطا:** `LineUnavailableException`

**راه حل:**
1. بررسی کنید میکروفون در Windows Settings فعال است
2. دسترسی میکروفون به برنامه را بدهید
3. میکروفون را به عنوان default input device تنظیم کنید

### مشکل 3: Python service متصل نمی‌شود

**خطا:** `سرویس در دسترس نیست`

**راه حل:**
1. مطمئن شوید Python service در حال اجرا است
2. بررسی کنید port 8000 آزاد است:
   ```powershell
   netstat -an | findstr 8000
   ```
3. اگر port اشغال است، در `MainApplication.java` آدرس را تغییر دهید

### مشکل 4: فونت فارسی نمایش داده نمی‌شود

**راه حل:**
- Windows به طور پیش‌فرض فونت‌های فارسی دارد
- اگر مشکل داشتید، فونت Tahoma یا Arial را نصب کنید

---

## 🔧 تنظیمات اختیاری

### تغییر آدرس Python Service

در `MainApplication.java` خط 48:
```java
httpClient = new HttpClient("http://localhost:8000");
```

### تنظیم API Keys (اختیاری)

برای استفاده از Azure TTS و OpenAI Summarization:

```powershell
# در PowerShell
$env:AZURE_SPEECH_KEY="your_key"
$env:AZURE_SPEECH_REGION="eastus"
$env:OPENAI_API_KEY="your_key"
$env:HUGGINGFACE_TOKEN="your_token"
```

---

## 📝 تست سریع

1. ✅ Python service را اجرا کنید
2. ✅ Desktop app را اجرا کنید
3. ✅ دکمه "شروع ضبط" را بزنید
4. ✅ صحبت کنید
5. ✅ متن باید در UI نمایش داده شود

---

## 🐛 Debug Mode

اگر مشکلی پیش آمد، لاگ‌ها را بررسی کنید:

```powershell
# اجرا با verbose logging
mvn exec:java -Dexec.mainClass="com.meetingassistant.app.MainApplication" -Dexec.args="-Djava.util.logging.config.file=logging.properties"
```

---

## ✅ نتیجه

**کد شما روی ویندوز اجرا می‌شود!** نیازی به رفتن به اوبونتو نیست.

اگر مشکلی پیش آمد، لاگ‌ها را بررسی کنید و به من بگویید.

