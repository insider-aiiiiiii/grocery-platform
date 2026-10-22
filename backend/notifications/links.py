import re
import urllib.parse
from typing import Any, Dict, Optional, Union

DEFAULT_LANGUAGE = "hinglish"
SUPPORTED_LANGUAGES = ("hinglish", "en", "hi")

MERCHANT_ACTION_TEMPLATES: Dict[str, Dict[str, str]] = {
    "ORDER_ACCEPTED": {
        "hinglish": "Hello! {shop_name} ne aapka order #{order_number} accept kar liya hai aur packing shuru hai. Jaldi deliver karenge!",
        "en": "Hello! Your order #{order_number} has been accepted by {shop_name} and is being packed. We will deliver it soon!",
        "hi": "नमस्ते! {shop_name} ने आपका ऑर्डर #{order_number} स्वीकार कर लिया है और सामान पैक हो रहा है। जल्द ही डिलीवर करेंगे!",
    },
    "ORDER_REJECTED": {
        "hinglish": "Hello, hum abhi {shop_name} par aapka order #{order_number} accept nahi kar pa rahe hain. Asuvidha ke liye sorry.",
        "en": "Hello, we are unable to accept your order #{order_number} at {shop_name} at this time. Sorry for the inconvenience.",
        "hi": "नमस्ते, हम अभी {shop_name} पर आपका ऑर्डर #{order_number} स्वीकार करने में असमर्थ हैं। असुविधा के लिए हमें खेद है।",
    },
    "QUANTITY_REDUCED": {
        "hinglish": "Hello! {shop_name} par aapke order #{order_number} me kuch items out of stock the, isliye quantity adjust ki gayi hai. Updated bill ₹{total_amount} hai.",
        "en": "Hello! Regarding your order #{order_number} at {shop_name}: some items were unavailable and quantities were adjusted. Updated total is ₹{total_amount}.",
        "hi": "नमस्ते! {shop_name} पर आपके ऑर्डर #{order_number} में कुछ सामान उपलब्ध नहीं था, इसलिए मात्रा बदली गई है। नया कुल बिल ₹{total_amount} है।",
    },
    "ORDER_PREPARING": {
        "hinglish": "Hello! {shop_name} par aapka order #{order_number} pack hona shuru ho gaya hai. Jald hi ready hoga!",
        "en": "Hello! Your order #{order_number} is being packed at {shop_name} and will be ready soon.",
        "hi": "नमस्ते! {shop_name} पर आपका ऑर्डर #{order_number} पैक होना शुरू हो गया है। जल्द ही तैयार होगा!",
    },
    "ORDER_READY": {
        "hinglish": "Hello! {shop_name} par aapka order #{order_number} ready hai! Pickup ke liye aa sakte hain ya deliver hone nikal raha hai.",
        "en": "Hello! Your order #{order_number} is ready at {shop_name}! You can pick it up or it's out for delivery.",
        "hi": "नमस्ते! {shop_name} पर आपका ऑर्डर #{order_number} तैयार है! आप इसे ले जा सकते हैं या डिलीवरी के लिए निकल रहा है।",
    },
    "ORDER_COMPLETED": {
        "hinglish": "Namaste! {shop_name} par aapka order #{order_number} deliver ho gaya hai. Shopping ke liye thank you! Dobara order karne ke liye is link par click karein: {shop_order_url}",
        "en": "Hello! Your order #{order_number} from {shop_name} has been delivered. Thank you for shopping with us! To reorder, please visit: {shop_order_url}",
        "hi": "नमस्ते! {shop_name} पर आपका ऑर्डर #{order_number} डिलीवर हो गया है। खरीदारी के लिए धन्यवाद! दोबारा ऑर्डर करने के लिए इस लिंक पर जाएं: {shop_order_url}",
    },
}

CUSTOMER_ACTION_TEMPLATES: Dict[str, Dict[str, str]] = {
    "NEW_ORDER": {
        "hinglish": "Namaste {shop_name}, maine order #{order_number} place kiya hai total ₹{total_amount} ka. Please check karke confirm karein.",
        "en": "Hi {shop_name}, I have placed order #{order_number} for ₹{total_amount}. Please confirm availability.",
        "hi": "नमस्ते {shop_name}, मैंने ₹{total_amount} का ऑर्डर #{order_number} दिया है। कृपया सामान चेक करके बताएं।",
    },
}



