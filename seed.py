import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid
from app.database import SessionLocal, engine
from app.models import Language, Institution
from app.utils.security import get_password_hash


LANGUAGES = [
    {"name": "Abkhaz", "code": "ab", "native_name": " аҧсшәа"},
    {"name": "Acehnese", "code": "ace", "native_name": "Bahsa Acèh"},
    {"name": "Acholi", "code": "ach", "native_name": "Acoli"},
    {"name": "Afar", "code": "aa", "native_name": "Afar"},
    {"name": "Afrikaans", "code": "af", "native_name": "Afrikaans"},
    {"name": "Albanian", "code": "sq", "native_name": "Shqip"},
    {"name": "Alur", "code": "alz", "native_name": "Alur"},
    {"name": "Amharic", "code": "am", "native_name": "አማርኛ"},
    {"name": "Arabic", "code": "ar", "native_name": "العربية"},
    {"name": "Armenian", "code": "hy", "native_name": "Հայերեն"},
    {"name": "Assamese", "code": "as", "native_name": "অসমীয়া"},
    {"name": "Avar", "code": "av", "native_name": "Авар"},
    {"name": "Awadhi", "code": "awa", "native_name": "अवधी"},
    {"name": "Aymara", "code": "ay", "native_name": "Aymar aru"},
    {"name": "Azerbaijani", "code": "az", "native_name": "Azərbaycanca"},
    {"name": "Balinese", "code": "ban", "native_name": "Basa Bali"},
    {"name": "Baluchi", "code": "bal", "native_name": "بلوچی"},
    {"name": "Bambara", "code": "bm", "native_name": "Bamanankan"},
    {"name": "Baoule", "code": "bci", "native_name": "Baoulé"},
    {"name": "Bashkir", "code": "ba", "native_name": "Башҡорт"},
    {"name": "Basque", "code": "eu", "native_name": "Euskara"},
    {"name": "Batak Karo", "code": "btx", "native_name": "Karo"},
    {"name": "Batak Simalungun", "code": "bts", "native_name": "Simalungun"},
    {"name": "Batak Toba", "code": "bbc", "native_name": "Hata Batak Toba"},
    {"name": "Belarusian", "code": "be", "native_name": "Беларуская"},
    {"name": "Bemba", "code": "bem", "native_name": "Ichibemba"},
    {"name": "Bengali", "code": "bn", "native_name": "বাংলা"},
    {"name": "Betawi", "code": "bew", "native_name": "Betawi"},
    {"name": "Bhojpuri", "code": "bho", "native_name": "भोजपुरी"},
    {"name": "Bikol", "code": "bik", "native_name": "Bikol"},
    {"name": "Bosnian", "code": "bs", "native_name": "Bosanski"},
    {"name": "Breton", "code": "br", "native_name": "Brezhoneg"},
    {"name": "Bulgarian", "code": "bg", "native_name": "Български"},
    {"name": "Buryat", "code": "bua", "native_name": "Буряад"},
    {"name": "Cantonese", "code": "yue", "native_name": "粵語"},
    {"name": "Catalan", "code": "ca", "native_name": "Català"},
    {"name": "Cebuano", "code": "ceb", "native_name": "Cebuano"},
    {"name": "Chamorro", "code": "ch", "native_name": "Chamoru"},
    {"name": "Chechen", "code": "ce", "native_name": "Нохчийн"},
    {"name": "Chichewa", "code": "ny", "native_name": "Chichewa"},
    {"name": "Chinese (Simplified)", "code": "zh-CN", "native_name": "中文（简体）"},
    {"name": "Chinese (Traditional)", "code": "zh-TW", "native_name": "中文（繁體）"},
    {"name": "Chuukese", "code": "chk", "native_name": "Chuukese"},
    {"name": "Chuvash", "code": "cv", "native_name": "Чăваш"},
    {"name": "Corsican", "code": "co", "native_name": "Corsu"},
    {"name": "Crimean Tatar (Cyrillic)", "code": "crh", "native_name": "Къырымтатар"},
    {"name": "Crimean Tatar (Latin)", "code": "crh-Latn", "native_name": "Qırımtatarca"},
    {"name": "Croatian", "code": "hr", "native_name": "Hrvatski"},
    {"name": "Czech", "code": "cs", "native_name": "Čeština"},
    {"name": "Danish", "code": "da", "native_name": "Dansk"},
    {"name": "Dari", "code": "prs", "native_name": "دری"},
    {"name": "Dhivehi", "code": "dv", "native_name": "ދިވެހި"},
    {"name": "Dinka", "code": "din", "native_name": "Thuɔŋjäŋ"},
    {"name": "Dogri", "code": "doi", "native_name": "डोगरी"},
    {"name": "Dombe", "code": "dov", "native_name": "Dombe"},
    {"name": "Dutch", "code": "nl", "native_name": "Nederlands"},
    {"name": "Dyula", "code": "dyu", "native_name": "Dyula"},
    {"name": "Dzongkha", "code": "dz", "native_name": "རྫོང་ཁ"},
    {"name": "English", "code": "en", "native_name": "English"},
    {"name": "Esperanto", "code": "eo", "native_name": "Esperanto"},
    {"name": "Estonian", "code": "et", "native_name": "Eesti"},
    {"name": "Ewe", "code": "ee", "native_name": "Eʋegbe"},
    {"name": "Faroese", "code": "fo", "native_name": "Føroyskt"},
    {"name": "Fijian", "code": "fj", "native_name": "Na Vosa Vakaviti"},
    {"name": "Filipino", "code": "fil", "native_name": "Filipino"},
    {"name": "Finnish", "code": "fi", "native_name": "Suomi"},
    {"name": "Fon", "code": "fon", "native_name": "Fon"},
    {"name": "French", "code": "fr", "native_name": "Français"},
    {"name": "French (Canada)", "code": "fr-CA", "native_name": "Français (Canada)"},
    {"name": "Frisian", "code": "fy", "native_name": "Frysk"},
    {"name": "Friulian", "code": "fur", "native_name": "Furlan"},
    {"name": "Fulani", "code": "ff", "native_name": "Fulfulde"},
    {"name": "Ga", "code": "gaa", "native_name": "Gã"},
    {"name": "Galician", "code": "gl", "native_name": "Galego"},
    {"name": "Georgian", "code": "ka", "native_name": "ქართული"},
    {"name": "German", "code": "de", "native_name": "Deutsch"},
    {"name": "Greek", "code": "el", "native_name": "Ελληνικά"},
    {"name": "Guarani", "code": "gn", "native_name": "Avañe'ẽ"},
    {"name": "Gujarati", "code": "gu", "native_name": "ગુજરાતી"},
    {"name": "Haitian Creole", "code": "ht", "native_name": "Kreyòl ayisyen"},
    {"name": "Hakha Chin", "code": "cnh", "native_name": "Hakha Chin"},
    {"name": "Hausa", "code": "ha", "native_name": "Hausa"},
    {"name": "Hawaiian", "code": "haw", "native_name": "ʻŌlelo Hawaiʻi"},
    {"name": "Hebrew", "code": "he", "native_name": "עברית"},
    {"name": "Hiligaynon", "code": "hil", "native_name": "Hiligaynon"},
    {"name": "Hindi", "code": "hi", "native_name": "हिन्दी"},
    {"name": "Hmong", "code": "hmn", "native_name": "Hmong"},
    {"name": "Hungarian", "code": "hu", "native_name": "Magyar"},
    {"name": "Hunsrik", "code": "hrx", "native_name": "Hunsrik"},
    {"name": "Iban", "code": "iba", "native_name": "Iban"},
    {"name": "Icelandic", "code": "is", "native_name": "Íslenska"},
    {"name": "Igbo", "code": "ig", "native_name": "Asụsụ Igbo"},
    {"name": "Ilocano", "code": "ilo", "native_name": "Ilokano"},
    {"name": "Indonesian", "code": "id", "native_name": "Bahasa Indonesia"},
    {"name": "Inuktut (Latin)", "code": "iu-Latn", "native_name": "Inuktut"},
    {"name": "Inuktut (Syllabics)", "code": "iu-Cans", "native_name": "ᐃᓄᒃᑎᑐᑦ"},
    {"name": "Irish", "code": "ga", "native_name": "Gaeilge"},
    {"name": "Italian", "code": "it", "native_name": "Italiano"},
    {"name": "Jamaican Patois", "code": "jam", "native_name": "Patois"},
    {"name": "Japanese", "code": "ja", "native_name": "日本語"},
    {"name": "Javanese", "code": "jv", "native_name": "Basa Jawa"},
    {"name": "Jingpo", "code": "kac", "native_name": "Jingpo"},
    {"name": "Kalaallisut", "code": "kl", "native_name": "Kalaallisut"},
    {"name": "Kannada", "code": "kn", "native_name": "ಕನ್ನಡ"},
    {"name": "Kanuri", "code": "kr", "native_name": "Kanuri"},
    {"name": "Kapampangan", "code": "pam", "native_name": "Kapampangan"},
    {"name": "Kazakh", "code": "kk", "native_name": "Қазақша"},
    {"name": "Khasi", "code": "kha", "native_name": "Khasi"},
    {"name": "Khmer", "code": "km", "native_name": "ខ្មែរ"},
    {"name": "Kiga", "code": "cgg", "native_name": "Runyankole-Rukiga"},
    {"name": "Kikongo", "code": "kg", "native_name": "Kikongo"},
    {"name": "Kinyarwanda", "code": "rw", "native_name": "Ikinyarwanda"},
    {"name": "Kituba", "code": "ktu", "native_name": "Kituba"},
    {"name": "Kokborok", "code": "trp", "native_name": "Kokborok"},
    {"name": "Komi", "code": "kv", "native_name": "Коми"},
    {"name": "Konkani", "code": "kok", "native_name": "कोंकणी"},
    {"name": "Korean", "code": "ko", "native_name": "한국어"},
    {"name": "Krio", "code": "kri", "native_name": "Krio"},
    {"name": "Kurdish (Kurmanji)", "code": "ku", "native_name": "Kurdî"},
    {"name": "Kurdish (Sorani)", "code": "ckb", "native_name": "کوردی"},
    {"name": "Kyrgyz", "code": "ky", "native_name": "Кыргызча"},
    {"name": "Lao", "code": "lo", "native_name": "ລາວ"},
    {"name": "Latgalian", "code": "ltg", "native_name": "Latgalīšu"},
    {"name": "Latin", "code": "la", "native_name": "Latina"},
    {"name": "Latvian", "code": "lv", "native_name": "Latviešu"},
    {"name": "Ligurian", "code": "lij", "native_name": "Ligure"},
    {"name": "Limburgish", "code": "li", "native_name": "Limburgs"},
    {"name": "Lingala", "code": "ln", "native_name": "Lingala"},
    {"name": "Lithuanian", "code": "lt", "native_name": "Lietuvių"},
    {"name": "Lombard", "code": "lmo", "native_name": "Lombard"},
    {"name": "Luganda", "code": "lg", "native_name": "Luganda"},
    {"name": "Luo", "code": "luo", "native_name": "Dholuo"},
    {"name": "Luxembourgish", "code": "lb", "native_name": "Lëtzebuergesch"},
    {"name": "Macedonian", "code": "mk", "native_name": "Македонски"},
    {"name": "Madurese", "code": "mad", "native_name": "Madhurâ"},
    {"name": "Maithili", "code": "mai", "native_name": "मैथिली"},
    {"name": "Makassar", "code": "mak", "native_name": "Basa Mangkasara'"},
    {"name": "Malagasy", "code": "mg", "native_name": "Malagasy"},
    {"name": "Malay", "code": "ms", "native_name": "Bahasa Melayu"},
    {"name": "Malay (Jawi)", "code": "ms-Arab", "native_name": "بهاس ملايو"},
    {"name": "Malayalam", "code": "ml", "native_name": "മലയാളം"},
    {"name": "Maltese", "code": "mt", "native_name": "Malti"},
    {"name": "Mam", "code": "mam", "native_name": "Mam"},
    {"name": "Manx", "code": "gv", "native_name": "Gaelg"},
    {"name": "Maori", "code": "mi", "native_name": "Māori"},
    {"name": "Marathi", "code": "mr", "native_name": "मराठी"},
    {"name": "Marshallese", "code": "mh", "native_name": "Kajin M̧ajeļ"},
    {"name": "Marwadi", "code": "mwr", "native_name": "मारवाड़ी"},
    {"name": "Mauritian Creole", "code": "mfe", "native_name": "Kreol Morisien"},
    {"name": "Meadow Mari", "code": "mhr", "native_name": "Олык марий"},
    {"name": "Minang", "code": "min", "native_name": "Minangkabau"},
    {"name": "Mizo", "code": "lus", "native_name": "Mizo"},
    {"name": "Mongolian", "code": "mn", "native_name": "Монгол"},
    {"name": "Myanmar (Burmese)", "code": "my", "native_name": "မြန်မာ"},
    {"name": "Nahuatl (Eastern Huasteca)", "code": "nhe", "native_name": "Nahuatl"},
    {"name": "Ndau", "code": "ndc", "native_name": "Ndau"},
    {"name": "Ndebele (South)", "code": "nr", "native_name": "isiNdebele"},
    {"name": "Nepalbhasa (Newari)", "code": "new", "native_name": "नेपाल भाषा"},
    {"name": "Nepali", "code": "ne", "native_name": "नेपाली"},
    {"name": "N'Ko", "code": "nqo", "native_name": "ߒߞߏ"},
    {"name": "Norwegian", "code": "no", "native_name": "Norsk"},
    {"name": "Nuer", "code": "nus", "native_name": "Naath"},
    {"name": "Occitan", "code": "oc", "native_name": "Occitan"},
    {"name": "Odia (Oriya)", "code": "or", "native_name": "ଓଡ଼ିଆ"},
    {"name": "Oromo", "code": "om", "native_name": "Afaan Oromoo"},
    {"name": "Ossetian", "code": "os", "native_name": "Ирон"},
    {"name": "Pangasinan", "code": "pag", "native_name": "Pangasinan"},
    {"name": "Papiamento", "code": "pap", "native_name": "Papiamentu"},
    {"name": "Pashto", "code": "ps", "native_name": "پښتو"},
    {"name": "Persian", "code": "fa", "native_name": "فارسی"},
    {"name": "Polish", "code": "pl", "native_name": "Polski"},
    {"name": "Portuguese (Brazil)", "code": "pt-BR", "native_name": "Português (Brasil)"},
    {"name": "Portuguese (Portugal)", "code": "pt-PT", "native_name": "Português (Portugal)"},
    {"name": "Punjabi (Gurmukhi)", "code": "pa", "native_name": "ਪੰਜਾਬੀ"},
    {"name": "Punjabi (Shahmukhi)", "code": "pa-Arab", "native_name": "پنجابی"},
    {"name": "Quechua", "code": "qu", "native_name": "Runa Simi"},
    {"name": "Qʼeqchiʼ", "code": "kek", "native_name": "Q'eqchi'"},
    {"name": "Romani", "code": "rom", "native_name": "Romani"},
    {"name": "Romanian", "code": "ro", "native_name": "Română"},
    {"name": "Rundi", "code": "rn", "native_name": "Ikirundi"},
    {"name": "Russian", "code": "ru", "native_name": "Русский"},
    {"name": "Sami (North)", "code": "se", "native_name": "Davvisámegiella"},
    {"name": "Samoan", "code": "sm", "native_name": "Gagana Samoa"},
    {"name": "Sango", "code": "sg", "native_name": "Sängö"},
    {"name": "Sanskrit", "code": "sa", "native_name": "संस्कृतम्"},
    {"name": "Santali", "code": "sat", "native_name": "ᱥᱟᱱᱛᱟᱲᱤ"},
    {"name": "Scots Gaelic", "code": "gd", "native_name": "Gàidhlig"},
    {"name": "Sepedi", "code": "nso", "native_name": "Sesotho sa Leboa"},
    {"name": "Serbian", "code": "sr", "native_name": "Српски"},
    {"name": "Sesotho", "code": "st", "native_name": "Sesotho"},
    {"name": "Seychellois Creole", "code": "crs", "native_name": "Kreol Seselwa"},
    {"name": "Shan", "code": "shn", "native_name": "ၽႃႇသႃႇတႆး"},
    {"name": "Shona", "code": "sn", "native_name": "chiShona"},
    {"name": "Sicilian", "code": "scn", "native_name": "Sicilianu"},
    {"name": "Silesian", "code": "szl", "native_name": "Ślůnski"},
    {"name": "Sindhi", "code": "sd", "native_name": "سنڌي"},
    {"name": "Sinhala", "code": "si", "native_name": "සිංහල"},
    {"name": "Slovak", "code": "sk", "native_name": "Slovenčina"},
    {"name": "Slovenian", "code": "sl", "native_name": "Slovenščina"},
    {"name": "Somali", "code": "so", "native_name": "Soomaali"},
    {"name": "Spanish", "code": "es", "native_name": "Español"},
    {"name": "Sundanese", "code": "su", "native_name": "Basa Sunda"},
    {"name": "Susu", "code": "sus", "native_name": "Sosoxui"},
    {"name": "Swahili", "code": "sw", "native_name": "Kiswahili"},
    {"name": "Swati", "code": "ss", "native_name": "siSwati"},
    {"name": "Swedish", "code": "sv", "native_name": "Svenska"},
    {"name": "Tagalog", "code": "tl", "native_name": "Tagalog"},
    {"name": "Tahitian", "code": "ty", "native_name": "Reo Tahiti"},
    {"name": "Tajik", "code": "tg", "native_name": "Тоҷикӣ"},
    {"name": "Tamazight", "code": "tzm", "native_name": "Tamazight"},
    {"name": "Tamil", "code": "ta", "native_name": "தமிழ்"},
    {"name": "Tatar", "code": "tt", "native_name": "Татарча"},
    {"name": "Telugu", "code": "te", "native_name": "తెలుగు"},
    {"name": "Tetum", "code": "tet", "native_name": "Tetum"},
    {"name": "Thai", "code": "th", "native_name": "ไทย"},
    {"name": "Tibetan", "code": "bo", "native_name": "བོད་ཡིག"},
    {"name": "Tigrinya", "code": "ti", "native_name": "ትግርኛ"},
    {"name": "Tiv", "code": "tiv", "native_name": "Tiv"},
    {"name": "Tok Pisin", "code": "tpi", "native_name": "Tok Pisin"},
    {"name": "Tongan", "code": "to", "native_name": "Lea faka-Tonga"},
    {"name": "Tsonga", "code": "ts", "native_name": "Xitsonga"},
    {"name": "Tswana", "code": "tn", "native_name": "Setswana"},
    {"name": "Tulu", "code": "tcy", "native_name": "ತುಳು"},
    {"name": "Tumbuka", "code": "tum", "native_name": "chiTumbuka"},
    {"name": "Turkish", "code": "tr", "native_name": "Türkçe"},
    {"name": "Turkmen", "code": "tk", "native_name": "Türkmençe"},
    {"name": "Tuvan", "code": "tyv", "native_name": "Тыва дыл"},
    {"name": "Twi", "code": "tw", "native_name": "Twi"},
    {"name": "Udmurt", "code": "udm", "native_name": "Удмурт кыл"},
    {"name": "Ukrainian", "code": "uk", "native_name": "Українська"},
    {"name": "Urdu", "code": "ur", "native_name": "اردو"},
    {"name": "Uyghur", "code": "ug", "native_name": "ئۇيغۇرچە"},
    {"name": "Uzbek", "code": "uz", "native_name": "Oʻzbekcha"},
    {"name": "Venda", "code": "ve", "native_name": "Tshivenḓa"},
    {"name": "Venetian", "code": "vec", "native_name": "Vèneto"},
    {"name": "Vietnamese", "code": "vi", "native_name": "Tiếng Việt"},
    {"name": "Waray", "code": "war", "native_name": "Waray"},
    {"name": "Welsh", "code": "cy", "native_name": "Cymraeg"},
    {"name": "Wolof", "code": "wo", "native_name": "Wolof"},
    {"name": "Xhosa", "code": "xh", "native_name": "isiXhosa"},
    {"name": "Yakut", "code": "sah", "native_name": "Саха тыла"},
    {"name": "Yiddish", "code": "yi", "native_name": "ייִדיש"},
    {"name": "Yoruba", "code": "yo", "native_name": "Yorùbá"},
    {"name": "Yucatec Maya", "code": "yua", "native_name": "Maya"},
    {"name": "Zapotec", "code": "zap", "native_name": "Zapotec"},
    {"name": "Zulu", "code": "zu", "native_name": "isiZulu"},
]


