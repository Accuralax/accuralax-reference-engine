import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

# Small, deterministic registry. It can be extended without changing the API contract.
COUNTRIES = {
    "ZA": {"name":"South Africa","currency":"ZAR","symbol":"R","language":"en","locale":"en-ZA","date":"dd/MM/yyyy","time":"HH:mm","week_start":1,"measurement":"metric","phone":"+27","postal":"postal_code","address_order":["address_line1","address_line2","suburb","city","province","postal_code","country"]},
    "US": {"name":"United States","currency":"USD","symbol":"$","language":"en","locale":"en-US","date":"MM/dd/yyyy","time":"h:mm a","week_start":0,"measurement":"imperial","phone":"+1","postal":"zip_code","address_order":["address_line1","address_line2","city","state","zip_code","country"]},
    "GB": {"name":"United Kingdom","currency":"GBP","symbol":"£","language":"en","locale":"en-GB","date":"dd/MM/yyyy","time":"HH:mm","week_start":1,"measurement":"metric","phone":"+44","postal":"postcode","address_order":["address_line1","address_line2","city","county","postcode","country"]},
    "NG": {"name":"Nigeria","currency":"NGN","symbol":"₦","language":"en","locale":"en-NG","date":"dd/MM/yyyy","time":"HH:mm","week_start":1,"measurement":"metric","phone":"+234","postal":"postal_code","address_order":["address_line1","address_line2","city","state","postal_code","country"]},
    "KE": {"name":"Kenya","currency":"KES","symbol":"KSh","language":"en","locale":"en-KE","date":"dd/MM/yyyy","time":"HH:mm","week_start":1,"measurement":"metric","phone":"+254","postal":"postal_code","address_order":["address_line1","address_line2","city","county","postal_code","country"]},
    "GH": {"name":"Ghana","currency":"GHS","symbol":"GH₵","language":"en","locale":"en-GH","date":"dd/MM/yyyy","time":"HH:mm","week_start":1,"measurement":"metric","phone":"+233","postal":"postal_code","address_order":["address_line1","address_line2","city","region","postal_code","country"]},
    "DE": {"name":"Germany","currency":"EUR","symbol":"€","language":"de","locale":"de-DE","date":"dd.MM.yyyy","time":"HH:mm","week_start":1,"measurement":"metric","phone":"+49","postal":"postal_code","address_order":["address_line1","address_line2","postal_code","city","country"]},
    "FR": {"name":"France","currency":"EUR","symbol":"€","language":"fr","locale":"fr-FR","date":"dd/MM/yyyy","time":"HH:mm","week_start":1,"measurement":"metric","phone":"+33","postal":"postal_code","address_order":["address_line1","address_line2","postal_code","city","region","country"]},
    "BR": {"name":"Brazil","currency":"BRL","symbol":"R$","language":"pt","locale":"pt-BR","date":"dd/MM/yyyy","time":"HH:mm","week_start":1,"measurement":"metric","phone":"+55","postal":"postal_code","address_order":["address_line1","address_line2","neighborhood","city","state","postal_code","country"]},
    "IN": {"name":"India","currency":"INR","symbol":"₹","language":"en","locale":"en-IN","date":"dd/MM/yyyy","time":"HH:mm","week_start":1,"measurement":"metric","phone":"+91","postal":"postal_code","address_order":["address_line1","address_line2","locality","city","state","postal_code","country"]},
    "AU": {"name":"Australia","currency":"AUD","symbol":"A$","language":"en","locale":"en-AU","date":"dd/MM/yyyy","time":"h:mm a","week_start":1,"measurement":"metric","phone":"+61","postal":"postcode","address_order":["address_line1","address_line2","suburb","state","postcode","country"]},
    "CA": {"name":"Canada","currency":"CAD","symbol":"C$","language":"en","locale":"en-CA","date":"yyyy-MM-dd","time":"h:mm a","week_start":0,"measurement":"metric","phone":"+1","postal":"postal_code","address_order":["address_line1","address_line2","city","province","postal_code","country"]},
    "AE": {"name":"United Arab Emirates","currency":"AED","symbol":"د.إ","language":"ar","locale":"ar-AE","date":"dd/MM/yyyy","time":"HH:mm","week_start":6,"measurement":"metric","phone":"+971","postal":"postal_code","address_order":["address_line1","address_line2","area","city","emirate","country"]},
}
LANGUAGE_NAMES = {"en":"English","zu":"isiZulu","xh":"isiXhosa","af":"Afrikaans","fr":"Français","de":"Deutsch","pt":"Português","es":"Español","ar":"العربية","hi":"हिन्दी","sw":"Kiswahili"}

