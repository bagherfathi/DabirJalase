# گزارش بررسی کدبیس - DabirJalase

## خلاصه وضعیت پروژه

پروژه شما یک **اسکلت اولیه (Scaffold)** برای یک اپلیکیشن رونویسی جلسات با تمرکز بر زبان فارسی است. ساختار کلی پروژه خوب طراحی شده اما اکثر کامپوننت‌ها هنوز **استاب (Stub)** هستند و نیاز به پیاده‌سازی کامل دارند.

---

## ✅ آنچه که پیاده‌سازی شده است

### 1. ساختار پروژه
- ✅ **هسته Kotlin/JVM**: اینترفیس‌ها و مدل‌های داده برای pipeline اصلی
- ✅ **اپلیکیشن دسکتاپ Java**: اسکلت JavaFX با کلاس‌های placeholder
- ✅ **سرویس Python**: API REST با FastAPI برای STT، TTS، Diarization، و Summarization
- ✅ **مدیریت Session**: سیستم مدیریت جلسات با ذخیره‌سازی و export

### 2. معماری Pipeline
- ✅ `MeetingPipeline`: هسته اصلی که VAD، STT، Diarization، و Summarization را به هم متصل می‌کند
- ✅ `ConversationState`: مدیریت وضعیت مکالمه و ذخیره‌سازی سخنرانان
- ✅ سیستم Export: خروجی Markdown و JSON برای transcripts

### 3. API Endpoints (Python)
- ✅ `/transcribe` - رونویسی متن
- ✅ `/vad` - تشخیص فعالیت صوتی
- ✅ `/sessions/{id}/ingest` - دریافت و پردازش صدا
- ✅ `/sessions/{id}/summary` - خلاصه‌سازی جلسه
- ✅ `/sessions/{id}/export` - خروجی transcript
- ✅ `/sessions/{id}/search` - جستجو در transcript
- ✅ `/tts` - تبدیل متن به گفتار
- ✅ `/sessions/{id}/speakers` - برچسب‌گذاری سخنرانان

---

## ❌ آنچه که باید پیاده‌سازی شود

### 1. **STT (Speech-to-Text) با کیفیت بالا برای فارسی**
**وضعیت فعلی:**
- `WhisperService` فقط یک استاب است که متن ورودی را بدون تغییر برمی‌گرداند
- هیچ مدل واقعی Whisper یا Vosk پیاده‌سازی نشده

**نیاز به پیاده‌سازی:**
```python
# باید در python_services/stt/whisper_service.py پیاده‌سازی شود:
- استفاده از Whisper large-v3 با پشتیبانی فارسی
- یا WhisperX برای هم‌راستایی بهتر
- یا Vosk Farsi model برای حالت آفلاین
- پشتیبانی از GPU (CUDA) برای سرعت بیشتر
- بازگشت partial hypotheses برای نمایش زنده
```

**پیشنهاد:**
- استفاده از `openai-whisper` یا `faster-whisper` برای STT
- مدل `large-v3` برای بهترین دقت فارسی
- استفاده از `onnxruntime` برای اجرای محلی و سریع‌تر

---

### 2. **TTS (Text-to-Speech) با کیفیت بالا برای فارسی**
**وضعیت فعلی:**
- `TextToSpeechService` فقط متن را به bytes تبدیل می‌کند

**نیاز به پیاده‌سازی:**
```python
# باید در python_services/tts/tts_service.py پیاده‌سازی شود:
- Microsoft Azure Neural Farsi voices (بهترین کیفیت)
- یا Google Cloud Wavenet Farsi
- یا Coqui TTS با مدل محلی VITS
- Cache کردن صداهای رایج برای کاهش latency
- پشتیبانی از SSML برای کنترل prosody
```

**پیشنهاد:**
- اولویت با Azure Cognitive Services (کیفیت بالا)
- Fallback به Coqui TTS برای حالت آفلاین

---