def normalize_whatsapp_phone(phone_raw: Optional[str], default_country_code: str = "91") -> str:
    """
    Normalizes a phone string into a numerical digits-only E.164 string required by wa.me links.
    - Strips spaces, dashes, plus signs, brackets, and non-numeric characters.
    - Prepends default_country_code for 10-digit numbers (common in India).
    - Strips leading zero from 11-digit numbers (0XXXXXXXXXX) and prepends country code.
    - Raises ValueError if no valid digits exist or input is empty.
    """
    if not phone_raw:
        raise ValueError("Phone number cannot be empty.")

    digits = re.sub(r"\D", "", str(phone_raw))
    if not digits:
        raise ValueError("Phone number must contain numeric digits.")

    # 10-digit mobile number: prepend default country code (e.g. 9876543210 -> 919876543210)
    if len(digits) == 10:
        return f"{default_country_code}{digits}"

    # 11-digit starting with 0: replace 0 with default country code (e.g. 09876543210 -> 919876543210)
    if len(digits) == 11 and digits.startswith("0"):
        return f"{default_country_code}{digits[1:]}"

    return digits


def build_whatsapp_link(phone: str, message_text: str, default_country_code: str = "91") -> str:
    """
    Constructs a standard, percent-encoded https://wa.me/<phone>?text=<encoded_text> URL.
    Properly handles Unicode characters (Devanagari, emojis, symbols) via urllib.parse.quote.
    """
    clean_phone = normalize_whatsapp_phone(phone, default_country_code=default_country_code)
    encoded_text = urllib.parse.quote(message_text, safe="")
    return f"https://wa.me/{clean_phone}?text={encoded_text}"


def resolve_order_customer_phone(order: Any) -> str:
    """
    Authoritatively resolves the customer's phone number from the Order instance.
    Follows priority order:
    1. customer_phone_snapshot (frozen at checkout)
    2. delivery_address.recipient_phone (if associated)
    3. customer.whatsapp_number (profile contact)
    """
    phone = getattr(order, "customer_phone_snapshot", None)
    if phone:
        return str(phone).strip()

    delivery_address = getattr(order, "delivery_address", None)
    if delivery_address and getattr(delivery_address, "recipient_phone", None):
        return str(delivery_address.recipient_phone).strip()

    customer = getattr(order, "customer", None)
    if customer and getattr(customer, "whatsapp_number", None):
        return str(customer.whatsapp_number).strip()

    raise ValueError(f"Order #{getattr(order, 'id', 'unknown')} has no valid customer contact phone.")


def _hydrate_template(template_format: str, context: Dict[str, str]) -> str:
    """
    Hydrates a template string supporting both standard python format {var}
    and mustache-style {{var}} placeholders.
    """
    text = template_format
    for key, val in context.items():
        text = text.replace(f"{{{{{key}}}}}", str(val))
        text = text.replace(f"{{{key}}}", str(val))
    return text


def get_template_text(event_type: str, language: str, context: Dict[str, str]) -> str:
    """
    Retrieves the message text for an event and language.
    Checks for an active custom NotificationTemplate in the database first;
    falls back to built-in default templates if none exists.
    """
    from notifications.models import NotificationTemplate

    lang_code_map = {
        "en": ["en", "en_US"],
        "hi": ["hi", "hi_IN"],
        "hinglish": ["hinglish", "hi_Latn"],
    }
    allowed_codes = lang_code_map.get(language, [language])

    try:
        custom = (
            NotificationTemplate.objects.filter(
                event_type=event_type,
                language_code__in=allowed_codes,
                is_active=True,
            )
            .order_by("-updated_at")
            .first()
        )
        if custom and custom.body_format:
            return _hydrate_template(custom.body_format, context)
    except Exception:
        pass

    if event_type in MERCHANT_ACTION_TEMPLATES:
        default_template = MERCHANT_ACTION_TEMPLATES[event_type][language]
    elif event_type in CUSTOMER_ACTION_TEMPLATES:
        default_template = CUSTOMER_ACTION_TEMPLATES[event_type][language]
    else:
        raise ValueError(f"Unknown event_type '{event_type}' for template resolution.")

    return _hydrate_template(default_template, context)


