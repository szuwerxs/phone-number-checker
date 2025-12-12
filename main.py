import phonenumbers
from phonenumbers import geocoder, carrier, timezone, PhoneNumberFormat
import requests
from bs4 import BeautifulSoup

# if u are some shitty skid who copy pastes this code without understanding it
# and then wonders why it doesn't work properly, please read the phonenumbers docs
# also if u use this code for illegal activities, remember that I'm not responsible for that
# if u steal this code, at least give me credit, thx bye skiddo

VOIP_PREFIXES = ["4470", "4484", "4487", "4857", "4858"]
DISPOSABLE_PREFIXES = ["4475", "4478", "4879"]
PREMIUM_PREFIXES = ["900", "901", "902", "905", "976"]
CORPORATE_PREFIXES = ["700", "800", "801", "804"]
CALLCENTER_HINTS = ["callcenter", "telemarket", "contact-center"]

SUSPICIOUS_CARRIERS = [
    "GlobalTel", "Call4Free", "VoipPlanet", "SapoTel", "EuroGlobal"
]

SPAM_SOURCES = [
    "nieznany-numer.pl",
    "sync.me",
    "tellows.com",
    "tnie.pl"
]

KEYWORDS_SPAM = ["scam"]

def phone_osint(phone_number, hlr_api=None):
    try:
        parsed = phonenumbers.parse(phone_number)
    except:
        return {"error": "Invalid phone number format"}

    info = {}

    info["📞 Phone number"] = phone_number
    info["🌍 Country"] = geocoder.description_for_number(parsed, "en") or "Unknown"
    info["🏢 Carrier"] = carrier.name_for_number(parsed, "en") or "Unknown"
    info["🕒 Timezone"] = ", ".join(timezone.time_zones_for_number(parsed))

    e164 = phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
    info["🔹 E.164 format"] = e164
    info["🔹 International format"] = phonenumbers.format_number(parsed, PhoneNumberFormat.INTERNATIONAL)
    info["🔹 National format"] = phonenumbers.format_number(parsed, PhoneNumberFormat.NATIONAL)

    info["🌐 Region code"] = parsed.country_code
    info["➕ Prefix"] = f"+{parsed.country_code}"

    info["🔢 National number"] = parsed.national_number
    info["📡 Possible number?"] = phonenumbers.is_possible_number(parsed)
    info["✔️ Valid number?"] = phonenumbers.is_valid_number(parsed)

    number_type = phonenumbers.number_type(parsed)
    types_dict = {
        0: "Unknown",
        1: "Fixed line",
        2: "Mobile",
        3: "VoIP",
        4: "Toll-free",
        5: "Premium",
        6: "Shared-cost",
        7: "Personal number",
        8: "Pager",
        9: "UAN",
        10: "Voicemail",
        11: "Short code",
        12: "Standard rate"
    }
    info["📗 Number type"] = types_dict.get(number_type, "Other")

    pure = e164.replace("+", "")

    info["📡 VoIP suspicion"] = starts(pure, VOIP_PREFIXES)
    info["🗑️ Disposable suspicion"] = starts(pure, DISPOSABLE_PREFIXES)
    info["💰 Premium-rate suspicion"] = starts(pure, PREMIUM_PREFIXES)
    info["🏢 Corporate line suspicion"] = starts(pure, CORPORATE_PREFIXES)

    info["🎧 Call-center guess"] = any(c.lower() in info["🏢 Carrier"].lower() for c in CALLCENTER_HINTS)

    info["⚠️ Suspicious carrier?"] = info["🏢 Carrier"] in SUSPICIOUS_CARRIERS

    info["🤖 Bot-like pattern?"] = is_bot_generated(pure)

    info["📏 Length OK for region?"] = phonenumbers.is_possible_number(parsed)

    spam_flag, details = multi_spam_scan(pure)
    info["🚨 Reported as scam/spam?"] = spam_flag
    info["📝 Scam report details"] = details

    info["🔥 Risk score (0-100)"] = generate_risk_score(info)

    info["📬 HLR/MNP"] = "Not enabled" if not hlr_api else hlr_lookup(hlr_api, pure)

    info["🔍 Reverse search"] = "Not implemented (legal restrictions)"

    return format_output(info)


def starts(num, prefixes):
    return any(num.startswith(p) for p in prefixes)

def is_bot_generated(num):
    return (
        num == "".join(sorted(num)) or
        num == "".join(sorted(num, reverse=True)) or
        len(set(num)) <= 2
    )

def multi_spam_scan(number):
    hits = 0
    details = []

    for site in SPAM_SOURCES:
        try:
            url = f"https://{site}/search/{number}"
            html = requests.get(url, timeout=4).text.lower()
            if any(k in html for k in KEYWORDS_SPAM):
                hits += 1
                details.append(f"Detected on {site}")
        except:
            pass

    if hits == 0:
        return False, "No spam records found"

    return True, f"Found reports on: {', '.join(details)}"

def generate_risk_score(info):
    score = 0
    if info["📡 VoIP suspicion"]:
        score += 20
    if info["🗑️ Disposable suspicion"]:
        score += 25
    if info["💰 Premium-rate suspicion"]:
        score += 15
    if info["🚨 Reported as scam/spam?"]:
        score += 30
    if info["⚠️ Suspicious carrier?"]:
        score += 10
    if info["🤖 Bot-like pattern?"]:
        score += 10
    return min(score, 100)

def hlr_lookup(api, number):
    return {"status": "HLR disabled in demo"}

def format_output(data):
    return "\n".join(f"{k}: {v}" for k, v in data.items())


print(phone_osint("put here the phone number or i eat ur nutella"))
