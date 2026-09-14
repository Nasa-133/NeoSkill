"""Fills the catalog with presentable demo content for a client walkthrough."""

from typing import Any

from django.core.management.base import BaseCommand, CommandParser
from django.db import transaction

from neoskill.assessment.models import Question, QuestionOption
from neoskill.catalog.models import (
    Category,
    Course,
    CourseFAQ,
    Instructor,
    Lesson,
    Module,
    Practice,
    Testimonial,
    Topic,
    TopicTest,
)

# Every id below was checked against YouTube's oEmbed endpoint, so the players load.
VIDEOS = {
    "python-1": "https://www.youtube.com/watch?v=fU-3YmGTWyg",
    "python-2": "https://www.youtube.com/watch?v=oo-hzL040gk",
    "html-1": "https://www.youtube.com/watch?v=xwaA2R7vJm8",
    "html-2": "https://www.youtube.com/watch?v=HAvDksj1RP0",
    "js-types": "https://www.youtube.com/watch?v=cZHHgHoEKrw",
    "js-if": "https://www.youtube.com/watch?v=f_w5Zx1yh2M",
    "js-while": "https://www.youtube.com/watch?v=f7q4DO3z0Eg",
    "js-func": "https://www.youtube.com/watch?v=BLItSQ30JqI",
    "js-object": "https://www.youtube.com/watch?v=8uypl88J8tk",
    "react-1": "https://www.youtube.com/watch?v=Qh2tRHZY-Dc",
}

CATEGORIES = [
    ("Dasturlash", "dasturlash"),
    ("Frontend", "frontend"),
    ("Dizayn", "dizayn"),
]

INSTRUCTORS = [
    {
        "name": "Sardor Karimov",
        "slug": "sardor-karimov",
        "title": "Senior Python Developer",
        "experience": "8 yillik amaliy tajriba",
        "bio": "Murakkab mavzularni sodda misollar orqali tushuntiradigan dasturchi va mentor. "
        "Fintech va ta’lim loyihalarida backend jamoalariga rahbarlik qilgan.",
    },
    {
        "name": "Madina Aliyeva",
        "slug": "madina-aliyeva",
        "title": "Product Designer",
        "experience": "6 yillik mahsulot dizayni tajribasi",
        "bio": "Foydalanuvchi tadqiqotidan prototipgacha bo‘lgan jarayonni boshqaradi. "
        "Bank va e-commerce mahsulotlarida interfeys dizayni bilan ishlagan.",
    },
    {
        "name": "Jasur Rahmonov",
        "slug": "jasur-rahmonov",
        "title": "Frontend Engineer",
        "experience": "5 yillik frontend tajribasi",
        "bio": "JavaScript va React bo‘yicha amaliyotchi. O‘quvchilarni birinchi ishga "
        "joylashgunicha kuzatib boradigan mentor.",
    },
]

