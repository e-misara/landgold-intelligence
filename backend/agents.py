import random
from datetime import datetime

AGENTS = {
    "james":   {"name": "James",   "lang": "en"},
    "dmitry":  {"name": "Dmitry",  "lang": "ru"},
    "abdullah":{"name": "Abdullah","lang": "ar"},
    "selim":   {"name": "Selim",   "lang": "tr"},
}

# Each agent has 2 template variants — no AI disclaimers, native register
TEMPLATES = {
    "james": [
        "Looking at the numbers — {area_m2:,.0f} m² of {land_type}, sitting at ${current_usd_m2}/m² today. "
        "If that {gov_signal} plays out, you're looking at ${projected_usd_m2}/m², total projected value ${total_projected_usd:,.0f}. "
        "ROI: {roi_percent}%. Risk score {risk_score}/100 — {risk_label}. My call: {verdict}",

        "Straight to it: current buy-in is ${total_current_usd:,.0f}, "
        "projection hits ${total_projected_usd:,.0f} on the back of '{gov_signal}'. "
        "Title constraints flagged: {constraints}. Risk is {risk_label} at {risk_score}/100. {verdict}",
    ],
    "dmitry": [
        "Анализ завершён. Участок {area_m2:,.0f} м², текущая стоимость ${current_usd_m2}/м². "
        "С учётом сигнала «{gov_signal}» прогноз: ${projected_usd_m2}/м² — итого ${total_projected_usd:,.0f}. "
        "ROI: {roi_percent}%. Риск: {risk_score}/100 ({risk_label}). Рекомендация: {verdict}",

        "Капитал защищается прежде всего. Актив {area_m2:,.0f} м², риск-индекс {risk_score}. "
        "При реализации «{gov_signal}» потенциал роста составит ${total_projected_usd:,.0f}. "
        "Обременения: {constraints}. {verdict}",
    ],
    "abdullah": [
        "بارك الله في هذه الصفقة. مساحة الأرض {area_m2:,.0f} متر مربع، السعر الحالي ${current_usd_m2}/م². "
        "مع إشارة «{gov_signal}» التوقع ${projected_usd_m2}/م²، الإجمالي ${total_projected_usd:,.0f}. "
        "العائد: {roi_percent}٪. المخاطرة: {risk_score}/100 — {risk_label}. التوصية: {verdict}",

        "الثقة أساس كل استثمار. القيود المسجّلة: {constraints}. "
        "القيمة الحالية ${total_current_usd:,.0f} مقابل التوقع ${total_projected_usd:,.0f}. "
        "مؤشر المخاطرة {risk_label}. {verdict}",
    ],
    "selim": [
        "{area_m2:,.0f} m² {land_type} parseli incelendi. Güncel birim değer ${current_usd_m2}/m². "
        "«{gov_signal}» sinyali gerçekleşirse projeksiyon ${projected_usd_m2}/m², toplam ${total_projected_usd:,.0f}. "
        "ROI: %{roi_percent}. Risk skoru {risk_score}/100 — {risk_label}. Sonuç: {verdict}",

        "3194 sayılı Kanun ve tapu kütüğü kısıtları değerlendirildi. "
        "Tespit edilen kısıtlar: {constraints}. Yola mesafe uyumu: {setback_status}. "
        "Yatırım risk düzeyi: {risk_label} ({risk_score}/100). {verdict}",
    ],
}

VERDICTS = {
    "LOW": {
        "james":    "I'd move on this fast.",
        "dmitry":   "Рекомендую к приобретению.",
        "abdullah": "أنصح بالمضي قُدُماً.",
        "selim":    "Alım için uygun görünüyor.",
    },
    "MEDIUM": {
        "james":    "Worth a closer look — negotiate hard on price.",
        "dmitry":   "Требует дополнительной проверки перед сделкой.",
        "abdullah": "يستحق الدراسة مع الحذر الواجب.",
        "selim":    "Dikkatli inceleme gerektirir, müzakere şart.",
    },
    "HIGH": {
        "james":    "Risky. Get legal on the title before anything else.",
        "dmitry":   "Высокий риск. Юридическая экспертиза обязательна.",
        "abdullah": "مخاطرة عالية. لا تتقدم بدون مراجعة قانونية.",
        "selim":    "Tapu müşavirliği olmadan ilerlemeyin.",
    },
    "CRITICAL": {
        "james":    "Walk away unless you have serious legal firepower.",
        "dmitry":   "Критический уровень риска — отказ рекомендован.",
        "abdullah": "خطر حرج. التوصية بالانسحاب الفوري.",
        "selim":    "Kritik risk. Bu aşamada yatırım tavsiye edilmez.",
    },
}


def generate_message(agent_key: str, analysis: dict, risk: dict) -> dict:
    agent   = AGENTS[agent_key]
    verdict = VERDICTS[risk["risk_label"]][agent_key]
    template = random.choice(TEMPLATES[agent_key])

    ctx = {
        **analysis,
        **risk,
        "verdict":        verdict,
        "setback_status": "uyumlu" if risk["setback_compliant"] else "uyumsuz",
    }

    try:
        message = template.format(**ctx)
    except (KeyError, ValueError):
        message = template

    return {
        "agent":     agent["name"],
        "lang":      agent["lang"],
        "message":   message,
        "status":    "PENDING_APPROVAL",
        "timestamp": datetime.utcnow().isoformat(),
    }


def generate_all(analysis: dict, risk: dict) -> list:
    return [generate_message(k, analysis, risk) for k in AGENTS]