class Internationalization:
    """Resolves presentation and business locale without trusting client IP data.

    Priority: explicit user preference > tenant/org preference > browser hints > safe default.
    Timezone is taken from an explicit IANA/browser hint; UTC is the safe fallback.
    """
    def __init__(self):
        self.default_country = os.getenv("DEFAULT_COUNTRY", "ZA").upper()
        self.default_language = os.getenv("DEFAULT_LANGUAGE", "en")
        self.default_currency = os.getenv("DEFAULT_CURRENCY", "ZAR")
        self.default_timezone = os.getenv("DEFAULT_TIMEZONE", "Africa/Johannesburg")

    def _country_from_locale(self, locale):
        if not locale: return None
        parts = locale.replace("_", "-").split("-")
        if len(parts) > 1 and parts[1].upper() in COUNTRIES: return parts[1].upper()
        return None

    def _language_from_accept(self, header):
        if not header: return None
        for item in header.split(','):
            lang = item.split(';')[0].strip().lower()
            if lang:
                return lang.split('-')[0]
        return None

    def resolve(self, user=None, organisation=None, headers=None):
        user, organisation, headers = user or {}, organisation or {}, headers or {}
        browser_locale = headers.get("Accept-Language") or headers.get("accept-language")
        browser_lang = self._language_from_accept(browser_locale)
        browser_country = self._country_from_locale((browser_locale or '').split(',')[0])
        country = str(user.get('country') or organisation.get('country') or browser_country or self.default_country).upper()
        profile = dict(COUNTRIES.get(country, COUNTRIES[self.default_country]))
        language = str(user.get('language') or organisation.get('language') or browser_lang or profile['language']).split('-')[0]
        locale = str(user.get('locale') or organisation.get('locale') or profile['locale'])
        currency = str(user.get('currency') or organisation.get('currency') or profile['currency']).upper()
        timezone_name = str(user.get('timezone') or organisation.get('timezone') or headers.get('X-Timezone') or headers.get('x-timezone') or self.default_timezone)
        try:
            ZoneInfo(timezone_name)
        except Exception:
            timezone_name = self.default_timezone
        try:
            local_now = datetime.now(ZoneInfo(timezone_name))
        except Exception:
            local_now = datetime.now(ZoneInfo(self.default_timezone))
        return {
            'country': country, 'country_name': profile['name'], 'language': language,
            'language_name': LANGUAGE_NAMES.get(language, language), 'locale': locale,
            'currency': currency, 'currency_symbol': profile['symbol'] if currency == profile['currency'] else currency,
            'timezone': timezone_name, 'utc_offset': local_now.strftime('%z'),
            'date_format': profile['date'], 'time_format': profile['time'], 'week_start': profile['week_start'],
            'measurement_system': profile['measurement'], 'phone_country_code': profile['phone'],
            'postal_field': profile['postal'], 'address_order': profile['address_order'],
            'decimal_separator': ',' if language in {'de','fr','pt'} else '.',
            'thousands_separator': '.' if language == 'de' else (' ' if language == 'fr' else ','),
            'text_direction': 'rtl' if language in {'ar'} else 'ltr',
            'auto_detected': not bool(user or organisation),
            'resolution': {'user': bool(user), 'organisation': bool(organisation), 'browser': bool(browser_locale), 'safe_default': not bool(browser_locale or user or organisation)},
        }

    def format_address_schema(self, context):
        return {'country': context['country'], 'fields': context['address_order'], 'postal_field': context['postal_field'], 'direction': context['text_direction']}

    def health(self):
        return {'status':'ok','engine':'internationalization','countries_supported':len(COUNTRIES),'auto_switch':True,'credentials_exposed':False}