QUESTION_BANK = {
    "python-basics": [
        ("Python fayli qaysi kengaytma bilan saqlanadi?", [".py", ".html", ".css", ".sql"], 0),
        ("Ekranga matn chiqaruvchi funksiya qaysi?", ["print()", "input()", "len()", "type()"], 0),
        ("Izoh (comment) qaysi belgi bilan boshlanadi?", ["#", "//", "--", "/*"], 0),
        (
            "Foydalanuvchidan ma’lumot oladigan funksiya qaysi?",
            ["input()", "print()", "open()", "str()"],
            0,
        ),
    ],
    "python-types": [
        ("3 / 2 amalining natijasi qanday turda bo‘ladi?", ["float", "int", "str", "bool"], 0),
        ("Matn turi qanday ataladi?", ["str", "text", "char", "string8"], 0),
        ("Ro‘yxat qanday qavs bilan yoziladi?", ["[ ]", "{ }", "( )", "< >"], 0),
    ],
    "html-basics": [
        ("HTML sahifaning eng tashqi tegi qaysi?", ["<html>", "<body>", "<head>", "<div>"], 0),
        ("Eng katta sarlavha tegi qaysi?", ["<h1>", "<h6>", "<title>", "<big>"], 0),
        ("Havola yaratuvchi teg qaysi?", ["<a>", "<link>", "<href>", "<url>"], 0),
        ("Rasm qo‘yish uchun qaysi teg ishlatiladi?", ["<img>", "<image>", "<pic>", "<src>"], 0),
    ],
    "html-lists": [
        ("Tartiblangan ro‘yxat qaysi teg bilan yaratiladi?", ["<ol>", "<ul>", "<li>", "<dl>"], 0),
        ("Ro‘yxat elementi qaysi teg?", ["<li>", "<ol>", "<item>", "<p>"], 0),
        ("Tartibsiz ro‘yxat qaysi teg?", ["<ul>", "<ol>", "<list>", "<nav>"], 0),
    ],
    "js-basics": [
        (
            "O‘zgaruvchini qayta tayinlanmaydigan qilib e’lon qilish uchun nima ishlatiladi?",
            ["const", "let", "var", "static"],
            0,
        ),
        ("typeof [] nima qaytaradi?", ["object", "array", "list", "undefined"], 0),
        (
            "=== operatori nimani tekshiradi?",
            ["Qiymat va tur", "Faqat qiymat", "Faqat tur", "Havola"],
            0,
        ),
        (
            "Massivga oxiridan element qo‘shadigan metod?",
            ["push()", "pop()", "shift()", "add()"],
            0,
        ),
    ],
    "js-logic": [
        (
            "Shart to‘g‘ri bo‘lmasa bajariladigan blok qaysi?",
            ["else", "elif", "otherwise", "catch"],
            0,
        ),
        (
            "while sikli qachon to‘xtaydi?",
            [
                "Shart yolg‘on bo‘lganda",
                "Har doim 10 martadan keyin",
                "break bo‘lmasa to‘xtamaydi",
                "Hech qachon",
            ],
            0,
        ),
        (
            "Funksiya qiymat qaytarish uchun qaysi kalit so‘z?",
            ["return", "yield", "give", "out"],
            0,
        ),
    ],
}


def question_set(test: TopicTest, key: str) -> None:
    for position, (text, options, correct) in enumerate(QUESTION_BANK[key], start=1):
        question = Question.objects.create(test=test, text=text, position=position)
        QuestionOption.objects.bulk_create(
            [
                QuestionOption(
                    question=question, text=option, position=index, is_correct=index - 1 == correct
                )
                for index, option in enumerate(options, start=1)
            ]
        )


