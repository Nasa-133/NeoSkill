# NeoSkill admin paneli — qo'llanma

Bu hujjat NeoSkill boshqaruv panelidan foydalanish tartibini tushuntiradi: kurs yaratishdan
tortib uni nashr qilish, test qo'shish va foydalanuvchilarni boshqarishgacha.

Texnik bilim talab qilinmaydi.

---

## 1. Kirish

1. Saytni oching va yuqori o'ng burchakdagi **Kirish** tugmasini bosing
2. Email va parolingizni kiriting
3. Administrator hisobi bilan kirsangiz avtomatik **Boshqaruv paneli**ga o'tasiz

Parolni unutsangiz — kirish sahifasidagi **«Parolni unutdingizmi?»** havolasi orqali
email'ingizga tiklash havolasi keladi. Havola 2 soat amal qiladi va bir marta ishlaydi.

> **Bir hisobda ko'pi bilan 2 ta qurilma.** Uchinchi qurilmadan kirmoqchi bo'lsangiz,
> tizim mavjud qurilmalar ro'yxatini ko'rsatadi va bittasini tanlab chiqarib yuborishni
> so'raydi. Chiqarilgan qurilma darhol tizimdan chiqadi.

---

## 2. Panel bo'limlari

Chap tomondagi menyu:

| Bo'lim | Vazifasi |
|---|---|
| **Boshqaruv paneli** | Umumiy ko'rsatkichlar va yangi arizalar |
| **Statistika** | Kurs ruxsatlari va yakunlangan test natijalari |
| **Referallar** | Takliflar, kurs ruxsatlari va yangi hisoblar uchun chegirma |
| **Kurslar** | Kurs yaratish, tahrirlash, o'quv dasturi |
| **Kategoriyalar** | Kurs yo'nalishlari |
| **Ustozlar** | O'qituvchi profillari |
| **Arizalar** | Pullik kurs arizalarini tasdiqlash |
| **Foydalanuvchilar** | Hisoblar, rollar, kurslarga ruxsat |
| **Testlar** | Mavzu testlari va savollar |
| **Fikrlar** | Bosh sahifadagi talaba fikrlari |
| **Sozlamalar** | Kompaniya, aloqa va parol tiklash emaili |

---

## 3. Birinchi kursni yaratish

Tartib muhim — har bir qadam keyingisiga kerak bo'ladi.

### 3.1. Kategoriya

**Kategoriyalar → + Kategoriya qo'shish**

- **Nomi** — masalan `Dasturlash`
- **Slug** — nom yozilganda avtomatik to'ldiriladi (`dasturlash`). Bu manzilda ko'rinadigan qism

### 3.2. Ustoz

**Ustozlar → + Ustoz qo'shish**

- Ism, lavozim, tajriba va qisqa bio
- **Rasm** — havola qo'yasiz yoki **«Kompyuterdan yuklash»** tugmasi bilan yuklaysiz.
  Tavsiya: 400×400 px, JPG/PNG/WebP, 2 MB gacha

Ustoz profili public sahifada «Amaliy tajribaga ega mutaxassislar» bo'limida ko'rinadi.

### 3.3. Kurs

**Kurslar → + Yangi kurs**

Kurs muharriri olti bo'limdan iborat. Yuqori o'ngdagi **Saqlash** tugmasi hammasi uchun umumiy.

**Asosiy**
- Kurs nomi va slug (nomdan avtomatik)
- Qisqa tavsif — katalog kartasida ko'rinadi
- To'liq tavsif — kurs sahifasida
- **Kurs muqovasi** — havola yoki kompyuterdan yuklash. Tavsiya: **1200×675 px** (16:9)

**Metadata**
- Kategoriya va ustoz (avval yaratganlaringizdan tanlanadi)
- Daraja, til, davomiylik
- **«Mavzular ketma-ket ochilsin»** — belgilangan bo'lsa, talaba test topshirmaguncha
  keyingi mavzu yopiq turadi. Odatda shunday qoldiriladi

**Narx**
- **«Bu kurs bepul»** belgilansa — talaba darhol kirish oladi, admin tasdig'i kerak emas
- Belgilanmasa — narx yoziladi va talaba **ariza** yuboradi, siz tasdiqlaysiz

**Landing**

Har qatorda bittadan yoziladi (Enter bilan yangi qator):
- **Nimalarni o'rganadi** — 3 tadan 10 tagacha
- **Kimlar uchun** — 3 tadan 8 tagacha
- **Talablar** — kamida 1 ta