INSTITUTIONS = [
    {"name": "University of Nairobi", "code": "UON"},
    {"name": "University of Ghana", "code": "UG"},
    {"name": "University of Lagos", "code": "UL"},
]

USERS = [
    {
        "email": "admin@curriculum.edu",
        "password": "admin123",
        "role": "admin",
        "institution_code": None,
    },
    {
        "email": "teacher@curriculum.edu",
        "password": "teacher123",
        "role": "teacher",
        "institution_code": "UON",
    },
    {
        "email": "student@curriculum.edu",
        "password": "student123",
        "role": "student",
        "institution_code": "UON",
    },
    {
        "email": "translator@curriculum.edu",
        "password": "translator123",
        "role": "translator",
        "institution_code": "UON",
    },
]


def seed():
    from app.models.base import Base
    from app.models.user import User

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        for lang_data in LANGUAGES:
            existing = (
                db.query(Language).filter(Language.code == lang_data["code"]).first()
            )
            if not existing:
                language = Language(**lang_data)
                db.add(language)

        for inst_data in INSTITUTIONS:
            existing = (
                db.query(Institution)
                .filter(Institution.code == inst_data["code"])
                .first()
            )
            if not existing:
                institution = Institution(**inst_data)
                db.add(institution)

        db.commit()

        for user_data in USERS:
            existing = db.query(User).filter(User.email == user_data["email"]).first()
            if not existing:
                institution_id = None
                if user_data["institution_code"]:
                    inst = (
                        db.query(Institution)
                        .filter(Institution.code == user_data["institution_code"])
                        .first()
                    )
                    if inst:
                        institution_id = inst.id

                user = User(
                    id=uuid.uuid4(),
                    email=user_data["email"],
                    hashed_password=get_password_hash(user_data["password"]),
                    role=user_data["role"],
                    is_active=True,
                    institution_id=institution_id,
                )
                db.add(user)

        db.commit()
        print(
            f"Seeded {len(LANGUAGES)} languages, {len(INSTITUTIONS)} institutions, {len(USERS)} users"
        )

    except Exception as e:
        db.rollback()
        print(f"Seed error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