def get_merchant_order_action_links(
    order: Any,
    event_type: str,
    language: Optional[str] = None,
    default_country_code: str = "91",
) -> Union[str, Dict[str, str]]:
    """
    Generates pre-filled wa.me Click-to-Chat link(s) for a Merchant to contact the Customer
    regarding an Order status event (ORDER_ACCEPTED, ORDER_REJECTED, QUANTITY_REDUCED).

    If language is specified (e.g. 'en', 'hi', 'hinglish'), returns the single link string.
    If language is None or 'all', returns a dictionary mapping all supported languages to links.
    """
    event_key = event_type.upper().strip()
    if event_key not in MERCHANT_ACTION_TEMPLATES:
        raise ValueError(
            f"Unsupported event_type '{event_type}'. Must be one of: {list(MERCHANT_ACTION_TEMPLATES.keys())}"
        )

    customer_phone = resolve_order_customer_phone(order)

    # Prepare template context
    order_id = str(getattr(order, "id", ""))
    short_order_num = order_id[:8] if order_id else "UNKNOWN"
    shop = getattr(order, "shop", None)
    shop_name = getattr(shop, "name", "Store") if shop else "Store"
    total_amount = str(getattr(order, "total_amount", "0.00"))
    public_slug = getattr(shop, "public_slug", "") if shop else ""
    shop_order_url = f"/api/v1/shops/public/{public_slug}/" if public_slug else ""

    context = {
        "order_number": short_order_num,
        "shop_name": shop_name,
        "total_amount": total_amount,
        "shop_order_url": shop_order_url,
    }

    if language:
        lang_key = language.lower().strip()
        if lang_key not in SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Unsupported language '{language}'. Supported languages: {SUPPORTED_LANGUAGES}"
            )
        message_text = get_template_text(event_key, lang_key, context)
        return build_whatsapp_link(customer_phone, message_text, default_country_code=default_country_code)

    # Return all supported languages
    result: Dict[str, str] = {}
    for lang in SUPPORTED_LANGUAGES:
        message_text = get_template_text(event_key, lang, context)
        result[lang] = build_whatsapp_link(customer_phone, message_text, default_country_code=default_country_code)

    return result


def get_merchant_order_action_link(
    order: Any,
    event_type: str,
    language: str = DEFAULT_LANGUAGE,
    default_country_code: str = "91",
) -> Optional[str]:
    """
    Generates a single pre-filled wa.me Click-to-Chat link in the merchant's preferred language
    (default: 'hinglish') to contact the customer upon order acceptance, rejection, or cancellation.
    Returns None safely if customer phone is missing or unparseable.
    """
    try:
        return get_merchant_order_action_links(
            order=order,
            event_type=event_type,
            language=language,
            default_country_code=default_country_code,
        )
    except Exception:
        return None


def get_customer_order_notification_links(
    order: Any,
    language: Optional[str] = None,
    default_country_code: str = "91",
) -> Union[str, Dict[str, str], None]:
    """
    Generates pre-filled wa.me Click-to-Chat link(s) for a Customer to notify the Merchant
    regarding their newly created Order (NEW_ORDER).

    When language is None, returns a dictionary of primary languages ('hinglish', 'en') for the
    customer confirmation screen. If a specific language is provided, returns that single link string.
    If language='all', returns all supported languages.

    Resolves target recipient strictly from order.shop.contact_number.
    Returns None gracefully if the shop has no valid contact number, preserving
    strict Order state isolation without interrupting checkout flows.
    """
    shop = getattr(order, "shop", None)
    if not shop:
        return None

    contact_number = getattr(shop, "contact_number", None)
    if not contact_number:
        return None

    try:
        clean_phone = normalize_whatsapp_phone(contact_number, default_country_code=default_country_code)
    except ValueError:
        return None

    order_id = str(getattr(order, "id", ""))
    short_order_num = order_id[:8] if order_id else "UNKNOWN"
    shop_name = getattr(shop, "name", "Store")
    total_amount = str(getattr(order, "total_amount", "0.00"))
    customer_name = getattr(order, "customer_name_snapshot", "")

    context = {
        "order_number": short_order_num,
        "shop_name": shop_name,
        "total_amount": total_amount,
        "customer_name": customer_name,
    }

    if language and language.lower().strip() != "all":
        lang_key = language.lower().strip()
        if lang_key not in SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Unsupported language '{language}'. Supported languages: {SUPPORTED_LANGUAGES}"
            )
        message_text = get_template_text("NEW_ORDER", lang_key, context)
        return build_whatsapp_link(clean_phone, message_text, default_country_code=default_country_code)

    target_languages = SUPPORTED_LANGUAGES if language == "all" else ("hinglish", "en")
    result: Dict[str, str] = {}
    for lang in target_languages:
        message_text = get_template_text("NEW_ORDER", lang, context)
        result[lang] = build_whatsapp_link(clean_phone, message_text, default_country_code=default_country_code)

    return result