Maydon ostida nechta yozilgani ko'rinib turadi.

**O'quv dasturi** — pastda alohida bo'limda tushuntirilgan.

**Nashr**
- Holat: **Qoralama** / **Nashr qilingan** / **Arxivlangan**
- Faqat **Nashr qilingan** kurs katalogda ko'rinadi
- Ro'yxatda nashr uchun talablar ✓ / ✗ bilan ko'rsatiladi. Hammasi ✓ bo'lmasa server
  nashrni qabul qilmaydi

> **Muhim:** yangi kurs yaratganda avval **Saqlash**ni bosing. Shundan keyin
> «O'quv dasturi» bo'limi ochiladi.

---

## 4. O'quv dasturi: modul, mavzu, dars

Kurs → **Tahrirlash** → **O'quv dasturi** tabi.

Tuzilma uch qavatli:

```
Modul                 (masalan «Python bilan tanishuv»)
  └─ Mavzu            (masalan «Birinchi qadamlar»)
       ├─ Dars        (video yoki matn)
       ├─ Amaliyot    (mavzuga bitta)
       └─ Test        (mavzuga bitta)
```

### Modul qo'shish

**+ Modul qo'shish** → nom yozing → **Saqlash**. Tartib avtomatik beriladi.

Har modul yonida: **↑ ↓** (tartibni o'zgartirish), **Nomini o'zgartirish**, **O'chirish**.

### Mavzu qo'shish

Modul ichidagi **+ Mavzu qo'shish**. Boshqaruv tugmalari modul bilan bir xil.

### Dars qo'shish

Mavzu ichidagi **+ Dars** tugmasi. O'ng tomondan forma ochiladi:

- **Dars nomi**
- **Turi** — Video dars yoki Matnli dars
- **Davomiyligi (daqiqa)**
- **Video havolasi** (video darsda majburiy) — pastda batafsil
- **Material havolasi** — qo'shimcha fayl yoki manba (ixtiyoriy)
- **Majburiy dars** — belgilangan bo'lsa, test ochilishi uchun bu darsni tugatish shart
- **Bepul preview** — belgilangan dars ro'yxatdan o'tmagan mehmonlarga ham ochiq bo'ladi

> **Maslahat:** har kursda kamida bitta darsni **bepul preview** qiling. Bu odamlarga
> kursni sotib olishdan oldin sifatini ko'rish imkonini beradi va sotuvni oshiradi.

Dars qatorida **Bepul preview** belgisi to'g'ridan-to'g'ri turadi — bosdingiz, saqlandi.

### Video havolasi

Qo'llab-quvvatlanadi:

| Manba | Havola ko'rinishi |
|---|---|
| Cloudflare Stream | `customer-xxx.cloudflarestream.com/<id>/iframe` |
| Kinescope | `kinescope.io/embed/<id>` |
| VdoCipher | `player.vdocipher.com/v2/?otp=...` |
| Bunny Stream | `iframe.mediadelivery.net/embed/...` |
| Gumlet | `play.gumlet.io/embed/...` |
| YouTube | `youtube.com/watch?v=...` yoki `youtu.be/...` |
| Vimeo | `vimeo.com/123456` |
| To'g'ridan-to'g'ri fayl | `.mp4`, `.webm` |

Video platformasida videoni oching, **Embed** bo'limidan havolani nusxalab qo'ying.

### Amaliyot

**+ Amaliyot** tugmasi. Topshiriq matni, namuna va qo'shimcha havola.
**Majburiy topshiriq** belgilansa, test ochilishi uchun uni bajarish shart bo'ladi.

### Test

Mavzu qatorida testning holati ko'rinadi (`Test 70%` yoki `Testsiz`).

- **+ Test qo'shish** — mavzuga test yaratadi
- **Savollarni tahrirlash →** — test sahifasiga o'tadi

---

## 5. Testlar va savollar

**Testlar** bo'limi yoki o'quv dasturidagi **«Savollarni tahrirlash →»** havolasi.

Ekran ikki qismga bo'lingan:

- **Chapda** — kursning barcha modul va mavzulari. Har mavzu yonida testi bor-yo'qligi
  va o'tish bali ko'rinadi. Mavzuni bossangiz o'ngda ochiladi
- **O'ngda** — tanlangan mavzu testi. Tepasida qayerda ishlayotganingiz yozilgan:
  `Kurs › 2-modul: Nomi › 1-mavzu: Nomi`

### Savol qo'shish

**+ Savol qo'shish** → savol matni → to'rtta variant → to'g'risini radio tugma bilan belgilang.

Qoidalar:
- Har savolda **aynan 4 ta** variant
- **Aynan bitta** to'g'ri javob
- Bo'sh variant bo'lmasin

Shartlar bajarilmasa **Testni saqlash** tugmasi faol bo'lmaydi va pastda nima yetishmayotgani yoziladi.

Savollarni **↑ ↓** bilan tartiblash, **×** bilan o'chirish mumkin.

**O'tish bali (%)** — talaba shu foizdan kam to'plasa test o'tmaydi va keyingi mavzu ochilmaydi.
Odatda 70–80%.

> Barcha o'zgarishlar **Testni saqlash** bosilgandan keyin kuchga kiradi.

---

## 6. Foydalanuvchilar

**Foydalanuvchilar** bo'limi.

### Yangi hisob yaratish

**+ Foydalanuvchi qo'shish**: ism, familiya, email, boshlang'ich parol, rol.

Parolni foydalanuvchiga o'zingiz yetkazasiz — tizim email yubormaydi.

### Rol

- **Talaba** — faqat o'z kurslarini ko'radi
- **Administrator** — butun boshqaruv paneliga kirish

### Amallar

| Tugma | Nima qiladi |
|---|---|
| **Ruxsatlar** | Foydalanuvchiga qaysi kurslar ochiqligini ko'rsatadi va o'zgartiradi |
| **Tahrirlash** | Ism, email, rol, faol/bloklangan holati |
| **Parol** | Yangi parol o'rnatadi |
| **O'chirish** | Hisobni, enrollmentlarini va progressini butunlay o'chiradi |

**Bloklangan** hisob tizimga kira olmaydi, lekin ma'lumotlari saqlanadi. Vaqtincha
to'xtatish uchun o'chirishdan ko'ra bloklash afzal.

### Kurslarga ruxsat

**Ruxsatlar** tugmasi → pastdagi ro'yxatdan kurs tanlaysiz → darhol ochiladi.
Bu ariza navbatini chetlab o'tadi, ya'ni pullik kursni to'lovsiz ochib berish mumkin.

> **Xavfsizlik:** admin o'z hisobini bloklay, o'chira yoki rolini pasaytira olmaydi —
> tizim buni rad etadi. Aks holda oxirgi administrator o'zini qulflab qo'yishi mumkin edi.

---

## 7. Arizalar

**Arizalar** bo'limi — pullik kurslarga yozilish so'rovlari.

Yuqoridagi tugmalar bilan holat bo'yicha filtr: **Kutilmoqda / Tasdiqlangan / Rad etilgan**.

Arizani bosing → o'ng tomonda tafsilot ochiladi → **Tasdiqlash** yoki **Rad etish**.

Tasdiqlaganingizdan keyin talabaga kurs darhol ochiladi.

Arizada kursning asl narxi, referral chegirmasi va chegirmadan keyingi so'ralgan narx alohida
ko'rinadi. Bu qiymatlar ariza yuborilgan paytda saqlanadi va keyingi narx yoki chegirma
o'zgarishlarida o'zgarmaydi.

### Referallar va chegirmalar

**Referallar** bo'limida har bir hisobning doimiy taklif kodi va quyidagi natijalar ko'rinadi:

- taklif havolasi orqali yangi hisob ochganlar soni;
- shu hisoblar ichida kamida bitta kursga ruxsat olganlar soni;
- alohida bepul va pullik kurs ruxsatlari soni.

Foydalanuvchini bosing, so'ng **Yangi referral uchun chegirma (%)** maydoniga 0–100 oralig'idagi
qiymatni kiriting. Bu chegirma faqat o'sha havola orqali keyin ro'yxatdan o'tadigan yangi
hisoblarga bir marta saqlanadi. Oldin ro'yxatdan o'tgan odamning chegirmasi o'zgarmaydi.

Referral kodi bir hisobni faqat ro'yxatdan o'tishda bog'laydi; mavjud hisobni boshqa taklifchiga
o'tkazmaydi. «Pullik kurs ruxsati» kurs ochilganini bildiradi, tasdiqlangan to'lov yoki daromadni
bildirmaydi.

---

## 8. Sozlamalar

**Sozlamalar** bo'limidagi qiymatlar server bazasida saqlanadi va barcha brauzerlarda bir xil
ishlaydi. Bu yerda kompaniya nomi, «Biz haqimizda» matni, manzil, yordam emaili, Telegram,
telefon, ish vaqti va sayt pastidagi matn kiritiladi. Saqlangandan keyin public aloqa va
kompaniya sahifalari darhol shu ma'lumotlardan foydalanadi.

### Parolni tiklash emaili

- **Serverdagi mavjud sozlamalar** — `backend/.env` ichidagi `EMAIL_*` qiymatlari ishlaydi.
- **Shu paneldan boshqarish** — SMTP server, port, login, parol, himoya turi va yuboruvchi
  emailini shu yerda kiritasiz.
- SMTP paroli ekranga qaytarilmaydi va bazada shifrlangan holda saqlanadi.
- Avval **Sozlamalarni saqlash**, keyin o'zingizning emailingizga **Test xatini yuborish**ni
  bosing. Test xati kelgach parolni tiklash xatlari ham shu sozlamadan yuboriladi.

`DJANGO_SECRET_KEY` SMTP parolini shifrlash kalitining bir qismi. Production kalitini
o'zgartirishdan oldin admin panelda SMTP parolini qayta kiritish kerak.

### Batafsil statistika

**Boshqaruv paneli**dagi foydalanuvchi, kurs ruxsati, kurs va kutilayotgan ariza kartalari
tegishli to'liq ro'yxatni ochadi. **Statistika** bo'limida:

- kurs ruxsatlarini bepul/pullik kurs bo'yicha filtrlash;
- foydalanuvchi yoki kurs nomi bo'yicha qidirish;
- yakunlangan testlarni o'tgan/o'tmagan natija bo'yicha filtrlash mumkin.

Filtrlar sahifa manzilida saqlanadi, shuning uchun yangilanganda yoki havola yuborilganda
tanlangan ko'rinish yo'qolmaydi. «Pullik kurs ruxsati» kurs ochilganini bildiradi; u tasdiqlangan
to'lov yoki daromad hisoboti emas.

---

## 9. Talaba nimani ko'radi

Tuzilma to'g'ri bo'lsa, talaba oqimi shunday bo'ladi:

1. Katalogdan kursni tanlaydi
2. Bepul preview darsini ko'radi
3. Bepul kursga darhol yoziladi, pullik uchun ariza yuboradi
4. Darslarni ketma-ket o'rganadi va har birini **«Darsni tugatdim»** bilan belgilaydi
5. Amaliy topshiriqni bajaradi
6. Barcha majburiy darslar tugagach **test ochiladi**
7. Testdan o'tsa — **keyingi mavzu ochiladi**
8. Progress saqlanadi va istalgan qurilmada davom ettiriladi

---

## 10. Tez-tez uchraydigan savollar

**Kurs katalogda ko'rinmayapti**
«Nashr» tabida holat **Nashr qilingan** ekanini tekshiring. Qoralama kurslar faqat
admin panelda ko'rinadi.

**Nashr qilib bo'lmayapti**
«Landing» tabidagi uch ro'yxat to'ldirilmagan. «Nashr» tabidagi ✓/✗ ro'yxati nima
yetishmayotganini ko'rsatadi.

**Test ochilmayapti**
Testda kamida bitta savol bo'lishi kerak. Talaba tomonida esa mavzudagi barcha
**majburiy** darslar tugatilgan bo'lishi shart.

**Video ko'rinmayapti**
Dars turi **Video dars** ekanini va havola to'g'ri nusxalanganini tekshiring.
Havola noto'g'ri bo'lsa pleyer «yangi oynada ochish» tugmasini ko'rsatadi.

**Uchinchi qurilmadan kira olmayapman**
Bu ataylab shunday. Ro'yxatdan bitta qurilmani tanlab chiqarib yuboring, yoki
profil sahifasidagi **«Faol qurilmalar»** bo'limidan boshqaring.

---

## 11. Video himoyasi haqida

Tizimda quyidagilar ishlaydi:

- Video havolasi faqat kursga yozilgan talabaga beriladi
- Bir hisobda ko'pi bilan 2 ta qurilma
- Video ustida talabaning emaili va vaqti turadi — belgi joyini o'zgartirib turadi
- Sahifani boshqa saytga joylashtirib bo'lmaydi

**Ekran yozib olishni to'liq to'sib bo'lmaydi** — bu brauzerda texnik jihatdan mumkin
emas. Video ustidagi belgi yozib olishni to'xtatmaydi, lekin tarqatilgan nusxa kimning
hisobidan chiqqanini ko'rsatadi. Amalda bu eng kuchli to'xtatuvchi vosita.

Qo'shimcha himoya kerak bo'lsa — DRM'li video platformasi (Kinescope, VdoCipher) va
mobil ilova orqali kuchaytiriladi.