class Command(BaseCommand):
    help = "Create demo courses, lessons with real YouTube videos, tests and testimonials."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete the demo courses first, so the command can be re-run cleanly.",
        )

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        slugs = ["python-asoslari-demo", "html-css-demo", "javascript-demo"]
        if options["reset"]:
            removed, _ = Course.objects.filter(slug__in=slugs).delete()
            self.stdout.write(f"Eski demo kurslar o‘chirildi ({removed} obyekt).")

        categories = {
            slug: Category.objects.get_or_create(slug=slug, defaults={"name": name})[0]
            for name, slug in CATEGORIES
        }
        instructors = {
            item["slug"]: Instructor.objects.get_or_create(slug=item["slug"], defaults=item)[0]
            for item in INSTRUCTORS
        }

        self.python_course(categories, instructors)
        self.html_course(categories, instructors)
        self.javascript_course(categories, instructors)
        self.testimonials()

        published = Course.objects.filter(slug__in=slugs).count()
        lessons = Lesson.objects.filter(topic__module__course__slug__in=slugs).count()
        tests = TopicTest.objects.filter(topic__module__course__slug__in=slugs).count()
        questions = Question.objects.filter(test__topic__module__course__slug__in=slugs).count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Tayyor: {published} kurs, {lessons} dars, {tests} test, {questions} savol."
            )
        )

    # ---------------------------------------------------------------- courses

    def _course(self, **fields: Any) -> Course | None:
        """Returns None when the demo course already exists, so re-runs stay idempotent."""
        course, created = Course.objects.get_or_create(slug=fields["slug"], defaults=fields)
        if not created:
            self.stdout.write(f"«{course.title}» allaqachon mavjud, o‘tkazib yuborildi.")
            return None
        return course

    def faqs(self, course: Course) -> None:
        entries = [
            (
                "Kursni qancha vaqtda tugataman?",
                "O‘z tezligingizda o‘qiysiz. Tavsiya etilgan jadval bo‘yicha "
                "6–8 haftada yakunlanadi.",
            ),
            (
                "Oldindan tajriba kerakmi?",
                "Yo‘q. Har bir tushuncha noldan, amaliy misollar bilan izohlanadi.",
            ),
            (
                "Progress saqlanadimi?",
                "Ha. Tugallangan dars, amaliyot va test natijalari serverda saqlanadi va "
                "istalgan qurilmada davom ettirasiz.",
            ),
            (
                "Sertifikat beriladimi?",
                "Hozirgi MVP bosqichida sertifikat berilmaydi. Bu imkoniyat keyingi "
                "mahsulot bosqichi uchun rejalashtirilgan.",
            ),
        ]
        CourseFAQ.objects.bulk_create(
            [
                CourseFAQ(course=course, question=question, answer=answer, position=position)
                for position, (question, answer) in enumerate(entries, start=1)
            ]
        )

    def python_course(
        self, categories: dict[str, Category], instructors: dict[str, Instructor]
    ) -> None:
        course = self._course(
            slug="python-asoslari-demo",
            category=categories["dasturlash"],
            instructor=instructors["sardor-karimov"],
            title="Python: noldan amaliy dasturchigacha",
            short_description="Python asoslarini real misollar orqali o‘rganib, birinchi "
            "dasturlaringizni yozasiz.",
            description="Kurs nazariya, amaliy topshiriq va mavzu testlarini bir oqimda "
            "birlashtiradi. Har bir mavzu oxirida test topshirasiz va keyingi mavzu shundan "
            "keyin ochiladi — shu tariqa bilim bo‘shliqsiz to‘planadi.",
            level=Course.Level.BEGINNER,
            language="O‘zbek",
            duration_minutes=720,
            is_free=True,
            price=None,
            status=Course.Status.PUBLISHED,
            sequential_learning=True,
            what_you_will_learn=[
                "Python sintaksisini ishonch bilan o‘qish va yozish",
                "O‘zgaruvchilar va ma’lumot turlari bilan ishlash",
                "Shart va sikllar orqali mantiq qurish",
                "Funksiyalarga ajratib, tartibli kod yozish",
                "Kichik amaliy dasturni mustaqil yakunlash",
            ],
            audience=[
                "Dasturlashni birinchi marta boshlayotganlar",
                "Boshqa kasbdan IT ga o‘tmoqchi bo‘lganlar",
                "Bilimini tizimga solmoqchi bo‘lgan o‘z-o‘zidan o‘rganuvchilar",
            ],
            requirements=[
                "Kompyuterdan foydalanish bo‘yicha boshlang‘ich bilim",
                "Haftasiga kamida 4 soat vaqt",
                "Internet va brauzer",
            ],
        )
        if course is None:
            return

        module = Module.objects.create(course=course, title="Python bilan tanishuv", position=1)
        topic = Topic.objects.create(module=module, title="Birinchi qadamlar", position=1)
        Lesson.objects.create(
            topic=topic,
            title="Python nima va u qayerda ishlatiladi?",
            position=1,
            kind=Lesson.Kind.VIDEO,
            video_url=VIDEOS["python-1"],
            content="Python nima uchun boshlovchilar uchun eng qulay til ekanini va uni qaysi "
            "sohalarda ishlatishlarini ko‘rib chiqamiz.",
            duration_minutes=14,
            is_required=True,
            free_preview=True,
        )
        Lesson.objects.create(
            topic=topic,
            title="Muhitni sozlash va birinchi dastur",
            position=2,
            kind=Lesson.Kind.VIDEO,
            video_url=VIDEOS["python-2"],
            content="Python o‘rnatamiz, loyiha papkasini tayyorlaymiz va birinchi dasturni "
            "terminalda ishga tushiramiz.",
            duration_minutes=18,
            is_required=True,
        )
        Practice.objects.create(
            topic=topic,
            instructions="Ismingiz va bugungi maqsadingizni ekranga chiqaradigan dastur yozing.",
            example='print("Salom, men Aziza. Bugun Python o‘rganaman!")',
            is_required=True,
        )
        question_set(TopicTest.objects.create(topic=topic, passing_score=70), "python-basics")

        second = Topic.objects.create(
            module=module, title="O‘zgaruvchilar va ma’lumot turlari", position=2
        )
        Lesson.objects.create(
            topic=second,
            title="Sonlar, matnlar va mantiqiy qiymatlar",
            position=1,
            kind=Lesson.Kind.TEXT,
            content="Python’da to‘rt asosiy tur bor: int, float, str va bool. Har birini "
            "qachon ishlatish kerakligini misollar bilan ko‘rib chiqamiz. int butun sonlar "
            "uchun, float kasrli sonlar uchun, str matn uchun, bool esa rost/yolg‘on uchun.",
            duration_minutes=24,
            is_required=True,
        )
        question_set(TopicTest.objects.create(topic=second, passing_score=70), "python-types")

        Module.objects.create(course=course, title="Amaliy dasturlash", position=2)
        self.faqs(course)

    def html_course(
        self, categories: dict[str, Category], instructors: dict[str, Instructor]
    ) -> None:
        course = self._course(
            slug="html-css-demo",
            category=categories["frontend"],
            instructor=instructors["jasur-rahmonov"],
            title="HTML va CSS: birinchi veb-sahifangiz",
            short_description="Noldan boshlab tirik veb-sahifa yasaysiz va uni brauzerda "
            "ishlab turganini ko‘rasiz.",
            description="Frontend yo‘lining birinchi qadami. Sahifa tuzilishini HTML bilan "
            "quramiz, ko‘rinishini CSS bilan boshqaramiz va oxirida o‘z portfolio sahifangizni "
            "yakunlaysiz.",
            level=Course.Level.BEGINNER,
            language="O‘zbek",
            duration_minutes=540,
            is_free=False,
            price="490000.00",
            status=Course.Status.PUBLISHED,
            sequential_learning=True,
            what_you_will_learn=[
                "HTML tegi va sahifa tuzilishini tushunish",
                "Ro‘yxat, jadval va havolalar bilan ishlash",
                "CSS orqali rang, shrift va joylashuvni boshqarish",
                "Mobil ekranga moslashadigan sahifa yasash",
            ],
            audience=[
                "Frontend yo‘nalishini boshlayotganlar",
                "O‘z portfolio sahifasini yasashni xohlaganlar",
                "Dizaynni kodga aylantirishni o‘rganmoqchi bo‘lganlar",
            ],
            requirements=["Kompyuter va brauzer", "Matn muharriri (VS Code tavsiya etiladi)"],
        )
        if course is None:
            return

        module = Module.objects.create(course=course, title="HTML asoslari", position=1)
        topic = Topic.objects.create(module=module, title="Sahifa tuzilishi", position=1)
        Lesson.objects.create(
            topic=topic,
            title="HTML nima va sahifa qanday tuziladi?",
            position=1,
            kind=Lesson.Kind.VIDEO,
            video_url=VIDEOS["html-1"],
            content="HTML sahifaning skeleti. html, head va body teglari nima uchun kerakligini "
            "va brauzer ularni qanday o‘qishini ko‘ramiz.",
            duration_minutes=22,
            is_required=True,
            free_preview=True,
        )
        question_set(TopicTest.objects.create(topic=topic, passing_score=70), "html-basics")

        second = Topic.objects.create(module=module, title="Ro‘yxatlar va havolalar", position=2)
        Lesson.objects.create(
            topic=second,
            title="Ro‘yxatlar bilan ishlash",
            position=1,
            kind=Lesson.Kind.VIDEO,
            video_url=VIDEOS["html-2"],
            content="Tartiblangan va tartibsiz ro‘yxatlar, ichma-ich ro‘yxatlar va ularni "
            "menyu yasashda qanday ishlatish.",
            duration_minutes=16,
            is_required=True,
        )
        Practice.objects.create(
            topic=second,
            instructions="O‘zingiz haqingizda sahifa yasang: sarlavha, qisqa matn va "
            "yoqtirgan uch narsangiz ro‘yxati bo‘lsin.",
            example="<h1>Men haqimda</h1>\n<ul>\n  <li>Kitob o‘qish</li>\n</ul>",
            is_required=True,
        )
        question_set(TopicTest.objects.create(topic=second, passing_score=70), "html-lists")

        Module.objects.create(course=course, title="CSS bilan ko‘rinish", position=2)
        self.faqs(course)

    def javascript_course(
        self, categories: dict[str, Category], instructors: dict[str, Instructor]
    ) -> None:
        course = self._course(
            slug="javascript-demo",
            category=categories["frontend"],
            instructor=instructors["jasur-rahmonov"],
            title="JavaScript: sahifani tirik qilish",
            short_description="Sahifaga mantiq qo‘shishni o‘rganib, interaktiv "
            "komponentlar yozasiz.",
            description="JavaScript frontend’ning mantiq qatlami. O‘zgaruvchidan boshlab "
            "funksiya va obyektlargacha bosqichma-bosqich o‘tamiz, har mavzuni test bilan "
            "mustahkamlaymiz.",
            level=Course.Level.INTERMEDIATE,
            language="O‘zbek",
            duration_minutes=660,
            is_free=False,
            price="590000.00",
            status=Course.Status.PUBLISHED,
            sequential_learning=True,
            what_you_will_learn=[
                "O‘zgaruvchi va ma’lumot turlarini to‘g‘ri tanlash",
                "Shart va sikllar bilan mantiq qurish",
                "Funksiyalarga ajratib, qayta ishlatiladigan kod yozish",
                "Obyekt va massivlar bilan ma’lumotni saqlash",
                "Sahifa elementlariga hodisa (event) ulash",
            ],
            audience=[
                "HTML va CSS asoslarini biladiganlar",
                "Frontend’da ishga joylashishni maqsad qilganlar",
                "React o‘rganishga tayyorlanayotganlar",
            ],
            requirements=[
                "HTML va CSS bo‘yicha boshlang‘ich bilim",
                "Haftasiga kamida 5 soat vaqt",
            ],
        )
        if course is None:
            return

        module = Module.objects.create(course=course, title="Til asoslari", position=1)
        topic = Topic.objects.create(module=module, title="O‘zgaruvchi va turlar", position=1)
        Lesson.objects.create(
            topic=topic,
            title="Ma’lumot turlari",
            position=1,
            kind=Lesson.Kind.VIDEO,
            video_url=VIDEOS["js-types"],
            content="let, const va var orasidagi farq, hamda JavaScript’dagi asosiy "
            "ma’lumot turlari.",
            duration_minutes=19,
            is_required=True,
            free_preview=True,
        )
        Lesson.objects.create(
            topic=topic,
            title="Obyektlar bilan tanishuv",
            position=2,
            kind=Lesson.Kind.VIDEO,
            video_url=VIDEOS["js-object"],
            content="Obyekt — bog‘langan ma’lumotlarni bir joyda saqlash usuli. "
            "Kalit-qiymat juftliklari va ularga murojaat qilish.",
            duration_minutes=21,
            is_required=True,
        )
        Practice.objects.create(
            topic=topic,
            instructions="O‘zingiz haqingizda obyekt yasang: ism, yosh va yoqtirgan tillar "
            "massivi bo‘lsin. Keyin uni konsolga chiqaring.",
            example="const men = { ism: 'Aziza', yosh: 21, tillar: ['uz', 'en'] };\n"
            "console.log(men.ism);",
            is_required=True,
        )
        question_set(TopicTest.objects.create(topic=topic, passing_score=75), "js-basics")

        second = Topic.objects.create(module=module, title="Shart, sikl va funksiya", position=2)
        Lesson.objects.create(
            topic=second,
            title="If / Else bilan qaror qabul qilish",
            position=1,
            kind=Lesson.Kind.VIDEO,
            video_url=VIDEOS["js-if"],
            content="Shartli operatorlar orqali dastur oqimini boshqarish.",
            duration_minutes=17,
            is_required=True,
        )
        Lesson.objects.create(
            topic=second,
            title="While va Do While sikllari",
            position=2,
            kind=Lesson.Kind.VIDEO,
            video_url=VIDEOS["js-while"],
            content="Takrorlanuvchi amallarni sikl bilan qisqartirish va cheksiz siklga "
            "tushmaslik.",
            duration_minutes=15,
            is_required=True,
        )
        Lesson.objects.create(
            topic=second,
            title="Funksiyalar",
            position=3,
            kind=Lesson.Kind.VIDEO,
            video_url=VIDEOS["js-func"],
            content="Kodni qayta ishlatiladigan bloklarga ajratish, parametr va return.",
            duration_minutes=23,
            is_required=True,
        )
        question_set(TopicTest.objects.create(topic=second, passing_score=75), "js-logic")

        advanced = Module.objects.create(course=course, title="Keyingi qadam: React", position=2)
        react_topic = Topic.objects.create(
            module=advanced, title="React bilan tanishuv", position=1
        )
        Lesson.objects.create(
            topic=react_topic,
            title="React’da marshrutlash xatolari",
            position=1,
            kind=Lesson.Kind.VIDEO,
            video_url=VIDEOS["react-1"],
            content="JavaScript asoslarini o‘zlashtirgach React’da nima kutayotganiga qisqa nazar.",
            duration_minutes=12,
            is_required=False,
        )
        self.faqs(course)

    def testimonials(self) -> None:
        entries = [
            (
                "Aziza Sobirova",
                "Junior dasturchi",
                "Darslar ketma-ketligi va har mavzudagi test o‘rganishni ancha "
                "osonlashtirdi. Uch oyda birinchi ishimga joylashdim.",
            ),
            (
                "Jasur Rahmonov",
                "Talaba",
                "Har mavzudan keyingi test qayerda xato qilayotganimni ko‘rsatdi. "
                "Shu tufayli bo‘shliqlar qolmadi.",
            ),
            (
                "Madina Toshpulatova",
                "Frontend dasturchi",
                "Amaliy topshiriqlar eng foydali qism bo‘ldi — har darsdan keyin "
                "darhol o‘zim yozib ko‘rdim.",
            ),
            (
                "Bekzod Umarov",
                "O‘qituvchi",
                "Progress saqlanishi juda qulay. Ishdan keyin qolgan joyimdan davom ettirardim.",
            ),
        ]
        for position, (name, title, quote) in enumerate(entries, start=1):
            Testimonial.objects.get_or_create(
                author_name=name,
                defaults={
                    "author_title": title,
                    "quote": quote,
                    "is_published": True,
                    "position": position,
                },
            )