### 3. **Speaker Identification (شناسایی سخنران)**
**وضعیت فعلی:**
- `DiarizationService` فقط بر اساس hash متن سخنران را تشخیص می‌دهد
- `EnergyCentroidDiarizationEngine` در Kotlin یک پیاده‌سازی ساده مبتنی بر انرژی است

**نیاز به پیاده‌سازی:**
```python
# باید در python_services/diarization/diarization_service.py پیاده‌سازی شود:
- استفاده از pyannote.audio 3.1 برای diarization
- یا SpeechBrain ECAPA-TDNN برای استخراج embeddings
- ذخیره‌سازی gallery از embeddings سخنرانان
- جستجوی similarity برای شناسایی سخنرانان جدید
- پشتیبانی از overlapping speech
```

**نیاز به پیاده‌سازی در Java/Kotlin:**
- UI برای پرسیدن "who is this?" هنگام شناسایی سخنران جدید
- ذخیره‌سازی نام‌های سخنرانان و ارتباط با embeddings

**پیشنهاد:**
- استفاده از `pyannote.audio` با مدل `pyannote/speaker-diarization-3.1`
- استخراج embeddings با `speechbrain/spkrec-ecapa-voxceleb`

---

### 4. **Automatic Silence Detection (VAD)**
**وضعیت فعلی:**
- `SimpleVad` در Python یک پیاده‌سازی ساده مبتنی بر threshold است
- `VadGate` در Java فقط یک placeholder است

**نیاز به پیاده‌سازی:**
```python
# باید در python_services/vad/simple_vad.py یا یک ماژول جدید پیاده‌سازی شود:
- استفاده از Silero VAD (ONNX Runtime)
- یا WebRTC VAD
- تشخیص دقیق شروع و پایان گفتار
- ارسال سریع chunk به STT پس از تشخیص سکوت
```

**نیاز به پیاده‌سازی در Java:**
```java
// باید در desktop-app/src/main/java/com/meetingassistant/audio/VadGate.java پیاده‌سازی شود:
- استفاده از Silero VAD ONNX Runtime
- یا WebRTC VAD bindings
- تشخیص real-time و ارسال chunk به Python service
```

**پیشنهاد:**
- استفاده از Silero VAD (مدل ONNX سبک و سریع)
- یا WebRTC VAD برای دقت بیشتر

---

### 5. **Audio Capture (ضبط صدا)**
**وضعیت فعلی:**
- `CaptureService` در Java فقط یک استاب است
- `startCapture()` یک `UnsupportedOperationException` پرتاب می‌کند

**نیاز به پیاده‌سازی:**
```java
// باید در desktop-app/src/main/java/com/meetingassistant/audio/CaptureService.java پیاده‌سازی شود:
- استفاده از javax.sound.sampled برای Windows/macOS/Linux
- یا WASAPI loopback برای Windows
- یا CoreAudio برای macOS
- یا PulseAudio/PipeWire برای Linux
- تبدیل به PCM format مناسب (16kHz, mono, 16-bit)
- ارسال frames به VAD و سپس به Python service
```

**برای Android (اگر نیاز باشد):**
- استفاده از Oboe یا AudioRecord
- ارسال stream به Python service از طریق gRPC

---

### 6. **Noise Suppression (کاهش نویز)**
**وضعیت فعلی:**
- `PassThroughSuppressor` در Kotlin فقط صدا را بدون تغییر برمی‌گرداند

**نیاز به پیاده‌سازی:**
```kotlin
// باید در src/main/kotlin/com/dabir/core/audio/PassThroughSuppressor.kt پیاده‌سازی شود:
- استفاده از RNNoise (ONNX Runtime)
- یا NSNet2
- یا WebRTC AudioProcessing
- کاهش نویز قبل از VAD و STT
```

**پیشنهاد:**
- استفاده از RNNoise ONNX model (سبک و موثر)
- یا WebRTC AudioProcessing برای کیفیت بالاتر

---

### 7. **UI Components (اجزای رابط کاربری)**
**وضعیت فعلی:**
- `ChatTimeline` و `SpeakerPrompt` فقط placeholder هستند

**نیاز به پیاده‌سازی:**
```java
// باید در desktop-app/src/main/java/com/meetingassistant/ui/ پیاده‌سازی شود:
- ChatTimeline: نمایش transcript به صورت chat-style با نام سخنران
- SpeakerPrompt: دیالوگ "who is this?" هنگام شناسایی سخنران جدید
- نمایش live transcript با RTL support برای فارسی
- نمایش confidence scores و trust cues
- دکمه export برای خلاصه جلسه
```

**پیشنهاد:**
- استفاده از JavaFX با پشتیبانی RTL
- یا Compose Multiplatform برای cross-platform بهتر

---

### 8. **Summarization (خلاصه‌سازی)**
**وضعیت فعلی:**
- `KeywordSummarizer` فقط جملات را به bullet points تبدیل می‌کند

**نیاز به پیاده‌سازی:**
```python
# باید در python_services/summarization/summarizer.py پیاده‌سازی شود:
- استفاده از LLM (GPT-4o-mini یا Llama 3 8B-instruct)
- تولید bullet points و action items
- Citation back-links به timestamps
- Faithfulness scoring
```

**پیشنهاد:**
- استفاده از GPT-4o-mini برای کیفیت بالا
- یا Llama 3 8B-instruct برای حالت آفلاین

---

### 9. **Focus on Main Speaker (تمرکز بر سخنران اصلی)**
**وضعیت فعلی:**
- هیچ پیاده‌سازی وجود ندارد

**نیاز به پیاده‌سازی:**
```kotlin
// باید در MeetingPipeline یا یک ماژول جدید پیاده‌سازی شود:
- محاسبه energy level برای هر سخنران
- تشخیص سخنران با بیشترین energy
- تاکید UI روی سخنران فعال
- کاهش volume سایر سخنرانان در محیط پرنویز
```

---

### 10. **gRPC Streaming (ارسال جریان صدا)**
**وضعیت فعلی:**
- `GrpcClient` در Java فقط یک placeholder است

**نیاز به پیاده‌سازی:**
```java
// باید در desktop-app/src/main/java/com/meetingassistant/transport/GrpcClient.java پیاده‌سازی شود:
- تعریف protobuf contracts برای audio streaming
- bi-directional streaming برای ارسال صدا و دریافت transcript
- backpressure handling برای جلوگیری از overflow
- reconnection logic برای قطعی شبکه
```

---

## 📋 نقشه راه پیشنهادی برای تولید اپلیکیشن

### فاز 1: پیاده‌سازی Core Features (4-6 هفته)

#### هفته 1-2: Audio Capture & VAD
1. پیاده‌سازی `CaptureService` در Java با `javax.sound.sampled`
2. پیاده‌سازی Silero VAD (ONNX Runtime) در Java
3. تست capture و VAD با فایل‌های صوتی نمونه

#### هفته 2-3: STT با کیفیت بالا
1. پیاده‌سازی Whisper large-v3 در Python
2. پشتیبانی از GPU (CUDA) برای سرعت
3. تست دقت با فایل‌های فارسی نمونه
4. هدف: WER < 15%

#### هفته 3-4: Speaker Diarization
1. پیاده‌سازی pyannote.audio در Python
2. استخراج embeddings با ECAPA-TDNN
3. پیاده‌سازی gallery برای ذخیره‌سازی سخنرانان
4. تست با جلسات چندنفره

#### هفته 4-5: UI Components
1. پیاده‌سازی `ChatTimeline` با JavaFX
2. پیاده‌سازی `SpeakerPrompt` برای "who is this?"
3. پشتیبانی RTL برای فارسی
4. نمایش live transcript

#### هفته 5-6: TTS & Summarization
1. پیاده‌سازی Azure TTS یا Coqui TTS
2. پیاده‌سازی LLM summarization
3. Export به Markdown/JSON
4. تست end-to-end

---

### فاز 2: بهبود کیفیت و Performance (2-3 هفته)

1. **Noise Suppression**: پیاده‌سازی RNNoise یا WebRTC
2. **Focus on Main Speaker**: الگوریتم تشخیص سخنران اصلی
3. **gRPC Streaming**: پیاده‌سازی streaming برای latency کمتر
4. **Caching**: Cache کردن TTS و embeddings
5. **Performance Tuning**: بهینه‌سازی latency و resource usage

---

### فاز 3: Cross-Platform & Polish (2-3 هفته)

1. **Android App**: اگر نیاز باشد، پیاده‌سازی Android client
2. **Installer**: ساخت installer برای Windows/macOS/Linux
3. **Testing**: تست‌های جامع و smoke tests
4. **Documentation**: مستندات کاربر و توسعه‌دهنده

---

## 🛠️ پیشنهادات تکنولوژی

### برای STT:
- **اولویت 1**: `faster-whisper` با مدل `large-v3` (بهترین دقت فارسی)
- **اولویت 2**: `openai-whisper` (راحت‌تر برای شروع)
- **Fallback**: `vosk` با مدل فارسی (برای CPU-only)

### برای TTS:
- **اولویت 1**: Microsoft Azure Neural Farsi (بهترین کیفیت)
- **اولویت 2**: Google Cloud Text-to-Speech Farsi
- **Fallback**: Coqui TTS با مدل محلی

### برای Diarization:
- **اولویت**: `pyannote.audio` 3.1 با `pyannote/speaker-diarization-3.1`
- **Embeddings**: `speechbrain/spkrec-ecapa-voxceleb`

### برای VAD:
- **اولویت**: Silero VAD (ONNX Runtime) - سبک و سریع
- **Alternative**: WebRTC VAD

### برای Noise Suppression:
- **اولویت**: RNNoise (ONNX Runtime)
- **Alternative**: WebRTC AudioProcessing

### برای Summarization:
- **اولویت**: GPT-4o-mini (API)
- **Fallback**: Llama 3 8B-instruct (local)

---

## 📝 نکات مهم

1. **کیفیت اولویت دارد**: طبق گفته شما، کیفیت مهم‌تر از زبان برنامه‌نویسی است. Python برای ML بهتر است، اما می‌توانید از Java/Kotlin برای UI استفاده کنید.

2. **Cross-Platform**: ساختار فعلی شما از Java/Kotlin برای desktop و Python برای services استفاده می‌کند که مناسب است.

3. **مدل‌های محلی vs Cloud**: برای privacy و offline mode، مدل‌های محلی (Whisper ONNX، Coqui TTS) بهتر هستند. اما برای کیفیت بالاتر، cloud services (Azure TTS) بهترند.

4. **Performance**: استفاده از GPU برای Whisper و pyannote ضروری است برای latency پایین.

5. **Testing**: باید فایل‌های صوتی نمونه فارسی برای تست دقت STT و diarization داشته باشید.

---

## 🎯 نتیجه‌گیری

پروژه شما یک **اسکلت خوب** دارد اما نیاز به **پیاده‌سازی کامل** کامپوننت‌های اصلی دارد. با توجه به نیازهای شما:

✅ **ساختار پروژه**: خوب طراحی شده  
⚠️ **پیاده‌سازی**: نیاز به کار زیاد دارد  
✅ **معماری**: مناسب برای cross-platform  

**زمان تخمینی برای MVP**: 8-12 هفته با یک تیم 2-3 نفره

**اولویت‌های فوری:**
1. Audio Capture در Java
2. STT با Whisper
3. Speaker Diarization
4. UI Components

اگر می‌خواهید، می‌توانم شروع به پیاده‌سازی هر یک از این کامپوننت‌ها کنم.

